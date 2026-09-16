"""Geodesic spatial neighborhood feature extraction for SkyGuard AI AWS networks."""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Sequence, Tuple
import numpy as np
import pandas as pd

from backend.app.core.constants import EARTH_RADIUS_KM
from backend.app.core.meteorology import station_to_sea_level_pressure


def haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Compute the great-circle distance between two points on a sphere using the Haversine formula.
    
    Args:
        lat1: Latitude of point 1 in decimal degrees.
        lon1: Longitude of point 1 in decimal degrees.
        lat2: Latitude of point 2 in decimal degrees.
        lon2: Longitude of point 2 in decimal degrees.
        
    Returns:
        Geodesic distance in kilometers.
    """
    if any(math.isnan(v) for v in (lat1, lon1, lat2, lon2)):
        return float("nan")

    # Validate coordinate bounds
    if not (-90.0 <= lat1 <= 90.0 and -90.0 <= lat2 <= 90.0):
        return float("nan")
    if not (-180.0 <= lon1 <= 180.0 and -180.0 <= lon2 <= 180.0):
        return float("nan")

    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    )
    # Clamp a to [0.0, 1.0] to prevent math domain error in asin
    a_clamped = min(1.0, max(0.0, a))
    c = 2.0 * math.atan2(math.sqrt(a_clamped), math.sqrt(1.0 - a_clamped))

    return EARTH_RADIUS_KM * c


class SpatialNeighborExtractor:
    """Extracts inter-station neighborhood deltas and consensus metrics across the AWS network.
    
    Uses exact geodesic (Haversine) distances and normalizes surface barometric pressure
    to Mean Sea Level (MSL) to enable physically valid inter-station spatial comparisons.
    """

    def __init__(
        self,
        station_metadata: Optional[Dict[str, Dict[str, Any]]] = None,
        max_distance_km: float = 600.0,
        max_neighbors: int = 5,
        temporal_tolerance_minutes: float = 30.0,
    ) -> None:
        """Initialize spatial extractor.
        
        Args:
            station_metadata: Mapping of station_id -> {latitude, longitude, elevation_m, ...}.
            max_distance_km: Maximum radius in km to consider a station as a spatial neighbor.
            max_neighbors: Maximum number of nearest neighbors to evaluate (k-NN).
            temporal_tolerance_minutes: Max timestamp difference to consider observations simultaneous.
        """
        self.station_metadata = station_metadata or {}
        self.max_distance_km = max_distance_km
        self.max_neighbors = max_neighbors
        self.temporal_tolerance_minutes = temporal_tolerance_minutes

    def compute_distance_matrix(self) -> pd.DataFrame:
        """Compute pairwise geodesic distance matrix across all registered stations.
        
        Returns:
            Square DataFrame indexed and columned by station_id with distances in km.
        """
        station_ids = list(self.station_metadata.keys())
        n = len(station_ids)
        matrix = np.full((n, n), np.nan)

        for i, s1 in enumerate(station_ids):
            m1 = self.station_metadata[s1]
            lat1, lon1 = m1.get("latitude"), m1.get("longitude")
            if lat1 is None or lon1 is None:
                continue

            for j, s2 in enumerate(station_ids):
                if i == j:
                    matrix[i, j] = 0.0
                    continue
                m2 = self.station_metadata[s2]
                lat2, lon2 = m2.get("latitude"), m2.get("longitude")
                if lat2 is None or lon2 is None:
                    continue

                d = haversine_distance_km(lat1, lon1, lat2, lon2)
                matrix[i, j] = d

        return pd.DataFrame(matrix, index=station_ids, columns=station_ids)

    def find_nearest_neighbors(self, target_station_id: str) -> List[Tuple[str, float]]:
        """Find the nearest eligible neighbors for a target station within max_distance_km.
        
        Args:
            target_station_id: Station identifier.
            
        Returns:
            List of (neighbor_station_id, distance_km) tuples sorted by increasing distance.
        """
        if target_station_id not in self.station_metadata:
            return []

        target_meta = self.station_metadata[target_station_id]
        t_lat, t_lon = target_meta.get("latitude"), target_meta.get("longitude")
        if t_lat is None or t_lon is None or math.isnan(t_lat) or math.isnan(t_lon):
            return []

        neighbors: List[Tuple[str, float]] = []
        for s_id, s_meta in self.station_metadata.items():
            if s_id == target_station_id:
                continue
            s_lat, s_lon = s_meta.get("latitude"), s_meta.get("longitude")
            if s_lat is None or s_lon is None or math.isnan(s_lat) or math.isnan(s_lon):
                continue

            dist = haversine_distance_km(t_lat, t_lon, s_lat, s_lon)
            if not math.isnan(dist) and dist <= self.max_distance_km:
                neighbors.append((s_id, dist))

        # Sort by distance and retain top k
        neighbors.sort(key=lambda x: x[1])
        return neighbors[: self.max_neighbors]

    def extract_features_multi_station(
        self,
        df: pd.DataFrame,
        timestamp_col: str = "timestamp",
        station_id_col: str = "station_id",
    ) -> pd.DataFrame:
        """Extract spatial neighbor features for a multi-station dataset.
        
        Args:
            df: DataFrame containing multi-station observations.
            timestamp_col: Name of timestamp column.
            station_id_col: Name of station ID column.
            
        Returns:
            DataFrame with added spatial neighbor delta and consensus columns.
        """
        if df.empty:
            return df.copy()

        result = df.copy()
        result[timestamp_col] = pd.to_datetime(result[timestamp_col], utc=True)

        # Ensure station metadata is populated from DataFrame if not already set
        if not self.station_metadata:
            for s_id, group in result.groupby(station_id_col):
                first_row = group.iloc[0]
                self.station_metadata[str(s_id)] = {
                    "latitude": first_row.get("latitude", float("nan")),
                    "longitude": first_row.get("longitude", float("nan")),
                    "elevation_m": first_row.get("elevation_m", first_row.get("elevation", float("nan"))),
                }

        # Precompute normalized sea-level pressure if missing but station pressure + elevation exists
        if "sea_level_pressure_hpa" not in result.columns:
            result["sea_level_pressure_hpa"] = np.nan

        if "station_pressure_hpa" in result.columns:
            mask_need_slp = result["sea_level_pressure_hpa"].isna() & result["station_pressure_hpa"].notna()
            if mask_need_slp.any() and "elevation_m" in result.columns and "temperature_c" in result.columns:
                for idx in result[mask_need_slp].index:
                    p_stn = result.at[idx, "station_pressure_hpa"]
                    elev = result.at[idx, "elevation_m"]
                    temp = result.at[idx, "temperature_c"]
                    derived_slp = station_to_sea_level_pressure(p_stn, elev, temp)
                    if derived_slp is not None:
                        result.at[idx, "sea_level_pressure_hpa"] = derived_slp

        # Initialize spatial feature columns
        spatial_cols = [
            "spatial_neighbor_count",
            "spatial_nearest_neighbor_dist_km",
            "spatial_neighbor_temp_mean",
            "spatial_neighbor_temp_median",
            "spatial_neighbor_temp_std",
            "spatial_temp_delta_from_neighbor_mean",
            "spatial_neighbor_rh_mean",
            "spatial_neighbor_rh_median",
            "spatial_neighbor_rh_std",
            "spatial_rh_delta_from_neighbor_mean",
            "spatial_neighbor_slp_mean",
            "spatial_neighbor_slp_median",
            "spatial_neighbor_slp_std",
            "spatial_slp_delta_from_neighbor_mean",
        ]
        for col in spatial_cols:
            result[col] = np.nan

        # Group observations by timestamp rounded to tolerance interval for synchronized spatial comparison
        tolerance_str = f"{int(self.temporal_tolerance_minutes)}min" if self.temporal_tolerance_minutes >= 1 else "1min"
        result["_time_bucket"] = result[timestamp_col].dt.round(tolerance_str)

        # Precompute neighbor lists for all stations
        unique_stations = result[station_id_col].unique()
        station_neighbors = {
            str(s_id): self.find_nearest_neighbors(str(s_id)) for s_id in unique_stations
        }

        # Iterate by time bucket to aggregate neighbor values
        for bucket, bucket_group in result.groupby("_time_bucket"):
            station_map = {str(row[station_id_col]): row for _, row in bucket_group.iterrows()}

            for idx, row in bucket_group.iterrows():
                curr_s_id = str(row[station_id_col])
                neighbors = station_neighbors.get(curr_s_id, [])

                if not neighbors:
                    result.at[idx, "spatial_neighbor_count"] = 0
                    continue

                active_temps: List[float] = []
                active_rhs: List[float] = []
                active_slps: List[float] = []
                active_dists: List[float] = []

                for n_id, n_dist in neighbors:
                    if n_id in station_map:
                        n_row = station_map[n_id]
                        t = n_row.get("temperature_c")
                        rh = n_row.get("relative_humidity_pct")
                        slp = n_row.get("sea_level_pressure_hpa")

                        if t is not None and not pd.isna(t):
                            active_temps.append(float(t))
                        if rh is not None and not pd.isna(rh):
                            active_rhs.append(float(rh))
                        if slp is not None and not pd.isna(slp):
                            active_slps.append(float(slp))
                        active_dists.append(n_dist)

                k_active = len(active_dists)
                result.at[idx, "spatial_neighbor_count"] = k_active

                if k_active > 0:
                    result.at[idx, "spatial_nearest_neighbor_dist_km"] = min(active_dists)

                # Temperature spatial aggregation
                if active_temps:
                    t_mean = float(np.mean(active_temps))
                    t_med = float(np.median(active_temps))
                    t_std = float(np.std(active_temps, ddof=1)) if len(active_temps) > 1 else 0.0
                    result.at[idx, "spatial_neighbor_temp_mean"] = t_mean
                    result.at[idx, "spatial_neighbor_temp_median"] = t_med
                    result.at[idx, "spatial_neighbor_temp_std"] = t_std

                    curr_t = row.get("temperature_c")
                    if curr_t is not None and not pd.isna(curr_t):
                        result.at[idx, "spatial_temp_delta_from_neighbor_mean"] = float(curr_t) - t_mean

                # Humidity spatial aggregation
                if active_rhs:
                    rh_mean = float(np.mean(active_rhs))
                    rh_med = float(np.median(active_rhs))
                    rh_std = float(np.std(active_rhs, ddof=1)) if len(active_rhs) > 1 else 0.0
                    result.at[idx, "spatial_neighbor_rh_mean"] = rh_mean
                    result.at[idx, "spatial_neighbor_rh_median"] = rh_med
                    result.at[idx, "spatial_neighbor_rh_std"] = rh_std

                    curr_rh = row.get("relative_humidity_pct")
                    if curr_rh is not None and not pd.isna(curr_rh):
                        result.at[idx, "spatial_rh_delta_from_neighbor_mean"] = float(curr_rh) - rh_mean

                # Pressure spatial aggregation (Sea-Level Pressure)
                if active_slps:
                    slp_mean = float(np.mean(active_slps))
                    slp_med = float(np.median(active_slps))
                    slp_std = float(np.std(active_slps, ddof=1)) if len(active_slps) > 1 else 0.0
                    result.at[idx, "spatial_neighbor_slp_mean"] = slp_mean
                    result.at[idx, "spatial_neighbor_slp_median"] = slp_med
                    result.at[idx, "spatial_neighbor_slp_std"] = slp_std

                    curr_slp = row.get("sea_level_pressure_hpa")
                    if curr_slp is not None and not pd.isna(curr_slp):
                        result.at[idx, "spatial_slp_delta_from_neighbor_mean"] = float(curr_slp) - slp_mean

        result = result.drop(columns=["_time_bucket"])
        return result
