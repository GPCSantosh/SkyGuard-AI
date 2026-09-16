"""Unit tests for SensorHealthEngine core calculations and recommendations."""

import pytest
import pandas as pd

from ml.decision.schema import (
    DataQualityEvidence,
    DecisionExplanation,
    DecisionReasonCode,
    DecisionSeverity,
    HybridDecision,
    HybridDecisionType,
    MLAnomalyEvidence,
    ObservationEvidence,
    SpatialEvidence,
    TemporalEvidence,
)
from ml.health.health_engine import SensorHealthEngine
from ml.health.health_schema import (
    HealthReasonCode,
    HealthStatusBand,
    HealthTrend,
    MaintenanceRecommendation,
)
from ml.spatial.schema import SpatialContextCategory


@pytest.fixture
def health_engine() -> SensorHealthEngine:
    return SensorHealthEngine()


def test_health_engine_deterministic_repeatability(health_engine: SensorHealthEngine):
    """Test that identical decision inputs produce identical scores and summaries."""
    decs = []
    base_t = pd.Timestamp("2026-09-17 00:00:00")
    for i in range(20):
        t_str = (base_t + pd.Timedelta(minutes=i * 5)).isoformat() + "Z"
        ev = ObservationEvidence(
            station_id="AWS_001",
            timestamp=t_str,
            data_quality=DataQualityEvidence(quality_status="VALID"),
            spatial=SpatialEvidence(context_category=SpatialContextCategory.REGIONAL_PATTERN, valid_neighbor_count=4),
        )
        dec = HybridDecision(
            station_id="AWS_001",
            timestamp=t_str,
            decision=HybridDecisionType.NORMAL,
            severity=DecisionSeverity.INFO,
            reason_codes=[DecisionReasonCode.NOMINAL_OBSERVATION],
            recommended_action="No action.",
            explanation=DecisionExplanation(summary="Normal observation."),
            evidence=ev,
        )
        decs.append(dec)

    res1 = health_engine.evaluate_station_health("AWS_001", decisions=decs)
    res2 = health_engine.evaluate_station_health("AWS_001", decisions=decs)

    assert res1.overall_health_score == res2.overall_health_score
    assert res1.status_band == res2.status_band
    assert res1.summary == res2.summary
    assert res1.maintenance_recommendation == res2.maintenance_recommendation
    assert res1.overall_health_score == 100.0
    assert res1.status_band == HealthStatusBand.HEALTHY
    assert res1.maintenance_recommendation == MaintenanceRecommendation.NO_ACTION


def test_parameter_level_health_isolation(health_engine: SensorHealthEngine):
    """Test that an issue on a single channel (e.g. Temperature drift) degrades that parameter while others remain healthy."""
    decs = []
    base_t = pd.Timestamp("2026-09-17 00:00:00")
    for i in range(20):
        t_str = (base_t + pd.Timedelta(minutes=i * 5)).isoformat() + "Z"
        # Temperature has large positive spatial deviation
        ev = ObservationEvidence(
            station_id="AWS_001",
            timestamp=t_str,
            spatial=SpatialEvidence(
                context_category=SpatialContextCategory.LOCAL_ONLY,
                temp_target_minus_mean=3.5,  # Temperature drift
                valid_neighbor_count=4,
            ),
        )
        dec = HybridDecision(
            station_id="AWS_001",
            timestamp=t_str,
            decision=HybridDecisionType.PROBABLE_SENSOR_ANOMALY,
            severity=DecisionSeverity.MEDIUM,
            reason_codes=[DecisionReasonCode.LOCAL_SPATIAL_ISOLATION],
            recommended_action="Inspect temperature sensor.",
            explanation=DecisionExplanation(summary="Temperature departure."),
            evidence=ev,
        )
        decs.append(dec)

    summary = health_engine.evaluate_station_health("AWS_001", decisions=decs)
    assert summary.parameter_health["temperature_c"].health_score is not None
    assert summary.parameter_health["temperature_c"].health_score < summary.parameter_health["relative_humidity"].health_score
    assert summary.parameter_health["temperature_c"].drift_indicator is not None
