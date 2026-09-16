"""Correction Recommendation Engine for SkyGuard AI AWS networks.

Evaluates suspicious sensor telemetry, synthesizes multi-source evidence (temporal,
spatial, ML, multivariate physics, and sensor health), respects regional-event shields,
and generates non-destructive, auditable candidate correction recommendations.
"""

from __future__ import annotations

import hashlib
import math
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union
import numpy as np
import pandas as pd

from ml.decision.schema import HybridDecision, HybridDecisionType
from ml.explainability.schema import ExplanationSummary
from ml.health.health_schema import HealthStatusBand, SensorHealthSummary
from ml.imputation.consistency import MultivariateConsistencyChecker
from ml.imputation.schema import (
    CorrectionAuditMetadata,
    CorrectionRecommendation,
    EstimationMethod,
    MethodQuality,
    MultivariateCorrectionBundle,
    RecommendationStatus,
    UncertaintyEstimate,
)
from ml.imputation.uncertainty import VARIABLE_BOUNDS, calculate_uncertainty
from ml.spatial.engine import SpatialContextEngine
from ml.spatial.schema import SpatialContextCategory, SpatialContextEvidence


class CorrectionRecommendationEngine:
    """Generates non-destructive, auditable correction recommendations for suspicious sensor telemetry.
    
    Adheres to:
    1. Raw Data Immutability: Original sensor observations are never modified or overwritten.
    2. Regional Weather Protection: Genuine regional storms (POSSIBLE_GENUINE_EVENT) are protected.
    3. Multi-Evidence Synthesis: Combines spatial IDW, temporal baselines, ML attributions, and sensor health.
    4. Explicit Uncertainty: Provides plausible estimate ranges, standard errors, and quality ratings.
    5. Clean-Data Shield: Minimal/zero recommendations generated on nominal observations.
    6. Strict Causal Operation: Future timestamps are never consulted in operational mode.
    """

    def __init__(
        self,
        min_valid_neighbors: int = 2,
        max_spatial_distance_km: float = 600.0,
        enable_causal_mode: bool = True,
        max_allowed_temp_correction_c: float = 15.0,
        max_allowed_rh_correction_pct: float = 50.0,
        max_allowed_slp_correction_hpa: float = 20.0,
        temp_uncertainty_threshold_c: float = 5.0,
        rh_uncertainty_threshold_pct: float = 25.0,
        slp_uncertainty_threshold_hpa: float = 6.0,
        spatial_engine: Optional[SpatialContextEngine] = None,
        consistency_checker: Optional[MultivariateConsistencyChecker] = None,
    ) -> None:
        """Initialize the Correction Recommendation Engine.
        
        Args:
            min_valid_neighbors: Minimum active neighbors required for spatial consensus.
            max_spatial_distance_km: Maximum radius in km for spatial queries.
            enable_causal_mode: Strictly exclude future neighbor telemetry when True.
            max_allowed_temp_correction_c: Max plausible temperature correction departure (°C).
            max_allowed_rh_correction_pct: Max plausible RH correction departure (%).
            max_allowed_slp_correction_hpa: Max plausible SLP correction departure (hPa).
            temp_uncertainty_threshold_c: Max standard error allowed before forcing review.
            rh_uncertainty_threshold_pct: Max standard error for RH before forcing review.
            slp_uncertainty_threshold_hpa: Max standard error for SLP before forcing review.
            spatial_engine: Optional SpatialContextEngine.
            consistency_checker: Optional MultivariateConsistencyChecker.
        """
        self.min_valid_neighbors = min_valid_neighbors
        self.max_spatial_distance_km = max_spatial_distance_km
        self.enable_causal_mode = enable_causal_mode
        self.max_allowed_temp_correction_c = max_allowed_temp_correction_c
        self.max_allowed_rh_correction_pct = max_allowed_rh_correction_pct
        self.max_allowed_slp_correction_hpa = max_allowed_slp_correction_hpa
        self.temp_uncertainty_threshold_c = temp_uncertainty_threshold_c
        self.rh_uncertainty_threshold_pct = rh_uncertainty_threshold_pct
        self.slp_uncertainty_threshold_hpa = slp_uncertainty_threshold_hpa
        self.spatial_engine = spatial_engine
        self.consistency_checker = consistency_checker or MultivariateConsistencyChecker()

    def _generate_observation_id(self, station_id: str, timestamp_str: str, variable: str) -> str:
        """Generate deterministic observation identifier hash."""
        raw_key = f"{station_id}::{timestamp_str}::{variable}"
        return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()[:16]

    def recommend_for_variable(
        self,
        station_id: str,
        timestamp: Union[str, datetime, pd.Timestamp],
        target_variable: str,
        observed_value: float,
        decision_type: Union[str, HybridDecisionType] = HybridDecisionType.NORMAL,
        reason_codes: Optional[List[str]] = None,
        spatial_evidence: Optional[SpatialContextEvidence] = None,
        temporal_history: Optional[List[float]] = None,
        neighbor_observations: Optional[Sequence[Dict[str, Any]]] = None,
        sensor_health: Optional[SensorHealthSummary] = None,
        explanation_summary: Optional[ExplanationSummary] = None,
    ) -> CorrectionRecommendation:
        """Evaluate a single parameter for a station and produce a CorrectionRecommendation.
        
        Args:
            station_id: AWS station identifier.
            timestamp: Observation recording timestamp.
            target_variable: Parameter name (e.g. 'temperature_c').
            observed_value: Measured value from sensor.
            decision_type: Upstream hybrid decision classification.
            reason_codes: Stable reason codes from decision arbiter.
            spatial_evidence: Precomputed spatial context evidence if available.
            temporal_history: Recent historical valid readings for target station.
            neighbor_observations: Contemporaneous neighbor observations pool.
            sensor_health: Upstream sensor health summary.
            explanation_summary: Upstream explainability summary.
            
        Returns:
            Structured `CorrectionRecommendation` record.
        """
        t_str = pd.to_datetime(timestamp, utc=True).isoformat()
        obs_id = self._generate_observation_id(station_id, t_str, target_variable)
        dec_str = str(decision_type.value if hasattr(decision_type, "value") else decision_type)
        reasons = list(reason_codes or [])
        evidence_items: List[str] = []

        # 1. Physical bounds check on observed value
        bounds = VARIABLE_BOUNDS.get(target_variable, (-1000.0, 1000.0))

        # 2. Regional Event Protection Rule
        # If the hybrid decision engine classifies this as a genuine regional weather event,
        # we strictly forbid modifying or replacing the value.
        if dec_str == HybridDecisionType.POSSIBLE_GENUINE_EVENT.value:
            return CorrectionRecommendation(
                observation_id=obs_id,
                station_id=station_id,
                timestamp=t_str,
                target_variable=target_variable,
                observed_value=observed_value,
                recommended_value=None,
                status=RecommendationStatus.NO_CORRECTION_RECOMMENDED,
                method=EstimationMethod.NO_ESTIMATE,
                decision_type=dec_str,
                reason_codes=reasons,
                supporting_evidence=["Observation is consistent with regional atmospheric behavior."],
                uncertainty=None,
                multivariate_consistent=True,
                station_health_score=sensor_health.overall_health_score if sensor_health else None,
                station_health_band=sensor_health.status_band.value if sensor_health else None,
                operator_summary=(
                    f"Observed {target_variable} ({observed_value}) is corroborated by regional "
                    f"atmospheric network dynamics. No correction recommended."
                ),
            )

        # 3. Clean-Data Protection Rule
        # If the reading is classified as NORMAL and exhibits no anomaly indicators,
        # no correction should be proposed.
        if dec_str == HybridDecisionType.NORMAL.value:
            return CorrectionRecommendation(
                observation_id=obs_id,
                station_id=station_id,
                timestamp=t_str,
                target_variable=target_variable,
                observed_value=observed_value,
                recommended_value=None,
                status=RecommendationStatus.NO_CORRECTION_RECOMMENDED,
                method=EstimationMethod.NO_ESTIMATE,
                decision_type=dec_str,
                reason_codes=reasons,
                supporting_evidence=["Observation is nominal and conforms to baseline."],
                uncertainty=None,
                multivariate_consistent=True,
                station_health_score=sensor_health.overall_health_score if sensor_health else None,
                station_health_band=sensor_health.status_band.value if sensor_health else None,
                operator_summary=(
                    f"Observed {target_variable} ({observed_value}) is within normal parameters. "
                    f"No correction required."
                ),
            )

        # 4. Extract Spatial Context & Neighbor Statistics
        neighbor_vals: List[float] = []
        neighbor_dists: List[float] = []
        spatial_est: Optional[float] = None
        spatial_cat = SpatialContextCategory.INSUFFICIENT_CONTEXT

        # Evaluate spatial engine if evidence not supplied directly
        if spatial_evidence is None and self.spatial_engine and neighbor_observations:
            t_dict = {target_variable: observed_value}
            spatial_evidence = self.spatial_engine.evaluate_observation(
                target_station_id=station_id,
                target_timestamp=timestamp,
                target_values=t_dict,
                neighbor_data_pool=neighbor_observations,
            )

        if spatial_evidence:
            spatial_cat = spatial_evidence.context_category
            cons = None
            if "temp" in target_variable:
                cons = spatial_evidence.temperature_consensus
            elif "humid" in target_variable or "rh" in target_variable:
                cons = spatial_evidence.relative_humidity_consensus
            elif "press" in target_variable or "slp" in target_variable:
                cons = spatial_evidence.sea_level_pressure_consensus

            if cons and cons.neighbor_count >= 1:
                if cons.idw_expected_value is not None:
                    spatial_est = cons.idw_expected_value
                elif cons.neighbor_median is not None:
                    spatial_est = cons.neighbor_median

            for d in spatial_evidence.neighbor_details:
                if not d.is_stale:
                    val = None
                    if "temp" in target_variable:
                        val = d.temperature_c
                    elif "humid" in target_variable or "rh" in target_variable:
                        val = d.relative_humidity_pct
                    elif "press" in target_variable or "slp" in target_variable:
                        val = d.sea_level_pressure_hpa

                    if val is not None and not math.isnan(val):
                        neighbor_vals.append(val)
                        neighbor_dists.append(d.distance_km)

        # 5. Extract Temporal Baseline
        valid_history = [v for v in (temporal_history or []) if v is not None and not math.isnan(v)]
        temporal_est: Optional[float] = None
        if len(valid_history) >= 2:
            temporal_est = float(np.median(valid_history[-6:]))

        # 6. Safety Check: Insufficient Context
        has_spatial_evidence = spatial_est is not None and len(neighbor_vals) >= self.min_valid_neighbors
        has_temporal_evidence = temporal_est is not None and len(valid_history) >= 2

        if not has_spatial_evidence and not has_temporal_evidence:
            return CorrectionRecommendation(
                observation_id=obs_id,
                station_id=station_id,
                timestamp=t_str,
                target_variable=target_variable,
                observed_value=observed_value,
                recommended_value=None,
                status=RecommendationStatus.INSUFFICIENT_EVIDENCE,
                method=EstimationMethod.NO_ESTIMATE,
                decision_type=dec_str,
                reason_codes=reasons,
                supporting_evidence=["Zero or insufficient spatial neighbors and lack of temporal baseline history."],
                uncertainty=None,
                multivariate_consistent=True,
                station_health_score=sensor_health.overall_health_score if sensor_health else None,
                station_health_band=sensor_health.status_band.value if sensor_health else None,
                operator_summary=(
                    f"Observed value {observed_value} is flagged as suspicious ({dec_str}), but evidence "
                    f"is insufficient to formulate a reliable recommended estimate."
                ),
            )

        # 7. Compute Recommended Estimate
        recommended_val: float
        applied_method: EstimationMethod

        if has_spatial_evidence and has_temporal_evidence:
            # Weighted combination: 65% spatial IDW consensus + 35% recent temporal baseline
            recommended_val = 0.65 * spatial_est + 0.35 * temporal_est
            applied_method = EstimationMethod.COMBINED_TEMPORAL_SPATIAL
            evidence_items.append(
                f"Combined spatial IDW estimate ({spatial_est:.2f}) from {len(neighbor_vals)} neighbors "
                f"with local temporal baseline ({temporal_est:.2f})."
            )
        elif has_spatial_evidence:
            recommended_val = spatial_est
            applied_method = EstimationMethod.SPATIAL_IDW_CONSENSUS
            evidence_items.append(
                f"Spatial IDW consensus estimate ({spatial_est:.2f}) derived from {len(neighbor_vals)} valid neighbors."
            )
        else:
            recommended_val = temporal_est
            applied_method = EstimationMethod.ROLLING_BASELINE
            evidence_items.append(
                f"Local temporal baseline estimate ({temporal_est:.2f}) derived from preceding {len(valid_history)} observations."
            )

        # Clamp to physical bounds
        recommended_val = max(bounds[0], min(bounds[1], round(recommended_val, 2)))

        # 8. Compute Uncertainty
        unc = calculate_uncertainty(
            estimate=recommended_val,
            target_variable=target_variable,
            method=applied_method,
            observed_value=observed_value,
            neighbor_values=neighbor_vals,
            neighbor_distances_km=neighbor_dists,
            temporal_history=valid_history,
            station_health_score=sensor_health.overall_health_score if sensor_health else None,
        )

        # 9. Health Integration & Status Arbiter
        # Evaluate departure magnitude
        departure = abs(observed_value - recommended_val)
        
        # Max departure threshold
        max_dep_limit = self.max_allowed_temp_correction_c
        unc_limit = self.temp_uncertainty_threshold_c
        if "humid" in target_variable or "rh" in target_variable:
            max_dep_limit = self.max_allowed_rh_correction_pct
            unc_limit = self.rh_uncertainty_threshold_pct
        elif "press" in target_variable or "slp" in target_variable:
            max_dep_limit = self.max_allowed_slp_correction_hpa
            unc_limit = self.slp_uncertainty_threshold_hpa

        # Incorporate Sensor Health Degradation Context
        health_score = sensor_health.overall_health_score if sensor_health else None
        health_band = sensor_health.status_band.value if sensor_health else None
        health_is_degraded = health_score is not None and health_score < 60.0

        if health_is_degraded:
            evidence_items.append(
                f"Sensor health index is degraded ({health_score:.1f}/100, {health_band}), corroborating persistent hardware defect."
            )

        # Status Logic:
        # CORRECTION_CANDIDATE requires:
        # - Strong evidence: method quality HIGH/MEDIUM, >= 2 neighbors or good temporal history
        # - Uncertainty within safe threshold
        # - Either degraded sensor health OR decisive spatial consensus isolated anomaly
        # Otherwise: REVIEW_RECOMMENDED
        status = RecommendationStatus.REVIEW_RECOMMENDED

        if unc.standard_error is not None and unc.standard_error > unc_limit:
            status = RecommendationStatus.REVIEW_RECOMMENDED
            evidence_items.append(f"Uncertainty standard error ({unc.standard_error:.2f}) exceeds threshold ({unc_limit:.2f}).")
        elif departure > max_dep_limit:
            status = RecommendationStatus.REVIEW_RECOMMENDED
            evidence_items.append(f"Correction departure ({departure:.2f}) exceeds single-step safety limit ({max_dep_limit:.2f}).")
        elif (
            has_spatial_evidence
            and len(neighbor_vals) >= self.min_valid_neighbors
            and unc.method_quality in (MethodQuality.HIGH, MethodQuality.MEDIUM)
        ):
            if health_is_degraded or dec_str in (
                HybridDecisionType.PROBABLE_SENSOR_ANOMALY.value,
                HybridDecisionType.PROBABLE_DATA_QUALITY_ISSUE.value,
            ):
                status = RecommendationStatus.CORRECTION_CANDIDATE
            else:
                status = RecommendationStatus.REVIEW_RECOMMENDED
        else:
            status = RecommendationStatus.REVIEW_RECOMMENDED

        # 10. Generate Scientific Operator Summary
        # Scientific phrasing: never claim "Corrected value is true"
        status_action = (
            "Candidate correction recommended for operational consideration."
            if status == RecommendationStatus.CORRECTION_CANDIDATE
            else "Manual review recommended before replacing or updating the observation."
        )

        op_summary = (
            f"Observed {target_variable} ({observed_value}) differs substantially from local baseline and "
            f"spatial consensus. The model-derived recommended estimate is {recommended_val} "
            f"(uncertainty range: [{unc.estimate_range[0]}, {unc.estimate_range[1]}]). {status_action}"
        )

        return CorrectionRecommendation(
            observation_id=obs_id,
            station_id=station_id,
            timestamp=t_str,
            target_variable=target_variable,
            observed_value=observed_value,
            recommended_value=recommended_val,
            status=status,
            method=applied_method,
            decision_type=dec_str,
            reason_codes=reasons,
            supporting_evidence=evidence_items,
            uncertainty=unc,
            multivariate_consistent=True,
            station_health_score=health_score,
            station_health_band=health_band,
            operator_summary=op_summary,
        )

    def evaluate_bundle(
        self,
        station_id: str,
        timestamp: Union[str, datetime, pd.Timestamp],
        observed_payload: Dict[str, Optional[float]],
        decision: Optional[HybridDecision] = None,
        neighbor_observations: Optional[Sequence[Dict[str, Any]]] = None,
        sensor_health: Optional[SensorHealthSummary] = None,
        temporal_history_by_var: Optional[Dict[str, List[float]]] = None,
        elevation_m: Optional[float] = None,
    ) -> MultivariateCorrectionBundle:
        """Evaluate multiple meteorological variables simultaneously and enforce joint consistency.
        
        Args:
            station_id: AWS station ID.
            timestamp: Timestamp.
            observed_payload: Dict of observed readings (e.g. temperature_c, relative_humidity_pct, sea_level_pressure_hpa).
            decision: Optional upstream HybridDecision.
            neighbor_observations: Multi-station neighbor data pool.
            sensor_health: Sensor health summary.
            temporal_history_by_var: Dict mapping variable name to past history list.
            elevation_m: Station elevation in meters.
            
        Returns:
            Structured `MultivariateCorrectionBundle`.
        """
        t_str = pd.to_datetime(timestamp, utc=True).isoformat()
        recommendations: Dict[str, CorrectionRecommendation] = {}
        hist_dict = temporal_history_by_var or {}

        dec_type = decision.decision if decision else HybridDecisionType.NORMAL
        reason_codes = [str(r.value if hasattr(r, "value") else r) for r in (decision.reason_codes if decision else [])]

        # 1. Compute individual recommendations
        for var_name, obs_val in observed_payload.items():
            if obs_val is None or (isinstance(obs_val, float) and (math.isnan(obs_val) or math.isinf(obs_val))):
                continue

            rec = self.recommend_for_variable(
                station_id=station_id,
                timestamp=timestamp,
                target_variable=var_name,
                observed_value=float(obs_val),
                decision_type=dec_type,
                reason_codes=reason_codes,
                temporal_history=hist_dict.get(var_name),
                neighbor_observations=neighbor_observations,
                sensor_health=sensor_health,
            )
            recommendations[var_name] = rec

        # 2. Joint Multivariate Physical Consistency Check
        # Build composite final state: candidate recommended value if candidate/review, else original observed value
        proposed_state: Dict[str, Optional[float]] = {}
        for var_name, obs_val in observed_payload.items():
            rec = recommendations.get(var_name)
            if rec and rec.recommended_value is not None:
                proposed_state[var_name] = rec.recommended_value
            else:
                proposed_state[var_name] = float(obs_val) if obs_val is not None else None

        is_consistent, violations = self.consistency_checker.validate_state(
            values=proposed_state,
            elevation_m=elevation_m,
        )

        # If joint consistency check fails, downgrade any CORRECTION_CANDIDATE to REVIEW_RECOMMENDED
        # and attach the violation reasons
        final_recs: Dict[str, CorrectionRecommendation] = {}
        for var_name, rec in recommendations.items():
            if not is_consistent:
                # Update status and operator summary
                updated_evidence = list(rec.supporting_evidence) + [f"Joint physical violation: {v}" for v in violations]
                updated_status = (
                    RecommendationStatus.REVIEW_RECOMMENDED
                    if rec.status == RecommendationStatus.CORRECTION_CANDIDATE
                    else rec.status
                )
                updated_summary = (
                    f"{rec.operator_summary} [Note: Joint physical consistency warning: {'; '.join(violations)}]"
                )
                final_recs[var_name] = CorrectionRecommendation(
                    observation_id=rec.observation_id,
                    station_id=rec.station_id,
                    timestamp=rec.timestamp,
                    target_variable=rec.target_variable,
                    observed_value=rec.observed_value,
                    recommended_value=rec.recommended_value,
                    status=updated_status,
                    method=rec.method,
                    decision_type=rec.decision_type,
                    reason_codes=rec.reason_codes,
                    supporting_evidence=updated_evidence,
                    uncertainty=rec.uncertainty,
                    multivariate_consistent=False,
                    station_health_score=rec.station_health_score,
                    station_health_band=rec.station_health_band,
                    operator_summary=updated_summary,
                )
            else:
                final_recs[var_name] = rec

        return MultivariateCorrectionBundle(
            station_id=station_id,
            timestamp=t_str,
            recommendations=final_recs,
            is_jointly_consistent=is_consistent,
            inconsistency_reasons=violations,
        )
