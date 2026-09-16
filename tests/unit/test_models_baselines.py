"""Unit tests for baseline anomaly detectors (FixedThreshold & RollingZScore)."""

from __future__ import annotations

import tempfile
from pathlib import Path
import numpy as np
import pandas as pd
import pytest

from ml.models.baselines import FixedThresholdDetector, RollingZScoreDetector


def test_fixed_threshold_detector() -> None:
    df = pd.DataFrame({
        "temperature_c": [20.0, 25.0, 75.0, -60.0],  # 75 and -60 exceed physical bounds [-50, 60]
        "relative_humidity_pct": [50.0, 110.0, 50.0, -10.0],  # 110 and -10 exceed [0, 100]
        "temperature_c_rate_per_5min": [0.5, 1.0, 8.0, 0.0],  # 8.0 exceeds rate max 5.0
    })

    detector = FixedThresholdDetector()
    detector.fit(df)
    scores = detector.score_samples(df)
    preds = detector.predict(df)

    # Row 0: Normal -> score = 0.0, pred = 0
    assert scores[0] == 0.0
    assert preds[0] == 0

    # Row 1: RH = 110 -> score > 0.0
    assert scores[1] > 0.0

    # Row 2: Temp = 75, Rate = 8.0 -> score > 0.5, pred = 1
    assert scores[2] >= 0.5
    assert preds[2] == 1


def test_rolling_zscore_detector_and_serialization() -> None:
    df = pd.DataFrame({
        "temperature_c": [20.0, 21.0, 20.0, 35.0],
        "temperature_c_rolling_mean_1h": [20.0, 20.5, 20.3, 20.5],
        "temperature_c_rolling_std_1h": [1.0, 1.0, 1.0, 1.0],
        "temperature_c_zscore_1h": [0.0, 0.5, -0.3, 14.5],  # 14.5 is extreme outlier
    })

    detector = RollingZScoreDetector(z_threshold=3.0, rolling_window="1h")
    detector.fit(df)
    scores = detector.score_samples(df)

    assert scores[0] < 0.2
    assert scores[3] > 0.95

    # Test save/load
    with tempfile.TemporaryDirectory() as tmpdir:
        save_path = detector.save(tmpdir)
        loaded = RollingZScoreDetector.load(tmpdir)
        assert loaded.model_id == detector.model_id
        loaded_scores = loaded.score_samples(df)
        np.testing.assert_allclose(scores, loaded_scores)
