"""SkyGuard AI — Feature Engineering Layer.

Provides modular temporal, time-aware rolling window, rate-of-change, persistence,
multivariate consistency, and geodesic spatial neighbor feature extractors.
"""

from ml.features.change import RateOfChangeExtractor
from ml.features.consistency import ConsistencyExtractor
from ml.features.pipeline import FeaturePipeline, FeaturePipelineConfig
from ml.features.rolling import RollingWindowExtractor
from ml.features.spatial import SpatialNeighborExtractor
from ml.features.temporal import TemporalFeatureExtractor

__all__ = [
    "TemporalFeatureExtractor",
    "RollingWindowExtractor",
    "RateOfChangeExtractor",
    "ConsistencyExtractor",
    "SpatialNeighborExtractor",
    "FeaturePipeline",
    "FeaturePipelineConfig",
]
