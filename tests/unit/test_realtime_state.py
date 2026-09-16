"""Unit tests for Real-Time State Management, Sliding Windows, and Causality."""

from datetime import datetime, timezone
import pytest

from backend.app.core.state import StationStateBuffer, StationStateManager
from backend.app.models.observation import ObservationSource, QualityStatus, WeatherObservation
from backend.app.models.processing import ProcessingStatus


def make_obs(station_id: str, ts_iso: str, temp: float = 25.0) -> WeatherObservation:
    return WeatherObservation(
        station_id=station_id,
        timestamp=datetime.fromisoformat(ts_iso).astimezone(timezone.utc),
        latitude=28.6,
        longitude=77.2,
        temperature=temp,
        humidity=50.0,
        pressure=1013.25,
        source=ObservationSource.SIMULATOR,
        data_quality_status=QualityStatus.VALID,
    )


def test_duplicate_and_idempotency_detection():
    buffer = StationStateBuffer(station_id="STN_001", max_retention=10)
    obs = make_obs("STN_001", "2024-01-01T12:00:00+00:00")

    status, reason = buffer.check_temporal_ordering(obs)
    assert status == ProcessingStatus.PROCESSED
    buffer.append_observation(obs)

    # Second arrival of exact same packet
    status_dup, reason_dup = buffer.check_temporal_ordering(obs)
    assert status_dup == ProcessingStatus.DUPLICATE_SKIPPED
    assert "Duplicate" in str(reason_dup)


def test_out_of_order_detection():
    buffer = StationStateBuffer(station_id="STN_001", max_retention=10)
    obs1 = make_obs("STN_001", "2024-01-01T12:10:00+00:00")
    buffer.append_observation(obs1)

    # Arriving observation with older timestamp (12:05 vs watermark 12:10)
    obs_late = make_obs("STN_001", "2024-01-01T12:05:00+00:00")
    status, reason = buffer.check_temporal_ordering(obs_late)
    assert status == ProcessingStatus.OUT_OF_ORDER
    assert "out-of-order" in str(reason)


def test_future_timestamp_detection():
    buffer = StationStateBuffer(station_id="STN_001", max_retention=10)
    # Timestamp clearly in future with non-simulator source
    future_obs = WeatherObservation(
        station_id="STN_001",
        timestamp=datetime.fromisoformat("2099-01-01T12:00:00+00:00"),
        latitude=28.6,
        longitude=77.2,
        temperature=25.0,
        source=ObservationSource.WEATHER_API,
        data_quality_status=QualityStatus.VALID,
    )
    status, reason = buffer.check_temporal_ordering(future_obs)
    assert status == ProcessingStatus.FUTURE_TIMESTAMP
    assert "future" in str(reason)


def test_causal_history_retrieval():
    buffer = StationStateBuffer(station_id="STN_001", max_retention=10)
    obs1 = make_obs("STN_001", "2026-09-17T12:00:00+00:00", temp=20.0)
    obs2 = make_obs("STN_001", "2026-09-17T12:05:00+00:00", temp=21.0)
    obs3 = make_obs("STN_001", "2026-09-17T12:10:00+00:00", temp=22.0)
    
    buffer.append_observation(obs1)
    buffer.append_observation(obs2)
    buffer.append_observation(obs3)

    # Query causal history at 12:05: should only return obs1 and obs2, NOT obs3
    cutoff = datetime.fromisoformat("2026-09-17T12:05:00+00:00").astimezone(timezone.utc)
    causal_list = buffer.get_causal_history(before_timestamp=cutoff)
    assert len(causal_list) == 2
    assert causal_list[-1].temperature == 21.0


def test_bounded_memory_retention():
    buffer = StationStateBuffer(station_id="STN_001", max_retention=5)
    for i in range(10):
        obs = make_obs("STN_001", f"2026-09-17T12:{i:02d}:00+00:00", temp=20.0 + i)
        buffer.append_observation(obs)

    # Buffer length must be bounded to max_retention (5)
    assert len(buffer.observations) == 5
    assert buffer.observations[0].temperature == 25.0
    assert buffer.observations[-1].temperature == 29.0


def test_station_level_isolation():
    manager = StationStateManager()
    buf_a = manager.get_or_create_buffer("STN_A")
    buf_b = manager.get_or_create_buffer("STN_B")

    obs_a = make_obs("STN_A", "2026-09-17T12:00:00+00:00", temp=25.0)
    buf_a.append_observation(obs_a)

    assert len(buf_a.observations) == 1
    assert len(buf_b.observations) == 0
