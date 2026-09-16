"""Stream Replay Simulator for sequential playback and real-time anomaly evaluation."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import math
import time
from typing import Any, Callable, Dict, Generator, List, Optional, Sequence, Tuple
import pandas as pd
from pydantic import BaseModel

from backend.app.core.engine import RealTimeProcessingEngine
from backend.app.models.observation import ObservationSource, QualityStatus, WeatherObservation
from backend.app.models.processing import ProcessingResult


class SyntheticGroundTruth(BaseModel):
    """Ground-truth metadata accompanying replayed observation (strictly isolated from engine)."""
    station_id: str
    timestamp: str
    is_anomaly: bool = False
    anomaly_category: str = "NORMAL"
    clean_temperature_c: Optional[float] = None


class StreamReplayEngine:
    """Simulates real-time telemetry streaming from historical datasets with optional fault injection."""

    def __init__(
        self,
        observations: Optional[Sequence[WeatherObservation]] = None,
        speed_multiplier: float = 60.0,
        interleaved_chronological: bool = True,
    ) -> None:
        self.observations: List[WeatherObservation] = list(observations or [])
        self.speed_multiplier = speed_multiplier
        self.interleaved_chronological = interleaved_chronological
        
        self.is_running = False
        self.emitted_count = 0
        self.current_index = 0
        self.injected_anomalies: Dict[str, Dict[str, Any]] = {}  # key: station_id::timestamp

        if self.interleaved_chronological and self.observations:
            self.observations.sort(key=lambda o: o.timestamp)

    def load_from_dataframe(
        self,
        df: pd.DataFrame,
        station_id_col: str = "station_id",
        timestamp_col: str = "timestamp",
    ) -> None:
        """Construct observation stream from pandas DataFrame."""
        self.observations = []
        df_sorted = df.sort_values(timestamp_col)

        for _, row in df_sorted.iterrows():
            obs = WeatherObservation(
                station_id=str(row[station_id_col]),
                station_name=str(row.get("station_name", f"Station {row[station_id_col]}")),
                latitude=float(row.get("latitude", 28.6)),
                longitude=float(row.get("longitude", 77.2)),
                elevation=float(row.get("elevation", row.get("elevation_m", 200.0))) if pd.notna(row.get("elevation", row.get("elevation_m"))) else None,
                timestamp=pd.to_datetime(row[timestamp_col], utc=True),
                temperature=float(row["temperature_c"]) if "temperature_c" in row and pd.notna(row["temperature_c"]) else (float(row["temperature"]) if "temperature" in row and pd.notna(row["temperature"]) else None),
                dew_point_c=float(row["dew_point_c"]) if "dew_point_c" in row and pd.notna(row["dew_point_c"]) else None,
                pressure=float(row["sea_level_pressure_hpa"]) if "sea_level_pressure_hpa" in row and pd.notna(row["sea_level_pressure_hpa"]) else (float(row["pressure"]) if "pressure" in row and pd.notna(row["pressure"]) else None),
                station_pressure_hpa=float(row["station_pressure_hpa"]) if "station_pressure_hpa" in row and pd.notna(row["station_pressure_hpa"]) else None,
                humidity=float(row["relative_humidity_pct"]) if "relative_humidity_pct" in row and pd.notna(row["relative_humidity_pct"]) else (float(row["humidity"]) if "humidity" in row and pd.notna(row["humidity"]) else None),
                source=ObservationSource.SIMULATOR,
                data_quality_status=QualityStatus.VALID,
            )
            self.observations.append(obs)

        self.current_index = 0
        self.emitted_count = 0

    def register_injected_anomaly(
        self,
        station_id: str,
        timestamp: Union[str, datetime],
        anomaly_type: str,
        corrupted_values: Dict[str, float],
    ) -> None:
        """Register a synthetic fault to inject during stream replay."""
        t_str = pd.to_datetime(timestamp, utc=True).isoformat()
        key = f"{station_id}::{t_str}"
        self.injected_anomalies[key] = {
            "anomaly_type": anomaly_type,
            "corrupted_values": corrupted_values,
        }

    def iterate_stream(self) -> Generator[Tuple[WeatherObservation, Optional[SyntheticGroundTruth]], None, None]:
        """Yield sequential observations with synthetic faults applied."""
        for obs in self.observations:
            t_str = obs.timestamp.astimezone(timezone.utc).isoformat()
            key = f"{obs.station_id}::{t_str}"
            
            ground_truth = SyntheticGroundTruth(
                station_id=obs.station_id,
                timestamp=t_str,
                is_anomaly=False,
                anomaly_category="NORMAL",
                clean_temperature_c=obs.temperature,
            )

            # Check if injected anomaly exists for this timestamp
            if key in self.injected_anomalies:
                injection = self.injected_anomalies[key]
                ground_truth = SyntheticGroundTruth(
                    station_id=obs.station_id,
                    timestamp=t_str,
                    is_anomaly=True,
                    anomaly_category=injection["anomaly_type"],
                    clean_temperature_c=obs.temperature,
                )
                
                # Apply corrupted values
                corrupt_dict = injection["corrupted_values"]
                obs_dict = obs.model_dump()
                for k, v in corrupt_dict.items():
                    if k in obs_dict:
                        obs_dict[k] = v
                obs = WeatherObservation(**obs_dict)

            self.emitted_count += 1
            yield obs, ground_truth

    def run_synchronous_simulation(
        self,
        engine: RealTimeProcessingEngine,
        max_steps: Optional[int] = None,
    ) -> List[ProcessingResult]:
        """Execute simulation synchronously through the engine."""
        results: List[ProcessingResult] = []
        count = 0

        for obs, gt in self.iterate_stream():
            res = engine.process_observation(obs)
            results.append(res)
            count += 1
            if max_steps is not None and count >= max_steps:
                break

        return results
