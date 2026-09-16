"""Unit tests for sensor health edge cases and low-data modes."""

import pytest
import pandas as pd

from ml.decision.schema import (
    DataQualityEvidence,
    DecisionExplanation,
    DecisionReasonCode,
    DecisionSeverity,
    HybridDecision,
    HybridDecisionType,
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
def engine() -> SensorHealthEngine:
    return SensorHealthEngine()


def test_edge_case_zero_observations(engine: SensorHealthEngine):
    """Test engine returns INSUFFICIENT_HISTORY with 0 observations."""
    summary = engine.evaluate_station_health("AWS_NEW", decisions=[])
    assert summary.status_band == HealthStatusBand.INSUFFICIENT_HISTORY
    assert summary.overall_health_score is None
    assert summary.trend == HealthTrend.INSUFFICIENT_HISTORY
    assert HealthReasonCode.INSUFFICIENT_OBSERVATION_HISTORY in summary.reason_codes
    assert "Insufficient observation history" in summary.summary


def test_edge_case_single_observation(engine: SensorHealthEngine):
    """Test engine returns INSUFFICIENT_HISTORY with 1 observation."""
    ev = ObservationEvidence(station_id="AWS_NEW", timestamp="2026-09-17T00:00:00Z")
    dec = HybridDecision(
        station_id="AWS_NEW", timestamp="2026-09-17T00:00:00Z", decision=HybridDecisionType.NORMAL,
        severity=DecisionSeverity.INFO, reason_codes=[DecisionReasonCode.NOMINAL_OBSERVATION],
        recommended_action="None", explanation=DecisionExplanation(summary="Normal"), evidence=ev,
    )
    summary = engine.evaluate_station_health("AWS_NEW", decisions=[dec])
    assert summary.status_band == HealthStatusBand.INSUFFICIENT_HISTORY
    assert summary.overall_health_score is None


def test_edge_case_healthy_station_with_single_isolated_anomaly(engine: SensorHealthEngine):
    """Test that a single isolated anomaly does not cause a healthy station to collapse to CRITICAL."""
    decs = []
    base_t = pd.Timestamp("2026-09-17 00:00:00")
    for i in range(24):
        t_str = (base_t + pd.Timedelta(minutes=i * 5)).isoformat() + "Z"
        is_isolated_spike = (i == 10)
        ev = ObservationEvidence(
            station_id="AWS_001",
            timestamp=t_str,
            spatial=SpatialEvidence(
                context_category=SpatialContextCategory.LOCAL_ONLY if is_isolated_spike else SpatialContextCategory.REGIONAL_PATTERN,
                valid_neighbor_count=4,
            ),
        )
        dec = HybridDecision(
            station_id="AWS_001",
            timestamp=t_str,
            decision=HybridDecisionType.PROBABLE_SENSOR_ANOMALY if is_isolated_spike else HybridDecisionType.NORMAL,
            severity=DecisionSeverity.MEDIUM if is_isolated_spike else DecisionSeverity.INFO,
            reason_codes=[DecisionReasonCode.LOCAL_SPATIAL_ISOLATION] if is_isolated_spike else [DecisionReasonCode.NOMINAL_OBSERVATION],
            recommended_action="Check",
            explanation=DecisionExplanation(summary="Observation"),
            evidence=ev,
        )
        decs.append(dec)

    summary = engine.evaluate_station_health("AWS_001", decisions=decs)
    assert summary.overall_health_score is not None
    # Score should remain high (>= 80.0) despite one transient glitch
    assert summary.overall_health_score >= 80.0
    assert summary.status_band in (HealthStatusBand.HEALTHY, HealthStatusBand.GOOD)
    assert summary.maintenance_recommendation == MaintenanceRecommendation.NO_ACTION


def test_edge_case_sudden_data_quality_collapse(engine: SensorHealthEngine):
    """Test that sudden widespread data quality / schema failure severely degrades health."""
    decs = []
    base_t = pd.Timestamp("2026-09-17 00:00:00")
    for i in range(20):
        t_str = (base_t + pd.Timedelta(minutes=i * 5)).isoformat() + "Z"
        ev = ObservationEvidence(
            station_id="AWS_001",
            timestamp=t_str,
            data_quality=DataQualityEvidence(
                quality_status="REJECTED",
                missing_fields=["temperature_c", "relative_humidity", "sea_level_pressure_hpa"],
            ),
        )
        dec = HybridDecision(
            station_id="AWS_001",
            timestamp=t_str,
            decision=HybridDecisionType.PROBABLE_DATA_QUALITY_ISSUE,
            severity=DecisionSeverity.CRITICAL,
            reason_codes=[DecisionReasonCode.MISSING_REQUIRED_VARIABLES],
            recommended_action="Check ingestion pipeline.",
            explanation=DecisionExplanation(summary="Schema rejection."),
            evidence=ev,
        )
        decs.append(dec)

    summary = engine.evaluate_station_health("AWS_001", decisions=decs)
    assert summary.overall_health_score is not None
    assert summary.overall_health_score <= 50.0
    assert summary.component_scores.data_quality_health == 0.0
    assert summary.status_band in (HealthStatusBand.ATTENTION, HealthStatusBand.DEGRADED, HealthStatusBand.CRITICAL)

