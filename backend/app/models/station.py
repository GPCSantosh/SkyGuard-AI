"""Station metadata and network topology schemas."""

from __future__ import annotations

from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class StationStatus(str, Enum):
    """Operational status of a weather station."""
    ACTIVE = "ACTIVE"
    DEGRADED = "DEGRADED"
    MAINTENANCE = "MAINTENANCE"
    OFFLINE = "OFFLINE"
    DECOMMISSIONED = "DECOMMISSIONED"


class GeoLocation(BaseModel):
    """Geodetic location model."""
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)
    elevation: Optional[float] = Field(default=None, ge=-500.0, le=9000.0)


class StationMetadata(BaseModel):
    """Metadata representing an Automatic Weather Station."""
    model_config = ConfigDict(str_strip_whitespace=True)

    station_id: str = Field(..., min_length=1, max_length=64)
    name: str = Field(..., min_length=1, max_length=128)
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)
    elevation: Optional[float] = Field(default=None, ge=-500.0, le=9000.0)
    state: Optional[str] = Field(default=None, max_length=64)
    sampling_interval_seconds: int = Field(default=300, ge=1)
    status: StationStatus = StationStatus.ACTIVE
    installed_sensors: List[str] = Field(
        default_factory=lambda: ["TEMPERATURE", "PRESSURE", "HUMIDITY"]
    )
