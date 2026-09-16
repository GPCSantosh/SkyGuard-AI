"""Isolation Forest unsupervised anomaly detector for SkyGuard AI."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Union
import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.impute import SimpleImputer

from backend.app.core.constants import EPSILON
from ml.models.base import BaseAnomalyModel, ModelMetadata


class IsolationForestDetector(BaseAnomalyModel):
    """Unsupervised Isolation Forest anomaly detector trained on normal historical observations."""

    def __init__(
        self,
        feature_list: Optional[Sequence[str]] = None,
        n_estimators: int = 100,
        max_samples: Union[str, int, float] = "auto",
        contamination: float = 0.01,
        random_state: int = 42,
        model_id: Optional[str] = None,
        model_version: str = "v1.0.0",
    ) -> None:
        super().__init__(feature_list=feature_list, model_id=model_id, random_seed=random_state)
        self.n_estimators = n_estimators
        self.max_samples = max_samples
        self.contamination = contamination
        self.model_version = model_version

        # Initialize scikit-learn estimator and imputer for numerical stability
        self.imputer = SimpleImputer(strategy="median")
        self.model = IsolationForest(
            n_estimators=self.n_estimators,
            max_samples=self.max_samples,
            contamination=self.contamination,
            random_state=self.random_seed,
            n_jobs=-1,
        )
        self.calibrated_threshold = 0.5
        self.is_fitted = False

        # Internal score normalization bounds
        self._score_min: float = -0.5
        self._score_max: float = 0.5

    def _prepare_features(self, X: pd.DataFrame, fit_imputer: bool = False) -> np.ndarray:
        """Extract and clean configured feature columns."""
        if not self.feature_list:
            # If no feature list passed, use all numeric columns
            self.feature_list = [c for c in X.select_dtypes(include=[np.number]).columns if not c.startswith("_")]

        # Subset dataframe and sanitize missing/inf values
        missing_cols = [c for c in self.feature_list if c not in X.columns]
        feat_df = X.copy()
        for mc in missing_cols:
            feat_df[mc] = 0.0
        feat_df = feat_df[self.feature_list].copy()

        # Replace Infs and NaNs safely
        feat_df = feat_df.replace([np.inf, -np.inf], np.nan).fillna(0.0)
        return feat_df.values.astype(float)

    def fit(self, X: pd.DataFrame, y: Optional[Union[pd.Series, np.ndarray]] = None) -> IsolationForestDetector:
        """Fit Isolation Forest on normal historical baseline observations."""
        if X.empty:
            raise ValueError("Cannot fit IsolationForestDetector on empty DataFrame.")

        X_mat = self._prepare_features(X, fit_imputer=True)
        self.model.fit(X_mat)
        self.is_fitted = True

        # Compute initial baseline score bounds on training data
        raw_decisions = -self.model.decision_function(X_mat)
        self._score_min = float(np.min(raw_decisions))
        self._score_max = float(np.max(raw_decisions))
        if self._score_max <= self._score_min:
            self._score_max = self._score_min + 1.0

        # Build metadata
        t_start = str(X["timestamp"].min()) if "timestamp" in X.columns else None
        t_end = str(X["timestamp"].max()) if "timestamp" in X.columns else None

        self.metadata = ModelMetadata(
            model_id=self.model_id,
            model_version=self.model_version,
            algorithm="IsolationForest",
            training_start=t_start,
            training_end=t_end,
            feature_list=self.feature_list,
            random_seed=self.random_seed,
            hyperparameters={
                "n_estimators": self.n_estimators,
                "max_samples": self.max_samples,
                "contamination": self.contamination,
                "random_state": self.random_seed,
                "_score_min": self._score_min,
                "_score_max": self._score_max,
            },
            calibrated_threshold=self.calibrated_threshold,
        )
        return self

    def score_samples(self, X: pd.DataFrame) -> np.ndarray:
        """Compute normalized anomaly scores in [0.0, 1.0].
        
        Note: scikit-learn decision_function returns negative values for outliers (lower = more abnormal).
        We negate the decision function so higher values indicate greater abnormality, then map to [0, 1].
        """
        if not self.is_fitted:
            raise RuntimeError("Model must be fitted before calling score_samples.")
        if X.empty:
            return np.array([], dtype=float)

        X_mat = self._prepare_features(X, fit_imputer=False)
        # Negate decision function: higher raw_anomaly = more abnormal
        raw_anomaly = -self.model.decision_function(X_mat)
        self._last_raw_scores = raw_anomaly

        # Min-max normalization clamped to [0.0, 1.0]
        denom = max(EPSILON, self._score_max - self._score_min)
        norm_scores = np.clip((raw_anomaly - self._score_min) / denom, 0.0, 1.0)
        return norm_scores

    def save(self, model_dir: Union[str, Path]) -> Path:
        """Save model artifacts (.joblib + _metadata.json)."""
        out_path = Path(model_dir)
        out_path.mkdir(parents=True, exist_ok=True)

        weights_file = out_path / f"{self.model_id}_weights.joblib"
        meta_file = out_path / f"{self.model_id}_metadata.json"

        # Update metadata
        if self.metadata:
            meta_dict = self.metadata.model_dump()
            meta_dict["calibrated_threshold"] = self.calibrated_threshold
            meta_dict["hyperparameters"]["_score_min"] = self._score_min
            meta_dict["hyperparameters"]["_score_max"] = self._score_max
            self.metadata = ModelMetadata(**meta_dict)

        payload = {
            "model": self.model,
            "imputer": self.imputer,
            "feature_list": self.feature_list,
            "_score_min": self._score_min,
            "_score_max": self._score_max,
            "calibrated_threshold": self.calibrated_threshold,
        }
        joblib.dump(payload, weights_file)

        if self.metadata:
            with open(meta_file, "w", encoding="utf-8") as f:
                f.write(self.metadata.model_dump_json(indent=2))

        return weights_file

    @classmethod
    def load(cls, model_dir: Union[str, Path]) -> IsolationForestDetector:
        """Load model artifacts and restore metadata."""
        p = Path(model_dir)
        if p.is_file() and p.suffix == ".joblib":
            weights_file = p
            meta_file = p.parent / p.name.replace("_weights.joblib", "_metadata.json")
        elif p.is_dir():
            weights_files = list(p.glob("*_weights.joblib"))
            if not weights_files:
                raise FileNotFoundError(f"No *_weights.joblib found in {p}")
            weights_file = weights_files[0]
            meta_file = weights_file.parent / weights_file.name.replace("_weights.joblib", "_metadata.json")
        else:
            raise FileNotFoundError(f"Invalid model path: {p}")

        payload = joblib.load(weights_file)
        detector = cls(
            feature_list=payload.get("feature_list", []),
            model_id=weights_file.stem.replace("_weights", ""),
        )
        detector.model = payload["model"]
        detector.imputer = payload["imputer"]
        detector._score_min = payload.get("_score_min", -0.5)
        detector._score_max = payload.get("_score_max", 0.5)
        detector.calibrated_threshold = payload.get("calibrated_threshold", 0.5)
        detector.is_fitted = True

        if meta_file.is_file():
            with open(meta_file, "r", encoding="utf-8") as f:
                detector.metadata = ModelMetadata(**json.load(f))

        return detector
