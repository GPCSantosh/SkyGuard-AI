"""Canonical RunContext Schema and Data Source Specifications for SkyGuard AI."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional
from pydantic import BaseModel, ConfigDict, Field


class DataSourceType(str, Enum):
    """Canonical data source origin classifications."""
    SYNTHETIC_VALIDATION = "SYNTHETIC_VALIDATION"
    HISTORICAL_CSV = "HISTORICAL_CSV"
    OPEN_METEO = "OPEN_METEO"
    IMD_AWS = "IMD_AWS"
    VISUAL_CROSSING = "VISUAL_CROSSING"


class RunMode(str, Enum):
    """Execution and processing mode for data sources."""
    SYNTHETIC_REPLAY = "SYNTHETIC_REPLAY"
    HISTORICAL_ANALYSIS = "HISTORICAL_ANALYSIS"
    HISTORICAL_REPLAY = "HISTORICAL_REPLAY"
    LIVE_MONITORING = "LIVE_MONITORING"


class TransportType(str, Enum):
    """Transport protocol delivering observations to frontend/consumers."""
    WEBSOCKET = "WEBSOCKET"
    LOCAL = "LOCAL"
    REST = "REST"


class RunStatus(str, Enum):
    """Active execution state of a RunContext."""
    IDLE = "IDLE"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    ERROR = "ERROR"


class RunContext(BaseModel):
    """Canonical RunContext representing active execution context across pipeline and UI."""
    model_config = ConfigDict(
        use_enum_values=True,
        populate_by_name=True,
        str_strip_whitespace=True,
    )

    run_id: str = Field(..., description="Unique run tracking identifier (e.g. RUN-20260917-001)")
    source_type: DataSourceType = Field(..., description="Data source origin type")
    source_name: str = Field(..., description="Human-readable data source name (e.g. 'Synthetic Benchmark')")
    mode: RunMode = Field(..., description="Execution mode")
    dataset_id: str = Field(..., description="Identifier for dataset or feed")
    dataset_version: str = Field(default="1.0.0", description="Dataset or connector version")
    station_count: int = Field(default=0, ge=0, description="Total stations in run context")
    observation_count: int = Field(default=0, ge=0, description="Total observations in run dataset")
    cadence: str = Field(default="5m", description="Sampling cadence (e.g. '5 minutes')")
    start_time: Optional[datetime] = Field(default=None, description="Start timestamp of observation window")
    end_time: Optional[datetime] = Field(default=None, description="End timestamp of observation window")
    ground_truth_available: bool = Field(default=False, description="Flag indicating if evaluation labels exist")
    replay_speed: float = Field(default=1.0, ge=1.0, le=300.0, description="Replay speed multiplier (1x, 10x, 60x, 300x)")
    current_synthetic_time: Optional[datetime] = Field(default=None, description="Current simulated UTC timestamp during replay")
    current_observation_index: int = Field(default=0, ge=0, description="Index of currently emitted observation")
    transport: TransportType = Field(default=TransportType.WEBSOCKET, description="Primary transport mode")
    database_target: str = Field(default="isolated_db", description="Storage isolation target or schema filter")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Run initialization timestamp")
    status: RunStatus = Field(default=RunStatus.IDLE, description="Current execution state")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Supplementary context details (e.g. seed, scenario stats)")


class SourceSelectRequest(BaseModel):
    """Payload for selecting a new data source and mode."""
    source_type: DataSourceType
    mode: RunMode
    dataset_id: Optional[str] = None
    config: Dict[str, Any] = Field(default_factory=dict)


class ReplayControlRequest(BaseModel):
    """Payload for replay controls (speed, step, scenario)."""
    action: str = Field(..., description="'start' | 'pause' | 'reset' | 'step' | 'set_speed' | 'load_scenario'")
    speed: Optional[float] = Field(default=None, ge=1.0, le=300.0)
    scenario_id: Optional[str] = None
    step_count: Optional[int] = Field(default=1, ge=1)
