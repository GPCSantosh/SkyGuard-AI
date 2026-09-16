"""Unit tests for Scenarios A through H in the Hybrid Decision Engine."""

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


def test_scenario_a_normal_observation(engine):
    """Scenario A: Pristine background weather -> NORMAL."""
    ev = ObservationEvidence(
        station_id="42182099999",
        timestamp="2024-06-01T12:00:00Z",
        data_quality=DataQualityEvidence(quality_status="VALID"),
        ml_anomaly=MLAnomalyEvidence(normalized_anomaly_score=0.10, ml_is_anomaly=False),
        spatial=SpatialEvidence(context_category=SpatialContextCategory.REGIONAL_PATTERN, temp_consensus_fraction=1.0),
    )
    res = engine.evaluate(ev)
    assert res.decision == HybridDecisionType.NORMAL
    assert res.severity == DecisionSeverity.INFO


def test_scenario_b_local_sensor_spike(engine):
    """Scenario B: Single-station spike -> PROBABLE_SENSOR_ANOMALY."""
    ev = ObservationEvidence(
        station_id="42182099999",
        timestamp="2024-06-01T12:00:00Z",
        data_quality=DataQualityEvidence(quality_status="VALID"),
        ml_anomaly=MLAnomalyEvidence(normalized_anomaly_score=0.95, ml_is_anomaly=True),
        temporal=TemporalEvidence(temp_rate_per_min=1.5, is_rate_abnormal=True),
        spatial=SpatialEvidence(context_category=SpatialContextCategory.LOCAL_ONLY, temp_target_minus_mean=8.0),
    )
    res = engine.evaluate(ev)
    assert res.decision == HybridDecisionType.PROBABLE_SENSOR_ANOMALY
    assert res.severity in (DecisionSeverity.HIGH, DecisionSeverity.CRITICAL)


def test_scenario_c_regional_event(engine):
    """Scenario C: Coherent regional weather front -> POSSIBLE_GENUINE_EVENT."""
    ev = ObservationEvidence(
        station_id="42182099999",
        timestamp="2024-06-01T12:00:00Z",
        data_quality=DataQualityEvidence(quality_status="VALID"),
        ml_anomaly=MLAnomalyEvidence(normalized_anomaly_score=0.75, ml_is_anomaly=True),
        temporal=TemporalEvidence(temp_rate_per_min=-0.80, is_rate_abnormal=True),
        spatial=SpatialEvidence(context_category=SpatialContextCategory.REGIONAL_PATTERN, temp_consensus_fraction=0.90),
    )
    res = engine.evaluate(ev)
    assert res.decision == HybridDecisionType.POSSIBLE_GENUINE_EVENT


def test_scenario_d_mixed_event(engine):
    """Scenario D: Mixed regional event + local fault -> PROBABLE_SENSOR_ANOMALY with regional trace."""
    ev = ObservationEvidence(
        station_id="42182099999",
        timestamp="2024-06-01T12:00:00Z",
        data_quality=DataQualityEvidence(quality_status="VALID"),
        ml_anomaly=MLAnomalyEvidence(normalized_anomaly_score=0.92, ml_is_anomaly=True),
        spatial=SpatialEvidence(
            context_category=SpatialContextCategory.REGIONAL_PATTERN,
            temp_target_minus_mean=8.0,
            temp_target_zscore=4.0,
        ),
    )
    res = engine.evaluate(ev)
    assert res.decision == HybridDecisionType.PROBABLE_SENSOR_ANOMALY
    assert DecisionReasonCode.MIXED_REGIONAL_EVENT_WITH_LOCAL_EXCESS in res.reason_codes


def test_scenario_e_missing_data_gap(engine):
    """Scenario E: Telemetry communication gap -> PROBABLE_DATA_QUALITY_ISSUE."""
    ev = ObservationEvidence(
        station_id="42182099999",
        timestamp="2024-06-01T12:00:00Z",
        data_quality=DataQualityEvidence(
            quality_status="GAP",
            missing_fields=["temperature_c", "relative_humidity_pct"],
            communication_gap_minutes=60.0,
        ),
    )
    res = engine.evaluate(ev)
    assert res.decision == HybridDecisionType.PROBABLE_DATA_QUALITY_ISSUE


def test_scenario_f_frozen_sensor(engine):
    """Scenario F: Stuck sensor flatline -> PROBABLE_SENSOR_ANOMALY."""
    ev = ObservationEvidence(
        station_id="42182099999",
        timestamp="2024-06-01T12:00:00Z",
        data_quality=DataQualityEvidence(quality_status="VALID"),
        temporal=TemporalEvidence(consecutive_unchanged_count=8, is_flatline=True),
    )
    res = engine.evaluate(ev)
    assert res.decision == HybridDecisionType.PROBABLE_SENSOR_ANOMALY
    assert DecisionReasonCode.PERSISTENT_VALUE in res.reason_codes


def test_scenario_g_slow_drift(engine):
    """Scenario G: Slow progressive sensor drift with local isolation -> PROBABLE_SENSOR_ANOMALY."""
    ev = ObservationEvidence(
        station_id="42182099999",
        timestamp="2024-06-01T12:00:00Z",
        data_quality=DataQualityEvidence(quality_status="VALID"),
        ml_anomaly=MLAnomalyEvidence(normalized_anomaly_score=0.70, ml_is_anomaly=True),
        temporal=TemporalEvidence(baseline_deviation_zscore=2.8),
        spatial=SpatialEvidence(context_category=SpatialContextCategory.LOCAL_ONLY, temp_target_minus_mean=3.5),
    )
    res = engine.evaluate(ev)
    assert res.decision == HybridDecisionType.PROBABLE_SENSOR_ANOMALY


def test_scenario_h_conflicting_evidence(engine):
    """Scenario H: High ML score with zero spatial network coverage -> UNCERTAIN."""
    ev = ObservationEvidence(
        station_id="42182099999",
        timestamp="2024-06-01T12:00:00Z",
        data_quality=DataQualityEvidence(quality_status="VALID"),
        ml_anomaly=MLAnomalyEvidence(normalized_anomaly_score=0.74, ml_is_anomaly=True),
        spatial=SpatialEvidence(context_category=SpatialContextCategory.INSUFFICIENT_CONTEXT),
    )
    res = engine.evaluate(ev)
    assert res.decision == HybridDecisionType.UNCERTAIN
