"""Explicit Feature Registry and catalog metadata for SkyGuard AI."""

from __future__ import annotations

from enum import Enum
from typing import Dict, List, Optional, Sequence
from pydantic import BaseModel, ConfigDict, Field


class FeatureCategory(str, Enum):
    """Categorical classification of engineered features."""
    RAW = "RAW"
    TEMPORAL = "TEMPORAL"
    ROLLING = "ROLLING"
    CHANGE = "CHANGE"
    PERSISTENCE = "PERSISTENCE"
    DEVIATION = "DEVIATION"
    MULTIVARIATE = "MULTIVARIATE"
    SPATIAL = "SPATIAL"


class FeatureDefinition(BaseModel):
    """Metadata specification for an individual feature."""
    model_config = ConfigDict(frozen=True)

    name: str = Field(..., description="Exact column name in the feature DataFrame")
    category: FeatureCategory = Field(..., description="Feature category grouping")
    description: str = Field(..., description="Detailed description of physical or statistical meaning")
    units: Optional[str] = Field(default=None, description="Physical unit (e.g., '°C', '%', 'hPa', 'min')")
    allowed_for_training: bool = Field(default=True, description="Whether feature is safe for ML model training")
    allowed_for_evaluation: bool = Field(default=True, description="Whether feature is suitable for evaluation")
    leakage_risk: str = Field(
        default="LOW",
        description="Assessed risk of lookahead data leakage ('NONE', 'LOW', 'HIGH')"
    )
    source_dependency: List[str] = Field(
        default_factory=list,
        description="Source parameters required to compute this feature"
    )


class FeatureRegistry:
    """Central registry and selector for SkyGuard AI feature definitions."""

    def __init__(self) -> None:
        self._registry: Dict[str, FeatureDefinition] = {}
        self._register_default_features()

    def register(self, feature: FeatureDefinition) -> None:
        """Register a feature definition."""
        self._registry[feature.name] = feature

    def get(self, name: str) -> Optional[FeatureDefinition]:
        """Retrieve a feature definition by name."""
        return self._registry.get(name)

    def list_features(
        self,
        category: Optional[FeatureCategory] = None,
        training_only: bool = False,
    ) -> List[FeatureDefinition]:
        """List registered features with optional filtering."""
        features = list(self._registry.values())
        if category:
            features = [f for f in features if f.category == category]
        if training_only:
            features = [f for f in features if f.allowed_for_training]
        return features

    def get_feature_names(
        self,
        category: Optional[FeatureCategory] = None,
        training_only: bool = False,
    ) -> List[str]:
        """Return list of feature names matching filter."""
        return [f.name for f in self.list_features(category=category, training_only=training_only)]

    def _register_default_features(self) -> None:
        """Populate the registry with standard SkyGuard AI feature definitions."""
        # 1. RAW
        raw_defs = [
            ("temperature_c", "Ambient dry-bulb air temperature", "°C", ["temperature"]),
            ("relative_humidity_pct", "Relative humidity percentage", "%", ["humidity"]),
            ("sea_level_pressure_hpa", "Sea-level barometric pressure", "hPa", ["pressure"]),
            ("station_pressure_hpa", "Surface station barometric pressure", "hPa", ["station_pressure"]),
            ("dew_point_c", "Dew point temperature", "°C", ["dew_point"]),
        ]
        for name, desc, unit, deps in raw_defs:
            self.register(FeatureDefinition(
                name=name, category=FeatureCategory.RAW, description=desc, units=unit,
                allowed_for_training=True, source_dependency=deps
            ))

        # 2. TEMPORAL
        temp_defs = [
            ("hour", "Integer hour of day in UTC", "hour"),
            ("minute", "Integer minute of hour in UTC", "min"),
            ("day_of_year", "Day of calendar year", "day"),
            ("month", "Calendar month of year", "month"),
            ("day_of_week", "Day of week index (0=Mon, 6=Sun)", "day"),
            ("sin_hour", "Sinusoidal cyclical embedding of diurnal hour", None),
            ("cos_hour", "Cosinusoidal cyclical embedding of diurnal hour", None),
            ("sin_day_of_year", "Sinusoidal cyclical embedding of annual solar cycle", None),
            ("cos_day_of_year", "Cosinusoidal cyclical embedding of annual solar cycle", None),
            ("sin_day_of_week", "Sinusoidal cyclical embedding of weekly cycle", None),
            ("cos_day_of_week", "Cosinusoidal cyclical embedding of weekly cycle", None),
        ]
        for name, desc, unit in temp_defs:
            self.register(FeatureDefinition(
                name=name, category=FeatureCategory.TEMPORAL, description=desc, units=unit,
                allowed_for_training=True, source_dependency=["timestamp"]
            ))

        # 3. ROLLING & LAGS
        params = ["temperature_c", "relative_humidity_pct", "sea_level_pressure_hpa", "station_pressure_hpa"]
        windows = ["15m", "30m", "1h", "3h", "6h", "24h"]
        for p in params:
            for lag in [1, 2, 3]:
                self.register(FeatureDefinition(
                    name=f"{p}_lag_{lag}", category=FeatureCategory.ROLLING,
                    description=f"{p} lagged by {lag} discrete observation steps",
                    allowed_for_training=True, source_dependency=[p, "timestamp"]
                ))
            for w in windows:
                for stat, s_desc in [("mean", "Rolling mean"), ("std", "Rolling standard deviation"),
                                     ("min", "Rolling minimum"), ("max", "Rolling maximum"),
                                     ("count", "Observation count in window")]:
                    self.register(FeatureDefinition(
                        name=f"{p}_rolling_{stat}_{w}", category=FeatureCategory.ROLLING,
                        description=f"{s_desc} of {p} over backward-looking {w} window",
                        allowed_for_training=True, source_dependency=[p, "timestamp"]
                    ))

        # 4. CHANGE / RATES
        for p in params:
            self.register(FeatureDefinition(
                name=f"{p}_delta", category=FeatureCategory.CHANGE,
                description=f"First-order difference X_t - X_{{t-1}} for {p}",
                allowed_for_training=True, source_dependency=[p, "timestamp"]
            ))
            self.register(FeatureDefinition(
                name=f"{p}_rate_per_minute", category=FeatureCategory.CHANGE,
                description=f"Time-normalized rate of change per minute for {p}",
                units=f"unit/min", allowed_for_training=True, source_dependency=[p, "timestamp"]
            ))
            self.register(FeatureDefinition(
                name=f"{p}_rate_per_5min", category=FeatureCategory.CHANGE,
                description=f"Standard 5-minute scaled rate of change for {p}",
                units=f"unit/5min", allowed_for_training=True, source_dependency=[p, "timestamp"]
            ))
            self.register(FeatureDefinition(
                name=f"{p}_rate_per_hour", category=FeatureCategory.CHANGE,
                description=f"Hourly scaled rate of change for {p}",
                units=f"unit/hr", allowed_for_training=True, source_dependency=[p, "timestamp"]
            ))
            self.register(FeatureDefinition(
                name=f"{p}_acceleration", category=FeatureCategory.CHANGE,
                description=f"Second derivative / acceleration of {p}",
                allowed_for_training=True, source_dependency=[p, "timestamp"]
            ))

        # 5. PERSISTENCE & DEVIATIONS
        for p in ["temperature_c", "relative_humidity_pct", "sea_level_pressure_hpa"]:
            self.register(FeatureDefinition(
                name=f"{p}_consecutive_unchanged_count", category=FeatureCategory.PERSISTENCE,
                description=f"Consecutive invariant observation counter for {p}",
                allowed_for_training=True, source_dependency=[p]
            ))
            self.register(FeatureDefinition(
                name=f"{p}_duration_unchanged_minutes", category=FeatureCategory.PERSISTENCE,
                description=f"Duration in minutes that {p} has remained constant",
                units="min", allowed_for_training=True, source_dependency=[p, "timestamp"]
            ))
            self.register(FeatureDefinition(
                name=f"{p}_rounded_unchanged_count", category=FeatureCategory.PERSISTENCE,
                description=f"Repeated rounded value counter for {p}",
                allowed_for_training=True, source_dependency=[p]
            ))
            self.register(FeatureDefinition(
                name=f"{p}_deviation_from_mean_1h", category=FeatureCategory.DEVIATION,
                description=f"Residual X - rolling_mean_1h for {p}",
                allowed_for_training=True, source_dependency=[p, "timestamp"]
            ))
            self.register(FeatureDefinition(
                name=f"{p}_zscore_1h", category=FeatureCategory.DEVIATION,
                description=f"Standardized local Z-score over 1h window for {p}",
                allowed_for_training=True, source_dependency=[p, "timestamp"]
            ))

        # 6. MULTIVARIATE
        multi_defs = [
            ("dew_point_spread_c", "Dew point spread T - Td", "°C", ["temperature_c", "dew_point_c"]),
            ("temp_rh_delta_interaction", "Product of temperature and RH deltas", None, ["temperature_c", "relative_humidity_pct"]),
            ("joint_temp_rh_divergence", "Standardized rate divergence between T and RH", None, ["temperature_c", "relative_humidity_pct"]),
            ("temp_slp_delta_interaction", "Product of temperature and pressure deltas", None, ["temperature_c", "sea_level_pressure_hpa"]),
            ("joint_standardized_anomaly_magnitude", "Euclidean norm of joint parameter Z-scores", None, ["temperature_c", "relative_humidity_pct", "sea_level_pressure_hpa"]),
        ]
        for name, desc, unit, deps in multi_defs:
            self.register(FeatureDefinition(
                name=name, category=FeatureCategory.MULTIVARIATE, description=desc, units=unit,
                allowed_for_training=True, source_dependency=deps
            ))

        # 7. SPATIAL
        spatial_defs = [
            ("spatial_neighbor_count", "Number of simultaneous active spatial neighbors", None),
            ("spatial_nearest_neighbor_dist_km", "Distance to closest active spatial neighbor", "km"),
            ("spatial_temp_delta_from_neighbor_mean", "Difference between station temperature and neighbor mean", "°C"),
            ("spatial_neighbor_temp_median", "Median temperature of spatial neighbors", "°C"),
            ("spatial_neighbor_temp_std", "Standard deviation of spatial neighbor temperatures", "°C"),
            ("spatial_rh_delta_from_neighbor_mean", "Difference between station RH and neighbor mean", "%"),
            ("spatial_neighbor_rh_median", "Median RH of spatial neighbors", "%"),
            ("spatial_neighbor_rh_std", "Standard deviation of spatial neighbor RH", "%"),
            ("spatial_slp_delta_from_neighbor_mean", "Difference between station MSL pressure and neighbor mean", "hPa"),
            ("spatial_neighbor_slp_median", "Median MSL pressure of spatial neighbors", "hPa"),
            ("spatial_neighbor_slp_std", "Standard deviation of spatial neighbor MSL pressure", "hPa"),
        ]
        for name, desc, unit in spatial_defs:
            self.register(FeatureDefinition(
                name=name, category=FeatureCategory.SPATIAL, description=desc, units=unit,
                allowed_for_training=True, source_dependency=["latitude", "longitude", "timestamp"]
            ))


# Predefined Feature Sets for Baseline Modeling & Ablation Studies (Strict 3 Weather Variables: T, P, RH)
FORBIDDEN_CORE_VARIABLES: List[str] = ["wind_speed", "wind_speed_mps", "precipitation", "dew_point_c", "dew_point"]

FEATURE_SET_A_RAW_TEMPORAL: List[str] = [
    "temperature_c",
    "relative_humidity_pct",
    "sea_level_pressure_hpa",
    "sin_hour",
    "cos_hour",
    "sin_day_of_year",
    "cos_day_of_year",
]

FEATURE_SET_B_TEMPORAL_ROLLING: List[str] = FEATURE_SET_A_RAW_TEMPORAL + [
    "temperature_c_rolling_mean_1h",
    "temperature_c_rolling_std_1h",
    "temperature_c_delta",
    "temperature_c_rate_per_minute",
    "temperature_c_duration_unchanged_minutes",
    "relative_humidity_pct_rolling_mean_1h",
    "relative_humidity_pct_rolling_std_1h",
    "relative_humidity_pct_delta",
    "sea_level_pressure_hpa_rolling_mean_1h",
    "sea_level_pressure_hpa_delta",
]

FEATURE_SET_C_MULTIVARIATE: List[str] = FEATURE_SET_B_TEMPORAL_ROLLING + [
    "temp_rh_delta_interaction",
    "joint_temp_rh_divergence",
    "temp_slp_delta_interaction",
    "joint_standardized_anomaly_magnitude",
]

FEATURE_SET_D_SPATIAL: List[str] = FEATURE_SET_C_MULTIVARIATE + [
    "spatial_neighbor_count",
    "spatial_temp_delta_from_neighbor_mean",
    "spatial_rh_delta_from_neighbor_mean",
    "spatial_slp_delta_from_neighbor_mean",
]

# CORE MODEL APPROVED FEATURE SET (Strict 3-Variable Scope: Temperature, Pressure, Relative Humidity)
CORE_FEATURE_SET: List[str] = FEATURE_SET_C_MULTIVARIATE.copy()

# Baseline Default Feature Set
BASELINE_FEATURE_SET: List[str] = CORE_FEATURE_SET.copy()


def validate_core_feature_list(features: Sequence[str]) -> bool:
    """Validate that feature list contains only approved 3-variable features (T, P, RH + temporal/spatial)."""
    for f in features:
        for forbidden in FORBIDDEN_CORE_VARIABLES:
            if forbidden == f or f.startswith(f"{forbidden}_"):
                raise ValueError(
                    f"Forbidden feature '{f}' detected in core model feature set. "
                    f"Core model is strictly restricted to Temperature, Atmospheric Pressure, and Relative Humidity."
                )
    return True

