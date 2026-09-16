"""Unit tests for the end-to-end FeaturePipeline."""

from __future__ import annotations

import pandas as pd
import pytest

from ml.features.pipeline import FeaturePipeline, FeaturePipelineConfig


def test_feature_pipeline_end_to_end() -> None:
    timestamps = pd.date_range("2024-01-01 00:00:00", periods=20, freq="30min", tz="UTC")
    df = pd.DataFrame({
        "station_id": ["42182099999"] * 20,
        "timestamp": timestamps,
        "temperature_c": [20.0 + (i % 5) for i in range(20)],
        "relative_humidity_pct": [60.0 - (i % 4) for i in range(20)],
        "sea_level_pressure_hpa": [1013.0 + 0.1 * i for i in range(20)],
        "station_pressure_hpa": [990.0 + 0.1 * i for i in range(20)],
        "dew_point_c": [12.0 + 0.2 * i for i in range(20)],
    })

    pipeline = FeaturePipeline()
    res = pipeline.transform(df)

    assert len(res) == 20
    assert "sin_hour" in res.columns
    assert "temperature_c_lag_1" in res.columns
    assert "temperature_c_rate_per_minute" in res.columns
    assert "temperature_c_consecutive_unchanged_count" in res.columns

    # Test get_feature_columns
    feature_cols = pipeline.get_feature_columns(res)
    assert len(feature_cols) > 20
    assert "station_id" not in feature_cols
    assert "timestamp" not in feature_cols
    assert "ground_truth" not in feature_cols
