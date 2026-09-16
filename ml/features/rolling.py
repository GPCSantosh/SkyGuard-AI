"""Time-aware and step-aware rolling window feature extraction for SkyGuard AI."""

from __future__ import annotations

from typing import Dict, List, Optional, Sequence
import numpy as np
import pandas as pd


class RollingWindowExtractor:
    """Computes time-aware and lag-based rolling statistics over meteorological time series.
    
    Supports irregular sampling intervals by computing window statistics based on actual
    elapsed datetime offsets rather than assuming static observation counts.
    """

    DEFAULT_TIME_WINDOWS: List[str] = ["15min", "30min", "1h", "3h", "6h", "24h"]
    DEFAULT_LAG_STEPS: List[int] = [1, 2, 3]
    DEFAULT_PARAMETERS: List[str] = [
        "temperature_c",
        "relative_humidity_pct",
        "sea_level_pressure_hpa",
        "station_pressure_hpa",
    ]

    def __init__(
        self,
        time_windows: Optional[Sequence[str]] = None,
        lag_steps: Optional[Sequence[int]] = None,
        parameters: Optional[Sequence[str]] = None,
        min_periods: int = 1,
    ) -> None:
        """Initialize rolling extractor configuration.
        
        Args:
            time_windows: List of pandas-compatible timedelta offset strings (e.g., ['30min', '1h', '6h']).
            lag_steps: List of discrete observation step lags (e.g., [1, 2, 3]).
            parameters: List of numeric column names to compute rolling statistics for.
            min_periods: Minimum number of valid observations required in window.
        """
        self.time_windows = list(time_windows or self.DEFAULT_TIME_WINDOWS)
        self.lag_steps = list(lag_steps or self.DEFAULT_LAG_STEPS)
        self.parameters = list(parameters or self.DEFAULT_PARAMETERS)
        self.min_periods = max(1, min_periods)

    def extract_features(
        self,
        df: pd.DataFrame,
        timestamp_col: str = "timestamp",
        sort_by_time: bool = True,
    ) -> pd.DataFrame:
        """Compute rolling statistics and lag features for configured parameters.
        
        Args:
            df: DataFrame containing meteorological telemetry.
            timestamp_col: Name of the datetime timestamp column.
            sort_by_time: If True, ensures the DataFrame is sorted chronologically.
            
        Returns:
            DataFrame augmented with rolling means, standard deviations, mins, maxs, and lags.
        """
        if df.empty:
            return df.copy()

        result = df.copy()

        # Convert timestamp to UTC DatetimeIndex for rolling operations
        result[timestamp_col] = pd.to_datetime(result[timestamp_col], utc=True)
        if sort_by_time:
            result = result.sort_values(by=timestamp_col).reset_index(drop=True)

        # Work on a temporary time-indexed view for time-aware rolling calculations
        indexed_df = result.set_index(timestamp_col)

        # 1. Compute observation-based lag features
        new_cols: Dict[str, Any] = {}
        for param in self.parameters:
            if param not in result.columns:
                continue
            for lag in self.lag_steps:
                col_name = f"{param}_lag_{lag}"
                new_cols[col_name] = result[param].shift(lag)

        # 2. Compute time-aware window statistics
        for param in self.parameters:
            if param not in result.columns:
                continue

            param_series = indexed_df[param]

            for window in self.time_windows:
                win_clean = window.replace("min", "m").replace("hours", "h").replace("hour", "h")

                rolling_obj = param_series.rolling(
                    window=window,
                    min_periods=self.min_periods,
                    closed="right",
                )

                mean_val = rolling_obj.mean().values
                std_val = rolling_obj.std(ddof=1).fillna(0.0).values
                min_val = rolling_obj.min().values
                max_val = rolling_obj.max().values
                count_val = rolling_obj.count().values

                new_cols[f"{param}_rolling_mean_{win_clean}"] = mean_val
                new_cols[f"{param}_rolling_std_{win_clean}"] = std_val
                new_cols[f"{param}_rolling_min_{win_clean}"] = min_val
                new_cols[f"{param}_rolling_max_{win_clean}"] = max_val
                new_cols[f"{param}_rolling_count_{win_clean}"] = count_val

        # Concat all new columns at once to prevent fragmentation
        if new_cols:
            new_df = pd.DataFrame(new_cols, index=result.index)
            result = pd.concat([result, new_df], axis=1)

        return result
