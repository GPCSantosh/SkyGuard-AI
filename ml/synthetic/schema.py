"""Schemas and data models for synthetic anomaly injection and ground truth registry."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
import pandas as pd
from pydantic import BaseModel, ConfigDict, Field


class SyntheticAnomalyType(str, Enum):
    """The 15 operational synthetic anomaly taxonomy categories + evaluation scenarios."""
    # 15 Operational Fault Categories
    SPIKE = "SPIKE"
    SMALL_SPIKE = "SMALL_SPIKE"
    NEGATIVE_SPIKE = "NEGATIVE_SPIKE"
    DRIFT = "DRIFT"
    OFFSET = "OFFSET"
    FROZEN_SENSOR = "FROZEN_SENSOR"
    INTERMITTENT_FREEZE = "INTERMITTENT_FREEZE"
    MISSING_DATA = "MISSING_DATA"
    COMMUNICATION_GAP = "COMMUNICATION_GAP"
    DUPLICATE_DATA = "DUPLICATE_DATA"
    OUT_OF_ORDER_DATA = "OUT_OF_ORDER_DATA"
    RANDOM_NOISE = "RANDOM_NOISE"
    MULTIVARIATE_INCONSISTENCY = "MULTIVARIATE_INCONSISTENCY"
    MULTI_SENSOR_FAULT = "MULTI_SENSOR_FAULT"
    COMBINED_FAULT = "COMBINED_FAULT"

    # Evaluation Reference Scenarios (Non-faults)
    POSSIBLE_GENUINE_EVENT = "POSSIBLE_GENUINE_EVENT"
    UNCERTAIN = "UNCERTAIN"


class GroundTruthRecord(BaseModel):
    """Standardized evaluation ground-truth label entry.
    
    CRITICAL: Stored in a separate registry and never passed into ML feature matrices.
    """
    model_config = ConfigDict(frozen=True)

    anomaly_id: str = Field(
        ...,
        description="Unique identifier for the anomaly event (e.g. ANOM-000001)"
    )
    station_id: str = Field(
        ...,
        description="Target Automatic Weather Station ID"
    )
    timestamp: datetime = Field(
        ...,
        description="Observation timestamp where the injection occurred"
    )
    anomaly_type: SyntheticAnomalyType = Field(
        ...,
        description="Taxonomy classification of the injected anomaly or event"
    )
    affected_variable: str = Field(
        ...,
        description="Sensor variable affected (e.g. 'temperature_c', 'relative_humidity_pct', 'all')"
    )
    original_value: Optional[float] = Field(
        default=None,
        description="Pristine pre-injection sensor value"
    )
    modified_value: Optional[float] = Field(
        default=None,
        description="Corrupted post-injection sensor value"
    )
    injection_start: datetime = Field(
        ...,
        description="Start timestamp of the anomaly episode"
    )
    injection_end: datetime = Field(
        ...,
        description="End timestamp of the anomaly episode"
    )
    severity_parameter: float = Field(
        default=1.0,
        description="Parameterized magnitude, slope, or noise level"
    )
    ground_truth_label: int = Field(
        default=1,
        description="Binary label for benchmark evaluation (1 = Sensor Fault, 0 = Nominal or Genuine Event)"
    )
    is_fault: bool = Field(
        default=True,
        description="True for hardware/data faults; False for genuine physical meteorological events"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Supplementary details regarding injection parameters"
    )


class AnomalyInjectionConfig(BaseModel):
    """Configuration for an anomaly injection experiment."""
    model_config = ConfigDict(frozen=True)

    seed: int = Field(default=42, description="Deterministic random seed")
    experiment_id: str = Field(default_factory=lambda: f"EXP_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}")
    target_stations: Optional[List[str]] = Field(default=None, description="Subset of stations to inject faults into")
    anomalies_to_inject: List[SyntheticAnomalyType] = Field(
        default_factory=lambda: list(SyntheticAnomalyType),
        description="List of anomaly types to inject"
    )
    num_anomalies_per_type: int = Field(default=2, ge=1)
    config_file_path: Optional[str] = Field(default="configs/anomalies.yaml")


class InjectedDatasetResult:
    """Encapsulates the output of a synthetic injection run."""

    def __init__(
        self,
        modified_df: pd.DataFrame,
        ground_truth_df: pd.DataFrame,
        experiment_id: str,
        seed: int,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.modified_df = modified_df
        self.ground_truth_df = ground_truth_df
        self.experiment_id = experiment_id
        self.seed = seed
        self.metadata = metadata or {}

    @property
    def total_injected_records(self) -> int:
        return len(self.ground_truth_df)

    def summary(self) -> str:
        counts = (
            self.ground_truth_df["anomaly_type"].value_counts().to_dict()
            if not self.ground_truth_df.empty
            else {}
        )
        return (
            f"Experiment ID: {self.experiment_id} (Seed: {self.seed})\n"
            f"Modified Records: {len(self.modified_df):,}\n"
            f"Ground Truth Anomalies: {len(self.ground_truth_df):,}\n"
            f"Distribution: {counts}"
        )
