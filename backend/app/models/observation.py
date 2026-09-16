"""Normalized WeatherObservation schema and data models for SkyGuard AI."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from backend.app.core.constants import (
    HUMIDITY_PHYSICAL_MAX_PCT,
    HUMIDITY_PHYSICAL_MIN_PCT,
    PRESSURE_PHYSICAL_MAX_HPA,
    PRESSURE_PHYSICAL_MIN_HPA,
    TEMP_PHYSICAL_MAX_C,
    TEMP_PHYSICAL_MIN_C,
)


class QualityStatus(str, Enum):
    """Normalized data quality classification state."""
    VALID = "VALID"
    SUSPECT = "SUSPECT"
    ERROR = "ERROR"
    MISSING = "MISSING"
    UNKNOWN = "UNKNOWN"


class ObservationSource(str, Enum):
    """Origin source for weather telemetry."""
    HISTORICAL_CSV = "HISTORICAL_CSV"
    NOAA_ISD = "NOAA_ISD"
    METEOSTAT = "METEOSTAT"
    OPEN_METEO = "OPEN_METEO"
    SIMULATOR = "SIMULATOR"
    WEATHER_API = "WEATHER_API"
    MQTT = "MQTT"
    MANUAL_INJECTION = "MANUAL_INJECTION"


class WeatherObservation(BaseModel):
    """Normalized canonical weather observation model.
    
    All incoming data connectors and parsers must transform raw payloads
    into this contract while preserving raw provenance and quality metadata.
    """
    model_config = ConfigDict(
        frozen=True,  # Enforce immutability of raw observation instances
        str_strip_whitespace=True,
        use_enum_values=True,
        populate_by_name=True,
        validate_default=True,
    )

    # Station Identification & Geospatial Topology
    station_id: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description="Unique identifier for the Automatic Weather Station"
    )
    station_name: Optional[str] = Field(
        default=None,
        description="Descriptive name or location of the station"
    )
    latitude: float = Field(
        ...,
        ge=-90.0,
        le=90.0,
        description="Geodetic latitude in decimal degrees"
    )
    longitude: float = Field(
        ...,
        ge=-180.0,
        le=180.0,
        description="Geodetic longitude in decimal degrees"
    )
    elevation: Optional[float] = Field(
        default=None,
        ge=-500.0,
        le=9000.0,
        description="Station elevation above sea level in meters"
    )

    # Observation UTC Timestamp
    timestamp: datetime = Field(
        ...,
        description="Observation timestamp in timezone-aware UTC"
    )

    # Primary Meteorological Trio & Derived Parameters
    temperature: Optional[float] = Field(
        default=None,
        description="Ambient air temperature in Celsius (°C)"
    )
    dew_point_c: Optional[float] = Field(
        default=None,
        description="Dew point temperature in Celsius (°C)"
    )
    pressure: Optional[float] = Field(
        default=None,
        description="Sea-Level barometric pressure (SLP) in hPa"
    )
    station_pressure_hpa: Optional[float] = Field(
        default=None,
        description="Atmospheric station / surface pressure in hPa"
    )
    humidity: Optional[float] = Field(
        default=None,
        description="Relative humidity percentage (0.0 - 100.0%)"
    )
    relative_humidity_source: Optional[str] = Field(
        default=None,
        description="Source/derivation indicator: 'direct_sensor' or 'derived_from_temperature_and_dew_point'"
    )

    # Provenance, Quality & Cadence Metadata
    source: ObservationSource = Field(
        default=ObservationSource.HISTORICAL_CSV,
        description="Ingestion source adapter type"
    )
    report_type: Optional[str] = Field(
        default=None,
        description="Source report type (e.g., FM-12, FM-15, METAR, AUTO)"
    )
    raw_quality_flags: Dict[str, Any] = Field(
        default_factory=dict,
        description="Preserved raw source quality control codes (e.g. NOAA ISD QC codes)"
    )
    data_quality_status: QualityStatus = Field(
        default=QualityStatus.UNKNOWN,
        description="Overall normalized data quality status"
    )
    ingestion_timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp when record was ingested into SkyGuard"
    )
    native_resolution_minutes: Optional[float] = Field(
        default=None,
        description="Estimated native sampling resolution in minutes"
    )
    is_synthetic: bool = Field(
        default=False,
        description="Flag indicating whether observation is simulated/interpolated"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Arbitrary supplementary hardware/telemetry metadata"
    )

    @model_validator(mode="before")
    @classmethod
    def normalize_aliases(cls, data: Any) -> Any:
        """Map canonical field aliases (e.g. temperature_c -> temperature) if provided in dict format."""
        if isinstance(data, dict):
            if "temperature_c" in data and "temperature" not in data:
                data["temperature"] = data.pop("temperature_c")
            if "sea_level_pressure_hpa" in data and "pressure" not in data:
                data["pressure"] = data.pop("sea_level_pressure_hpa")
            if "relative_humidity_pct" in data and "humidity" not in data:
                data["humidity"] = data.pop("relative_humidity_pct")
            if "elevation_m" in data and "elevation" not in data:
                data["elevation"] = data.pop("elevation_m")
        return data

    @property
    def temperature_c(self) -> Optional[float]:
        """Convenience property for temperature in °C."""
        return self.temperature

    @property
    def sea_level_pressure_hpa(self) -> Optional[float]:
        """Convenience property for sea-level pressure in hPa."""
        return self.pressure

    @property
    def relative_humidity_pct(self) -> Optional[float]:
        """Convenience property for relative humidity in %."""
        return self.humidity

    @property
    def elevation_m(self) -> Optional[float]:
        """Convenience property for elevation in meters."""
        return self.elevation

    @field_validator("timestamp", mode="before")
    @classmethod
    def parse_and_validate_timestamp(cls, value: Any) -> datetime:
        """Ensure timestamp is parsed to UTC timezone-aware datetime."""
        if isinstance(value, str):
            # Parse ISO 8601 string, handling Z and offset notations
            clean_str = value.replace("Z", "+00:00")
            parsed = datetime.fromisoformat(clean_str)
            if parsed.tzinfo is None:
                return parsed.replace(tzinfo=timezone.utc)
            return parsed.astimezone(timezone.utc)
        elif isinstance(value, datetime):
            if value.tzinfo is None:
                return value.replace(tzinfo=timezone.utc)
            return value.astimezone(timezone.utc)
        raise ValueError(f"Invalid timestamp format: {value}")

    @field_validator("temperature")
    @classmethod
    def validate_temperature_bounds(cls, v: Optional[float]) -> Optional[float]:
        """Validate temperature is within physical bounds if present."""
        if v is not None:
            if v < TEMP_PHYSICAL_MIN_C or v > TEMP_PHYSICAL_MAX_C:
                raise ValueError(
                    f"Temperature {v}°C exceeds physical limits [{TEMP_PHYSICAL_MIN_C}, {TEMP_PHYSICAL_MAX_C}]"
                )
        return v

    @field_validator("dew_point_c")
    @classmethod
    def validate_dew_point_bounds(cls, v: Optional[float]) -> Optional[float]:
        """Validate dew point is within physical limits if present."""
        if v is not None:
            if v < -80.0 or v > 60.0:
                raise ValueError(
                    f"Dew point {v}°C exceeds physical limits [-80.0, 60.0]"
                )
        return v

    @field_validator("pressure")
    @classmethod
    def validate_pressure_bounds(cls, v: Optional[float]) -> Optional[float]:
        """Validate sea-level barometric pressure is within physical bounds if present."""
        if v is not None:
            if v < PRESSURE_PHYSICAL_MIN_HPA or v > PRESSURE_PHYSICAL_MAX_HPA:
                raise ValueError(
                    f"Pressure {v} hPa exceeds physical limits [{PRESSURE_PHYSICAL_MIN_HPA}, {PRESSURE_PHYSICAL_MAX_HPA}]"
                )
        return v

    @field_validator("station_pressure_hpa")
    @classmethod
    def validate_station_pressure_bounds(cls, v: Optional[float]) -> Optional[float]:
        """Validate station barometric pressure is within physical bounds if present."""
        if v is not None:
            # Accommodate high altitude stations down to 300 hPa
            if v < 300.0 or v > PRESSURE_PHYSICAL_MAX_HPA:
                raise ValueError(
                    f"Station pressure {v} hPa exceeds physical limits [300.0, {PRESSURE_PHYSICAL_MAX_HPA}]"
                )
        return v

    @field_validator("humidity")
    @classmethod
    def validate_humidity_bounds(cls, v: Optional[float]) -> Optional[float]:
        """Validate relative humidity is within physical bounds [0, 100]% if present."""
        if v is not None:
            if v < HUMIDITY_PHYSICAL_MIN_PCT or v > HUMIDITY_PHYSICAL_MAX_PCT:
                raise ValueError(
                    f"Relative humidity {v}% exceeds physical limits [{HUMIDITY_PHYSICAL_MIN_PCT}, {HUMIDITY_PHYSICAL_MAX_PCT}]"
                )
        return v


class ImputedObservation(BaseModel):
    """Model-derived or imputed observation value.
    
    Stored strictly separately from the immutable raw WeatherObservation.
    """
    model_config = ConfigDict(frozen=True)

    station_id: str
    timestamp: datetime
    parameter: str  # 'temperature' | 'pressure' | 'humidity'
    original_value: Optional[float]
    imputed_value: float
    imputation_method: str
    model_version: str
    confidence: float = Field(ge=0.0, le=1.0)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
