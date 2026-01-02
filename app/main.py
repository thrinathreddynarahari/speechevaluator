"""FastAPI application entry point.

English Evaluation Service - An internal service for evaluating English
communication skills from audio recordings using ElevenLabs transcription
and Claude AI analysis.
"""

import logging
import sys

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers.v1 import router as v1_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)

logger = logging.getLogger(__name__)

# Create FastAPI application
app = FastAPI(
    title="English Evaluation Service",
    description="""
    Internal service for evaluating English communication skills.
    
    ## Features
    
    - Audio transcription via ElevenLabs Speech-to-Text
    - AI-powered evaluation using Claude (Anthropic)
    - Detailed scoring across multiple dimensions:
        - Fluency
        - Grammar
        - Pronunciation
        - Vocabulary
        - Structure
    - Actionable improvement recommendations
    
    ## Authentication
    
    All endpoints require Azure AD Bearer token authentication.
    Include the token in the Authorization header:
    ```
    Authorization: Bearer <token>
    ```
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get(
    "/health",
    tags=["Health"],
    summary="Health Check",
    description="Check if the service is running.",
)
async def health_check() -> dict:
    """Return service health status."""
    return {
        "status": "healthy",
        "service": "english-evaluation-service",
        "version": "1.0.0",
    }


# Include API routers
app.include_router(
    v1_router,
    prefix="/api",
)

logger.info("English Evaluation Service initialized")
