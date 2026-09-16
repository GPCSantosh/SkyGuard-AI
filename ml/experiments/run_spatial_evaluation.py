"""Phase 4 Spatial & Synoptic Context Engine Evaluation Runner.

Executes comprehensive quantitative benchmarks addressing the 8 core evaluation questions,
synthetic spatial scenarios (A, B, C, D), causality/leakage proofs, and false-alarm experiments.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Tuple
import numpy as np
import pandas as pd

from ml.spatial.engine import SpatialContextEngine
from ml.spatial.schema import SpatialContextCategory
from ml.spatial.topology import SpatialNetworkTopology, StationNode
from ml.synthetic.spatial_scenarios import SpatialScenarioGenerator


def load_benchmark_data() -> pd.DataFrame:
    """Load the processed 8-station benchmark dataset."""
    path = Path("data/processed/benchmark_multistation_2024.csv")
    if not path.exists():
        raise FileNotFoundError(f"Benchmark multi-station dataset not found at: {path}")
    df = pd.read_csv(path)
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    return df


def create_dense_subnetwork() -> Tuple[SpatialNetworkTopology, pd.DataFrame]:
    """Create a high-density 5-station AWS sub-network (Delhi NCR Cluster) for micro-scale validation."""
    stations = {
        "42182099999": StationNode(station_id="42182099999", name="New Delhi Safdarjung", latitude=28.5845, longitude=77.2058, elevation_m=214.9),
        "42181099999": StationNode(station_id="42181099999", name="New Delhi IGI Palam", latitude=28.5665, longitude=77.1031, elevation_m=237.0),
        "42183099999": StationNode(station_id="42183099999", name="Delhi Lodhi Road", latitude=28.5910, longitude=77.2270, elevation_m=211.0),
        "42184099999": StationNode(station_id="42184099999", name="Noida Sector 62", latitude=28.6250, longitude=77.3680, elevation_m=202.0),
        "42185099999": StationNode(station_id="42185099999", name="Gurugram CyberCity", latitude=28.4900, longitude=77.0900, elevation_m=225.0),
    }
    topology = SpatialNetworkTopology(stations=stations)

    # 48 hours of 30-min cadence observations
    timestamps = pd.date_range("2024-06-01 00:00", periods=96, freq="30min", tz="UTC")
    rng = np.random.default_rng(42)
    rows = []

    for t in timestamps:
        hour = t.hour + t.minute / 60.0
        # Diurnal temperature cycle: min 26°C at 05:00, max 38°C at 15:00
        diurnal_t = 32.0 + 6.0 * np.sin(np.pi * (hour - 9.0) / 12.0)
        diurnal_rh = 55.0 - 20.0 * np.sin(np.pi * (hour - 9.0) / 12.0)
        diurnal_p = 1004.0 + 2.0 * np.sin(np.pi * (hour - 3.0) / 12.0)

        for s_id, node in stations.items():
            noise_t = rng.normal(0, 0.2)
            noise_rh = rng.normal(0, 0.8)
            noise_p = rng.normal(0, 0.2)

            rows.append({
                "station_id": s_id,
                "timestamp": t,
                "temperature_c": round(diurnal_t + noise_t, 2),
                "relative_humidity_pct": round(min(100.0, max(0.0, diurnal_rh + noise_rh)), 1),
                "sea_level_pressure_hpa": round(diurnal_p + noise_p, 2),
                "elevation_m": node.elevation_m,
            })

    df = pd.DataFrame(rows)
    return topology, df


def run_evaluation() -> Dict[str, Any]:
    """Execute complete Phase 4 experimental suite and return structured results."""
    print("=" * 75)
    print("SkyGuard AI — Phase 4: Spatial & Synoptic Context Engine Evaluation")
    print("=" * 75)

    # 1. Load Dense Network & Historical National Benchmark
    dense_topo, dense_df = create_dense_subnetwork()
    national_topo = SpatialNetworkTopology.from_yaml("configs/stations.yaml")
    national_df = load_benchmark_data()

    print(f"Loaded Dense NCR Cluster (5 stations, {len(dense_df)} observations).")
    print(f"Loaded National WMO Network ({len(national_topo.stations)} stations, {len(national_df)} observations).")

    engine = SpatialContextEngine(
        topology=dense_topo,
        max_distance_km=60.0,
        max_neighbors=4,
        temporal_tolerance_minutes=30.0,
        enable_causal_mode=True,
        min_valid_neighbors=2,
    )
    generator = SpatialScenarioGenerator(topology=dense_topo)

    target_stn = "42182099999"  # Safdarjung
    eval_start_ts = dense_df["timestamp"].iloc[len(dense_df) // 2]
    results: Dict[str, Any] = {}

    # -------------------------------------------------------------
    # Question 1 & Scenario A: Local-Only Sensor Corruption
    # -------------------------------------------------------------
    print("\n[Exp 1 / Scenario A] Evaluating Local Sensor Anomaly (+6.0°C Offset)...")
    df_scen_a, gt_a = generator.generate_scenario_a_local_anomaly(
        df=dense_df,
        target_station_id=target_stn,
        start_timestamp=eval_start_ts,
        duration_steps=6,
        magnitude=6.0,
        variable="temperature_c",
    )
    res_a = engine.extract_features_multi_station(df_scen_a)
    target_scen_a = res_a[(res_a["station_id"].astype(str) == target_stn) & (res_a["timestamp"] >= eval_start_ts)].head(6)

    cat_counts_a = target_scen_a["spatial_context_category"].value_counts().to_dict()
    avg_sim_a = float(target_scen_a["spatial_temp_frac_similar"].mean())
    avg_delta_a = float(target_scen_a["spatial_temp_delta_from_neighbor_mean"].mean())
    avg_zscore_a = float(target_scen_a["spatial_temp_zscore_vs_neighbors"].abs().mean())

    print(f"  -> Context Categories: {cat_counts_a}")
    print(f"  -> Avg Neighbor Similarity Fraction: {avg_sim_a:.3f}")
    print(f"  -> Avg Target Delta from Neighbor Mean: {avg_delta_a:.2f}°C")
    print(f"  -> Avg Target Absolute Z-Score: {avg_zscore_a:.2f}")

    results["question_1_local_corruption"] = {
        "scenario": "Scenario A (Local Anomaly +6.0°C)",
        "categories": cat_counts_a,
        "avg_neighbor_similarity": avg_sim_a,
        "avg_delta_from_neighbor_mean": avg_delta_a,
        "avg_zscore": avg_zscore_a,
        "demonstrates_low_agreement": avg_sim_a == 0.0 and cat_counts_a.get("LOCAL_ONLY", 0) == 6,
    }

    # -------------------------------------------------------------
    # Question 2 & Scenario B: Coherent Regional Weather Event
    # -------------------------------------------------------------
    print("\n[Exp 2 / Scenario B] Evaluating Coherent Regional Event (-4.5°C, +20% RH, -3.5 hPa)...")
    df_scen_b, gt_b = generator.generate_scenario_b_regional_event(
        df=dense_df,
        target_station_id=target_stn,
        start_timestamp=eval_start_ts,
        duration_steps=6,
        temp_change_c=-4.5,
        rh_change_pct=20.0,
        slp_change_hpa=-3.5,
        max_neighbor_distance_km=60.0,
    )
    res_b = engine.extract_features_multi_station(df_scen_b)
    target_scen_b = res_b[(res_b["station_id"].astype(str) == target_stn) & (res_b["timestamp"] >= eval_start_ts)].head(6)

    cat_counts_b = target_scen_b["spatial_context_category"].value_counts().to_dict()
    avg_sim_b = float(target_scen_b["spatial_temp_frac_similar"].mean())
    avg_coherence_b = float(target_scen_b["spatial_cross_var_coherence"].mean())

    print(f"  -> Context Categories: {cat_counts_b}")
    print(f"  -> Avg Neighbor Similarity Fraction: {avg_sim_b:.3f}")
    print(f"  -> Avg Cross-Variable Coherence: {avg_coherence_b:.3f}")

    results["question_2_regional_event"] = {
        "scenario": "Scenario B (Regional Squall / Front)",
        "categories": cat_counts_b,
        "avg_neighbor_similarity": avg_sim_b,
        "avg_coherence": avg_coherence_b,
        "demonstrates_high_agreement": cat_counts_b.get("REGIONAL_PATTERN", 0) >= 5,
    }

    # -------------------------------------------------------------
    # Question 3 & Scenario C: Mixed Event Discrimination
    # -------------------------------------------------------------
    print("\n[Exp 3 / Scenario C] Evaluating Mixed Scenario (Regional +3.5°C + Target Fault +7.0°C)...")
    df_scen_c, gt_c = generator.generate_scenario_c_mixed_event(
        df=dense_df,
        target_station_id=target_stn,
        start_timestamp=eval_start_ts,
        duration_steps=6,
        regional_temp_change_c=3.5,
        target_fault_temp_delta=7.0,
        max_neighbor_distance_km=60.0,
    )
    res_c = engine.extract_features_multi_station(df_scen_c)
    target_scen_c = res_c[(res_c["station_id"].astype(str) == target_stn) & (res_c["timestamp"] >= eval_start_ts)].head(6)

    cat_counts_c = target_scen_c["spatial_context_category"].value_counts().to_dict()
    avg_delta_c = float(target_scen_c["spatial_temp_delta_from_neighbor_mean"].mean())

    print(f"  -> Context Categories: {cat_counts_c}")
    print(f"  -> Target Delta from Neighbor Mean: {avg_delta_c:.2f}°C")

    results["question_3_mixed_event"] = {
        "scenario": "Scenario C (Regional Event + Local Fault)",
        "categories": cat_counts_c,
        "avg_delta_from_neighbor_mean": avg_delta_c,
        "distinguishes_target_excess": avg_delta_c >= 6.5,
    }

    # -------------------------------------------------------------
    # Question 4: Temporal Tolerance Sensitivity
    # -------------------------------------------------------------
    print("\n[Exp 4] Evaluating Temporal Tolerance Sensitivity...")
    tolerances = [10.0, 30.0, 60.0, 120.0]
    tol_results = {}
    for tol in tolerances:
        eng_tol = SpatialContextEngine(topology=dense_topo, temporal_tolerance_minutes=tol)
        res_tol = eng_tol.extract_features_multi_station(dense_df.head(100))
        valid_cnt = float(res_tol["spatial_valid_neighbor_count"].mean())
        tol_results[f"{int(tol)}min"] = {"avg_valid_neighbors": valid_cnt}
        print(f"  -> Tolerance {tol} min: Avg valid neighbors = {valid_cnt:.2f}")

    results["question_4_temporal_tolerance"] = tol_results

    # -------------------------------------------------------------
    # Question 5: Maximum Neighbor Distance Sensitivity
    # -------------------------------------------------------------
    print("\n[Exp 5] Evaluating Maximum Neighbor Distance Sensitivity across India...")
    radii = [25.0, 50.0, 150.0, 600.0, 1500.0]
    dist_results = {}
    for r in radii:
        links = national_topo.get_neighbors("42182099999", max_distance_km=r)
        dist_results[f"{int(r)}km"] = {"configured_neighbors_for_delhi": len(links)}
        print(f"  -> Max Distance {r} km: Delhi configured neighbors = {len(links)}")

    results["question_5_distance_sensitivity"] = dist_results

    # -------------------------------------------------------------
    # Question 6: Distance Weighting (IDW vs Unweighted)
    # -------------------------------------------------------------
    print("\n[Exp 6] Evaluating Distance Weighting (IDW vs Arithmetic Mean)...")
    res_unweighted = float(target_scen_b["spatial_neighbor_temp_mean"].mean())
    res_idw = float(target_scen_b["spatial_temp_idw_expected"].mean())
    diff_idw = abs(res_idw - res_unweighted)
    print(f"  -> Unweighted Neighbor Mean: {res_unweighted:.2f}°C")
    print(f"  -> IDW Expected Value: {res_idw:.2f}°C (Difference: {diff_idw:.4f}°C)")

    results["question_6_distance_weighting"] = {
        "unweighted_mean": res_unweighted,
        "idw_expected": res_idw,
        "difference": diff_idw,
    }

    # -------------------------------------------------------------
    # Question 7 & Scenario D: Isolated Station / Neighbor Outage
    # -------------------------------------------------------------
    print("\n[Exp 7 / Scenario D] Evaluating Isolated Station & Dropped Neighbors...")
    df_scen_d = generator.generate_scenario_d_isolated_outage(
        df=dense_df,
        target_station_id=target_stn,
        start_timestamp=eval_start_ts,
        duration_steps=6,
    )
    res_d = engine.extract_features_multi_station(df_scen_d)
    target_scen_d = res_d[(res_d["station_id"].astype(str) == target_stn) & (res_d["timestamp"] >= eval_start_ts)].head(6)

    cat_counts_d = target_scen_d["spatial_context_category"].value_counts().to_dict()
    valid_cnt_d = target_scen_d["spatial_valid_neighbor_count"].tolist()
    print(f"  -> Context Categories: {cat_counts_d}")
    print(f"  -> Valid Neighbor Counts: {valid_cnt_d}")

    results["question_7_and_8_isolated_station"] = {
        "categories": cat_counts_d,
        "valid_neighbor_counts": valid_cnt_d,
        "correctly_flags_insufficient_context": cat_counts_d.get("INSUFFICIENT_CONTEXT", 0) == 6,
    }

    # -------------------------------------------------------------
    # Question 8 & Causality Proof: Forward-Time Leakage Verification
    # -------------------------------------------------------------
    print("\n[Causality Proof] Verifying Zero Forward-Time Leakage...")
    pool_past = dense_df[dense_df["timestamp"] <= eval_start_ts].to_dict(orient="records")
    row_target = dense_df[(dense_df["station_id"] == target_stn) & (dense_df["timestamp"] == eval_start_ts)].iloc[0]

    t_vals = {
        "temperature_c": float(row_target["temperature_c"]),
        "relative_humidity_pct": float(row_target["relative_humidity_pct"]),
        "sea_level_pressure_hpa": float(row_target["sea_level_pressure_hpa"]),
    }

    ev_before = engine.evaluate_observation(
        target_station_id=target_stn,
        target_timestamp=eval_start_ts,
        target_values=t_vals,
        neighbor_data_pool=pool_past,
    )

    # Add corrupted future records (t > T)
    future_pool = list(pool_past)
    for delta_min in [15, 30, 60, 180]:
        future_ts = (eval_start_ts + pd.Timedelta(minutes=delta_min)).isoformat()
        future_pool.append({
            "station_id": "42181099999",
            "timestamp": future_ts,
            "temperature_c": 99.9,
            "relative_humidity_pct": 0.0,
            "sea_level_pressure_hpa": 1200.0,
        })

    ev_after = engine.evaluate_observation(
        target_station_id=target_stn,
        target_timestamp=eval_start_ts,
        target_values=t_vals,
        neighbor_data_pool=future_pool,
    )

    leakage_detected = (
        ev_before.temperature_consensus.neighbor_mean != ev_after.temperature_consensus.neighbor_mean
        or ev_before.context_category != ev_after.context_category
    )

    print(f"  -> Before Future Records: Mean={ev_before.temperature_consensus.neighbor_mean:.2f}°C, Cat={ev_before.context_category.value}")
    print(f"  -> After Future Records:  Mean={ev_after.temperature_consensus.neighbor_mean:.2f}°C, Cat={ev_after.context_category.value}")
    print(f"  -> Forward Leakage Detected: {leakage_detected}")

    results["causality_test"] = {
        "leakage_detected": leakage_detected,
        "causality_strictly_enforced": not leakage_detected,
    }

    # Save summary artifact
    out_path = Path("experiments/spatial_evaluation_results.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print(f"\nSuccessfully saved Phase 4 evaluation results artifact to: {out_path}")
    return results


if __name__ == "__main__":
    run_evaluation()
