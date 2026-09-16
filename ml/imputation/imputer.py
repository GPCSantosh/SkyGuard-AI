"""Missing Data Imputer for SkyGuard AI AWS telemetry networks.

Implements gap-length safety bounds, strictly causal historical estimation by default,
retrospective offline mode, spatial neighbor IDW assistance, and non-destructive
imputation records.
"""

from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence, Union
import numpy as np
import pandas as pd

from ml.imputation.schema import (
    EstimationMethod,
    ImputationRecord,
    ImputationStatus,
    UncertaintyEstimate,
)
from ml.imputation.uncertainty import VARIABLE_BOUNDS, calculate_uncertainty
from ml.spatial.engine import SpatialContextEngine
from ml.spatial.topology import SpatialNetworkTopology


class MissingDataImputer:
    """Estimates values for missing sensor readings across Automatic Weather Stations.
    
    Adheres to:
    1. Gap-length safety: rejects estimation when gap exceeds safety tolerance.
    2. Causal operation: real-time streaming mode never uses future timestamps.
    3. Multi-method support: temporal interpolation, spatial IDW, rolling baselines.
    4. Non-destructive outputs: returns ImputationRecord without altering raw inputs.
    """

    def __init__(
        self,
        max_interpolation_gap_minutes: float = 60.0,
        max_consecutive_missing_steps: int = 12,
        default_mode: str = "causal",
        rolling_window_steps: int = 12,
        min_history_steps: int = 3,
        spatial_engine: Optional[SpatialContextEngine] = None,
    ) -> None:
        """Initialize the Missing Data Imputer.
        
        Args:
            max_interpolation_gap_minutes: Maximum gap duration in minutes permitted for imputation.
            max_consecutive_missing_steps: Maximum consecutive missing steps permitted.
            default_mode: 'causal' (default real-time) or 'retrospective' (offline analysis).
            rolling_window_steps: Window size for local temporal baseline.
            min_history_steps: Minimum historical observations needed for temporal extrapolation.
            spatial_engine: Optional SpatialContextEngine instance for neighbor-assisted estimation.
        """
        self.max_interpolation_gap_minutes = max_interpolation_gap_minutes
        self.max_consecutive_missing_steps = max_consecutive_missing_steps
        self.default_mode = default_mode.lower()
        self.rolling_window_steps = rolling_window_steps
        self.min_history_steps = min_history_steps
        self.spatial_engine = spatial_engine

    def impute_missing_value(
        self,
        station_id: str,
        timestamp: Union[str, datetime, pd.Timestamp],
        target_variable: str,
        gap_duration_minutes: float,
        consecutive_missing_steps: int = 1,
        temporal_history: Optional[List[float]] = None,
        subsequent_history: Optional[List[float]] = None,
        neighbor_observations: Optional[Sequence[Dict[str, Any]]] = None,
        mode: Optional[str] = None,
        station_health_score: Optional[float] = None,
    ) -> ImputationRecord:
        """Attempt to impute a single missing sensor value.
        
        Args:
            station_id: Station identifier.
            timestamp: Timestamp of the missing observation.
            target_variable: Parameter name (e.g. 'temperature_c').
            gap_duration_minutes: Elapsed gap duration in minutes.
            consecutive_missing_steps: Number of consecutive missing packets.
            temporal_history: Prior valid readings for this station (in chronological order).
            subsequent_history: Subsequent future readings (used only in retrospective mode).
            neighbor_observations: Contemporaneous neighbor observations dicts.
            mode: Override operational mode ('causal' or 'retrospective').
            station_health_score: Optional sensor health score.
            
        Returns:
            Structured `ImputationRecord`.
        """
        op_mode = (mode or self.default_mode).lower()
        is_causal = op_mode == "causal"
        t_str = pd.to_datetime(timestamp, utc=True).isoformat()

        # 1. Gap-Length Safety Check
        if (
            gap_duration_minutes > self.max_interpolation_gap_minutes
            or consecutive_missing_steps > self.max_consecutive_missing_steps
        ):
            return ImputationRecord(
                station_id=station_id,
                timestamp=t_str,
                target_variable=target_variable,
                original_value=None,
                imputed_value=None,
                status=ImputationStatus.NOT_IMPUTABLE,
                method=EstimationMethod.NO_ESTIMATE,
                reason=(
                    f"Data gap ({gap_duration_minutes:.1f} min, {consecutive_missing_steps} steps) "
                    f"exceeds maximum allowed safety limit ({self.max_interpolation_gap_minutes:.1f} min)."
                ),
                gap_duration_minutes=gap_duration_minutes,
                consecutive_missing_steps=consecutive_missing_steps,
                uncertainty=None,
                is_causal=is_causal,
            )

        valid_history = [v for v in (temporal_history or []) if v is not None and not math.isnan(v)]
        valid_subsequent = [v for v in (subsequent_history or []) if v is not None and not math.isnan(v)]

        # Extract contemporaneous neighbor readings if spatial engine and neighbor pool available
        neighbor_vals: List[float] = []
        neighbor_dists: List[float] = []
        spatial_estimate: Optional[float] = None

        if self.spatial_engine and neighbor_observations:
            # Query spatial evidence for target
            target_vals_dummy = {target_variable: None}
            evidence = self.spatial_engine.evaluate_observation(
                target_station_id=station_id,
                target_timestamp=timestamp,
                target_values=target_vals_dummy,
                neighbor_data_pool=neighbor_observations,
            )
            # Find consensus for target variable
            var_consensus = None
            if "temp" in target_variable:
                var_consensus = evidence.temperature_consensus
            elif "humid" in target_variable or "rh" in target_variable:
                var_consensus = evidence.relative_humidity_consensus
            elif "press" in target_variable or "slp" in target_variable:
                var_consensus = evidence.sea_level_pressure_consensus

            if var_consensus and var_consensus.neighbor_count >= 1:
                if var_consensus.idw_expected_value is not None:
                    spatial_estimate = var_consensus.idw_expected_value
                elif var_consensus.neighbor_median is not None:
                    spatial_estimate = var_consensus.neighbor_median

            for detail in evidence.neighbor_details:
                if not detail.is_stale:
                    val = None
                    if "temp" in target_variable:
                        val = detail.temperature_c
                    elif "humid" in target_variable or "rh" in target_variable:
                        val = detail.relative_humidity_pct
                    elif "press" in target_variable or "slp" in target_variable:
                        val = detail.sea_level_pressure_hpa

                    if val is not None and not math.isnan(val):
                        neighbor_vals.append(val)
                        neighbor_dists.append(detail.distance_km)

        # 2. Strategy Selection based on Mode & Data Availability
        imputed_val: Optional[float] = None
        method_applied: EstimationMethod = EstimationMethod.NO_ESTIMATE
        rationale: str = ""

        # Strategy A: Retrospective Mode (Two-sided interpolation)
        if not is_causal and valid_history and valid_subsequent:
            last_past = valid_history[-1]
            first_future = valid_subsequent[0]
            # Linear interpolation weighted across step index
            imputed_val = 0.5 * (last_past + first_future)
            method_applied = EstimationMethod.RETROSPECTIVE_INTERPOLATION
            rationale = (
                f"Two-sided retrospective interpolation between past ({last_past:.2f}) "
                f"and future ({first_future:.2f})."
            )

        # Strategy B: Combined Temporal & Spatial (Best when both available)
        elif spatial_estimate is not None and len(valid_history) >= self.min_history_steps:
            temporal_recent = float(np.median(valid_history[-self.rolling_window_steps:]))
            imputed_val = 0.6 * spatial_estimate + 0.4 * temporal_recent
            method_applied = EstimationMethod.COMBINED_TEMPORAL_SPATIAL
            rationale = (
                f"Combined spatial IDW estimate ({spatial_estimate:.2f}) with "
                f"temporal rolling baseline ({temporal_recent:.2f})."
            )

        # Strategy C: Spatial IDW Consensus (When neighbors exist)
        elif spatial_estimate is not None:
            imputed_val = spatial_estimate
            method_applied = EstimationMethod.SPATIAL_IDW_CONSENSUS
            rationale = f"Spatial consensus estimate derived from {len(neighbor_vals)} active neighbors."

        # Strategy D: Causal Temporal Extrapolation / Trend
        elif len(valid_history) >= self.min_history_steps:
            recent_slice = valid_history[-self.min_history_steps:]
            # If rate is steady, apply small slope extrapolation clamped to reasonable delta
            if len(recent_slice) >= 3:
                slope = float((recent_slice[-1] - recent_slice[0]) / (len(recent_slice) - 1))
                # Dampen slope to avoid runaway extrapolation
                damped_slope = max(-1.0, min(1.0, slope * 0.5))
                imputed_val = float(recent_slice[-1] + damped_slope * consecutive_missing_steps)
            else:
                imputed_val = float(np.mean(recent_slice))

            method_applied = EstimationMethod.CAUSAL_TEMPORAL_INTERPOLATION
            rationale = f"Causal temporal extrapolation from preceding {len(recent_slice)} steps."

        # Strategy E: Fallback Rolling Baseline (Single or few points)
        elif len(valid_history) >= 1:
            imputed_val = float(np.mean(valid_history))
            method_applied = EstimationMethod.ROLLING_BASELINE
            rationale = f"Rolling mean baseline from {len(valid_history)} historical observations."

        # Strategy F: Insufficient Context
        else:
            return ImputationRecord(
                station_id=station_id,
                timestamp=t_str,
                target_variable=target_variable,
                original_value=None,
                imputed_value=None,
                status=ImputationStatus.NOT_IMPUTABLE,
                method=EstimationMethod.NO_ESTIMATE,
                reason="Insufficient local temporal history and zero available spatial neighbors.",
                gap_duration_minutes=gap_duration_minutes,
                consecutive_missing_steps=consecutive_missing_steps,
                uncertainty=None,
                is_causal=is_causal,
            )

        # Clamp imputed value to physical limits
        bounds = VARIABLE_BOUNDS.get(target_variable, (-1000.0, 1000.0))
        imputed_val = max(bounds[0], min(bounds[1], round(imputed_val, 3)))

        # 3. Compute Uncertainty
        unc = calculate_uncertainty(
            estimate=imputed_val,
            target_variable=target_variable,
            method=method_applied,
            observed_value=None,
            neighbor_values=neighbor_vals,
            neighbor_distances_km=neighbor_dists,
            temporal_history=valid_history,
            gap_minutes=gap_duration_minutes,
            station_health_score=station_health_score,
        )

        return ImputationRecord(
            station_id=station_id,
            timestamp=t_str,
            target_variable=target_variable,
            original_value=None,
            imputed_value=imputed_val,
            status=ImputationStatus.IMPUTED,
            method=method_applied,
            reason=rationale,
            gap_duration_minutes=gap_duration_minutes,
            consecutive_missing_steps=consecutive_missing_steps,
            uncertainty=unc,
            is_causal=is_causal,
        )

    def impute_series(
        self,
        station_id: str,
        timestamps: Sequence[Union[str, datetime, pd.Timestamp]],
        values: Sequence[Optional[float]],
        target_variable: str = "temperature_c",
        cadence_minutes: float = 5.0,
        neighbor_data_pool: Optional[Sequence[Dict[str, Any]]] = None,
        mode: Optional[str] = None,
    ) -> List[ImputationRecord]:
        """Impute all missing entries in a single station's time series sequence.
        
        Args:
            station_id: Target station ID.
            timestamps: Sequence of timestamps.
            values: Sequence of values (with NaNs or Nones for missing steps).
            target_variable: Variable name.
            cadence_minutes: Nominal step cadence in minutes.
            neighbor_data_pool: Optional multi-station pool for spatial assistance.
            mode: 'causal' or 'retrospective'.
            
        Returns:
            List of ImputationRecords for every missing timestamp encountered.
        """
        records: List[ImputationRecord] = []
        history: List[float] = []
        n_points = len(values)
        consecutive_missing = 0

        for i in range(n_points):
            v = values[i]
            t = timestamps[i]
            is_missing = v is None or (isinstance(v, float) and (math.isnan(v) or math.isinf(v)))

            if is_missing:
                consecutive_missing += 1
                gap_min = consecutive_missing * cadence_minutes
                
                subsequent: List[float] = []
                # In retrospective mode, look ahead to collect valid future points
                for j in range(i + 1, n_points):
                    fut_v = values[j]
                    if fut_v is not None and not (isinstance(fut_v, float) and math.isnan(fut_v)):
                        subsequent.append(fut_v)
                        if len(subsequent) >= 3:
                            break

                rec = self.impute_missing_value(
                    station_id=station_id,
                    timestamp=t,
                    target_variable=target_variable,
                    gap_duration_minutes=gap_min,
                    consecutive_missing_steps=consecutive_missing,
                    temporal_history=list(history),
                    subsequent_history=subsequent,
                    neighbor_observations=neighbor_data_pool,
                    mode=mode,
                )
                records.append(rec)
                # If successfully imputed, feed imputed value into causal history buffer for subsequent steps
                if rec.status == ImputationStatus.IMPUTED and rec.imputed_value is not None:
                    history.append(rec.imputed_value)
            else:
                consecutive_missing = 0
                history.append(float(v))

        return records
