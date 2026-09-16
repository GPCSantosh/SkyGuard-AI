"""Complex multi-fault scenarios and genuine meteorological event evaluation generators."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import pandas as pd

from ml.synthetic.injectors import (
    BaseAnomalyInjector,
    DriftInjector,
    FrozenSensorInjector,
    MissingDataInjector,
    OffsetInjector,
    SpikeInjector,
)
from ml.synthetic.schema import GroundTruthRecord, SyntheticAnomalyType


class MultiSensorFaultInjector(BaseAnomalyInjector):
    """Injects faults across multiple physical sensors simultaneously (e.g. Temp Drift + RH Freeze)."""

    def __init__(self) -> None:
        super().__init__(SyntheticAnomalyType.MULTI_SENSOR_FAULT)
        self.temp_injector = DriftInjector()
        self.rh_injector = FrozenSensorInjector()

    def inject(
        self,
        df: pd.DataFrame,
        target_idx: int,
        param: str,
        anomaly_id: str,
        rng: np.random.Generator,
        config: Optional[Dict[str, Any]] = None,
    ) -> Tuple[pd.DataFrame, List[GroundTruthRecord]]:
        result_df = df.copy()
        gt_records: List[GroundTruthRecord] = []

        if target_idx >= len(df):
            return result_df, gt_records

        # 1. Primary fault: temperature drift
        if "temperature_c" in result_df.columns:
            res_temp, gt_temp = self.temp_injector.inject(
                result_df,
                target_idx=target_idx,
                param="temperature_c",
                anomaly_id=f"{anomaly_id}_TMP",
                rng=rng,
                config=config,
            )
            result_df = res_temp
            for r in gt_temp:
                gt_records.append(
                    GroundTruthRecord(
                        anomaly_id=anomaly_id,
                        station_id=r.station_id,
                        timestamp=r.timestamp,
                        anomaly_type=self.anomaly_type,
                        affected_variable="temperature_c",
                        original_value=r.original_value,
                        modified_value=r.modified_value,
                        injection_start=r.injection_start,
                        injection_end=r.injection_end,
                        severity_parameter=r.severity_parameter,
                        ground_truth_label=1,
                        is_fault=True,
                        metadata={"sub_fault": "temperature_drift"},
                    )
                )

        # 2. Secondary fault: humidity freeze
        if "relative_humidity_pct" in result_df.columns:
            res_rh, gt_rh = self.rh_injector.inject(
                result_df,
                target_idx=target_idx,
                param="relative_humidity_pct",
                anomaly_id=f"{anomaly_id}_RH",
                rng=rng,
                config=config,
            )
            result_df = res_rh
            for r in gt_rh:
                gt_records.append(
                    GroundTruthRecord(
                        anomaly_id=anomaly_id,
                        station_id=r.station_id,
                        timestamp=r.timestamp,
                        anomaly_type=self.anomaly_type,
                        affected_variable="relative_humidity_pct",
                        original_value=r.original_value,
                        modified_value=r.modified_value,
                        injection_start=r.injection_start,
                        injection_end=r.injection_end,
                        severity_parameter=r.severity_parameter,
                        ground_truth_label=1,
                        is_fault=True,
                        metadata={"sub_fault": "humidity_freeze"},
                    )
                )

        return result_df, gt_records


class CombinedFaultInjector(BaseAnomalyInjector):
    """Compound multi-stage sequential failure (e.g. Spike -> Missing Data -> Step Offset)."""

    def __init__(self) -> None:
        super().__init__(SyntheticAnomalyType.COMBINED_FAULT)
        self.spike_inj = SpikeInjector()
        self.missing_inj = MissingDataInjector()
        self.offset_inj = OffsetInjector()

    def inject(
        self,
        df: pd.DataFrame,
        target_idx: int,
        param: str,
        anomaly_id: str,
        rng: np.random.Generator,
        config: Optional[Dict[str, Any]] = None,
    ) -> Tuple[pd.DataFrame, List[GroundTruthRecord]]:
        result_df = df.copy()
        gt_records: List[GroundTruthRecord] = []

        if target_idx + 15 >= len(df):
            return result_df, gt_records

        # Stage 1: Spike at target_idx
        res_spike, gt_spike = self.spike_inj.inject(
            result_df, target_idx, "temperature_c", f"{anomaly_id}_STG1", rng, config
        )
        result_df = res_spike
        gt_records.extend(gt_spike)

        # Stage 2: Missing Data burst 3 steps later
        mid_idx = target_idx + 3
        if mid_idx < len(result_df):
            res_miss, gt_miss = self.missing_inj.inject(
                result_df, mid_idx, "temperature_c", f"{anomaly_id}_STG2", rng, config
            )
            result_df = res_miss
            gt_records.extend(gt_miss)

        # Stage 3: Step Offset
        late_idx = target_idx + 6
        if late_idx < len(result_df):
            res_off, gt_off = self.offset_inj.inject(
                result_df, late_idx, "temperature_c", f"{anomaly_id}_STG3", rng, config
            )
            result_df = res_off
            gt_records.extend(gt_off)

        return result_df, gt_records


class PossibleGenuineEventScenario(BaseAnomalyInjector):
    """Generates a physically coherent severe weather event (e.g., gust front / squall line).
    
    CRITICAL: Labeled with ground_truth_label = 0 (is_fault = False) to test system False Positive Rate.
    """

    def __init__(self) -> None:
        super().__init__(SyntheticAnomalyType.POSSIBLE_GENUINE_EVENT)

    def inject(
        self,
        df: pd.DataFrame,
        target_idx: int,
        param: str,
        anomaly_id: str,
        rng: np.random.Generator,
        config: Optional[Dict[str, Any]] = None,
    ) -> Tuple[pd.DataFrame, List[GroundTruthRecord]]:
        result_df = df.copy()
        gt_records: List[GroundTruthRecord] = []

        if target_idx >= len(df):
            return result_df, gt_records

        avail = len(df) - target_idx
        duration_steps = int(rng.integers(1, min(6, avail) + 1)) if avail >= 1 else 1
        # Squall physics: temperature drops, pressure rises, humidity jumps
        temp_drop = float(rng.uniform(4.0, 8.0))
        pressure_jump = float(rng.uniform(2.0, 5.0))
        rh_rise = float(rng.uniform(15.0, 30.0))

        t_start = pd.to_datetime(result_df.iloc[target_idx]["timestamp"], utc=True).to_pydatetime()
        t_end = pd.to_datetime(result_df.iloc[target_idx + duration_steps - 1]["timestamp"], utc=True).to_pydatetime()
        stn_id = str(result_df.iloc[target_idx]["station_id"])

        for step in range(duration_steps):
            idx = target_idx + step
            t_step = pd.to_datetime(result_df.iloc[idx]["timestamp"], utc=True).to_pydatetime()

            # Apply coherent meteorological gradient
            if "temperature_c" in result_df.columns and not pd.isna(result_df.at[idx, "temperature_c"]):
                orig_t = float(result_df.at[idx, "temperature_c"])
                mod_t = orig_t - temp_drop
                result_df.at[idx, "temperature_c"] = mod_t
                gt_records.append(
                    GroundTruthRecord(
                        anomaly_id=anomaly_id,
                        station_id=stn_id,
                        timestamp=t_step,
                        anomaly_type=self.anomaly_type,
                        affected_variable="temperature_c",
                        original_value=orig_t,
                        modified_value=mod_t,
                        injection_start=t_start,
                        injection_end=t_end,
                        severity_parameter=temp_drop,
                        ground_truth_label=0,  # NOT a fault
                        is_fault=False,
                        metadata={"phenomenon": "squall_gust_front", "coherent_vars": ["temperature", "pressure", "humidity"]},
                    )
                )

            if "sea_level_pressure_hpa" in result_df.columns and not pd.isna(result_df.at[idx, "sea_level_pressure_hpa"]):
                orig_p = float(result_df.at[idx, "sea_level_pressure_hpa"])
                result_df.at[idx, "sea_level_pressure_hpa"] = orig_p + pressure_jump

            if "relative_humidity_pct" in result_df.columns and not pd.isna(result_df.at[idx, "relative_humidity_pct"]):
                orig_rh = float(result_df.at[idx, "relative_humidity_pct"])
                result_df.at[idx, "relative_humidity_pct"] = min(100.0, orig_rh + rh_rise)

        return result_df, gt_records


class UncertainScenario(BaseAnomalyInjector):
    """Generates an ambiguous borderline reading for calibration and uncertainty testing."""

    def __init__(self) -> None:
        super().__init__(SyntheticAnomalyType.UNCERTAIN)

    def inject(
        self,
        df: pd.DataFrame,
        target_idx: int,
        param: str,
        anomaly_id: str,
        rng: np.random.Generator,
        config: Optional[Dict[str, Any]] = None,
    ) -> Tuple[pd.DataFrame, List[GroundTruthRecord]]:
        result_df = df.copy()
        gt_records: List[GroundTruthRecord] = []

        if target_idx >= len(df) or param not in df.columns:
            return result_df, gt_records

        orig_val = result_df.at[target_idx, param]
        if pd.isna(orig_val):
            return result_df, gt_records

        # Borderline deviation
        delta = float(rng.uniform(1.2, 2.5))
        orig_val_f = float(orig_val)
        mod_val_f = orig_val_f + delta
        result_df.at[target_idx, param] = mod_val_f

        t_step = pd.to_datetime(result_df.iloc[target_idx]["timestamp"], utc=True).to_pydatetime()
        stn_id = str(result_df.iloc[target_idx]["station_id"])

        gt_records.append(
            GroundTruthRecord(
                anomaly_id=anomaly_id,
                station_id=stn_id,
                timestamp=t_step,
                anomaly_type=self.anomaly_type,
                affected_variable=param,
                original_value=orig_val_f,
                modified_value=mod_val_f,
                injection_start=t_step,
                injection_end=t_step,
                severity_parameter=delta,
                ground_truth_label=0,  # Ambiguous / Non-definite fault
                is_fault=False,
                metadata={"evaluation_class": "UNCERTAIN"},
            )
        )
        return result_df, gt_records
