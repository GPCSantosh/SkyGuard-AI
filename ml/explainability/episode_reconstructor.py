"""Anomaly episode timeline reconstruction for SkyGuard AI."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Union
import numpy as np
import pandas as pd

from ml.explainability.schema import AnomalyEpisode


class AnomalyEpisodeReconstructor:
    """Reconstructs anomaly episode lifecycle: baseline -> onset -> peak -> recovery."""

    def __init__(
        self,
        default_preceding_steps: int = 5,
        default_following_steps: int = 5,
    ) -> None:
        """Initialize Episode Reconstructor.
        
        Args:
            default_preceding_steps: Number of normal steps before onset to capture.
            default_following_steps: Number of recovery steps to capture.
        """
        self.preceding_steps = default_preceding_steps
        self.following_steps = default_following_steps

    def reconstruct_episode(
        self,
        station_id: str,
        event_timestamp: str,
        history_df: pd.DataFrame,
        target_variable: str = "temperature_c",
        score_column: str = "normalized_anomaly_score",
        decision_column: str = "decision",
        neighbor_df: Optional[pd.DataFrame] = None,
    ) -> AnomalyEpisode:
        """Reconstruct the lifecycle of an anomaly event from chronological station history.
        
        Args:
            station_id: Station identifier.
            event_timestamp: ISO timestamp of anomalous observation.
            history_df: Chronological observation DataFrame for the station.
            target_variable: Primary variable under investigation.
            score_column: Column name for continuous anomaly score.
            decision_column: Column name for decision string or enum.
            neighbor_df: Optional DataFrame of concurrent neighboring station records.
            
        Returns:
            `AnomalyEpisode` container with onset, peak, duration, and slice records.
        """
        if history_df.empty:
            return AnomalyEpisode(
                station_id=station_id,
                target_variable=target_variable,
                onset_timestamp=event_timestamp,
                peak_timestamp=event_timestamp,
                recovery_timestamp=None,
                duration_minutes=0.0,
                peak_value=None,
                peak_anomaly_score=None,
            )

        df = history_df.copy()
        if "station_id" in df.columns:
            df = df[df["station_id"] == station_id].copy()

        df["dt"] = pd.to_datetime(df["timestamp"])
        df = df.sort_values("dt").reset_index(drop=True)

        target_dt = pd.to_datetime(event_timestamp)
        matches = df[df["dt"] == target_dt]
        if not matches.empty:
            event_idx = matches.index[0]
        else:
            # Closest preceding or nearest
            diffs = (df["dt"] - target_dt).abs()
            event_idx = diffs.idxmin()

        # Determine anomaly condition per step: score >= 0.5 or decision != 'NORMAL' or flag
        is_anom = np.zeros(len(df), dtype=bool)
        if score_column in df.columns:
            is_anom |= (df[score_column] >= 0.5)
        if decision_column in df.columns:
            is_anom |= (df[decision_column].astype(str) != "NORMAL")
        if "is_anomaly" in df.columns:
            is_anom |= (df["is_anomaly"] == 1)

        # If no explicit column found, treat event_idx as anomalous
        is_anom[event_idx] = True

        # 1. Trace onset backward
        onset_idx = event_idx
        while onset_idx > 0 and is_anom[onset_idx - 1]:
            onset_idx -= 1

        # 2. Trace recovery forward
        recovery_idx = event_idx
        while recovery_idx < len(df) - 1 and is_anom[recovery_idx]:
            recovery_idx += 1

        # Check if actually recovered or ongoing
        recovered = not is_anom[recovery_idx]
        actual_recovery_timestamp = str(df.iloc[recovery_idx]["timestamp"]) if recovered else None

        onset_timestamp = str(df.iloc[onset_idx]["timestamp"])
        onset_dt = df.iloc[onset_idx]["dt"]
        end_dt = df.iloc[recovery_idx]["dt"] if recovered else df.iloc[-1]["dt"]
        duration_min = max(0.0, float((end_dt - onset_dt).total_seconds() / 60.0))

        # 3. Identify Peak
        episode_slice = df.iloc[onset_idx : (recovery_idx + 1 if recovered else len(df))].copy()
        if score_column in episode_slice.columns and not episode_slice[score_column].isna().all():
            peak_sub_idx = episode_slice[score_column].idxmax()
        elif target_variable in episode_slice.columns:
            # Maximum deviation from pre-onset baseline
            baseline_val = df.iloc[max(0, onset_idx - 1)][target_variable] if onset_idx > 0 and target_variable in df.columns else 0.0
            peak_sub_idx = (episode_slice[target_variable] - baseline_val).abs().idxmax()
        else:
            peak_sub_idx = event_idx

        peak_row = df.loc[peak_sub_idx]
        peak_timestamp = str(peak_row["timestamp"])
        peak_val = float(peak_row[target_variable]) if target_variable in peak_row and pd.notna(peak_row[target_variable]) else None
        peak_score = float(peak_row[score_column]) if score_column in peak_row and pd.notna(peak_row[score_column]) else None

        # 4. Slices for timeline view
        prec_start = max(0, onset_idx - self.preceding_steps)
        preceding_obs = self._records_to_dict_list(df.iloc[prec_start:onset_idx], target_variable, score_column)

        ep_end = recovery_idx if recovered else len(df)
        episode_obs = self._records_to_dict_list(df.iloc[onset_idx:ep_end], target_variable, score_column)

        rec_end = min(len(df), recovery_idx + self.following_steps) if recovered else len(df)
        recovering_obs = self._records_to_dict_list(df.iloc[recovery_idx:rec_end], target_variable, score_column) if recovered else []

        # 5. Neighbor context during episode
        neighbor_summary: Dict[str, Any] = {}
        if neighbor_df is not None and not neighbor_df.empty and "timestamp" in neighbor_df.columns:
            ndf = neighbor_df.copy()
            ndf["dt"] = pd.to_datetime(ndf["timestamp"])
            ep_ndf = ndf[(ndf["dt"] >= onset_dt) & (ndf["dt"] <= end_dt)]
            if not ep_ndf.empty and target_variable in ep_ndf.columns:
                n_valid = ep_ndf[target_variable].dropna()
                neighbor_summary = {
                    "neighbor_station_count": int(ep_ndf["station_id"].nunique()) if "station_id" in ep_ndf.columns else 0,
                    "neighbor_mean": round(float(n_valid.mean()), 3) if not n_valid.empty else None,
                    "neighbor_min": round(float(n_valid.min()), 3) if not n_valid.empty else None,
                    "neighbor_max": round(float(n_valid.max()), 3) if not n_valid.empty else None,
                }

        return AnomalyEpisode(
            station_id=station_id,
            target_variable=target_variable,
            onset_timestamp=onset_timestamp,
            peak_timestamp=peak_timestamp,
            recovery_timestamp=actual_recovery_timestamp,
            duration_minutes=round(duration_min, 1),
            peak_value=peak_val,
            peak_anomaly_score=round(peak_score, 3) if peak_score is not None else None,
            preceding_normal_observations=preceding_obs,
            episode_observations=episode_obs,
            recovering_observations=recovering_obs,
            neighbor_context_summary=neighbor_summary,
        )

    def _records_to_dict_list(
        self,
        df: pd.DataFrame,
        target_variable: str,
        score_column: str,
    ) -> List[Dict[str, Any]]:
        """Convert slice of dataframe to compact JSON-friendly observation records."""
        results: List[Dict[str, Any]] = []
        for _, row in df.iterrows():
            item: Dict[str, Any] = {
                "timestamp": str(row["timestamp"]),
            }
            if target_variable in row and pd.notna(row[target_variable]):
                item[target_variable] = round(float(row[target_variable]), 3)
            if score_column in row and pd.notna(row[score_column]):
                item["anomaly_score"] = round(float(row[score_column]), 3)
            if "decision" in row:
                item["decision"] = str(row["decision"])
            results.append(item)
        return results
