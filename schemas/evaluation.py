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


class CategoryScore(BaseModel):
    """Score and notes for a specific evaluation category."""

    score: int = Field(
        ge=0,
        le=100,
        description="Score from 0 to 100",
    )
    notes: str = Field(
        description="Detailed notes about this category",
    )


class ActionPlanItem(BaseModel):
    """An individual action item for improvement."""

    item: str = Field(
        description="The action item description",
    )
    why: str = Field(
        description="Why this action is important",
    )
    how: str = Field(
        description="How to implement this action",
    )


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
    summary: str = Field(
        description="Brief summary of the evaluation",
    )
    strengths: list[str] = Field(
        min_length=1,
        max_length=10,
        description="List of identified strengths (1-10 items)",
    )
    improvements: list[str] = Field(
        min_length=1,
        max_length=10,
        description="List of areas for improvement (1-10 items)",
    )
    fluency: CategoryScore = Field(
        description="Fluency score and notes",
    )
    grammar: CategoryScore = Field(
        description="Grammar score and notes",
    )
    pronunciation: CategoryScore = Field(
        description="Pronunciation score and notes",
    )
    vocabulary: CategoryScore = Field(
        description="Vocabulary usage score and notes",
    )
    structure: CategoryScore = Field(
        description="Communication structure score and notes",
    )
    action_plan: list[ActionPlanItem] = Field(
        min_length=1,
        max_length=7,
        description="Actionable improvement plan (1-7 items)",
    )

    @field_validator("strengths", "improvements")
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
                    "summary": "Good communication skills with room for improvement in grammar.",
                    "strengths": ["Clear articulation", "Good vocabulary"],
                    "improvements": ["Grammar accuracy", "Sentence structure"],
                    "fluency": {"score": 80, "notes": "Speaks smoothly with few hesitations."},
                    "grammar": {"score": 65, "notes": "Some grammatical errors observed."},
                    "pronunciation": {"score": 78, "notes": "Clear pronunciation overall."},
                    "vocabulary": {"score": 82, "notes": "Uses varied vocabulary."},
                    "structure": {"score": 70, "notes": "Could improve logical flow."},
                    "action_plan": [
                        {
                            "item": "Practice grammar exercises",
                            "why": "To reduce grammatical errors",
                            "how": "Use grammar workbooks or online exercises daily",
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
