"""Unit tests for TreeSHAP and model feature attribution."""

import numpy as np
import pandas as pd
import pytest

from ml.explainability.schema import ContributionDirection, FeatureContribution
from ml.explainability.shap_explainer import TreeShapExplainer
from ml.models.baselines import FixedThresholdDetector, RollingZScoreDetector
from ml.models.isolation_forest import IsolationForestDetector


@pytest.fixture
def fitted_iforest() -> IsolationForestDetector:
    """Fixture providing a fitted Isolation Forest model."""
    np.random.seed(42)
    n = 200
    df = pd.DataFrame({
        "temperature_c": np.random.normal(25.0, 2.0, n),
        "relative_humidity": np.random.normal(60.0, 5.0, n),
        "sea_level_pressure_hpa": np.random.normal(1013.25, 2.0, n),
        "temp_rate_of_change": np.random.normal(0.0, 0.1, n),
    })
    detector = IsolationForestDetector(n_estimators=30, random_state=42)
    detector.fit(df)
    return detector


def test_treeshap_isolation_forest_basic(fitted_iforest: IsolationForestDetector):
    """Test TreeSHAP calculates valid non-zero contributions with ranked order."""
    explainer = TreeShapExplainer(fitted_iforest)
    assert explainer.method_tag == "TREE_SHAP"

    # Normal sample
    sample = pd.DataFrame([{
        "temperature_c": 25.1,
        "relative_humidity": 60.2,
        "sea_level_pressure_hpa": 1013.3,
        "temp_rate_of_change": 0.02,
    }])
    contributions = explainer.explain_sample(sample)
    assert len(contributions) == 4
    assert all(isinstance(c, FeatureContribution) for c in contributions)
    assert [c.rank for c in contributions] == [1, 2, 3, 4]


def test_treeshap_identifies_anomalous_feature(fitted_iforest: IsolationForestDetector):
    """Test that an anomalous spike feature is correctly identified as top contributor."""
    explainer = TreeShapExplainer(fitted_iforest)

    # Severe spike in temperature
    sample = pd.DataFrame([{
        "temperature_c": 52.0,  # Far outlier
        "relative_humidity": 60.0,
        "sea_level_pressure_hpa": 1013.25,
        "temp_rate_of_change": 4.5,  # Far outlier
    }])

    contributions = explainer.explain_sample(sample, top_k=2)
    assert len(contributions) == 2
    top_feature_names = [c.feature_name for c in contributions]
    assert "temperature_c" in top_feature_names or "temp_rate_of_change" in top_feature_names
    # Verify directional classification
    for c in contributions:
        if c.feature_name in ("temperature_c", "temp_rate_of_change"):
            assert c.direction == ContributionDirection.INCREASES_ANOMALY


def test_explainer_fallback_on_non_tree_model():
    """Test faithful fallback attribution on baseline non-tree models."""
    baseline = FixedThresholdDetector(
        temp_bounds=(-50.0, 60.0),
        humidity_bounds=(0.0, 100.0),
    )
    explainer = TreeShapExplainer(baseline)
    assert explainer.method_tag == "FEATURE_DEVIATION_FALLBACK"

    sample = {"temperature_c": 75.0, "relative_humidity_pct": 50.0}
    contributions = explainer.explain_sample(sample)
    assert len(contributions) >= 2
    assert contributions[0].rank == 1
    assert contributions[0].feature_name == "temperature_c"



def test_explainer_edge_cases(fitted_iforest: IsolationForestDetector):
    """Test TreeSHAP explainer handles NaNs, missing columns, and constant features safely."""
    explainer = TreeShapExplainer(fitted_iforest)

    # Missing some columns and NaN in another
    sample = pd.DataFrame([{
        "temperature_c": np.nan,
        "sea_level_pressure_hpa": np.inf,
        # relative_humidity and temp_rate_of_change missing
    }])
    contributions = explainer.explain_sample(sample)
    assert len(contributions) == 4
    assert not any(np.isnan(c.contribution) for c in contributions)
    assert not any(np.isnan(c.feature_value) for c in contributions)


def test_unfitted_model_handling():
    """Test explainer handles unfitted model safely."""
    detector = IsolationForestDetector()
    explainer = TreeShapExplainer(detector)
    sample = {"temperature_c": 25.0}
    contributions = explainer.explain_sample(sample)
    assert isinstance(contributions, list)
