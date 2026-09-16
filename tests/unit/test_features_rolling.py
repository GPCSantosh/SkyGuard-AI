"""Unit tests for time-aware rolling window extractor."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from ml.features.rolling import RollingWindowExtractor


def test_rolling_window_extractor_regular_cadence() -> None:
    # 5-minute intervals
    timestamps = pd.date_range("2024-01-01 00:00:00", periods=12, freq="5min", tz="UTC")
    temps = [20.0, 21.0, 22.0, 23.0, 24.0, 25.0, 26.0, 27.0, 28.0, 29.0, 30.0, 31.0]
    df = pd.DataFrame({"timestamp": timestamps, "temperature_c": temps})

    extractor = RollingWindowExtractor(
        time_windows=["15min", "30min", "1h"],
        lag_steps=[1, 2],
        parameters=["temperature_c"],
    )
    res = extractor.extract_features(df)

    assert "temperature_c_lag_1" in res.columns
    assert "temperature_c_lag_2" in res.columns
    assert "temperature_c_rolling_mean_30m" in res.columns

    # Lag checks
    assert pd.isna(res.at[0, "temperature_c_lag_1"])
    assert res.at[1, "temperature_c_lag_1"] == 20.0
    assert res.at[2, "temperature_c_lag_2"] == 20.0

    # At row 6 (00:30), 30min window (closed='right') covers (00:00, 00:30] (6 observations: 21..26)
    # mean = (21+22+23+24+25+26)/6 = 23.5
    assert pytest.approx(res.at[6, "temperature_c_rolling_mean_30m"], abs=1e-2) == 23.5


def test_rolling_window_irregular_timestamps() -> None:
    # Irregular intervals: 0 min, 30 min, 35 min, 120 min
    timestamps = pd.to_datetime([
        "2024-01-01 00:00:00Z",
        "2024-01-01 00:30:00Z",
        "2024-01-01 00:35:00Z",
        "2024-01-01 02:00:00Z",
    ])
    temps = [20.0, 22.0, 24.0, 30.0]
    df = pd.DataFrame({"timestamp": timestamps, "temperature_c": temps})

    extractor = RollingWindowExtractor(
        time_windows=["30min", "1h"],
        parameters=["temperature_c"],
    )
    res = extractor.extract_features(df)

    # At 00:35, 30min window covers (00:05, 00:35] -> includes 00:30 and 00:35 (22.0 and 24.0)
    # mean = 23.0, count = 2
    assert res.at[2, "temperature_c_rolling_count_30m"] == 2
    assert pytest.approx(res.at[2, "temperature_c_rolling_mean_30m"], abs=1e-2) == 23.0

    # At 02:00, 30min window covers (01:30, 02:00] -> includes only 02:00 (30.0)
    assert res.at[3, "temperature_c_rolling_count_30m"] == 1
    assert res.at[3, "temperature_c_rolling_mean_30m"] == 30.0
