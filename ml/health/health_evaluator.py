"""Synthetic health scenario evaluator and validation suite for Phase 6B."""

from __future__ import annotations

from typing import Any, Dict, List, Tuple
import pandas as pd

from ml.decision.schema import (
    DataQualityEvidence,
    DecisionExplanation,
    DecisionReasonCode,
    DecisionSeverity,
    HybridDecision,
    HybridDecisionType,
    MLAnomalyEvidence,
    MultivariateEvidence,
    ObservationEvidence,
    SpatialEvidence,
    TemporalEvidence,
)
from ml.health.health_engine import SensorHealthEngine
from ml.health.health_schema import (
    HealthReasonCode,
    HealthStatusBand,
    HealthTrend,
    MaintenanceRecommendation,
    SensorHealthSummary,
)
from ml.spatial.schema import SpatialContextCategory


class HealthScenarioEvaluator:
    """Runs and validates the 8 canonical synthetic degradation and health scenarios."""

    def __init__(self, engine: Optional[SensorHealthEngine] = None) -> None:
        self.engine = engine or SensorHealthEngine()

    def generate_scenario_decisions(self, scenario_type: str, n_steps: int = 24) -> List[HybridDecision]:
        """Generate synthetic sequence of HybridDecisions representing controlled operational profiles."""
        decisions: List[HybridDecision] = []
        base_time = pd.Timestamp("2026-09-17 00:00:00")

        for i in range(n_steps):
            t_str = (base_time + pd.Timedelta(minutes=i * 5)).isoformat() + "Z"

            if scenario_type == "HEALTHY":
                ev = ObservationEvidence(
                    station_id="AWS_001",
                    timestamp=t_str,
                    data_quality=DataQualityEvidence(quality_status="VALID"),
                    ml_anomaly=MLAnomalyEvidence(normalized_anomaly_score=0.10),
                    temporal=TemporalEvidence(temp_rate_per_min=0.05),
                    spatial=SpatialEvidence(context_category=SpatialContextCategory.REGIONAL_PATTERN, valid_neighbor_count=4),
                )
                dec = HybridDecision(
                    station_id="AWS_001",
                    timestamp=t_str,
                    decision=HybridDecisionType.NORMAL,
                    severity=DecisionSeverity.INFO,
                    reason_codes=[DecisionReasonCode.NOMINAL_OBSERVATION],
                    recommended_action="No action.",
                    explanation=DecisionExplanation(summary="Normal observation."),
                    evidence=ev,
                )

            elif scenario_type == "REPEATED_SPIKES":
                # Every 4th step is a severe single-station spike
                is_spike = (i % 4 == 0)
                ev = ObservationEvidence(
                    station_id="AWS_001",
                    timestamp=t_str,
                    ml_anomaly=MLAnomalyEvidence(normalized_anomaly_score=0.92 if is_spike else 0.15, ml_is_anomaly=is_spike),
                    temporal=TemporalEvidence(temp_rate_per_min=1.8 if is_spike else 0.05, is_rate_abnormal=is_spike),
                    spatial=SpatialEvidence(context_category=SpatialContextCategory.LOCAL_ONLY if is_spike else SpatialContextCategory.REGIONAL_PATTERN, valid_neighbor_count=4),
                )
                dec = HybridDecision(
                    station_id="AWS_001",
                    timestamp=t_str,
                    decision=HybridDecisionType.PROBABLE_SENSOR_ANOMALY if is_spike else HybridDecisionType.NORMAL,
                    severity=DecisionSeverity.HIGH if is_spike else DecisionSeverity.INFO,
                    reason_codes=[DecisionReasonCode.LOCAL_SPATIAL_ISOLATION, DecisionReasonCode.RAPID_RATE_OF_CHANGE] if is_spike else [DecisionReasonCode.NOMINAL_OBSERVATION],
                    recommended_action="Inspect.",
                    explanation=DecisionExplanation(summary="Spike anomaly."),
                    evidence=ev,
                )

            elif scenario_type == "GRADUAL_DRIFT":
                # Progressive divergence
                drift_val = 0.2 * i
                is_drift = drift_val >= 2.0
                ev = ObservationEvidence(
                    station_id="AWS_001",
                    timestamp=t_str,
                    ml_anomaly=MLAnomalyEvidence(normalized_anomaly_score=min(0.85, 0.2 + 0.03 * i)),
                    temporal=TemporalEvidence(temp_rate_per_min=0.02),
                    spatial=SpatialEvidence(context_category=SpatialContextCategory.LOCAL_ONLY if is_drift else SpatialContextCategory.REGIONAL_PATTERN, temp_target_minus_mean=drift_val, valid_neighbor_count=4),
                )
                dec = HybridDecision(
                    station_id="AWS_001",
                    timestamp=t_str,
                    decision=HybridDecisionType.PROBABLE_SENSOR_ANOMALY if is_drift else HybridDecisionType.NORMAL,
                    severity=DecisionSeverity.MEDIUM if is_drift else DecisionSeverity.INFO,
                    reason_codes=[DecisionReasonCode.LOCAL_SPATIAL_ISOLATION] if is_drift else [DecisionReasonCode.NOMINAL_OBSERVATION],
                    recommended_action="Calibrate.",
                    explanation=DecisionExplanation(summary="Drift observed."),
                    evidence=ev,
                )

            elif scenario_type == "FROZEN_SENSOR":
                # Flatline sensor
                ev = ObservationEvidence(
                    station_id="AWS_001",
                    timestamp=t_str,
                    temporal=TemporalEvidence(consecutive_unchanged_count=i + 1, flatline_duration_minutes=(i + 1) * 5.0, is_flatline=(i >= 6)),
                )
                dec = HybridDecision(
                    station_id="AWS_001",
                    timestamp=t_str,
                    decision=HybridDecisionType.PROBABLE_SENSOR_ANOMALY if i >= 6 else HybridDecisionType.NORMAL,
                    severity=DecisionSeverity.HIGH if i >= 12 else (DecisionSeverity.MEDIUM if i >= 6 else DecisionSeverity.INFO),
                    reason_codes=[DecisionReasonCode.PERSISTENT_VALUE] if i >= 6 else [DecisionReasonCode.NOMINAL_OBSERVATION],
                    recommended_action="Inspect transducer.",
                    explanation=DecisionExplanation(summary="Flatline sensor."),
                    evidence=ev,
                )

            elif scenario_type == "COMMUNICATION_DEGRADATION":
                # Multiple telemetry gaps
                is_gap = (i % 5 == 0)
                ev = ObservationEvidence(
                    station_id="AWS_001",
                    timestamp=t_str,
                    data_quality=DataQualityEvidence(
                        quality_status="GAP" if is_gap else "VALID",
                        communication_gap_minutes=45.0 if is_gap else 5.0,
                        missing_fields=["temperature_c"] if is_gap else [],
                    ),
                )
                dec = HybridDecision(
                    station_id="AWS_001",
                    timestamp=t_str,
                    decision=HybridDecisionType.PROBABLE_DATA_QUALITY_ISSUE if is_gap else HybridDecisionType.NORMAL,
                    severity=DecisionSeverity.HIGH if is_gap else DecisionSeverity.INFO,
                    reason_codes=[DecisionReasonCode.DATA_GAP] if is_gap else [DecisionReasonCode.NOMINAL_OBSERVATION],
                    recommended_action="Check telemetry link.",
                    explanation=DecisionExplanation(summary="Telemetry gap."),
                    evidence=ev,
                )

            elif scenario_type == "REGIONAL_EVENT":
                # REGIONAL WEATHER SQUALL: all observations marked POSSIBLE_GENUINE_EVENT
                ev = ObservationEvidence(
                    station_id="AWS_001",
                    timestamp=t_str,
                    ml_anomaly=MLAnomalyEvidence(normalized_anomaly_score=0.75),
                    temporal=TemporalEvidence(temp_rate_per_min=1.2, is_rate_abnormal=True),
                    spatial=SpatialEvidence(context_category=SpatialContextCategory.REGIONAL_PATTERN, valid_neighbor_count=5),
                )
                dec = HybridDecision(
                    station_id="AWS_001",
                    timestamp=t_str,
                    decision=HybridDecisionType.POSSIBLE_GENUINE_EVENT,
                    severity=DecisionSeverity.LOW,
                    reason_codes=[DecisionReasonCode.REGIONAL_SPATIAL_AGREEMENT, DecisionReasonCode.RAPID_RATE_OF_CHANGE],
                    recommended_action="Monitor regional front.",
                    explanation=DecisionExplanation(summary="Regional squall."),
                    evidence=ev,
                )

            else:
                # Default normal
                ev = ObservationEvidence(station_id="AWS_001", timestamp=t_str)
                dec = HybridDecision(
                    station_id="AWS_001", timestamp=t_str, decision=HybridDecisionType.NORMAL,
                    severity=DecisionSeverity.INFO, reason_codes=[DecisionReasonCode.NOMINAL_OBSERVATION],
                    recommended_action="None", explanation=DecisionExplanation(summary="Normal"), evidence=ev,
                )

            decisions.append(dec)

        return decisions

    def evaluate_all_scenarios(self) -> Dict[str, Any]:
        """Execute and validate all 8 synthetic benchmark scenarios."""
        results: Dict[str, Any] = {}

        # 1. Healthy Station
        h_decs = self.generate_scenario_decisions("HEALTHY", 24)
        h_summary = self.engine.evaluate_station_health("AWS_001", decisions=h_decs)
        results["Scenario_A_Healthy"] = {
            "score": h_summary.overall_health_score,
            "band": h_summary.status_band.value,
            "recommendation": h_summary.maintenance_recommendation.value,
            "passed": h_summary.overall_health_score is not None and h_summary.overall_health_score >= 90.0,
        }

        # 2. Repeated Spikes
        sp_decs = self.generate_scenario_decisions("REPEATED_SPIKES", 24)
        sp_summary = self.engine.evaluate_station_health("AWS_001", decisions=sp_decs)
        results["Scenario_B_Spikes"] = {
            "score": sp_summary.overall_health_score,
            "band": sp_summary.status_band.value,
            "recommendation": sp_summary.maintenance_recommendation.value,
            "passed": sp_summary.overall_health_score is not None and sp_summary.overall_health_score < 75.0,
        }

        # 3. Gradual Drift
        dr_decs = self.generate_scenario_decisions("GRADUAL_DRIFT", 24)
        dr_summary = self.engine.evaluate_station_health("AWS_001", decisions=dr_decs)
        results["Scenario_C_Drift"] = {
            "score": dr_summary.overall_health_score,
            "band": dr_summary.status_band.value,
            "has_drift_reason": HealthReasonCode.INCREASING_DRIFT in dr_summary.reason_codes,
            "passed": dr_summary.overall_health_score is not None and dr_summary.overall_health_score < 85.0,
        }

        # 4. Frozen Sensor
        fr_decs = self.generate_scenario_decisions("FROZEN_SENSOR", 24)
        fr_summary = self.engine.evaluate_station_health("AWS_001", decisions=fr_decs)
        results["Scenario_D_Frozen"] = {
            "score": fr_summary.overall_health_score,
            "band": fr_summary.status_band.value,
            "has_flatline_reason": HealthReasonCode.PERSISTENT_FLATLINE in fr_summary.reason_codes,
            "passed": fr_summary.overall_health_score is not None and fr_summary.overall_health_score < 60.0,
        }

        # 5. Communication Degradation
        com_decs = self.generate_scenario_decisions("COMMUNICATION_DEGRADATION", 24)
        com_summary = self.engine.evaluate_station_health("AWS_001", decisions=com_decs)
        results["Scenario_E_Comms"] = {
            "score": com_summary.overall_health_score,
            "band": com_summary.status_band.value,
            "comm_health": com_summary.component_scores.communication_health,
            "passed": com_summary.component_scores.communication_health < 60.0,
        }

        # 6. Regional Event Protection (CRITICAL SCENARIO H)
        reg_decs = self.generate_scenario_decisions("REGIONAL_EVENT", 24)
        reg_summary = self.engine.evaluate_station_health("AWS_001", decisions=reg_decs)
        results["Scenario_H_Regional_Protection"] = {
            "score": reg_summary.overall_health_score,
            "band": reg_summary.status_band.value,
            "recommendation": reg_summary.maintenance_recommendation.value,
            # Protected: score must remain HEALTHY >= 90.0
            "passed": reg_summary.overall_health_score is not None and reg_summary.overall_health_score >= 90.0,
        }

        # 7. Recovery Trend (Scenario G)
        rec_summary = self.engine.evaluate_station_health(
            "AWS_001",
            decisions=h_decs,  # Current is healthy
            previous_decisions=sp_decs,  # Previous had repeated spikes
        )
        results["Scenario_G_Recovery"] = {
            "current_score": rec_summary.overall_health_score,
            "trend": rec_summary.trend.value,
            "health_delta": rec_summary.health_delta,
            "passed": rec_summary.trend == HealthTrend.IMPROVING and rec_summary.health_delta is not None and rec_summary.health_delta > 0,
        }

        # 8. Low History Mode
        low_decs = self.generate_scenario_decisions("HEALTHY", 5)  # 5 < 12 required
        low_summary = self.engine.evaluate_station_health("AWS_001", decisions=low_decs)
        results["Scenario_Low_History"] = {
            "status_band": low_summary.status_band.value,
            "score": low_summary.overall_health_score,
            "passed": low_summary.status_band == HealthStatusBand.INSUFFICIENT_HISTORY and low_summary.overall_health_score is None,
        }

        all_passed = all(r.get("passed", False) for r in results.values())
        return {
            "all_scenarios_passed": all_passed,
            "scenario_details": results,
        }
