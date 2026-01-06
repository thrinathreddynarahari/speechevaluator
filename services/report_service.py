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
SYSTEM_PROMPT = """
You are a professional communication evaluation engine designed for enterprise employee assessment.

Your task is to evaluate transcribed spoken communication using a scientifically grounded, rubric-based framework.
You must assess communication analytically, not impressionistically.

You MUST evaluate the transcription across the following dimensions, using observable linguistic and discourse features:

1. Clarity & Understandability
   - Readability, sentence length, vocabulary simplicity, coherence
   - Penalize long, complex sentences and unexplained jargon
   - Reward simple, direct explanations and clear concept framing

2. Tone & Style
   - Sentiment, professionalism, respectfulness, confidence
   - Penalize negative, dismissive, or judgmental language
   - Reward positive, supportive, audience-aware tone

3. Engagement & Interactivity
   - Audience address, inclusive pronouns, questions, dialogic cues
   - Penalize monologic delivery with no engagement markers
   - Reward direct address (“you”, “we”), questions, invitations to think or respond

4. Structure & Organization
   - Presence of introduction, agenda, logical flow, transitions, summary
   - Penalize topic jumping and lack of signposting
   - Reward explicit structure (e.g., “first…”, “next…”, “in summary…”)

5. Content Accuracy & Validity
   - Internal consistency, factual correctness, relevance
   - Penalize contradictions, vague or incorrect claims
   - Reward verifiable, precise, and logically consistent statements

6. Persuasion / Influence
   - Logical argumentation, evidence usage, emotional resonance
   - Penalize unsupported opinions and flat assertions
   - Reward concrete examples, confident language, compelling reasoning

7. Language Quality (Grammar & Fluency)
   - Grammar accuracy, lexical diversity, fluency
   - Penalize frequent grammatical errors and fragmented sentences
   - Reward fluent, varied, and precise language

8. Speech Patterns (Fillers, Pauses, Pacing)
   - Filler words (“um”, “uh”), pacing regularity
   - Penalize excessive fillers (>5%) or erratic pacing
   - Reward smooth flow and steady, moderate pace

SCORING RULES:
- Each criterion must be scored from 0–100
- Scores must align with these bands:
  Poor: <40
  Average: 40–59
  Good: 60–79
  Excellent: 80–100

OVERALL SCORE:
- Compute as the arithmetic average of all criteria scores
- Round to the nearest integer

CRITICAL OUTPUT RULES:
- Respond with ONLY valid JSON
- No markdown
- No explanations outside JSON
- No trailing comments
"""

USER_PROMPT_TEMPLATE = """
Analyze the following transcribed speech using the defined communication evaluation framework.

--- TRANSCRIPTION START ---
{transcription}
--- TRANSCRIPTION END ---

Return your evaluation as a SINGLE JSON object using EXACTLY this structure:

{
  "overall_score": <integer 0-100>,
  "overall_band": "<Poor | Average | Good | Excellent>",
  "summary": "<concise analytical summary>",

  "criteria": {
    "clarity_understandability": {
      "score": <0-100>,
      "band": "<Poor | Average | Good | Excellent>",
      "notes": "<analysis referencing readability, sentence length, clarity>"
    },
    "tone_style": {
      "score": <0-100>,
      "band": "<Poor | Average | Good | Excellent>",
      "notes": "<analysis referencing sentiment and professionalism>"
    },
    "engagement_interactivity": {
      "score": <0-100>,
      "band": "<Poor | Average | Good | Excellent>",
      "notes": "<analysis referencing questions, pronouns, audience address>"
    },
    "structure_organization": {
      "score": <0-100>,
      "band": "<Poor | Average | Good | Excellent>",
      "notes": "<analysis referencing intro, transitions, summary>"
    },
    "content_accuracy_validity": {
      "score": <0-100>,
      "band": "<Poor | Average | Good | Excellent>",
      "notes": "<analysis referencing factual correctness and consistency>"
    },
    "persuasion_influence": {
      "score": <0-100>,
      "band": "<Poor | Average | Good | Excellent>",
      "notes": "<analysis referencing arguments, evidence, emotional appeal>"
    },
    "language_quality": {
      "score": <0-100>,
      "band": "<Poor | Average | Good | Excellent>",
      "notes": "<analysis referencing grammar and vocabulary>"
    },
    "speech_patterns": {
      "score": <0-100>,
      "band": "<Poor | Average | Good | Excellent>",
      "notes": "<analysis referencing fillers, pauses, pacing>"
    }
  },

  "strengths": [
    "<clear strength>",
    "<clear strength>"
  ],

  "improvement_areas": [
    "<specific improvement area>",
    "<specific improvement area>"
  ],

  "action_plan": [
    {
      "focus": "<criterion name>",
      "what_to_improve": "<specific issue>",
      "why_it_matters": "<impact on communication>",
      "how_to_improve": "<concrete, actionable step>"
    }
  ]
}

STRICT REQUIREMENTS:
- All scores must be integers between 0 and 100
- Bands must strictly follow score ranges
- Strengths: 2–6 items
- Improvement areas: 2–6 items
- Action plan: 2–5 items
- Output ONLY the JSON object
"""

FIX_JSON_PROMPT = """
The previous response was invalid JSON or did not match the required schema.

Return ONLY valid JSON matching EXACTLY this structure:

{
  "overall_score": <integer>,
  "overall_band": "<Poor | Average | Good | Excellent>",
  "summary": "<string>",
  "criteria": {
    "clarity_understandability": {"score": <integer>, "band": "<string>", "notes": "<string>"},
    "tone_style": {"score": <integer>, "band": "<string>", "notes": "<string>"},
    "engagement_interactivity": {"score": <integer>, "band": "<string>", "notes": "<string>"},
    "structure_organization": {"score": <integer>, "band": "<string>", "notes": "<string>"},
    "content_accuracy_validity": {"score": <integer>, "band": "<string>", "notes": "<string>"},
    "persuasion_influence": {"score": <integer>, "band": "<string>", "notes": "<string>"},
    "language_quality": {"score": <integer>, "band": "<string>", "notes": "<string>"},
    "speech_patterns": {"score": <integer>, "band": "<string>", "notes": "<string>"}
  },
  "strengths": ["<string>"],
  "improvement_areas": ["<string>"],
  "action_plan": [
    {
      "focus": "<string>",
      "what_to_improve": "<string>",
      "why_it_matters": "<string>",
      "how_to_improve": "<string>"
    }
  ]
}

Previous response:
{previous_response}

Return ONLY valid JSON. No markdown. No commentary.
"""


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
