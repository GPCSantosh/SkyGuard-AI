"""Common anomaly model interfaces and artifact schemas for SkyGuard AI."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np
import pandas as pd
from pydantic import BaseModel, ConfigDict, Field


class ModelMetadata(BaseModel):
    """Provenance and specification metadata saved alongside model weights."""
    model_config = ConfigDict(frozen=True)

    model_id: str = Field(..., description="Unique model identifier (UUID or semantic tag)")
    model_version: str = Field(default="v1.0.0", description="Semantic model version")
    algorithm: str = Field(..., description="Model algorithm name (e.g., 'IsolationForest', 'RollingZScore')")
    training_start: Optional[str] = Field(default=None, description="Earliest UTC timestamp in training split")
    training_end: Optional[str] = Field(default=None, description="Latest UTC timestamp in training split")
    feature_list: List[str] = Field(..., description="Exact ordered list of feature column names used for training")
    preprocessing_version: str = Field(default="v1.0.0", description="Feature engineering pipeline version")
    random_seed: int = Field(default=42, description="Random seed used during training")
    hyperparameters: Dict[str, Any] = Field(default_factory=dict, description="Algorithm hyperparameters")
    calibrated_threshold: float = Field(default=0.5, description="Calibrated decision threshold for anomaly scoring")
    dataset_reference: Optional[str] = Field(default=None, description="Source dataset URI or hash")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Serialization UTC timestamp")


class AnomalyPredictionResult(BaseModel):
    """Structured container for model inference outputs."""
    model_config = ConfigDict(arbitrary_types_allowed=True)

    raw_scores: np.ndarray = Field(..., description="Raw decision function or distance output from model")
    anomaly_scores: np.ndarray = Field(..., description="Normalized continuous anomaly score metric in [0.0, 1.0]")
    is_anomaly: np.ndarray = Field(..., description="Binary decision flags (1 = Anomaly, 0 = Nominal)")
    calibrated_threshold: float = Field(..., description="Decision boundary used for classification")
    model_id: str = Field(..., description="Originating model identifier")


class BaseAnomalyModel(ABC):
    """Abstract base contract for all SkyGuard AI anomaly detection models.
    
    Ensures seamless interchangeability among baseline thresholders, Isolation Forests,
    One-Class SVMs, and future deep autoencoders.
    """

    def __init__(
        self,
        feature_list: Optional[Sequence[str]] = None,
        model_id: Optional[str] = None,
        random_seed: int = 42,
    ) -> None:
        self.feature_list = list(feature_list or [])
        self.model_id = model_id or f"{self.__class__.__name__}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
        self.random_seed = random_seed
        self.calibrated_threshold: float = 0.5
        self.metadata: Optional[ModelMetadata] = None
        self.is_fitted: bool = False

    @abstractmethod
    def fit(self, X: pd.DataFrame, y: Optional[Union[pd.Series, np.ndarray]] = None) -> BaseAnomalyModel:
        """Fit the model on normal historical observations.
        
        Args:
            X: Training feature DataFrame.
            y: Ignored in unsupervised models.
        """
        pass

    @abstractmethod
    def score_samples(self, X: pd.DataFrame) -> np.ndarray:
        """Compute normalized anomaly scores in [0.0, 1.0] where higher values indicate greater abnormality.
        
        CRITICAL: Output is a normalized distance/anomaly metric, NOT an uncalibrated probability.
        """
        pass

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """Predict binary anomaly decisions (1 = Anomaly, 0 = Nominal) using calibrated_threshold."""
        scores = self.score_samples(X)
        return (scores >= self.calibrated_threshold).astype(int)

    def predict_result(self, X: pd.DataFrame) -> AnomalyPredictionResult:
        """Return structured prediction results with raw scores, normalized scores, and binary flags."""
        scores = self.score_samples(X)
        binary_preds = (scores >= self.calibrated_threshold).astype(int)
        raw_scores = getattr(self, "_last_raw_scores", scores)
        return AnomalyPredictionResult(
            raw_scores=raw_scores,
            anomaly_scores=scores,
            is_anomaly=binary_preds,
            calibrated_threshold=self.calibrated_threshold,
            model_id=self.model_id,
        )

    def calibrate_threshold(
        self,
        val_df: pd.DataFrame,
        y_val: np.ndarray,
        target_metric: str = "f1",
        candidate_percentiles: Optional[Sequence[float]] = None,
    ) -> float:
        """Calibrate optimal decision threshold on validation data.
        
        Args:
            val_df: Validation feature DataFrame.
            y_val: Binary ground truth labels (1 = Fault, 0 = Nominal/Genuine Event).
            target_metric: Optimization objective ('f1', 'precision', 'balanced').
            candidate_percentiles: Percentiles of validation scores to evaluate.
        """
        scores = self.score_samples(val_df)
        if len(scores) == 0 or len(np.unique(y_val)) < 2:
            self.calibrated_threshold = 0.5
            return self.calibrated_threshold

        percentiles = candidate_percentiles or np.linspace(1, 99, 99)
        candidates = np.percentile(scores, percentiles)
        best_threshold = 0.5
        best_score = -1.0

        for thresh in np.unique(candidates):
            preds = (scores >= thresh).astype(int)
            tp = np.sum((preds == 1) & (y_val == 1))
            fp = np.sum((preds == 1) & (y_val == 0))
            fn = np.sum((preds == 0) & (y_val == 1))

            precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
            recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
            f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

            metric_val = f1 if target_metric == "f1" else (precision if target_metric == "precision" else (precision + recall) / 2.0)
            if metric_val > best_score:
                best_score = metric_val
                best_threshold = float(thresh)

        self.calibrated_threshold = best_threshold
        if self.metadata:
            # Update metadata threshold
            meta_dict = self.metadata.model_dump()
            meta_dict["calibrated_threshold"] = best_threshold
            self.metadata = ModelMetadata(**meta_dict)

        return self.calibrated_threshold

    @abstractmethod
    def save(self, model_dir: Union[str, Path]) -> Path:
        """Serialize model weights and metadata JSON artifact to directory."""
        pass

    @classmethod
    @abstractmethod
    def load(cls, model_dir: Union[str, Path]) -> BaseAnomalyModel:
        """Deserialize model weights and restore metadata."""
        pass
