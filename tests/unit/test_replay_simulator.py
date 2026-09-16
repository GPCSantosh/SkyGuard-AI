"""Unit tests for StreamReplayEngine and Synthetic Anomaly Injections."""

import pandas as pd
import pytest

from backend.app.core.engine import RealTimeProcessingEngine
from backend.app.core.replay import StreamReplayEngine


def test_replay_from_dataframe():
    df = pd.DataFrame([
        {"station_id": "STN_001", "timestamp": "2026-09-17 12:00:00+00:00", "temperature_c": 25.0, "relative_humidity_pct": 50.0, "sea_level_pressure_hpa": 1013.25},
        {"station_id": "STN_001", "timestamp": "2026-09-17 12:05:00+00:00", "temperature_c": 25.5, "relative_humidity_pct": 51.0, "sea_level_pressure_hpa": 1013.0},
        {"station_id": "STN_001", "timestamp": "2026-09-17 12:10:00+00:00", "temperature_c": 26.0, "relative_humidity_pct": 52.0, "sea_level_pressure_hpa": 1012.8},
    ])

    replay = StreamReplayEngine()
    replay.load_from_dataframe(df)

    assert len(replay.observations) == 3
    
    stream_items = list(replay.iterate_stream())
    assert len(stream_items) == 3
    assert stream_items[0][0].temperature == 25.0
    assert stream_items[-1][0].temperature == 26.0


def test_replay_with_synthetic_fault_injection():
    df = pd.DataFrame([
        {"station_id": "STN_001", "timestamp": "2026-09-17 12:00:00+00:00", "temperature_c": 25.0, "relative_humidity_pct": 50.0, "sea_level_pressure_hpa": 1013.25},
        {"station_id": "STN_001", "timestamp": "2026-09-17 12:05:00+00:00", "temperature_c": 25.5, "relative_humidity_pct": 51.0, "sea_level_pressure_hpa": 1013.0},
    ])

    replay = StreamReplayEngine()
    replay.load_from_dataframe(df)

    # Register spike at 12:05
    replay.register_injected_anomaly(
        station_id="STN_001",
        timestamp="2026-09-17 12:05:00+00:00",
        anomaly_type="SPIKE",
        corrupted_values={"temperature": 55.0},
    )

    stream_items = list(replay.iterate_stream())
    obs2, gt2 = stream_items[1]
    assert obs2.temperature == 55.0
    assert gt2.is_anomaly is True
    assert gt2.clean_temperature_c == 25.5
    assert gt2.anomaly_category == "SPIKE"


def test_replay_synchronous_stepping():
    df = pd.DataFrame([
        {"station_id": "STN_001", "timestamp": f"2026-09-17 12:{i:02d}:00+00:00", "temperature_c": 25.0 + i, "relative_humidity_pct": 50.0, "sea_level_pressure_hpa": 1013.0}
        for i in range(5)
    ])

    replay = StreamReplayEngine()
    replay.load_from_dataframe(df)
    engine = RealTimeProcessingEngine()

    results = replay.run_synchronous_simulation(engine=engine, max_steps=3)
    assert len(results) == 3
    assert replay.emitted_count == 3
