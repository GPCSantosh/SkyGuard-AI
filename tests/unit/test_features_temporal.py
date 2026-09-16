"""Unit tests for temporal and cyclical feature extraction."""

from __future__ import annotations

from datetime import datetime, timezone
import numpy as np
import pandas as pd
import pytest

from ml.features.temporal import TemporalFeatureExtractor


def test_temporal_extractor_basic() -> None:
    data = {
        "timestamp": [
            "2024-01-01T00:00:00Z",
            "2024-01-01T06:00:00Z",
            "2024-01-01T12:00:00Z",
            "2024-01-01T18:00:00Z",
        ],
        "temperature_c": [15.0, 18.0, 25.0, 20.0],
    }
    df = pd.DataFrame(data)
    res = TemporalFeatureExtractor.extract_features(df)

    assert "hour" in res.columns
    assert "sin_hour" in res.columns
    assert "cos_hour" in res.columns
    assert "sin_day_of_year" in res.columns
    assert "cos_day_of_year" in res.columns

    # Hour 0: sin(0) = 0, cos(0) = 1
    assert pytest.approx(res.at[0, "sin_hour"], abs=1e-4) == 0.0
    assert pytest.approx(res.at[0, "cos_hour"], abs=1e-4) == 1.0

    # Hour 6: sin(pi/2) = 1, cos(pi/2) = 0
    assert pytest.approx(res.at[1, "sin_hour"], abs=1e-4) == 1.0
    assert pytest.approx(res.at[1, "cos_hour"], abs=1e-4) == 0.0

    # Hour 12: sin(pi) = 0, cos(pi) = -1
    assert pytest.approx(res.at[2, "sin_hour"], abs=1e-4) == 0.0
    assert pytest.approx(res.at[2, "cos_hour"], abs=1e-4) == -1.0


def test_temporal_extractor_empty_df() -> None:
    df = pd.DataFrame()
    res = TemporalFeatureExtractor.extract_features(df)
    assert res.empty
    assert "sin_hour" in res.columns
