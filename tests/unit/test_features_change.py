"""Unit tests for RateOfChangeExtractor."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from ml.features.change import RateOfChangeExtractor


def test_rate_of_change_regular_and_edge_cases() -> None:
    # Row 0: Initial
    # Row 1: 5 mins later, +2.5 deg (rate = 0.5 deg/min)
    # Row 2: 0 mins later (duplicate timestamp), +1.0 deg -> div-by-zero check!
    # Row 3: 10 mins later, -5.0 deg (rate = -0.5 deg/min)
    timestamps = pd.to_datetime([
        "2024-01-01 00:00:00Z",
        "2024-01-01 00:05:00Z",
        "2024-01-01 00:05:00Z",
        "2024-01-01 00:15:00Z",
    ])
    temps = [20.0, 22.5, 23.5, 18.5]
    df = pd.DataFrame({"timestamp": timestamps, "temperature_c": temps})

    extractor = RateOfChangeExtractor(parameters=["temperature_c"])
    res = extractor.extract_features(df, sort_by_time=False)

    # Row 0 (no previous obs)
    assert pd.isna(res.at[0, "temperature_c_delta"])
    assert pd.isna(res.at[0, "temperature_c_rate_per_minute"])

    # Row 1 (5 mins later, delta = 2.5)
    assert pytest.approx(res.at[1, "temperature_c_delta"], abs=1e-3) == 2.5
    assert pytest.approx(res.at[1, "temperature_c_rate_per_minute"], abs=1e-3) == 0.5
    assert pytest.approx(res.at[1, "temperature_c_rate_per_5min"], abs=1e-3) == 2.5
    assert pytest.approx(res.at[1, "temperature_c_rate_per_hour"], abs=1e-3) == 30.0

    # Row 2 (0 mins later -> elapsed = 0.0 -> rate should be NaN, not raise ZeroDivisionError)
    assert res.at[2, "elapsed_minutes"] == 0.0
    assert pd.isna(res.at[2, "temperature_c_rate_per_minute"])

    # Row 3 (10 mins later, delta = 18.5 - 23.5 = -5.0)
    assert pytest.approx(res.at[3, "temperature_c_delta"], abs=1e-3) == -5.0
    assert pytest.approx(res.at[3, "temperature_c_rate_per_minute"], abs=1e-3) == -0.5
