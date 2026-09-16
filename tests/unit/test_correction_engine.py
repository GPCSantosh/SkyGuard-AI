"""Unit tests for CorrectionRecommendationEngine."""

import pytest

from ml.decision.schema import HybridDecisionType
from ml.health.health_schema import (
    ComponentHealthScores,
    HealthAuditMetadata,
    HealthStatusBand,
    HealthTrend,
    MaintenanceRecommendation,
    SensorHealthSummary,
)
from ml.imputation.correction_engine import CorrectionRecommendationEngine
from ml.imputation.schema import EstimationMethod, RecommendationStatus
from ml.spatial.engine import SpatialContextEngine
from ml.spatial.topology import SpatialNetworkTopology, StationNode


@pytest.fixture
def sample_topology():
    topo = SpatialNetworkTopology()
    topo.add_station(StationNode(station_id="TARGET", name="Target Station", latitude=28.6139, longitude=77.2090, elevation_m=216.0))
    topo.add_station(StationNode(station_id="N1", name="Neighbor 1", latitude=28.5800, longitude=77.2300, elevation_m=215.0))
    topo.add_station(StationNode(station_id="N2", name="Neighbor 2", latitude=28.6500, longitude=77.1900, elevation_m=220.0))
    return topo


@pytest.fixture
def degraded_health_summary():
    return SensorHealthSummary(
        station_id="TARGET",
        window_name="24h",
        overall_health_score=38.0,
        status_band=HealthStatusBand.DEGRADED,
        trend=HealthTrend.DEGRADING,
        component_scores=ComponentHealthScores(
            anomaly_health=30.0,
            data_quality_health=50.0,
            communication_health=80.0,
            temporal_stability_health=40.0,
            spatial_consistency_health=35.0,
        ),
        maintenance_recommendation=MaintenanceRecommendation.INSPECT,
        summary="Station has persistent localized anomalies and failing temperature probe.",
        recommended_action="Inspect temperature probe.",
        audit_metadata=HealthAuditMetadata(input_station_id="TARGET"),
    )


def test_regional_event_protection(sample_topology):
    spatial_engine = SpatialContextEngine(topology=sample_topology)
    engine = CorrectionRecommendationEngine(spatial_engine=spatial_engine)

    rec = engine.recommend_for_variable(
        station_id="TARGET",
        timestamp="2026-09-17T12:00:00Z",
        target_variable="temperature_c",
        observed_value=45.0,  # Extreme heatwave reading
        decision_type=HybridDecisionType.POSSIBLE_GENUINE_EVENT,
        reason_codes=["REGIONAL_SPATIAL_AGREEMENT"],
    )

    assert rec.status == RecommendationStatus.NO_CORRECTION_RECOMMENDED
    assert rec.recommended_value is None
    assert rec.method == EstimationMethod.NO_ESTIMATE
    assert "consistent with regional atmospheric behavior" in rec.supporting_evidence[0]


def test_clean_data_protection():
    engine = CorrectionRecommendationEngine()

    rec = engine.recommend_for_variable(
        station_id="TARGET",
        timestamp="2026-09-17T12:00:00Z",
        target_variable="temperature_c",
        observed_value=24.5,
        decision_type=HybridDecisionType.NORMAL,
        reason_codes=["NOMINAL_OBSERVATION"],
    )

    assert rec.status == RecommendationStatus.NO_CORRECTION_RECOMMENDED
    assert rec.recommended_value is None
    assert rec.method == EstimationMethod.NO_ESTIMATE
    assert "nominal" in rec.supporting_evidence[0].lower()


def test_suspicious_spike_correction_candidate(sample_topology, degraded_health_summary):
    spatial_engine = SpatialContextEngine(topology=sample_topology)
    engine = CorrectionRecommendationEngine(spatial_engine=spatial_engine)

    neighbors = [
        {"station_id": "N1", "timestamp": "2026-09-17T12:00:00Z", "temperature_c": 28.0},
        {"station_id": "N2", "timestamp": "2026-09-17T12:00:00Z", "temperature_c": 28.2},
    ]
    temporal_hist = [27.8, 27.9, 28.0, 28.1]

    rec = engine.recommend_for_variable(
        station_id="TARGET",
        timestamp="2026-09-17T12:00:00Z",
        target_variable="temperature_c",
        observed_value=39.0,  # 39°C spike while neighbors are 28°C
        decision_type=HybridDecisionType.PROBABLE_SENSOR_ANOMALY,
        reason_codes=["LOCAL_SPATIAL_ISOLATION", "RAPID_RATE_OF_CHANGE"],
        neighbor_observations=neighbors,
        temporal_history=temporal_hist,
        sensor_health=degraded_health_summary,
    )

    assert rec.status == RecommendationStatus.CORRECTION_CANDIDATE
    assert rec.recommended_value is not None
    assert 27.5 <= rec.recommended_value <= 28.5
    assert rec.method == EstimationMethod.COMBINED_TEMPORAL_SPATIAL
    assert rec.uncertainty is not None
    assert rec.uncertainty.supporting_neighbor_count == 2
    assert "degraded" in rec.operator_summary.lower() or "candidate" in rec.operator_summary.lower()


def test_insufficient_evidence_when_no_neighbors_and_no_history():
    engine = CorrectionRecommendationEngine()

    rec = engine.recommend_for_variable(
        station_id="TARGET",
        timestamp="2026-09-17T12:00:00Z",
        target_variable="temperature_c",
        observed_value=35.0,
        decision_type=HybridDecisionType.PROBABLE_SENSOR_ANOMALY,
        temporal_history=[],
        neighbor_observations=[],
    )

    assert rec.status == RecommendationStatus.INSUFFICIENT_EVIDENCE
    assert rec.recommended_value is None
    assert "insufficient" in rec.operator_summary.lower()
