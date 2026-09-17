"""Live AWS / Weather API Source Qualification Adapter and Quality Gates.

Implements Phase 11A live source qualification, contract auditing,
source-health diagnostics, and strict canonical normalization into
the WeatherObservation contract.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
import math
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, ConfigDict, Field

from backend.app.core.constants import (
    HUMIDITY_PHYSICAL_MAX_PCT,
    HUMIDITY_PHYSICAL_MIN_PCT,
    PRESSURE_PHYSICAL_MAX_HPA,
    PRESSURE_PHYSICAL_MIN_HPA,
    TEMP_PHYSICAL_MAX_C,
    TEMP_PHYSICAL_MIN_C,
)
from backend.app.models.observation import (
    ObservationSource,
    QualityStatus,
    WeatherObservation,
)


class PressureSemantics(str, Enum):
    """Semantic meaning of the incoming pressure variable."""
    MEAN_SEA_LEVEL_PRESSURE = "MSLP"
    STATION_SURFACE_PRESSURE = "SURFACE"
    UNSPECIFIED_OR_UNKNOWN = "UNKNOWN"


class LiveSourceHealthStatus(BaseModel):
    """Operational health state of the live upstream API / telemetry feed.
    
    CRITICAL ARCHITECTURAL DISTINCTION:
    - Sensor Health = physical instrument health of a specific Automatic Weather Station.
    - Source Health = network, auth, latency, and contract compliance of the upstream API/feed.
    """
    model_config = ConfigDict(populate_by_name=True)

    provider: str = Field(..., description="Provider identifier (e.g. open_meteo, imd_aws)")
    is_reachable: bool = Field(default=True, description="Whether the upstream API endpoint is reachable")
    last_successful_fetch: Optional[datetime] = Field(default=None, description="UTC timestamp of last successful 200 OK")
    last_attempt_timestamp: Optional[datetime] = Field(default=None, description="UTC timestamp of last request attempt")
    consecutive_failures: int = Field(default=0, ge=0, description="Count of consecutive request or parse failures")
    last_response_latency_ms: Optional[float] = Field(default=None, ge=0.0, description="HTTP round-trip latency in ms")
    stale_feed_duration_seconds: Optional[float] = Field(default=None, ge=0.0, description="Elapsed time since last valid observation")
    rate_limit_remaining: Optional[int] = Field(default=None, description="Remaining API quota for the window")
    rate_limit_reset_seconds: Optional[int] = Field(default=None, description="Seconds until quota reset")
    authentication_status: str = Field(
        default="UNAUTHENTICATED_OPEN",
        description="Auth state: AUTHENTICATED, UNAUTHENTICATED_OPEN, INVALID_CREDENTIALS, EXPIRED"
    )
    malformed_response_count: int = Field(default=0, ge=0, description="Total count of unparseable or schema-violating responses")
    last_error_message: Optional[str] = Field(default=None, description="Description of the most recent failure")

    def record_success(self, latency_ms: float, timestamp: Optional[datetime] = None) -> None:
        """Record a successful HTTP fetch and response cycle."""
        now = timestamp or datetime.now(timezone.utc)
        self.is_reachable = True
        self.last_successful_fetch = now
        self.last_attempt_timestamp = now
        self.consecutive_failures = 0
        self.last_response_latency_ms = round(latency_ms, 2)
        self.last_error_message = None

    def record_failure(
        self,
        error_msg: str,
        is_malformed: bool = False,
        auth_failed: bool = False,
        timestamp: Optional[datetime] = None
    ) -> None:
        """Record an API, network, or schema validation failure."""
        now = timestamp or datetime.now(timezone.utc)
        self.last_attempt_timestamp = now
        self.consecutive_failures += 1
        if self.consecutive_failures >= 3:
            self.is_reachable = False
        if is_malformed:
            self.malformed_response_count += 1
        if auth_failed:
            self.authentication_status = "INVALID_CREDENTIALS"
        self.last_error_message = error_msg


class QualificationGateResult(BaseModel):
    """Result of evaluating an incoming observation against Phase 11A Quality Gates."""
    model_config = ConfigDict(frozen=True)

    is_qualified: bool
    checks: Dict[str, bool]
    reasons: List[str]
    observation: Optional[WeatherObservation] = None


class LiveSourceQualificationGate:
    """Rigorous qualification gate for incoming live observations."""

    @staticmethod
    def evaluate(
        obs: WeatherObservation,
        pressure_semantics: PressureSemantics = PressureSemantics.MEAN_SEA_LEVEL_PRESSURE,
        expected_station_id: Optional[str] = None
    ) -> QualificationGateResult:
        """Run all Phase 11A quality gates on a normalized observation candidate."""
        checks: Dict[str, bool] = {}
        reasons: List[str] = []

        # 1. Station Identity
        station_valid = bool(obs.station_id and len(obs.station_id.strip()) > 0)
        if expected_station_id and obs.station_id != expected_station_id:
            station_valid = False
            reasons.append(f"Station ID mismatch: got '{obs.station_id}', expected '{expected_station_id}'")
        checks["station_identity_valid"] = station_valid

        # 2. Timestamp Valid & UTC Aware
        ts_valid = obs.timestamp is not None and obs.timestamp.tzinfo is not None
        checks["timestamp_utc_aware"] = ts_valid
        if not ts_valid:
            reasons.append("Observation timestamp missing timezone or not UTC")

        # 3. Latitude Valid
        lat_valid = -90.0 <= obs.latitude <= 90.0
        checks["latitude_valid"] = lat_valid
        if not lat_valid:
            reasons.append(f"Latitude out of bounds: {obs.latitude}")

        # 4. Longitude Valid
        lon_valid = -180.0 <= obs.longitude <= 180.0
        checks["longitude_valid"] = lon_valid
        if not lon_valid:
            reasons.append(f"Longitude out of bounds: {obs.longitude}")

        # 5. Temperature Physically Valid (if present)
        temp_valid = True
        if obs.temperature is not None:
            if obs.temperature < TEMP_PHYSICAL_MIN_C or obs.temperature > TEMP_PHYSICAL_MAX_C:
                temp_valid = False
                reasons.append(f"Temperature {obs.temperature}°C outside physical limits [{TEMP_PHYSICAL_MIN_C}, {TEMP_PHYSICAL_MAX_C}]")
        checks["temperature_physically_valid"] = temp_valid

        # 6. Relative Humidity Valid (if present)
        rh_valid = True
        if obs.humidity is not None:
            if obs.humidity < HUMIDITY_PHYSICAL_MIN_PCT or obs.humidity > HUMIDITY_PHYSICAL_MAX_PCT:
                rh_valid = False
                reasons.append(f"Relative humidity {obs.humidity}% outside valid bounds [0, 100]")
        checks["rh_physically_valid"] = rh_valid

        # 7. Pressure Physically Valid (if present)
        press_valid = True
        if obs.pressure is not None:
            if obs.pressure < PRESSURE_PHYSICAL_MIN_HPA or obs.pressure > PRESSURE_PHYSICAL_MAX_HPA:
                press_valid = False
                reasons.append(f"Sea-level pressure {obs.pressure} hPa outside physical bounds [{PRESSURE_PHYSICAL_MIN_HPA}, {PRESSURE_PHYSICAL_MAX_HPA}]")
        checks["pressure_physically_valid"] = press_valid

        # 8. Pressure Semantics Confirmed
        semantics_confirmed = pressure_semantics in (
            PressureSemantics.MEAN_SEA_LEVEL_PRESSURE,
            PressureSemantics.STATION_SURFACE_PRESSURE,
        )
        if pressure_semantics == PressureSemantics.UNSPECIFIED_OR_UNKNOWN:
            semantics_confirmed = False
            reasons.append("Pressure semantics unconfirmed: cannot assume raw pressure is Sea-Level Pressure without verification")
        checks["pressure_semantics_confirmed"] = semantics_confirmed

        # 9. Physical Consistency (e.g., Dew point <= Temperature if both present)
        consistency_valid = True
        if obs.temperature is not None and obs.dew_point_c is not None:
            if obs.dew_point_c > (obs.temperature + 0.5):  # allow 0.5C margin for measurement noise
                consistency_valid = False
                reasons.append(f"Impossible physical state: dew point ({obs.dew_point_c}°C) > temperature ({obs.temperature}°C)")
        checks["physical_consistency_valid"] = consistency_valid

        # 10. Source Provenance Retained
        provenance_valid = bool(obs.source in (ObservationSource.WEATHER_API, ObservationSource.OPEN_METEO, ObservationSource.NOAA_ISD))
        checks["source_provenance_retained"] = provenance_valid

        is_all_passed = all(checks.values())
        return QualificationGateResult(
            is_qualified=is_all_passed,
            checks=checks,
            reasons=reasons,
            observation=obs if is_all_passed else None
        )


class OpenMeteoQualificationAdapter:
    """Normalizes raw Open-Meteo REST API responses into canonical WeatherObservation objects.
    
    Maps Open-Meteo fields:
      - `time` (ISO 8601 string) -> `timestamp` (UTC datetime)
      - `latitude`, `longitude`, `elevation` -> geodetic coordinates
      - `temperature_2m` (°C) -> `temperature`
      - `relative_humidity_2m` (%) -> `humidity`
      - `pressure_msl` (hPa) -> `pressure` (SLP)
      - `surface_pressure` (hPa) -> `station_pressure_hpa`
      - supplementary fields (wind_speed, precipitation) -> stored in `metadata["source_supplementary"]`
    """

    KNOWN_MISSING_SENTINELS = {-9999.0, -999.0, 999.9, 9999.0, -9999, -999}

    def __init__(
        self,
        default_station_id: str = "OPEN_METEO_DEFAULT",
        default_station_name: Optional[str] = "Open-Meteo AWS Feed",
        source_type: ObservationSource = ObservationSource.OPEN_METEO,
    ) -> None:
        self.default_station_id = default_station_id
        self.default_station_name = default_station_name
        self.source_type = source_type

    @classmethod
    def clean_missing_float(cls, val: Any) -> Optional[float]:
        """Convert null, empty string, NaN, or sentinel numbers to None."""
        if val is None:
            return None
        if isinstance(val, str):
            clean = val.strip()
            if clean in ("", "null", "None", "NaN", "nan", "-9999", "-999", "999.9"):
                return None
            try:
                val = float(clean)
            except ValueError:
                return None
        try:
            num = float(val)
            if math.isnan(num) or math.isinf(num):
                return None
            if num in cls.KNOWN_MISSING_SENTINELS:
                return None
            return num
        except (TypeError, ValueError):
            return None

    @classmethod
    def parse_utc_timestamp(cls, raw_ts: Any) -> datetime:
        """Parse raw timestamp ensuring UTC timezone awareness."""
        if isinstance(raw_ts, datetime):
            if raw_ts.tzinfo is None:
                return raw_ts.replace(tzinfo=timezone.utc)
            return raw_ts.astimezone(timezone.utc)
        if isinstance(raw_ts, str):
            clean = raw_ts.strip().replace("Z", "+00:00")
            parsed = datetime.fromisoformat(clean)
            if parsed.tzinfo is None:
                return parsed.replace(tzinfo=timezone.utc)
            return parsed.astimezone(timezone.utc)
        if isinstance(raw_ts, (int, float)):
            # Unix epoch timestamp
            return datetime.fromtimestamp(raw_ts, tz=timezone.utc)
        raise ValueError(f"Unsupported timestamp format: {raw_ts}")

    def normalize(
        self,
        raw_payload: Dict[str, Any],
        station_id: Optional[str] = None,
        station_name: Optional[str] = None,
        retrieval_timestamp: Optional[datetime] = None,
        pressure_semantics: PressureSemantics = PressureSemantics.MEAN_SEA_LEVEL_PRESSURE
    ) -> List[WeatherObservation]:
        """Normalize an Open-Meteo JSON payload into canonical WeatherObservation instances."""
        ingestion_ts = retrieval_timestamp or datetime.now(timezone.utc)
        target_station_id = station_id or raw_payload.get("station_id") or self.default_station_id
        target_station_name = station_name or raw_payload.get("station_name") or self.default_station_name

        lat = self.clean_missing_float(raw_payload.get("latitude"))
        lon = self.clean_missing_float(raw_payload.get("longitude"))
        elev = self.clean_missing_float(raw_payload.get("elevation"))

        if lat is None or lon is None:
            raise ValueError("Raw payload missing required latitude/longitude coordinates")

        observations: List[WeatherObservation] = []

        # 1. Single observation payload (e.g. 'current' or single object)
        if "current" in raw_payload and isinstance(raw_payload["current"], dict):
            curr = raw_payload["current"]
            ts = self.parse_utc_timestamp(curr.get("time"))
            temp = self.clean_missing_float(curr.get("temperature_2m"))
            humidity = self.clean_missing_float(curr.get("relative_humidity_2m"))
            slp = self.clean_missing_float(curr.get("pressure_msl"))
            surf_press = self.clean_missing_float(curr.get("surface_pressure"))
            dew_point = self.clean_missing_float(curr.get("dew_point_2m"))

            # Capture non-core parameters in metadata for provenance
            supplementary: Dict[str, Any] = {}
            for k in ("wind_speed_10m", "wind_direction_10m", "precipitation", "cloud_cover", "direct_normal_irradiance"):
                if k in curr:
                    val = self.clean_missing_float(curr[k])
                    if val is not None:
                        supplementary[k] = val

            obs = WeatherObservation(
                station_id=target_station_id,
                station_name=target_station_name,
                latitude=lat,
                longitude=lon,
                elevation=elev,
                timestamp=ts,
                temperature=temp,
                dew_point_c=dew_point,
                pressure=slp if pressure_semantics == PressureSemantics.MEAN_SEA_LEVEL_PRESSURE else None,
                station_pressure_hpa=surf_press,
                humidity=humidity,
                relative_humidity_source="direct_sensor" if humidity is not None else None,
                source=self.source_type,
                report_type="LIVE_API_CURRENT",
                raw_quality_flags={"open_meteo_current_interval": curr.get("interval", 900)},
                data_quality_status=QualityStatus.VALID if (temp is not None and humidity is not None and slp is not None) else QualityStatus.SUSPECT,
                ingestion_timestamp=ingestion_ts,
                native_resolution_minutes=float(curr.get("interval", 900)) / 60.0 if curr.get("interval") else 15.0,
                is_synthetic=False,
                metadata={
                    "live_source_provider": "open_meteo",
                    "pressure_semantics": pressure_semantics.value,
                    "source_supplementary": supplementary,
                }
            )
            observations.append(obs)

        # 2. Time series array payload (e.g. 'hourly' or 'minutely_15')
        elif "hourly" in raw_payload and isinstance(raw_payload["hourly"], dict):
            hourly = raw_payload["hourly"]
            times = hourly.get("time", [])
            temps = hourly.get("temperature_2m", [])
            hums = hourly.get("relative_humidity_2m", [])
            mslp_list = hourly.get("pressure_msl", [])
            surf_list = hourly.get("surface_pressure", [])
            dew_list = hourly.get("dew_point_2m", [])

            count = len(times)
            for i in range(count):
                ts = self.parse_utc_timestamp(times[i])
                temp = self.clean_missing_float(temps[i]) if i < len(temps) else None
                hum = self.clean_missing_float(hums[i]) if i < len(hums) else None
                slp = self.clean_missing_float(mslp_list[i]) if i < len(mslp_list) else None
                surf = self.clean_missing_float(surf_list[i]) if i < len(surf_list) else None
                dew = self.clean_missing_float(dew_list[i]) if i < len(dew_list) else None

                supplementary_i: Dict[str, Any] = {}
                for k in ("wind_speed_10m", "wind_direction_10m", "precipitation"):
                    if k in hourly and i < len(hourly[k]):
                        val = self.clean_missing_float(hourly[k][i])
                        if val is not None:
                            supplementary_i[k] = val

                obs = WeatherObservation(
                    station_id=target_station_id,
                    station_name=target_station_name,
                    latitude=lat,
                    longitude=lon,
                    elevation=elev,
                    timestamp=ts,
                    temperature=temp,
                    dew_point_c=dew,
                    pressure=slp if pressure_semantics == PressureSemantics.MEAN_SEA_LEVEL_PRESSURE else None,
                    station_pressure_hpa=surf,
                    humidity=hum,
                    relative_humidity_source="direct_sensor" if hum is not None else None,
                    source=self.source_type,
                    report_type="LIVE_API_HOURLY",
                    raw_quality_flags={},
                    data_quality_status=QualityStatus.VALID if (temp is not None and hum is not None and slp is not None) else QualityStatus.SUSPECT,
                    ingestion_timestamp=ingestion_ts,
                    native_resolution_minutes=60.0,
                    is_synthetic=False,
                    metadata={
                        "live_source_provider": "open_meteo",
                        "pressure_semantics": pressure_semantics.value,
                        "source_supplementary": supplementary_i,
                    }
                )
                observations.append(obs)

        # 3. Flat dictionary payload
        elif "time" in raw_payload:
            ts = self.parse_utc_timestamp(raw_payload["time"])
            temp = self.clean_missing_float(raw_payload.get("temperature_2m") or raw_payload.get("temperature") or raw_payload.get("temp"))
            humidity = self.clean_missing_float(raw_payload.get("relative_humidity_2m") or raw_payload.get("humidity") or raw_payload.get("rh"))
            slp = self.clean_missing_float(raw_payload.get("pressure_msl") or raw_payload.get("pressure") or raw_payload.get("slp"))
            surf_press = self.clean_missing_float(raw_payload.get("surface_pressure") or raw_payload.get("station_pressure"))
            dew_point = self.clean_missing_float(raw_payload.get("dew_point_2m") or raw_payload.get("dew_point"))

            obs = WeatherObservation(
                station_id=target_station_id,
                station_name=target_station_name,
                latitude=lat,
                longitude=lon,
                elevation=elev,
                timestamp=ts,
                temperature=temp,
                dew_point_c=dew_point,
                pressure=slp if pressure_semantics == PressureSemantics.MEAN_SEA_LEVEL_PRESSURE else None,
                station_pressure_hpa=surf_press,
                humidity=humidity,
                relative_humidity_source="direct_sensor" if humidity is not None else None,
                source=self.source_type,
                report_type="LIVE_API_FLAT",
                raw_quality_flags={},
                data_quality_status=QualityStatus.VALID if (temp is not None and humidity is not None and slp is not None) else QualityStatus.SUSPECT,
                ingestion_timestamp=ingestion_ts,
                native_resolution_minutes=15.0,
                is_synthetic=False,
                metadata={
                    "live_source_provider": "open_meteo",
                    "pressure_semantics": pressure_semantics.value,
                }
            )
            observations.append(obs)

        else:
            raise ValueError("Unrecognized Open-Meteo payload structure: missing 'current', 'hourly', or flat 'time' fields")

        return observations
