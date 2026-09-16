"""Uncertainty quantification engine for meteorological value estimation in SkyGuard AI."""

from __future__ import annotations

import math
from typing import List, Optional, Tuple
import numpy as np

from ml.imputation.schema import EstimationMethod, MethodQuality, UncertaintyEstimate


# Parameter-specific physical bounds and standard error floors
VARIABLE_BOUNDS = {
    "temperature_c": (-50.0, 60.0),
    "temperature": (-50.0, 60.0),
    "relative_humidity_pct": (0.0, 100.0),
    "relative_humidity": (0.0, 100.0),
    "humidity": (0.0, 100.0),
    "sea_level_pressure_hpa": (870.0, 1085.0),
    "station_pressure_hpa": (300.0, 1085.0),
    "pressure": (300.0, 1085.0),
    "dew_point_c": (-80.0, 60.0),
}

VARIABLE_STD_FLOORS = {
    "temperature_c": 0.25,
    "temperature": 0.25,
    "relative_humidity_pct": 1.50,
    "relative_humidity": 1.50,
    "humidity": 1.50,
    "sea_level_pressure_hpa": 0.30,
    "station_pressure_hpa": 0.30,
    "pressure": 0.30,
    "dew_point_c": 0.30,
}


def calculate_uncertainty(
    estimate: float,
    target_variable: str,
    method: EstimationMethod,
    observed_value: Optional[float] = None,
    neighbor_values: Optional[List[float]] = None,
    neighbor_distances_km: Optional[List[float]] = None,
    temporal_history: Optional[List[float]] = None,
    gap_minutes: float = 0.0,
    station_health_score: Optional[float] = None,
) -> UncertaintyEstimate:
    """Calculate transparent, physically grounded uncertainty bounds for an estimated value.
    
    Args:
        estimate: The computed numerical estimate.
        target_variable: Meteorological parameter name (e.g. 'temperature_c').
        method: The estimation method used.
        observed_value: Optional original observed sensor value.
        neighbor_values: Optional list of contemporaneous neighbor readings.
        neighbor_distances_km: Optional list of neighbor geodesic distances.
        temporal_history: Optional list of recent historical values for the station.
        gap_minutes: Duration of missing gap in minutes (if applicable).
        station_health_score: Optional 0-100 sensor health index.
        
    Returns:
        Structured `UncertaintyEstimate`.
    """
    notes: List[str] = []
    
    # 1. Base standard error floor for the variable
    std_floor = VARIABLE_STD_FLOORS.get(target_variable, 0.5)
    bounds = VARIABLE_BOUNDS.get(target_variable, (-1000.0, 1000.0))

    # 2. Spatial Dispersion Component
    valid_neighbors = [v for v in (neighbor_values or []) if v is not None and not math.isnan(v)]
    n_count = len(valid_neighbors)
    spatial_std = 0.0
    dist_penalty = 1.0

    if n_count >= 2:
        spatial_std = float(np.std(valid_neighbors, ddof=1))
        if neighbor_distances_km:
            valid_dists = [d for d in neighbor_distances_km if d is not None and not math.isnan(d)]
            if valid_dists:
                avg_dist = float(np.mean(valid_dists))
                # Slight penalty for distant neighbor networks (> 100 km)
                dist_penalty = max(1.0, 1.0 + (avg_dist - 100.0) / 400.0)
    elif n_count == 1:
        spatial_std = std_floor * 1.5

    # 3. Temporal Dispersion Component
    valid_temporal = [v for v in (temporal_history or []) if v is not None and not math.isnan(v)]
    t_count = len(valid_temporal)
    temporal_std = 0.0

    if t_count >= 2:
        temporal_std = float(np.std(valid_temporal, ddof=1))
    elif t_count == 1:
        temporal_std = std_floor * 1.5

    # 4. Synthesize Standard Error based on method
    if method in (EstimationMethod.SPATIAL_IDW_CONSENSUS, EstimationMethod.NEIGHBOR_WEIGHTED_MEDIAN):
        if n_count >= 2:
            base_se = max(std_floor, spatial_std * dist_penalty / math.sqrt(n_count))
            notes.append(f"Spatial uncertainty derived from {n_count} neighbors (spread: {spatial_std:.2f}).")
        elif n_count == 1:
            base_se = max(std_floor * 1.5, spatial_std * dist_penalty)
            notes.append("Single neighbor available; spatial uncertainty elevated.")
        else:
            base_se = std_floor * 3.0
            notes.append("Zero valid neighbors; default spatial uncertainty baseline applied.")

    elif method in (EstimationMethod.CAUSAL_TEMPORAL_INTERPOLATION, EstimationMethod.ROLLING_BASELINE):
        if t_count >= 2:
            base_se = max(std_floor, temporal_std / math.sqrt(t_count))
            notes.append(f"Temporal uncertainty derived from {t_count} historical steps (spread: {temporal_std:.2f}).")
        else:
            base_se = std_floor * 2.5
            notes.append("Limited temporal history; baseline uncertainty elevated.")

    elif method == EstimationMethod.COMBINED_TEMPORAL_SPATIAL:
        s_se = max(std_floor, spatial_std / math.sqrt(max(1, n_count)))
        t_se = max(std_floor, temporal_std / math.sqrt(max(1, t_count)))
        base_se = math.sqrt(0.6 * (s_se ** 2) + 0.4 * (t_se ** 2)) * dist_penalty
        notes.append(f"Combined spatial ({n_count} neighbors) and temporal ({t_count} steps) uncertainty.")

    elif method == EstimationMethod.RETROSPECTIVE_INTERPOLATION:
        if t_count >= 2:
            # Retrospective two-sided interpolation reduces interpolation variance
            base_se = max(std_floor * 0.8, (temporal_std / math.sqrt(t_count)) * 0.8)
            notes.append("Two-sided retrospective interpolation uncertainty applied.")
        else:
            base_se = std_floor * 2.0
    else:
        base_se = std_floor * 3.0
        notes.append("Default non-parametric uncertainty baseline applied.")

    # 5. Gap Penalty
    if gap_minutes > 5.0:
        gap_factor = math.sqrt(1.0 + (gap_minutes - 5.0) / 30.0)
        base_se *= gap_factor
        notes.append(f"Gap penalty applied for {gap_minutes:.1f} min missing duration.")

    # 6. Absolute Deviation vs Observed
    abs_dev = None
    if observed_value is not None and not math.isnan(observed_value):
        abs_dev = float(abs(observed_value - estimate))

    # 7. Method Quality Determination
    if method == EstimationMethod.COMBINED_TEMPORAL_SPATIAL and n_count >= 3 and t_count >= 3:
        quality = MethodQuality.HIGH
    elif method in (EstimationMethod.SPATIAL_IDW_CONSENSUS, EstimationMethod.NEIGHBOR_WEIGHTED_MEDIAN) and n_count >= 3:
        quality = MethodQuality.HIGH
    elif method == EstimationMethod.RETROSPECTIVE_INTERPOLATION and t_count >= 4 and gap_minutes <= 15.0:
        quality = MethodQuality.HIGH
    elif (n_count >= 2 or t_count >= 3) and gap_minutes <= 30.0:
        quality = MethodQuality.MEDIUM
    elif n_count == 1 or t_count == 2 or gap_minutes <= 60.0:
        quality = MethodQuality.LOW
    else:
        quality = MethodQuality.POOR

    # 8. Confidence / Certainty Index Calculation (0.0 to 1.0)
    quality_weights = {
        MethodQuality.HIGH: 0.90,
        MethodQuality.MEDIUM: 0.75,
        MethodQuality.LOW: 0.50,
        MethodQuality.POOR: 0.25,
    }
    base_conf = quality_weights[quality]
    
    # Penalize if standard error is large relative to physical span
    span = bounds[1] - bounds[0]
    relative_se = min(1.0, (base_se * 2.0) / (span * 0.1))
    certainty = max(0.1, min(0.98, base_conf * (1.0 - 0.5 * relative_se)))

    # Adjust for sensor health if known
    if station_health_score is not None:
        if station_health_score < 40.0:
            notes.append(f"Station health is degraded ({station_health_score:.1f}/100); corroborating evidence prioritized.")

    # 9. Plausible Estimate Range (1.96 * SE, ~95% confidence interval)
    margin = 1.96 * base_se
    lower_bound = max(bounds[0], estimate - margin)
    upper_bound = min(bounds[1], estimate + margin)

    return UncertaintyEstimate(
        estimate_range=(round(lower_bound, 3), round(upper_bound, 3)),
        standard_error=round(base_se, 3),
        absolute_deviation=round(abs_dev, 3) if abs_dev is not None else None,
        supporting_neighbor_count=n_count,
        method_quality=quality,
        confidence_index=round(certainty, 3),
        notes=notes,
    )
