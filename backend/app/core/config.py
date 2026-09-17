"""Configuration management for SkyGuard AI.

Loads default configuration from YAML files with runtime environment variable overrides.
"""

from __future__ import annotations

import functools
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import yaml
from pydantic import AliasChoices, BaseModel, ConfigDict, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def get_project_root() -> Path:
    """Return the absolute path to the project root directory."""
    return Path(__file__).resolve().parents[3]


class SystemSettings(BaseModel):
    """System identification settings."""
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    project_name: str = "SkyGuard AI"
    version: str = "0.1.0"
    environment: str = "development"
    log_level: str = "INFO"


class TelemetrySettings(BaseModel):
    """Telemetry and sampling interval settings."""
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    default_sampling_interval_seconds: int = Field(
        default=300,
        description="Default observation cadence in seconds (300s = 5 minutes)"
    )
    allowed_sampling_intervals_seconds: List[int] = Field(
        default_factory=lambda: [60, 300, 600, 900, 1800, 3600]
    )
    missing_data_timeout_multiplier: float = 2.5
    out_of_order_tolerance_seconds: int = 600


class SpatialSettings(BaseModel):
    """Geospatial calculation settings."""
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    geodesic_distance_metric: str = "haversine"
    default_neighbor_radius_km: float = 150.0
    max_neighbors_for_consensus: int = 5
    min_neighbors_required: int = 2
    elevation_lapse_rate_c_per_km: float = 6.5


class PipelineSettings(BaseModel):
    """Data processing and feature engineering settings."""
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    sliding_windows_minutes: List[int] = Field(
        default_factory=lambda: [15, 60, 360, 1440]
    )
    batch_size: int = 1000
    enable_imputation: bool = True
    imputation_strategy: str = "idw_spatial_temporal"


class StorageSettings(BaseModel):
    """Database and file storage settings."""
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    database_type: str = "sqlite"
    database_url: str = "sqlite:///./data/skyguard_dev.db"
    raw_retention_days: int = -1
    quality_retention_days: int = -1


class ModelSettings(BaseModel):
    """ML model and registry settings."""
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    registry_dir: str = "models/registry"
    active_version: str = "v0.1.0_baseline"
    anomaly_score_threshold: float = 0.75
    min_anomaly_cluster_size: int = 1


class LiveSourceSettings(BaseModel):
    """Live Weather / AWS API source qualification and ingestion configuration."""
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    enabled: bool = Field(
        default=False,
        description="Whether live external API ingestion is enabled"
    )
    provider: str = Field(
        default="open_meteo",
        description="Live API provider identifier (e.g. open_meteo, noaa_live, imd_aws, generic_rest)"
    )
    base_url: str = Field(
        default="https://api.open-meteo.com/v1",
        description="Base HTTP REST API endpoint for the live weather source"
    )
    api_key: Optional[str] = Field(
        default=None,
        description="Optional authentication API key/token (never logged or serialized)"
    )
    timeout_seconds: float = Field(
        default=10.0,
        ge=1.0,
        le=60.0,
        description="HTTP request timeout in seconds"
    )
    poll_interval_seconds: int = Field(
        default=900,
        ge=60,
        le=86400,
        description="Live observation polling cadence in seconds (900s = 15min)"
    )
    retry_limit: int = Field(
        default=3,
        ge=0,
        le=10,
        description="Maximum consecutive retry attempts on transient network failure"
    )
    rate_limit_per_minute: int = Field(
        default=60,
        ge=1,
        le=1000,
        description="Maximum permitted requests per minute against the provider API"
    )
    pressure_product_type: str = Field(
        default="msl",
        description="Expected pressure product semantics: 'msl' (sea-level) or 'surface' (station elevation)"
    )


class AppSettings(BaseSettings):
    """Master application configuration with environment variable support."""
    
    model_config = SettingsConfigDict(
        env_prefix="SKYGUARD_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    # Core environment overrides
    env: str = Field(
        default="development",
        validation_alias=AliasChoices("SKYGUARD_ENV", "env")
    )
    debug: bool = Field(
        default=True,
        validation_alias=AliasChoices("SKYGUARD_DEBUG", "debug")
    )
    log_level: str = Field(
        default="INFO",
        validation_alias=AliasChoices("SKYGUARD_LOG_LEVEL", "log_level")
    )
    
    # API server settings
    api_host: str = Field(
        default="127.0.0.1",
        validation_alias=AliasChoices("SKYGUARD_API_HOST", "api_host")
    )
    api_port: int = Field(
        default=8000,
        validation_alias=AliasChoices("SKYGUARD_API_PORT", "api_port")
    )
    api_reload: bool = Field(
        default=True,
        validation_alias=AliasChoices("SKYGUARD_API_RELOAD", "api_reload")
    )
    api_prefix: str = Field(
        default="/api/v1",
        validation_alias=AliasChoices("SKYGUARD_API_PREFIX", "api_prefix")
    )

    # Cadence override
    observation_interval_seconds: int = Field(
        default=300,
        validation_alias=AliasChoices(
            "SKYGUARD_OBSERVATION_INTERVAL_SECONDS",
            "observation_interval_seconds"
        ),
        description="Observation interval in seconds (default: 300s / 5min)"
    )

    # Database URL
    database_url: str = Field(
        default="sqlite:///./data/skyguard_dev.db",
        validation_alias=AliasChoices("SKYGUARD_DATABASE_URL", "database_url")
    )

    # Sub-component configurations
    system: SystemSettings = Field(default_factory=SystemSettings)
    telemetry: TelemetrySettings = Field(default_factory=TelemetrySettings)
    spatial: SpatialSettings = Field(default_factory=SpatialSettings)
    pipeline: PipelineSettings = Field(default_factory=PipelineSettings)
    storage: StorageSettings = Field(default_factory=StorageSettings)
    model: ModelSettings = Field(default_factory=ModelSettings)
    live_source: LiveSourceSettings = Field(default_factory=LiveSourceSettings)


def load_yaml_config(config_path: Optional[Union[Path, str]] = None) -> Dict[str, Any]:
    """Load configuration from a YAML file if it exists."""
    if config_path is None:
        target_path = get_project_root() / "configs" / "default.yaml"
    else:
        target_path = Path(config_path)
        if not target_path.is_absolute() and not target_path.exists():
            target_path = get_project_root() / config_path

    if target_path.is_file():
        with open(target_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
            return data if isinstance(data, dict) else {}
    return {}


def get_settings(config_file: Optional[str] = None) -> AppSettings:
    """Factory function to build AppSettings merged with YAML defaults and env vars."""
    yaml_data = load_yaml_config(config_file)
    
    # Instantiate sub-models if present in YAML
    init_kwargs: Dict[str, Any] = {}
    if "system" in yaml_data:
        init_kwargs["system"] = SystemSettings(**yaml_data["system"])
    if "telemetry" in yaml_data:
        init_kwargs["telemetry"] = TelemetrySettings(**yaml_data["telemetry"])
    if "spatial" in yaml_data:
        init_kwargs["spatial"] = SpatialSettings(**yaml_data["spatial"])
    if "pipeline" in yaml_data:
        init_kwargs["pipeline"] = PipelineSettings(**yaml_data["pipeline"])
    if "storage" in yaml_data:
        init_kwargs["storage"] = StorageSettings(**yaml_data["storage"])
    if "model" in yaml_data:
        init_kwargs["model"] = ModelSettings(**yaml_data["model"])
    if "live_source" in yaml_data:
        init_kwargs["live_source"] = LiveSourceSettings(**yaml_data["live_source"])

    settings = AppSettings(**init_kwargs)

    # Synchronize top-level observation interval with telemetry sub-model if needed
    if "SKYGUARD_OBSERVATION_INTERVAL_SECONDS" in os.environ:
        val = int(os.environ["SKYGUARD_OBSERVATION_INTERVAL_SECONDS"])
        settings.observation_interval_seconds = val
        settings.telemetry.default_sampling_interval_seconds = val
    elif "telemetry" in yaml_data and "default_sampling_interval_seconds" in yaml_data["telemetry"]:
        settings.observation_interval_seconds = yaml_data["telemetry"]["default_sampling_interval_seconds"]

    # Environment variable overrides for live source
    if "SKYGUARD_LIVE_SOURCE_ENABLED" in os.environ:
        settings.live_source.enabled = os.environ["SKYGUARD_LIVE_SOURCE_ENABLED"].lower() in ("true", "1", "yes")
    if "SKYGUARD_LIVE_SOURCE_BASE_URL" in os.environ:
        settings.live_source.base_url = os.environ["SKYGUARD_LIVE_SOURCE_BASE_URL"]
    if "SKYGUARD_LIVE_SOURCE_API_KEY" in os.environ:
        settings.live_source.api_key = os.environ["SKYGUARD_LIVE_SOURCE_API_KEY"]
    if "SKYGUARD_LIVE_SOURCE_TIMEOUT_SECONDS" in os.environ:
        settings.live_source.timeout_seconds = float(os.environ["SKYGUARD_LIVE_SOURCE_TIMEOUT_SECONDS"])
    if "SKYGUARD_LIVE_SOURCE_POLL_INTERVAL_SECONDS" in os.environ:
        settings.live_source.poll_interval_seconds = int(os.environ["SKYGUARD_LIVE_SOURCE_POLL_INTERVAL_SECONDS"])
    if "SKYGUARD_LIVE_SOURCE_RETRY_LIMIT" in os.environ:
        settings.live_source.retry_limit = int(os.environ["SKYGUARD_LIVE_SOURCE_RETRY_LIMIT"])
    if "SKYGUARD_LIVE_SOURCE_PRESSURE_PRODUCT_TYPE" in os.environ:
        settings.live_source.pressure_product_type = os.environ["SKYGUARD_LIVE_SOURCE_PRESSURE_PRODUCT_TYPE"]

    return settings


