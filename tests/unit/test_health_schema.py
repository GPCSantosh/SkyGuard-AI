"""Unit tests for sensor health schemas and data models."""

import pytest

from ml.health.health_schema import (
    ComponentHealthScores,
    HealthAuditMetadata,
    HealthReasonCode,
    HealthStatusBand,
    HealthTrend,
    MaintenanceRecommendation,
    ParameterHealth,
    SensorHealthSummary,
)


def test_health_schema_instantiation_and_immutability():
    """Test valid instantiation and immutability of health summaries."""
    comp = ComponentHealthScores(
        anomaly_health=95.0,
        data_quality_health=100.0,
        communication_health=90.0,
        temporal_stability_health=100.0,
        spatial_consistency_health=92.0,
    )

    audit = HealthAuditMetadata(
        health_engine_version="health_v1.0.0",
        decision_engine_version="hybrid_v1.0.0",
        feature_version="v1.0.0",
        window_name="24h",
        window_hours=24.0,
        min_observations_required=12,
        total_observations_evaluated=288,
    )

    param_temp = ParameterHealth(
        parameter_name="temperature_c",
        health_score=94.5,
        status_band=HealthStatusBand.HEALTHY,
        trend=HealthTrend.STABLE,
        component_scores=comp,
        drift_indicator=None,
        flatline_duration_minutes=0.0,
        supporting_evidence=["Nominal operation"],
    )

    summary = SensorHealthSummary(
        station_id="AWS_001",
        window_name="24h",
        overall_health_score=95.4,
        status_band=HealthStatusBand.HEALTHY,
        trend=HealthTrend.STABLE,
        health_delta=0.5,
        component_scores=comp,
        parameter_health={"temperature_c": param_temp},
        maintenance_recommendation=MaintenanceRecommendation.NO_ACTION,
        reason_codes=[HealthReasonCode.NOMINAL_OPERATION],
        summary="Sensor Health Index: 95.4/100 (HEALTHY, trend: stable).",
        supporting_evidence=["All indicators normal"],
        recommended_action="No action required.",
        audit_metadata=audit,
    )

    assert summary.station_id == "AWS_001"
    assert summary.overall_health_score == 95.4
    assert summary.status_band == HealthStatusBand.HEALTHY
    assert summary.parameter_health["temperature_c"].health_score == 94.5

    # Test immutability
    with pytest.raises(Exception):
        summary.overall_health_score = 50.0  # frozen model


def test_health_bands_and_recommendations_enums():
    """Test enum members and string representations."""
    assert HealthStatusBand.HEALTHY.value == "HEALTHY"
    assert HealthStatusBand.INSUFFICIENT_HISTORY.value == "INSUFFICIENT_HISTORY"
    assert HealthTrend.IMPROVING.value == "IMPROVING"
    assert MaintenanceRecommendation.PRIORITY_INSPECTION.value == "PRIORITY_INSPECTION"
