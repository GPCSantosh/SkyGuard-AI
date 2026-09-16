"""Advisory correction recommendation endpoints for human-in-the-loop review."""

from __future__ import annotations

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query

from backend.app.api.v1.deps import get_repository
from backend.app.core.database import DatabaseRepository
from backend.app.models.processing import PaginatedResponse, PaginationMeta
from ml.imputation.schema import CorrectionRecommendation

router = APIRouter(prefix="/corrections", tags=["Correction Review"])


@router.get("", response_model=PaginatedResponse[CorrectionRecommendation])
async def list_corrections(
    station_id: Optional[str] = Query(None, description="Filter by station ID"),
    status: Optional[str] = Query(None, description="Filter by recommendation status (e.g. REVIEW_RECOMMENDED)"),
    target_variable: Optional[str] = Query(None, description="Filter by variable (e.g. temperature_c)"),
    limit: int = Query(50, ge=1, le=500, description="Items per page"),
    offset: int = Query(0, ge=0, description="Page offset"),
    repo: DatabaseRepository = Depends(get_repository),
):
    """List advisory correction recommendations with multi-field filtering and pagination."""
    items, total = repo.get_corrections(
        station_id=station_id,
        status=status,
        target_variable=target_variable,
        limit=limit,
        offset=offset,
    )
    return PaginatedResponse(
        items=items,
        pagination=PaginationMeta(
            total_count=total,
            limit=limit,
            offset=offset,
            has_more=(offset + limit) < total,
        ),
    )


@router.get("/{observation_id}", response_model=CorrectionRecommendation)
async def get_correction_detail(
    observation_id: str,
    repo: DatabaseRepository = Depends(get_repository),
):
    """Get single advisory correction recommendation record by its observation ID."""
    corr = repo.get_correction_by_id(observation_id)
    if not corr:
        raise HTTPException(status_code=404, detail=f"Correction recommendation '{observation_id}' not found.")
    return corr
