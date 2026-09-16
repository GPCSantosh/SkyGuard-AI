"""Neighbor comparison and spatial alignment analyzer for SkyGuard AI."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Union
import numpy as np
import pandas as pd

from ml.explainability.schema import NeighborComparison


class NeighborComparator:
    """Computes strictly causal, multi-station neighbor comparisons for sensor anomaly validation."""

    def __init__(
        self,
        default_tolerances: Optional[Dict[str, float]] = None,
        alignment_window_minutes: float = 15.0,
    ) -> None:
        """Initialize NeighborComparator.
        
        Args:
            default_tolerances: Mapping of meteorological variables to max absolute difference considered 'in agreement'.
            alignment_window_minutes: Maximum lookback window for neighbor temporal synchronization.
        """
        self.tolerances = default_tolerances or {
            "temperature_c": 2.0,
            "relative_humidity": 10.0,
            "sea_level_pressure_hpa": 2.5,
            "station_pressure_hpa": 2.5,
            "dew_point_c": 2.5,
            "wind_speed_mps": 3.0,
        }
        self.alignment_window_minutes = alignment_window_minutes

    def compare_neighbors(
        self,
        target_station_id: str,
        target_timestamp: str,
        target_variable: str,
        target_value: Optional[float],
        neighbor_data: Union[Dict[str, Optional[float]], pd.DataFrame],
        custom_tolerance: Optional[float] = None,
    ) -> NeighborComparison:
        """Perform spatial neighbor comparison for target variable at target timestamp.
        
        Args:
            target_station_id: Station ID under inspection.
            target_timestamp: Timestamp of the target observation.
            target_variable: Primary variable name (e.g. 'temperature_c').
            target_value: Measured value on target station.
            neighbor_data: Dict mapping neighbor_station_id to value, or DataFrame of neighbor records.
            custom_tolerance: Optional tolerance overriding default.
            
        Returns:
            `NeighborComparison` object containing median, deviation, and agreement counts.
        """
        tolerance = custom_tolerance or self.tolerances.get(target_variable, 2.0)
        neighbor_values: Dict[str, Optional[float]] = {}

        if isinstance(neighbor_data, pd.DataFrame):
            # If a DataFrame is provided, filter out future observations to enforce strict causality
            df = neighbor_data.copy()
            if "station_id" in df.columns:
                df = df[df["station_id"] != target_station_id]
            if "timestamp" in df.columns:
                t_target = pd.to_datetime(target_timestamp)
                # Keep only past or current observations up to target_timestamp within alignment window
                df["dt"] = pd.to_datetime(df["timestamp"])
                df = df[(df["dt"] <= t_target) & (df["dt"] >= t_target - pd.Timedelta(minutes=self.alignment_window_minutes))]
                # Get the most recent value for each neighbor
                if not df.empty and target_variable in df.columns:
                    latest = df.sort_values("dt").groupby("station_id").last()
                    for nid, row in latest.iterrows():
                        val = row[target_variable]
                        neighbor_values[str(nid)] = float(val) if pd.notna(val) else None
        elif isinstance(neighbor_data, dict):
            for nid, val in neighbor_data.items():
                if str(nid) != str(target_station_id):
                    neighbor_values[str(nid)] = float(val) if val is not None and not np.isnan(val) else None

        valid_vals = [v for v in neighbor_values.values() if v is not None and not np.isnan(v)]
        total_valid = len(valid_vals)

        if total_valid == 0:
            status = "NO_NEIGHBORS" if len(neighbor_values) == 0 else "STALE_OR_MISSING"
            return NeighborComparison(
                target_variable=target_variable,
                target_value=target_value,
                neighbor_values=neighbor_values,
                neighbor_median=None,
                target_deviation=None,
                agreeing_neighbor_count=0,
                total_valid_neighbors=0,
                temporal_alignment_window_minutes=self.alignment_window_minutes,
                temporal_alignment_status=status,
            )

        neighbor_med = float(np.median(valid_vals))
        dev = float(target_value - neighbor_med) if target_value is not None else None

        # Agreeing neighbors: neighbor values close to target value within tolerance
        agree_count = 0
        if target_value is not None:
            agree_count = sum(1 for v in valid_vals if abs(v - target_value) <= tolerance)

        status = "ALIGNED" if total_valid >= 3 else "SPARSE"

        return NeighborComparison(
            target_variable=target_variable,
            target_value=round(target_value, 3) if target_value is not None else None,
            neighbor_values={k: (round(v, 3) if v is not None else None) for k, v in neighbor_values.items()},
            neighbor_median=round(neighbor_med, 3),
            target_deviation=round(dev, 3) if dev is not None else None,
            agreeing_neighbor_count=agree_count,
            total_valid_neighbors=total_valid,
            temporal_alignment_window_minutes=self.alignment_window_minutes,
            temporal_alignment_status=status,
        )
