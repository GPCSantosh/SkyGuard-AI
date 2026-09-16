"""Normalized WeatherObservation schema and data models."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator

from backend.app.core.constants import (
    HUMIDITY_PHYSICAL_MAX_PCT,
    HUMIDITY_PHYSICAL_MIN_PCT,
    PRESSURE_PHYSICAL_MAX_HPA,
    PRESSURE_PHYSICAL_MIN_HPA,
    TEMP_PHYSICAL_MAX_C,
    TEMP_PHYSICAL_MIN_C,
)


class ObservationSource(str, Enum):
    """Origin source for weather telemetry."""
    HISTORICAL_CSV = "HISTORICAL_CSV"
    SIMULATOR = "SIMULATOR"
    WEATHER_API = "WEATHER_API"
    MQTT = "MQTT"
    MANUAL_INJECTION = "MANUAL_INJECTION"


class WeatherObservation(BaseModel):
    """Normalized internal weather observation model.
    
    All incoming data connectors must transform raw payloads into this contract.
    """
    model_config = ConfigDict(
        frozen=True,  # Enforce immutability of observation instances
        str_strip_whitespace=True,
        use_enum_values=True,
    )

    # Station Identification
    station_id: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description="Unique identifier for the Automatic Weather Station"
    )

    # Observation UTC Timestamp
    timestamp: datetime = Field(
        ...,
        description="Observation timestamp in UTC"
    )

    # Primary Meteorological Trio
    temperature: Optional[float] = Field(
        default=None,
        description="Ambient air temperature in Celsius (°C)"
    )
    pressure: Optional[float] = Field(
        default=None,
        description="Atmospheric / barometric surface pressure in hPa"
    )
    humidity: Optional[float] = Field(
        default=None,
        description="Relative humidity percentage (0.0 - 100.0%)"
    )

    # Geospatial Coordinates
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

    # Provenance Metadata
    source: ObservationSource = Field(
        default=ObservationSource.HISTORICAL_CSV,
        description="Ingestion source adapter type"
    )
    ingestion_timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp when record was ingested into SkyGuard"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Arbitrary supplementary hardware/telemetry metadata"
    )

    @field_validator("timestamp", mode="before")
    @classmethod
    def parse_and_validate_timestamp(cls, value: Any) -> datetime:
        """Ensure timestamp is parsed to UTC timezone-aware datetime."""
        if isinstance(value, str):
            # Parse ISO 8601 string
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
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

    @field_validator("pressure")
    @classmethod
    def validate_pressure_bounds(cls, v: Optional[float]) -> Optional[float]:
        """Validate barometric pressure is within physical bounds if present."""
        if v is not None:
            if v < PRESSURE_PHYSICAL_MIN_HPA or v > PRESSURE_PHYSICAL_MAX_HPA:
                raise ValueError(
                    f"Pressure {v} hPa exceeds physical limits [{PRESSURE_PHYSICAL_MIN_HPA}, {PRESSURE_PHYSICAL_MAX_HPA}]"
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
