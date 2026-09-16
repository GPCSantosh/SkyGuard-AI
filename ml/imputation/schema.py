"""Schemas and data models for SkyGuard AI Data Imputation and Correction Recommendation Layer."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, ConfigDict, Field


class ImputationStatus(str, Enum):
    """Status of a missing data imputation attempt."""
    IMPUTED = "IMPUTED"
    NOT_IMPUTABLE = "NOT_IMPUTABLE"


class RecommendationStatus(str, Enum):
    """Operational status of a suspicious observation correction recommendation."""
    NO_CORRECTION_RECOMMENDED = "NO_CORRECTION_RECOMMENDED"
    REVIEW_RECOMMENDED = "REVIEW_RECOMMENDED"
    CORRECTION_CANDIDATE = "CORRECTION_CANDIDATE"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


class EstimationMethod(str, Enum):
    """Mathematical and algorithmic methods used for estimation."""
    CAUSAL_TEMPORAL_INTERPOLATION = "CAUSAL_TEMPORAL_INTERPOLATION"
    RETROSPECTIVE_INTERPOLATION = "RETROSPECTIVE_INTERPOLATION"
    SPATIAL_IDW_CONSENSUS = "SPATIAL_IDW_CONSENSUS"
    NEIGHBOR_WEIGHTED_MEDIAN = "NEIGHBOR_WEIGHTED_MEDIAN"
    ROLLING_BASELINE = "ROLLING_BASELINE"
    COMBINED_TEMPORAL_SPATIAL = "COMBINED_TEMPORAL_SPATIAL"
    NO_ESTIMATE = "NO_ESTIMATE"


class MethodQuality(str, Enum):
    """Qualitative tier of estimation reliability based on evidence density."""
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    POOR = "POOR"


class UncertaintyEstimate(BaseModel):
    """Explicit uncertainty quantification for an estimated meteorological value."""
    model_config = ConfigDict(frozen=True)

    estimate_range: Tuple[float, float] = Field(
        ...,
        description="Plausible range [min_bound, max_bound] for the estimated value."
    )
    standard_error: Optional[float] = Field(
        None,
        ge=0.0,
        description="Standard error or estimated residual standard deviation."
    )
    absolute_deviation: Optional[float] = Field(
        None,
        ge=0.0,
        description="Absolute deviation / departure between estimate and baseline."
    )
    supporting_neighbor_count: int = Field(
        0,
        ge=0,
        description="Number of contemporaneous active neighbors supporting the estimate."
    )
    method_quality: MethodQuality = Field(
        MethodQuality.MEDIUM,
        description="Overall method quality tier reflecting data density and stability."
    )
    confidence_index: float = Field(
        0.5,
        ge=0.0,
        le=1.0,
        description="Composite empirical certainty index (not an uncalibrated probability)."
    )
    notes: List[str] = Field(
        default_factory=list,
        description="Descriptive factors contributing to the uncertainty calculation."
    )


class ImputationRecord(BaseModel):
    """Strictly separated non-destructive record for an imputed missing value."""
    model_config = ConfigDict(frozen=True)

    station_id: str = Field(..., description="Target AWS station identifier.")
    timestamp: str = Field(..., description="ISO 8601 timestamp of the missing record.")
    target_variable: str = Field(..., description="Meteorological parameter (e.g. 'temperature_c').")
    original_value: Optional[float] = Field(None, description="Raw incoming value (None for missing data).")
    imputed_value: Optional[float] = Field(None, description="Model-derived imputed value if successful.")
    status: ImputationStatus = Field(..., description="IMPUTED or NOT_IMPUTABLE.")
    method: EstimationMethod = Field(..., description="Imputation algorithm applied.")
    reason: str = Field(..., description="Detailed deterministic rationale for the status.")
    gap_duration_minutes: float = Field(0.0, ge=0.0, description="Duration in minutes of the data gap.")
    consecutive_missing_steps: int = Field(0, ge=0, description="Consecutive missing steps evaluated.")
    uncertainty: Optional[UncertaintyEstimate] = Field(None, description="Uncertainty quantification of imputed value.")
    is_causal: bool = Field(True, description="True if only historical telemetry was utilized (zero lookahead).")
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="UTC creation timestamp."
    )


class CorrectionAuditMetadata(BaseModel):
    """Complete provenance and model tracking for correction recommendations."""
    model_config = ConfigDict(frozen=True)

    imputation_engine_version: str = Field("imputation_v1.0.0", description="Version of imputation layer.")
    decision_engine_version: str = Field("hybrid_v1.0.0", description="Version of hybrid decision engine.")
    explanation_engine_version: str = Field("xai_v1.0.0", description="Version of explainability engine.")
    health_engine_version: str = Field("health_v1.0.0", description="Version of sensor health engine.")
    spatial_engine_version: str = Field("spatial_v1.0.0", description="Version of spatial topology engine.")
    is_causal_mode: bool = Field(True, description="Causality guarantee flag.")
    generated_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="UTC timestamp of generation."
    )


class CorrectionRecommendation(BaseModel):
    """Strictly separated non-destructive correction recommendation for a suspicious observation."""
    model_config = ConfigDict(frozen=True)

    observation_id: str = Field(..., description="Unique hash/identifier of target observation.")
    station_id: str = Field(..., description="Target AWS station identifier.")
    timestamp: str = Field(..., description="ISO 8601 timestamp of the observation.")
    target_variable: str = Field(..., description="Meteorological parameter evaluated (e.g. 'temperature_c').")
    observed_value: float = Field(..., description="Raw observed value from sensor (remains immutable).")
    recommended_value: Optional[float] = Field(None, description="Model-derived recommended estimate.")
    status: RecommendationStatus = Field(..., description="Actionable recommendation tier.")
    method: EstimationMethod = Field(..., description="Algorithm used to derive the recommended estimate.")
    
    # Evidence & Decision Context
    decision_type: str = Field(..., description="Upstream hybrid decision (e.g. PROBABLE_SENSOR_ANOMALY).")
    reason_codes: List[str] = Field(default_factory=list, description="Reason codes from upstream decision engine.")
    supporting_evidence: List[str] = Field(default_factory=list, description="Direct and contextual evidence items.")
    
    # Uncertainty & Multi-Variable Physics
    uncertainty: Optional[UncertaintyEstimate] = Field(None, description="Uncertainty quantification of recommendation.")
    multivariate_consistent: bool = Field(True, description="True if recommended value satisfies joint physical laws.")
    
    # Station Reliability Context
    station_health_score: Optional[float] = Field(None, description="Upstream Sensor Health Index (0-100).")
    station_health_band: Optional[str] = Field(None, description="Upstream Sensor Health Status Band.")
    
    # Operator Guidance & Provenance
    operator_summary: str = Field(..., description="Scientific, operator-facing natural language explanation.")
    audit_metadata: CorrectionAuditMetadata = Field(default_factory=CorrectionAuditMetadata)
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="UTC creation timestamp."
    )


class MultivariateCorrectionBundle(BaseModel):
    """Bundle of simultaneous candidate corrections for a station timestep with joint validation."""
    model_config = ConfigDict(frozen=True)

    station_id: str = Field(..., description="Target AWS station identifier.")
    timestamp: str = Field(..., description="ISO 8601 timestamp.")
    recommendations: Dict[str, CorrectionRecommendation] = Field(
        default_factory=dict,
        description="Mapping from variable name to CorrectionRecommendation."
    )
    is_jointly_consistent: bool = Field(True, description="True if all recommended values together satisfy physics.")
    inconsistency_reasons: List[str] = Field(default_factory=list, description="Notes on any joint physical violations.")
