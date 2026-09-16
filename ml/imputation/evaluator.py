"""Evaluation and benchmarking harness for Data Imputation and Correction Recommendations.

Measures reconstruction accuracy against synthetic ground truth (MAE, RMSE, coverage,
unsafe corrections) and validates clean-data protection rate.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Sequence
import numpy as np
import pandas as pd
from pydantic import BaseModel, ConfigDict, Field

from ml.decision.schema import HybridDecisionType
from ml.imputation.correction_engine import CorrectionRecommendationEngine
from ml.imputation.imputer import MissingDataImputer
from ml.imputation.schema import ImputationStatus, RecommendationStatus


class ReconstructionBenchmarkMetrics(BaseModel):
    """Evaluation metrics comparing recommended/imputed values to clean ground truth."""
    model_config = ConfigDict(frozen=True)

    total_evaluated_points: int = Field(..., description="Total points evaluated.")
    total_anomalous_points: int = Field(..., description="Total injected anomaly ground-truth points.")
    total_clean_points: int = Field(..., description="Total uncorrupted clean points.")
    
    # Recommendation counts
    candidates_count: int = Field(0, description="Count of CORRECTION_CANDIDATE recommendations.")
    review_count: int = Field(0, description="Count of REVIEW_RECOMMENDED recommendations.")
    insufficient_evidence_count: int = Field(0, description="Count of INSUFFICIENT_EVIDENCE outcomes.")
    no_correction_count: int = Field(0, description="Count of NO_CORRECTION_RECOMMENDED outcomes.")
    
    # Accuracy vs Clean Ground Truth (on anomalous points where recommendation was made)
    mae: Optional[float] = Field(None, description="Mean Absolute Error vs clean ground truth.")
    rmse: Optional[float] = Field(None, description="Root Mean Squared Error vs clean ground truth.")
    relative_error_pct: Optional[float] = Field(None, description="Mean relative error percentage.")
    
    # Safety and Protection Rates
    correction_coverage: float = Field(..., description="Fraction of anomalies receiving candidate/review recommendations.")
    unsafe_correction_rate: float = Field(0.0, description="Fraction of recommendations increasing error vs clean ground truth.")
    unnecessary_correction_rate: float = Field(0.0, description="Fraction of clean points receiving unwanted corrections.")


class ImputationEvaluator:
    """Evaluates imputation and correction engines against known synthetic and clean series."""

    def __init__(
        self,
        imputer: Optional[MissingDataImputer] = None,
        correction_engine: Optional[CorrectionRecommendationEngine] = None,
    ) -> None:
        self.imputer = imputer or MissingDataImputer()
        self.correction_engine = correction_engine or CorrectionRecommendationEngine()

    def evaluate_synthetic_reconstruction(
        self,
        clean_values: Sequence[float],
        corrupted_values: Sequence[Optional[float]],
        anomaly_labels: Sequence[int],  # 1 for anomalous/injected, 0 for clean
        timestamps: Sequence[Any],
        station_id: str = "TEST_STATION",
        target_variable: str = "temperature_c",
        neighbor_data_pool: Optional[Sequence[Dict[str, Any]]] = None,
    ) -> ReconstructionBenchmarkMetrics:
        """Benchmark correction recommendation accuracy against clean ground truth."""
        n_points = len(clean_values)
        history: List[float] = []

        total_anom = sum(1 for lbl in anomaly_labels if lbl == 1)
        total_clean = n_points - total_anom

        candidates = 0
        reviews = 0
        insufficient = 0
        no_corr = 0

        abs_errors: List[float] = []
        sq_errors: List[float] = []
        rel_errors: List[float] = []
        unsafe_corrections = 0
        unnecessary_corrections = 0

        for i in range(n_points):
            t = timestamps[i]
            y_clean = clean_values[i]
            y_corrupt = corrupted_values[i]
            is_anom = anomaly_labels[i] == 1

            # Handle missing vs corrupted
            if y_corrupt is None or (isinstance(y_corrupt, float) and math.isnan(y_corrupt)):
                # Evaluate missing imputation
                imp_rec = self.imputer.impute_missing_value(
                    station_id=station_id,
                    timestamp=t,
                    target_variable=target_variable,
                    gap_duration_minutes=5.0,
                    consecutive_missing_steps=1,
                    temporal_history=list(history),
                    neighbor_observations=neighbor_data_pool,
                )
                if imp_rec.status == ImputationStatus.IMPUTED and imp_rec.imputed_value is not None:
                    y_est = imp_rec.imputed_value
                    err = abs(y_clean - y_est)
                    abs_errors.append(err)
                    sq_errors.append(err ** 2)
                    if abs(y_clean) > 1e-3:
                        rel_errors.append(err / abs(y_clean) * 100.0)
                    candidates += 1
                    history.append(y_est)
                else:
                    insufficient += 1
            else:
                # Suspicious observation correction evaluation
                # Decision proxy: if anomalous, simulated decision is PROBABLE_SENSOR_ANOMALY
                dec_type = (
                    HybridDecisionType.PROBABLE_SENSOR_ANOMALY
                    if is_anom
                    else HybridDecisionType.NORMAL
                )

                rec = self.correction_engine.recommend_for_variable(
                    station_id=station_id,
                    timestamp=t,
                    target_variable=target_variable,
                    observed_value=float(y_corrupt),
                    decision_type=dec_type,
                    temporal_history=list(history),
                    neighbor_observations=neighbor_data_pool,
                )

                if rec.status == RecommendationStatus.CORRECTION_CANDIDATE:
                    candidates += 1
                elif rec.status == RecommendationStatus.REVIEW_RECOMMENDED:
                    reviews += 1
                elif rec.status == RecommendationStatus.INSUFFICIENT_EVIDENCE:
                    insufficient += 1
                elif rec.status == RecommendationStatus.NO_CORRECTION_RECOMMENDED:
                    no_corr += 1

                if is_anom:
                    if rec.recommended_value is not None:
                        y_est = rec.recommended_value
                        rec_err = abs(y_clean - y_est)
                        corrupt_err = abs(y_clean - y_corrupt)
                        
                        abs_errors.append(rec_err)
                        sq_errors.append(rec_err ** 2)
                        if abs(y_clean) > 1e-3:
                            rel_errors.append(rec_err / abs(y_clean) * 100.0)

                        if rec_err > corrupt_err + 0.5:
                            unsafe_corrections += 1
                else:
                    # Clean point protection check
                    if rec.status in (RecommendationStatus.CORRECTION_CANDIDATE, RecommendationStatus.REVIEW_RECOMMENDED):
                        unnecessary_corrections += 1

                # Feed observed or clean value into history
                history.append(float(y_corrupt) if not is_anom else y_clean)

        evaluated_recs_count = len(abs_errors)
        mae = float(np.mean(abs_errors)) if abs_errors else None
        rmse = float(math.sqrt(np.mean(sq_errors))) if sq_errors else None
        rel_err = float(np.mean(rel_errors)) if rel_errors else None

        coverage = (candidates + reviews) / max(1, total_anom)
        unsafe_rate = unsafe_corrections / max(1, evaluated_recs_count)
        unnecessary_rate = unnecessary_corrections / max(1, total_clean)

        return ReconstructionBenchmarkMetrics(
            total_evaluated_points=n_points,
            total_anomalous_points=total_anom,
            total_clean_points=total_clean,
            candidates_count=candidates,
            review_count=reviews,
            insufficient_evidence_count=insufficient,
            no_correction_count=no_corr,
            mae=round(mae, 3) if mae is not None else None,
            rmse=round(rmse, 3) if rmse is not None else None,
            relative_error_pct=round(rel_err, 2) if rel_err is not None else None,
            correction_coverage=round(coverage, 3),
            unsafe_correction_rate=round(unsafe_rate, 4),
            unnecessary_correction_rate=round(unnecessary_rate, 4),
        )
