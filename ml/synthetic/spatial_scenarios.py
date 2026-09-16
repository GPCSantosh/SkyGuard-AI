"""Multi-station synthetic spatial scenario generators for spatial context evaluation."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import pandas as pd

from ml.spatial.topology import SpatialNetworkTopology
from ml.synthetic.injectors import SpikeInjector, OffsetInjector, DriftInjector
from ml.synthetic.schema import GroundTruthRecord, SyntheticAnomalyType


class SpatialScenarioGenerator:
    """Generates multi-station synthetic scenarios for validating the Spatial & Synoptic Context Engine."""

    def __init__(self, topology: Optional[SpatialNetworkTopology] = None) -> None:
        self.topology = topology or SpatialNetworkTopology()

    def generate_scenario_a_local_anomaly(
        self,
        df: pd.DataFrame,
        target_station_id: str,
        start_timestamp: Any,
        duration_steps: int = 6,
        magnitude: float = 6.0,
        variable: str = "temperature_c",
        station_id_col: str = "station_id",
        timestamp_col: str = "timestamp",
        anomaly_id: str = "SCEN-A-LOCAL",
    ) -> Tuple[pd.DataFrame, List[GroundTruthRecord]]:
        """Scenario A: Local Sensor Anomaly.
        
        Only the target station is corrupted with a sensor fault (e.g., severe offset/spike),
        while neighboring stations remain completely pristine.
        """
        result = df.copy()
        result[timestamp_col] = pd.to_datetime(result[timestamp_col], utc=True)
        t_start = pd.to_datetime(start_timestamp, utc=True)

        stn_mask = (result[station_id_col].astype(str) == str(target_station_id)) & (result[timestamp_col] >= t_start)
        target_indices = result[stn_mask].index[:duration_steps]

        gt_records: List[GroundTruthRecord] = []
        if len(target_indices) == 0:
            return result, gt_records

        t_end = result.loc[target_indices[-1], timestamp_col]

        for idx in target_indices:
            orig = result.at[idx, variable]
            if pd.isna(orig):
                continue
            mod = float(orig) + magnitude
            result.at[idx, variable] = mod

            gt_records.append(
                GroundTruthRecord(
                    anomaly_id=anomaly_id,
                    station_id=str(target_station_id),
                    timestamp=result.loc[idx, timestamp_col].to_pydatetime(),
                    anomaly_type=SyntheticAnomalyType.OFFSET,
                    affected_variable=variable,
                    original_value=float(orig),
                    modified_value=mod,
                    injection_start=t_start.to_pydatetime(),
                    injection_end=t_end.to_pydatetime(),
                    severity_parameter=magnitude,
                    ground_truth_label=1,
                    is_fault=True,
                    metadata={"scenario": "Scenario A: Local Sensor Anomaly"},
                )
            )

        return result, gt_records

    def generate_scenario_b_regional_event(
        self,
        df: pd.DataFrame,
        target_station_id: str,
        start_timestamp: Any,
        duration_steps: int = 6,
        temp_change_c: float = -4.5,
        rh_change_pct: float = 20.0,
        slp_change_hpa: float = -3.5,
        max_neighbor_distance_km: float = 600.0,
        station_id_col: str = "station_id",
        timestamp_col: str = "timestamp",
        anomaly_id: str = "SCEN-B-REGIONAL",
    ) -> Tuple[pd.DataFrame, List[GroundTruthRecord]]:
        """Scenario B: Coherent Regional Meteorological Event.
        
        A physical weather front (e.g. squall line / cold front) sweeps through the region,
        causing coherent physical shifts across the target station and all nearby neighbors.
        """
        result = df.copy()
        result[timestamp_col] = pd.to_datetime(result[timestamp_col], utc=True)
        t_start = pd.to_datetime(start_timestamp, utc=True)

        # Find eligible stations in the spatial neighborhood
        neighbor_links = self.topology.get_neighbors(
            target_station_id=target_station_id,
            max_distance_km=max_neighbor_distance_km,
            max_neighbors=10,
        )
        cluster_stations = [str(target_station_id)] + [str(link.neighbor_station_id) for link in neighbor_links]

        gt_records: List[GroundTruthRecord] = []
        rng = np.random.default_rng(42)

        for s_id in cluster_stations:
            stn_mask = (result[station_id_col].astype(str) == s_id) & (result[timestamp_col] >= t_start)
            stn_indices = result[stn_mask].index[:duration_steps]
            if len(stn_indices) == 0:
                continue

            t_end = result.loc[stn_indices[-1], timestamp_col]

            # Realistic spatial variance in event magnitude across the cluster
            stn_t_delta = temp_change_c * rng.uniform(0.85, 1.15)
            stn_rh_delta = rh_change_pct * rng.uniform(0.85, 1.15)
            stn_slp_delta = slp_change_hpa * rng.uniform(0.85, 1.15)

            for idx in stn_indices:
                orig_t = result.at[idx, "temperature_c"]
                if pd.notna(orig_t):
                    mod_t = float(orig_t) + stn_t_delta
                    result.at[idx, "temperature_c"] = mod_t
                    gt_records.append(
                        GroundTruthRecord(
                            anomaly_id=f"{anomaly_id}_{s_id}",
                            station_id=s_id,
                            timestamp=result.loc[idx, timestamp_col].to_pydatetime(),
                            anomaly_type=SyntheticAnomalyType.POSSIBLE_GENUINE_EVENT,
                            affected_variable="temperature_c",
                            original_value=float(orig_t),
                            modified_value=mod_t,
                            injection_start=t_start.to_pydatetime(),
                            injection_end=t_end.to_pydatetime(),
                            severity_parameter=abs(temp_change_c),
                            ground_truth_label=0,
                            is_fault=False,
                            metadata={"scenario": "Scenario B: Regional Event", "cluster_station": s_id},
                        )
                    )

                orig_rh = result.at[idx, "relative_humidity_pct"]
                if pd.notna(orig_rh):
                    mod_rh = min(100.0, max(0.0, float(orig_rh) + stn_rh_delta))
                    result.at[idx, "relative_humidity_pct"] = mod_rh

                orig_slp = result.at[idx, "sea_level_pressure_hpa"]
                if pd.notna(orig_slp):
                    mod_slp = float(orig_slp) + stn_slp_delta
                    result.at[idx, "sea_level_pressure_hpa"] = mod_slp

        return result, gt_records

    def generate_scenario_c_mixed_event(
        self,
        df: pd.DataFrame,
        target_station_id: str,
        start_timestamp: Any,
        duration_steps: int = 6,
        regional_temp_change_c: float = 3.5,
        target_fault_temp_delta: float = 7.0,
        max_neighbor_distance_km: float = 600.0,
        station_id_col: str = "station_id",
        timestamp_col: str = "timestamp",
        anomaly_id: str = "SCEN-C-MIXED",
    ) -> Tuple[pd.DataFrame, List[GroundTruthRecord]]:
        """Scenario C: Mixed Event (Regional Weather Event + Local Sensor Fault).
        
        All stations in the neighborhood experience a genuine regional warming event (+3.5°C),
        but the target station experiences an additional unphysical sensor spike/offset (+7.0°C).
        """
        # Step 1: Generate regional event across cluster
        res_regional, gt_regional = self.generate_scenario_b_regional_event(
            df=df,
            target_station_id=target_station_id,
            start_timestamp=start_timestamp,
            duration_steps=duration_steps,
            temp_change_c=regional_temp_change_c,
            rh_change_pct=-10.0,
            slp_change_hpa=1.0,
            max_neighbor_distance_km=max_neighbor_distance_km,
            station_id_col=station_id_col,
            timestamp_col=timestamp_col,
            anomaly_id=f"{anomaly_id}_REG",
        )

        # Step 2: Inject additional sensor fault on target station
        res_mixed, gt_target_fault = self.generate_scenario_a_local_anomaly(
            df=res_regional,
            target_station_id=target_station_id,
            start_timestamp=start_timestamp,
            duration_steps=duration_steps,
            magnitude=target_fault_temp_delta,
            variable="temperature_c",
            station_id_col=station_id_col,
            timestamp_col=timestamp_col,
            anomaly_id=f"{anomaly_id}_FAULT",
        )

        all_gt = gt_regional + gt_target_fault
        return res_mixed, all_gt

    def generate_scenario_d_isolated_outage(
        self,
        df: pd.DataFrame,
        target_station_id: str,
        start_timestamp: Any,
        duration_steps: int = 6,
        station_id_col: str = "station_id",
        timestamp_col: str = "timestamp",
    ) -> pd.DataFrame:
        """Scenario D: Isolated Station / Neighbor Outage.
        
        Drops all neighbor telemetry around the target station during the evaluation window,
        testing the engine's ability to safely return INSUFFICIENT_CONTEXT.
        """
        result = df.copy()
        result[timestamp_col] = pd.to_datetime(result[timestamp_col], utc=True)
        t_start = pd.to_datetime(start_timestamp, utc=True)

        # Mask out all neighbor data during the window
        mask = (result[station_id_col].astype(str) != str(target_station_id)) & (result[timestamp_col] >= t_start)
        neighbor_indices = result[mask].index[: duration_steps * 10]
        
        result.loc[neighbor_indices, ["temperature_c", "relative_humidity_pct", "sea_level_pressure_hpa"]] = np.nan
        return result
