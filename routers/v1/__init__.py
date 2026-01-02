"""API v1 router aggregation."""

from fastapi import APIRouter

from routers.v1.evaluation import router as evaluation_router

# Create v1 API router
router = APIRouter(prefix="/v1")

# Include sub-routers
router.include_router(
    evaluation_router,
    prefix="/evaluations",
    tags=["Evaluations"],
)
