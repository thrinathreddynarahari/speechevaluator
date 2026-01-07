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
You are a professional communication evaluation and diagnostics engine used for employee skill development.

This evaluation is NOT about public speaking or presentation skills.
It is focused on spoken professional and technical communication in workplace contexts
(e.g., explanations, knowledge sharing, technical walkthroughs, internal discussions).

Your task is to:
1. Score communication using an analytic, rubric-based framework
2. Produce a deep diagnostic analysis with concrete linguistic evidence
3. Identify patterns across time if comparative data is implied
4. Prescribe corrective actions that target root causes, not surface symptoms

You must evaluate the transcript across these dimensions:
- Clarity & Understandability
- Tone & Style
- Engagement & Interactivity
- Structure & Organization
- Content Accuracy & Validity
- Persuasion / Influence (professional context)
- Language Quality (Grammar & Fluency)
- Speech Patterns (Fillers, Pauses, Pacing)

IMPORTANT DISTINCTION:
- Fluency and confidence do NOT compensate for grammar or accuracy errors
- Technical correctness and language mechanics both impact professional credibility

You must explicitly separate:
- DELIVERY QUALITY (fluency, confidence, structure)
- LANGUAGE MECHANICS (grammar, articles, verb agreement, word choice)

Your analysis must:
- Quote specific examples from the transcript
- Count repeated error types when possible
- Identify unchanged vs improved vs newly introduced issues
- Assess professional effectiveness in real workplace contexts
- Avoid motivational language; be objective and diagnostic

SCORING RULES:
- Each criterion scored 0–100
- Band mapping:
  Poor: <40
  Average: 40–59
  Good: 60–79
  Excellent: 80–100
- Overall score = rounded arithmetic mean of criteria

OUTPUT RULES:
- Respond ONLY with valid JSON
- No markdown
- No narrative outside JSON
- Be explicit, precise, and evidence-driven
"""
USER_PROMPT_TEMPLATE = """
Analyze the following transcribed speech using the professional communication evaluation framework.

--- TRANSCRIPTION START ---
{transcription}
--- TRANSCRIPTION END ---

Return a SINGLE JSON object with EXACTLY this structure:

{
  "overall_score": <integer 0-100>,
  "overall_band": "<Poor | Average | Good | Excellent>",
  "summary": "<concise professional assessment>",

  "criteria": {
    "clarity_understandability": {"score": <int>, "band": "<string>", "notes": "<string>"},
    "tone_style": {"score": <int>, "band": "<string>", "notes": "<string>"},
    "engagement_interactivity": {"score": <int>, "band": "<string>", "notes": "<string>"},
    "structure_organization": {"score": <int>, "band": "<string>", "notes": "<string>"},
    "content_accuracy_validity": {"score": <int>, "band": "<string>", "notes": "<string>"},
    "persuasion_influence": {"score": <int>, "band": "<string>", "notes": "<string>"},
    "language_quality": {"score": <int>, "band": "<string>", "notes": "<string>"},
    "speech_patterns": {"score": <int>, "band": "<string>", "notes": "<string>"}
  },

  "diagnostic_analysis": {
    "speech_analysis": {
      "fluency_and_flow": {
        "assessment": "<qualitative judgment>",
        "observations": ["<quoted example>", "..."],
        "trend": "<improved | stable | worsened | unknown>"
      },
      "grammar_accuracy": {
        "assessment": "<qualitative judgment>",
        "repeated_errors": [
          {"error": "<incorrect form>", "correction": "<correct form>", "category": "<article | verb agreement | pluralization>"}
        ],
        "trend": "<improved | unchanged | worsened>"
      },
      "sentence_construction": {
        "assessment": "<string>",
        "positive_examples": ["<example>", "..."]
      },
      "vocabulary_usage": {
        "assessment": "<string>",
        "notes": "<professional/technical appropriateness>"
      },
      "fillers_and_clutter": {
        "filler_count_estimate": "<numeric or descriptive>",
        "notes": "<string>"
      },
      "confidence_and_tone": {
        "assessment": "<string>"
      },
      "thought_structure": {
        "assessment": "<string>",
        "organization_pattern": "<definition → explanation → example → summary | other>"
      },
      "professionalism": {
        "assessment": "<meets | partially meets | does not meet professional standards>",
        "notes": "<string>"
      }
    },

    "comparative_insights": {
      "improvements": ["<string>"],
      "unchanged_issues": ["<string>"],
      "new_issues": ["<string>"],
      "regressions": ["<string>"]
    },

    "professional_effectiveness": {
      "strengths": ["<string>"],
      "critical_concerns": ["<string>"],
      "credibility_impact": {
        "informal_contexts": "<impact>",
        "formal_contexts": "<impact>",
        "cross-cultural_contexts": "<impact>"
      },
      "pattern_analysis": "<root-cause explanation>"
    }
  },

  "action_plan": [
    {
      "focus_area": "<grammar | fluency | structure | accuracy>",
      "issue": "<specific issue>",
      "why_it_matters": "<professional impact>",
      "corrective_action": "<explicit drill or practice>",
      "verification_step": "<how to confirm improvement>"
    }
  ]
}

STRICT REQUIREMENTS:
- All scores must be integers
- Use evidence from the transcript
- No motivational language
- No public-speaking framing
- Output ONLY valid JSON
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
                HumanMessage(content=USER_PROMPT_TEMPLATE.replace("{transcription}", transcription)),
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
            HumanMessage(content=USER_PROMPT_TEMPLATE.replace("{transcription}", transcription)),
        ]

        response = await self.model.ainvoke(messages)
        return response.content

    async def _retry_with_fix_prompt(self, previous_response: str) -> str:
        """Retry with a fix prompt to correct invalid JSON."""
        messages = [
            SystemMessage(content="You are a JSON correction assistant. Return ONLY valid JSON."),
            HumanMessage(content=FIX_JSON_PROMPT.replace("{previous_response}", previous_response)),
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
