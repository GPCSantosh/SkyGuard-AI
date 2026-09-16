"""SkyGuard AI — Synthetic Anomaly Injection & Evaluation Engine.

Provides parameterized fault injection, double-blind ground truth isolation,
evaluation scenarios, and high-cadence 5-minute stream simulation.
"""

from ml.synthetic.engine import SyntheticAnomalyEngine
from ml.synthetic.injectors import BaseAnomalyInjector
from ml.synthetic.schema import (
    AnomalyInjectionConfig,
    GroundTruthRecord,
    InjectedDatasetResult,
    SyntheticAnomalyType,
)
from ml.synthetic.stream_simulator import StreamSimulator

__all__ = [
    "SyntheticAnomalyType",
    "GroundTruthRecord",
    "AnomalyInjectionConfig",
    "InjectedDatasetResult",
    "BaseAnomalyInjector",
    "SyntheticAnomalyEngine",
    "StreamSimulator",
]
