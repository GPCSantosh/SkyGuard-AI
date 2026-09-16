"""Sensor health status and metric schemas."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Dict, Optional
from pydantic import BaseModel, ConfigDict, Field


class HealthTier(str, Enum):
    """Overall sensor/station operational health grade."""
    HEALTHY = "HEALTHY"      # Score 85 - 100
    DEGRADED = "DEGRADED"    # Score 60 - 84
    CRITICAL = "CRITICAL"    # Score 0 - 59
    OFFLINE = "OFFLINE"      # Missing consecutive data


class SensorHealthStatus(BaseModel):
    """Health evaluation index for a station and its individual sensors."""
    model_config = ConfigDict(frozen=True)

    station_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Overall health score on a 0 - 100 scale
    overall_health_score: float = Field(
        ge=0.0,
        le=100.0,
        description="Composite health index (0 to 100)"
    )
    health_tier: HealthTier
    
    # Individual sensor scores
    temperature_health: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    pressure_health: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    humidity_health: Optional[float] = Field(default=None, ge=0.0, le=100.0)

    # Diagnostic counters (past 24h)
    anomaly_count_24h: int = Field(default=0, ge=0)
    missing_intervals_24h: int = Field(default=0, ge=0)
    data_completeness_pct_24h: float = Field(default=100.0, ge=0.0, le=100.0)
    drift_detected: bool = False
    frozen_detected: bool = False
