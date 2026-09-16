"""Unit tests for Hybrid Decision Engine rule hierarchy and decision gates."""

from __future__ import annotations

import pytest

from ml.decision.engine import HybridDecisionEngine
from ml.decision.schema import (
    DataQualityEvidence,
    DecisionReasonCode,
    DecisionSeverity,
    HybridDecisionType,
    MLAnomalyEvidence,
    MultivariateEvidence,
    ObservationEvidence,
    SpatialEvidence,
    TemporalEvidence,
)
from ml.spatial.schema import SpatialContextCategory


@pytest.fixture
def engine() -> HybridDecisionEngine:
    return HybridDecisionEngine()


def test_data_quality_precedence_gate(engine):
    """Gate 1: Telemetry defect must supersede normal or abnormal ML scores."""
    ev = ObservationEvidence(
        station_id="42182099999",
        timestamp="2024-06-01T12:00:00Z",
        data_quality=DataQualityEvidence(
            quality_status="GAP",
            missing_fields=["temperature_c"],
            communication_gap_minutes=60.0,
        ),
        ml_anomaly=MLAnomalyEvidence(normalized_anomaly_score=0.99, ml_is_anomaly=True),
        spatial=SpatialEvidence(context_category=SpatialContextCategory.REGIONAL_PATTERN),
    )

    decision = engine.evaluate(ev)
    assert decision.decision == HybridDecisionType.PROBABLE_DATA_QUALITY_ISSUE
    assert DecisionReasonCode.DATA_GAP in decision.reason_codes
    assert DecisionReasonCode.MISSING_REQUIRED_VARIABLES in decision.reason_codes
    assert decision.severity in (DecisionSeverity.HIGH, DecisionSeverity.CRITICAL)


def test_physical_planetary_boundary_gate(engine):
    """Gate 2: Physical thermodynamic bound breach must produce CRITICAL PROBABLE_SENSOR_ANOMALY."""
    ev = ObservationEvidence(
        station_id="42182099999",
        timestamp="2024-06-01T12:00:00Z",
        data_quality=DataQualityEvidence(quality_status="VALID", is_physical_out_of_bounds=True),
        ml_anomaly=MLAnomalyEvidence(normalized_anomaly_score=0.90, ml_is_anomaly=True),
    )

    decision = engine.evaluate(ev)
    assert decision.decision == HybridDecisionType.PROBABLE_SENSOR_ANOMALY
    assert decision.severity == DecisionSeverity.CRITICAL
    assert DecisionReasonCode.OUT_OF_RANGE_PHYSICAL in decision.reason_codes


def test_persistent_flatline_gate(engine):
    """Gate 3: Sensor stuck flatline must trigger PROBABLE_SENSOR_ANOMALY."""
    ev = ObservationEvidence(
        station_id="42182099999",
        timestamp="2024-06-01T12:00:00Z",
        data_quality=DataQualityEvidence(quality_status="VALID"),
        temporal=TemporalEvidence(
            consecutive_unchanged_count=10,
            flatline_duration_minutes=50.0,
            is_flatline=True,
        ),
        spatial=SpatialEvidence(context_category=SpatialContextCategory.REGIONAL_PATTERN),
    )

    decision = engine.evaluate(ev)
    assert decision.decision == HybridDecisionType.PROBABLE_SENSOR_ANOMALY
    assert DecisionReasonCode.PERSISTENT_VALUE in decision.reason_codes


def test_multivariate_contradiction_gate(engine):
    """Gate 4: Physical thermodynamic contradiction must trigger PROBABLE_SENSOR_ANOMALY."""
    ev = ObservationEvidence(
        station_id="42182099999",
        timestamp="2024-06-01T12:00:00Z",
        data_quality=DataQualityEvidence(quality_status="VALID"),
        multivariate=MultivariateEvidence(is_multivariate_abnormal=True, temp_rh_inconsistent=True),
    )

    decision = engine.evaluate(ev)
    assert decision.decision == HybridDecisionType.PROBABLE_SENSOR_ANOMALY
    assert DecisionReasonCode.MULTIVARIATE_DEVIATION in decision.reason_codes


def test_spatial_ml_local_isolation(engine):
    """Gate 5B: High ML score + LOCAL_ONLY spatial context -> PROBABLE_SENSOR_ANOMALY."""
    ev = ObservationEvidence(
        station_id="42182099999",
        timestamp="2024-06-01T12:00:00Z",
        data_quality=DataQualityEvidence(quality_status="VALID"),
        ml_anomaly=MLAnomalyEvidence(normalized_anomaly_score=0.88, ml_is_anomaly=True),
        spatial=SpatialEvidence(
            valid_neighbor_count=4,
            context_category=SpatialContextCategory.LOCAL_ONLY,
            temp_target_minus_mean=6.5,
            is_spatially_isolated=True,
        ),
    )

    decision = engine.evaluate(ev)
    assert decision.decision == HybridDecisionType.PROBABLE_SENSOR_ANOMALY
    assert decision.severity == DecisionSeverity.HIGH
    assert DecisionReasonCode.LOCAL_SPATIAL_ISOLATION in decision.reason_codes


def test_spatial_ml_regional_agreement(engine):
    """Gate 5A: High ML score + REGIONAL_PATTERN spatial context -> POSSIBLE_GENUINE_EVENT."""
    ev = ObservationEvidence(
        station_id="42182099999",
        timestamp="2024-06-01T12:00:00Z",
        data_quality=DataQualityEvidence(quality_status="VALID"),
        ml_anomaly=MLAnomalyEvidence(normalized_anomaly_score=0.82, ml_is_anomaly=True),
        temporal=TemporalEvidence(temp_rate_per_min=-0.75, is_rate_abnormal=True),
        spatial=SpatialEvidence(
            valid_neighbor_count=4,
            context_category=SpatialContextCategory.REGIONAL_PATTERN,
            temp_consensus_fraction=0.80,
            temp_target_minus_mean=-0.2,
            is_regionally_corroborated=True,
        ),
    )

    decision = engine.evaluate(ev)
    assert decision.decision == HybridDecisionType.POSSIBLE_GENUINE_EVENT
    assert DecisionReasonCode.REGIONAL_SPATIAL_AGREEMENT in decision.reason_codes


def test_mixed_event_retention(engine):
    """Gate 5A: Regional event with excessive target deviation retains both evidence traces."""
    ev = ObservationEvidence(
        station_id="42182099999",
        timestamp="2024-06-01T12:00:00Z",
        data_quality=DataQualityEvidence(quality_status="VALID"),
        ml_anomaly=MLAnomalyEvidence(normalized_anomaly_score=0.90, ml_is_anomaly=True),
        spatial=SpatialEvidence(
            valid_neighbor_count=4,
            context_category=SpatialContextCategory.REGIONAL_PATTERN,
            temp_target_minus_mean=8.5,
            temp_target_zscore=4.2,
        ),
    )

    decision = engine.evaluate(ev)
    assert decision.decision == HybridDecisionType.PROBABLE_SENSOR_ANOMALY
    assert DecisionReasonCode.MIXED_REGIONAL_EVENT_WITH_LOCAL_EXCESS in decision.reason_codes
    assert DecisionReasonCode.REGIONAL_SPATIAL_AGREEMENT in decision.reason_codes


def test_uncertainty_resolution(engine):
    """Gate 5D / Gate 6: Missing spatial coverage with anomaly score produces UNCERTAIN."""
    ev = ObservationEvidence(
        station_id="42182099999",
        timestamp="2024-06-01T12:00:00Z",
        data_quality=DataQualityEvidence(quality_status="VALID"),
        ml_anomaly=MLAnomalyEvidence(normalized_anomaly_score=0.75, ml_is_anomaly=True),
        spatial=SpatialEvidence(
            valid_neighbor_count=0,
            context_category=SpatialContextCategory.INSUFFICIENT_CONTEXT,
        ),
    )

    decision = engine.evaluate(ev)
    assert decision.decision == HybridDecisionType.UNCERTAIN
    assert DecisionReasonCode.INSUFFICIENT_SPATIAL_CONTEXT in decision.reason_codes
    assert DecisionReasonCode.CONFLICTING_EVIDENCE in decision.reason_codes


def test_nominal_fallback(engine):
    """Gate 7: Nominal observation produces NORMAL with INFO severity."""
    ev = ObservationEvidence(
        station_id="42182099999",
        timestamp="2024-06-01T12:00:00Z",
        data_quality=DataQualityEvidence(quality_status="VALID"),
        ml_anomaly=MLAnomalyEvidence(normalized_anomaly_score=0.10, ml_is_anomaly=False),
        spatial=SpatialEvidence(
            valid_neighbor_count=4,
            context_category=SpatialContextCategory.REGIONAL_PATTERN,
            temp_target_minus_mean=0.1,
        ),
    )

    decision = engine.evaluate(ev)
    assert decision.decision == HybridDecisionType.NORMAL
    assert decision.severity == DecisionSeverity.INFO
    assert DecisionReasonCode.NOMINAL_OBSERVATION in decision.reason_codes
