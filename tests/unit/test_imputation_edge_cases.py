"""Unit tests for Imputation and Correction Edge Cases."""

import pytest
from datetime import datetime, timezone

from ml.decision.schema import HybridDecisionType
from ml.imputation.correction_engine import CorrectionRecommendationEngine
from ml.imputation.imputer import MissingDataImputer
from ml.imputation.schema import ImputationStatus, MethodQuality, RecommendationStatus
from ml.spatial.engine import SpatialContextEngine
from ml.spatial.topology import SpatialNetworkTopology, StationNode


@pytest.fixture
def test_topology():
    topo = SpatialNetworkTopology()
    topo.add_station(StationNode(station_id="STN_A", name="Station A", latitude=28.6, longitude=77.2, elevation_m=200.0))
    topo.add_station(StationNode(station_id="STN_B", name="Station B", latitude=28.62, longitude=77.22, elevation_m=205.0))
    topo.add_station(StationNode(station_id="STN_C", name="Station C", latitude=28.58, longitude=77.18, elevation_m=195.0))
    return topo


def test_edge_case_stale_neighbors(test_topology):
    spatial_engine = SpatialContextEngine(topology=test_topology, temporal_tolerance_minutes=15.0)
    engine = CorrectionRecommendationEngine(spatial_engine=spatial_engine)

    # Neighbors are 45 minutes stale (exceeding 15m tolerance)
    stale_neighbors = [
        {"station_id": "STN_B", "timestamp": "2026-09-17T11:15:00Z", "temperature_c": 25.0},
        {"station_id": "STN_C", "timestamp": "2026-09-17T11:15:00Z", "temperature_c": 25.2},
    ]

    rec = engine.recommend_for_variable(
        station_id="STN_A",
        timestamp="2026-09-17T12:00:00Z",
        target_variable="temperature_c",
        observed_value=35.0,
        decision_type=HybridDecisionType.PROBABLE_SENSOR_ANOMALY,
        neighbor_observations=stale_neighbors,
        temporal_history=[25.0, 25.1],
    )

    # Stale neighbors are ignored, relying only on temporal baseline
    assert rec.status == RecommendationStatus.REVIEW_RECOMMENDED
    assert rec.uncertainty.supporting_neighbor_count == 0


def test_edge_case_conflicting_high_variance_neighbors(test_topology):
    spatial_engine = SpatialContextEngine(topology=test_topology)
    engine = CorrectionRecommendationEngine(spatial_engine=spatial_engine)

    # Conflicting neighbors: one says 15°C, other says 35°C (high spatial spread)
    conflicting_neighbors = [
        {"station_id": "STN_B", "timestamp": "2026-09-17T12:00:00Z", "temperature_c": 15.0},
        {"station_id": "STN_C", "timestamp": "2026-09-17T12:00:00Z", "temperature_c": 35.0},
    ]

    rec = engine.recommend_for_variable(
        station_id="STN_A",
        timestamp="2026-09-17T12:00:00Z",
        target_variable="temperature_c",
        observed_value=45.0,
        decision_type=HybridDecisionType.PROBABLE_SENSOR_ANOMALY,
        neighbor_observations=conflicting_neighbors,
    )

    # High spatial uncertainty forces REVIEW_RECOMMENDED
    assert rec.status == RecommendationStatus.REVIEW_RECOMMENDED
    assert rec.uncertainty.standard_error > 3.0


def test_edge_case_frozen_sensor_flatline(test_topology):
    spatial_engine = SpatialContextEngine(topology=test_topology)
    engine = CorrectionRecommendationEngine(spatial_engine=spatial_engine)

    # Target station has flatlined at 20.0°C for hours while daytime heating brought neighbors to 32°C
    neighbors = [
        {"station_id": "STN_B", "timestamp": "2026-09-17T12:00:00Z", "temperature_c": 31.8},
        {"station_id": "STN_C", "timestamp": "2026-09-17T12:00:00Z", "temperature_c": 32.2},
    ]
    frozen_history = [20.0, 20.0, 20.0, 20.0, 20.0, 20.0]

    rec = engine.recommend_for_variable(
        station_id="STN_A",
        timestamp="2026-09-17T12:00:00Z",
        target_variable="temperature_c",
        observed_value=20.0,
        decision_type=HybridDecisionType.PROBABLE_SENSOR_ANOMALY,
        reason_codes=["PERSISTENT_VALUE", "LOCAL_SPATIAL_ISOLATION"],
        neighbor_observations=neighbors,
        temporal_history=frozen_history,
    )

    # Recommendation should shift towards actual dynamic neighbor baseline (~32°C) rather than stuck 20°C
    assert rec.recommended_value is not None
    assert rec.recommended_value > 25.0
    assert rec.status in (RecommendationStatus.CORRECTION_CANDIDATE, RecommendationStatus.REVIEW_RECOMMENDED)


def test_edge_case_gradual_sensor_drift(test_topology):
    spatial_engine = SpatialContextEngine(topology=test_topology)
    engine = CorrectionRecommendationEngine(spatial_engine=spatial_engine)

    # Target drifting upwards steadily to 38°C while neighbors are ~29°C
    neighbors = [
        {"station_id": "STN_B", "timestamp": "2026-09-17T12:00:00Z", "temperature_c": 29.0},
        {"station_id": "STN_C", "timestamp": "2026-09-17T12:00:00Z", "temperature_c": 29.4},
    ]
    drift_history = [32.0, 34.0, 36.0, 37.5]

    rec = engine.recommend_for_variable(
        station_id="STN_A",
        timestamp="2026-09-17T12:00:00Z",
        target_variable="temperature_c",
        observed_value=38.0,
        decision_type=HybridDecisionType.PROBABLE_SENSOR_ANOMALY,
        reason_codes=["LOCAL_SPATIAL_ISOLATION"],
        neighbor_observations=neighbors,
        temporal_history=drift_history,
    )

    assert rec.recommended_value is not None
    assert 28.5 <= rec.recommended_value <= 33.0


def test_edge_case_extreme_unphysical_observed_value(test_topology):
    spatial_engine = SpatialContextEngine(topology=test_topology)
    engine = CorrectionRecommendationEngine(spatial_engine=spatial_engine)

    neighbors = [
        {"station_id": "STN_B", "timestamp": "2026-09-17T12:00:00Z", "temperature_c": 22.0},
        {"station_id": "STN_C", "timestamp": "2026-09-17T12:00:00Z", "temperature_c": 22.5},
    ]

    # Extreme value (120°C hardware short circuit)
    rec = engine.recommend_for_variable(
        station_id="STN_A",
        timestamp="2026-09-17T12:00:00Z",
        target_variable="temperature_c",
        observed_value=120.0,
        decision_type=HybridDecisionType.PROBABLE_SENSOR_ANOMALY,
        reason_codes=["OUT_OF_RANGE_PHYSICAL"],
        neighbor_observations=neighbors,
    )

    assert rec.recommended_value is not None
    # Recommended value clamped to physical bounds and aligned with neighbors ~22°C
    assert 21.0 <= rec.recommended_value <= 24.0
    # Because departure (120 - 22 = 98) exceeds 15°C single-step limit, review is recommended
    assert rec.status == RecommendationStatus.REVIEW_RECOMMENDED
