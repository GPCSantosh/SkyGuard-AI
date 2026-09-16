"""Unit tests for spatial edge cases and boundary conditions."""

from __future__ import annotations

import math
import pandas as pd
import pytest

from ml.spatial.engine import SpatialContextEngine
from ml.spatial.schema import SpatialContextCategory
from ml.spatial.topology import SpatialNetworkTopology, StationNode


def test_edge_case_zero_neighbors():
    """Verify an isolated station with no neighbors returns INSUFFICIENT_CONTEXT."""
    stations = {
        "SOLO_STN": StationNode(station_id="SOLO_STN", latitude=28.5, longitude=77.2, elevation_m=200.0)
    }
    engine = SpatialContextEngine(topology=SpatialNetworkTopology(stations=stations))
    ev = engine.evaluate_observation(
        target_station_id="SOLO_STN",
        target_timestamp="2024-06-01T12:00:00Z",
        target_values={"temperature_c": 25.0},
        neighbor_data_pool=[],
    )
    assert ev.configured_neighbors_count == 0
    assert ev.valid_neighbors_count == 0
    assert ev.context_category == SpatialContextCategory.INSUFFICIENT_CONTEXT


def test_edge_case_one_neighbor():
    """Verify behavior with exactly 1 neighbor."""
    stations = {
        "STN_A": StationNode(station_id="STN_A", latitude=28.5, longitude=77.2, elevation_m=200.0),
        "STN_B": StationNode(station_id="STN_B", latitude=28.6, longitude=77.2, elevation_m=200.0),
    }
    # Set min_valid_neighbors = 1
    engine = SpatialContextEngine(topology=SpatialNetworkTopology(stations=stations), min_valid_neighbors=1)
    ev = engine.evaluate_observation(
        target_station_id="STN_A",
        target_timestamp="2024-06-01T12:00:00Z",
        target_values={"temperature_c": 25.0},
        neighbor_data_pool=[{"station_id": "STN_B", "timestamp": "2024-06-01T12:00:00Z", "temperature_c": 25.2}],
    )
    assert ev.configured_neighbors_count == 1
    assert ev.valid_neighbors_count == 1
    assert ev.temperature_consensus.neighbor_count == 1
    assert ev.temperature_consensus.neighbor_std == 0.0
    assert ev.context_category in (SpatialContextCategory.REGIONAL_PATTERN, SpatialContextCategory.LOCAL_CLUSTER)


def test_edge_case_nan_neighbor_value():
    """Verify NaN values in neighbor observations do not crash the engine or corrupt statistics."""
    stations = {
        "STN_A": StationNode(station_id="STN_A", latitude=28.5, longitude=77.2, elevation_m=200.0),
        "STN_B": StationNode(station_id="STN_B", latitude=28.6, longitude=77.2, elevation_m=200.0),
        "STN_C": StationNode(station_id="STN_C", latitude=28.4, longitude=77.2, elevation_m=200.0),
    }
    engine = SpatialContextEngine(topology=SpatialNetworkTopology(stations=stations), min_valid_neighbors=1)
    ev = engine.evaluate_observation(
        target_station_id="STN_A",
        target_timestamp="2024-06-01T12:00:00Z",
        target_values={"temperature_c": 25.0},
        neighbor_data_pool=[
            {"station_id": "STN_B", "timestamp": "2024-06-01T12:00:00Z", "temperature_c": float("nan")},
            {"station_id": "STN_C", "timestamp": "2024-06-01T12:00:00Z", "temperature_c": 25.5},
        ],
    )
    assert ev.temperature_consensus.neighbor_count == 1
    assert ev.temperature_consensus.neighbor_mean == 25.5


def test_edge_case_duplicate_coordinates():
    """Verify identical station coordinates return distance 0.0 without division errors."""
    stations = {
        "CO_STN_1": StationNode(station_id="CO_STN_1", latitude=28.5, longitude=77.2, elevation_m=200.0),
        "CO_STN_2": StationNode(station_id="CO_STN_2", latitude=28.5, longitude=77.2, elevation_m=200.0),
    }
    topo = SpatialNetworkTopology(stations=stations)
    links = topo.get_neighbors("CO_STN_1")
    assert len(links) == 1
    assert links[0].distance_km == 0.0

    engine = SpatialContextEngine(topology=topo, min_valid_neighbors=1)
    ev = engine.evaluate_observation(
        target_station_id="CO_STN_1",
        target_timestamp="2024-06-01T12:00:00Z",
        target_values={"temperature_c": 30.0},
        neighbor_data_pool=[{"station_id": "CO_STN_2", "timestamp": "2024-06-01T12:00:00Z", "temperature_c": 30.0}],
    )
    # IDW should clamp min distance to 1.0 km to avoid division by zero
    assert ev.temperature_consensus.idw_expected_value == 30.0


def test_edge_case_extremely_distant_neighbors():
    """Verify neighbors exceeding max_distance_km are excluded."""
    stations = {
        "DELHI": StationNode(station_id="DELHI", latitude=28.58, longitude=77.20, elevation_m=215.0),
        "CHENNAI": StationNode(station_id="CHENNAI", latitude=12.99, longitude=80.18, elevation_m=16.0), # ~1750 km away
    }
    topo = SpatialNetworkTopology(stations=stations)
    links = topo.get_neighbors("DELHI", max_distance_km=600.0)
    assert len(links) == 0


def test_edge_case_one_outlier_neighbor():
    """Verify one corrupted neighbor among multiple healthy neighbors does not mislead the engine."""
    stations = {
        "TARGET": StationNode(station_id="TARGET", latitude=28.50, longitude=77.20, elevation_m=200.0),
        "N1": StationNode(station_id="N1", latitude=28.51, longitude=77.21, elevation_m=200.0),
        "N2": StationNode(station_id="N2", latitude=28.49, longitude=77.19, elevation_m=200.0),
        "N3": StationNode(station_id="N3", latitude=28.52, longitude=77.22, elevation_m=200.0),
        "N4_CORRUPT": StationNode(station_id="N4_CORRUPT", latitude=28.48, longitude=77.18, elevation_m=200.0),
    }
    engine = SpatialContextEngine(topology=SpatialNetworkTopology(stations=stations), min_valid_neighbors=3)

    t_eval = "2024-06-01T12:00:00Z"
    target_vals = {"temperature_c": 30.0}
    # 3 healthy neighbors reporting 30.0°C, 1 corrupted neighbor reporting 99.0°C
    pool = [
        {"station_id": "N1", "timestamp": t_eval, "temperature_c": 30.1},
        {"station_id": "N2", "timestamp": t_eval, "temperature_c": 29.9},
        {"station_id": "N3", "timestamp": t_eval, "temperature_c": 30.0},
        {"station_id": "N4_CORRUPT", "timestamp": t_eval, "temperature_c": 99.0},
    ]

    ev = engine.evaluate_observation("TARGET", t_eval, target_vals, pool)
    # Median is robust to the outlier
    assert abs(ev.temperature_consensus.neighbor_median - 30.0) < 0.2
    assert ev.temperature_consensus.fraction_similar == 0.75  # 3 out of 4 agree
    assert ev.context_category == SpatialContextCategory.REGIONAL_PATTERN
