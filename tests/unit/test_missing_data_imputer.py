"""Unit tests for MissingDataImputer."""

import math
import pytest
from datetime import datetime, timezone

from ml.imputation.imputer import MissingDataImputer
from ml.imputation.schema import EstimationMethod, ImputationStatus
from ml.spatial.engine import SpatialContextEngine
from ml.spatial.topology import SpatialNetworkTopology, StationNode


@pytest.fixture
def sample_topology():
    topo = SpatialNetworkTopology()
    topo.add_station(StationNode(station_id="TARGET", name="Target Station", latitude=28.6139, longitude=77.2090, elevation_m=216.0))
    topo.add_station(StationNode(station_id="N1", name="Neighbor 1", latitude=28.5800, longitude=77.2300, elevation_m=215.0))
    topo.add_station(StationNode(station_id="N2", name="Neighbor 2", latitude=28.6500, longitude=77.1900, elevation_m=220.0))
    return topo


def test_short_gap_causal_imputation():
    imputer = MissingDataImputer(max_interpolation_gap_minutes=60.0)
    history = [20.0, 20.5, 21.0, 21.5]
    
    rec = imputer.impute_missing_value(
        station_id="STN_001",
        timestamp="2026-09-17T12:00:00Z",
        target_variable="temperature_c",
        gap_duration_minutes=5.0,
        consecutive_missing_steps=1,
        temporal_history=history,
        mode="causal",
    )
    assert rec.status == ImputationStatus.IMPUTED
    assert rec.imputed_value is not None
    # Slope is +0.5 per step, damped slope extrapolation around 21.5 + 0.25 = 21.75
    assert 21.0 <= rec.imputed_value <= 22.5
    assert rec.method == EstimationMethod.CAUSAL_TEMPORAL_INTERPOLATION
    assert rec.is_causal is True
    assert rec.uncertainty is not None


def test_long_gap_safety_rejection():
    imputer = MissingDataImputer(max_interpolation_gap_minutes=60.0)
    history = [20.0, 21.0, 22.0]
    
    # 75 minute gap exceeds 60m threshold
    rec = imputer.impute_missing_value(
        station_id="STN_001",
        timestamp="2026-09-17T12:00:00Z",
        target_variable="temperature_c",
        gap_duration_minutes=75.0,
        consecutive_missing_steps=15,
        temporal_history=history,
    )
    assert rec.status == ImputationStatus.NOT_IMPUTABLE
    assert rec.imputed_value is None
    assert "exceeds maximum allowed safety limit" in rec.reason
    assert rec.method == EstimationMethod.NO_ESTIMATE


def test_retrospective_interpolation_mode():
    imputer = MissingDataImputer(max_interpolation_gap_minutes=60.0)
    past = [20.0, 20.0]
    future = [30.0, 30.0]
    
    rec = imputer.impute_missing_value(
        station_id="STN_001",
        timestamp="2026-09-17T12:00:00Z",
        target_variable="temperature_c",
        gap_duration_minutes=10.0,
        consecutive_missing_steps=2,
        temporal_history=past,
        subsequent_history=future,
        mode="retrospective",
    )
    assert rec.status == ImputationStatus.IMPUTED
    assert rec.is_causal is False
    assert rec.method == EstimationMethod.RETROSPECTIVE_INTERPOLATION
    # 0.5 * (20.0 + 30.0) = 25.0
    assert rec.imputed_value == 25.0


def test_neighbor_assisted_imputation(sample_topology):
    spatial_engine = SpatialContextEngine(topology=sample_topology)
    imputer = MissingDataImputer(spatial_engine=spatial_engine)

    neighbors = [
        {"station_id": "N1", "timestamp": "2026-09-17T12:00:00Z", "temperature_c": 28.0},
        {"station_id": "N2", "timestamp": "2026-09-17T12:00:00Z", "temperature_c": 28.4},
    ]

    rec = imputer.impute_missing_value(
        station_id="TARGET",
        timestamp="2026-09-17T12:00:00Z",
        target_variable="temperature_c",
        gap_duration_minutes=5.0,
        consecutive_missing_steps=1,
        temporal_history=[],  # Zero temporal history
        neighbor_observations=neighbors,
    )
    assert rec.status == ImputationStatus.IMPUTED
    assert rec.imputed_value is not None
    assert 27.9 <= rec.imputed_value <= 28.5
    assert rec.method == EstimationMethod.SPATIAL_IDW_CONSENSUS
    assert rec.uncertainty is not None
    assert rec.uncertainty.supporting_neighbor_count == 2


def test_impute_series_with_intermittent_gaps():
    imputer = MissingDataImputer(max_interpolation_gap_minutes=60.0)
    timestamps = [f"2026-09-17T12:{i:02d}:00Z" for i in range(0, 30, 5)]
    values = [25.0, 25.2, None, 25.6, None, None]  # 6 steps, with 1-step and 2-step gaps

    recs = imputer.impute_series(
        station_id="STN_001",
        timestamps=timestamps,
        values=values,
        target_variable="temperature_c",
        cadence_minutes=5.0,
    )
    assert len(recs) == 3  # 3 missing points
    for r in recs:
        assert r.status == ImputationStatus.IMPUTED
        assert r.imputed_value is not None
        assert 24.0 <= r.imputed_value <= 27.0
