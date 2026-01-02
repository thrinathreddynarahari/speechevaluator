"""ElevenLabs Speech-to-Text service using direct REST API."""

import logging
from typing import BinaryIO

import httpx
from fastapi import HTTPException

from config.settings import settings

logger = logging.getLogger(__name__)

# ElevenLabs API endpoint
ELEVENLABS_STT_URL = "https://api.elevenlabs.io/v1/speech-to-text"


class ElevenLabsService:
    """Service for transcribing audio using ElevenLabs Speech-to-Text API."""

    def __init__(self):
        """Initialize the service with API configuration."""
        self.api_key = settings.elevenlabs_api_key
        self.model_id = settings.elevenlabs_model_id
        self.timeout = httpx.Timeout(120.0, connect=10.0)

    async def transcribe(
        self,
        audio_file: BinaryIO,
        filename: str,
        content_type: str,
        language_code: str = "eng",
        diarize: bool = True,
        tag_audio_events: bool = True,
    ) -> str:
        """Transcribe audio file to text using ElevenLabs API.

        Args:
            audio_file: Binary file-like object containing audio data.
            filename: Original filename for the upload.
            content_type: MIME type of the audio file.
            language_code: ISO 639-3 language code (default: "eng").
            diarize: Enable speaker diarization.
            tag_audio_events: Tag audio events like laughter, applause.

        Returns:
            Transcription text from the audio.

        Raises:
            HTTPException: 502 if ElevenLabs API fails.
        """
        logger.info(
            "Starting transcription: filename=%s, language=%s, diarize=%s",
            filename,
            language_code,
            diarize,
        )

        headers = {
            "xi-api-key": self.api_key,
        }

        # Read file content
        audio_content = audio_file.read()
        if hasattr(audio_file, "seek"):
            audio_file.seek(0)

        # Prepare multipart form data
        files = {
            "file": (filename, audio_content, content_type),
        }

        data = {
            "model_id": self.model_id,
            "language_code": language_code,
            "diarize": str(diarize).lower(),
            "tag_audio_events": str(tag_audio_events).lower(),
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    ELEVENLABS_STT_URL,
                    headers=headers,
                    files=files,
                    data=data,
                )

                if response.status_code != 200:
                    logger.error(
                        "ElevenLabs API error: status=%d, response=%s",
                        response.status_code,
                        response.text[:500],
                    )
                    raise HTTPException(
                        status_code=502,
                        detail=f"ElevenLabs transcription failed: {response.status_code}",
                    )

                result = response.json()
                transcription = result.get("text", "")

                if not transcription:
                    logger.warning("ElevenLabs returned empty transcription")
                    raise HTTPException(
                        status_code=502,
                        detail="ElevenLabs returned empty transcription",
                    )

                logger.info(
                    "Transcription completed: length=%d chars",
                    len(transcription),
                )
                return transcription

        except httpx.TimeoutException as e:
            logger.error("ElevenLabs API timeout: %s", str(e))
            raise HTTPException(
                status_code=502,
                detail="ElevenLabs API request timed out",
            ) from e
        except httpx.RequestError as e:
            logger.error("ElevenLabs API request error: %s", str(e))
            raise HTTPException(
                status_code=502,
                detail=f"ElevenLabs API request failed: {str(e)}",
            ) from e
        except HTTPException:
            raise
        except Exception as e:
            logger.exception("Unexpected error during transcription")
            raise HTTPException(
                status_code=502,
                detail=f"Transcription failed: {str(e)}",
            ) from e
