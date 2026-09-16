"""Schemas and data models for the SkyGuard Hybrid Decision Engine."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from ml.spatial.schema import SpatialContextCategory


class HybridDecisionType(str, Enum):
    """Operational hybrid classification decisions."""
    NORMAL = "NORMAL"
    POSSIBLE_GENUINE_EVENT = "POSSIBLE_GENUINE_EVENT"
    PROBABLE_SENSOR_ANOMALY = "PROBABLE_SENSOR_ANOMALY"
    PROBABLE_DATA_QUALITY_ISSUE = "PROBABLE_DATA_QUALITY_ISSUE"
    UNCERTAIN = "UNCERTAIN"


class DecisionSeverity(str, Enum):
    """Operational alert severity level."""
    INFO = "INFO"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class EvidenceState(str, Enum):
    """Standardized alignment of a specific subsystem evidence source relative to a hypothesis."""
    SUPPORTS = "SUPPORTS"
    CONTRADICTS = "CONTRADICTS"
    NEUTRAL = "NEUTRAL"
    UNAVAILABLE = "UNAVAILABLE"


class DecisionReasonCode(str, Enum):
    """Stable, machine-readable reason codes explaining decision triggers."""
    NOMINAL_OBSERVATION = "NOMINAL_OBSERVATION"
    DATA_GAP = "DATA_GAP"
    DUPLICATE_TIMESTAMP = "DUPLICATE_TIMESTAMP"
    OUT_OF_ORDER_TIMESTAMP = "OUT_OF_ORDER_TIMESTAMP"
    MISSING_REQUIRED_VARIABLES = "MISSING_REQUIRED_VARIABLES"
    OUT_OF_RANGE_PHYSICAL = "OUT_OF_RANGE_PHYSICAL"
    PERSISTENT_VALUE = "PERSISTENT_VALUE"
    RAPID_RATE_OF_CHANGE = "RAPID_RATE_OF_CHANGE"
    MULTIVARIATE_DEVIATION = "MULTIVARIATE_DEVIATION"
    ML_HIGH_ANOMALY_SCORE = "ML_HIGH_ANOMALY_SCORE"
    ML_MODERATE_ANOMALY_SCORE = "ML_MODERATE_ANOMALY_SCORE"
    LOCAL_SPATIAL_ISOLATION = "LOCAL_SPATIAL_ISOLATION"
    REGIONAL_SPATIAL_AGREEMENT = "REGIONAL_SPATIAL_AGREEMENT"
    LOCAL_CLUSTER_AGREEMENT = "LOCAL_CLUSTER_AGREEMENT"
    INSUFFICIENT_SPATIAL_CONTEXT = "INSUFFICIENT_SPATIAL_CONTEXT"
    CONFLICTING_EVIDENCE = "CONFLICTING_EVIDENCE"
    MIXED_REGIONAL_EVENT_WITH_LOCAL_EXCESS = "MIXED_REGIONAL_EVENT_WITH_LOCAL_EXCESS"


class DataQualityEvidence(BaseModel):
    """Evidence derived from telemetry integrity, schemas, and communication checks."""
    model_config = ConfigDict(frozen=True)

    quality_status: str = Field("VALID", description="High-level ingestion status (VALID, REJECTED, GAP, DUPLICATE).")
    missing_fields: List[str] = Field(default_factory=list, description="List of missing required meteorological fields.")
    communication_gap_minutes: Optional[float] = Field(None, ge=0.0, description="Elapsed time since previous packet.")
    is_duplicate: bool = Field(False, description="True if timestamp/payload is duplicate.")
    is_out_of_order: bool = Field(False, description="True if packet arrived out of chronological sequence.")
    is_physical_out_of_bounds: bool = Field(False, description="True if raw value exceeds planetary limits.")
    evidence_state: EvidenceState = Field(EvidenceState.NEUTRAL, description="Evidence alignment for data defect.")


class MLAnomalyEvidence(BaseModel):
    """Evidence derived from unsupervised/semi-supervised ML models (e.g. Isolation Forest)."""
    model_config = ConfigDict(frozen=True)

    raw_model_score: Optional[float] = Field(None, description="Raw model decision function or distance metric.")
    normalized_anomaly_score: float = Field(0.0, ge=0.0, le=1.0, description="Normalized score metric in [0, 1]. Not a probability.")
    ml_is_anomaly: bool = Field(False, description="True if score exceeds validation calibrated threshold.")
    model_version: str = Field("isolation_forest_v1", description="Model architecture identifier.")
    evidence_state: EvidenceState = Field(EvidenceState.NEUTRAL, description="Evidence alignment for anomaly.")


class TemporalEvidence(BaseModel):
    """Evidence derived from rate-of-change, sliding window variance, and persistence counters."""
    model_config = ConfigDict(frozen=True)

    temp_rate_per_min: Optional[float] = Field(None, description="Temperature rate of change (°C/min).")
    rh_rate_per_min: Optional[float] = Field(None, description="RH rate of change (%/min).")
    slp_rate_per_min: Optional[float] = Field(None, description="SLP rate of change (hPa/min).")
    consecutive_unchanged_count: int = Field(0, ge=0, description="Consecutive unchanged observation count.")
    flatline_duration_minutes: float = Field(0.0, ge=0.0, description="Duration in minutes of unchanged readings.")
    baseline_deviation_zscore: Optional[float] = Field(None, description="Local 1h sliding window Z-score residual.")
    is_rate_abnormal: bool = Field(False, description="True if rate of change exceeds physical step threshold.")
    is_flatline: bool = Field(False, description="True if sensor is stuck for prolonged period.")
    evidence_state: EvidenceState = Field(EvidenceState.NEUTRAL, description="Evidence alignment for temporal anomaly.")


class MultivariateEvidence(BaseModel):
    """Evidence derived from physical relationships between Temperature, Humidity, and Pressure."""
    model_config = ConfigDict(frozen=True)

    dew_point_spread_c: Optional[float] = Field(None, description="T - Td spread (°C).")
    temp_rh_inconsistent: bool = Field(False, description="True if T and RH violate thermodynamic consistency.")
    joint_standardized_divergence: Optional[float] = Field(None, description="Joint multi-parameter divergence norm.")
    is_multivariate_abnormal: bool = Field(False, description="True if joint physical consistency check fails.")
    evidence_state: EvidenceState = Field(EvidenceState.NEUTRAL, description="Evidence alignment for physical contradiction.")


class SpatialEvidence(BaseModel):
    """Evidence derived from Phase 4 Geodesic Spatial & Synoptic Context Engine."""
    model_config = ConfigDict(frozen=True)

    configured_neighbor_count: int = Field(0, ge=0, description="Configured stations within spatial radius.")
    valid_neighbor_count: int = Field(0, ge=0, description="Active neighbors within temporal window.")
    context_category: SpatialContextCategory = Field(
        SpatialContextCategory.INSUFFICIENT_CONTEXT,
        description="High-level spatial context category."
    )
    temp_consensus_fraction: float = Field(0.0, ge=0.0, le=1.0, description="Fraction of neighbors agreeing in value.")
    temp_target_minus_mean: Optional[float] = Field(None, description="Target temperature minus neighbor mean (°C).")
    temp_target_zscore: Optional[float] = Field(None, description="Target Z-score relative to neighbor distribution.")
    is_spatially_isolated: bool = Field(False, description="True if target deviates while neighbors are stable.")
    is_regionally_corroborated: bool = Field(False, description="True if neighbors share the same deviation/trend.")
    evidence_state: EvidenceState = Field(EvidenceState.NEUTRAL, description="Evidence alignment for spatial corroboration.")


class ObservationEvidence(BaseModel):
    """Comprehensive, unflattened multi-subsystem evidence container for a weather observation."""
    model_config = ConfigDict(frozen=True)

    station_id: str = Field(..., description="Target station identifier.")
    timestamp: str = Field(..., description="ISO 8601 observation timestamp.")
    
    # Subsystem evidence packages
    data_quality: DataQualityEvidence = Field(default_factory=DataQualityEvidence)
    ml_anomaly: MLAnomalyEvidence = Field(default_factory=MLAnomalyEvidence)
    temporal: TemporalEvidence = Field(default_factory=TemporalEvidence)
    multivariate: MultivariateEvidence = Field(default_factory=MultivariateEvidence)
    spatial: SpatialEvidence = Field(default_factory=SpatialEvidence)


class DecisionExplanation(BaseModel):
    """Structured, human-readable and machine-traceable explanation of decision rationale."""
    model_config = ConfigDict(frozen=True)

    summary: str = Field(..., description="Concise multi-sentence explanation of decision.")
    reason_codes: List[DecisionReasonCode] = Field(default_factory=list, description="Triggered reason codes.")
    supporting_evidence: List[str] = Field(default_factory=list, description="Subsystems supporting the decision.")
    contradicting_evidence: List[str] = Field(default_factory=list, description="Subsystems contradicting or ruling out alternatives.")
    unavailable_evidence: List[str] = Field(default_factory=list, description="Subsystems with missing or insufficient telemetry.")


class RecommendedCorrection(BaseModel):
    """Optional placeholder structure for future Phase 6 non-destructive value estimation."""
    model_config = ConfigDict(frozen=True)

    estimated_value: Optional[float] = Field(None, description="Estimated corrected parameter value.")
    target_variable: Optional[str] = Field(None, description="Parameter requiring correction.")
    method: str = Field("IDW_SPATIAL_INTERPOLATION", description="Recommended estimation algorithm.")
    supporting_observations_count: int = Field(0, description="Count of observations used in estimate.")
    confidence_description: str = Field("Pending Phase 6 Imputer", description="Qualitative estimate confidence.")


class HybridDecision(BaseModel):
    """Complete traceable hybrid decision generated for an observation."""
    model_config = ConfigDict(frozen=True)

    station_id: str = Field(..., description="Target AWS station identifier.")
    timestamp: str = Field(..., description="ISO 8601 observation timestamp.")
    decision: HybridDecisionType = Field(..., description="High-level operational decision classification.")
    severity: DecisionSeverity = Field(..., description="Operational urgency severity.")
    reason_codes: List[DecisionReasonCode] = Field(default_factory=list, description="Stable reason code identifiers.")
    supporting_metrics: Dict[str, Any] = Field(default_factory=dict, description="Key numerical metrics backing decision.")
    recommended_action: str = Field(..., description="Standard operating procedure (SOP) guidance text.")
    explanation: DecisionExplanation = Field(..., description="Structured explanation container.")
    evidence: ObservationEvidence = Field(..., description="Original multi-source evidence package.")
    recommended_correction: Optional[RecommendedCorrection] = Field(None, description="Optional placeholder for future imputation.")
