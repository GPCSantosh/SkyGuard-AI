"""Mandatory automated anti-leakage tests verifying zero lookahead dependencies."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from ml.features.pipeline import FeaturePipeline


def test_future_data_modification_does_not_alter_past_features() -> None:
    """CRITICAL VERIFICATION: Modifying observations after timestamp T must NEVER alter features at t <= T."""
    timestamps = pd.date_range("2024-01-01 00:00:00", periods=50, freq="15min", tz="UTC")
    df_pristine = pd.DataFrame({
        "station_id": ["42182099999"] * 50,
        "timestamp": timestamps,
        "temperature_c": [20.0 + 0.5 * (i % 8) for i in range(50)],
        "relative_humidity_pct": [60.0 - 0.5 * (i % 6) for i in range(50)],
        "sea_level_pressure_hpa": [1013.0 + 0.1 * (i % 4) for i in range(50)],
        "station_pressure_hpa": [990.0 + 0.1 * (i % 4) for i in range(50)],
        "dew_point_c": [12.0 + 0.1 * (i % 5) for i in range(50)],
    })

    pipeline = FeaturePipeline()
    features_pristine = pipeline.transform(df_pristine)
    feature_cols = pipeline.get_feature_columns(features_pristine)

    # Cutoff index T = 25
    cutoff_idx = 25

    # Create radically corrupted future dataset where all rows after cutoff_idx are altered
    df_corrupted_future = df_pristine.copy()
    for idx in range(cutoff_idx + 1, len(df_corrupted_future)):
        df_corrupted_future.at[idx, "temperature_c"] = 99.9  # Extreme future spike
        df_corrupted_future.at[idx, "relative_humidity_pct"] = 0.1
        df_corrupted_future.at[idx, "sea_level_pressure_hpa"] = 550.0

    features_corrupted = pipeline.transform(df_corrupted_future)

    # Extract past slices (t <= cutoff_idx)
    past_pristine = features_pristine.iloc[: cutoff_idx + 1][feature_cols]
    past_corrupted = features_corrupted.iloc[: cutoff_idx + 1][feature_cols]

    # Assert bitwise/numerical identity for every single past feature
    for col in feature_cols:
        val_pristine = past_pristine[col].values
        val_corrupted = past_corrupted[col].values

        # Handle NaNs identically
        nan_mask_p = np.isnan(val_pristine) if np.issubdtype(val_pristine.dtype, np.number) else pd.isna(val_pristine)
        nan_mask_c = np.isnan(val_corrupted) if np.issubdtype(val_corrupted.dtype, np.number) else pd.isna(val_corrupted)
        np.testing.assert_array_equal(nan_mask_p, nan_mask_c, err_msg=f"NaN mismatch in {col}")

        # Non-nan numerical equality
        valid_idx = ~nan_mask_p
        np.testing.assert_allclose(
            val_pristine[valid_idx],
            val_corrupted[valid_idx],
            rtol=1e-5,
            atol=1e-5,
            err_msg=f"Data leakage detected! Feature '{col}' at t <= T changed when future values (t > T) were modified!",
        )
