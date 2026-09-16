"""Station metadata, live status, history, and health endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query

from backend.app.api.v1.deps import get_repository
from backend.app.core.database import DatabaseRepository
from backend.app.models.observation import WeatherObservation
from backend.app.models.processing import LiveStationSnapshot, PaginatedResponse, PaginationMeta
from ml.health.health_schema import SensorHealthSummary

router = APIRouter(prefix="/stations", tags=["Stations"])


@router.get("", response_model=List[Dict[str, Any]])
async def list_stations(
    repo: DatabaseRepository = Depends(get_repository),
):
    """List all configured Automatic Weather Stations with coordinates and status."""
    return repo.get_stations()


@router.get("/{station_id}", response_model=Dict[str, Any])
async def get_station(
    station_id: str,
    repo: DatabaseRepository = Depends(get_repository),
):
    """Get metadata for a specific station."""
    stn = repo.get_station_by_id(station_id)
    if not stn:
        raise HTTPException(status_code=404, detail=f"Station '{station_id}' not found.")
    return stn


@router.get("/{station_id}/latest", response_model=LiveStationSnapshot)
async def get_station_latest(
    station_id: str,
    repo: DatabaseRepository = Depends(get_repository),
):
    """Get real-time operational status snapshot for a station."""
    snapshot = repo.get_station_latest(station_id)
    if not snapshot:
        raise HTTPException(status_code=404, detail=f"Station '{station_id}' not found.")
    return snapshot


@router.get("/{station_id}/history", response_model=PaginatedResponse[WeatherObservation])
async def get_station_history(
    station_id: str,
    start_time: Optional[datetime] = Query(None, description="ISO start time filter"),
    end_time: Optional[datetime] = Query(None, description="ISO end time filter"),
    limit: int = Query(100, ge=1, le=1000, description="Items per page"),
    offset: int = Query(0, ge=0, description="Page offset"),
    repo: DatabaseRepository = Depends(get_repository),
):
    """Get chronological observation telemetry for a station with filters and pagination."""
    items, total = repo.get_station_history(
        station_id=station_id,
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


@router.get("/{station_id}/health", response_model=Optional[SensorHealthSummary])
async def get_station_health(
    station_id: str,
    repo: DatabaseRepository = Depends(get_repository),
):
    """Get latest continuous 0-100 Sensor Health evaluation for a station."""
    health = repo.get_station_health(station_id)
    if not health:
        raise HTTPException(status_code=404, detail=f"No health records available for station '{station_id}'.")
    return health
