"""Data models and schemas for the Spatial & Synoptic Context Engine."""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict


class SpatialContextCategory(str, Enum):
    """Categorization of spatial context evidence around a target observation."""
    LOCAL_ONLY = "LOCAL_ONLY"
    LOCAL_CLUSTER = "LOCAL_CLUSTER"
    REGIONAL_PATTERN = "REGIONAL_PATTERN"
    INSUFFICIENT_CONTEXT = "INSUFFICIENT_CONTEXT"


class NeighborObservationRecord(BaseModel):
    """Snapshot of a neighbor station's observation matched to a target observation."""
    model_config = ConfigDict(frozen=True)

    station_id: str = Field(..., description="Unique station identifier of the neighbor.")
    timestamp: Optional[str] = Field(None, description="ISO timestamp of neighbor observation.")
    distance_km: float = Field(..., ge=0.0, description="Geodesic distance from target station in km.")
    bearing_deg: float = Field(..., ge=0.0, le=360.0, description="Compass bearing from target station (0-360°).")
    elevation_diff_m: float = Field(..., description="Elevation difference in meters (neighbor - target).")
    time_delta_seconds: Optional[float] = Field(None, description="Time offset in seconds (neighbor_t - target_t).")
    temperature_c: Optional[float] = Field(None, description="Surface temperature in °C.")
    relative_humidity_pct: Optional[float] = Field(None, ge=0.0, le=100.0, description="Relative humidity in %.")
    sea_level_pressure_hpa: Optional[float] = Field(None, description="Mean sea-level pressure in hPa.")
    is_stale: bool = Field(False, description="True if observation falls outside temporal tolerance.")


class VariableConsensus(BaseModel):
    """Statistical consensus metrics for a single meteorological variable across neighbors."""
    model_config = ConfigDict(frozen=True)

    variable_name: str = Field(..., description="Name of the meteorological variable.")
    target_value: Optional[float] = Field(None, description="Value observed at target station.")
    target_delta_prev: Optional[float] = Field(None, description="Target station's change from its own prior reading.")
    
    # Basic neighbor distribution statistics
    neighbor_count: int = Field(0, ge=0, description="Number of valid active neighbors contributing.")
    neighbor_mean: Optional[float] = Field(None, description="Arithmetic mean across valid neighbors.")
    neighbor_median: Optional[float] = Field(None, description="Median across valid neighbors.")
    neighbor_std: Optional[float] = Field(None, ge=0.0, description="Sample standard deviation across neighbors.")
    neighbor_min: Optional[float] = Field(None, description="Minimum neighbor value.")
    neighbor_max: Optional[float] = Field(None, description="Maximum neighbor value.")
    
    # Target relative differences
    target_minus_mean: Optional[float] = Field(None, description="Target value minus neighbor mean.")
    target_minus_median: Optional[float] = Field(None, description="Target value minus neighbor median.")
    target_zscore: Optional[float] = Field(None, description="Standard score of target vs neighbor distribution.")
    
    # Value level consensus (are neighbor values similar/higher/lower than target?)
    fraction_higher: float = Field(0.0, ge=0.0, le=1.0, description="Fraction of neighbors with value > target + tolerance.")
    fraction_lower: float = Field(0.0, ge=0.0, le=1.0, description="Fraction of neighbors with value < target - tolerance.")
    fraction_similar: float = Field(0.0, ge=0.0, le=1.0, description="Fraction of neighbors within tolerance of target.")
    
    # Change / Trend consensus (do neighbors show the same directional tendency?)
    fraction_increasing: float = Field(0.0, ge=0.0, le=1.0, description="Fraction of neighbors with positive rate-of-change.")
    fraction_decreasing: float = Field(0.0, ge=0.0, le=1.0, description="Fraction of neighbors with negative rate-of-change.")
    fraction_stable: float = Field(0.0, ge=0.0, le=1.0, description="Fraction of neighbors with rate-of-change near zero.")
    
    # Directional agreement index with target change: [-1.0 (opposite), 0.0 (neutral), 1.0 (unanimous agreement)]
    directional_agreement: Optional[float] = Field(None, ge=-1.0, le=1.0, description="Alignment of neighbor trends with target trend.")
    
    # Inverse Distance Weighted (IDW) statistics
    idw_expected_value: Optional[float] = Field(None, description="Distance-weighted expected value from neighbors.")
    target_minus_idw: Optional[float] = Field(None, description="Target minus distance-weighted neighbor expected value.")


class SpatialContextEvidence(BaseModel):
    """Comprehensive contextual evidence record generated for an observation at a specific station and timestamp."""
    model_config = ConfigDict(frozen=True)

    target_station_id: str = Field(..., description="Target AWS station identifier.")
    timestamp: str = Field(..., description="ISO 8601 timestamp of target observation.")
    target_elevation_m: Optional[float] = Field(None, description="Elevation of target station in meters.")
    
    # Network coverage metadata
    configured_neighbors_count: int = Field(0, ge=0, description="Total geographical neighbors within radius.")
    valid_neighbors_count: int = Field(0, ge=0, description="Neighbors with valid observations within time window.")
    stale_neighbors_count: int = Field(0, ge=0, description="Neighbors excluded due to stale timestamps.")
    
    # Variable-specific consensus objects
    temperature_consensus: Optional[VariableConsensus] = Field(None, description="Spatial consensus for Temperature (°C).")
    relative_humidity_consensus: Optional[VariableConsensus] = Field(None, description="Spatial consensus for Relative Humidity (%).")
    sea_level_pressure_consensus: Optional[VariableConsensus] = Field(None, description="Spatial consensus for Sea-Level Pressure (hPa).")
    
    # Cross-variable multi-sensor coherence
    cross_variable_coherence: float = Field(
        0.0, ge=0.0, le=1.0,
        description="Index [0, 1] indicating whether multi-parameter shifts across T, RH, and P correlate with regional trends."
    )
    
    # Contextual Classification
    context_category: SpatialContextCategory = Field(
        SpatialContextCategory.INSUFFICIENT_CONTEXT,
        description="High-level contextual evidence category."
    )
    
    # Additional execution metadata
    temporal_tolerance_minutes: float = Field(..., description="Time window tolerance used.")
    max_distance_km: float = Field(..., description="Max neighbor radius in km.")
    is_causal: bool = Field(True, description="True if forward-time neighbor data was strictly excluded.")
    neighbor_details: List[NeighborObservationRecord] = Field(
        default_factory=list,
        description="Detailed list of evaluated neighbor records."
    )
    evidence_notes: List[str] = Field(default_factory=list, description="Diagnostic contextual notes.")
