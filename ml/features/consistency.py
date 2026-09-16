"""Persistence, deviation, and multivariate physical consistency feature extraction for SkyGuard AI."""

from __future__ import annotations

from typing import List, Optional, Sequence
import numpy as np
import pandas as pd

from backend.app.core.constants import EPSILON


class ConsistencyExtractor:
    """Extracts sensor persistence (frozen signal markers), local deviations, and multivariate gradients."""

    DEFAULT_PARAMETERS: List[str] = [
        "temperature_c",
        "relative_humidity_pct",
        "sea_level_pressure_hpa",
    ]

    def __init__(
        self,
        parameters: Optional[Sequence[str]] = None,
        rolling_reference_window: str = "1h",
    ) -> None:
        """Initialize consistency extractor.
        
        Args:
            parameters: List of numeric column names to analyze.
            rolling_reference_window: Window key used for deviation baseline (e.g. '1h' or '3h').
        """
        self.parameters = list(parameters or self.DEFAULT_PARAMETERS)
        self.ref_win = rolling_reference_window.replace("min", "m").replace("hours", "h").replace("hour", "h")

    def extract_features(
        self,
        df: pd.DataFrame,
        timestamp_col: str = "timestamp",
    ) -> pd.DataFrame:
        """Extract persistence, deviation, and multivariate features.
        
        Args:
            df: DataFrame containing telemetry, rolling stats, and deltas.
            timestamp_col: Name of the timestamp column.
            
        Returns:
            DataFrame augmented with persistence, deviation, and multivariate features.
        """
        if df.empty:
            return df.copy()

        result = df.copy()
        result[timestamp_col] = pd.to_datetime(result[timestamp_col], utc=True)

        # 1. Persistence Features (Frozen Sensor Indicators)
        for param in self.parameters:
            if param not in result.columns:
                continue

            values = result[param].values
            n = len(values)

            # A. Consecutive identical values run length counter
            consecutive_counts = np.zeros(n, dtype=int)
            time_since_change_mins = np.zeros(n, dtype=float)

            current_count = 1
            last_change_idx = 0

            for i in range(n):
                if i == 0 or pd.isna(values[i]):
                    consecutive_counts[i] = 1
                    time_since_change_mins[i] = 0.0
                    last_change_idx = i
                else:
                    prev_val = values[i - 1]
                    curr_val = values[i]

                    if not pd.isna(prev_val) and curr_val == prev_val:
                        current_count += 1
                        consecutive_counts[i] = current_count
                        # Time since last change
                        t_curr = result[timestamp_col].iloc[i]
                        t_change = result[timestamp_col].iloc[last_change_idx]
                        time_since_change_mins[i] = (t_curr - t_change).total_seconds() / 60.0
                    else:
                        current_count = 1
                        consecutive_counts[i] = 1
                        last_change_idx = i
                        time_since_change_mins[i] = 0.0

            result[f"{param}_consecutive_unchanged_count"] = consecutive_counts
            result[f"{param}_duration_unchanged_minutes"] = time_since_change_mins

            # B. Repeated rounded values (rounded to 1 decimal place or nearest integer)
            rounded_vals = np.round(values, 1)
            rounded_consecutive = np.zeros(n, dtype=int)
            r_count = 1
            for i in range(n):
                if i == 0 or pd.isna(rounded_vals[i]):
                    rounded_consecutive[i] = 1
                else:
                    if not pd.isna(rounded_vals[i - 1]) and rounded_vals[i] == rounded_vals[i - 1]:
                        r_count += 1
                    else:
                        r_count = 1
                    rounded_consecutive[i] = r_count
            result[f"{param}_rounded_unchanged_count"] = rounded_consecutive

        # 2. Deviation Features (Residuals, Z-scores, and safe percentage deviations)
        for param in self.parameters:
            if param not in result.columns:
                continue

            mean_col = f"{param}_rolling_mean_{self.ref_win}"
            std_col = f"{param}_rolling_std_{self.ref_win}"

            if mean_col in result.columns:
                # Residual: X - rolling_mean
                residual = result[param] - result[mean_col]
                result[f"{param}_deviation_from_mean_{self.ref_win}"] = residual

                # Safe percentage deviation: (X - mean) / mean where |mean| > 0.1
                safe_mean_denom = np.where(result[mean_col].abs() > 0.1, result[mean_col], np.nan)
                result[f"{param}_pct_deviation_{self.ref_win}"] = (residual / safe_mean_denom) * 100.0

            if mean_col in result.columns and std_col in result.columns:
                # Z-Score: (X - mean) / (std + epsilon)
                safe_std = np.where(result[std_col] > EPSILON, result[std_col], np.nan)
                result[f"{param}_zscore_{self.ref_win}"] = residual / safe_std

        # 3. Multivariate Consistency Features (Joint physical interaction)
        has_temp = "temperature_c" in result.columns
        has_rh = "relative_humidity_pct" in result.columns
        has_slp = "sea_level_pressure_hpa" in result.columns
        has_dew = "dew_point_c" in result.columns

        # A. Dew point spread: T - Td
        if has_temp and has_dew:
            result["dew_point_spread_c"] = result["temperature_c"] - result["dew_point_c"]

        # B. Delta Temperature vs Delta Humidity interaction
        if has_temp and has_rh and "temperature_c_delta" in result.columns and "relative_humidity_pct_delta" in result.columns:
            # Physical expectation: rising temp typically correlates with dropping RH during diurnal cycle
            # Product of deltas: positive value indicates both increased or both decreased
            result["temp_rh_delta_interaction"] = result["temperature_c_delta"] * result["relative_humidity_pct_delta"]
            
            # Standardized rate difference
            if f"temperature_c_rolling_std_{self.ref_win}" in result.columns and f"relative_humidity_pct_rolling_std_{self.ref_win}" in result.columns:
                std_t = result[f"temperature_c_rolling_std_{self.ref_win}"].replace(0.0, np.nan)
                std_rh = result[f"relative_humidity_pct_rolling_std_{self.ref_win}"].replace(0.0, np.nan)
                norm_dt = result["temperature_c_delta"] / (std_t + EPSILON)
                norm_drh = result["relative_humidity_pct_delta"] / (std_rh + EPSILON)
                result["joint_temp_rh_divergence"] = norm_dt - norm_drh

        # C. Delta Temperature vs Delta Pressure interaction
        if has_temp and has_slp and "temperature_c_delta" in result.columns and "sea_level_pressure_hpa_delta" in result.columns:
            result["temp_slp_delta_interaction"] = result["temperature_c_delta"] * result["sea_level_pressure_hpa_delta"]

        # D. Joint multi-parameter standardized deviation (Euclidean norm of available z-scores)
        z_cols = [f"{p}_zscore_{self.ref_win}" for p in self.parameters if f"{p}_zscore_{self.ref_win}" in result.columns]
        if z_cols:
            z_matrix = result[z_cols].fillna(0.0).values
            result["joint_standardized_anomaly_magnitude"] = np.sqrt(np.sum(z_matrix ** 2, axis=1))

        return result
