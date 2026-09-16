"""Phase 5 Hybrid Decision Engine Evaluation Runner.

Executes comprehensive quantitative benchmarking across the 8 operational evaluation scenarios
(Scenarios A through H), confusion distributions, and uncertainty metrics.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List
import pandas as pd

from ml.decision.engine import HybridDecisionEngine
from ml.decision.schema import (
    DataQualityEvidence,
    DecisionReasonCode,
    DecisionSeverity,
    EvidenceState,
    HybridDecisionType,
    MLAnomalyEvidence,
    MultivariateEvidence,
    ObservationEvidence,
    SpatialEvidence,
    TemporalEvidence,
)
from ml.spatial.schema import SpatialContextCategory


def run_evaluation() -> Dict[str, Any]:
    """Execute complete Phase 5 Hybrid Decision Engine evaluation across Scenarios A-H."""
    print("=" * 75)
    print("SkyGuard AI — Phase 5: Hybrid Decision Engine Evaluation")
    print("=" * 75)

    engine = HybridDecisionEngine()
    results: Dict[str, Any] = {}
    scenario_decisions: Dict[str, str] = {}
    scenario_severities: Dict[str, str] = {}
    scenario_reasons: Dict[str, List[str]] = {}

    # -------------------------------------------------------------
    # Scenario A: Normal Meteorological Observation
    # -------------------------------------------------------------
    ev_a = ObservationEvidence(
        station_id="42182099999",
        timestamp="2024-06-01T12:00:00Z",
        data_quality=DataQualityEvidence(quality_status="VALID"),
        ml_anomaly=MLAnomalyEvidence(raw_model_score=-0.12, normalized_anomaly_score=0.15, ml_is_anomaly=False),
        temporal=TemporalEvidence(temp_rate_per_min=0.05, consecutive_unchanged_count=1, flatline_duration_minutes=5.0),
        multivariate=MultivariateEvidence(dew_point_spread_c=8.5, temp_rh_inconsistent=False),
        spatial=SpatialEvidence(
            valid_neighbor_count=4,
            context_category=SpatialContextCategory.REGIONAL_PATTERN,
            temp_consensus_fraction=0.85,
            temp_target_minus_mean=0.2,
        ),
    )
    dec_a = engine.evaluate(ev_a)
    scenario_decisions["Scenario_A_Normal"] = dec_a.decision.value
    scenario_severities["Scenario_A_Normal"] = dec_a.severity.value
    scenario_reasons["Scenario_A_Normal"] = [r.value for r in dec_a.reason_codes]
    print(f"\n[Scenario A: Normal Weather] -> Decision: {dec_a.decision.value} ({dec_a.severity.value}) | Reasons: {scenario_reasons['Scenario_A_Normal']}")

    # -------------------------------------------------------------
    # Scenario B: Local Single-Station Sensor Spike
    # -------------------------------------------------------------
    ev_b = ObservationEvidence(
        station_id="42182099999",
        timestamp="2024-06-01T12:00:00Z",
        data_quality=DataQualityEvidence(quality_status="VALID"),
        ml_anomaly=MLAnomalyEvidence(raw_model_score=0.85, normalized_anomaly_score=0.92, ml_is_anomaly=True),
        temporal=TemporalEvidence(temp_rate_per_min=1.40, is_rate_abnormal=True),
        multivariate=MultivariateEvidence(dew_point_spread_c=18.0),
        spatial=SpatialEvidence(
            valid_neighbor_count=4,
            context_category=SpatialContextCategory.LOCAL_ONLY,
            temp_consensus_fraction=0.0,
            temp_target_minus_mean=7.5,
            temp_target_zscore=5.8,
            is_spatially_isolated=True,
        ),
    )
    dec_b = engine.evaluate(ev_b)
    scenario_decisions["Scenario_B_Local_Spike"] = dec_b.decision.value
    scenario_severities["Scenario_B_Local_Spike"] = dec_b.severity.value
    scenario_reasons["Scenario_B_Local_Spike"] = [r.value for r in dec_b.reason_codes]
    print(f"[Scenario B: Local Sensor Spike] -> Decision: {dec_b.decision.value} ({dec_b.severity.value}) | Reasons: {scenario_reasons['Scenario_B_Local_Spike']}")

    # -------------------------------------------------------------
    # Scenario C: Coherent Regional Weather Event (Front / Squall)
    # -------------------------------------------------------------
    ev_c = ObservationEvidence(
        station_id="42182099999",
        timestamp="2024-06-01T12:00:00Z",
        data_quality=DataQualityEvidence(quality_status="VALID"),
        ml_anomaly=MLAnomalyEvidence(raw_model_score=0.72, normalized_anomaly_score=0.78, ml_is_anomaly=True),
        temporal=TemporalEvidence(temp_rate_per_min=-0.80, is_rate_abnormal=True),
        multivariate=MultivariateEvidence(dew_point_spread_c=1.2, temp_rh_inconsistent=False),
        spatial=SpatialEvidence(
            valid_neighbor_count=4,
            context_category=SpatialContextCategory.REGIONAL_PATTERN,
            temp_consensus_fraction=0.90,
            temp_target_minus_mean=-0.3,
            temp_target_zscore=0.4,
            is_regionally_corroborated=True,
        ),
    )
    dec_c = engine.evaluate(ev_c)
    scenario_decisions["Scenario_C_Regional_Event"] = dec_c.decision.value
    scenario_severities["Scenario_C_Regional_Event"] = dec_c.severity.value
    scenario_reasons["Scenario_C_Regional_Event"] = [r.value for r in dec_c.reason_codes]
    print(f"[Scenario C: Regional Weather Front] -> Decision: {dec_c.decision.value} ({dec_c.severity.value}) | Reasons: {scenario_reasons['Scenario_C_Regional_Event']}")

    # -------------------------------------------------------------
    # Scenario D: Mixed Event (Regional Event + Local Sensor Fault)
    # -------------------------------------------------------------
    ev_d = ObservationEvidence(
        station_id="42182099999",
        timestamp="2024-06-01T12:00:00Z",
        data_quality=DataQualityEvidence(quality_status="VALID"),
        ml_anomaly=MLAnomalyEvidence(raw_model_score=0.88, normalized_anomaly_score=0.94, ml_is_anomaly=True),
        temporal=TemporalEvidence(temp_rate_per_min=1.80, is_rate_abnormal=True),
        multivariate=MultivariateEvidence(dew_point_spread_c=22.0),
        spatial=SpatialEvidence(
            valid_neighbor_count=4,
            context_category=SpatialContextCategory.REGIONAL_PATTERN,
            temp_consensus_fraction=0.0,
            temp_target_minus_mean=8.2,
            temp_target_zscore=4.5,
        ),
    )
    dec_d = engine.evaluate(ev_d)
    scenario_decisions["Scenario_D_Mixed_Event"] = dec_d.decision.value
    scenario_severities["Scenario_D_Mixed_Event"] = dec_d.severity.value
    scenario_reasons["Scenario_D_Mixed_Event"] = [r.value for r in dec_d.reason_codes]
    print(f"[Scenario D: Mixed Regional+Fault] -> Decision: {dec_d.decision.value} ({dec_d.severity.value}) | Reasons: {scenario_reasons['Scenario_D_Mixed_Event']}")

    # -------------------------------------------------------------
    # Scenario E: Telemetry / Missing Data Gap
    # -------------------------------------------------------------
    ev_e = ObservationEvidence(
        station_id="42182099999",
        timestamp="2024-06-01T12:00:00Z",
        data_quality=DataQualityEvidence(
            quality_status="GAP",
            missing_fields=["temperature_c", "relative_humidity_pct"],
            communication_gap_minutes=45.0,
        ),
        ml_anomaly=MLAnomalyEvidence(normalized_anomaly_score=0.0, ml_is_anomaly=False),
    )
    dec_e = engine.evaluate(ev_e)
    scenario_decisions["Scenario_E_Data_Gap"] = dec_e.decision.value
    scenario_severities["Scenario_E_Data_Gap"] = dec_e.severity.value
    scenario_reasons["Scenario_E_Data_Gap"] = [r.value for r in dec_e.reason_codes]
    print(f"[Scenario E: Telemetry Data Gap] -> Decision: {dec_e.decision.value} ({dec_e.severity.value}) | Reasons: {scenario_reasons['Scenario_E_Data_Gap']}")

    # -------------------------------------------------------------
    # Scenario F: Frozen Sensor Flatline
    # -------------------------------------------------------------
    ev_f = ObservationEvidence(
        station_id="42182099999",
        timestamp="2024-06-01T12:00:00Z",
        data_quality=DataQualityEvidence(quality_status="VALID"),
        ml_anomaly=MLAnomalyEvidence(raw_model_score=0.60, normalized_anomaly_score=0.68, ml_is_anomaly=True),
        temporal=TemporalEvidence(
            consecutive_unchanged_count=8,
            flatline_duration_minutes=40.0,
            is_flatline=True,
        ),
        spatial=SpatialEvidence(
            valid_neighbor_count=4,
            context_category=SpatialContextCategory.REGIONAL_PATTERN,
        ),
    )
    dec_f = engine.evaluate(ev_f)
    scenario_decisions["Scenario_F_Frozen_Sensor"] = dec_f.decision.value
    scenario_severities["Scenario_F_Frozen_Sensor"] = dec_f.severity.value
    scenario_reasons["Scenario_F_Frozen_Sensor"] = [r.value for r in dec_f.reason_codes]
    print(f"[Scenario F: Frozen Sensor] -> Decision: {dec_f.decision.value} ({dec_f.severity.value}) | Reasons: {scenario_reasons['Scenario_F_Frozen_Sensor']}")

    # -------------------------------------------------------------
    # Scenario G: Gradual Sensor Drift
    # -------------------------------------------------------------
    ev_g = ObservationEvidence(
        station_id="42182099999",
        timestamp="2024-06-01T12:00:00Z",
        data_quality=DataQualityEvidence(quality_status="VALID"),
        ml_anomaly=MLAnomalyEvidence(raw_model_score=0.66, normalized_anomaly_score=0.72, ml_is_anomaly=True),
        temporal=TemporalEvidence(temp_rate_per_min=0.08, baseline_deviation_zscore=2.8),
        spatial=SpatialEvidence(
            valid_neighbor_count=4,
            context_category=SpatialContextCategory.LOCAL_ONLY,
            temp_target_minus_mean=3.8,
            temp_target_zscore=2.6,
        ),
    )
    dec_g = engine.evaluate(ev_g)
    scenario_decisions["Scenario_G_Sensor_Drift"] = dec_g.decision.value
    scenario_severities["Scenario_G_Sensor_Drift"] = dec_g.severity.value
    scenario_reasons["Scenario_G_Sensor_Drift"] = [r.value for r in dec_g.reason_codes]
    print(f"[Scenario G: Slow Sensor Drift] -> Decision: {dec_g.decision.value} ({dec_g.severity.value}) | Reasons: {scenario_reasons['Scenario_G_Sensor_Drift']}")

    # -------------------------------------------------------------
    # Scenario H: Conflicting Evidence / Isolated Station
    # -------------------------------------------------------------
    ev_h = ObservationEvidence(
        station_id="42182099999",
        timestamp="2024-06-01T12:00:00Z",
        data_quality=DataQualityEvidence(quality_status="VALID"),
        ml_anomaly=MLAnomalyEvidence(raw_model_score=0.68, normalized_anomaly_score=0.74, ml_is_anomaly=True),
        temporal=TemporalEvidence(temp_rate_per_min=0.25, is_rate_abnormal=False),
        spatial=SpatialEvidence(
            valid_neighbor_count=0,
            context_category=SpatialContextCategory.INSUFFICIENT_CONTEXT,
        ),
    )
    dec_h = engine.evaluate(ev_h)
    scenario_decisions["Scenario_H_Conflicting_Evidence"] = dec_h.decision.value
    scenario_severities["Scenario_H_Conflicting_Evidence"] = dec_h.severity.value
    scenario_reasons["Scenario_H_Conflicting_Evidence"] = [r.value for r in dec_h.reason_codes]
    print(f"[Scenario H: Conflicting / Isolated Station] -> Decision: {dec_h.decision.value} ({dec_h.severity.value}) | Reasons: {scenario_reasons['Scenario_H_Conflicting_Evidence']}")

    # Summary results dictionary
    results["scenarios"] = {
        "decisions": scenario_decisions,
        "severities": scenario_severities,
        "reasons": scenario_reasons,
    }

    # Accuracy against expected ground truth behaviors
    expected = {
        "Scenario_A_Normal": "NORMAL",
        "Scenario_B_Local_Spike": "PROBABLE_SENSOR_ANOMALY",
        "Scenario_C_Regional_Event": "POSSIBLE_GENUINE_EVENT",
        "Scenario_D_Mixed_Event": "PROBABLE_SENSOR_ANOMALY",
        "Scenario_E_Data_Gap": "PROBABLE_DATA_QUALITY_ISSUE",
        "Scenario_F_Frozen_Sensor": "PROBABLE_SENSOR_ANOMALY",
        "Scenario_G_Sensor_Drift": "PROBABLE_SENSOR_ANOMALY",
        "Scenario_H_Conflicting_Evidence": "UNCERTAIN",
    }

    correct_cnt = sum(1 for s, exp in expected.items() if scenario_decisions.get(s) == exp)
    results["metrics"] = {
        "total_scenarios": len(expected),
        "correct_decisions": correct_cnt,
        "scenario_accuracy": correct_cnt / len(expected),
        "uncertainty_rate": sum(1 for d in scenario_decisions.values() if d == "UNCERTAIN") / len(expected),
    }

    # Save summary artifact
    out_path = Path("experiments/hybrid_evaluation_results.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print(f"\nSuccessfully evaluated all {len(expected)} scenarios with {correct_cnt}/{len(expected)} exact matches.")
    print(f"Saved Phase 5 evaluation results artifact to: {out_path}")
    return results


if __name__ == "__main__":
    run_evaluation()
