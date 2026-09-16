"""SkyGuard Hybrid Decision Engine.

Synthesizes Data Quality, ML Anomaly scores, Temporal sliding residuals,
Multivariate physical constraints, and Spatial/Synoptic Context into transparent,
traceable operational decisions without score flattening.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union
import yaml

from ml.decision.schema import (
    DataQualityEvidence,
    DecisionExplanation,
    DecisionReasonCode,
    DecisionSeverity,
    EvidenceState,
    HybridDecision,
    HybridDecisionType,
    MLAnomalyEvidence,
    MultivariateEvidence,
    ObservationEvidence,
    RecommendedCorrection,
    SpatialEvidence,
    TemporalEvidence,
)
from ml.spatial.schema import SpatialContextCategory, SpatialContextEvidence


class HybridDecisionEngine:
    """Configurable hybrid arbiter combining physical meteorological rules, ML, and spatial context."""

    def __init__(self, config_path: Optional[Union[str, Path]] = None) -> None:
        """Initialize the Hybrid Decision Engine.
        
        Args:
            config_path: Path to `configs/hybrid_decision.yaml`. If None, uses defaults.
        """
        self.config = self._load_config(config_path)
        self._unpack_config_parameters()

    def _load_config(self, config_path: Optional[Union[str, Path]]) -> Dict[str, Any]:
        """Load configuration dictionary from YAML or provide safe defaults."""
        path = Path(config_path) if config_path else Path("configs/hybrid_decision.yaml")
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}

        # Default fallback config if file is missing
        return {
            "thresholds": {
                "ml_anomaly": {"score_low": 0.40, "score_medium": 0.65, "score_high": 0.80},
                "temporal": {
                    "temp_rate_max_c_per_min": 0.50,
                    "consecutive_unchanged_steps_threshold": 6,
                    "flatline_duration_minutes_threshold": 30.0,
                },
                "spatial": {
                    "local_deviation_zscore_threshold": 2.2,
                    "local_deviation_temp_c": 2.5,
                },
                "physical_bounds": {
                    "temperature_min_c": -50.0,
                    "temperature_max_c": 60.0,
                    "relative_humidity_min_pct": 0.0,
                    "relative_humidity_max_pct": 100.0,
                    "sea_level_pressure_min_hpa": 870.0,
                    "sea_level_pressure_max_hpa": 1085.0,
                },
            },
            "recommended_actions": {
                "NORMAL": "No action required. Telemetry is meteorologically consistent and temporally coherent.",
                "POSSIBLE_GENUINE_EVENT": "Corroborated by regional network. Compare adjacent station observations and monitor atmospheric event progression.",
                "PROBABLE_SENSOR_ANOMALY": "Inspect sensor hardware and wiring. Validate against portable reference instrument or redundant sensor.",
                "PROBABLE_DATA_QUALITY_ISSUE": "Check communication telemetry link, data logger encoding, and ingestion pipeline queue.",
                "UNCERTAIN": "Collect additional observation cycles and review manual field logs before executing corrective maintenance.",
            },
        }

    def _unpack_config_parameters(self) -> None:
        """Unpack thresholds and actions from configuration dictionary."""
        thresh = self.config.get("thresholds", {})
        ml_th = thresh.get("ml_anomaly", {})
        self.ml_score_low = float(ml_th.get("score_low", 0.40))
        self.ml_score_medium = float(ml_th.get("score_medium", 0.65))
        self.ml_score_high = float(ml_th.get("score_high", 0.80))

        temp_th = thresh.get("temporal", {})
        self.temp_rate_max = float(temp_th.get("temp_rate_max_c_per_min", 0.50))
        self.flatline_steps_th = int(temp_th.get("consecutive_unchanged_steps_threshold", 6))
        self.flatline_duration_th = float(temp_th.get("flatline_duration_minutes_threshold", 30.0))

        spat_th = thresh.get("spatial", {})
        self.spat_zscore_th = float(spat_th.get("local_deviation_zscore_threshold", 2.2))
        self.spat_temp_dev_th = float(spat_th.get("local_deviation_temp_c", 2.5))

        phys_th = thresh.get("physical_bounds", {})
        self.temp_min = float(phys_th.get("temperature_min_c", -50.0))
        self.temp_max = float(phys_th.get("temperature_max_c", 60.0))
        self.rh_min = float(phys_th.get("relative_humidity_min_pct", 0.0))
        self.rh_max = float(phys_th.get("relative_humidity_max_pct", 100.0))
        self.slp_min = float(phys_th.get("sea_level_pressure_min_hpa", 870.0))
        self.slp_max = float(phys_th.get("sea_level_pressure_max_hpa", 1085.0))

        self.actions = self.config.get("recommended_actions", {})

    def evaluate(self, evidence: ObservationEvidence) -> HybridDecision:
        """Evaluate multi-subsystem evidence through the explicit rule hierarchy.
        
        Args:
            evidence: Comprehensive `ObservationEvidence` container.
            
        Returns:
            Traceable `HybridDecision` object.
        """
        reasons: List[DecisionReasonCode] = []
        metrics: Dict[str, Any] = {
            "ml_anomaly_score": evidence.ml_anomaly.normalized_anomaly_score,
            "quality_status": evidence.data_quality.quality_status,
            "spatial_context_category": evidence.spatial.context_category.value,
            "consecutive_unchanged_steps": evidence.temporal.consecutive_unchanged_count,
        }
        supporting_ev: List[str] = []
        contradicting_ev: List[str] = []
        unavailable_ev: List[str] = []

        # Populate evidence availability notes
        if evidence.spatial.context_category == SpatialContextCategory.INSUFFICIENT_CONTEXT:
            unavailable_ev.append("Spatial neighborhood telemetry is unavailable or sparse.")
        if evidence.ml_anomaly.raw_model_score is None:
            unavailable_ev.append("Raw ML model decision score is unavailable.")

        # =========================================================
        # Gate 1: Definitive Data Quality Defect
        # =========================================================
        dq = evidence.data_quality
        is_dq_issue = (
            dq.quality_status in ("REJECTED", "GAP", "DUPLICATE", "CORRUPTED")
            or dq.is_duplicate
            or dq.is_out_of_order
            or len(dq.missing_fields) > 0
            or (dq.communication_gap_minutes is not None and dq.communication_gap_minutes > 15.0)
        )

        if is_dq_issue:
            if dq.is_duplicate:
                reasons.append(DecisionReasonCode.DUPLICATE_TIMESTAMP)
            if dq.is_out_of_order:
                reasons.append(DecisionReasonCode.OUT_OF_ORDER_TIMESTAMP)
            if dq.missing_fields:
                reasons.append(DecisionReasonCode.MISSING_REQUIRED_VARIABLES)
            if dq.communication_gap_minutes and dq.communication_gap_minutes > 15.0:
                reasons.append(DecisionReasonCode.DATA_GAP)

            supporting_ev.append("Data quality subsystem identified packet/schema telemetry failure.")
            contradicting_ev.append("Atmospheric and ML behavioral models bypassed due to data transport defects.")

            # Determine severity
            if dq.communication_gap_minutes and dq.communication_gap_minutes >= 180.0:
                severity = DecisionSeverity.CRITICAL
            elif "temperature_c" in dq.missing_fields or len(dq.missing_fields) >= 2:
                severity = DecisionSeverity.HIGH
            elif dq.is_duplicate or dq.is_out_of_order:
                severity = DecisionSeverity.LOW
            else:
                severity = DecisionSeverity.MEDIUM

            explanation = DecisionExplanation(
                summary="Telemetry ingestion failure detected. Packet contains transport, formatting, or communication gaps.",
                reason_codes=reasons,
                supporting_evidence=supporting_ev,
                contradicting_evidence=contradicting_ev,
                unavailable_evidence=unavailable_ev,
            )

            return HybridDecision(
                station_id=evidence.station_id,
                timestamp=evidence.timestamp,
                decision=HybridDecisionType.PROBABLE_DATA_QUALITY_ISSUE,
                severity=severity,
                reason_codes=reasons,
                supporting_metrics=metrics,
                recommended_action=self.actions.get(
                    "PROBABLE_DATA_QUALITY_ISSUE",
                    "Check communication telemetry link and data pipeline."
                ),
                explanation=explanation,
                evidence=evidence,
            )

        # =========================================================
        # Gate 2: Physical Planetary Boundary Violation
        # =========================================================
        if dq.is_physical_out_of_bounds:
            reasons.append(DecisionReasonCode.OUT_OF_RANGE_PHYSICAL)
            supporting_ev.append("Observation exceeds physical atmospheric bounds on Earth.")
            explanation = DecisionExplanation(
                summary="Observed sensor reading exceeds physical thermodynamic limits for surface atmosphere.",
                reason_codes=reasons,
                supporting_evidence=supporting_ev,
                contradicting_evidence=contradicting_ev,
                unavailable_evidence=unavailable_ev,
            )
            return HybridDecision(
                station_id=evidence.station_id,
                timestamp=evidence.timestamp,
                decision=HybridDecisionType.PROBABLE_SENSOR_ANOMALY,
                severity=DecisionSeverity.CRITICAL,
                reason_codes=reasons,
                supporting_metrics=metrics,
                recommended_action=self.actions.get(
                    "PROBABLE_SENSOR_ANOMALY",
                    "Inspect sensor hardware and wiring."
                ),
                explanation=explanation,
                evidence=evidence,
            )

        # =========================================================
        # Gate 3: Persistent Flatline / Stuck Sensor
        # =========================================================
        temp_ev = evidence.temporal
        if temp_ev.is_flatline or temp_ev.consecutive_unchanged_count >= self.flatline_steps_th:
            reasons.append(DecisionReasonCode.PERSISTENT_VALUE)
            supporting_ev.append(
                f"Sensor output has remained unchanged for {temp_ev.consecutive_unchanged_count} consecutive steps ({temp_ev.flatline_duration_minutes:.1f} min)."
            )
            severity = (
                DecisionSeverity.HIGH
                if temp_ev.consecutive_unchanged_count >= 12
                else DecisionSeverity.MEDIUM
            )
            explanation = DecisionExplanation(
                summary="Sensor persistence check failed. Reading exhibits zero variance during dynamic atmospheric conditions.",
                reason_codes=reasons,
                supporting_evidence=supporting_ev,
                contradicting_evidence=contradicting_ev,
                unavailable_evidence=unavailable_ev,
            )
            return HybridDecision(
                station_id=evidence.station_id,
                timestamp=evidence.timestamp,
                decision=HybridDecisionType.PROBABLE_SENSOR_ANOMALY,
                severity=severity,
                reason_codes=reasons,
                supporting_metrics=metrics,
                recommended_action=self.actions.get(
                    "PROBABLE_SENSOR_ANOMALY",
                    "Inspect sensor hardware for mechanical/transducer freezing."
                ),
                explanation=explanation,
                evidence=evidence,
            )

        # =========================================================
        # Gate 4: Multivariate Physical Contradiction
        # =========================================================
        mv = evidence.multivariate
        if mv.is_multivariate_abnormal or mv.temp_rh_inconsistent:
            reasons.append(DecisionReasonCode.MULTIVARIATE_DEVIATION)
            supporting_ev.append("Multivariate thermodynamic consistency check failed (August-Roche-Magnus T-RH violation).")
            explanation = DecisionExplanation(
                summary="Sensor trio exhibits internal physical contradictions (e.g. saturation during peak heat).",
                reason_codes=reasons,
                supporting_evidence=supporting_ev,
                contradicting_evidence=contradicting_ev,
                unavailable_evidence=unavailable_ev,
            )
            return HybridDecision(
                station_id=evidence.station_id,
                timestamp=evidence.timestamp,
                decision=HybridDecisionType.PROBABLE_SENSOR_ANOMALY,
                severity=DecisionSeverity.MEDIUM,
                reason_codes=reasons,
                supporting_metrics=metrics,
                recommended_action=self.actions.get(
                    "PROBABLE_SENSOR_ANOMALY",
                    "Validate joint temperature and humidity sensor calibration."
                ),
                explanation=explanation,
                evidence=evidence,
            )

        # =========================================================
        # Gate 5: Spatial-ML Synergy & Cross-Arbitration
        # =========================================================
        ml = evidence.ml_anomaly
        spat = evidence.spatial
        is_ml_anom = ml.ml_is_anomaly or ml.normalized_anomaly_score >= self.ml_score_medium
        is_ml_moderate = ml.normalized_anomaly_score >= self.ml_score_low
        has_anomaly_signal = is_ml_anom or is_ml_moderate or temp_ev.is_rate_abnormal

        if has_anomaly_signal:
            if is_ml_anom:
                reasons.append(
                    DecisionReasonCode.ML_HIGH_ANOMALY_SCORE
                    if ml.normalized_anomaly_score >= self.ml_score_high
                    else DecisionReasonCode.ML_MODERATE_ANOMALY_SCORE
                )

            # Subcase 5A: Spatial Context confirms REGIONAL_PATTERN
            if spat.context_category == SpatialContextCategory.REGIONAL_PATTERN:
                # Check for mixed scenario: regional event exists, but target has severe excess departure
                target_delta = spat.temp_target_minus_mean or 0.0
                target_zscore = abs(spat.temp_target_zscore or 0.0)

                if target_zscore >= 3.0 or abs(target_delta) >= self.spat_temp_dev_th * 2.5:
                    reasons.append(DecisionReasonCode.MIXED_REGIONAL_EVENT_WITH_LOCAL_EXCESS)
                    reasons.append(DecisionReasonCode.REGIONAL_SPATIAL_AGREEMENT)
                    supporting_ev.append(
                        f"Regional weather event corroborated, but target station exhibits unphysical excess deviation (+{target_delta:.2f}°C)."
                    )
                    explanation = DecisionExplanation(
                        summary="Mixed meteorological event: A genuine regional weather transition is underway, but this station's reading deviates excessively beyond regional consensus.",
                        reason_codes=reasons,
                        supporting_evidence=supporting_ev,
                        contradicting_evidence=contradicting_ev,
                        unavailable_evidence=unavailable_ev,
                    )
                    return HybridDecision(
                        station_id=evidence.station_id,
                        timestamp=evidence.timestamp,
                        decision=HybridDecisionType.PROBABLE_SENSOR_ANOMALY,
                        severity=DecisionSeverity.HIGH,
                        reason_codes=reasons,
                        supporting_metrics=metrics,
                        recommended_action="Validate target sensor calibration. Regional event confirmed but local magnitude is excessive.",
                        explanation=explanation,
                        evidence=evidence,
                    )

                # Genuine regional event corroborated by neighbors
                reasons.append(DecisionReasonCode.REGIONAL_SPATIAL_AGREEMENT)
                if temp_ev.is_rate_abnormal:
                    reasons.append(DecisionReasonCode.RAPID_RATE_OF_CHANGE)

                supporting_ev.append(
                    f"Regional AWS network consensus ({spat.valid_neighbor_count} stations) corroborates atmospheric transition."
                )
                contradicting_ev.append("Isolated sensor fault hypothesis contradicted by multi-station consensus.")

                explanation = DecisionExplanation(
                    summary="Observation exhibits steep atmospheric dynamics corroborated by neighboring AWS stations (synoptic front/squall).",
                    reason_codes=reasons,
                    supporting_evidence=supporting_ev,
                    contradicting_evidence=contradicting_ev,
                    unavailable_evidence=unavailable_ev,
                )
                return HybridDecision(
                    station_id=evidence.station_id,
                    timestamp=evidence.timestamp,
                    decision=HybridDecisionType.POSSIBLE_GENUINE_EVENT,
                    severity=DecisionSeverity.LOW if is_ml_anom else DecisionSeverity.INFO,
                    reason_codes=reasons,
                    supporting_metrics=metrics,
                    recommended_action=self.actions.get(
                        "POSSIBLE_GENUINE_EVENT",
                        "Compare regional observations and monitor event."
                    ),
                    explanation=explanation,
                    evidence=evidence,
                )

            # Subcase 5B: Spatial Context confirms LOCAL_ONLY (isolated deviation)
            if spat.context_category == SpatialContextCategory.LOCAL_ONLY:
                reasons.append(DecisionReasonCode.LOCAL_SPATIAL_ISOLATION)
                supporting_ev.append(
                    f"Observation is locally isolated: {spat.valid_neighbor_count} adjacent stations do not corroborate reading."
                )
                if is_ml_anom:
                    supporting_ev.append(f"ML anomaly detector score ({ml.normalized_anomaly_score:.2f}) indicates severe deviation.")

                severity = (
                    DecisionSeverity.HIGH
                    if ml.normalized_anomaly_score >= self.ml_score_high
                    else DecisionSeverity.MEDIUM
                )
                explanation = DecisionExplanation(
                    summary="Sensor anomaly indicated. Single-station departure is contradicted by stable surrounding AWS network.",
                    reason_codes=reasons,
                    supporting_evidence=supporting_ev,
                    contradicting_evidence=contradicting_ev,
                    unavailable_evidence=unavailable_ev,
                )
                return HybridDecision(
                    station_id=evidence.station_id,
                    timestamp=evidence.timestamp,
                    decision=HybridDecisionType.PROBABLE_SENSOR_ANOMALY,
                    severity=severity,
                    reason_codes=reasons,
                    supporting_metrics=metrics,
                    recommended_action=self.actions.get(
                        "PROBABLE_SENSOR_ANOMALY",
                        "Inspect affected sensor and compare with reference instrument."
                    ),
                    explanation=explanation,
                    evidence=evidence,
                )

            # Subcase 5C: Spatial Context is LOCAL_CLUSTER
            if spat.context_category == SpatialContextCategory.LOCAL_CLUSTER:
                reasons.append(DecisionReasonCode.LOCAL_CLUSTER_AGREEMENT)
                supporting_ev.append("Immediate nearest neighbor corroborates reading, while wider region differs.")
                explanation = DecisionExplanation(
                    summary="Localized meso-scale weather variation detected across immediate neighboring cluster.",
                    reason_codes=reasons,
                    supporting_evidence=supporting_ev,
                    contradicting_evidence=contradicting_ev,
                    unavailable_evidence=unavailable_ev,
                )
                return HybridDecision(
                    station_id=evidence.station_id,
                    timestamp=evidence.timestamp,
                    decision=HybridDecisionType.POSSIBLE_GENUINE_EVENT,
                    severity=DecisionSeverity.LOW,
                    reason_codes=reasons,
                    supporting_metrics=metrics,
                    recommended_action=self.actions.get("POSSIBLE_GENUINE_EVENT", "Monitor local cluster."),
                    explanation=explanation,
                    evidence=evidence,
                )

            # Subcase 5D: Spatial Context is INSUFFICIENT_CONTEXT (Isolated Station)
            if spat.context_category == SpatialContextCategory.INSUFFICIENT_CONTEXT:
                reasons.append(DecisionReasonCode.INSUFFICIENT_SPATIAL_CONTEXT)
                reasons.append(DecisionReasonCode.CONFLICTING_EVIDENCE)
                supporting_ev.append(f"ML detector flags anomaly (score: {ml.normalized_anomaly_score:.2f}).")
                contradicting_ev.append("Spatial corroboration unavailable to confirm whether anomaly is local or regional.")
                explanation = DecisionExplanation(
                    summary="Uncertain evaluation: Statistical ML model indicates anomaly, but spatial network coverage is insufficient for validation.",
                    reason_codes=reasons,
                    supporting_evidence=supporting_ev,
                    contradicting_evidence=contradicting_ev,
                    unavailable_evidence=unavailable_ev,
                )
                return HybridDecision(
                    station_id=evidence.station_id,
                    timestamp=evidence.timestamp,
                    decision=HybridDecisionType.UNCERTAIN,
                    severity=DecisionSeverity.MEDIUM,
                    reason_codes=reasons,
                    supporting_metrics=metrics,
                    recommended_action=self.actions.get(
                        "UNCERTAIN",
                        "Collect additional observations before corrective action."
                    ),
                    explanation=explanation,
                    evidence=evidence,
                )

        # =========================================================
        # Gate 6: Uncertainty Resolution
        # =========================================================
        if is_ml_moderate:
            reasons.append(DecisionReasonCode.CONFLICTING_EVIDENCE)
            supporting_ev.append("Moderate statistical residual observed.")
            explanation = DecisionExplanation(
                summary="Evidence is inconclusive. Observation exhibits borderline metrics requiring additional telemetry.",
                reason_codes=reasons,
                supporting_evidence=supporting_ev,
                contradicting_evidence=contradicting_ev,
                unavailable_evidence=unavailable_ev,
            )
            return HybridDecision(
                station_id=evidence.station_id,
                timestamp=evidence.timestamp,
                decision=HybridDecisionType.UNCERTAIN,
                severity=DecisionSeverity.LOW,
                reason_codes=reasons,
                supporting_metrics=metrics,
                recommended_action=self.actions.get("UNCERTAIN", "Review manual field logs."),
                explanation=explanation,
                evidence=evidence,
            )

        # =========================================================
        # Gate 7: Nominal Meteorological Operation (Fallback)
        # =========================================================
        reasons.append(DecisionReasonCode.NOMINAL_OBSERVATION)
        supporting_ev.append("All physical range checks, temporal rates, and spatial consensus metrics within nominal tolerances.")
        explanation = DecisionExplanation(
            summary="Observation is meteorologically consistent, temporally coherent, and corroborated by network context.",
            reason_codes=reasons,
            supporting_evidence=supporting_ev,
            contradicting_evidence=contradicting_ev,
            unavailable_evidence=unavailable_ev,
        )

        return HybridDecision(
            station_id=evidence.station_id,
            timestamp=evidence.timestamp,
            decision=HybridDecisionType.NORMAL,
            severity=DecisionSeverity.INFO,
            reason_codes=reasons,
            supporting_metrics=metrics,
            recommended_action=self.actions.get("NORMAL", "No action required."),
            explanation=explanation,
            evidence=evidence,
        )
