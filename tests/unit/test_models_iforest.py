"""Unit tests for IsolationForestDetector."""

from __future__ import annotations

import tempfile
from pathlib import Path
import numpy as np
import pandas as pd
import pytest

from ml.models.isolation_forest import IsolationForestDetector


@pytest.fixture
def clean_train_df() -> pd.DataFrame:
    rng = np.random.default_rng(42)
    return pd.DataFrame({
        "temperature_c": rng.normal(25.0, 2.0, 100),
        "relative_humidity_pct": rng.normal(50.0, 5.0, 100),
        "sea_level_pressure_hpa": rng.normal(1013.0, 2.0, 100),
    })


def test_isolation_forest_fit_and_score(clean_train_df: pd.DataFrame) -> None:
    detector = IsolationForestDetector(
        feature_list=["temperature_c", "relative_humidity_pct", "sea_level_pressure_hpa"],
        n_estimators=50,
        contamination=0.01,
        random_state=42,
    )
    detector.fit(clean_train_df)
    assert detector.is_fitted is True
    assert detector.metadata is not None
    assert detector.metadata.algorithm == "IsolationForest"

    # Score normal vs outlier
    test_df = pd.DataFrame({
        "temperature_c": [25.0, 60.0],  # 60.0 is severe outlier
        "relative_humidity_pct": [50.0, 5.0],
        "sea_level_pressure_hpa": [1013.0, 950.0],
    })
    scores = detector.score_samples(test_df)
    assert len(scores) == 2
    assert 0.0 <= scores[0] <= 1.0
    assert 0.0 <= scores[1] <= 1.0
    assert scores[1] > scores[0]  # Outlier has higher anomaly score


def test_isolation_forest_threshold_calibration(clean_train_df: pd.DataFrame) -> None:
    detector = IsolationForestDetector(
        feature_list=["temperature_c", "relative_humidity_pct", "sea_level_pressure_hpa"],
        random_state=42,
    )
    detector.fit(clean_train_df)

    val_df = pd.DataFrame({
        "temperature_c": [25.0, 25.2, 24.8, 55.0, 58.0],
        "relative_humidity_pct": [50.0, 51.0, 49.0, 10.0, 8.0],
        "sea_level_pressure_hpa": [1013.0, 1013.1, 1012.9, 970.0, 960.0],
    })
    y_val = np.array([0, 0, 0, 1, 1])

    calib_thresh = detector.calibrate_threshold(val_df, y_val, target_metric="f1")
    assert 0.0 < calib_thresh < 1.0
    preds = detector.predict(val_df)
    assert preds[0] == 0
    assert preds[1] == 0
    assert preds[3] == 1
    assert preds[4] == 1


def test_isolation_forest_save_and_load(clean_train_df: pd.DataFrame) -> None:
    detector = IsolationForestDetector(
        feature_list=["temperature_c", "relative_humidity_pct", "sea_level_pressure_hpa"],
        model_id="test_iforest_001",
        random_state=42,
    )
    detector.fit(clean_train_df)
    scores_before = detector.score_samples(clean_train_df.head(10))

    with tempfile.TemporaryDirectory() as tmpdir:
        save_path = detector.save(tmpdir)
        assert Path(save_path).is_file()

        loaded_detector = IsolationForestDetector.load(tmpdir)
        assert loaded_detector.model_id == "test_iforest_001"
        assert loaded_detector.is_fitted is True

        scores_after = loaded_detector.score_samples(clean_train_df.head(10))
        np.testing.assert_allclose(scores_before, scores_after)
