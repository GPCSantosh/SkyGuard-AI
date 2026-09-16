"""Unit tests for SpatialNeighborExtractor and geodesic calculations."""

from __future__ import annotations

import math
import numpy as np
import pandas as pd
import pytest

from ml.features.spatial import SpatialNeighborExtractor, haversine_distance_km


def test_haversine_distance_calculation() -> None:
    # New Delhi Safdarjung (28.5845, 77.2058) to New Delhi Palam (28.5665, 77.1031) ~ 10 km
    d = haversine_distance_km(28.5845, 77.2058, 28.5665, 77.1031)
    assert 9.0 <= d <= 12.0

    # Same coordinates -> 0.0 km
    assert haversine_distance_km(28.5, 77.2, 28.5, 77.2) == 0.0

    # Invalid coordinates (lat > 90) -> NaN
    assert math.isnan(haversine_distance_km(95.0, 77.0, 28.0, 77.0))
    assert math.isnan(haversine_distance_km(float("nan"), 77.0, 28.0, 77.0))


def test_spatial_neighbors_multi_station() -> None:
    # 3 stations: A and B are close (10 km), C is very far (1500 km)
    station_metadata = {
        "STN_A": {"latitude": 28.5845, "longitude": 77.2058, "elevation_m": 214.0},
        "STN_B": {"latitude": 28.5665, "longitude": 77.1031, "elevation_m": 237.0},
        "STN_C": {"latitude": 12.9500, "longitude": 77.6667, "elevation_m": 888.0},  # Bengaluru ~ 1700km
    }

    extractor = SpatialNeighborExtractor(
        station_metadata=station_metadata,
        max_distance_km=100.0,
        max_neighbors=3,
    )

    # STN_A should have 1 neighbor (STN_B)
    neighbors_a = extractor.find_nearest_neighbors("STN_A")
    assert len(neighbors_a) == 1
    assert neighbors_a[0][0] == "STN_B"

    # STN_C should have 0 neighbors (within 100 km)
    neighbors_c = extractor.find_nearest_neighbors("STN_C")
    assert len(neighbors_c) == 0

    # Multi-station DataFrame extraction
    df = pd.DataFrame([
        {
            "station_id": "STN_A",
            "timestamp": "2024-01-01T12:00:00Z",
            "temperature_c": 25.0,
            "relative_humidity_pct": 50.0,
            "sea_level_pressure_hpa": 1012.0,
        },
        {
            "station_id": "STN_B",
            "timestamp": "2024-01-01T12:00:00Z",
            "temperature_c": 27.0,
            "relative_humidity_pct": 48.0,
            "sea_level_pressure_hpa": 1011.0,
        },
        {
            "station_id": "STN_C",
            "timestamp": "2024-01-01T12:00:00Z",
            "temperature_c": 30.0,
            "relative_humidity_pct": 60.0,
            "sea_level_pressure_hpa": 1010.0,
        },
    ])

    res = extractor.extract_features_multi_station(df)

    # STN_A: neighbor is STN_B (temp=27.0) -> delta = 25.0 - 27.0 = -2.0
    row_a = res[res["station_id"] == "STN_A"].iloc[0]
    assert row_a["spatial_neighbor_count"] == 1
    assert pytest.approx(row_a["spatial_temp_delta_from_neighbor_mean"], abs=1e-2) == -2.0

    # STN_C: 0 neighbors -> count = 0, delta = NaN
    row_c = res[res["station_id"] == "STN_C"].iloc[0]
    assert row_c["spatial_neighbor_count"] == 0
    assert pd.isna(row_c["spatial_temp_delta_from_neighbor_mean"])


def test_spatial_neighbors_edge_cases() -> None:
    # 1 station only: no neighbors
    station_metadata = {
        "ISLAND_STN": {"latitude": 8.3, "longitude": 73.15, "elevation_m": 2.0},
    }
    extractor = SpatialNeighborExtractor(station_metadata=station_metadata)
    assert extractor.find_nearest_neighbors("ISLAND_STN") == []
    assert extractor.find_nearest_neighbors("UNKNOWN_STN") == []
