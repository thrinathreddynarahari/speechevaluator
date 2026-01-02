"""Report generation service using Claude via LangChain."""

import logging

from fastapi import HTTPException
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import ValidationError

from config.settings import settings
from schemas.evaluation import EvaluationReportSchema

logger = logging.getLogger(__name__)

# System prompt for English evaluation
SYSTEM_PROMPT = """You are an expert English communication coach and evaluator. Your task is to analyze transcribed speech and provide a comprehensive evaluation of the speaker's English communication skills.

Analyze the transcription for:
1. Fluency - smoothness of speech, hesitations, filler words
2. Grammar - correctness of sentence structures, tenses, agreements
3. Pronunciation - clarity and accuracy (based on transcription patterns)
4. Vocabulary - range, appropriateness, word choice
5. Structure - logical organization, coherence, flow of ideas

Provide constructive, actionable feedback that helps the speaker improve.

CRITICAL: You must respond with ONLY valid JSON. No markdown formatting, no code blocks, no commentary before or after the JSON. The response must be parseable as raw JSON."""

USER_PROMPT_TEMPLATE = """Analyze the following transcribed speech and provide a detailed evaluation:

--- TRANSCRIPTION START ---
{transcription}
--- TRANSCRIPTION END ---

Provide your evaluation as a JSON object with exactly this structure:
{{
  "overall_score": <integer 0-100>,
  "summary": "<brief overall assessment>",
  "strengths": ["<strength 1>", "<strength 2>", ...],
  "improvements": ["<area 1>", "<area 2>", ...],
  "fluency": {{"score": <0-100>, "notes": "<detailed notes>"}},
  "grammar": {{"score": <0-100>, "notes": "<detailed notes>"}},
  "pronunciation": {{"score": <0-100>, "notes": "<detailed notes>"}},
  "vocabulary": {{"score": <0-100>, "notes": "<detailed notes>"}},
  "structure": {{"score": <0-100>, "notes": "<detailed notes>"}},
  "action_plan": [
    {{"item": "<what to do>", "why": "<reason>", "how": "<method>"}},
    ...
  ]
}}

Requirements:
- overall_score: integer between 0 and 100
- strengths: 1-10 items
- improvements: 1-10 items
- action_plan: 1-7 items
- All scores must be integers between 0 and 100

Return ONLY the JSON object, nothing else."""

FIX_JSON_PROMPT = """The previous response was not valid JSON. Please fix it and return ONLY valid JSON matching this exact structure:

{{
  "overall_score": <integer 0-100>,
  "summary": "<string>",
  "strengths": ["<string>", ...],
  "improvements": ["<string>", ...],
  "fluency": {{"score": <0-100>, "notes": "<string>"}},
  "grammar": {{"score": <0-100>, "notes": "<string>"}},
  "pronunciation": {{"score": <0-100>, "notes": "<string>"}},
  "vocabulary": {{"score": <0-100>, "notes": "<string>"}},
  "structure": {{"score": <0-100>, "notes": "<string>"}},
  "action_plan": [{{"item": "<string>", "why": "<string>", "how": "<string>"}}]
}}

Previous invalid response:
{previous_response}

Return ONLY valid JSON, no markdown, no code blocks, no explanation."""


class ReportService:
    """Service for generating evaluation reports using Claude."""

    def __init__(self):
        """Initialize the service with Claude configuration."""
        self.model = ChatAnthropic(
            api_key=settings.anthropic_api_key,
            model=settings.claude_model,
            temperature=0.3,
            max_tokens=4096,
        )

    async def generate_report(
        self,
        transcription: str,
    ) -> EvaluationReportSchema:
        """Generate an evaluation report from transcription text.

        Uses Claude to analyze the transcription and produce a structured
        evaluation report. Includes retry logic for JSON parsing failures.

        Args:
            transcription: The transcribed speech text to evaluate.

        Returns:
            Validated EvaluationReportSchema object.

        Raises:
            HTTPException: 502 if Claude API fails or output cannot be parsed.
        """
        if not transcription or not transcription.strip():
            raise HTTPException(
                status_code=422,
                detail="Transcription is empty, cannot generate report",
            )

        logger.info(
            "Generating evaluation report for transcription: length=%d chars",
            len(transcription),
        )

        try:
            # First attempt with structured output
            report = await self._generate_with_structured_output(transcription)
            if report:
                return report

            # Fallback to manual parsing
            response_text = await self._generate_raw_response(transcription)
            report = self._parse_and_validate(response_text)
            if report:
                return report

            # Retry with fix prompt
            logger.warning("First attempt failed, retrying with fix prompt")
            fixed_response = await self._retry_with_fix_prompt(response_text)
            report = self._parse_and_validate(fixed_response)
            if report:
                return report

            raise HTTPException(
                status_code=502,
                detail="Failed to generate valid evaluation report after retry",
            )

        except HTTPException:
            raise
        except Exception as e:
            logger.exception("Unexpected error generating report")
            raise HTTPException(
                status_code=502,
                detail=f"Report generation failed: {str(e)}",
            ) from e

    async def _generate_with_structured_output(
        self,
        transcription: str,
    ) -> EvaluationReportSchema | None:
        """Attempt to generate report using structured output."""
        try:
            structured_model = self.model.with_structured_output(
                EvaluationReportSchema,
                method="json_schema",
            )

            messages = [
                SystemMessage(content=SYSTEM_PROMPT),
                HumanMessage(content=USER_PROMPT_TEMPLATE.format(transcription=transcription)),
            ]

            result = await structured_model.ainvoke(messages)
            logger.info("Successfully generated report with structured output")
            return result

        except Exception as e:
            logger.warning(
                "Structured output failed, falling back to manual parsing: %s",
                str(e),
            )
            return None

    async def _generate_raw_response(self, transcription: str) -> str:
        """Generate raw text response from Claude."""
        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=USER_PROMPT_TEMPLATE.format(transcription=transcription)),
        ]

        response = await self.model.ainvoke(messages)
        return response.content

    async def _retry_with_fix_prompt(self, previous_response: str) -> str:
        """Retry with a fix prompt to correct invalid JSON."""
        messages = [
            SystemMessage(content="You are a JSON correction assistant. Return ONLY valid JSON."),
            HumanMessage(content=FIX_JSON_PROMPT.format(previous_response=previous_response)),
        ]

        response = await self.model.ainvoke(messages)
        return response.content

    def _parse_and_validate(self, response_text: str) -> EvaluationReportSchema | None:
        """Parse and validate the response text as JSON.

        Args:
            response_text: Raw response from Claude.

        Returns:
            Validated EvaluationReportSchema or None if parsing fails.
        """
        import json

        # Clean the response text
        text = response_text.strip()

        # Remove markdown code blocks if present
        if text.startswith("```"):
            lines = text.split("\n")
            # Remove first and last lines (code block markers)
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            text = "\n".join(lines)

        text = text.strip()

        try:
            data = json.loads(text)
            report = EvaluationReportSchema.model_validate(data)
            logger.info("Successfully parsed and validated report")
            return report

        except json.JSONDecodeError as e:
            logger.warning("JSON parsing failed: %s", str(e))
            return None
        except ValidationError as e:
            logger.warning("Pydantic validation failed: %s", str(e))
            return None
