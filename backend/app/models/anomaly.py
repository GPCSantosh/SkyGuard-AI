"""Anomaly taxonomy and diagnostic data schemas for SkyGuard AI."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class AnomalyCategory(str, Enum):
    """15-Category Operational Anomaly Taxonomy."""
    NORMAL = "NORMAL"
    SPIKE = "SPIKE"
    SMALL_SPIKE = "SMALL_SPIKE"
    DRIFT = "DRIFT"
    OFFSET = "OFFSET"
    FROZEN_SENSOR = "FROZEN_SENSOR"
    INTERMITTENT_SENSOR = "INTERMITTENT_SENSOR"
    MISSING_DATA = "MISSING_DATA"
    COMMUNICATION_ERROR = "COMMUNICATION_ERROR"
    DUPLICATE_DATA = "DUPLICATE_DATA"
    OUT_OF_ORDER_DATA = "OUT_OF_ORDER_DATA"
    MULTIVARIATE_INCONSISTENCY = "MULTIVARIATE_INCONSISTENCY"
    POSSIBLE_GENUINE_EVENT = "POSSIBLE_GENUINE_EVENT"
    UNCERTAIN = "UNCERTAIN"
    MULTI_FAULT = "MULTI_FAULT"


class AnomalySeverity(str, Enum):
    """Operational alert severity level."""
    NOMINAL = "NOMINAL"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class AnomalyRecord(BaseModel):
    """Record of a detected anomaly event or quality classification."""
    model_config = ConfigDict(frozen=True)

    anomaly_id: Optional[str] = None
    station_id: str
    timestamp: datetime
    parameter: str  # 'temperature' | 'pressure' | 'humidity' | 'multivariate'
    
    category: AnomalyCategory
    severity: AnomalySeverity
    
    # Anomaly score (distance / loss metric, not a raw probability)
    anomaly_score: float = Field(
        ge=0.0,
        description="Normalized anomaly score metric (0.0 = nominal, 1.0 = maximum deviation)"
    )
    
    # Confidence in classification
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Confidence score based on rule consensus and spatial agreement"
    )

    is_spatial_corroborated: bool = False
    contributing_features: List[str] = Field(default_factory=list)
    explanation: Optional[str] = None
    model_version: str = "rule_baseline_v0.1.0"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = Field(default_factory=dict)
