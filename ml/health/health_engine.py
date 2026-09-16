"""Master Sensor Health & Degradation Monitoring Engine for SkyGuard AI."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union
import numpy as np
import yaml

from ml.decision.schema import (
    DecisionReasonCode,
    DecisionSeverity,
    HybridDecision,
    HybridDecisionType,
)
from ml.health.health_features import HealthFeatureExtractor
from ml.health.health_history import HealthHistoryBuffer
from ml.health.health_schema import (
    ComponentHealthScores,
    HealthAuditMetadata,
    HealthReasonCode,
    HealthStatusBand,
    HealthTrend,
    MaintenanceRecommendation,
    ParameterHealth,
    SensorHealthSummary,
)


class SensorHealthEngine:
    """Computes transparent 0-100 Sensor Health Index, trends, and maintenance recommendations."""

    def __init__(
        self,
        config_path: Optional[Union[str, Path]] = None,
        feature_version: str = "v1.0.0",
        decision_engine_version: str = "hybrid_v1.0.0",
        health_engine_version: str = "health_v1.0.0",
    ) -> None:
        """Initialize Sensor Health Engine.
        
        Args:
            config_path: Path to `configs/sensor_health.yaml`.
            feature_version: Upstream feature version.
            decision_engine_version: Upstream decision engine version.
            health_engine_version: Health engine semantic version.
        """
        self.config = self._load_config(config_path)
        self.feature_version = feature_version
        self.decision_engine_version = decision_engine_version
        self.health_engine_version = health_engine_version

        self._unpack_config()
        self.feature_extractor = HealthFeatureExtractor(
            severity_penalties=self.severity_penalties,
            nominal_sampling_interval_min=5.0,
        )
        self.history_buffer = HealthHistoryBuffer(
            default_window=self.default_window,
            window_definitions=self.window_definitions,
            recency_lambda=self.recency_lambda,
        )

    def _load_config(self, config_path: Optional[Union[str, Path]]) -> Dict[str, Any]:
        """Load configuration dictionary from YAML or defaults."""
        path = Path(config_path) if config_path else Path("configs/sensor_health.yaml")
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}

        # Fallback default configuration
        return {
            "health_engine": {"min_observations_required": 12},
            "weights": {
                "anomaly_health": 0.30,
                "data_quality_health": 0.20,
                "communication_health": 0.15,
                "temporal_stability_health": 0.20,
                "spatial_consistency_health": 0.15,
            },
            "time_windows": {"24h": 24.0, "7d": 168.0, "30d": 720.0, "default_window": "24h"},
            "recency": {"enabled": True, "decay_lambda": 1.5},
            "severity_penalties": {"INFO": 0.0, "LOW": 0.25, "MEDIUM": 0.60, "HIGH": 1.00, "CRITICAL": 2.00},
            "trend": {"improving_threshold": 3.0, "degrading_threshold": -3.0},
        }

    def _unpack_config(self) -> None:
        """Unpack configuration variables."""
        he = self.config.get("health_engine", {})
        self.min_observations = int(he.get("min_observations_required", 12))

        w = self.config.get("weights", {})
        self.w_anom = float(w.get("anomaly_health", 0.30))
        self.w_dq = float(w.get("data_quality_health", 0.20))
        self.w_comm = float(w.get("communication_health", 0.15))
        self.w_temp = float(w.get("temporal_stability_health", 0.20))
        self.w_spat = float(w.get("spatial_consistency_health", 0.15))

        tw = self.config.get("time_windows", {})
        self.window_definitions = {k: float(v) for k, v in tw.items() if k != "default_window"}
        self.default_window = str(tw.get("default_window", "24h"))

        rc = self.config.get("recency", {})
        self.recency_enabled = bool(rc.get("enabled", True))
        self.recency_lambda = float(rc.get("decay_lambda", 1.5))

        self.severity_penalties = self.config.get("severity_penalties", {
            "INFO": 0.0, "LOW": 0.25, "MEDIUM": 0.60, "HIGH": 1.00, "CRITICAL": 2.00,
        })

        tr = self.config.get("trend", {})
        self.trend_improving = float(tr.get("improving_threshold", 3.0))
        self.trend_degrading = float(tr.get("degrading_threshold", -3.0))

    def evaluate_station_health(
        self,
        station_id: str,
        decisions: Optional[Sequence[HybridDecision]] = None,
        window: str = "24h",
        custom_hours: Optional[float] = None,
        previous_decisions: Optional[Sequence[HybridDecision]] = None,
    ) -> SensorHealthSummary:
        """Calculate comprehensive station and parameter-level health index.
        
        Args:
            station_id: Target AWS station identifier.
            decisions: Optional sequence of decisions in the evaluated window.
                       If None, queries from internal `history_buffer`.
            window: Named window key ('24h', '7d', '30d').
            custom_hours: Explicit window duration in hours.
            previous_decisions: Optional preceding window decisions for trend comparison.
            
        Returns:
            `SensorHealthSummary` object.
        """
        # Retrieve decisions if not explicitly provided
        recency_weights = None
        if decisions is None:
            curr_decs, recency_weights = self.history_buffer.get_window_decisions(
                station_id=station_id,
                window=window,
                custom_hours=custom_hours,
            )
            eval_decisions = curr_decs
            if previous_decisions is None:
                _, prev_decs = self.history_buffer.get_comparison_windows(
                    station_id=station_id,
                    window=window,
                )
                eval_prev_decisions = prev_decs
            else:
                eval_prev_decisions = list(previous_decisions)
        else:
            eval_decisions = list(decisions)
            eval_prev_decisions = list(previous_decisions) if previous_decisions is not None else []
            if self.recency_enabled and len(eval_decisions) > 0:
                # Generate linear/exponential decay array
                n = len(eval_decisions)
                age_fracs = np.linspace(1.0, 0.0, n)
                recency_weights = np.exp(-self.recency_lambda * age_fracs)
                recency_weights = recency_weights / np.mean(recency_weights)

        window_hours = custom_hours or self.window_definitions.get(window, 24.0)
        total_obs = len(eval_decisions)

        audit_meta = HealthAuditMetadata(
            health_engine_version=self.health_engine_version,
            decision_engine_version=self.decision_engine_version,
            feature_version=self.feature_version,
            window_name=window,
            window_hours=window_hours,
            min_observations_required=self.min_observations,
            total_observations_evaluated=total_obs,
            generated_at=datetime.now(timezone.utc).isoformat(),
        )

        # 1. LOW-DATA / INSUFFICIENT HISTORY CHECK
        if total_obs < self.min_observations:
            return SensorHealthSummary(
                station_id=station_id,
                window_name=window,
                overall_health_score=None,
                status_band=HealthStatusBand.INSUFFICIENT_HISTORY,
                trend=HealthTrend.INSUFFICIENT_HISTORY,
                health_delta=None,
                component_scores=ComponentHealthScores(
                    anomaly_health=100.0,
                    data_quality_health=100.0,
                    communication_health=100.0,
                    temporal_stability_health=100.0,
                    spatial_consistency_health=100.0,
                ),
                parameter_health={},
                maintenance_recommendation=MaintenanceRecommendation.MONITOR,
                reason_codes=[HealthReasonCode.INSUFFICIENT_OBSERVATION_HISTORY],
                summary=f"Insufficient observation history ({total_obs} observed < {self.min_observations} required) to calculate a statistically sound health index. Telemetry under initial observation.",
                supporting_evidence=[f"Observed count: {total_obs}, Minimum required: {self.min_observations}"],
                recommended_action="Continue collecting observations. Reliability evaluation will activate once minimum history is reached.",
                audit_metadata=audit_meta,
            )

        # 2. Compute 5-Dimensional Component Scores
        comp_scores, supporting_notes, reason_codes = self._compute_components(
            decisions=eval_decisions,
            recency_weights=recency_weights,
            window_hours=window_hours,
        )

        # 3. Overall Health Composite
        overall_score = (
            self.w_anom * comp_scores.anomaly_health
            + self.w_dq * comp_scores.data_quality_health
            + self.w_comm * comp_scores.communication_health
            + self.w_temp * comp_scores.temporal_stability_health
            + self.w_spat * comp_scores.spatial_consistency_health
        )
        overall_score = float(np.clip(round(overall_score, 1), 0.0, 100.0))

        # 4. Status Band
        status_band = self._assign_health_band(overall_score)

        # 5. Trend Calculation
        health_delta = None
        trend = HealthTrend.STABLE
        if eval_prev_decisions and len(eval_prev_decisions) >= self.min_observations:
            prev_comp, _, _ = self._compute_components(
                decisions=eval_prev_decisions,
                recency_weights=None,
                window_hours=window_hours,
            )
            prev_score = (
                self.w_anom * prev_comp.anomaly_health
                + self.w_dq * prev_comp.data_quality_health
                + self.w_comm * prev_comp.communication_health
                + self.w_temp * prev_comp.temporal_stability_health
                + self.w_spat * prev_comp.spatial_consistency_health
            )
            health_delta = float(round(overall_score - prev_score, 1))
            if health_delta >= self.trend_improving:
                trend = HealthTrend.IMPROVING
                reason_codes.append(HealthReasonCode.RECENT_RECOVERY_OBSERVED)
            elif health_delta <= self.trend_degrading:
                trend = HealthTrend.DEGRADING
            else:
                trend = HealthTrend.STABLE

        # 6. Parameter-Level Health Breakdown
        param_health = self._compute_parameter_breakdowns(
            decisions=eval_decisions,
            recency_weights=recency_weights,
            window_hours=window_hours,
        )

        # 7. Maintenance Recommendation & SOP Actions
        maint_rec, action_text = self._determine_maintenance_recommendation(
            overall_score=overall_score,
            status_band=status_band,
            trend=trend,
            reason_codes=reason_codes,
            param_health=param_health,
        )

        # 8. Deterministic Summary Synthesis
        summary_text = self._synthesize_health_summary(
            overall_score=overall_score,
            status_band=status_band,
            trend=trend,
            comp_scores=comp_scores,
            reason_codes=reason_codes,
            param_health=param_health,
        )

        return SensorHealthSummary(
            station_id=station_id,
            window_name=window,
            overall_health_score=overall_score,
            status_band=status_band,
            trend=trend,
            health_delta=health_delta,
            component_scores=comp_scores,
            parameter_health=param_health,
            maintenance_recommendation=maint_rec,
            reason_codes=list(dict.fromkeys(reason_codes)),
            summary=summary_text,
            supporting_evidence=supporting_notes,
            recommended_action=action_text,
            audit_metadata=audit_meta,
        )

    def _compute_components(
        self,
        decisions: Sequence[HybridDecision],
        recency_weights: Optional[np.ndarray],
        window_hours: float,
    ) -> Tuple[ComponentHealthScores, List[str], List[HealthReasonCode]]:
        """Calculate the 5 distinct component scores."""
        total = len(decisions)
        notes: List[str] = []
        reasons: List[HealthReasonCode] = []

        # A. Anomaly Health
        anom_stats = self.feature_extractor.extract_anomaly_stats(decisions, recency_weights)
        # Deduct based on severity-weighted anomaly frequency
        # Baseline capacity: ~10% severe anomalies reduces anomaly health by 100 points
        anom_penalty = min(100.0, (anom_stats.severity_weighted_anomalies / max(1.0, 0.12 * total)) * 100.0)
        anom_health = float(np.clip(100.0 - anom_penalty, 0.0, 100.0))

        if anom_stats.is_persistent:
            reasons.append(HealthReasonCode.PERSISTENT_ANOMALY)
            notes.append(f"Persistent anomaly sequence detected ({anom_stats.max_consecutive_anomalies} consecutive steps).")
        elif anom_stats.is_repeated:
            reasons.append(HealthReasonCode.REPEATED_ANOMALIES)
            notes.append(f"Repeated anomalous observations ({anom_stats.anomaly_count} events, rate: {anom_stats.anomaly_rate_per_100:.1f}%).")

        if anom_stats.genuine_event_count > 0:
            notes.append(f"Corroborated regional weather events ({anom_stats.genuine_event_count} observations) protected from health penalty.")

        # B. Data Quality Health
        dq_stats = self.feature_extractor.extract_data_quality_stats(decisions, recency_weights)
        dq_penalty = min(100.0, (dq_stats.dq_defect_rate / 0.15) * 100.0)
        dq_health = float(np.clip(100.0 - dq_penalty, 0.0, 100.0))

        if dq_stats.missing_fields_count > 0:
            reasons.append(HealthReasonCode.HIGH_MISSING_RATE)
            notes.append(f"Missing required meteorological fields ({dq_stats.missing_fields_count} instances).")

        # C. Communication Health
        comm_stats = self.feature_extractor.extract_communication_stats(decisions)
        window_minutes = window_hours * 60.0
        # 15% communication outage = 0 comm health
        comm_penalty = min(100.0, (comm_stats.total_gap_minutes / max(1.0, window_minutes * 0.15)) * 100.0)
        comm_health = float(np.clip(100.0 - comm_penalty, 0.0, 100.0))

        if comm_stats.gap_episodes_count > 0:
            reasons.append(HealthReasonCode.COMMUNICATION_INSTABILITY)
            notes.append(f"Telemetry communication outages ({comm_stats.total_gap_minutes:.1f} min across {comm_stats.gap_episodes_count} episodes).")

        # D. Temporal Stability Health
        temp_stats = self.feature_extractor.extract_temporal_stability_stats(decisions)
        temp_penalty = min(100.0, (temp_stats.total_flatline_minutes / max(1.0, window_minutes * 0.10)) * 100.0)
        temp_health = float(np.clip(100.0 - temp_penalty, 0.0, 100.0))

        if temp_stats.stuck_sensor_flag:
            reasons.append(HealthReasonCode.PERSISTENT_FLATLINE)
            notes.append(f"Sensor flatline / stuck readings ({temp_stats.total_flatline_minutes:.1f} min, max run: {temp_stats.max_flatline_steps} steps).")

        # E. Spatial Consistency Health
        spat_stats = self.feature_extractor.extract_spatial_consistency_stats(decisions)
        drift_stats = self.feature_extractor.extract_drift_stats(decisions)
        
        spat_penalty = min(100.0, (spat_stats.isolation_rate / 0.15) * 100.0)
        if drift_stats.has_significant_drift:
            spat_penalty = min(100.0, spat_penalty + 30.0)
            reasons.append(HealthReasonCode.INCREASING_DRIFT)
            notes.append(f"Progressive calibration drift detected (mean departure: {drift_stats.drift_magnitude:.2f}°C, persistence: {drift_stats.drift_persistence_fraction*100:.0f}%).")

        spat_health = float(np.clip(100.0 - spat_penalty, 0.0, 100.0))

        if spat_stats.spatial_isolation_count >= 3:
            reasons.append(HealthReasonCode.REPEATED_LOCAL_SPATIAL_DEVIATION)
            notes.append(f"Repeated uncorroborated single-station spatial departures ({spat_stats.spatial_isolation_count} instances).")

        if not reasons:
            reasons.append(HealthReasonCode.NOMINAL_OPERATION)
            notes.append("All observation streams, telemetry links, and spatial consensus metrics within healthy operational tolerances.")

        scores = ComponentHealthScores(
            anomaly_health=round(anom_health, 1),
            data_quality_health=round(dq_health, 1),
            communication_health=round(comm_health, 1),
            temporal_stability_health=round(temp_health, 1),
            spatial_consistency_health=round(spat_health, 1),
        )

        return scores, notes, reasons

    def _compute_parameter_breakdowns(
        self,
        decisions: Sequence[HybridDecision],
        recency_weights: Optional[np.ndarray],
        window_hours: float,
    ) -> Dict[str, ParameterHealth]:
        """Compute channel-specific health assessments for Temperature, RH, and Pressure."""
        parameters = ["temperature_c", "relative_humidity", "sea_level_pressure_hpa"]
        results: Dict[str, ParameterHealth] = {}

        for param in parameters:
            # Extract channel specific indicators
            drift_stats = self.feature_extractor.extract_drift_stats(decisions, target_param=param)
            temp_stats = self.feature_extractor.extract_temporal_stability_stats(decisions)
            anom_stats = self.feature_extractor.extract_anomaly_stats(decisions, recency_weights, target_param=param)

            # Parameter-level score composite
            param_score = 100.0
            p_notes: List[str] = []

            if drift_stats.has_significant_drift:
                param_score -= min(40.0, drift_stats.drift_magnitude * 8.0)
                p_notes.append(f"Drift indicator: {drift_stats.drift_magnitude:.2f} units.")
            if temp_stats.stuck_sensor_flag:
                param_score -= min(50.0, temp_stats.total_flatline_minutes * 0.5)
                p_notes.append(f"Flatline duration: {temp_stats.total_flatline_minutes:.1f} min.")
            if anom_stats.anomaly_count > 0:
                param_score -= min(30.0, anom_stats.anomaly_count * 5.0)

            param_score = float(np.clip(round(param_score, 1), 0.0, 100.0))
            band = self._assign_health_band(param_score)

            results[param] = ParameterHealth(
                parameter_name=param,
                health_score=param_score,
                status_band=band,
                trend=HealthTrend.STABLE,
                drift_indicator=drift_stats.drift_magnitude if drift_stats.has_significant_drift else None,
                flatline_duration_minutes=temp_stats.total_flatline_minutes,
                supporting_evidence=p_notes if p_notes else ["Channel operating within normal physical parameters."],
            )

        return results

    def _assign_health_band(self, score: float) -> HealthStatusBand:
        """Map numerical 0-100 score to qualitative operational band."""
        if score >= 90.0:
            return HealthStatusBand.HEALTHY
        if score >= 75.0:
            return HealthStatusBand.GOOD
        if score >= 50.0:
            return HealthStatusBand.ATTENTION
        if score >= 25.0:
            return HealthStatusBand.DEGRADED
        return HealthStatusBand.CRITICAL

    def _determine_maintenance_recommendation(
        self,
        overall_score: float,
        status_band: HealthStatusBand,
        trend: HealthTrend,
        reason_codes: Sequence[HealthReasonCode],
        param_health: Dict[str, ParameterHealth],
    ) -> Tuple[MaintenanceRecommendation, str]:
        """Determine actionable maintenance recommendation without failure predictions."""
        # Priority Inspection
        if status_band == HealthStatusBand.CRITICAL or (status_band == HealthStatusBand.DEGRADED and trend == HealthTrend.DEGRADING):
            return (
                MaintenanceRecommendation.PRIORITY_INSPECTION,
                "Priority on-site maintenance required. Severe degradation indicators or persistent physical/hardware anomalies detected.",
            )

        # Inspect if overall degraded, or attention with degrading trend, or if any individual channel is CRITICAL/DEGRADED, or persistent flatline
        has_critical_channel = any(h.status_band in (HealthStatusBand.CRITICAL, HealthStatusBand.DEGRADED) for h in param_health.values())
        has_persistent_issue = HealthReasonCode.PERSISTENT_FLATLINE in reason_codes or HealthReasonCode.PERSISTENT_ANOMALY in reason_codes

        if status_band == HealthStatusBand.DEGRADED or (status_band == HealthStatusBand.ATTENTION and trend == HealthTrend.DEGRADING) or has_critical_channel or has_persistent_issue:
            return (
                MaintenanceRecommendation.INSPECT,
                "Schedule sensor inspection and field calibration check during next routine maintenance window.",
            )

        # Monitor
        if status_band == HealthStatusBand.ATTENTION or trend == HealthTrend.DEGRADING:
            return (
                MaintenanceRecommendation.MONITOR,
                "Increase monitoring cadence. Minor performance degradation observed across telemetry or spatial consistency channels.",
            )

        # No Action
        return (
            MaintenanceRecommendation.NO_ACTION,
            "No maintenance action required. Observed reliability indicators remain favorable across all sensor channels.",
        )

    def _synthesize_health_summary(
        self,
        overall_score: float,
        status_band: HealthStatusBand,
        trend: HealthTrend,
        comp_scores: ComponentHealthScores,
        reason_codes: Sequence[HealthReasonCode],
        param_health: Dict[str, ParameterHealth],
    ) -> str:
        """Synthesize deterministic, operator-readable health explanation."""
        trend_desc = {
            HealthTrend.IMPROVING: "improving",
            HealthTrend.STABLE: "stable",
            HealthTrend.DEGRADING: "degrading",
            HealthTrend.INSUFFICIENT_HISTORY: "under initial observation",
        }.get(trend, "stable")

        parts = [
            f"Sensor Health Index: {overall_score:.1f}/100 ({status_band.value}, trend: {trend_desc}).",
        ]

        # Mention weak components if any
        weak_comps = []
        if comp_scores.anomaly_health < 75.0:
            weak_comps.append(f"anomaly frequency ({comp_scores.anomaly_health:.0f})")
        if comp_scores.data_quality_health < 75.0:
            weak_comps.append(f"data quality ({comp_scores.data_quality_health:.0f})")
        if comp_scores.communication_health < 75.0:
            weak_comps.append(f"telemetry link ({comp_scores.communication_health:.0f})")
        if comp_scores.temporal_stability_health < 75.0:
            weak_comps.append(f"temporal stability ({comp_scores.temporal_stability_health:.0f})")
        if comp_scores.spatial_consistency_health < 75.0:
            weak_comps.append(f"spatial consistency ({comp_scores.spatial_consistency_health:.0f})")

        if weak_comps:
            parts.append(f"Primary deductions observed in {', '.join(weak_comps)}.")
        else:
            parts.append("All subsystem health indicators remain in good standing.")

        # Mention single channel failures if applicable
        channel_alerts = [f"{p} ({h.status_band.value})" for p, h in param_health.items() if h.status_band in (HealthStatusBand.DEGRADED, HealthStatusBand.CRITICAL)]
        if channel_alerts:
            parts.append(f"Specific sensor channels requiring attention: {', '.join(channel_alerts)}.")

        return " ".join(parts)
