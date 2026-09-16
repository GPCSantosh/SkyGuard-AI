"""Scientific reason-code mapping, evidence structuring, and explanation synthesis for SkyGuard AI."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence
import numpy as np

from ml.decision.schema import (
    DataQualityEvidence,
    DecisionReasonCode,
    DecisionSeverity,
    EvidenceState,
    HybridDecision,
    HybridDecisionType,
    MultivariateEvidence,
    SpatialEvidence,
    TemporalEvidence,
)
from ml.explainability.schema import (
    EvidenceHierarchy,
    FeatureContribution,
    NeighborComparison,
)


class ExplanationSynthesizer:
    """Synthesizes deterministic, scientific human-readable explanations and builds evidence hierarchies."""

    def __init__(self) -> None:
        pass

    def build_evidence_hierarchy(
        self,
        decision: HybridDecision,
        contributions: List[FeatureContribution],
        neighbor_comparison: Optional[NeighborComparison] = None,
        direct_values: Optional[Dict[str, Any]] = None,
    ) -> EvidenceHierarchy:
        """Construct structured 4-tier EvidenceHierarchy separating direct, model, contextual, and operational data."""
        ev = decision.evidence

        # 1. Direct Evidence
        direct_ev: Dict[str, Any] = direct_values.copy() if direct_values else {}
        direct_ev["station_id"] = decision.station_id
        direct_ev["timestamp"] = decision.timestamp
        if neighbor_comparison:
            direct_ev["target_variable"] = neighbor_comparison.target_variable
            direct_ev["measured_target_value"] = neighbor_comparison.target_value
            direct_ev["neighbor_measured_values"] = neighbor_comparison.neighbor_values
            direct_ev["temporal_alignment_window_min"] = neighbor_comparison.temporal_alignment_window_minutes

        # 2. Model Evidence
        top_contrib_names = [f"{c.feature_name} ({c.direction.value}, val={c.feature_value:.2f}, impact={c.contribution:+.3f})" for c in contributions[:3]]
        model_ev: Dict[str, Any] = {
            "model_version": ev.ml_anomaly.model_version,
            "raw_model_score": ev.ml_anomaly.raw_model_score,
            "normalized_anomaly_score": ev.ml_anomaly.normalized_anomaly_score,
            "ml_anomaly_flag": ev.ml_anomaly.ml_is_anomaly,
            "top_feature_attributions": top_contrib_names,
            "attribution_note": "SHAP identifies the model features that contributed most to the anomaly score.",
        }

        # 3. Contextual Evidence
        contextual_ev: Dict[str, Any] = {
            "spatial_category": ev.spatial.context_category.value,
            "spatial_neighbors_active": ev.spatial.valid_neighbor_count,
            "spatial_isolated_flag": ev.spatial.is_spatially_isolated,
            "spatial_regional_corroboration": ev.spatial.is_regionally_corroborated,
            "temporal_consecutive_unchanged_count": ev.temporal.consecutive_unchanged_count,
            "temporal_flatline_duration_minutes": ev.temporal.flatline_duration_minutes,
            "temporal_rate_abnormal_flag": ev.temporal.is_rate_abnormal,
            "multivariate_temp_rh_inconsistent": ev.multivariate.temp_rh_inconsistent,
            "multivariate_abnormal_flag": ev.multivariate.is_multivariate_abnormal,
        }
        if ev.temporal.temp_rate_per_min is not None:
            contextual_ev["temp_rate_per_min"] = ev.temporal.temp_rate_per_min

        # 4. Operational Interpretation
        op_interp_map = {
            HybridDecisionType.NORMAL: "nominal observation",
            HybridDecisionType.POSSIBLE_GENUINE_EVENT: "possible regional event",
            HybridDecisionType.PROBABLE_SENSOR_ANOMALY: "probable sensor anomaly",
            HybridDecisionType.PROBABLE_DATA_QUALITY_ISSUE: "probable data quality issue",
            HybridDecisionType.UNCERTAIN: "uncertain",
        }
        operational_interpretation = op_interp_map.get(decision.decision, "uncertain")

        return EvidenceHierarchy(
            direct_evidence=direct_ev,
            model_evidence=model_ev,
            contextual_evidence=contextual_ev,
            operational_interpretation=operational_interpretation,
        )

    def synthesize_summary(
        self,
        decision: HybridDecision,
        contributions: List[FeatureContribution],
        neighbor_comp: Optional[NeighborComparison] = None,
    ) -> str:
        """Generate deterministic, concise, evidence-grounded human-readable summary."""
        ev = decision.evidence
        dtype = decision.decision
        reasons = decision.reason_codes

        # Top SHAP features mention
        top_shap_str = ""
        if contributions:
            top_feats = [c.feature_name for c in contributions[:2] if c.direction.value == "increases_anomaly"]
            if top_feats:
                top_shap_str = f" The strongest model contributors were {', '.join(top_feats)}."

        # Case 1: Data Quality Issues
        if dtype == HybridDecisionType.PROBABLE_DATA_QUALITY_ISSUE:
            dq = ev.data_quality
            parts: List[str] = ["Data quality defect detected."]
            if dq.is_duplicate:
                parts.append("Duplicate observation timestamp received.")
            if dq.is_out_of_order:
                parts.append("Packet arrived out of chronological sequence.")
            if dq.missing_fields:
                parts.append(f"Missing required meteorological fields: {', '.join(dq.missing_fields)}.")
            if dq.communication_gap_minutes and dq.communication_gap_minutes > 15.0:
                parts.append(f"Communication telemetry gap of {dq.communication_gap_minutes:.1f} minutes observed.")
            return " ".join(parts)

        # Case 2: Physical Boundary Violation
        if DecisionReasonCode.OUT_OF_RANGE_PHYSICAL in reasons or ev.data_quality.is_physical_out_of_bounds:
            return "Observation breaches physical planetary atmospheric limits. Measured values exceed terrestrial surface boundary constraints."

        # Case 3: Stuck / Frozen Sensor
        if DecisionReasonCode.PERSISTENT_VALUE in reasons or ev.temporal.is_flatline:
            cnt = ev.temporal.consecutive_unchanged_count
            dur = ev.temporal.flatline_duration_minutes
            return f"Sensor persistence check failed. Reading has remained completely unchanged for {cnt} consecutive intervals ({dur:.1f} minutes), indicating possible transducer or mechanical freezing."

        # Case 4: Multivariate Violation
        if DecisionReasonCode.MULTIVARIATE_DEVIATION in reasons or ev.multivariate.is_multivariate_abnormal:
            return "Multivariate thermodynamic consistency check failed. Physical relationship between temperature, relative humidity, and dew point violates August-Roche-Magnus thermodynamic limits."

        # Case 5: Genuine Event
        if dtype == HybridDecisionType.POSSIBLE_GENUINE_EVENT:
            n_valid = ev.spatial.valid_neighbor_count
            rate_str = " Rapid rate of change observed." if ev.temporal.is_rate_abnormal else ""
            if DecisionReasonCode.LOCAL_CLUSTER_AGREEMENT in reasons:
                return f"Localized meso-scale atmospheric variation detected across immediate neighboring cluster.{rate_str} Evidence is consistent with a localized genuine weather transition."
            return f"Atmospheric dynamics corroborated across {n_valid} active regional AWS stations.{rate_str} Evidence is consistent with a regional event.{top_shap_str}"

        # Case 6: Mixed Regional Event with Local Excess
        if DecisionReasonCode.MIXED_REGIONAL_EVENT_WITH_LOCAL_EXCESS in reasons:
            dev_str = f" (+{ev.spatial.temp_target_minus_mean:.2f}°C relative to neighbor mean)" if ev.spatial.temp_target_minus_mean is not None else ""
            return f"Mixed meteorological event: A genuine regional weather transition is underway across surrounding AWS stations, but this station exhibits unphysical excess departure{dev_str}.{top_shap_str}"

        # Case 7: Local Sensor Spike / Isolation / Drift
        if dtype == HybridDecisionType.PROBABLE_SENSOR_ANOMALY:
            dev_str = ""
            if neighbor_comp and neighbor_comp.target_deviation is not None:
                dev_str = f" Station deviates by {neighbor_comp.target_deviation:+.2f} from the neighbor median ({neighbor_comp.neighbor_median:.2f})."
            elif ev.spatial.temp_target_minus_mean is not None:
                dev_str = f" Station departs by {ev.spatial.temp_target_minus_mean:+.2f}°C from regional AWS baseline."

            rate_str = ""
            if ev.temporal.is_rate_abnormal and ev.temporal.temp_rate_per_min is not None:
                rate_str = f" Temperature changed rapidly ({ev.temporal.temp_rate_per_min:+.2f}°C/min) over the latest observation window."

            isolation_str = f" Surrounding network ({ev.spatial.valid_neighbor_count} active stations) remains stable and does not corroborate this change."

            return f"Probable sensor anomaly detected.{rate_str}{dev_str}{isolation_str}{top_shap_str}"

        # Case 8: Uncertain
        if dtype == HybridDecisionType.UNCERTAIN:
            if DecisionReasonCode.INSUFFICIENT_SPATIAL_CONTEXT in reasons or ev.spatial.valid_neighbor_count == 0:
                return f"Uncertain classification: ML anomaly detector flagged elevated residual (score: {ev.ml_anomaly.normalized_anomaly_score:.2f}), but spatial neighborhood telemetry is insufficient to confirm or refute a localized anomaly.{top_shap_str}"
            if DecisionReasonCode.CONFLICTING_EVIDENCE in reasons:
                return f"Uncertain classification: Conflicting evidence between subsystem indicators (ML anomaly score: {ev.ml_anomaly.normalized_anomaly_score:.2f}, active neighbors: {ev.spatial.valid_neighbor_count}). Additional observation cycles required to reach consensus."
            return f"Uncertain classification: Borderline statistical residual (score: {ev.ml_anomaly.normalized_anomaly_score:.2f}) with inconclusive corroboration. Telemetry is under extended observation."

        # Case 9: Normal
        return "Nominal meteorological observation. All physical bounds, temporal rates of change, multivariate thermodynamic relations, and spatial neighbor consensus are within normal operational tolerances."

    def generate_investigation_steps(
        self,
        decision: HybridDecision,
    ) -> List[str]:
        """Generate actionable, prioritized Standard Operating Procedure (SOP) investigation steps."""
        reasons = decision.reason_codes
        dtype = decision.decision
        steps: List[str] = []

        # Data Quality Steps
        if dtype == HybridDecisionType.PROBABLE_DATA_QUALITY_ISSUE:
            if DecisionReasonCode.DATA_GAP in reasons:
                steps.append("1. Inspect AWS cellular/satellite telemetry link and data logger buffer queue for dropped packets.")
            if DecisionReasonCode.MISSING_REQUIRED_VARIABLES in reasons:
                steps.append("2. Validate telemetry packet parsing format and payload decoding configuration for missing fields.")
            if DecisionReasonCode.DUPLICATE_TIMESTAMP in reasons or DecisionReasonCode.OUT_OF_ORDER_TIMESTAMP in reasons:
                steps.append("3. Check ingestion queue sequencing and upstream message timestamping synchronization.")
            steps.append("4. Verify data ingestion pipeline health before dispatching physical station maintenance.")
            return steps

        # Physical Boundary Breach
        if DecisionReasonCode.OUT_OF_RANGE_PHYSICAL in reasons:
            steps.append("1. Perform urgent on-site sensor inspection; reading exceeds physical terrestrial atmospheric limits.")
            steps.append("2. Check transducer wiring for electrical short-circuit or voltage surge.")
            steps.append("3. Compare against portable reference meteorological standard.")
            return steps

        # Stuck Flatline
        if DecisionReasonCode.PERSISTENT_VALUE in reasons:
            steps.append("1. Inspect transducer for mechanical obstruction, icing, or sensor freeze.")
            steps.append("2. Verify analog-to-digital converter (ADC) channel output on data logger.")
            steps.append("3. Power-cycle the sensor interface module.")
            return steps

        # Multivariate Inconsistency
        if DecisionReasonCode.MULTIVARIATE_DEVIATION in reasons:
            steps.append("1. Cross-check temperature and relative humidity sensor pair calibration.")
            steps.append("2. Inspect RH sensor membrane/hygristor for contamination, condensation, or degradation.")
            steps.append("3. Verify barometric pressure transducer against calibrated field barometer.")
            return steps

        # Mixed Event
        if DecisionReasonCode.MIXED_REGIONAL_EVENT_WITH_LOCAL_EXCESS in reasons:
            steps.append("1. Confirm regional synoptic weather event progression across adjacent AWS stations.")
            steps.append("2. Perform calibration check on target station sensor to isolate local gain/offset error.")
            steps.append("3. Cross-validate against station secondary/redundant channel if equipped.")
            return steps

        # Probable Sensor Anomaly (Local Spike / Drift)
        if dtype == HybridDecisionType.PROBABLE_SENSOR_ANOMALY:
            steps.append("1. Inspect sensor transducer and wiring harness for intermittent connection or electrical noise.")
            steps.append("2. Compare target reading with adjacent AWS stations and regional radar/satellite imagery.")
            steps.append("3. Execute on-site zero-point and span calibration check using reference instrument.")
            return steps

        # Genuine Event
        if dtype == HybridDecisionType.POSSIBLE_GENUINE_EVENT:
            steps.append("1. Monitor regional weather event trajectory across AWS station network.")
            steps.append("2. Cross-reference synoptic radar, satellite, and lightning detection products.")
            steps.append("3. No sensor hardware intervention required unless unphysical divergence emerges.")
            return steps

        # Uncertain
        if dtype == HybridDecisionType.UNCERTAIN:
            steps.append("1. Maintain observation over next 3-5 sampling cycles to assess trend stability.")
            steps.append("2. Check nearest neighboring station telemetry status to resolve sparse spatial context.")
            steps.append("3. Review maintenance logs for recent sensor servicing or calibration changes.")
            return steps

        # Normal
        steps.append("1. No operational intervention required. Observation meets quality standards.")
        return steps
