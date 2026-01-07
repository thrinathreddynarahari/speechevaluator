"""Pydantic schemas for evaluation API request/response and Claude output validation."""

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class EvaluationRequest(BaseModel):
    """Optional form fields for the evaluation request."""

    language_code: str = Field(
        default="eng",
        description="Language code for transcription (ISO 639-3)",
    )
    diarize: bool = Field(
        default=True,
        description="Whether to enable speaker diarization",
    )
    tag_audio_events: bool = Field(
        default=True,
        description="Whether to tag audio events like laughter, applause, etc.",
    )


class CriteriaItem(BaseModel):
    """Score, band, and notes for a specific evaluation criterion."""

    score: int = Field(ge=0, le=100, description="Score from 0 to 100")
    band: str = Field(description="Performance band (Poor, Average, Good, Excellent)")
    notes: str = Field(description="Detailed analysis notes for this criterion")


class EvaluationCriteria(BaseModel):
    """Container for all 8 evaluation criteria."""

    clarity_understandability: CriteriaItem
    tone_style: CriteriaItem
    engagement_interactivity: CriteriaItem
    structure_organization: CriteriaItem
    content_accuracy_validity: CriteriaItem
    persuasion_influence: CriteriaItem
    language_quality: CriteriaItem
    speech_patterns: CriteriaItem


class ActionPlanItem(BaseModel):
    """An individual action item for improvement."""

    focus: str = Field(description="The criterion or area to focus on")
    what_to_improve: str = Field(description="Specific issue to address")
    why_it_matters: str = Field(description="Impact on communication effectiveness")
    how_to_improve: str = Field(description="Concrete, actionable step to take")


class EvaluationReportSchema(BaseModel):
    """Strict JSON schema for Claude-generated evaluation report.

    This schema is used both for structured output from Claude
    and for validation before storing in the database.
    """

    overall_score: int = Field(
        ge=0,
        le=100,
        description="Overall English communication score from 0 to 100",
    )
    overall_band: str = Field(
        description="Overall performance band",
    )
    summary: str = Field(
        description="Brief summary of the evaluation",
    )
    criteria: EvaluationCriteria = Field(
        description="Detailed scoring for all 8 criteria",
    )
    strengths: list[str] = Field(
        min_length=1,
        max_length=10,
        description="List of identified strengths (1-10 items)",
    )
    improvement_areas: list[str] = Field(
        min_length=1,
        max_length=10,
        description="List of areas for improvement (1-10 items)",
    )
    action_plan: list[ActionPlanItem] = Field(
        min_length=1,
        max_length=7,
        description="Actionable improvement plan (1-7 items)",
    )

    @field_validator("strengths", "improvement_areas")
    @classmethod
    def validate_list_not_empty(cls, v: list[str]) -> list[str]:
        """Ensure list items are non-empty strings."""
        validated = [item.strip() for item in v if item.strip()]
        if not validated:
            raise ValueError("List must contain at least one non-empty item")
        return validated


class EvaluationResponse(BaseModel):
    """Response schema for the evaluation endpoint."""

    evaluation_id: UUID = Field(
        description="ID of the EmployeeEvaluation record",
    )
    report_id: UUID = Field(
        description="ID of the EmployeeEvaluationReports record",
    )
    transcription: str = Field(
        description="Transcription text from the audio",
    )
    report: EvaluationReportSchema = Field(
        description="The generated evaluation report",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "evaluation_id": "123e4567-e89b-12d3-a456-426614174000",
                "report_id": "123e4567-e89b-12d3-a456-426614174001",
                "transcription": "Hello, I would like to discuss the quarterly report...",
                "report": {
                    "overall_score": 75,
                    "overall_band": "Good",
                    "summary": "Good communication skills with room for improvement in grammar.",
                    "criteria": {
                        "fluency": {"score": 80, "band": "Excellent", "notes": "Speaks smoothly with few hesitations."},
                        "grammar": {"score": 65, "band": "Good", "notes": "Some grammatical errors observed."},
                        "pronunciation": {"score": 78, "band": "Good", "notes": "Clear pronunciation overall."},
                        "vocabulary": {"score": 82, "band": "Excellent", "notes": "Uses varied vocabulary."},
                        "structure": {"score": 70, "band": "Good", "notes": "Could improve logical flow."},
                        "clarity_understandability": {"score": 75, "band": "Good", "notes": "Generally clear."},
                        "tone_style": {"score": 80, "band": "Excellent", "notes": "Professional tone."},
                        "engagement_interactivity": {"score": 70, "band": "Good", "notes": "Engages well."},
                        "content_accuracy_validity": {"score": 85, "band": "Excellent", "notes": "Accurate content."},
                        "persuasion_influence": {"score": 72, "band": "Good", "notes": "Moderately persuasive."},
                        "language_quality": {"score": 75, "band": "Good", "notes": "Good language quality."},
                        "speech_patterns": {"score": 78, "band": "Good", "notes": "Steady pace."}
                    },
                    "strengths": ["Clear articulation", "Good vocabulary"],
                    "improvement_areas": ["Grammar accuracy", "Sentence structure"],
                    "action_plan": [
                        {
                            "focus": "grammar",
                            "what_to_improve": "Grammar accuracy",
                            "why_it_matters": "To reduce grammatical errors",
                            "how_to_improve": "Use grammar workbooks or online exercises daily",
                        }
                    ],
                },
            }
        }
    }


class ErrorResponse(BaseModel):
    """Standard error response schema."""

    detail: str = Field(
        description="Error message",
    )
    error_code: str | None = Field(
        default=None,
        description="Optional error code for client handling",
    )
