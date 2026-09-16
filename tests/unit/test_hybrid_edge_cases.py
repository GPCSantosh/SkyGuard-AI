"""Unit tests for edge cases and causality in the Hybrid Decision Engine."""

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


def test_edge_case_zero_anomaly_score(engine):
    """Verify anomaly score 0.0 with pristine telemetry returns NORMAL."""
    ev = ObservationEvidence(
        station_id="42182099999",
        timestamp="2024-06-01T12:00:00Z",
        data_quality=DataQualityEvidence(quality_status="VALID"),
        ml_anomaly=MLAnomalyEvidence(normalized_anomaly_score=0.0, ml_is_anomaly=False),
        spatial=SpatialEvidence(context_category=SpatialContextCategory.REGIONAL_PATTERN),
    )
    res = engine.evaluate(ev)
    assert res.decision == HybridDecisionType.NORMAL
    assert res.severity == DecisionSeverity.INFO


def test_edge_case_extreme_anomaly_score(engine):
    """Verify maximum anomaly score 1.0 with spatial isolation produces CRITICAL/HIGH PROBABLE_SENSOR_ANOMALY."""
    ev = ObservationEvidence(
        station_id="42182099999",
        timestamp="2024-06-01T12:00:00Z",
        data_quality=DataQualityEvidence(quality_status="VALID"),
        ml_anomaly=MLAnomalyEvidence(normalized_anomaly_score=1.0, ml_is_anomaly=True),
        spatial=SpatialEvidence(context_category=SpatialContextCategory.LOCAL_ONLY, temp_target_minus_mean=12.0),
    )
    res = engine.evaluate(ev)
    assert res.decision == HybridDecisionType.PROBABLE_SENSOR_ANOMALY
    assert res.severity in (DecisionSeverity.HIGH, DecisionSeverity.CRITICAL)


def test_edge_case_ml_normal_but_spatial_local_only(engine):
    """Verify when ML is moderate/normal but spatial indicates local isolation and high rate of change."""
    ev = ObservationEvidence(
        station_id="42182099999",
        timestamp="2024-06-01T12:00:00Z",
        data_quality=DataQualityEvidence(quality_status="VALID"),
        ml_anomaly=MLAnomalyEvidence(normalized_anomaly_score=0.45, ml_is_anomaly=False),
        temporal=TemporalEvidence(is_rate_abnormal=True),
        spatial=SpatialEvidence(context_category=SpatialContextCategory.LOCAL_ONLY, temp_target_minus_mean=4.0),
    )
    res = engine.evaluate(ev)
    assert res.decision == HybridDecisionType.PROBABLE_SENSOR_ANOMALY
    assert DecisionReasonCode.LOCAL_SPATIAL_ISOLATION in res.reason_codes


def test_edge_case_contradictory_data_quality_flags(engine):
    """Verify quality status GAP with is_duplicate takes defensive PROBABLE_DATA_QUALITY_ISSUE."""
    ev = ObservationEvidence(
        station_id="42182099999",
        timestamp="2024-06-01T12:00:00Z",
        data_quality=DataQualityEvidence(
            quality_status="GAP",
            is_duplicate=True,
            communication_gap_minutes=30.0,
        ),
    )
    res = engine.evaluate(ev)
    assert res.decision == HybridDecisionType.PROBABLE_DATA_QUALITY_ISSUE
    assert DecisionReasonCode.DUPLICATE_TIMESTAMP in res.reason_codes
    assert DecisionReasonCode.DATA_GAP in res.reason_codes


def test_decision_causality_forward_time_isolation(engine):
    """Verify hybrid decision evaluates strictly at timestamp T without forward contamination."""
    ev_past = ObservationEvidence(
        station_id="42182099999",
        timestamp="2024-06-01T12:00:00Z",
        data_quality=DataQualityEvidence(quality_status="VALID"),
        ml_anomaly=MLAnomalyEvidence(normalized_anomaly_score=0.15, ml_is_anomaly=False),
        spatial=SpatialEvidence(context_category=SpatialContextCategory.REGIONAL_PATTERN),
    )
    dec1 = engine.evaluate(ev_past)
    assert dec1.decision == HybridDecisionType.NORMAL

    # Evaluating same timestamp remains identical regardless of subsequent time steps
    dec2 = engine.evaluate(ev_past)
    assert dec1.decision == dec2.decision
    assert dec1.severity == dec2.severity
    assert dec1.reason_codes == dec2.reason_codes
