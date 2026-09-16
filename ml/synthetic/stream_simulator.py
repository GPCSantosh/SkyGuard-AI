"""High-cadence 5-minute synthetic stream simulator for SkyGuard AI."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd


class StreamSimulator:
    """Generates high-cadence 5-minute simulation streams from lower-cadence or irregular historical series.
    
    CRITICAL METEOROLOGICAL & AUDITING PRINCIPLE:
    - Simulated observations are strictly tagged with is_synthetic = True.
    - Interpolation is used purely as a temporal testing mechanism, NEVER as manufactured ground truth.
    """

    DEFAULT_TARGET_CADENCE_MINUTES: float = 5.0

    def __init__(
        self,
        target_cadence_minutes: float = 5.0,
        interpolation_method: str = "time",
        add_micro_turbulence: bool = True,
        seed: int = 42,
    ) -> None:
        """Initialize stream simulator.
        
        Args:
            target_cadence_minutes: Target regular stream cadence in minutes (default 5.0).
            interpolation_method: Resampling interpolation method (e.g. 'time', 'linear', 'cubic').
            add_micro_turbulence: Whether to add low-amplitude realistic micro-meteorological noise.
            seed: Random seed for noise generation.
        """
        self.target_cadence_minutes = target_cadence_minutes
        self.interpolation_method = interpolation_method
        self.add_micro_turbulence = add_micro_turbulence
        self.rng = np.random.default_rng(seed)

    def simulate_stream(
        self,
        df: pd.DataFrame,
        timestamp_col: str = "timestamp",
        station_id_col: str = "station_id",
    ) -> pd.DataFrame:
        """Resample input observations onto a regular 5-minute time grid with explicit synthetic provenance.
        
        Args:
            df: Historical observations DataFrame.
            timestamp_col: Name of the timestamp column.
            station_id_col: Name of the station ID column.
            
        Returns:
            DataFrame resampled to 5-minute grid with is_synthetic=True and derivation metadata.
        """
        if df.empty:
            return df.copy()

        result_stations: List[pd.DataFrame] = []
        df_copy = df.copy()
        df_copy[timestamp_col] = pd.to_datetime(df_copy[timestamp_col], utc=True)

        for s_id, group in df_copy.groupby(station_id_col):
            stn_group = group.sort_values(by=timestamp_col).drop_duplicates(subset=[timestamp_col])
            if len(stn_group) < 2:
                result_stations.append(stn_group)
                continue

            # Estimate source resolution
            median_delta_mins = float(
                stn_group[timestamp_col].diff().dt.total_seconds().median() / 60.0
            )

            # Reindex onto regular 5-minute grid
            stn_group = stn_group.set_index(timestamp_col)
            freq_str = f"{int(self.target_cadence_minutes)}min"
            resampled = stn_group.resample(freq_str).asfreq()

            # Interpolate numeric columns
            numeric_cols = [
                "temperature_c",
                "relative_humidity_pct",
                "sea_level_pressure_hpa",
                "station_pressure_hpa",
                "dew_point_c",
            ]
            for col in numeric_cols:
                if col in resampled.columns:
                    resampled[col] = resampled[col].interpolate(method=self.interpolation_method)
                    # Add subtle micro-turbulence if enabled
                    if self.add_micro_turbulence:
                        noise_scale = 0.05 if "temp" in col else (0.2 if "humidity" in col else 0.02)
                        noise = self.rng.normal(0.0, noise_scale, size=len(resampled))
                        resampled[col] = resampled[col] + noise

            # Forward-fill static metadata
            static_cols = [
                station_id_col,
                "station_name",
                "latitude",
                "longitude",
                "elevation_m",
                "source",
                "report_type",
            ]
            for col in static_cols:
                if col in resampled.columns:
                    resampled[col] = resampled[col].ffill().bfill()

            resampled = resampled.reset_index()

            # Set mandatory synthetic provenance flags
            resampled["is_synthetic"] = True
            resampled["native_resolution_minutes"] = self.target_cadence_minutes
            resampled["source_resolution_minutes"] = median_delta_mins
            resampled["simulation_resolution_minutes"] = self.target_cadence_minutes
            resampled["simulation_method"] = self.interpolation_method
            resampled["ingestion_timestamp"] = datetime.now(timezone.utc).isoformat()

            result_stations.append(resampled)

        return pd.concat(result_stations, ignore_index=True)
