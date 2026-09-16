"""Unit tests for high-cadence 5-minute StreamSimulator."""

from __future__ import annotations

import pandas as pd
import pytest

from ml.synthetic.stream_simulator import StreamSimulator


def test_stream_simulator_metadata_and_resampling() -> None:
    # 30-minute synoptic observations over 2 hours (5 rows)
    timestamps = pd.date_range("2024-01-01 00:00:00", periods=5, freq="30min", tz="UTC")
    df = pd.DataFrame({
        "station_id": ["42182099999"] * 5,
        "timestamp": timestamps,
        "temperature_c": [20.0, 21.0, 22.0, 23.0, 24.0],
        "relative_humidity_pct": [60.0, 58.0, 56.0, 54.0, 52.0],
        "sea_level_pressure_hpa": [1013.0, 1013.2, 1013.4, 1013.6, 1013.8],
    })

    sim = StreamSimulator(target_cadence_minutes=5.0, add_micro_turbulence=False)
    sim_df = sim.simulate_stream(df)

    # 2 hours from 00:00 to 02:00 at 5-min cadence = 25 timestamps
    assert len(sim_df) == 25

    # Check mandatory synthetic provenance metadata
    assert "is_synthetic" in sim_df.columns
    assert sim_df["is_synthetic"].all() is True or (sim_df["is_synthetic"] == True).all()  # noqa: E712
    assert "native_resolution_minutes" in sim_df.columns
    assert (sim_df["native_resolution_minutes"] == 5.0).all()
    assert (sim_df["source_resolution_minutes"] == 30.0).all()

    # Verify linear interpolation midpoints (e.g. at 00:15, temp should be ~20.5)
    row_15 = sim_df[sim_df["timestamp"] == pd.Timestamp("2024-01-01 00:15:00", tz="UTC")].iloc[0]
    assert pytest.approx(row_15["temperature_c"], abs=1e-2) == 20.5
