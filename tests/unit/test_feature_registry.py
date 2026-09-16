"""Unit tests for FeatureRegistry and feature definitions."""

from __future__ import annotations

import pytest

from ml.features.registry import (
    BASELINE_FEATURE_SET,
    FEATURE_SET_A_RAW_TEMPORAL,
    FEATURE_SET_B_TEMPORAL_ROLLING,
    FEATURE_SET_C_MULTIVARIATE,
    FEATURE_SET_D_SPATIAL,
    FeatureCategory,
    FeatureDefinition,
    FeatureRegistry,
)


def test_feature_registry_lookup_and_categories() -> None:
    registry = FeatureRegistry()

    # Check key features exist
    t_feat = registry.get("temperature_c")
    assert t_feat is not None
    assert t_feat.category == FeatureCategory.RAW
    assert t_feat.allowed_for_training is True

    sin_h = registry.get("sin_hour")
    assert sin_h is not None
    assert sin_h.category == FeatureCategory.TEMPORAL

    roll_t = registry.get("temperature_c_rolling_mean_1h")
    assert roll_t is not None
    assert roll_t.category == FeatureCategory.ROLLING

    # Category filtering
    spatial_feats = registry.list_features(category=FeatureCategory.SPATIAL)
    assert len(spatial_feats) >= 5
    for sf in spatial_feats:
        assert sf.category == FeatureCategory.SPATIAL


def test_ablation_feature_sets_integrity() -> None:
    registry = FeatureRegistry()
    all_names = set(registry.get_feature_names())

    for f_set in [
        FEATURE_SET_A_RAW_TEMPORAL,
        FEATURE_SET_B_TEMPORAL_ROLLING,
        FEATURE_SET_C_MULTIVARIATE,
        FEATURE_SET_D_SPATIAL,
        BASELINE_FEATURE_SET,
    ]:
        assert len(f_set) > 0
        for fname in f_set:
            assert fname in all_names, f"Feature {fname} in feature set not found in registry!"


def test_register_custom_feature() -> None:
    registry = FeatureRegistry()
    custom = FeatureDefinition(
        name="custom_metric",
        category=FeatureCategory.MULTIVARIATE,
        description="Custom sensor ratio",
        allowed_for_training=False,
    )
    registry.register(custom)
    assert registry.get("custom_metric") == custom
    assert "custom_metric" not in registry.get_feature_names(training_only=True)
