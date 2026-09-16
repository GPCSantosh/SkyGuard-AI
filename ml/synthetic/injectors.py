"""Individual anomaly injection algorithms for all 15 operational categories."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import pandas as pd

from ml.synthetic.schema import GroundTruthRecord, SyntheticAnomalyType


def safe_integers(rng: np.random.Generator, low: int, high: int, max_limit: int) -> int:
    """Safely sample an integer between [low, high] bounded by max_limit without raising low >= high."""
    upper = min(high, max_limit)
    if upper <= low:
        return max(1, upper)
    return int(rng.integers(low, upper + 1))


class BaseAnomalyInjector(ABC):
    """Abstract base class for all synthetic fault injectors."""

    def __init__(self, anomaly_type: SyntheticAnomalyType) -> None:
        self.anomaly_type = anomaly_type

    @abstractmethod
    def inject(
        self,
        df: pd.DataFrame,
        target_idx: int,
        param: str,
        anomaly_id: str,
        rng: np.random.Generator,
        config: Optional[Dict[str, Any]] = None,
    ) -> Tuple[pd.DataFrame, List[GroundTruthRecord]]:
        """Inject anomaly into a copy of df starting at target_idx."""
        pass


class SpikeInjector(BaseAnomalyInjector):
    """Injects high-magnitude single-step or short burst impulses."""

    def __init__(self, anomaly_type: SyntheticAnomalyType = SyntheticAnomalyType.SPIKE) -> None:
        super().__init__(anomaly_type)

    def inject(
        self,
        df: pd.DataFrame,
        target_idx: int,
        param: str,
        anomaly_id: str,
        rng: np.random.Generator,
        config: Optional[Dict[str, Any]] = None,
    ) -> Tuple[pd.DataFrame, List[GroundTruthRecord]]:
        config = config or {}
        result_df = df.copy()
        gt_records: List[GroundTruthRecord] = []

        if target_idx >= len(df) or param not in df.columns:
            return result_df, gt_records

        mag_range = config.get("magnitude_range", {}).get(param, [5.0, 15.0])
        burst_len_range = config.get("burst_length_steps", [1, 2])
        direction = config.get("direction", "positive")

        avail = len(df) - target_idx
        burst_len = safe_integers(rng, burst_len_range[0], burst_len_range[1], avail)
        
        raw_mag = float(rng.uniform(mag_range[0], mag_range[1]))
        mag = -abs(raw_mag) if direction == "negative" else abs(raw_mag)

        t_start = pd.to_datetime(result_df.iloc[target_idx]["timestamp"], utc=True).to_pydatetime()
        t_end = pd.to_datetime(result_df.iloc[target_idx + burst_len - 1]["timestamp"], utc=True).to_pydatetime()
        stn_id = str(result_df.iloc[target_idx]["station_id"])

        for step in range(burst_len):
            idx = target_idx + step
            orig_val = result_df.at[idx, param]
            if pd.isna(orig_val):
                continue
            orig_val_f = float(orig_val)
            mod_val_f = orig_val_f + mag
            result_df.at[idx, param] = mod_val_f

            t_step = pd.to_datetime(result_df.iloc[idx]["timestamp"], utc=True).to_pydatetime()
            gt_records.append(
                GroundTruthRecord(
                    anomaly_id=anomaly_id,
                    station_id=stn_id,
                    timestamp=t_step,
                    anomaly_type=self.anomaly_type,
                    affected_variable=param,
                    original_value=orig_val_f,
                    modified_value=mod_val_f,
                    injection_start=t_start,
                    injection_end=t_end,
                    severity_parameter=mag,
                    ground_truth_label=1,
                    is_fault=True,
                    metadata={"step_in_burst": step + 1, "burst_length": burst_len},
                )
            )

        return result_df, gt_records


class SmallSpikeInjector(SpikeInjector):
    """Injects subtle low-amplitude spikes (+0.5°C to +2.0°C) to test filter sensitivity."""

    def __init__(self) -> None:
        super().__init__(SyntheticAnomalyType.SMALL_SPIKE)


class NegativeSpikeInjector(SpikeInjector):
    """Injects large negative impulses."""

    def __init__(self) -> None:
        super().__init__(SyntheticAnomalyType.NEGATIVE_SPIKE)


class DriftInjector(BaseAnomalyInjector):
    """Injects gradual linear drift slope across consecutive observations."""

    def __init__(self) -> None:
        super().__init__(SyntheticAnomalyType.DRIFT)

    def inject(
        self,
        df: pd.DataFrame,
        target_idx: int,
        param: str,
        anomaly_id: str,
        rng: np.random.Generator,
        config: Optional[Dict[str, Any]] = None,
    ) -> Tuple[pd.DataFrame, List[GroundTruthRecord]]:
        config = config or {}
        result_df = df.copy()
        gt_records: List[GroundTruthRecord] = []

        if target_idx >= len(df) or param not in df.columns:
            return result_df, gt_records

        slope_range = config.get("slope_per_hour", {}).get(param, [0.1, 0.5])
        slope_per_hour = float(rng.uniform(slope_range[0], slope_range[1]))
        if config.get("direction", "both") == "both" and rng.random() < 0.5:
            slope_per_hour = -slope_per_hour

        avail = len(df) - target_idx
        duration_steps = safe_integers(rng, 6, 48, avail)

        t_start = pd.to_datetime(result_df.iloc[target_idx]["timestamp"], utc=True).to_pydatetime()
        t_end = pd.to_datetime(result_df.iloc[target_idx + duration_steps - 1]["timestamp"], utc=True).to_pydatetime()
        stn_id = str(result_df.iloc[target_idx]["station_id"])

        for step in range(duration_steps):
            idx = target_idx + step
            orig_val = result_df.at[idx, param]
            if pd.isna(orig_val):
                continue

            t_step = pd.to_datetime(result_df.iloc[idx]["timestamp"], utc=True).to_pydatetime()
            elapsed_hours = (t_step - t_start).total_seconds() / 3600.0
            if elapsed_hours <= 0.0:
                elapsed_hours = (step * 5.0) / 60.0

            drift_delta = slope_per_hour * elapsed_hours
            orig_val_f = float(orig_val)
            mod_val_f = orig_val_f + drift_delta
            result_df.at[idx, param] = mod_val_f

            gt_records.append(
                GroundTruthRecord(
                    anomaly_id=anomaly_id,
                    station_id=stn_id,
                    timestamp=t_step,
                    anomaly_type=self.anomaly_type,
                    affected_variable=param,
                    original_value=orig_val_f,
                    modified_value=mod_val_f,
                    injection_start=t_start,
                    injection_end=t_end,
                    severity_parameter=slope_per_hour,
                    ground_truth_label=1,
                    is_fault=True,
                    metadata={"drift_delta": drift_delta, "elapsed_hours": elapsed_hours},
                )
            )

        return result_df, gt_records


class OffsetInjector(BaseAnomalyInjector):
    """Injects sudden persistent step offset jump."""

    def __init__(self) -> None:
        super().__init__(SyntheticAnomalyType.OFFSET)

    def inject(
        self,
        df: pd.DataFrame,
        target_idx: int,
        param: str,
        anomaly_id: str,
        rng: np.random.Generator,
        config: Optional[Dict[str, Any]] = None,
    ) -> Tuple[pd.DataFrame, List[GroundTruthRecord]]:
        config = config or {}
        result_df = df.copy()
        gt_records: List[GroundTruthRecord] = []

        if target_idx >= len(df) or param not in df.columns:
            return result_df, gt_records

        offset_range = config.get("offset_magnitude", {}).get(param, [3.0, 8.0])
        offset = float(rng.uniform(offset_range[0], offset_range[1]))
        if rng.random() < 0.5:
            offset = -offset

        avail = len(df) - target_idx
        duration_steps = safe_integers(rng, 5, 50, avail)

        t_start = pd.to_datetime(result_df.iloc[target_idx]["timestamp"], utc=True).to_pydatetime()
        t_end = pd.to_datetime(result_df.iloc[target_idx + duration_steps - 1]["timestamp"], utc=True).to_pydatetime()
        stn_id = str(result_df.iloc[target_idx]["station_id"])

        for step in range(duration_steps):
            idx = target_idx + step
            orig_val = result_df.at[idx, param]
            if pd.isna(orig_val):
                continue
            orig_val_f = float(orig_val)
            mod_val_f = orig_val_f + offset
            result_df.at[idx, param] = mod_val_f

            t_step = pd.to_datetime(result_df.iloc[idx]["timestamp"], utc=True).to_pydatetime()
            gt_records.append(
                GroundTruthRecord(
                    anomaly_id=anomaly_id,
                    station_id=stn_id,
                    timestamp=t_step,
                    anomaly_type=self.anomaly_type,
                    affected_variable=param,
                    original_value=orig_val_f,
                    modified_value=mod_val_f,
                    injection_start=t_start,
                    injection_end=t_end,
                    severity_parameter=offset,
                    ground_truth_label=1,
                    is_fault=True,
                )
            )

        return result_df, gt_records


class FrozenSensorInjector(BaseAnomalyInjector):
    """Holds a sensor value constant over multiple consecutive observations."""

    def __init__(self) -> None:
        super().__init__(SyntheticAnomalyType.FROZEN_SENSOR)

    def inject(
        self,
        df: pd.DataFrame,
        target_idx: int,
        param: str,
        anomaly_id: str,
        rng: np.random.Generator,
        config: Optional[Dict[str, Any]] = None,
    ) -> Tuple[pd.DataFrame, List[GroundTruthRecord]]:
        config = config or {}
        result_df = df.copy()
        gt_records: List[GroundTruthRecord] = []

        if target_idx >= len(df) or param not in df.columns:
            return result_df, gt_records

        duration_range = config.get("duration_steps", [6, 24])
        avail = len(df) - target_idx
        duration_steps = safe_integers(rng, duration_range[0], duration_range[1], avail)

        freeze_val = result_df.at[target_idx, param]
        if pd.isna(freeze_val):
            return result_df, gt_records
        freeze_val_f = float(freeze_val)

        t_start = pd.to_datetime(result_df.iloc[target_idx]["timestamp"], utc=True).to_pydatetime()
        t_end = pd.to_datetime(result_df.iloc[target_idx + duration_steps - 1]["timestamp"], utc=True).to_pydatetime()
        stn_id = str(result_df.iloc[target_idx]["station_id"])

        for step in range(duration_steps):
            idx = target_idx + step
            orig_val = result_df.at[idx, param]
            orig_val_f = float(orig_val) if not pd.isna(orig_val) else freeze_val_f
            result_df.at[idx, param] = freeze_val_f

            t_step = pd.to_datetime(result_df.iloc[idx]["timestamp"], utc=True).to_pydatetime()
            gt_records.append(
                GroundTruthRecord(
                    anomaly_id=anomaly_id,
                    station_id=stn_id,
                    timestamp=t_step,
                    anomaly_type=self.anomaly_type,
                    affected_variable=param,
                    original_value=orig_val_f,
                    modified_value=freeze_val_f,
                    injection_start=t_start,
                    injection_end=t_end,
                    severity_parameter=float(duration_steps),
                    ground_truth_label=1,
                    is_fault=True,
                    metadata={"frozen_value": freeze_val_f},
                )
            )

        return result_df, gt_records


class IntermittentFreezeInjector(BaseAnomalyInjector):
    """Alternates between valid dynamic readings and frozen constant slices."""

    def __init__(self) -> None:
        super().__init__(SyntheticAnomalyType.INTERMITTENT_FREEZE)

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

        slice_len = 3
        repetitions = 3
        total_span = (slice_len * 2) * repetitions
        if target_idx + total_span > len(df):
            total_span = len(df) - target_idx

        t_start = pd.to_datetime(result_df.iloc[target_idx]["timestamp"], utc=True).to_pydatetime()
        t_end = pd.to_datetime(result_df.iloc[target_idx + total_span - 1]["timestamp"], utc=True).to_pydatetime()
        stn_id = str(result_df.iloc[target_idx]["station_id"])

        curr_idx = target_idx
        for rep in range(repetitions):
            if curr_idx >= len(df):
                break
            freeze_val = result_df.at[curr_idx, param]
            if pd.isna(freeze_val):
                curr_idx += slice_len * 2
                continue
            freeze_val_f = float(freeze_val)

            for step in range(min(slice_len, len(df) - curr_idx)):
                idx = curr_idx + step
                orig_val = result_df.at[idx, param]
                orig_val_f = float(orig_val) if not pd.isna(orig_val) else freeze_val_f
                result_df.at[idx, param] = freeze_val_f
                t_step = pd.to_datetime(result_df.iloc[idx]["timestamp"], utc=True).to_pydatetime()

                gt_records.append(
                    GroundTruthRecord(
                        anomaly_id=anomaly_id,
                        station_id=stn_id,
                        timestamp=t_step,
                        anomaly_type=self.anomaly_type,
                        affected_variable=param,
                        original_value=orig_val_f,
                        modified_value=freeze_val_f,
                        injection_start=t_start,
                        injection_end=t_end,
                        severity_parameter=float(slice_len),
                        ground_truth_label=1,
                        is_fault=True,
                        metadata={"repetition": rep + 1},
                    )
                )
            curr_idx += slice_len * 2

        return result_df, gt_records


class MissingDataInjector(BaseAnomalyInjector):
    """Drops observation rows non-destructively on dataset copies."""

    def __init__(self) -> None:
        super().__init__(SyntheticAnomalyType.MISSING_DATA)

    def inject(
        self,
        df: pd.DataFrame,
        target_idx: int,
        param: str,
        anomaly_id: str,
        rng: np.random.Generator,
        config: Optional[Dict[str, Any]] = None,
    ) -> Tuple[pd.DataFrame, List[GroundTruthRecord]]:
        config = config or {}
        gt_records: List[GroundTruthRecord] = []

        if target_idx >= len(df) or len(df) <= 5:
            return df.copy(), gt_records

        burst_range = config.get("burst_size", [3, 12])
        avail = len(df) - target_idx
        max_droppable = max(1, len(df) - 5)
        burst_size = safe_integers(rng, burst_range[0], min(burst_range[1], max_droppable), avail)
        stn_id = str(df.iloc[target_idx]["station_id"])
        t_start = pd.to_datetime(df.iloc[target_idx]["timestamp"], utc=True).to_pydatetime()
        t_end = pd.to_datetime(df.iloc[target_idx + burst_size - 1]["timestamp"], utc=True).to_pydatetime()

        indices_to_drop: List[int] = []
        for step in range(burst_size):
            idx = target_idx + step
            indices_to_drop.append(idx)
            t_step = pd.to_datetime(df.iloc[idx]["timestamp"], utc=True).to_pydatetime()
            orig_val = df.at[idx, param] if param in df.columns else None

            gt_records.append(
                GroundTruthRecord(
                    anomaly_id=anomaly_id,
                    station_id=stn_id,
                    timestamp=t_step,
                    anomaly_type=self.anomaly_type,
                    affected_variable="all_parameters",
                    original_value=float(orig_val) if orig_val is not None and not pd.isna(orig_val) else None,
                    modified_value=None,
                    injection_start=t_start,
                    injection_end=t_end,
                    severity_parameter=float(burst_size),
                    ground_truth_label=1,
                    is_fault=True,
                    metadata={"dropped_index": idx},
                )
            )

        result_df = df.drop(index=indices_to_drop).reset_index(drop=True)
        return result_df, gt_records


class CommunicationGapInjector(MissingDataInjector):
    """Simulates multi-hour network outage dropping a station's records."""

    def __init__(self) -> None:
        super().__init__()
        self.anomaly_type = SyntheticAnomalyType.COMMUNICATION_GAP


class DuplicateDataInjector(BaseAnomalyInjector):
    """Duplicates observations with preserved provenance."""

    def __init__(self) -> None:
        super().__init__(SyntheticAnomalyType.DUPLICATE_DATA)

    def inject(
        self,
        df: pd.DataFrame,
        target_idx: int,
        param: str,
        anomaly_id: str,
        rng: np.random.Generator,
        config: Optional[Dict[str, Any]] = None,
    ) -> Tuple[pd.DataFrame, List[GroundTruthRecord]]:
        gt_records: List[GroundTruthRecord] = []
        if target_idx >= len(df):
            return df.copy(), gt_records

        row_to_dup = df.iloc[target_idx].copy()
        stn_id = str(row_to_dup["station_id"])
        t_step = pd.to_datetime(row_to_dup["timestamp"], utc=True).to_pydatetime()
        orig_val = row_to_dup.get(param, None)

        gt_records.append(
            GroundTruthRecord(
                anomaly_id=anomaly_id,
                station_id=stn_id,
                timestamp=t_step,
                anomaly_type=self.anomaly_type,
                affected_variable=param,
                original_value=float(orig_val) if orig_val is not None and not pd.isna(orig_val) else None,
                modified_value=float(orig_val) if orig_val is not None and not pd.isna(orig_val) else None,
                injection_start=t_step,
                injection_end=t_step,
                severity_parameter=1.0,
                ground_truth_label=1,
                is_fault=True,
            )
        )

        top_part = df.iloc[: target_idx + 1]
        bottom_part = df.iloc[target_idx + 1 :]
        result_df = pd.concat([top_part, pd.DataFrame([row_to_dup]), bottom_part], ignore_index=True)
        return result_df, gt_records


class OutOfOrderDataInjector(BaseAnomalyInjector):
    """Permutes/shuffles row sequence on copies without modifying raw source."""

    def __init__(self) -> None:
        super().__init__(SyntheticAnomalyType.OUT_OF_ORDER_DATA)

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
        window_size = 4
        if target_idx + window_size > len(df):
            window_size = len(df) - target_idx
        if window_size < 2:
            return result_df, gt_records

        stn_id = str(result_df.iloc[target_idx]["station_id"])
        t_start = pd.to_datetime(result_df.iloc[target_idx]["timestamp"], utc=True).to_pydatetime()
        t_end = pd.to_datetime(result_df.iloc[target_idx + window_size - 1]["timestamp"], utc=True).to_pydatetime()

        row_a = result_df.iloc[target_idx].copy()
        row_b = result_df.iloc[target_idx + 1].copy()
        result_df.iloc[target_idx] = row_b
        result_df.iloc[target_idx + 1] = row_a

        gt_records.append(
            GroundTruthRecord(
                anomaly_id=anomaly_id,
                station_id=stn_id,
                timestamp=pd.to_datetime(row_a["timestamp"], utc=True).to_pydatetime(),
                anomaly_type=self.anomaly_type,
                affected_variable="timestamp_order",
                original_value=None,
                modified_value=None,
                injection_start=t_start,
                injection_end=t_end,
                severity_parameter=float(window_size),
                ground_truth_label=1,
                is_fault=True,
            )
        )
        return result_df, gt_records


class RandomNoiseInjector(BaseAnomalyInjector):
    """Injects high-frequency Gaussian noise degrading sensor signal-to-noise ratio."""

    def __init__(self) -> None:
        super().__init__(SyntheticAnomalyType.RANDOM_NOISE)

    def inject(
        self,
        df: pd.DataFrame,
        target_idx: int,
        param: str,
        anomaly_id: str,
        rng: np.random.Generator,
        config: Optional[Dict[str, Any]] = None,
    ) -> Tuple[pd.DataFrame, List[GroundTruthRecord]]:
        config = config or {}
        result_df = df.copy()
        gt_records: List[GroundTruthRecord] = []

        if target_idx >= len(df) or param not in df.columns:
            return result_df, gt_records

        noise_std = float(config.get("noise_std", {}).get(param, 2.0))
        avail = len(df) - target_idx
        duration_steps = safe_integers(rng, 6, 24, avail)

        t_start = pd.to_datetime(result_df.iloc[target_idx]["timestamp"], utc=True).to_pydatetime()
        t_end = pd.to_datetime(result_df.iloc[target_idx + duration_steps - 1]["timestamp"], utc=True).to_pydatetime()
        stn_id = str(result_df.iloc[target_idx]["station_id"])

        for step in range(duration_steps):
            idx = target_idx + step
            orig_val = result_df.at[idx, param]
            if pd.isna(orig_val):
                continue

            noise = float(rng.normal(0.0, noise_std))
            orig_val_f = float(orig_val)
            mod_val_f = orig_val_f + noise
            result_df.at[idx, param] = mod_val_f

            t_step = pd.to_datetime(result_df.iloc[idx]["timestamp"], utc=True).to_pydatetime()
            gt_records.append(
                GroundTruthRecord(
                    anomaly_id=anomaly_id,
                    station_id=stn_id,
                    timestamp=t_step,
                    anomaly_type=self.anomaly_type,
                    affected_variable=param,
                    original_value=orig_val_f,
                    modified_value=mod_val_f,
                    injection_start=t_start,
                    injection_end=t_end,
                    severity_parameter=noise_std,
                    ground_truth_label=1,
                    is_fault=True,
                )
            )

        return result_df, gt_records


class MultivariateInconsistencyInjector(BaseAnomalyInjector):
    """Creates controlled multi-parameter physical divergence (e.g. large temp jump with stagnant RH)."""

    def __init__(self) -> None:
        super().__init__(SyntheticAnomalyType.MULTIVARIATE_INCONSISTENCY)

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
        duration_steps = safe_integers(rng, 2, 8, avail)
        temp_delta = float(rng.uniform(6.0, 12.0))

        t_start = pd.to_datetime(result_df.iloc[target_idx]["timestamp"], utc=True).to_pydatetime()
        t_end = pd.to_datetime(result_df.iloc[target_idx + duration_steps - 1]["timestamp"], utc=True).to_pydatetime()
        stn_id = str(result_df.iloc[target_idx]["station_id"])

        for step in range(duration_steps):
            idx = target_idx + step
            t_step = pd.to_datetime(result_df.iloc[idx]["timestamp"], utc=True).to_pydatetime()

            if "temperature_c" in result_df.columns:
                orig_t = result_df.at[idx, "temperature_c"]
                if not pd.isna(orig_t):
                    mod_t = float(orig_t) + temp_delta
                    result_df.at[idx, "temperature_c"] = mod_t
                    gt_records.append(
                        GroundTruthRecord(
                            anomaly_id=anomaly_id,
                            station_id=stn_id,
                            timestamp=t_step,
                            anomaly_type=self.anomaly_type,
                            affected_variable="temperature_c",
                            original_value=float(orig_t),
                            modified_value=mod_t,
                            injection_start=t_start,
                            injection_end=t_end,
                            severity_parameter=temp_delta,
                            ground_truth_label=1,
                            is_fault=True,
                            metadata={"divergence_type": "temp_jump_rh_static"},
                        )
                    )

        return result_df, gt_records
