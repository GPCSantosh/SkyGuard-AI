"""Unit tests for synthetic multi-station spatial scenarios (A, B, C, D)."""

from __future__ import annotations

import pandas as pd
import pytest

from ml.spatial.engine import SpatialContextEngine
from ml.spatial.schema import SpatialContextCategory
from ml.spatial.topology import SpatialNetworkTopology, StationNode
from ml.synthetic.spatial_scenarios import SpatialScenarioGenerator


@pytest.fixture
def scenario_test_setup():
    stations = {
        "S_TARGET": StationNode(station_id="S_TARGET", name="Target", latitude=28.50, longitude=77.20, elevation_m=200.0),
        "S_NEAR1": StationNode(station_id="S_NEAR1", name="Near 1", latitude=28.55, longitude=77.22, elevation_m=202.0),
        "S_NEAR2": StationNode(station_id="S_NEAR2", name="Near 2", latitude=28.48, longitude=77.25, elevation_m=198.0),
        "S_NEAR3": StationNode(station_id="S_NEAR3", name="Near 3", latitude=28.52, longitude=77.15, elevation_m=205.0),
    }
    topology = SpatialNetworkTopology(stations=stations)
    generator = SpatialScenarioGenerator(topology=topology)
    engine = SpatialContextEngine(topology=topology, max_distance_km=50.0, min_valid_neighbors=2)

    # Create synthetic multi-station baseline dataset (10 timesteps)
    timestamps = pd.date_range("2024-06-01 10:00", periods=10, freq="30min", tz="UTC")
    rows = []
    for s_id in stations:
        for t in timestamps:
            rows.append({
                "station_id": s_id,
                "timestamp": t,
                "temperature_c": 30.0,
                "relative_humidity_pct": 50.0,
                "sea_level_pressure_hpa": 1005.0,
                "elevation_m": stations[s_id].elevation_m,
            })
    base_df = pd.DataFrame(rows)

    return topology, generator, engine, base_df, timestamps[4]


def test_scenario_a_local_sensor_anomaly(scenario_test_setup):
    """Scenario A: Local sensor spike/offset produces LOCAL_ONLY contextual classification."""
    topology, generator, engine, base_df, eval_ts = scenario_test_setup

    mod_df, gt = generator.generate_scenario_a_local_anomaly(
        df=base_df,
        target_station_id="S_TARGET",
        start_timestamp=eval_ts,
        duration_steps=4,
        magnitude=8.0,
        variable="temperature_c",
    )

    assert len(gt) == 4
    assert all(r.ground_truth_label == 1 and r.is_fault for r in gt)

    feat_df = engine.extract_features_multi_station(mod_df)
    target_eval = feat_df[(feat_df["station_id"] == "S_TARGET") & (feat_df["timestamp"] >= eval_ts)].head(4)

    # Must classify as LOCAL_ONLY due to isolated target deviation
    categories = target_eval["spatial_context_category"].tolist()
    assert all(c == SpatialContextCategory.LOCAL_ONLY.value for c in categories)
    # Target delta from neighbor mean must be ~+8.0°C
    assert (target_eval["spatial_temp_delta_from_neighbor_mean"] > 7.0).all()


def test_scenario_b_regional_event(scenario_test_setup):
    """Scenario B: Coherent regional weather event produces REGIONAL_PATTERN classification."""
    topology, generator, engine, base_df, eval_ts = scenario_test_setup

    mod_df, gt = generator.generate_scenario_b_regional_event(
        df=base_df,
        target_station_id="S_TARGET",
        start_timestamp=eval_ts,
        duration_steps=4,
        temp_change_c=-5.0,
        rh_change_pct=25.0,
        slp_change_hpa=-4.0,
    )

    # Ground truth records must be marked is_fault=False
    assert len(gt) > 0
    assert all(r.ground_truth_label == 0 and not r.is_fault for r in gt)

    feat_df = engine.extract_features_multi_station(mod_df)
    target_eval = feat_df[(feat_df["station_id"] == "S_TARGET") & (feat_df["timestamp"] >= eval_ts)].head(4)

    # Must classify as REGIONAL_PATTERN or LOCAL_CLUSTER because neighbors share the shift
    categories = target_eval["spatial_context_category"].tolist()
    assert all(c in (SpatialContextCategory.REGIONAL_PATTERN.value, SpatialContextCategory.LOCAL_CLUSTER.value) for c in categories)


def test_scenario_c_mixed_event(scenario_test_setup):
    """Scenario C: Mixed regional weather + target sensor fault retains deviation evidence."""
    topology, generator, engine, base_df, eval_ts = scenario_test_setup

    mod_df, gt = generator.generate_scenario_c_mixed_event(
        df=base_df,
        target_station_id="S_TARGET",
        start_timestamp=eval_ts,
        duration_steps=4,
        regional_temp_change_c=3.0,
        target_fault_temp_delta=8.0,
    )

    feat_df = engine.extract_features_multi_station(mod_df)
    target_eval = feat_df[(feat_df["station_id"] == "S_TARGET") & (feat_df["timestamp"] >= eval_ts)].head(4)

    # Target temperature should be elevated above neighbor mean by ~+8.0°C
    deltas = target_eval["spatial_temp_delta_from_neighbor_mean"].tolist()
    assert all(d > 6.0 for d in deltas)


def test_scenario_d_isolated_station_outage(scenario_test_setup):
    """Scenario D: Neighbor dropout correctly triggers INSUFFICIENT_CONTEXT."""
    topology, generator, engine, base_df, eval_ts = scenario_test_setup

    outage_df = generator.generate_scenario_d_isolated_outage(
        df=base_df,
        target_station_id="S_TARGET",
        start_timestamp=eval_ts,
        duration_steps=4,
    )

    feat_df = engine.extract_features_multi_station(outage_df)
    target_eval = feat_df[(feat_df["station_id"] == "S_TARGET") & (feat_df["timestamp"] >= eval_ts)].head(4)

    categories = target_eval["spatial_context_category"].tolist()
    valid_counts = target_eval["spatial_valid_neighbor_count"].tolist()

    assert all(c == SpatialContextCategory.INSUFFICIENT_CONTEXT.value for c in categories)
    assert all(vc == 0 for vc in valid_counts)
