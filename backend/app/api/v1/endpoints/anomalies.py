"""Anomaly detection alerts, event drilldown, and explainability endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query

from backend.app.api.v1.deps import get_repository
from backend.app.core.database import DatabaseRepository
from backend.app.models.processing import AnomalyEventRecord, PaginatedResponse, PaginationMeta
from ml.explainability.schema import ExplanationSummary

router = APIRouter(prefix="/anomalies", tags=["Anomalies & Alerts"])


@router.get("", response_model=PaginatedResponse[AnomalyEventRecord])
async def list_anomalies(
    station_id: Optional[str] = Query(None, description="Filter by station ID"),
    decision: Optional[str] = Query(None, description="Filter by hybrid decision (e.g. PROBABLE_SENSOR_ANOMALY)"),
    severity: Optional[str] = Query(None, description="Filter by severity (e.g. HIGH, CRITICAL)"),
    start_time: Optional[datetime] = Query(None, description="Start timestamp filter"),
    end_time: Optional[datetime] = Query(None, description="End timestamp filter"),
    limit: int = Query(50, ge=1, le=500, description="Items per page"),
    offset: int = Query(0, ge=0, description="Page offset"),
    repo: DatabaseRepository = Depends(get_repository),
):
    """List detected anomalies with multi-criteria filtering and pagination."""
    items, total = repo.get_anomalies(
        station_id=station_id,
        decision=decision,
        severity=severity,
        start_time=start_time,
        end_time=end_time,
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


@router.get("/{event_id}", response_model=AnomalyEventRecord)
async def get_anomaly_detail(
    event_id: str,
    repo: DatabaseRepository = Depends(get_repository),
):
    """Get single anomaly event record by its unique event ID."""
    ev = repo.get_anomaly_by_id(event_id)
    if not ev:
        raise HTTPException(status_code=404, detail=f"Anomaly event '{event_id}' not found.")
    return ev


@router.get("/{event_id}/explanation", response_model=ExplanationSummary)
async def get_anomaly_explanation(
    event_id: str,
    repo: DatabaseRepository = Depends(get_repository),
):
    """Get complete Explainability package (SHAP attributions, neighbor comparison, SOP steps)."""
    exp = repo.get_anomaly_explanation(event_id)
    if not exp:
        raise HTTPException(
            status_code=404,
            detail=f"Explanation package for anomaly event '{event_id}' not found.",
        )
    return exp
