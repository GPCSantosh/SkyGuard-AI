"""Unified Feature Engineering Pipeline for SkyGuard AI."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence
import numpy as np
import pandas as pd
from pydantic import BaseModel, ConfigDict, Field

from ml.features.change import RateOfChangeExtractor
from ml.features.consistency import ConsistencyExtractor
from ml.features.rolling import RollingWindowExtractor
from ml.features.spatial import SpatialNeighborExtractor
from ml.features.temporal import TemporalFeatureExtractor


class FeaturePipelineConfig(BaseModel):
    """Configuration schema for FeaturePipeline."""
    model_config = ConfigDict(frozen=True)

    time_windows: List[str] = Field(
        default_factory=lambda: ["15min", "30min", "1h", "3h", "6h", "24h"],
        description="Time-aware rolling window intervals"
    )
    lag_steps: List[int] = Field(
        default_factory=lambda: [1, 2, 3],
        description="Discrete observation lag steps"
    )
    parameters: List[str] = Field(
        default_factory=lambda: [
            "temperature_c",
            "relative_humidity_pct",
            "sea_level_pressure_hpa",
            "station_pressure_hpa",
        ],
        description="Physical telemetry parameters to extract features for"
    )
    consistency_reference_window: str = Field(
        default="1h",
        description="Rolling window key for deviation and z-score calculations"
    )
    enable_spatial_features: bool = Field(
        default=True,
        description="Whether to compute geodesic spatial neighbor features"
    )
    spatial_max_distance_km: float = Field(
        default=600.0,
        description="Maximum radius for geodesic neighborhood detection"
    )
    spatial_max_neighbors: int = Field(
        default=5,
        description="Maximum number of nearest neighbors"
    )


class FeaturePipeline:
    """Orchestrates end-to-end feature extraction over single-station or multi-station datasets.
    
    Guarantees strict auditability, deterministic computation, and zero data leakage.
    """

    # Reserved metadata columns preserved for traceability but excluded from ML training vectors
    METADATA_COLUMNS: List[str] = [
        "station_id",
        "station_name",
        "timestamp",
        "latitude",
        "longitude",
        "elevation_m",
        "source",
        "report_type",
        "data_quality_status",
        "raw_quality_flags",
        "is_synthetic",
        "ingestion_timestamp",
    ]

    def __init__(
        self,
        config: Optional[FeaturePipelineConfig] = None,
        station_metadata: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> None:
        """Initialize FeaturePipeline with configuration and spatial metadata."""
        self.config = config or FeaturePipelineConfig()
        self.station_metadata = station_metadata or {}

        # Initialize sub-extractors
        self.temporal_extractor = TemporalFeatureExtractor()
        self.rolling_extractor = RollingWindowExtractor(
            time_windows=self.config.time_windows,
            lag_steps=self.config.lag_steps,
            parameters=self.config.parameters,
        )
        self.change_extractor = RateOfChangeExtractor(
            parameters=self.config.parameters
        )
        self.consistency_extractor = ConsistencyExtractor(
            parameters=[p for p in self.config.parameters if p != "station_pressure_hpa"],
            rolling_reference_window=self.config.consistency_reference_window,
        )
        self.spatial_extractor = SpatialNeighborExtractor(
            station_metadata=self.station_metadata,
            max_distance_km=self.config.spatial_max_distance_km,
            max_neighbors=self.config.spatial_max_neighbors,
        )

    def transform(
        self,
        df: pd.DataFrame,
        timestamp_col: str = "timestamp",
        station_id_col: str = "station_id",
    ) -> pd.DataFrame:
        """Execute full feature extraction pipeline on the input dataset.
        
        Args:
            df: Raw or normalized observations DataFrame.
            timestamp_col: Timestamp column identifier.
            station_id_col: Station ID column identifier.
            
        Returns:
            DataFrame containing preserved raw telemetry + comprehensive engineered features.
        """
        if df.empty:
            return df.copy()

        result = df.copy()

        # Handle column alias normalization if necessary
        alias_map = {
            "temperature": "temperature_c",
            "pressure": "sea_level_pressure_hpa",
            "humidity": "relative_humidity_pct",
            "elevation": "elevation_m",
        }
        for old_col, new_col in alias_map.items():
            if old_col in result.columns and new_col not in result.columns:
                result[new_col] = result[old_col]

        # Ensure timestamp is UTC datetime
        result[timestamp_col] = pd.to_datetime(result[timestamp_col], utc=True)

        # 1. Temporal & Cyclical features (independent of station grouping)
        result = self.temporal_extractor.extract_features(result, timestamp_col=timestamp_col)

        # 2. Station-wise temporal series processing (Rolling, Rates, Persistence, Deviations)
        station_dfs: List[pd.DataFrame] = []
        if station_id_col in result.columns:
            for _, station_group in result.groupby(station_id_col):
                # Sort chronologically per station
                stn_df = station_group.sort_values(by=timestamp_col).reset_index(drop=True)
                # A. Rolling windows and lags
                stn_df = self.rolling_extractor.extract_features(stn_df, timestamp_col=timestamp_col)
                # B. Rate of change and acceleration
                stn_df = self.change_extractor.extract_features(stn_df, timestamp_col=timestamp_col)
                # C. Persistence, Deviations, and Multivariate consistency
                stn_df = self.consistency_extractor.extract_features(stn_df, timestamp_col=timestamp_col)
                station_dfs.append(stn_df)
            result = pd.concat(station_dfs, ignore_index=True)
        else:
            result = result.sort_values(by=timestamp_col).reset_index(drop=True)
            result = self.rolling_extractor.extract_features(result, timestamp_col=timestamp_col)
            result = self.change_extractor.extract_features(result, timestamp_col=timestamp_col)
            result = self.consistency_extractor.extract_features(result, timestamp_col=timestamp_col)

        # 3. Spatial neighborhood features (across stations)
        if self.config.enable_spatial_features and station_id_col in result.columns:
            result = self.spatial_extractor.extract_features_multi_station(
                result,
                timestamp_col=timestamp_col,
                station_id_col=station_id_col,
            )

        return result

    def get_feature_columns(self, df: pd.DataFrame) -> List[str]:
        """Return list of purely numerical/categorical ML feature column names, excluding metadata.
        
        Guarantees no ground truth or raw identifier leakage into model inputs.
        """
        excluded = set(self.METADATA_COLUMNS)
        excluded.update([
            "ground_truth", "ground_truth_label", "anomaly_id", "anomaly_type",
            "original_value", "modified_value", "injection_start", "injection_end",
            "severity_parameter", "is_fault"
        ])
        return [col for col in df.columns if col not in excluded and not col.startswith("_")]
