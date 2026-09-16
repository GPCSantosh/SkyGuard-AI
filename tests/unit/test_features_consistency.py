"""Unit tests for ConsistencyExtractor (persistence, deviations, multivariate)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from ml.features.consistency import ConsistencyExtractor
from ml.features.rolling import RollingWindowExtractor


def test_persistence_frozen_sensor_counting() -> None:
    timestamps = pd.date_range("2024-01-01 00:00:00", periods=6, freq="10min", tz="UTC")
    # Values: 20.0, 20.0, 20.0, 20.0, 25.0, 25.0
    temps = [20.0, 20.0, 20.0, 20.0, 25.0, 25.0]
    df = pd.DataFrame({"timestamp": timestamps, "temperature_c": temps})

    extractor = ConsistencyExtractor(parameters=["temperature_c"])
    res = extractor.extract_features(df)

    assert "temperature_c_consecutive_unchanged_count" in res.columns
    assert "temperature_c_duration_unchanged_minutes" in res.columns

    # Check run counts
    counts = res["temperature_c_consecutive_unchanged_count"].tolist()
    assert counts == [1, 2, 3, 4, 1, 2]

    # Check duration unchanged
    durations = res["temperature_c_duration_unchanged_minutes"].tolist()
    assert durations == [0.0, 10.0, 20.0, 30.0, 0.0, 10.0]


def test_deviation_and_zscore_features() -> None:
    timestamps = pd.date_range("2024-01-01 00:00:00", periods=5, freq="1h", tz="UTC")
    df = pd.DataFrame({
        "timestamp": timestamps,
        "temperature_c": [10.0, 12.0, 14.0, 16.0, 18.0],
        "temperature_c_rolling_mean_1h": [10.0, 11.0, 13.0, 15.0, 17.0],
        "temperature_c_rolling_std_1h": [0.0, 1.414, 1.414, 1.414, 1.414],
    })

    extractor = ConsistencyExtractor(
        parameters=["temperature_c"],
        rolling_reference_window="1h",
    )
    res = extractor.extract_features(df)

    assert "temperature_c_deviation_from_mean_1h" in res.columns
    assert "temperature_c_zscore_1h" in res.columns

    # Row 1: X = 12, mean = 11 -> dev = 1.0
    assert pytest.approx(res.at[1, "temperature_c_deviation_from_mean_1h"], abs=1e-2) == 1.0
    assert pytest.approx(res.at[1, "temperature_c_zscore_1h"], abs=1e-2) == (1.0 / 1.414)
