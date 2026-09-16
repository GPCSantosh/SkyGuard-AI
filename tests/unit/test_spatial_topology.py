"""Unit tests for spatial network topology and geodesic metrics."""

from __future__ import annotations

import math
from pathlib import Path
import pytest
import pandas as pd

from ml.spatial.topology import (
    NeighborLink,
    SpatialNetworkTopology,
    StationNode,
    haversine_distance_km,
    initial_compass_bearing_deg,
)


def test_haversine_distance_known_points():
    """Verify Haversine formula against known meteorological ground coordinates."""
    # Delhi Safdarjung (28.5845° N, 77.2058° E) to Delhi Palam (28.5665° N, 77.1031° E)
    # Expected distance: ~10.2 km
    dist_delhi = haversine_distance_km(28.5845, 77.2058, 28.5665, 77.1031)
    assert not math.isnan(dist_delhi)
    assert 9.5 < dist_delhi < 11.0

    # Delhi to Mumbai (~1150 km)
    dist_delhi_mumbai = haversine_distance_km(28.5845, 77.2058, 19.1167, 72.8500)
    assert 1100.0 < dist_delhi_mumbai < 1200.0

    # Identical coordinates -> exactly 0.0
    assert haversine_distance_km(28.5, 77.2, 28.5, 77.2) == 0.0


def test_haversine_invalid_coordinates():
    """Verify invalid or out-of-bounds coordinates return NaN safely."""
    assert math.isnan(haversine_distance_km(95.0, 77.0, 28.0, 77.0))
    assert math.isnan(haversine_distance_km(28.0, 190.0, 28.0, 77.0))
    assert math.isnan(haversine_distance_km(float("nan"), 77.0, 28.0, 77.0))


def test_initial_compass_bearing_calculation():
    """Verify compass bearing calculation for cardinal directions."""
    # North: from (0, 0) to (10, 0) -> 0°
    b_north = initial_compass_bearing_deg(0.0, 0.0, 10.0, 0.0)
    assert abs(b_north - 0.0) < 1e-3

    # East: from (0, 0) to (0, 10) -> 90°
    b_east = initial_compass_bearing_deg(0.0, 0.0, 0.0, 10.0)
    assert abs(b_east - 90.0) < 1e-3

    # South: from (10, 0) to (0, 0) -> 180°
    b_south = initial_compass_bearing_deg(10.0, 0.0, 0.0, 0.0)
    assert abs(b_south - 180.0) < 1e-3

    # West: from (0, 10) to (0, 0) -> 270°
    b_west = initial_compass_bearing_deg(0.0, 10.0, 0.0, 0.0)
    assert abs(b_west - 270.0) < 1e-3


def test_spatial_network_topology_from_yaml():
    """Verify loading topology graph from SkyGuard stations.yaml."""
    config_path = Path("configs/stations.yaml")
    if not config_path.exists():
        pytest.skip("stations.yaml not found.")

    topology = SpatialNetworkTopology.from_yaml(config_path)
    assert len(topology.stations) >= 8

    # Query nearest neighbors for Delhi Safdarjung (42182099999)
    neighbors = topology.get_neighbors("42182099999", max_distance_km=600.0, max_neighbors=5)
    assert len(neighbors) > 0
    # First neighbor must be Palam (42181099999) ~10 km away
    assert neighbors[0].neighbor_station_id == "42181099999"
    assert neighbors[0].distance_km < 20.0
    assert 0.0 <= neighbors[0].bearing_deg <= 360.0


def test_spatial_network_topology_from_dataframe():
    """Verify building topology dynamically from observation DataFrame."""
    df = pd.DataFrame([
        {"station_id": "STN_A", "latitude": 28.5, "longitude": 77.2, "elevation_m": 210.0},
        {"station_id": "STN_B", "latitude": 28.6, "longitude": 77.3, "elevation_m": 220.0},
        {"station_id": "STN_C", "latitude": 19.1, "longitude": 72.8, "elevation_m": 15.0},
    ])
    topology = SpatialNetworkTopology.from_dataframe(df)
    assert len(topology.stations) == 3

    neighbors_a = topology.get_neighbors("STN_A", max_distance_km=50.0)
    assert len(neighbors_a) == 1
    assert neighbors_a[0].neighbor_station_id == "STN_B"


def test_spatial_topology_serialization(tmp_path: Path):
    """Verify JSON serialization and deserialization of network graph."""
    nodes = {
        "S1": StationNode(station_id="S1", name="Stn 1", latitude=28.0, longitude=77.0, elevation_m=200.0),
        "S2": StationNode(station_id="S2", name="Stn 2", latitude=28.1, longitude=77.1, elevation_m=210.0),
    }
    topo1 = SpatialNetworkTopology(stations=nodes)
    json_path = tmp_path / "network_topology.json"
    topo1.save_json(json_path)

    assert json_path.exists()
    topo2 = SpatialNetworkTopology.load_json(json_path)
    assert len(topo2.stations) == 2
    assert "S1" in topo2.stations
    assert "S2" in topo2.stations
