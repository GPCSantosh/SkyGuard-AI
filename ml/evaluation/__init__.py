"""SkyGuard AI — Machine Learning Evaluation Framework."""

from ml.evaluation.evaluator import ModelEvaluator
from ml.evaluation.metrics import (
    EvaluationMetricsBundle,
    EventMetrics,
    ObservationMetrics,
    compute_event_metrics,
    compute_observation_metrics,
)
from ml.evaluation.splitting import ChronologicalSplitter, DatasetSplitResult

__all__ = [
    "ChronologicalSplitter",
    "DatasetSplitResult",
    "ObservationMetrics",
    "EventMetrics",
    "EvaluationMetricsBundle",
    "ModelEvaluator",
    "compute_observation_metrics",
    "compute_event_metrics",
]
