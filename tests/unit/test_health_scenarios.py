"""Unit tests for synthetic health scenarios A through H."""

import pytest

from ml.health.health_evaluator import HealthScenarioEvaluator
from ml.health.health_schema import HealthStatusBand, HealthTrend, MaintenanceRecommendation


@pytest.fixture
def evaluator() -> HealthScenarioEvaluator:
    return HealthScenarioEvaluator()


def test_scenario_a_healthy_station(evaluator: HealthScenarioEvaluator):
    """Scenario A: Healthy station maintains stable 90-100 score."""
    decs = evaluator.generate_scenario_decisions("HEALTHY", 24)
    summary = evaluator.engine.evaluate_station_health("AWS_001", decisions=decs)

    assert summary.overall_health_score is not None
    assert summary.overall_health_score >= 90.0
    assert summary.status_band == HealthStatusBand.HEALTHY
    assert summary.maintenance_recommendation == MaintenanceRecommendation.NO_ACTION


def test_scenario_b_repeated_spikes(evaluator: HealthScenarioEvaluator):
    """Scenario B: Repeated isolated spikes significantly reduce anomaly health."""
    decs = evaluator.generate_scenario_decisions("REPEATED_SPIKES", 24)
    summary = evaluator.engine.evaluate_station_health("AWS_001", decisions=decs)

    assert summary.overall_health_score is not None
    assert summary.overall_health_score < 75.0
    assert summary.status_band in (HealthStatusBand.ATTENTION, HealthStatusBand.DEGRADED)
    assert summary.component_scores.anomaly_health < 50.0


def test_scenario_c_gradual_drift(evaluator: HealthScenarioEvaluator):
    """Scenario C: Gradual drift reduces spatial consistency health and triggers INCREASING_DRIFT."""
    decs = evaluator.generate_scenario_decisions("GRADUAL_DRIFT", 24)
    summary = evaluator.engine.evaluate_station_health("AWS_001", decisions=decs)

    assert summary.overall_health_score is not None
    assert summary.component_scores.spatial_consistency_health < 80.0
    assert any("drift" in r.value.lower() or "spatial" in r.value.lower() for r in summary.reason_codes)


def test_scenario_d_frozen_sensor(evaluator: HealthScenarioEvaluator):
    """Scenario D: Frozen sensor flatline reduces temporal stability health and triggers INSPECT."""
    decs = evaluator.generate_scenario_decisions("FROZEN_SENSOR", 24)
    summary = evaluator.engine.evaluate_station_health("AWS_001", decisions=decs)

    assert summary.overall_health_score is not None
    assert summary.overall_health_score < 60.0
    assert summary.component_scores.temporal_stability_health < 50.0
    assert summary.maintenance_recommendation in (MaintenanceRecommendation.INSPECT, MaintenanceRecommendation.PRIORITY_INSPECTION)


def test_scenario_e_communication_degradation(evaluator: HealthScenarioEvaluator):
    """Scenario E: Telemetry communication gaps degrade communication health."""
    decs = evaluator.generate_scenario_decisions("COMMUNICATION_DEGRADATION", 24)
    summary = evaluator.engine.evaluate_station_health("AWS_001", decisions=decs)

    assert summary.overall_health_score is not None
    assert summary.component_scores.communication_health < 60.0


def test_scenario_h_regional_event_protection(evaluator: HealthScenarioEvaluator):
    """Scenario H (CRITICAL): Genuine regional weather event does NOT unfairly penalize sensor health."""
    decs = evaluator.generate_scenario_decisions("REGIONAL_EVENT", 24)
    summary = evaluator.engine.evaluate_station_health("AWS_001", decisions=decs)

    # Score MUST remain high because squalls/fronts are genuine atmospheric phenomena
    assert summary.overall_health_score is not None
    assert summary.overall_health_score >= 90.0
    assert summary.status_band == HealthStatusBand.HEALTHY
    assert summary.component_scores.anomaly_health == 100.0
    assert summary.maintenance_recommendation == MaintenanceRecommendation.NO_ACTION


def test_scenario_g_recovery_trend(evaluator: HealthScenarioEvaluator):
    """Scenario G: Recovery after previous degradation yields IMPROVING trend."""
    h_decs = evaluator.generate_scenario_decisions("HEALTHY", 24)
    sp_decs = evaluator.generate_scenario_decisions("REPEATED_SPIKES", 24)

    summary = evaluator.engine.evaluate_station_health(
        "AWS_001",
        decisions=h_decs,  # Current: pristine
        previous_decisions=sp_decs,  # Previous: degraded
    )

    assert summary.trend == HealthTrend.IMPROVING
    assert summary.health_delta is not None and summary.health_delta > 0.0


def test_all_scenarios_batch(evaluator: HealthScenarioEvaluator):
    """Execute all 8 scenarios and verify all pass."""
    batch_res = evaluator.evaluate_all_scenarios()
    assert batch_res["all_scenarios_passed"] is True
