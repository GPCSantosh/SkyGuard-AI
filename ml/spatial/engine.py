"""Spatial & Synoptic Context Engine for SkyGuard AI AWS networks."""

from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union
import numpy as np
import pandas as pd

from backend.app.core.meteorology import station_to_sea_level_pressure
from ml.spatial.schema import (
    NeighborObservationRecord,
    SpatialContextCategory,
    SpatialContextEvidence,
    VariableConsensus,
)
from ml.spatial.topology import SpatialNetworkTopology, haversine_distance_km


class SpatialContextEngine:
    """Evaluates spatial neighborhood consistency and synoptic context for weather observations.
    
    Adheres strictly to causal operation (no future data leakage in real-time mode),
    geodesic topology, barometric sea-level pressure normalization, and transparent
    contextual evidence generation.
    """

    def __init__(
        self,
        topology: Optional[SpatialNetworkTopology] = None,
        max_distance_km: float = 600.0,
        max_neighbors: int = 5,
        temporal_tolerance_minutes: float = 30.0,
        enable_causal_mode: bool = True,
        min_valid_neighbors: int = 2,
        temp_tolerance_c: float = 1.0,
        rh_tolerance_pct: float = 5.0,
        slp_tolerance_hpa: float = 1.5,
        temp_trend_tolerance_c: float = 0.3,
        rh_trend_tolerance_pct: float = 1.5,
        slp_trend_tolerance_hpa: float = 0.4,
        idw_power: float = 1.0,
    ) -> None:
        """Initialize the Spatial Context Engine.
        
        Args:
            topology: Station network topology graph with coordinates and elevations.
            max_distance_km: Maximum radius in km to consider candidate neighbors.
            max_neighbors: Maximum number of nearest neighbors to query.
            temporal_tolerance_minutes: Max time difference for neighbor observations.
            enable_causal_mode: If True, strictly excludes any neighbor observation where t > target_t.
            min_valid_neighbors: Minimum active neighbors required for robust regional classification.
            temp_tolerance_c: Absolute tolerance for temperature similarity (°C).
            rh_tolerance_pct: Absolute tolerance for relative humidity similarity (%).
            slp_tolerance_hpa: Absolute tolerance for sea-level pressure similarity (hPa).
            temp_trend_tolerance_c: Rate-of-change threshold for temperature trend detection (°C).
            rh_trend_tolerance_pct: Rate-of-change threshold for RH trend detection (%).
            slp_trend_tolerance_hpa: Rate-of-change threshold for SLP trend detection (hPa).
            idw_power: Distance exponent for Inverse Distance Weighting (IDW).
        """
        self.topology = topology or SpatialNetworkTopology()
        self.max_distance_km = max_distance_km
        self.max_neighbors = max_neighbors
        self.temporal_tolerance_minutes = temporal_tolerance_minutes
        self.enable_causal_mode = enable_causal_mode
        self.min_valid_neighbors = min_valid_neighbors
        self.temp_tolerance_c = temp_tolerance_c
        self.rh_tolerance_pct = rh_tolerance_pct
        self.slp_tolerance_hpa = slp_tolerance_hpa
        self.temp_trend_tolerance_c = temp_trend_tolerance_c
        self.rh_trend_tolerance_pct = rh_trend_tolerance_pct
        self.slp_trend_tolerance_hpa = slp_trend_tolerance_hpa
        self.idw_power = idw_power

    def _normalize_slp(
        self,
        slp: Optional[float],
        stn_p: Optional[float],
        elev_m: Optional[float],
        temp_c: Optional[float],
    ) -> Optional[float]:
        """Ensure sea-level pressure is populated, converting station pressure if necessary."""
        if slp is not None and not (isinstance(slp, float) and math.isnan(slp)):
            return float(slp)
        if stn_p is not None and elev_m is not None and temp_c is not None:
            if not (math.isnan(stn_p) or math.isnan(elev_m) or math.isnan(temp_c)):
                derived = station_to_sea_level_pressure(stn_p, elev_m, temp_c)
                if derived is not None and not math.isnan(derived):
                    return float(derived)
        return None

    def _compute_variable_consensus(
        self,
        var_name: str,
        target_val: Optional[float],
        target_delta: Optional[float],
        neighbor_vals: List[float],
        neighbor_deltas: List[float],
        neighbor_distances: List[float],
        tolerance: float,
        trend_tolerance: float,
    ) -> VariableConsensus:
        """Compute statistical consensus, distribution metrics, and IDW for a single parameter."""
        # Filter out NaNs
        valid_pairs = [
            (v, d, dist)
            for v, d, dist in zip(neighbor_vals, neighbor_deltas, neighbor_distances)
            if v is not None and not math.isnan(v)
        ]

        if not valid_pairs:
            return VariableConsensus(
                variable_name=var_name,
                target_value=target_val,
                target_delta_prev=target_delta,
                neighbor_count=0,
            )

        vals = [p[0] for p in valid_pairs]
        deltas = [p[1] for p in valid_pairs if p[1] is not None and not math.isnan(p[1])]
        dists = [p[2] for p in valid_pairs]
        n_count = len(vals)

        n_mean = float(np.mean(vals))
        n_med = float(np.median(vals))
        n_std = float(np.std(vals, ddof=1)) if n_count > 1 else 0.0
        n_min = float(np.min(vals))
        n_max = float(np.max(vals))

        target_minus_mean: Optional[float] = None
        target_minus_med: Optional[float] = None
        target_zscore: Optional[float] = None

        frac_higher = 0.0
        frac_lower = 0.0
        frac_similar = 0.0

        if target_val is not None and not math.isnan(target_val):
            target_minus_mean = target_val - n_mean
            target_minus_med = target_val - n_med
            
            # Safe zscore calculation with variance floor
            if n_std > 1e-4:
                target_zscore = float(target_minus_mean / n_std)
            else:
                # When all neighbors have identical readings
                if abs(target_minus_mean) <= tolerance:
                    target_zscore = 0.0
                else:
                    # Scaled by tolerance as proxy standard deviation
                    target_zscore = float(target_minus_mean / max(tolerance, 0.1))

            higher_cnt = sum(1 for v in vals if v > target_val + tolerance)
            lower_cnt = sum(1 for v in vals if v < target_val - tolerance)
            sim_cnt = sum(1 for v in vals if abs(v - target_val) <= tolerance)

            frac_higher = higher_cnt / n_count
            frac_lower = lower_cnt / n_count
            frac_similar = sim_cnt / n_count

        # Trend / Change consensus
        frac_inc = 0.0
        frac_dec = 0.0
        frac_stab = 0.0
        dir_agreement: Optional[float] = None

        if deltas:
            n_deltas_count = len(deltas)
            inc_cnt = sum(1 for d in deltas if d > trend_tolerance)
            dec_cnt = sum(1 for d in deltas if d < -trend_tolerance)
            stab_cnt = sum(1 for d in deltas if abs(d) <= trend_tolerance)

            frac_inc = inc_cnt / n_deltas_count
            frac_dec = dec_cnt / n_deltas_count
            frac_stab = stab_cnt / n_deltas_count

            if target_delta is not None and not math.isnan(target_delta):
                if target_delta > trend_tolerance:
                    # Target is rising: agreement is fraction of neighbors rising minus fraction falling
                    dir_agreement = frac_inc - frac_dec
                elif target_delta < -trend_tolerance:
                    # Target is falling: agreement is fraction of neighbors falling minus fraction rising
                    dir_agreement = frac_dec - frac_inc
                else:
                    # Target is stable: agreement is fraction of neighbors stable
                    dir_agreement = frac_stab - (frac_inc + frac_dec)
                dir_agreement = max(-1.0, min(1.0, dir_agreement))

        # Inverse Distance Weighting (IDW)
        idw_expected: Optional[float] = None
        target_minus_idw: Optional[float] = None

        if dists and vals:
            weights = [1.0 / (max(d, 1.0) ** self.idw_power) for d in dists]
            total_w = sum(weights)
            if total_w > 0:
                idw_expected = float(sum(w * v for w, v in zip(weights, vals)) / total_w)
                if target_val is not None and not math.isnan(target_val):
                    target_minus_idw = target_val - idw_expected

        return VariableConsensus(
            variable_name=var_name,
            target_value=target_val,
            target_delta_prev=target_delta,
            neighbor_count=n_count,
            neighbor_mean=n_mean,
            neighbor_median=n_med,
            neighbor_std=n_std,
            neighbor_min=n_min,
            neighbor_max=n_max,
            target_minus_mean=target_minus_mean,
            target_minus_median=target_minus_med,
            target_zscore=target_zscore,
            fraction_higher=frac_higher,
            fraction_lower=frac_lower,
            fraction_similar=frac_similar,
            fraction_increasing=frac_inc,
            fraction_decreasing=frac_dec,
            fraction_stable=frac_stab,
            directional_agreement=dir_agreement,
            idw_expected_value=idw_expected,
            target_minus_idw=target_minus_idw,
        )

    def evaluate_observation(
        self,
        target_station_id: str,
        target_timestamp: Union[str, datetime, pd.Timestamp],
        target_values: Dict[str, Optional[float]],
        neighbor_data_pool: Sequence[Dict[str, Any]],
        target_deltas: Optional[Dict[str, Optional[float]]] = None,
    ) -> SpatialContextEvidence:
        """Evaluate spatial context evidence for a single target observation against neighbor observations.
        
        Args:
            target_station_id: Station ID of the observation.
            target_timestamp: Timestamp of the observation.
            target_values: Dict with keys ('temperature_c', 'relative_humidity_pct', 'sea_level_pressure_hpa',
                           and optionally 'station_pressure_hpa', 'elevation_m').
            neighbor_data_pool: List or Sequence of neighbor observation dictionaries.
            target_deltas: Optional Dict with rate-of-change deltas vs prior timestep.
            
        Returns:
            Structured `SpatialContextEvidence` record.
        """
        # Parse timestamp to UTC datetime
        t_target = pd.to_datetime(target_timestamp, utc=True)
        t_target_str = t_target.isoformat()

        target_node = self.topology.stations.get(target_station_id)
        target_elev = target_node.elevation_m if target_node else target_values.get("elevation_m")

        # Normalize target SLP if necessary
        target_t = target_values.get("temperature_c")
        target_rh = target_values.get("relative_humidity_pct")
        target_slp = self._normalize_slp(
            target_values.get("sea_level_pressure_hpa"),
            target_values.get("station_pressure_hpa"),
            target_elev,
            target_t,
        )

        deltas_dict = target_deltas or {}
        target_t_delta = deltas_dict.get("temperature_c")
        target_rh_delta = deltas_dict.get("relative_humidity_pct")
        target_slp_delta = deltas_dict.get("sea_level_pressure_hpa")

        # Query configured neighbors from topology
        configured_links = self.topology.get_neighbors(
            target_station_id=target_station_id,
            max_distance_km=self.max_distance_km,
            max_neighbors=self.max_neighbors,
        )
        configured_count = len(configured_links)

        if configured_count == 0:
            return SpatialContextEvidence(
                target_station_id=target_station_id,
                timestamp=t_target_str,
                target_elevation_m=target_elev,
                configured_neighbors_count=0,
                valid_neighbors_count=0,
                stale_neighbors_count=0,
                context_category=SpatialContextCategory.INSUFFICIENT_CONTEXT,
                temporal_tolerance_minutes=self.temporal_tolerance_minutes,
                max_distance_km=self.max_distance_km,
                is_causal=self.enable_causal_mode,
                evidence_notes=["Zero configured neighbors within spatial radius."],
            )

        # Index neighbor candidate data
        # Structure: neighbor_id -> list of records
        neighbor_records_by_stn: Dict[str, List[Dict[str, Any]]] = {}
        for rec in neighbor_data_pool:
            s_id = str(rec.get("station_id", ""))
            if s_id and s_id != target_station_id:
                neighbor_records_by_stn.setdefault(s_id, []).append(rec)

        eval_neighbor_records: List[NeighborObservationRecord] = []
        valid_t_vals: List[float] = []
        valid_rh_vals: List[float] = []
        valid_slp_vals: List[float] = []
        
        valid_t_deltas: List[float] = []
        valid_rh_deltas: List[float] = []
        valid_slp_deltas: List[float] = []
        
        valid_dists: List[float] = []
        stale_count = 0

        tolerance_sec = self.temporal_tolerance_minutes * 60.0

        for link in configured_links:
            n_id = link.neighbor_station_id
            candidates = neighbor_records_by_stn.get(n_id, [])
            if not candidates:
                continue

            # Filter candidates by time alignment & causality
            valid_candidates = []
            for c in candidates:
                c_time = pd.to_datetime(c["timestamp"], utc=True)
                dt_sec = (c_time - t_target).total_seconds()

                if self.enable_causal_mode and dt_sec > 0:
                    # Strict causal rule: future observations ignored
                    continue

                abs_dt = abs(dt_sec)
                valid_candidates.append((c, c_time, dt_sec, abs_dt))

            if not valid_candidates:
                continue

            # Select the observation with the smallest absolute time delta
            # In causal mode where dt_sec <= 0, smallest abs_dt is the latest observation <= T
            valid_candidates.sort(key=lambda x: x[3])
            best_cand, best_time, dt_sec, abs_dt = valid_candidates[0]

            is_stale = abs_dt > tolerance_sec
            if is_stale:
                stale_count += 1

            n_t = best_cand.get("temperature_c")
            n_rh = best_cand.get("relative_humidity_pct")
            n_node = self.topology.stations.get(n_id)
            n_elev = n_node.elevation_m if n_node else best_cand.get("elevation_m")
            n_slp = self._normalize_slp(
                best_cand.get("sea_level_pressure_hpa"),
                best_cand.get("station_pressure_hpa"),
                n_elev,
                n_t,
            )

            rec = NeighborObservationRecord(
                station_id=n_id,
                timestamp=best_time.isoformat(),
                distance_km=link.distance_km,
                bearing_deg=link.bearing_deg,
                elevation_diff_m=link.elevation_diff_m,
                time_delta_seconds=dt_sec,
                temperature_c=float(n_t) if n_t is not None and not pd.isna(n_t) else None,
                relative_humidity_pct=float(n_rh) if n_rh is not None and not pd.isna(n_rh) else None,
                sea_level_pressure_hpa=float(n_slp) if n_slp is not None and not pd.isna(n_slp) else None,
                is_stale=is_stale,
            )
            eval_neighbor_records.append(rec)

            has_valid_measurements = any(
                v is not None and not (isinstance(v, float) and math.isnan(v))
                for v in (rec.temperature_c, rec.relative_humidity_pct, rec.sea_level_pressure_hpa)
            )

            if not is_stale and has_valid_measurements:
                valid_dists.append(link.distance_km)
                if rec.temperature_c is not None and not math.isnan(rec.temperature_c):
                    valid_t_vals.append(rec.temperature_c)
                    n_dt = best_cand.get("delta_temperature_c", best_cand.get("temperature_delta"))
                    if n_dt is not None and not pd.isna(n_dt):
                        valid_t_deltas.append(float(n_dt))
                    else:
                        valid_t_deltas.append(float("nan"))

                if rec.relative_humidity_pct is not None and not math.isnan(rec.relative_humidity_pct):
                    valid_rh_vals.append(rec.relative_humidity_pct)
                    n_drh = best_cand.get("delta_relative_humidity_pct", best_cand.get("rh_delta"))
                    if n_drh is not None and not pd.isna(n_drh):
                        valid_rh_deltas.append(float(n_drh))
                    else:
                        valid_rh_deltas.append(float("nan"))

                if rec.sea_level_pressure_hpa is not None and not math.isnan(rec.sea_level_pressure_hpa):
                    valid_slp_vals.append(rec.sea_level_pressure_hpa)
                    n_dslp = best_cand.get("delta_sea_level_pressure_hpa", best_cand.get("slp_delta"))
                    if n_dslp is not None and not pd.isna(n_dslp):
                        valid_slp_deltas.append(float(n_dslp))
                    else:
                        valid_slp_deltas.append(float("nan"))

        valid_count = len(valid_dists)

        # Compute Consensus Per Variable
        t_cons = self._compute_variable_consensus(
            "temperature_c",
            target_t,
            target_t_delta,
            valid_t_vals,
            valid_t_deltas,
            valid_dists,
            self.temp_tolerance_c,
            self.temp_trend_tolerance_c,
        )

        rh_cons = self._compute_variable_consensus(
            "relative_humidity_pct",
            target_rh,
            target_rh_delta,
            valid_rh_vals,
            valid_rh_deltas,
            valid_dists,
            self.rh_tolerance_pct,
            self.rh_trend_tolerance_pct,
        )

        slp_cons = self._compute_variable_consensus(
            "sea_level_pressure_hpa",
            target_slp,
            target_slp_delta,
            valid_slp_vals,
            valid_slp_deltas,
            valid_dists,
            self.slp_tolerance_hpa,
            self.slp_trend_tolerance_hpa,
        )

        # Cross-Variable Multi-Sensor Coherence Index
        # Combines similarity and trend agreement across active variables
        coherence_scores: List[float] = []
        for cons in (t_cons, rh_cons, slp_cons):
            if cons.neighbor_count > 0 and cons.target_value is not None:
                # Metric 1: Fraction similar in level
                sim_score = cons.fraction_similar
                # Metric 2: Directional trend agreement mapped from [-1, 1] to [0, 1]
                trend_score = 0.5
                if cons.directional_agreement is not None:
                    trend_score = (cons.directional_agreement + 1.0) / 2.0
                
                # Combined variable coherence score
                var_score = 0.6 * sim_score + 0.4 * trend_score
                coherence_scores.append(var_score)

        cross_var_coherence = float(np.mean(coherence_scores)) if coherence_scores else 0.0

        # Context Classification Logic
        notes: List[str] = []
        category = SpatialContextCategory.INSUFFICIENT_CONTEXT

        if valid_count < self.min_valid_neighbors:
            category = SpatialContextCategory.INSUFFICIENT_CONTEXT
            notes.append(f"Insufficient active neighbors ({valid_count}/{self.min_valid_neighbors} required).")
        else:
            # Check for significant anomaly/departure on target vs neighbors
            # A departure exists if target is not similar to majority AND deviates from neighbor median
            t_departure = (
                t_cons.fraction_similar < 0.5
                and (abs(t_cons.target_zscore or 0.0) >= 2.2 or abs(t_cons.target_minus_median or 0.0) > 2.0 * self.temp_tolerance_c)
            )
            rh_departure = (
                rh_cons.fraction_similar < 0.5
                and (abs(rh_cons.target_zscore or 0.0) >= 2.2 or abs(rh_cons.target_minus_median or 0.0) > 2.0 * self.rh_tolerance_pct)
            )
            slp_departure = (
                slp_cons.fraction_similar < 0.5
                and (abs(slp_cons.target_zscore or 0.0) >= 2.2 or abs(slp_cons.target_minus_median or 0.0) > 2.0 * self.slp_tolerance_hpa)
            )

            has_departure = t_departure or rh_departure or slp_departure

            # Average trend agreement across variables where directional agreement is present
            agreements = [c.directional_agreement for c in (t_cons, rh_cons, slp_cons) if c.directional_agreement is not None]
            avg_agreement = float(np.mean(agreements)) if agreements else 0.0

            if not has_departure:
                # Target is in close agreement with neighbors across all active variables
                category = SpatialContextCategory.REGIONAL_PATTERN
                notes.append("Target reading aligns with regional background conditions.")
            else:
                # Target exhibits departure on one or more variables.
                # Check whether each departing variable is corroborated by its spatial neighborhood.
                corroborated_departures: List[str] = []
                uncorroborated_departures: List[str] = []

                for is_dep, cons, trend_tol in [
                    (t_departure, t_cons, self.temp_trend_tolerance_c),
                    (rh_departure, rh_cons, self.rh_trend_tolerance_pct),
                    (slp_departure, slp_cons, self.slp_trend_tolerance_hpa),
                ]:
                    if is_dep:
                        # Corroborated if either majority is similar in absolute level (value-level consensus),
                        # OR target is undergoing an event-scale rate-of-change corroborated by neighboring trends.
                        target_event_scale_change = (
                            cons.target_delta_prev is not None
                            and not math.isnan(cons.target_delta_prev)
                            and abs(cons.target_delta_prev) >= 2.5 * trend_tol
                        )
                        is_corr = (
                            cons.fraction_similar >= 0.5
                            or (
                                target_event_scale_change
                                and cons.directional_agreement is not None
                                and cons.directional_agreement >= 0.5
                            )
                        )
                        if is_corr:
                            corroborated_departures.append(cons.variable_name)
                        else:
                            uncorroborated_departures.append(cons.variable_name)

                if corroborated_departures and not uncorroborated_departures:
                    category = SpatialContextCategory.REGIONAL_PATTERN
                    notes.append(f"Regional agreement confirms coherent event in: {', '.join(corroborated_departures)}.")
                else:
                    # Check nearest neighbor for local cluster
                    valid_neighbor_records = [r for r in eval_neighbor_records if not r.is_stale and r.temperature_c is not None]
                    nearest_record = valid_neighbor_records[0] if valid_neighbor_records else None
                    if nearest_record:
                        n_t_near = nearest_record.temperature_c
                        if n_t_near is not None and target_t is not None and abs(target_t - n_t_near) <= self.temp_tolerance_c * 1.5:
                            category = SpatialContextCategory.LOCAL_CLUSTER
                            notes.append("Nearest neighbor corroborates departure, but wider network differs.")
                        else:
                            category = SpatialContextCategory.LOCAL_ONLY
                            notes.append(f"Target departure locally isolated in: {', '.join(uncorroborated_departures)}.")
                    else:
                        category = SpatialContextCategory.LOCAL_ONLY
                        notes.append(f"Target departure uncorroborated in: {', '.join(uncorroborated_departures)}.")

        return SpatialContextEvidence(
            target_station_id=target_station_id,
            timestamp=t_target_str,
            target_elevation_m=target_elev,
            configured_neighbors_count=configured_count,
            valid_neighbors_count=valid_count,
            stale_neighbors_count=stale_count,
            temperature_consensus=t_cons,
            relative_humidity_consensus=rh_cons,
            sea_level_pressure_consensus=slp_cons,
            cross_variable_coherence=cross_var_coherence,
            context_category=category,
            temporal_tolerance_minutes=self.temporal_tolerance_minutes,
            max_distance_km=self.max_distance_km,
            is_causal=self.enable_causal_mode,
            neighbor_details=eval_neighbor_records,
            evidence_notes=notes,
        )

    def extract_features_multi_station(
        self,
        df: pd.DataFrame,
        timestamp_col: str = "timestamp",
        station_id_col: str = "station_id",
    ) -> pd.DataFrame:
        """Vectorized/batch feature extraction across a multi-station DataFrame.
        
        Appends spatial statistics, neighbor deltas, consensus ratios, and context categories.
        
        Args:
            df: Multi-station observations DataFrame.
            timestamp_col: Name of the timestamp column.
            station_id_col: Name of the station ID column.
            
        Returns:
            DataFrame enriched with spatial context features.
        """
        if df.empty:
            return df.copy()

        result = df.copy()
        result[timestamp_col] = pd.to_datetime(result[timestamp_col], utc=True)
        result = result.sort_values(timestamp_col)

        # Ensure topology is initialized
        if not self.topology.stations:
            self.topology = SpatialNetworkTopology.from_dataframe(result, station_id_col=station_id_col)

        # Precompute SLP if missing
        if "sea_level_pressure_hpa" not in result.columns:
            result["sea_level_pressure_hpa"] = np.nan

        if "station_pressure_hpa" in result.columns:
            mask_slp = result["sea_level_pressure_hpa"].isna() & result["station_pressure_hpa"].notna()
            if mask_slp.any() and "elevation_m" in result.columns and "temperature_c" in result.columns:
                for idx in result[mask_slp].index:
                    p_stn = result.at[idx, "station_pressure_hpa"]
                    elev = result.at[idx, "elevation_m"]
                    temp = result.at[idx, "temperature_c"]
                    derived = station_to_sea_level_pressure(p_stn, elev, temp)
                    if derived is not None:
                        result.at[idx, "sea_level_pressure_hpa"] = derived

        # Precompute deltas per station if not present
        for col, dcol in [
            ("temperature_c", "delta_temperature_c"),
            ("relative_humidity_pct", "delta_relative_humidity_pct"),
            ("sea_level_pressure_hpa", "delta_sea_level_pressure_hpa"),
        ]:
            if col in result.columns and dcol not in result.columns:
                result[dcol] = result.groupby(station_id_col)[col].diff()

        # Allocate feature columns
        spatial_cols = [
            "spatial_neighbor_count",
            "spatial_valid_neighbor_count",
            "spatial_nearest_dist_km",
            "spatial_neighbor_temp_mean",
            "spatial_neighbor_temp_std",
            "spatial_temp_delta_from_neighbor_mean",
            "spatial_temp_zscore_vs_neighbors",
            "spatial_temp_frac_similar",
            "spatial_temp_idw_expected",
            "spatial_neighbor_rh_mean",
            "spatial_neighbor_rh_std",
            "spatial_rh_delta_from_neighbor_mean",
            "spatial_rh_zscore_vs_neighbors",
            "spatial_rh_frac_similar",
            "spatial_rh_idw_expected",
            "spatial_neighbor_slp_mean",
            "spatial_neighbor_slp_std",
            "spatial_slp_delta_from_neighbor_mean",
            "spatial_slp_zscore_vs_neighbors",
            "spatial_slp_frac_similar",
            "spatial_slp_idw_expected",
            "spatial_cross_var_coherence",
            "spatial_context_category",
        ]
        for col in spatial_cols:
            result[col] = np.nan if col != "spatial_context_category" else "INSUFFICIENT_CONTEXT"

        # Round timestamps into time buckets for efficient neighbor candidate pooling
        bucket_size = f"{int(max(1.0, self.temporal_tolerance_minutes))}min"
        result["_time_bucket"] = result[timestamp_col].dt.round(bucket_size)

        # Group by time bucket
        for bucket, grp in result.groupby("_time_bucket"):
            pool = grp.to_dict(orient="records")
            for idx, row in grp.iterrows():
                stn = str(row[station_id_col])
                t_val = row.get("temperature_c")
                rh_val = row.get("relative_humidity_pct")
                slp_val = row.get("sea_level_pressure_hpa")
                stn_p_val = row.get("station_pressure_hpa")
                elev_val = row.get("elevation_m")

                t_dict = {
                    "temperature_c": float(t_val) if pd.notna(t_val) else None,
                    "relative_humidity_pct": float(rh_val) if pd.notna(rh_val) else None,
                    "sea_level_pressure_hpa": float(slp_val) if pd.notna(slp_val) else None,
                    "station_pressure_hpa": float(stn_p_val) if pd.notna(stn_p_val) else None,
                    "elevation_m": float(elev_val) if pd.notna(elev_val) else None,
                }
                d_dict = {
                    "temperature_c": float(row.get("delta_temperature_c")) if pd.notna(row.get("delta_temperature_c")) else None,
                    "relative_humidity_pct": float(row.get("delta_relative_humidity_pct")) if pd.notna(row.get("delta_relative_humidity_pct")) else None,
                    "sea_level_pressure_hpa": float(row.get("delta_sea_level_pressure_hpa")) if pd.notna(row.get("delta_sea_level_pressure_hpa")) else None,
                }

                evidence = self.evaluate_observation(
                    target_station_id=stn,
                    target_timestamp=row[timestamp_col],
                    target_values=t_dict,
                    neighbor_data_pool=pool,
                    target_deltas=d_dict,
                )

                result.at[idx, "spatial_neighbor_count"] = evidence.configured_neighbors_count
                result.at[idx, "spatial_valid_neighbor_count"] = evidence.valid_neighbors_count
                if evidence.neighbor_details:
                    result.at[idx, "spatial_nearest_dist_km"] = evidence.neighbor_details[0].distance_km

                if evidence.temperature_consensus:
                    tc = evidence.temperature_consensus
                    result.at[idx, "spatial_neighbor_temp_mean"] = tc.neighbor_mean
                    result.at[idx, "spatial_neighbor_temp_std"] = tc.neighbor_std
                    result.at[idx, "spatial_temp_delta_from_neighbor_mean"] = tc.target_minus_mean
                    result.at[idx, "spatial_temp_zscore_vs_neighbors"] = tc.target_zscore
                    result.at[idx, "spatial_temp_frac_similar"] = tc.fraction_similar
                    result.at[idx, "spatial_temp_idw_expected"] = tc.idw_expected_value

                if evidence.relative_humidity_consensus:
                    rhc = evidence.relative_humidity_consensus
                    result.at[idx, "spatial_neighbor_rh_mean"] = rhc.neighbor_mean
                    result.at[idx, "spatial_neighbor_rh_std"] = rhc.neighbor_std
                    result.at[idx, "spatial_rh_delta_from_neighbor_mean"] = rhc.target_minus_mean
                    result.at[idx, "spatial_rh_zscore_vs_neighbors"] = rhc.target_zscore
                    result.at[idx, "spatial_rh_frac_similar"] = rhc.fraction_similar
                    result.at[idx, "spatial_rh_idw_expected"] = rhc.idw_expected_value

                if evidence.sea_level_pressure_consensus:
                    slpc = evidence.sea_level_pressure_consensus
                    result.at[idx, "spatial_neighbor_slp_mean"] = slpc.neighbor_mean
                    result.at[idx, "spatial_neighbor_slp_std"] = slpc.neighbor_std
                    result.at[idx, "spatial_slp_delta_from_neighbor_mean"] = slpc.target_minus_mean
                    result.at[idx, "spatial_slp_zscore_vs_neighbors"] = slpc.target_zscore
                    result.at[idx, "spatial_slp_frac_similar"] = slpc.fraction_similar
                    result.at[idx, "spatial_slp_idw_expected"] = slpc.idw_expected_value

                result.at[idx, "spatial_cross_var_coherence"] = evidence.cross_variable_coherence
                result.at[idx, "spatial_context_category"] = evidence.context_category.value

        result = result.drop(columns=["_time_bucket"])
        return result
