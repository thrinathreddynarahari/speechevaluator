"""Evaluation API endpoints."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.auth.auth import token_required
from config.database import get_db
from config.settings import settings
from repositories.evaluation_repository import EvaluationRepository
from schemas.evaluation import EvaluationResponse
from services.elevenlabs_service import ElevenLabsService
from services.report_service import ReportService

logger = logging.getLogger(__name__)

router = APIRouter()

# Allowed content types for audio/video files
ALLOWED_CONTENT_TYPES = {
    "audio/mpeg",
    "audio/mp3",
    "audio/wav",
    "audio/wave",
    "audio/x-wav",
    "audio/webm",
    "audio/ogg",
    "audio/flac",
    "audio/m4a",
    "audio/x-m4a",
    "audio/mp4",
    "video/mp4",
    "video/webm",
    "video/ogg",
    "video/quicktime",
}


def validate_upload_file(file: UploadFile) -> None:
    """Validate the uploaded file.

    Args:
        file: The uploaded file to validate.

    Raises:
        HTTPException: 422 if file is invalid.
    """
    # Check if file is present
    if not file or not file.filename:
        raise HTTPException(
            status_code=422,
            detail="No file provided",
        )

    # Check content type
    content_type = file.content_type or ""
    if not (
        content_type.startswith("audio/")
        or content_type.startswith("video/")
        or content_type in ALLOWED_CONTENT_TYPES
    ):
        raise HTTPException(
            status_code=422,
            detail=f"Invalid file type: {content_type}. Must be audio or video.",
        )

    # Check file size (read and reset)
    file.file.seek(0, 2)  # Seek to end
    file_size = file.file.tell()
    file.file.seek(0)  # Reset to beginning

    if file_size == 0:
        raise HTTPException(
            status_code=422,
            detail="File is empty",
        )

    if file_size > settings.max_upload_bytes:
        raise HTTPException(
            status_code=422,
            detail=f"File too large. Maximum size: {settings.max_upload_mb}MB",
        )


@router.post(
    "/report",
    response_model=EvaluationResponse,
    summary="Generate English Evaluation Report",
    description="""
    Upload an audio file to get an English communication evaluation report.
    
    The endpoint will:
    1. Transcribe the audio using ElevenLabs Speech-to-Text
    2. Create or update an evaluation record for the authenticated employee
    3. Generate a detailed evaluation report using Claude AI
    4. Store and return the evaluation report
    """,
    responses={
        401: {"description": "Authentication failed"},
        422: {"description": "Invalid file or validation error"},
        502: {"description": "External service (ElevenLabs/Claude) failure"},
        500: {"description": "Internal server error"},
    },
)
async def create_evaluation_report(
    file: Annotated[UploadFile, File(description="Audio or video file to evaluate")],
    auth_payload: Annotated[dict, Depends(token_required)],
    db: Annotated[Session, Depends(get_db)],
    language_code: Annotated[
        str,
        Form(description="Language code (ISO 639-3)"),
    ] = "eng",
    diarize: Annotated[
        bool,
        Form(description="Enable speaker diarization"),
    ] = True,
    tag_audio_events: Annotated[
        bool,
        Form(description="Tag audio events"),
    ] = True,
) -> EvaluationResponse:
    """Generate an English evaluation report from an uploaded audio file.

    Args:
        file: Audio or video file to transcribe and evaluate.
        auth_payload: Authenticated user information from token.
        db: Database session.
        language_code: ISO 639-3 language code for transcription.
        diarize: Whether to enable speaker diarization.
        tag_audio_events: Whether to tag audio events.

    Returns:
        EvaluationResponse containing evaluation ID, report ID, transcription, and report.
    """
    employee_id = auth_payload["user_id"]
    logger.info(
        "Starting evaluation for employee_id=%s, file=%s",
        employee_id,
        file.filename,
    )

    # Validate the uploaded file
    validate_upload_file(file)

    try:
        # Step 1: Transcribe audio using ElevenLabs
        elevenlabs_service = ElevenLabsService()
        transcription = await elevenlabs_service.transcribe(
            audio_file=file.file,
            filename=file.filename or "audio",
            content_type=file.content_type or "audio/mpeg",
            language_code=language_code,
            diarize=diarize,
            tag_audio_events=tag_audio_events,
        )

        # Step 2: Get or create evaluation record (upsert)
        repo = EvaluationRepository(db)
        evaluation, was_created = repo.get_or_create_evaluation(
            employee_id=employee_id,
            feedback=transcription,
            user_id=employee_id,
        )
        logger.info(
            "Evaluation record: id=%s, created=%s",
            evaluation.id,
            was_created,
        )

        # Step 3: Generate evaluation report using Claude
        report_service = ReportService()
        report_data = await report_service.generate_report(transcription)

        # Step 4: Store the report
        report_record = repo.create_evaluation_report(
            evaluation_id=evaluation.id,
            report=report_data.model_dump(),
            created_by=employee_id,
        )

        # Commit the transaction
        db.commit()

        logger.info(
            "Evaluation complete: evaluation_id=%s, report_id=%s",
            evaluation.id,
            report_record.id,
        )

        return EvaluationResponse(
            evaluation_id=evaluation.id,
            report_id=report_record.id,
            transcription=transcription,
            report=report_data,
        )

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.exception("Unexpected error during evaluation")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}",
        ) from e
