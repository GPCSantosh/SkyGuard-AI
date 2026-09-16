"""Temporal and cyclical calendar feature extraction for SkyGuard AI."""

from __future__ import annotations

from typing import Optional
import numpy as np
import pandas as pd


class TemporalFeatureExtractor:
    """Extracts calendar and cyclical temporal features from observation timestamps.
    
    Avoids linear encoding artifacts for periodic cycles (e.g., hour 23 and hour 0
    being represented with maximum numerical distance) by computing sinusoidal embeddings.
    """

    @staticmethod
    def extract_features(df: pd.DataFrame, timestamp_col: str = "timestamp") -> pd.DataFrame:
        """Extract calendar and circular temporal features.
        
        Args:
            df: DataFrame containing at least the timestamp column.
            timestamp_col: Name of the timestamp column.
            
        Returns:
            DataFrame with added temporal feature columns.
        """
        if df.empty:
            result = df.copy()
            for col in [
                "hour", "minute", "day_of_year", "month", "day_of_week",
                "sin_hour", "cos_hour", "sin_day_of_year", "cos_day_of_year",
                "sin_day_of_week", "cos_day_of_week"
            ]:
                result[col] = pd.Series(dtype=float)
            return result

        result = df.copy()
        ts = pd.to_datetime(result[timestamp_col], utc=True)

        result["hour"] = ts.dt.hour
        result["minute"] = ts.dt.minute
        result["day_of_year"] = ts.dt.dayofyear
        result["month"] = ts.dt.month
        result["day_of_week"] = ts.dt.dayofweek

        # Cyclical transforms (2*pi * t / T)
        # Hour of day (period = 24 hours + minute fractional offset)
        fractional_hour = result["hour"] + result["minute"] / 60.0
        result["sin_hour"] = np.sin(2.0 * np.pi * fractional_hour / 24.0)
        result["cos_hour"] = np.cos(2.0 * np.pi * fractional_hour / 24.0)

        # Day of year (period = 365.25 days)
        result["sin_day_of_year"] = np.sin(2.0 * np.pi * (result["day_of_year"] - 1) / 365.25)
        result["cos_day_of_year"] = np.cos(2.0 * np.pi * (result["day_of_year"] - 1) / 365.25)

        # Day of week (period = 7 days)
        result["sin_day_of_week"] = np.sin(2.0 * np.pi * result["day_of_week"] / 7.0)
        result["cos_day_of_week"] = np.cos(2.0 * np.pi * result["day_of_week"] / 7.0)

        return result
