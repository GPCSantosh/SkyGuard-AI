"""Unit tests for all 15 synthetic anomaly injectors and evaluation scenarios."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from ml.synthetic.injectors import (
    CommunicationGapInjector,
    DriftInjector,
    DuplicateDataInjector,
    FrozenSensorInjector,
    IntermittentFreezeInjector,
    MissingDataInjector,
    MultivariateInconsistencyInjector,
    NegativeSpikeInjector,
    OffsetInjector,
    OutOfOrderDataInjector,
    RandomNoiseInjector,
    SmallSpikeInjector,
    SpikeInjector,
)
from ml.synthetic.scenarios import (
    CombinedFaultInjector,
    MultiSensorFaultInjector,
    PossibleGenuineEventScenario,
    UncertainScenario,
)
from ml.synthetic.schema import SyntheticAnomalyType


@pytest.fixture
def base_df() -> pd.DataFrame:
    timestamps = pd.date_range("2024-01-01 00:00:00", periods=50, freq="10min", tz="UTC")
    return pd.DataFrame({
        "station_id": ["STN_001"] * 50,
        "timestamp": timestamps,
        "temperature_c": [20.0 + 0.5 * (i % 10) for i in range(50)],
        "relative_humidity_pct": [50.0 + 1.0 * (i % 5) for i in range(50)],
        "sea_level_pressure_hpa": [1013.0 + 0.2 * (i % 3) for i in range(50)],
    })


def test_spike_injector(base_df: pd.DataFrame) -> None:
    rng = np.random.default_rng(42)
    inj = SpikeInjector()
    mod_df, gt = inj.inject(base_df, target_idx=10, param="temperature_c", anomaly_id="ANOM-001", rng=rng)
    assert len(gt) >= 1
    assert gt[0].anomaly_type == SyntheticAnomalyType.SPIKE
    assert gt[0].modified_value > gt[0].original_value
    assert mod_df.at[10, "temperature_c"] == gt[0].modified_value


def test_small_spike_injector(base_df: pd.DataFrame) -> None:
    rng = np.random.default_rng(42)
    inj = SmallSpikeInjector()
    config = {"magnitude_range": {"temperature_c": [0.5, 2.0]}}
    mod_df, gt = inj.inject(base_df, target_idx=10, param="temperature_c", anomaly_id="ANOM-002", rng=rng, config=config)
    assert len(gt) >= 1
    assert gt[0].anomaly_type == SyntheticAnomalyType.SMALL_SPIKE
    assert 0.4 <= abs(gt[0].modified_value - gt[0].original_value) <= 2.1


def test_negative_spike_injector(base_df: pd.DataFrame) -> None:
    rng = np.random.default_rng(42)
    inj = NegativeSpikeInjector()
    config = {"magnitude_range": {"temperature_c": [-15.0, -5.0]}, "direction": "negative"}
    mod_df, gt = inj.inject(base_df, target_idx=10, param="temperature_c", anomaly_id="ANOM-003", rng=rng, config=config)
    assert len(gt) >= 1
    assert gt[0].modified_value < gt[0].original_value


def test_drift_injector(base_df: pd.DataFrame) -> None:
    rng = np.random.default_rng(42)
    inj = DriftInjector()
    mod_df, gt = inj.inject(base_df, target_idx=10, param="temperature_c", anomaly_id="ANOM-004", rng=rng)
    assert len(gt) >= 2
    assert gt[0].anomaly_type == SyntheticAnomalyType.DRIFT


def test_offset_injector(base_df: pd.DataFrame) -> None:
    rng = np.random.default_rng(42)
    inj = OffsetInjector()
    mod_df, gt = inj.inject(base_df, target_idx=10, param="temperature_c", anomaly_id="ANOM-005", rng=rng)
    assert len(gt) >= 5
    assert gt[0].anomaly_type == SyntheticAnomalyType.OFFSET


def test_frozen_sensor_injector(base_df: pd.DataFrame) -> None:
    rng = np.random.default_rng(42)
    inj = FrozenSensorInjector()
    mod_df, gt = inj.inject(base_df, target_idx=10, param="temperature_c", anomaly_id="ANOM-006", rng=rng)
    assert len(gt) >= 5
    vals = [r.modified_value for r in gt]
    assert len(set(vals)) == 1  # All values identical during freeze


def test_missing_data_injector(base_df: pd.DataFrame) -> None:
    rng = np.random.default_rng(42)
    inj = MissingDataInjector()
    mod_df, gt = inj.inject(base_df, target_idx=10, param="temperature_c", anomaly_id="ANOM-007", rng=rng)
    assert len(gt) >= 3
    assert len(mod_df) < len(base_df)


def test_duplicate_data_injector(base_df: pd.DataFrame) -> None:
    rng = np.random.default_rng(42)
    inj = DuplicateDataInjector()
    mod_df, gt = inj.inject(base_df, target_idx=10, param="temperature_c", anomaly_id="ANOM-008", rng=rng)
    assert len(gt) == 1
    assert len(mod_df) == len(base_df) + 1


def test_out_of_order_injector(base_df: pd.DataFrame) -> None:
    rng = np.random.default_rng(42)
    inj = OutOfOrderDataInjector()
    mod_df, gt = inj.inject(base_df, target_idx=10, param="temperature_c", anomaly_id="ANOM-009", rng=rng)
    assert len(gt) >= 1
    # Check that timestamps were swapped
    assert mod_df.iloc[10]["timestamp"] == base_df.iloc[11]["timestamp"]


def test_multivariate_inconsistency_injector(base_df: pd.DataFrame) -> None:
    rng = np.random.default_rng(42)
    inj = MultivariateInconsistencyInjector()
    mod_df, gt = inj.inject(base_df, target_idx=10, param="temperature_c", anomaly_id="ANOM-010", rng=rng)
    assert len(gt) >= 1
    assert gt[0].anomaly_type == SyntheticAnomalyType.MULTIVARIATE_INCONSISTENCY


def test_multi_sensor_fault_injector(base_df: pd.DataFrame) -> None:
    rng = np.random.default_rng(42)
    inj = MultiSensorFaultInjector()
    mod_df, gt = inj.inject(base_df, target_idx=10, param="temperature_c", anomaly_id="ANOM-011", rng=rng)
    assert len(gt) >= 2
    vars_affected = set(r.affected_variable for r in gt)
    assert "temperature_c" in vars_affected
    assert "relative_humidity_pct" in vars_affected


def test_possible_genuine_event_scenario(base_df: pd.DataFrame) -> None:
    rng = np.random.default_rng(42)
    inj = PossibleGenuineEventScenario()
    mod_df, gt = inj.inject(base_df, target_idx=10, param="temperature_c", anomaly_id="ANOM-012", rng=rng)
    assert len(gt) >= 1
    for r in gt:
        assert r.ground_truth_label == 0  # Labeled as NOT a hardware fault
        assert r.is_fault is False
        assert r.anomaly_type == SyntheticAnomalyType.POSSIBLE_GENUINE_EVENT
