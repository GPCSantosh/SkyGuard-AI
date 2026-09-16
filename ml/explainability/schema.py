"""Schemas and data models for SkyGuard AI Explainability and Investigation Layer."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from ml.decision.schema import (
    DataQualityEvidence,
    DecisionReasonCode,
    DecisionSeverity,
    EvidenceState,
    HybridDecisionType,
    MultivariateEvidence,
    SpatialEvidence,
    TemporalEvidence,
)


class ContributionDirection(str, Enum):
    """Direction of a feature's contribution towards anomaly classification."""
    INCREASES_ANOMALY = "increases_anomaly"
    DECREASES_ANOMALY = "decreases_anomaly"
    NEUTRAL = "neutral"


class FeatureContribution(BaseModel):
    """Individual feature contribution derived from model explanation (e.g. TreeSHAP)."""
    model_config = ConfigDict(frozen=True)

    feature_name: str = Field(..., description="Exact feature column name.")
    feature_value: float = Field(..., description="Observed input feature value.")
    contribution: float = Field(..., description="Model attribution value / SHAP value.")
    direction: ContributionDirection = Field(
        ContributionDirection.NEUTRAL,
        description="Whether this feature increases or decreases the anomaly score."
    )
    rank: int = Field(..., ge=1, description="Importance rank (1 = highest magnitude contribution).")


class EvidenceHierarchy(BaseModel):
    """Structured taxonomy separating direct, model, contextual, and operational evidence."""
    model_config = ConfigDict(frozen=True)

    direct_evidence: Dict[str, Any] = Field(
        default_factory=dict,
        description="Direct physical sensor readings, timestamps, and raw neighbor values."
    )
    model_evidence: Dict[str, Any] = Field(
        default_factory=dict,
        description="ML anomaly score, decision score, calibrated threshold, and top feature attributions."
    )
    contextual_evidence: Dict[str, Any] = Field(
        default_factory=dict,
        description="Spatial network consensus, temporal dynamics (rate, flatline), and multivariate physics."
    )
    operational_interpretation: str = Field(
        ...,
        description="High-level operational interpretation (e.g., 'probable sensor anomaly', 'possible regional event')."
    )


class NeighborComparison(BaseModel):
    """Neighbor comparison metrics for spatial validation of sensor anomalies."""
    model_config = ConfigDict(frozen=True)

    target_variable: str = Field("temperature_c", description="Primary meteorological variable compared.")
    target_value: Optional[float] = Field(None, description="Target station measured value.")
    neighbor_values: Dict[str, Optional[float]] = Field(
        default_factory=dict,
        description="Contemporaneous readings from adjacent AWS stations."
    )
    neighbor_median: Optional[float] = Field(None, description="Median of valid active neighbor readings.")
    target_deviation: Optional[float] = Field(None, description="Target value minus neighbor median.")
    agreeing_neighbor_count: int = Field(0, ge=0, description="Count of neighbors within agreement tolerance.")
    total_valid_neighbors: int = Field(0, ge=0, description="Total active neighbors available in temporal window.")
    temporal_alignment_window_minutes: float = Field(
        15.0,
        description="Temporal tolerance window for neighbor alignment (minutes)."
    )
    temporal_alignment_status: str = Field(
        "ALIGNED",
        description="Status of spatial temporal alignment (e.g. 'ALIGNED', 'SPARSE', 'NO_NEIGHBORS')."
    )


class AnomalyEpisode(BaseModel):
    """Data-oriented reconstruction of an anomaly event timeline."""
    model_config = ConfigDict(frozen=True)

    station_id: str = Field(..., description="Target AWS station identifier.")
    target_variable: Optional[str] = Field(None, description="Primary variable exhibiting anomaly.")
    onset_timestamp: Optional[str] = Field(None, description="Timestamp when observation first became anomalous.")
    peak_timestamp: Optional[str] = Field(None, description="Timestamp of maximum anomaly score or departure.")
    recovery_timestamp: Optional[str] = Field(None, description="Timestamp when observation returned to normal baseline.")
    duration_minutes: Optional[float] = Field(None, ge=0.0, description="Duration in minutes of anomaly episode.")
    peak_value: Optional[float] = Field(None, description="Measured value at peak anomaly timestamp.")
    peak_anomaly_score: Optional[float] = Field(None, description="Maximum normalized anomaly score during episode.")
    preceding_normal_observations: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Sample of normal observations immediately prior to onset."
    )
    episode_observations: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Sequence of observations during the anomaly episode."
    )
    recovering_observations: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Observations following recovery."
    )
    neighbor_context_summary: Dict[str, Any] = Field(
        default_factory=dict,
        description="Summary of neighboring station behavior across episode window."
    )


class AuditMetadata(BaseModel):
    """Traceable provenance metadata for reproducible auditability."""
    model_config = ConfigDict(frozen=True)

    model_version: str = Field("isolation_forest_v1", description="Identifier of the anomaly model.")
    feature_version: str = Field("v1.0.0", description="Feature engineering pipeline version.")
    decision_engine_version: str = Field("hybrid_v1.0.0", description="Hybrid decision engine version.")
    explanation_engine_version: str = Field("xai_v1.0.0", description="Explainability engine version.")
    explanation_method: str = Field("TREE_SHAP", description="Method used to compute feature contributions.")
    input_station_id: str = Field(..., description="Station ID evaluated.")
    input_timestamp: str = Field(..., description="Observation timestamp evaluated.")
    generated_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="UTC timestamp when explanation was produced."
    )


class ExplanationSummary(BaseModel):
    """Complete, structured Explainability and Anomaly Investigation package."""
    model_config = ConfigDict(frozen=True)

    station_id: str = Field(..., description="Target AWS station identifier.")
    timestamp: str = Field(..., description="ISO 8601 observation timestamp.")
    decision: HybridDecisionType = Field(..., description="Hybrid operational decision.")
    severity: DecisionSeverity = Field(..., description="Operational urgency severity.")
    
    # Human-readable operator summary
    summary: str = Field(..., description="Deterministic, operator-readable explanation of decision.")
    
    # Evidence categorization
    supporting_evidence: List[str] = Field(default_factory=list, description="Subsystem evidence supporting decision.")
    contradicting_evidence: List[str] = Field(default_factory=list, description="Evidence ruling out alternative causes.")
    unavailable_evidence: List[str] = Field(default_factory=list, description="Subsystems with missing/sparse context.")
    
    # Granular evidence subsystems
    feature_contributions: List[FeatureContribution] = Field(
        default_factory=list,
        description="Ranked ML feature attributions from actual model."
    )
    spatial_evidence: SpatialEvidence = Field(default_factory=SpatialEvidence)
    temporal_evidence: TemporalEvidence = Field(default_factory=TemporalEvidence)
    data_quality_evidence: DataQualityEvidence = Field(default_factory=DataQualityEvidence)
    multivariate_evidence: MultivariateEvidence = Field(default_factory=MultivariateEvidence)
    
    # Structured evidence hierarchy & neighbor comparison
    evidence_hierarchy: EvidenceHierarchy = Field(..., description="Separated direct, model, contextual, and operational evidence.")
    neighbor_comparison: Optional[NeighborComparison] = Field(None, description="Comparative neighbor metrics.")
    
    # Actionable guidance & audit
    recommended_investigation_steps: List[str] = Field(
        default_factory=list,
        description="Prioritized, actionable operational investigation steps."
    )
    audit_metadata: AuditMetadata = Field(..., description="Provenance metadata for auditing.")
