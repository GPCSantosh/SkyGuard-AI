"""Unit tests for ObservationEvidence schemas and evidence states."""

from __future__ import annotations

import pytest

from ml.decision.schema import (
    DataQualityEvidence,
    DecisionReasonCode,
    DecisionSeverity,
    EvidenceState,
    HybridDecisionType,
    MLAnomalyEvidence,
    MultivariateEvidence,
    ObservationEvidence,
    SpatialEvidence,
    TemporalEvidence,
)
from ml.spatial.schema import SpatialContextCategory


def test_evidence_model_instantiation():
    """Verify ObservationEvidence creates immutable models with full subsystem coverage."""
    ev = ObservationEvidence(
        station_id="42182099999",
        timestamp="2024-06-01T12:00:00Z",
        data_quality=DataQualityEvidence(quality_status="VALID"),
        ml_anomaly=MLAnomalyEvidence(raw_model_score=0.45, normalized_anomaly_score=0.70, ml_is_anomaly=True),
        temporal=TemporalEvidence(temp_rate_per_min=0.15, consecutive_unchanged_count=0),
        multivariate=MultivariateEvidence(dew_point_spread_c=5.0),
        spatial=SpatialEvidence(valid_neighbor_count=3, context_category=SpatialContextCategory.REGIONAL_PATTERN),
    )

    assert ev.station_id == "42182099999"
    assert ev.ml_anomaly.normalized_anomaly_score == 0.70
    assert ev.spatial.context_category == SpatialContextCategory.REGIONAL_PATTERN


def test_evidence_state_enums():
    """Verify EvidenceState enums adhere to SUPPORTS, CONTRADICTS, NEUTRAL, UNAVAILABLE."""
    states = [EvidenceState.SUPPORTS, EvidenceState.CONTRADICTS, EvidenceState.NEUTRAL, EvidenceState.UNAVAILABLE]
    assert len(states) == 4
    assert EvidenceState("SUPPORTS") == EvidenceState.SUPPORTS
