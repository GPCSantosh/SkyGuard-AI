"""Unit tests for SyntheticAnomalyEngine reproducibility and ground truth separation."""

from __future__ import annotations

import pandas as pd
import pytest

from ml.synthetic.engine import SyntheticAnomalyEngine
from ml.synthetic.schema import AnomalyInjectionConfig, SyntheticAnomalyType


@pytest.fixture
def clean_baseline_df() -> pd.DataFrame:
    timestamps = pd.date_range("2024-01-01 00:00:00", periods=100, freq="15min", tz="UTC")
    return pd.DataFrame({
        "station_id": ["42182099999"] * 100,
        "timestamp": timestamps,
        "temperature_c": [20.0 + (i % 8) * 0.5 for i in range(100)],
        "relative_humidity_pct": [60.0 - (i % 6) * 1.0 for i in range(100)],
        "sea_level_pressure_hpa": [1013.0 + 0.1 * (i % 5) for i in range(100)],
    })


def test_synthetic_engine_reproducibility(clean_baseline_df: pd.DataFrame) -> None:
    cfg1 = AnomalyInjectionConfig(
        seed=42,
        anomalies_to_inject=[SyntheticAnomalyType.SPIKE, SyntheticAnomalyType.DRIFT],
        num_anomalies_per_type=2,
    )
    engine1 = SyntheticAnomalyEngine(config=cfg1)
    res1 = engine1.run_injection(clean_baseline_df)

    cfg2 = AnomalyInjectionConfig(
        seed=42,
        anomalies_to_inject=[SyntheticAnomalyType.SPIKE, SyntheticAnomalyType.DRIFT],
        num_anomalies_per_type=2,
    )
    engine2 = SyntheticAnomalyEngine(config=cfg2)
    res2 = engine2.run_injection(clean_baseline_df)

    # Assert bitwise identical modified datasets and ground truth tables
    pd.testing.assert_frame_equal(res1.modified_df, res2.modified_df)
    pd.testing.assert_frame_equal(res1.ground_truth_df, res2.ground_truth_df)


def test_ground_truth_separation(clean_baseline_df: pd.DataFrame) -> None:
    cfg = AnomalyInjectionConfig(
        seed=42,
        anomalies_to_inject=[SyntheticAnomalyType.SPIKE, SyntheticAnomalyType.FROZEN_SENSOR],
    )
    engine = SyntheticAnomalyEngine(config=cfg)
    res = engine.run_injection(clean_baseline_df)

    # Ensure modified_df does NOT contain any ground truth metadata columns
    for col in [
        "ground_truth_label",
        "anomaly_id",
        "anomaly_type",
        "original_value",
        "modified_value",
        "injection_start",
        "injection_end",
        "severity_parameter",
        "is_fault",
    ]:
        assert col not in res.modified_df.columns

    # Ensure ground_truth_df has the mandatory fields
    assert not res.ground_truth_df.empty
    assert "anomaly_id" in res.ground_truth_df.columns
    assert "ground_truth_label" in res.ground_truth_df.columns
    assert "affected_variable" in res.ground_truth_df.columns
