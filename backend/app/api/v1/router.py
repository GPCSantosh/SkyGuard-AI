"""FastAPI API v1 Router Registration."""

from __future__ import annotations

from fastapi import APIRouter

from backend.app.api.v1.endpoints.anomalies import router as anomalies_router
from backend.app.api.v1.endpoints.observations import router as observations_router
from backend.app.api.v1.endpoints.replay import router as replay_router
from backend.app.api.v1.endpoints.stations import router as stations_router
from backend.app.api.v1.endpoints.system import router as system_router

router = APIRouter()

# Register sub-routers
router.include_router(stations_router)
router.include_router(anomalies_router)
router.include_router(observations_router)
router.include_router(system_router)
router.include_router(replay_router)


@router.get("/health", tags=["Health"])
async def health_check():
    """Basic service liveness probe."""
    return {
        "status": "healthy",
        "service": "skyguard-ai-backend",
        "version": "1.0.0",
    }
