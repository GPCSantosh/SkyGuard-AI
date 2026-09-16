"""Unit tests for Spatial & Synoptic Context Engine core logic."""

from __future__ import annotations

import math
import pandas as pd
import pytest

from ml.spatial.engine import SpatialContextEngine
from ml.spatial.schema import SpatialContextCategory
from ml.spatial.topology import SpatialNetworkTopology, StationNode


@pytest.fixture
def test_topology() -> SpatialNetworkTopology:
    stations = {
        "TARGET": StationNode(station_id="TARGET", name="Target Station", latitude=28.50, longitude=77.20, elevation_m=200.0),
        "NEIGHBOR_1": StationNode(station_id="NEIGHBOR_1", name="Near North", latitude=28.60, longitude=77.20, elevation_m=205.0), # ~11 km
        "NEIGHBOR_2": StationNode(station_id="NEIGHBOR_2", name="Near East", latitude=28.50, longitude=77.30, elevation_m=195.0),  # ~10 km
        "NEIGHBOR_3": StationNode(station_id="NEIGHBOR_3", name="Near South", latitude=28.40, longitude=77.20, elevation_m=210.0), # ~11 km
        "FAR_STN": StationNode(station_id="FAR_STN", name="Distant", latitude=20.00, longitude=75.00, elevation_m=500.0),        # ~960 km
    }
    return SpatialNetworkTopology(stations=stations)


def test_temporal_alignment_and_stale_data(test_topology):
    """Verify observations within tolerance are accepted, while older ones are flagged STALE."""
    engine = SpatialContextEngine(
        topology=test_topology,
        max_distance_km=50.0,
        temporal_tolerance_minutes=30.0,
        enable_causal_mode=True,
    )

    t_eval = "2024-06-01T12:00:00Z"
    target_vals = {"temperature_c": 30.0, "relative_humidity_pct": 50.0, "sea_level_pressure_hpa": 1005.0}

    # Pool containing on-time, slightly delayed, and stale observations
    pool = [
        # NEIGHBOR_1: exactly on time (0 min delta) -> Valid
        {"station_id": "NEIGHBOR_1", "timestamp": "2024-06-01T12:00:00Z", "temperature_c": 29.8, "relative_humidity_pct": 51.0, "sea_level_pressure_hpa": 1005.2},
        # NEIGHBOR_2: 20 min prior (within 30m tolerance) -> Valid
        {"station_id": "NEIGHBOR_2", "timestamp": "2024-06-01T11:40:00Z", "temperature_c": 30.2, "relative_humidity_pct": 49.0, "sea_level_pressure_hpa": 1004.9},
        # NEIGHBOR_3: 2 hours prior (120 min > 30m tolerance) -> STALE
        {"station_id": "NEIGHBOR_3", "timestamp": "2024-06-01T10:00:00Z", "temperature_c": 25.0, "relative_humidity_pct": 70.0, "sea_level_pressure_hpa": 1010.0},
    ]

    evidence = engine.evaluate_observation("TARGET", t_eval, target_vals, pool)

    assert evidence.configured_neighbors_count == 3  # N1, N2, N3 within 50km
    assert evidence.valid_neighbors_count == 2       # N1, N2 valid
    assert evidence.stale_neighbors_count == 1       # N3 is stale
    assert evidence.temperature_consensus.neighbor_count == 2
    # Stale 25.0°C from N3 must NOT contaminate neighbor mean
    assert abs(evidence.temperature_consensus.neighbor_mean - 30.0) < 0.2


def test_causality_forward_time_exclusion(test_topology):
    """Verify in causal mode, observations with t > target_t are strictly excluded."""
    engine = SpatialContextEngine(
        topology=test_topology,
        max_distance_km=50.0,
        temporal_tolerance_minutes=30.0,
        enable_causal_mode=True,
    )

    t_eval = "2024-06-01T12:00:00Z"
    target_vals = {"temperature_c": 30.0, "relative_humidity_pct": 50.0, "sea_level_pressure_hpa": 1005.0}

    # Pool with a past observation and a future observation for NEIGHBOR_1
    pool_past_only = [
        {"station_id": "NEIGHBOR_1", "timestamp": "2024-06-01T12:00:00Z", "temperature_c": 30.0},
        {"station_id": "NEIGHBOR_2", "timestamp": "2024-06-01T12:00:00Z", "temperature_c": 30.0},
    ]
    ev1 = engine.evaluate_observation("TARGET", t_eval, target_vals, pool_past_only)

    # Now add future observation at 12:10 UTC (t > 12:00 UTC) with extreme corrupted value
    pool_with_future = list(pool_past_only) + [
        {"station_id": "NEIGHBOR_1", "timestamp": "2024-06-01T12:10:00Z", "temperature_c": 99.0},
    ]
    ev2 = engine.evaluate_observation("TARGET", t_eval, target_vals, pool_with_future)

    # Future 99.0°C must NOT leak into the 12:00 evaluation
    assert ev1.temperature_consensus.neighbor_mean == ev2.temperature_consensus.neighbor_mean
    assert ev1.context_category == ev2.context_category


def test_pressure_normalization_in_spatial_engine(test_topology):
    """Verify raw station pressure is automatically normalized to SLP using elevation."""
    engine = SpatialContextEngine(topology=test_topology, max_distance_km=50.0)

    t_eval = "2024-06-01T12:00:00Z"
    # Target has only station_pressure_hpa (980 hPa at 200m elevation, 30°C -> approx 1002.5 hPa SLP)
    target_vals = {
        "temperature_c": 30.0,
        "station_pressure_hpa": 980.0,
        "elevation_m": 200.0,
    }

    pool = [
        {"station_id": "NEIGHBOR_1", "timestamp": t_eval, "temperature_c": 30.0, "station_pressure_hpa": 980.0, "elevation_m": 205.0},
        {"station_id": "NEIGHBOR_2", "timestamp": t_eval, "temperature_c": 30.0, "station_pressure_hpa": 980.0, "elevation_m": 195.0},
    ]

    evidence = engine.evaluate_observation("TARGET", t_eval, target_vals, pool)
    assert evidence.sea_level_pressure_consensus.neighbor_count == 2
    assert evidence.sea_level_pressure_consensus.target_value is not None
    assert 1000.0 < evidence.sea_level_pressure_consensus.target_value < 1005.0


def test_consensus_statistics_and_zero_variance(test_topology):
    """Verify statistical metrics (mean, median, std, z-score) handle zero-variance safely."""
    engine = SpatialContextEngine(topology=test_topology, max_distance_km=50.0)

    t_eval = "2024-06-01T12:00:00Z"
    # Target: 30.0, all neighbors exactly 30.0 (std = 0.0)
    target_vals = {"temperature_c": 30.0, "relative_humidity_pct": 50.0, "sea_level_pressure_hpa": 1005.0}
    pool = [
        {"station_id": "NEIGHBOR_1", "timestamp": t_eval, "temperature_c": 30.0, "relative_humidity_pct": 50.0, "sea_level_pressure_hpa": 1005.0},
        {"station_id": "NEIGHBOR_2", "timestamp": t_eval, "temperature_c": 30.0, "relative_humidity_pct": 50.0, "sea_level_pressure_hpa": 1005.0},
    ]

    evidence = engine.evaluate_observation("TARGET", t_eval, target_vals, pool)
    tc = evidence.temperature_consensus
    assert tc.neighbor_mean == 30.0
    assert tc.neighbor_std == 0.0
    assert tc.target_minus_mean == 0.0
    assert tc.target_zscore == 0.0
    assert tc.fraction_similar == 1.0


def test_idw_distance_weighting(test_topology):
    """Verify Inverse Distance Weighting gives closer stations proportionally higher weight."""
    engine = SpatialContextEngine(topology=test_topology, max_distance_km=50.0, idw_power=1.0)

    t_eval = "2024-06-01T12:00:00Z"
    target_vals = {"temperature_c": 25.0}

    # NEIGHBOR_2 is closer (~10.8 km) with Temp=20°C, NEIGHBOR_1 is slightly farther (~11.1 km) with Temp=30°C
    pool = [
        {"station_id": "NEIGHBOR_1", "timestamp": t_eval, "temperature_c": 30.0},
        {"station_id": "NEIGHBOR_2", "timestamp": t_eval, "temperature_c": 20.0},
    ]

    evidence = engine.evaluate_observation("TARGET", t_eval, target_vals, pool)
    tc = evidence.temperature_consensus
    assert tc.idw_expected_value is not None
    # IDW value must be between 20 and 30
    assert 20.0 < tc.idw_expected_value < 30.0
