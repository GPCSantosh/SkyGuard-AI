"""Deterministic Anomaly Injection Engine for Synthetic AWS Network.

Applies controlled meteorological faults, physical boundary violations, data-quality errors,
and regional genuine events to baseline observations, generating an isolated ground-truth event registry.
"""

from __future__ import annotations

import copy
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np

from backend.app.models.observation import (
    ObservationSource,
    QualityStatus,
    WeatherObservation,
)
from synthetic_validation.scenarios.definitions import (
    SCENARIO_DEFINITIONS,
    ScenarioDefinition,
    get_scenario_by_id,
)


class SyntheticAnomalyInjector:
    """Injects deterministic anomalies into synthetic baseline observations without polluting model features."""

    def __init__(self, seed: int = 42) -> None:
        self.seed = seed
        self.rng = np.random.RandomState(seed)

    def inject_all_scenarios(
        self,
        baseline_observations: List[WeatherObservation],
        scenarios: Optional[List[ScenarioDefinition]] = None,
    ) -> Tuple[List[WeatherObservation], List[Dict[str, Any]]]:
        """Inject all registered validation scenarios into the baseline dataset sequentially.
        
        Returns:
            Tuple of (injected_observations, ground_truth_events)
        """
        if scenarios is None:
            scenarios = SCENARIO_DEFINITIONS

        # Work on deepcopy to guarantee baseline immutability
        injected_obs: List[WeatherObservation] = list(baseline_observations)
        ground_truth_registry: List[Dict[str, Any]] = []

        # Map by (station_id, step_index or timestamp) for rapid lookup
        # Step indices are recorded in metadata["step_index"]
        obs_by_station_step: Dict[Tuple[str, int], WeatherObservation] = {}
        for obs in injected_obs:
            step = obs.metadata.get("step_index", 0) if obs.metadata else 0
            obs_by_station_step[(obs.station_id, step)] = obs

        event_counter = 0

        for sc in scenarios:
            if sc.anomaly_type == "NONE":
                continue

            for s_id in sc.target_stations:
                for step in range(sc.injection_start_step, sc.injection_end_step + 1):
                    key = (s_id, step)
                    if key not in obs_by_station_step:
                        continue

                    orig_obs = obs_by_station_step[key]
                    injected_entry, truth_record = self._apply_single_injection(
                        scenario=sc,
                        orig_obs=orig_obs,
                        step=step,
                        event_num=event_counter + 1,
                    )
                    if injected_entry is not None:
                        obs_by_station_step[key] = injected_entry
                    if truth_record is not None:
                        event_counter += 1
                        ground_truth_registry.append(truth_record)

        # Re-assemble observation list in transmission/arrival sequence (step_index)
        final_obs_list = sorted(obs_by_station_step.values(), key=lambda o: (o.metadata.get("step_index", 0) if o.metadata else 0, o.station_id))
        return final_obs_list, ground_truth_registry

    def _apply_single_injection(
        self,
        scenario: ScenarioDefinition,
        orig_obs: WeatherObservation,
        step: int,
        event_num: int,
    ) -> Tuple[Optional[WeatherObservation], Optional[Dict[str, Any]]]:
        """Apply specific fault transform to a single observation instance."""
        anom_type = scenario.anomaly_type
        params = scenario.parameters or {}

        orig_temp = orig_obs.temperature
        orig_rh = orig_obs.humidity
        orig_slp = orig_obs.pressure

        new_temp = orig_temp
        new_rh = orig_rh
        new_slp = orig_slp
        new_qc = orig_obs.data_quality_status
        new_ts = orig_obs.timestamp

        # 1. Positive Spike
        if anom_type == "SPIKE_POSITIVE":
            delta = float(params.get("delta_temp_c", 12.0))
            new_temp = round(float(orig_temp + delta), 2) if orig_temp is not None else 35.0

        # 2. Negative Drop
        elif anom_type == "SPIKE_NEGATIVE":
            delta = float(params.get("delta_temp_c", -15.0))
            new_temp = round(float(orig_temp + delta), 2) if orig_temp is not None else 5.0

        # 3. Step Change
        elif anom_type == "STEP_CHANGE":
            delta = float(params.get("delta_temp_c", 8.0))
            new_temp = round(float(orig_temp + delta), 2) if orig_temp is not None else 30.0

        # 4. Drift
        elif anom_type == "DRIFT":
            rate = float(params.get("drift_rate_c_per_step", 0.3))
            offset_steps = step - scenario.injection_start_step + 1
            new_temp = round(float(orig_temp + (rate * offset_steps)), 2) if orig_temp is not None else 25.0

        # 5. Flatline / Frozen Sensor
        elif anom_type == "FLATLINE":
            # Clamp to constant values throughout frozen period
            new_temp = 24.50
            new_rh = 60.00
            new_slp = 1013.25

        # 6. Oscillation
        elif anom_type == "OSCILLATION":
            amp = float(params.get("amplitude_c", 7.5))
            sign = 1.0 if (step % 2 == 0) else -1.0
            new_temp = round(float(orig_temp + (sign * amp)), 2) if orig_temp is not None else 25.0

        # 7. Rate of Change Violation
        elif anom_type == "RATE_OF_CHANGE_VIOLATION":
            jump = float(params.get("jump_c", 9.5))
            new_temp = round(float(orig_temp + jump), 2) if orig_temp is not None else 35.0

        # 8. Impossible Temperature
        elif anom_type == "IMPOSSIBLE_TEMPERATURE":
            new_temp = 59.80  # Extreme near-limit physical reading
            new_qc = QualityStatus.ERROR

        # 9. Invalid RH
        elif anom_type == "INVALID_RH":
            new_rh = 99.90
            new_qc = QualityStatus.ERROR

        # 10. Invalid Pressure
        elif anom_type == "INVALID_PRESSURE":
            new_slp = 875.00
            new_qc = QualityStatus.ERROR

        # 11. Missing Temperature
        elif anom_type == "MISSING_TEMPERATURE":
            new_temp = None
            new_qc = QualityStatus.MISSING

        # 12. Missing RH
        elif anom_type == "MISSING_RH":
            new_rh = None
            new_qc = QualityStatus.MISSING

        # 13. Missing Pressure
        elif anom_type == "MISSING_PRESSURE":
            new_slp = None
            new_qc = QualityStatus.MISSING

        # 14. Multivariate Inconsistency
        elif anom_type == "MULTIVARIATE_INCONSISTENCY":
            new_temp = float(params.get("temp_c", 42.0))
            new_rh = float(params.get("rh_pct", 98.0))

        # 15. Spatial Outlier
        elif anom_type == "SPATIAL_OUTLIER":
            offset = float(params.get("temp_offset_c", 10.5))
            new_temp = round(float(orig_temp + offset), 2) if orig_temp is not None else 35.0

        # 16. Regional Event (Cold pool / Squall)
        elif anom_type == "REGIONAL_EVENT":
            t_drop = float(params.get("temp_drop_c", -8.0))
            rh_surge = float(params.get("rh_surge_pct", 28.0))
            slp_jump = float(params.get("slp_jump_hpa", 3.5))
            new_temp = round(float(orig_temp + t_drop), 2) if orig_temp is not None else 18.0
            new_rh = round(float(np.clip(orig_rh + rh_surge, 10.0, 98.0)), 2) if orig_rh is not None else 85.0
            new_slp = round(float(orig_slp + slp_jump), 2) if orig_slp is not None else 1015.0

        # 17. Out of Order Observation
        elif anom_type == "OUT_OF_ORDER":
            delay = int(params.get("delay_minutes", 30))
            new_ts = orig_obs.timestamp - timedelta(minutes=delay)
            new_qc = QualityStatus.SUSPECT

        # Construct updated WeatherObservation instance
        # Notice: No truth labels or scenario metadata are injected into detector-consumed fields
        updated_obs = WeatherObservation(
            station_id=orig_obs.station_id,
            station_name=orig_obs.station_name,
            latitude=orig_obs.latitude,
            longitude=orig_obs.longitude,
            elevation=orig_obs.elevation,
            timestamp=new_ts,
            temperature=new_temp,
            dew_point_c=orig_obs.dew_point_c,
            humidity=new_rh,
            pressure=new_slp,
            source=orig_obs.source,
            data_quality_status=new_qc,
            is_synthetic=True,
            metadata={"step_index": step},
        )

        truth_record = {
            "event_id": f"TRUTH-{scenario.scenario_id}-{orig_obs.station_id}-{event_num:04d}",
            "scenario_id": scenario.scenario_id,
            "scenario_name": scenario.name,
            "station_id": orig_obs.station_id,
            "timestamp": orig_obs.timestamp.isoformat(),
            "step_index": step,
            "anomaly_type": anom_type,
            "original_values": {
                "temperature_c": orig_temp,
                "relative_humidity_pct": orig_rh,
                "sea_level_pressure_hpa": orig_slp,
            },
            "injected_values": {
                "temperature_c": new_temp,
                "relative_humidity_pct": new_rh,
                "sea_level_pressure_hpa": new_slp,
            },
            "expected_decision": scenario.expected_decision,
            "accepted_decisions": scenario.accepted_decisions,
            "expected_sensor_health_direction": scenario.expected_sensor_health_direction,
            "expected_source_health": scenario.expected_source_health,
            "expected_correction": scenario.expected_correction,
            "expected_qc_status": scenario.expected_qc_status,
        }

        return updated_obs, truth_record
