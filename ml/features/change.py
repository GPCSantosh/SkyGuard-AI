"""Rate of change and time-normalized gradient feature extraction for SkyGuard AI."""

from __future__ import annotations

from typing import List, Optional, Sequence
import numpy as np
import pandas as pd


class RateOfChangeExtractor:
    """Calculates instantaneous differences and time-normalized rates of change (per minute / per hour).
    
    Guarantees strict safety against zero-elapsed-time divisions, missing lag records,
    and out-of-order temporal records.
    """

    DEFAULT_PARAMETERS: List[str] = [
        "temperature_c",
        "relative_humidity_pct",
        "sea_level_pressure_hpa",
        "station_pressure_hpa",
    ]

    def __init__(self, parameters: Optional[Sequence[str]] = None) -> None:
        """Initialize rate of change extractor.
        
        Args:
            parameters: List of numeric column names to compute rates for.
        """
        self.parameters = list(parameters or self.DEFAULT_PARAMETERS)

    def extract_features(
        self,
        df: pd.DataFrame,
        timestamp_col: str = "timestamp",
        sort_by_time: bool = True,
    ) -> pd.DataFrame:
        """Calculate first-order step deltas and time-normalized rates of change.
        
        Args:
            df: DataFrame containing meteorological telemetry.
            timestamp_col: Name of the datetime timestamp column.
            sort_by_time: If True, ensures the DataFrame is sorted chronologically.
            
        Returns:
            DataFrame augmented with step delta and per-minute rate-of-change columns.
        """
        if df.empty:
            return df.copy()

        result = df.copy()
        result[timestamp_col] = pd.to_datetime(result[timestamp_col], utc=True)
        if sort_by_time:
            result = result.sort_values(by=timestamp_col).reset_index(drop=True)

        # Compute elapsed time between consecutive observations in minutes
        time_diff = result[timestamp_col].diff().dt.total_seconds() / 60.0
        result["elapsed_minutes"] = time_diff

        # For the very first observation, elapsed_minutes is NaN
        for param in self.parameters:
            if param not in result.columns:
                continue

            # 1. Discrete step delta (X_t - X_{t-1})
            delta_col = f"{param}_delta"
            param_delta = result[param].diff()
            result[delta_col] = param_delta

            # 2. Time-normalized rate of change: delta / elapsed_minutes
            # Prevent division by zero if elapsed_minutes is 0.0 or negative/NaN
            rate_col = f"{param}_rate_per_minute"
            rate_5min_col = f"{param}_rate_per_5min"
            rate_hour_col = f"{param}_rate_per_hour"

            # Use numpy where condition for division safety
            valid_time = (time_diff > 0.0) & (~time_diff.isna()) & (~param_delta.isna())
            safe_elapsed = np.where(valid_time, time_diff, np.nan)

            rate_per_min = np.where(valid_time, param_delta / safe_elapsed, np.nan)
            result[rate_col] = rate_per_min
            result[rate_5min_col] = rate_per_min * 5.0
            result[rate_hour_col] = rate_per_min * 60.0

            # Second-order difference (acceleration / rate change)
            result[f"{param}_acceleration"] = result[delta_col].diff()

        return result
