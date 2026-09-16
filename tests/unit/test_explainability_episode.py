"""Unit tests for anomaly episode timeline reconstruction."""

import pandas as pd
import pytest

from ml.explainability.episode_reconstructor import AnomalyEpisodeReconstructor
from ml.explainability.schema import AnomalyEpisode


def test_anomaly_episode_lifecycle_reconstruction():
    """Test full episode reconstruction: normal -> onset -> peak -> recovery."""
    reconstructor = AnomalyEpisodeReconstructor(default_preceding_steps=3, default_following_steps=3)

    timestamps = pd.date_range("2026-09-17 00:00", periods=12, freq="5min")
    # Temperature profile: 20 -> 20 -> 20 -> 25 (onset) -> 35 (peak) -> 30 -> 21 (recovered) -> 20 ...
    temps = [20.0, 20.1, 20.0, 25.0, 35.0, 30.0, 20.5, 20.2, 20.1, 20.0, 20.0, 20.0]
    scores = [0.1, 0.1, 0.1, 0.7, 0.95, 0.8, 0.2, 0.1, 0.1, 0.1, 0.1, 0.1]
    decisions = [
        "NORMAL", "NORMAL", "NORMAL",
        "PROBABLE_SENSOR_ANOMALY", "PROBABLE_SENSOR_ANOMALY", "PROBABLE_SENSOR_ANOMALY",
        "NORMAL", "NORMAL", "NORMAL", "NORMAL", "NORMAL", "NORMAL"
    ]

    df = pd.DataFrame({
        "station_id": ["AWS_001"] * 12,
        "timestamp": [t.isoformat() for t in timestamps],
        "temperature_c": temps,
        "normalized_anomaly_score": scores,
        "decision": decisions,
    })

    # Event query at peak timestamp (index 4 = 00:20)
    event_t = timestamps[4].isoformat()
    episode = reconstructor.reconstruct_episode(
        station_id="AWS_001",
        event_timestamp=event_t,
        history_df=df,
        target_variable="temperature_c",
    )

    assert isinstance(episode, AnomalyEpisode)
    assert episode.station_id == "AWS_001"
    # Onset at index 3 (00:15)
    assert episode.onset_timestamp == timestamps[3].isoformat()
    # Peak at index 4 (00:20)
    assert episode.peak_timestamp == timestamps[4].isoformat()
    assert episode.peak_value == 35.0
    assert episode.peak_anomaly_score == 0.95
    # Recovery at index 6 (00:30)
    assert episode.recovery_timestamp == timestamps[6].isoformat()
    # Duration: from 00:15 to 00:30 = 15 minutes
    assert episode.duration_minutes == 15.0

    # Verify slices
    assert len(episode.preceding_normal_observations) == 3
    assert len(episode.episode_observations) == 3  # Indices 3, 4, 5
    assert len(episode.recovering_observations) >= 1


def test_episode_ongoing_without_recovery():
    """Test episode reconstruction when anomaly is ongoing at the end of the history."""
    reconstructor = AnomalyEpisodeReconstructor()

    timestamps = pd.date_range("2026-09-17 00:00", periods=6, freq="5min")
    temps = [20.0, 20.0, 20.0, 28.0, 30.0, 32.0]
    scores = [0.1, 0.1, 0.1, 0.7, 0.8, 0.85]
    decisions = ["NORMAL", "NORMAL", "NORMAL", "PROBABLE_SENSOR_ANOMALY", "PROBABLE_SENSOR_ANOMALY", "PROBABLE_SENSOR_ANOMALY"]

    df = pd.DataFrame({
        "station_id": ["AWS_001"] * 6,
        "timestamp": [t.isoformat() for t in timestamps],
        "temperature_c": temps,
        "normalized_anomaly_score": scores,
        "decision": decisions,
    })

    episode = reconstructor.reconstruct_episode(
        station_id="AWS_001",
        event_timestamp=timestamps[5].isoformat(),
        history_df=df,
    )

    assert episode.recovery_timestamp is None  # Still ongoing
    assert episode.duration_minutes == 10.0
