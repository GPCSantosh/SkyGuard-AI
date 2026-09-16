"""Statistical and rule-based baseline anomaly detectors for SkyGuard AI."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Union
import joblib
import numpy as np
import pandas as pd

from backend.app.core.constants import EPSILON
from ml.models.base import BaseAnomalyModel, ModelMetadata


class FixedThresholdDetector(BaseAnomalyInjectorModel if False else BaseAnomalyModel):
    """Deterministic baseline flagging observations exceeding static physical and rate limits."""

    def __init__(
        self,
        temp_bounds: Sequence[float] = (-50.0, 60.0),
        humidity_bounds: Sequence[float] = (0.0, 100.0),
        slp_bounds: Sequence[float] = (500.0, 1080.0),
        temp_rate_max_5min: float = 5.0,
        model_id: Optional[str] = None,
    ) -> None:
        super().__init__(feature_list=["temperature_c", "relative_humidity_pct", "sea_level_pressure_hpa"], model_id=model_id)
        self.temp_bounds = tuple(temp_bounds)
        self.humidity_bounds = tuple(humidity_bounds)
        self.slp_bounds = tuple(slp_bounds)
        self.temp_rate_max_5min = temp_rate_max_5min
        self.calibrated_threshold = 0.5
        self.is_fitted = True

    def fit(self, X: pd.DataFrame, y: Optional[Union[pd.Series, np.ndarray]] = None) -> FixedThresholdDetector:
        """Fixed thresholds do not require fitting."""
        self.is_fitted = True
        self.metadata = ModelMetadata(
            model_id=self.model_id,
            algorithm="FixedThresholdDetector",
            feature_list=self.feature_list,
            hyperparameters={
                "temp_bounds": self.temp_bounds,
                "humidity_bounds": self.humidity_bounds,
                "slp_bounds": self.slp_bounds,
                "temp_rate_max_5min": self.temp_rate_max_5min,
            },
            calibrated_threshold=self.calibrated_threshold,
        )
        return self

    def score_samples(self, X: pd.DataFrame) -> np.ndarray:
        """Compute severity score in [0.0, 1.0] based on degree of boundary violation."""
        if X.empty:
            return np.array([], dtype=float)

        n = len(X)
        scores = np.zeros(n, dtype=float)

        # Temperature physical bounds
        if "temperature_c" in X.columns:
            t = X["temperature_c"].values
            t_low_viol = np.maximum(0.0, self.temp_bounds[0] - t)
            t_high_viol = np.maximum(0.0, t - self.temp_bounds[1])
            t_score = np.clip((t_low_viol + t_high_viol) / 10.0, 0.0, 1.0)
            scores = np.maximum(scores, np.nan_to_num(t_score, nan=0.0))

        # Relative humidity bounds
        if "relative_humidity_pct" in X.columns:
            rh = X["relative_humidity_pct"].values
            rh_low_viol = np.maximum(0.0, self.humidity_bounds[0] - rh)
            rh_high_viol = np.maximum(0.0, rh - self.humidity_bounds[1])
            rh_score = np.clip((rh_low_viol + rh_high_viol) / 20.0, 0.0, 1.0)
            scores = np.maximum(scores, np.nan_to_num(rh_score, nan=0.0))

        # Atmospheric pressure bounds
        if "sea_level_pressure_hpa" in X.columns:
            p = X["sea_level_pressure_hpa"].values
            p_low_viol = np.maximum(0.0, self.slp_bounds[0] - p)
            p_high_viol = np.maximum(0.0, p - self.slp_bounds[1])
            p_score = np.clip((p_low_viol + p_high_viol) / 50.0, 0.0, 1.0)
            scores = np.maximum(scores, np.nan_to_num(p_score, nan=0.0))

        # Rate of change check
        if "temperature_c_rate_per_5min" in X.columns:
            tr = np.abs(X["temperature_c_rate_per_5min"].values)
            rate_viol = np.maximum(0.0, tr - self.temp_rate_max_5min)
            rate_score = np.clip(rate_viol / 5.0, 0.0, 1.0)
            scores = np.maximum(scores, np.nan_to_num(rate_score, nan=0.0))

        self._last_raw_scores = scores
        return scores

    def save(self, model_dir: Union[str, Path]) -> Path:
        out_path = Path(model_dir)
        out_path.mkdir(parents=True, exist_ok=True)
        meta_file = out_path / f"{self.model_id}_metadata.json"
        if not self.metadata:
            self.fit(pd.DataFrame())
        with open(meta_file, "w", encoding="utf-8") as f:
            f.write(self.metadata.model_dump_json(indent=2))
        return meta_file

    @classmethod
    def load(cls, model_dir: Union[str, Path]) -> FixedThresholdDetector:
        p = Path(model_dir)
        meta_files = list(p.glob("*_metadata.json")) if p.is_dir() else [p]
        with open(meta_files[0], "r", encoding="utf-8") as f:
            data = json.load(f)
        meta = ModelMetadata(**data)
        detector = cls(
            temp_bounds=meta.hyperparameters.get("temp_bounds", (-50.0, 60.0)),
            humidity_bounds=meta.hyperparameters.get("humidity_bounds", (0.0, 100.0)),
            slp_bounds=meta.hyperparameters.get("slp_bounds", (500.0, 1080.0)),
            temp_rate_max_5min=meta.hyperparameters.get("temp_rate_max_5min", 5.0),
            model_id=meta.model_id,
        )
        detector.metadata = meta
        detector.calibrated_threshold = meta.calibrated_threshold
        return detector


class RollingZScoreDetector(BaseAnomalyModel):
    """Statistical baseline flagging observations where local temporal Z-score exceeds a threshold."""

    def __init__(
        self,
        z_threshold: float = 3.0,
        rolling_window: str = "1h",
        parameters: Optional[Sequence[str]] = None,
        model_id: Optional[str] = None,
    ) -> None:
        params = list(parameters or ["temperature_c", "relative_humidity_pct", "sea_level_pressure_hpa"])
        super().__init__(feature_list=params, model_id=model_id)
        self.z_threshold = z_threshold
        self.rolling_window = rolling_window.replace("min", "m").replace("hour", "h")
        self.calibrated_threshold = float(z_threshold)
        self.is_fitted = False

    def fit(self, X: pd.DataFrame, y: Optional[Union[pd.Series, np.ndarray]] = None) -> RollingZScoreDetector:
        self.is_fitted = True
        self.metadata = ModelMetadata(
            model_id=self.model_id,
            algorithm="RollingZScoreDetector",
            feature_list=self.feature_list,
            hyperparameters={
                "z_threshold": self.z_threshold,
                "rolling_window": self.rolling_window,
            },
            calibrated_threshold=self.calibrated_threshold,
        )
        return self

    def score_samples(self, X: pd.DataFrame) -> np.ndarray:
        """Compute maximum Z-score anomaly metric across evaluated parameters."""
        if X.empty:
            return np.array([], dtype=float)

        n = len(X)
        max_z = np.zeros(n, dtype=float)

        for param in self.feature_list:
            z_col = f"{param}_zscore_{self.rolling_window}"
            if z_col in X.columns:
                z_vals = np.abs(np.nan_to_num(X[z_col].values, nan=0.0))
                max_z = np.maximum(max_z, z_vals)
            elif param in X.columns and f"{param}_rolling_mean_{self.rolling_window}" in X.columns:
                mean = X[f"{param}_rolling_mean_{self.rolling_window}"].values
                std = X.get(f"{param}_rolling_std_{self.rolling_window}", pd.Series(1.0, index=X.index)).values
                val = X[param].values
                z = np.abs(val - mean) / (np.maximum(std, EPSILON))
                max_z = np.maximum(max_z, np.nan_to_num(z, nan=0.0))

        self._last_raw_scores = max_z
        # Normalize continuous Z-score using smooth saturation: tanh(Z / 3.0)
        normalized_scores = np.tanh(max_z / 3.0)
        return normalized_scores

    def save(self, model_dir: Union[str, Path]) -> Path:
        out_path = Path(model_dir)
        out_path.mkdir(parents=True, exist_ok=True)
        meta_file = out_path / f"{self.model_id}_metadata.json"
        if not self.metadata:
            self.fit(pd.DataFrame())
        with open(meta_file, "w", encoding="utf-8") as f:
            f.write(self.metadata.model_dump_json(indent=2))
        return meta_file

    @classmethod
    def load(cls, model_dir: Union[str, Path]) -> RollingZScoreDetector:
        p = Path(model_dir)
        meta_files = list(p.glob("*_metadata.json")) if p.is_dir() else [p]
        with open(meta_files[0], "r", encoding="utf-8") as f:
            data = json.load(f)
        meta = ModelMetadata(**data)
        detector = cls(
            z_threshold=meta.hyperparameters.get("z_threshold", 3.0),
            rolling_window=meta.hyperparameters.get("rolling_window", "1h"),
            parameters=meta.feature_list,
            model_id=meta.model_id,
        )
        detector.metadata = meta
        detector.calibrated_threshold = meta.calibrated_threshold
        detector.is_fitted = True
        return detector
