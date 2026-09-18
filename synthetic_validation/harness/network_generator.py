"""Synthetic 20-Station AWS Network & Meteorological Baseline Generator.

Generates physically consistent, geographically distributed Automatic Weather Stations
with deterministic diurnal cycles, altitude gradients, and spatial proximity.
"""

from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple
import numpy as np
import pandas as pd

from backend.app.models.observation import (
    ObservationSource,
    QualityStatus,
    WeatherObservation,
)
from ml.spatial.topology import SpatialNetworkTopology, StationNode


# Pre-defined deterministic 20-station network spanning the Delhi-NCR / North India basin
# Contains tightly clustered stations, moderate-distance clusters, and an isolated hilltop/outlier station.
DEFAULT_SYNTHETIC_STATIONS: List[Dict[str, float | str]] = [
    # Cluster A: Urban Central (Close neighbors: 5-15 km)
    {"station_id": "AWS_DEL_001", "name": "Delhi Safdarjung AWS", "latitude": 28.5840, "longitude": 77.2060, "elevation_m": 216.0, "t_offset": 0.0, "p_offset": 0.0},
    {"station_id": "AWS_DEL_002", "name": "Delhi Palam AWS", "latitude": 28.5665, "longitude": 77.1031, "elevation_m": 224.0, "t_offset": 0.4, "p_offset": -0.8},
    {"station_id": "AWS_DEL_003", "name": "Delhi Lodhi Road AWS", "latitude": 28.5910, "longitude": 77.2270, "elevation_m": 211.0, "t_offset": -0.2, "p_offset": 0.3},
    {"station_id": "AWS_DEL_004", "name": "Delhi Ridge AWS", "latitude": 28.6700, "longitude": 77.2180, "elevation_m": 235.0, "t_offset": -0.5, "p_offset": -1.5},
    {"station_id": "AWS_DEL_005", "name": "Delhi Ayanagar AWS", "latitude": 28.4810, "longitude": 77.1260, "elevation_m": 240.0, "t_offset": 0.2, "p_offset": -2.0},

    # Cluster B: NCR Suburban Ring (Moderate distance: 20-40 km from center)
    {"station_id": "AWS_NCR_006", "name": "Noida Sector 62 AWS", "latitude": 28.6271, "longitude": 77.3620, "elevation_m": 204.0, "t_offset": 0.1, "p_offset": 0.8},
    {"station_id": "AWS_NCR_007", "name": "Greater Noida AWS", "latitude": 28.4744, "longitude": 77.5040, "elevation_m": 198.0, "t_offset": -0.3, "p_offset": 1.2},
    {"station_id": "AWS_NCR_008", "name": "Gurugram CyberCity AWS", "latitude": 28.4950, "longitude": 77.0890, "elevation_m": 228.0, "t_offset": 0.6, "p_offset": -1.0},
    {"station_id": "AWS_NCR_009", "name": "Faridabad NIT AWS", "latitude": 28.4089, "longitude": 77.3178, "elevation_m": 206.0, "t_offset": 0.3, "p_offset": 0.5},
    {"station_id": "AWS_NCR_010", "name": "Ghaziabad Vasundhara AWS", "latitude": 28.6692, "longitude": 77.3820, "elevation_m": 210.0, "t_offset": 0.0, "p_offset": 0.2},

    # Cluster C: Regional Plains & Agricultural Ring (Moderate-to-far distance: 45-80 km)
    {"station_id": "AWS_REG_011", "name": "Sonipat Urban AWS", "latitude": 28.9931, "longitude": 77.0151, "elevation_m": 220.0, "t_offset": -0.7, "p_offset": -0.3},
    {"station_id": "AWS_REG_012", "name": "Rohtak Central AWS", "latitude": 28.8955, "longitude": 76.6066, "elevation_m": 220.0, "t_offset": -0.4, "p_offset": -0.2},
    {"station_id": "AWS_REG_013", "name": "Jhajjar Rural AWS", "latitude": 28.6064, "longitude": 76.6565, "elevation_m": 222.0, "t_offset": -0.5, "p_offset": -0.5},
    {"station_id": "AWS_REG_014", "name": "Meerut Cantt AWS", "latitude": 28.9845, "longitude": 77.7064, "elevation_m": 219.0, "t_offset": -0.6, "p_offset": -0.2},
    {"station_id": "AWS_REG_015", "name": "Bulandshahr AWS", "latitude": 28.4070, "longitude": 77.8498, "elevation_m": 196.0, "t_offset": 0.2, "p_offset": 1.4},
    {"station_id": "AWS_REG_016", "name": "Palwal Highway AWS", "latitude": 28.1487, "longitude": 77.3320, "elevation_m": 195.0, "t_offset": 0.5, "p_offset": 1.5},
    {"station_id": "AWS_REG_017", "name": "Rewari Industrial AWS", "latitude": 28.1820, "longitude": 76.6180, "elevation_m": 242.0, "t_offset": 0.7, "p_offset": -2.2},
    {"station_id": "AWS_REG_018", "name": "Alwar Outpost AWS", "latitude": 27.5530, "longitude": 76.6346, "elevation_m": 270.0, "t_offset": 1.1, "p_offset": -4.2},
    {"station_id": "AWS_REG_019", "name": "Panipat Refinery AWS", "latitude": 29.3909, "longitude": 76.9635, "elevation_m": 219.0, "t_offset": -0.8, "p_offset": -0.2},

    # Station D: Isolated High-Elevation Foot-Hill Outlier (> 130 km from cluster)
    {"station_id": "AWS_ISO_020", "name": "Dehradun Foothill Outlier AWS", "latitude": 30.3165, "longitude": 78.0322, "elevation_m": 680.0, "t_offset": -4.8, "p_offset": -42.0},
]


class SyntheticNetworkGenerator:
    """Generates a deterministic 20-station network and physically consistent meteorological baseline series."""

    def __init__(
        self,
        station_configs: Optional[List[Dict[str, float | str]]] = None,
        seed: int = 42,
    ) -> None:
        self.station_configs = station_configs or DEFAULT_SYNTHETIC_STATIONS
        self.seed = seed
        self.rng = np.random.RandomState(seed)

    def create_topology(self) -> SpatialNetworkTopology:
        """Create a SpatialNetworkTopology populated with all synthetic AWS stations."""
        topo = SpatialNetworkTopology()
        for cfg in self.station_configs:
            topo.add_station(StationNode(
                station_id=str(cfg["station_id"]),
                name=str(cfg["name"]),
                latitude=float(cfg["latitude"]),
                longitude=float(cfg["longitude"]),
                elevation_m=float(cfg["elevation_m"]),
            ))
        return topo

    def generate_baseline_observations(
        self,
        start_time: Optional[datetime] = None,
        duration_hours: float = 24.0,
        interval_minutes: int = 5,
        base_temp_c: float = 26.0,
        temp_amplitude_c: float = 7.0,
        base_rh_pct: float = 65.0,
        rh_amplitude_pct: float = 22.0,
        base_slp_hpa: float = 1012.0,
        slp_amplitude_hpa: float = 2.5,
    ) -> List[WeatherObservation]:
        """Generate physically consistent baseline observation series across all network stations.
        
        Physics Model:
        - Diurnal Temperature Cycle: Peak at 14:00 UTC+5:30 (approx 08:30 UTC), trough at 05:00 UTC+5:30
        - Inverse Relative Humidity: Peak early morning when temperature is minimum, trough in afternoon
        - Semidiurnal Atmospheric Pressure Tide: Natural ~12-hour barometric cycle with lapse-rate adjustments
        - Realistic measurement noise: Gaussian white noise (sigma_T=0.15°C, sigma_RH=0.6%, sigma_P=0.08 hPa)
        """
        if start_time is None:
            start_time = datetime(2026, 9, 17, 0, 0, 0, tzinfo=timezone.utc)

        total_steps = int((duration_hours * 60) // interval_minutes)
        observations: List[WeatherObservation] = []

        # Reset RNG with deterministic seed for full reproducibility
        rng = np.random.RandomState(self.seed)

        for step in range(total_steps):
            current_time = start_time + timedelta(minutes=step * interval_minutes)
            hour_utc = current_time.hour + current_time.minute / 60.0

            # Diurnal phase: solar maximum around 08:30 UTC (14:00 IST)
            solar_phase = 2.0 * math.pi * (hour_utc - 8.5) / 24.0
            t_diurnal = float(math.cos(solar_phase))  # +1 at solar noon, -1 at min

            # Semidiurnal atmospheric tide for pressure (peaks at 10:00 and 22:00 local time)
            pressure_phase = 4.0 * math.pi * (hour_utc - 4.5) / 24.0
            p_tide = float(math.cos(pressure_phase))

            # Regional synoptic baseline
            reg_temp = base_temp_c + temp_amplitude_c * t_diurnal
            reg_rh = base_rh_pct - rh_amplitude_pct * t_diurnal
            reg_slp = base_slp_hpa + slp_amplitude_hpa * p_tide

            for cfg in self.station_configs:
                s_id = str(cfg["station_id"])
                s_name = str(cfg["name"])
                lat = float(cfg["latitude"])
                lon = float(cfg["longitude"])
                elev = float(cfg["elevation_m"])
                t_off = float(cfg["t_offset"])
                p_off = float(cfg["p_offset"])

                # Local stochastic sensor noise
                noise_t = rng.normal(0.0, 0.12)
                noise_rh = rng.normal(0.0, 0.5)
                noise_p = rng.normal(0.0, 0.06)

                stn_temp = round(float(reg_temp + t_off + noise_t), 2)
                stn_rh = round(float(np.clip(reg_rh - (t_off * 1.5) + noise_rh, 10.0, 98.0)), 2)
                stn_slp = round(float(reg_slp + p_off + noise_p), 2)

                # Physically derived dew point using Magnus formula approximation
                # Td ~= T - ((100 - RH) / 5)
                stn_dew = round(float(stn_temp - ((100.0 - stn_rh) / 5.0)), 2)

                obs = WeatherObservation(
                    station_id=s_id,
                    station_name=s_name,
                    latitude=lat,
                    longitude=lon,
                    elevation=elev,
                    timestamp=current_time,
                    temperature=stn_temp,
                    dew_point_c=stn_dew,
                    humidity=stn_rh,
                    pressure=stn_slp,
                    source=ObservationSource.SIMULATOR,
                    data_quality_status=QualityStatus.VALID,
                    is_synthetic=True,
                    metadata={"network": "SYNTHETIC_20_AWS", "step_index": step},
                )
                observations.append(obs)

        return observations

    def generate_baseline_dataframe(
        self,
        start_time: Optional[datetime] = None,
        duration_hours: float = 24.0,
        interval_minutes: int = 5,
    ) -> pd.DataFrame:
        """Generate baseline observation dataset as a standardized pandas DataFrame."""
        obs_list = self.generate_baseline_observations(
            start_time=start_time,
            duration_hours=duration_hours,
            interval_minutes=interval_minutes,
        )
        records = []
        for o in obs_list:
            records.append({
                "station_id": o.station_id,
                "station_name": o.station_name,
                "latitude": o.latitude,
                "longitude": o.longitude,
                "elevation": o.elevation,
                "timestamp": o.timestamp.isoformat(),
                "temperature_c": o.temperature,
                "dew_point_c": o.dew_point_c,
                "relative_humidity_pct": o.humidity,
                "sea_level_pressure_hpa": o.pressure,
                "source": o.source,
                "data_quality_status": o.data_quality_status,
                "is_synthetic": True,
            })
        return pd.DataFrame(records)
