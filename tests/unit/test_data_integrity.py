"""Mandatory data integrity and immutability verification tests for SkyGuard AI."""

from __future__ import annotations

import hashlib
from pathlib import Path
import pandas as pd
import pytest

from ml.features.pipeline import FeaturePipeline
from ml.synthetic.engine import SyntheticAnomalyEngine
from ml.synthetic.schema import AnomalyInjectionConfig
from ml.synthetic.stream_simulator import StreamSimulator


def _compute_df_hash(df: pd.DataFrame) -> str:
    """Compute SHA-256 checksum of DataFrame byte contents."""
    csv_bytes = df.to_csv(index=False).encode("utf-8")
    return hashlib.sha256(csv_bytes).hexdigest()


def test_raw_data_immutability_across_all_operations() -> None:
    """Verify that feature generation, anomaly injection, and simulation NEVER mutate input data."""
    # Create sample baseline DataFrame
    timestamps = pd.date_range("2024-01-01 00:00:00", periods=60, freq="10min", tz="UTC")
    baseline_df = pd.DataFrame({
        "station_id": ["42182099999"] * 60,
        "timestamp": timestamps,
        "temperature_c": [20.0 + 0.3 * (i % 10) for i in range(60)],
        "relative_humidity_pct": [55.0 - 0.2 * (i % 8) for i in range(60)],
        "sea_level_pressure_hpa": [1012.5 + 0.05 * (i % 5) for i in range(60)],
        "station_pressure_hpa": [990.0 + 0.05 * (i % 5) for i in range(60)],
    })

    initial_hash = _compute_df_hash(baseline_df)

    # 1. Run Feature Engineering Pipeline
    feature_pipeline = FeaturePipeline()
    _ = feature_pipeline.transform(baseline_df)
    post_fe_hash = _compute_df_hash(baseline_df)
    assert post_fe_hash == initial_hash, "Feature pipeline mutated the raw input DataFrame in-place!"

    # 2. Run Synthetic Anomaly Injection
    inj_cfg = AnomalyInjectionConfig(seed=42, num_anomalies_per_type=1)
    engine = SyntheticAnomalyEngine(config=inj_cfg)
    _ = engine.run_injection(baseline_df)
    post_inj_hash = _compute_df_hash(baseline_df)
    assert post_inj_hash == initial_hash, "Anomaly injection engine mutated the raw input DataFrame in-place!"

    # 3. Run Stream Simulator
    simulator = StreamSimulator(target_cadence_minutes=5.0)
    _ = simulator.simulate_stream(baseline_df)
    post_sim_hash = _compute_df_hash(baseline_df)
    assert post_sim_hash == initial_hash, "Stream simulator mutated the raw input DataFrame in-place!"
