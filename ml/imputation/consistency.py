"""Multivariate physical and thermodynamic consistency validator for candidate corrections."""

from __future__ import annotations

import math
from typing import Dict, List, Optional, Tuple

from backend.app.core.meteorology import (
    calculate_relative_humidity,
    is_physically_consistent_trio,
    sea_level_to_station_pressure,
    station_to_sea_level_pressure,
)
from ml.imputation.uncertainty import VARIABLE_BOUNDS


class MultivariateConsistencyChecker:
    """Validates that candidate corrections across multiple meteorological channels
    do not produce physically or thermodynamically contradictory station states.
    """

    def __init__(
        self,
        dew_point_tolerance_c: float = 0.2,
        rh_tolerance_pct: float = 15.0,
        pressure_tolerance_hpa: float = 6.0,
    ) -> None:
        self.dew_point_tolerance_c = dew_point_tolerance_c
        self.rh_tolerance_pct = rh_tolerance_pct
        self.pressure_tolerance_hpa = pressure_tolerance_hpa

    def validate_variable_bounds(self, var_name: str, value: float) -> Tuple[bool, Optional[str]]:
        """Verify that a single numerical value falls within its planetary physical limits."""
        if value is None or math.isnan(value) or math.isinf(value):
            return False, f"Variable '{var_name}' has NaN/Inf or None value."
            
        bounds = VARIABLE_BOUNDS.get(var_name)
        if bounds:
            min_v, max_v = bounds
            if value < min_v or value > max_v:
                return False, f"Value {value} for '{var_name}' exceeds physical bounds [{min_v}, {max_v}]."
        return True, None

    def validate_state(
        self,
        values: Dict[str, Optional[float]],
        elevation_m: Optional[float] = None,
    ) -> Tuple[bool, List[str]]:
        """Validate joint consistency of a complete meteorological state dictionary.
        
        Args:
            values: Mapping containing any combination of:
                    'temperature_c', 'dew_point_c', 'relative_humidity_pct',
                    'sea_level_pressure_hpa', 'station_pressure_hpa'.
            elevation_m: Optional station elevation above sea level in meters.
            
        Returns:
            (is_consistent, list_of_violations)
        """
        violations: List[str] = []

        # 1. Individual variable physical boundaries
        for k, v in values.items():
            if v is not None and not math.isnan(v):
                valid, err = self.validate_variable_bounds(k, float(v))
                if not valid and err:
                    violations.append(err)

        # 2. Thermodynamic trio consistency (Temperature, Dew Point, Relative Humidity)
        t_c = values.get("temperature_c", values.get("temperature"))
        td_c = values.get("dew_point_c")
        rh = values.get("relative_humidity_pct", values.get("relative_humidity", values.get("humidity")))

        if t_c is not None and td_c is not None:
            if td_c > t_c + self.dew_point_tolerance_c:
                violations.append(
                    f"Thermodynamic violation: Dew point ({td_c:.2f}°C) exceeds air temperature ({t_c:.2f}°C)."
                )

        if t_c is not None and td_c is not None and rh is not None:
            consistent, reason = is_physically_consistent_trio(
                t_c, td_c, rh, tolerance_pct=self.rh_tolerance_pct
            )
            if not consistent and reason:
                violations.append(f"Multivariate trio inconsistency: {reason}")

        # 3. Barometric hypsometric consistency (Station Pressure vs Sea-Level Pressure)
        slp = values.get("sea_level_pressure_hpa", values.get("pressure"))
        stn_p = values.get("station_pressure_hpa")

        if slp is not None and stn_p is not None and elevation_m is not None:
            if elevation_m >= 0:
                # Station pressure should be <= Sea level pressure for positive elevation
                if stn_p > slp + self.pressure_tolerance_hpa:
                    violations.append(
                        f"Barometric violation: Station pressure ({stn_p:.1f} hPa) exceeds SLP ({slp:.1f} hPa) at elevation {elevation_m:.1f}m."
                    )
            expected_stn = sea_level_to_station_pressure(slp, elevation_m, t_c if t_c is not None else 15.0)
            if expected_stn is not None:
                diff = abs(expected_stn - stn_p)
                if diff > self.pressure_tolerance_hpa:
                    violations.append(
                        f"Hypsometric inconsistency: Station pressure ({stn_p:.1f} hPa) differs from expected ({expected_stn:.1f} hPa) by {diff:.1f} hPa."
                    )

        is_consistent = len(violations) == 0
        return is_consistent, violations
