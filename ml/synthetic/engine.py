"""Synthetic Anomaly Generation Engine for SkyGuard AI."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd
import yaml

from ml.synthetic.injectors import (
    BaseAnomalyInjector,
    CommunicationGapInjector,
    DriftInjector,
    DuplicateDataInjector,
    FrozenSensorInjector,
    IntermittentFreezeInjector,
    MissingDataInjector,
    MultivariateInconsistencyInjector,
    NegativeSpikeInjector,
    OffsetInjector,
    OutOfOrderDataInjector,
    RandomNoiseInjector,
    SmallSpikeInjector,
    SpikeInjector,
)
from ml.synthetic.scenarios import (
    CombinedFaultInjector,
    MultiSensorFaultInjector,
    PossibleGenuineEventScenario,
    UncertainScenario,
)
from ml.synthetic.schema import (
    AnomalyInjectionConfig,
    GroundTruthRecord,
    InjectedDatasetResult,
    SyntheticAnomalyType,
)


class SyntheticAnomalyEngine:
    """Orchestrates parameterized, reproducible anomaly injection into historical baseline datasets."""

    def __init__(self, config: Optional[AnomalyInjectionConfig] = None) -> None:
        self.config = config or AnomalyInjectionConfig()
        self.rng = np.random.default_rng(self.config.seed)
        self.yaml_config = self._load_yaml_config(self.config.config_file_path)

        # Register all 15 injector instances + 2 evaluation scenarios
        self.injectors: Dict[SyntheticAnomalyType, BaseAnomalyInjector] = {
            SyntheticAnomalyType.SPIKE: SpikeInjector(),
            SyntheticAnomalyType.SMALL_SPIKE: SmallSpikeInjector(),
            SyntheticAnomalyType.NEGATIVE_SPIKE: NegativeSpikeInjector(),
            SyntheticAnomalyType.DRIFT: DriftInjector(),
            SyntheticAnomalyType.OFFSET: OffsetInjector(),
            SyntheticAnomalyType.FROZEN_SENSOR: FrozenSensorInjector(),
            SyntheticAnomalyType.INTERMITTENT_FREEZE: IntermittentFreezeInjector(),
            SyntheticAnomalyType.MISSING_DATA: MissingDataInjector(),
            SyntheticAnomalyType.COMMUNICATION_GAP: CommunicationGapInjector(),
            SyntheticAnomalyType.DUPLICATE_DATA: DuplicateDataInjector(),
            SyntheticAnomalyType.OUT_OF_ORDER_DATA: OutOfOrderDataInjector(),
            SyntheticAnomalyType.RANDOM_NOISE: RandomNoiseInjector(),
            SyntheticAnomalyType.MULTIVARIATE_INCONSISTENCY: MultivariateInconsistencyInjector(),
            SyntheticAnomalyType.MULTI_SENSOR_FAULT: MultiSensorFaultInjector(),
            SyntheticAnomalyType.COMBINED_FAULT: CombinedFaultInjector(),
            SyntheticAnomalyType.POSSIBLE_GENUINE_EVENT: PossibleGenuineEventScenario(),
            SyntheticAnomalyType.UNCERTAIN: UncertainScenario(),
        }

    def _load_yaml_config(self, path_str: Optional[str]) -> Dict[str, Any]:
        """Safely load anomaly injection YAML configuration if present."""
        if not path_str:
            return {}
        p = Path(path_str)
        if p.is_file():
            with open(p, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        return {}

    def run_injection(
        self,
        df: pd.DataFrame,
        timestamp_col: str = "timestamp",
        station_id_col: str = "station_id",
    ) -> InjectedDatasetResult:
        """Run anomaly injection on a copy of the input observations DataFrame.
        
        Args:
            df: Pristine baseline observations.
            timestamp_col: Name of timestamp column.
            station_id_col: Name of station ID column.
            
        Returns:
            InjectedDatasetResult containing modified DataFrame and isolated ground truth table.
        """
        # Strict requirement: Never mutate raw input dataframe
        modified_df = df.copy()
        if modified_df.empty:
            return InjectedDatasetResult(
                modified_df=modified_df,
                ground_truth_df=pd.DataFrame(),
                experiment_id=self.config.experiment_id,
                seed=self.config.seed,
            )

        # Ensure timestamp is datetime and sorted
        modified_df[timestamp_col] = pd.to_datetime(modified_df[timestamp_col], utc=True)
        all_gt_records: List[GroundTruthRecord] = []
        anomaly_counter = 1

        # Determine target parameters
        default_params = ["temperature_c", "relative_humidity_pct", "sea_level_pressure_hpa"]
        avail_params = [p for p in default_params if p in modified_df.columns]
        if not avail_params and "temperature" in modified_df.columns:
            avail_params = ["temperature"]

        # If target stations specified, filter indices
        target_stations = self.config.target_stations or modified_df[station_id_col].unique().tolist()

        for anom_type in self.config.anomalies_to_inject:
            if anom_type not in self.injectors:
                continue

            injector = self.injectors[anom_type]
            config_key = anom_type.value.lower()
            inj_config = self.yaml_config.get("anomaly_types", {}).get(
                config_key,
                self.yaml_config.get("evaluation_scenarios", {}).get(config_key, {}),
            )

            for _ in range(self.config.num_anomalies_per_type):
                if len(modified_df) < 10:
                    break

                # Pick a random station and target index
                chosen_station = str(self.rng.choice(target_stations))
                stn_indices = modified_df[modified_df[station_id_col].astype(str) == chosen_station].index.tolist()
                if not stn_indices or len(stn_indices) < 8:
                    continue

                # Pick index with margin from end
                margin = min(50, len(stn_indices) // 2)
                target_idx = int(self.rng.choice(stn_indices[: max(1, len(stn_indices) - margin)]))
                param = str(self.rng.choice(avail_params)) if avail_params else "temperature_c"
                anomaly_id = f"ANOM-{anomaly_counter:06d}"

                res_df, gt_list = injector.inject(
                    df=modified_df,
                    target_idx=target_idx,
                    param=param,
                    anomaly_id=anomaly_id,
                    rng=self.rng,
                    config=inj_config,
                )

                if gt_list:
                    modified_df = res_df
                    all_gt_records.extend(gt_list)
                    anomaly_counter += 1

        # Convert ground truth records to DataFrame
        gt_dicts = [r.model_dump() for r in all_gt_records]
        ground_truth_df = pd.DataFrame(gt_dicts)

        return InjectedDatasetResult(
            modified_df=modified_df,
            ground_truth_df=ground_truth_df,
            experiment_id=self.config.experiment_id,
            seed=self.config.seed,
            metadata={
                "anomalies_injected_count": len(all_gt_records),
                "unique_anomaly_episodes": anomaly_counter - 1,
                "config_seed": self.config.seed,
            },
        )
