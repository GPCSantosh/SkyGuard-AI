"""Service health and system status endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from backend.app.api.v1.deps import get_repository
from backend.app.core.database import DatabaseRepository
from backend.app.models.processing import SystemHealthStatus

router = APIRouter(prefix="/system", tags=["System Observability"])


@router.get("/health", response_model=SystemHealthStatus)
async def get_system_health(
    repo: DatabaseRepository = Depends(get_repository),
):
    """Get end-to-end service status of all core subsystems (database, model, pipeline, replay)."""
    return repo.get_system_health()
