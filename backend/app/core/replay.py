"""Stream Replay Simulator for sequential playback and real-time anomaly evaluation."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import time
from typing import Any, Callable, Dict, Generator, List, Optional, Sequence, Tuple, Union
import pandas as pd
from pydantic import BaseModel

from backend.app.core.config import get_project_root
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
    """Simulates real-time telemetry streaming from historical or frozen demo datasets with optional fault injection."""

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
        self.current_scenario_id: str = "flagship_narrative"
        self.injected_anomalies: Dict[str, Dict[str, Any]] = {}  # key: station_id::timestamp
        self._playback_task: Optional[asyncio.Task] = None

        if self.interleaved_chronological and self.observations:
            self.observations.sort(key=lambda o: o.timestamp)

    def get_available_scenarios(self) -> List[Dict[str, Any]]:
        """Return list of available frozen demo scenarios from registry."""
        registry_path = get_project_root() / "demo" / "replay" / "scenario_registry.json"
        if registry_path.exists():
            try:
                with open(registry_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return data.get("scenarios", [])
            except Exception:
                pass
        return [
            {
                "id": "flagship_narrative",
                "name": "Flagship Demo Narrative",
                "description": "Standard 8-12 min demo replay sequence.",
                "total_steps": 48,
                "total_observations": len(self.observations),
            }
        ]

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

    def load_scenario(self, scenario_id: str) -> bool:
        """Load specific demo scenario by ID from demo/replay folder."""
        replay_dir = get_project_root() / "demo" / "replay"
        csv_path = replay_dir / "narrative_replay_dataset.csv"
        
        if not csv_path.exists():
            return False

        try:
            df = pd.read_csv(csv_path)
            self.load_from_dataframe(df)
            self.current_scenario_id = scenario_id
            self.current_index = 0
            self.emitted_count = 0
            return True
        except Exception:
            return False

    def reset(self, preserve_db: bool = True) -> Dict[str, Any]:
        """Safely reset transient replay simulation pointers without mutating production database."""
        self.is_running = False
        self.current_index = 0
        self.emitted_count = 0
        return {
            "status": "reset_successful",
            "current_index": 0,
            "emitted_count": 0,
            "current_scenario_id": self.current_scenario_id,
            "database_preserved": preserve_db,
        }

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

    def reset(self, preserve_db: bool = True) -> dict:
        """Reset transient demo simulation pointer state.

        Only resets in-memory replay pointers. Does not delete any database records,
        does not alter frozen evaluation artifacts, does not modify production observation history.

        Args:
            preserve_db: Ignored — database is always preserved. Present for API clarity.

        Returns:
            Status dict confirming reset.
        """
        self.current_index = 0
        self.emitted_count = 0
        self.is_running = False
        return {
            "status": "RESET",
            "current_index": self.current_index,
            "emitted_count": self.emitted_count,
            "total_observations": len(self.observations),
            "current_scenario_id": self.current_scenario_id,
            "database_preserved": True,
            "evaluation_artifacts_unchanged": True,
        }

    def step(
        self,
        engine: RealTimeProcessingEngine,
        count: int = 1,
    ) -> List[ProcessingResult]:
        """Step the replay simulation forward by N observations and process through engine."""
        results: List[ProcessingResult] = []
        if not self.observations:
            return results

        for _ in range(count):
            if self.current_index >= len(self.observations):
                # Loop back or stop
                break
            
            obs = self.observations[self.current_index]
            t_str = obs.timestamp.astimezone(timezone.utc).isoformat()
            key = f"{obs.station_id}::{t_str}"

            if key in self.injected_anomalies:
                injection = self.injected_anomalies[key]
                corrupt_dict = injection["corrupted_values"]
                obs_dict = obs.model_dump()
                for k, v in corrupt_dict.items():
                    if k in obs_dict:
                        obs_dict[k] = v
                obs = WeatherObservation(**obs_dict)

            res = engine.process_observation(obs)
            results.append(res)
            self.current_index += 1
            self.emitted_count += 1

        return results

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
