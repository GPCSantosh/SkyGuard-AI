"""Unit tests for spatial neighbor comparison and temporal causality."""

from datetime import datetime, timezone
import numpy as np
import pandas as pd
import pytest

from ml.explainability.neighbor_comparator import NeighborComparator
from ml.explainability.schema import NeighborComparison


def test_neighbor_comparison_dict_input():
    """Test neighbor comparison with simple dictionary input."""
    comparator = NeighborComparator(alignment_window_minutes=15.0)

    neighbor_data = {
        "AWS_002": 24.5,
        "AWS_003": 25.0,
        "AWS_004": 25.5,
        "AWS_005": 24.8,
    }

    comp = comparator.compare_neighbors(
        target_station_id="AWS_001",
        target_timestamp="2026-09-17T12:00:00Z",
        target_variable="temperature_c",
        target_value=28.5,  # +3.6°C higher than median (24.9)
        neighbor_data=neighbor_data,
    )

    assert comp.target_value == 28.5
    assert comp.neighbor_median == 24.9
    assert comp.target_deviation == 3.6
    assert comp.total_valid_neighbors == 4
    # With tolerance 2.0, no neighbors agree with 28.5
    assert comp.agreeing_neighbor_count == 0
    assert comp.temporal_alignment_status == "ALIGNED"


def test_neighbor_comparison_dataframe_causality():
    """Test that future observations in dataframe are strictly excluded to preserve causality."""
    comparator = NeighborComparator(alignment_window_minutes=15.0)

    # DataFrame containing past, present, and future observations
    t_target = "2026-09-17T12:00:00Z"
    records = [
        # Past (within 15m window)
        {"station_id": "AWS_002", "timestamp": "2026-09-17T11:55:00Z", "temperature_c": 22.0},
        {"station_id": "AWS_003", "timestamp": "2026-09-17T12:00:00Z", "temperature_c": 22.2},
        # Stale (older than 15m)
        {"station_id": "AWS_004", "timestamp": "2026-09-17T11:30:00Z", "temperature_c": 15.0},
        # Future (after 12:00) -> MUST BE EXCLUDED
        {"station_id": "AWS_005", "timestamp": "2026-09-17T12:05:00Z", "temperature_c": 99.0},
    ]
    df = pd.DataFrame(records)

    comp = comparator.compare_neighbors(
        target_station_id="AWS_001",
        target_timestamp=t_target,
        target_variable="temperature_c",
        target_value=22.1,
        neighbor_data=df,
    )

    # Only AWS_002 and AWS_003 should be included
    assert "AWS_005" not in comp.neighbor_values
    assert "AWS_004" not in comp.neighbor_values
    assert comp.total_valid_neighbors == 2
    assert comp.neighbor_median == 22.1
    assert comp.target_deviation == 0.0
    assert comp.agreeing_neighbor_count == 2
    assert comp.temporal_alignment_status == "SPARSE"


def test_neighbor_comparison_edge_cases():
    """Test edge cases: zero neighbors, NaN neighbor values, target station excluded."""
    comparator = NeighborComparator()

    # 1. Zero neighbors
    comp_empty = comparator.compare_neighbors(
        target_station_id="AWS_001",
        target_timestamp="2026-09-17T12:00:00Z",
        target_variable="temperature_c",
        target_value=25.0,
        neighbor_data={},
    )
    assert comp_empty.total_valid_neighbors == 0
    assert comp_empty.neighbor_median is None
    assert comp_empty.target_deviation is None
    assert comp_empty.temporal_alignment_status == "NO_NEIGHBORS"

    # 2. Target station passed in neighbor dict (must be ignored)
    comp_self = comparator.compare_neighbors(
        target_station_id="AWS_001",
        target_timestamp="2026-09-17T12:00:00Z",
        target_variable="temperature_c",
        target_value=25.0,
        neighbor_data={"AWS_001": 25.0, "AWS_002": np.nan},
    )
    assert "AWS_001" not in comp_self.neighbor_values
    assert comp_self.total_valid_neighbors == 0
