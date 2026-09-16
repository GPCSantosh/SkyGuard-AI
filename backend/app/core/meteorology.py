"""Meteorological computation and thermodynamic conversion utilities for SkyGuard AI.

Implements standard WMO and August-Roche-Magnus formulations for:
- Relative humidity derivation from dry-bulb air temperature and dew point
- Barometric formula for sea-level / station pressure reduction
- Physical consistency checks and saturation vapor pressure calculations
"""

from __future__ import annotations

import math
from typing import Optional, Tuple

from backend.app.core.constants import (
    HUMIDITY_PHYSICAL_MAX_PCT,
    HUMIDITY_PHYSICAL_MIN_PCT,
    PRESSURE_PHYSICAL_MAX_HPA,
    PRESSURE_PHYSICAL_MIN_HPA,
    TEMP_PHYSICAL_MAX_C,
    TEMP_PHYSICAL_MIN_C,
)

# August-Roche-Magnus standard constants (Alduchov & Eskridge, 1996 / WMO guidelines)
# Valid across the standard meteorological range: -40°C to +50°C
MAGNUS_A: float = 17.625
MAGNUS_B: float = 243.04  # °C
MAGNUS_C: float = 6.1078  # hPa (Saturation vapor pressure at 0°C)

# Standard atmospheric constants
STANDARD_SEA_LEVEL_PRESSURE_HPA: float = 1013.25
STANDARD_SEA_LEVEL_TEMP_K: float = 288.15
STANDARD_LAPSE_RATE_K_PER_M: float = 0.0065  # 6.5 K / 1000m
GRAVITATIONAL_ACCELERATION_M_S2: float = 9.80665
MOLAR_MASS_AIR_KG_MOL: float = 0.0289644
UNIVERSAL_GAS_CONSTANT_J_MOL_K: float = 8.31447


def calculate_saturation_vapor_pressure(temperature_c: float) -> float:
    """Calculate saturation vapor pressure e_s(T) in hPa using the Magnus formula.
    
    Formula:
        e_s(T) = c * exp((a * T) / (b + T))
    
    Args:
        temperature_c: Air temperature in degrees Celsius.
        
    Returns:
        Saturation vapor pressure in hPa.
    """
    if temperature_c + MAGNUS_B == 0:
        raise ZeroDivisionError("Temperature causes singularity in Magnus formula.")
    exponent = (MAGNUS_A * temperature_c) / (MAGNUS_B + temperature_c)
    return MAGNUS_C * math.exp(exponent)


def calculate_actual_vapor_pressure(dew_point_c: float) -> float:
    """Calculate actual vapor pressure e(T_d) in hPa from dew point temperature.
    
    Formula:
        e(T_d) = c * exp((a * T_d) / (b + T_d))
        
    Args:
        dew_point_c: Dew point temperature in degrees Celsius.
        
    Returns:
        Actual vapor pressure in hPa.
    """
    return calculate_saturation_vapor_pressure(dew_point_c)


def calculate_relative_humidity(
    temperature_c: Optional[float],
    dew_point_c: Optional[float],
    clamp: bool = True,
) -> Optional[float]:
    """Derive relative humidity (%) from air temperature and dew point.
    
    Uses the August-Roche-Magnus formula:
        RH = 100.0 * (e(T_d) / e_s(T))
           = 100.0 * exp( (a * T_d) / (b + T_d) - (a * T) / (b + T) )
    
    Args:
        temperature_c: Air temperature in °C.
        dew_point_c: Dew point temperature in °C.
        clamp: If True, restricts result to physical bounds [0.0, 100.0]%.
               If False, returns mathematically calculated value (e.g. 100.4% if T_d > T).
               
    Returns:
        Derived relative humidity in % (0.0 - 100.0), or None if inputs are missing/invalid.
    """
    if temperature_c is None or dew_point_c is None:
        return None

    # Check for NaN or Inf
    if math.isnan(temperature_c) or math.isnan(dew_point_c):
        return None
    if math.isinf(temperature_c) or math.isinf(dew_point_c):
        return None

    # Check for unphysical extremes where Magnus formula is invalid
    if temperature_c < -80.0 or temperature_c > 80.0:
        return None
    if dew_point_c < -90.0 or dew_point_c > 60.0:
        return None

    try:
        alpha = (MAGNUS_A * dew_point_c) / (MAGNUS_B + dew_point_c)
        beta = (MAGNUS_A * temperature_c) / (MAGNUS_B + temperature_c)
        rh = 100.0 * math.exp(alpha - beta)
    except (OverflowError, ZeroDivisionError):
        return None

    if clamp:
        if rh < HUMIDITY_PHYSICAL_MIN_PCT:
            return HUMIDITY_PHYSICAL_MIN_PCT
        if rh > HUMIDITY_PHYSICAL_MAX_PCT:
            return HUMIDITY_PHYSICAL_MAX_PCT

    return round(rh, 2)


def sea_level_to_station_pressure(
    sea_level_pressure_hpa: Optional[float],
    elevation_m: Optional[float],
    temperature_c: Optional[float] = 15.0,
) -> Optional[float]:
    """Convert Sea-Level Pressure (SLP) to Station Pressure (P_stn) using the hypsometric formula.
    
    Args:
        sea_level_pressure_hpa: Sea-level pressure in hPa.
        elevation_m: Station elevation above mean sea level in meters.
        temperature_c: Mean ambient temperature in °C (defaults to standard 15°C).
        
    Returns:
        Estimated station pressure in hPa, or None if inputs are missing.
    """
    if sea_level_pressure_hpa is None or elevation_m is None:
        return None

    if math.isnan(sea_level_pressure_hpa) or math.isnan(elevation_m):
        return None

    temp_k = (temperature_c if temperature_c is not None else 15.0) + 273.15
    if temp_k <= 0:
        temp_k = STANDARD_SEA_LEVEL_TEMP_K

    try:
        # Hypsometric exponent: (g * M) / (R0 * L)
        exponent = (GRAVITATIONAL_ACCELERATION_M_S2 * MOLAR_MASS_AIR_KG_MOL) / (
            UNIVERSAL_GAS_CONSTANT_J_MOL_K * STANDARD_LAPSE_RATE_K_PER_M
        )
        base = 1.0 - (STANDARD_LAPSE_RATE_K_PER_M * elevation_m) / temp_k
        if base <= 0:
            return None
        stn_pres = sea_level_pressure_hpa * (base**exponent)
        return round(stn_pres, 2)
    except (ValueError, ZeroDivisionError, OverflowError):
        return None


def station_to_sea_level_pressure(
    station_pressure_hpa: Optional[float],
    elevation_m: Optional[float],
    temperature_c: Optional[float] = 15.0,
) -> Optional[float]:
    """Convert Station Pressure (P_stn) to Sea-Level Pressure (SLP) using the inverse hypsometric formula.
    
    Args:
        station_pressure_hpa: Atmospheric station pressure in hPa.
        elevation_m: Station elevation above mean sea level in meters.
        temperature_c: Mean ambient temperature in °C.
        
    Returns:
        Estimated sea-level pressure in hPa, or None if inputs are missing.
    """
    if station_pressure_hpa is None or elevation_m is None:
        return None

    if math.isnan(station_pressure_hpa) or math.isnan(elevation_m):
        return None

    temp_k = (temperature_c if temperature_c is not None else 15.0) + 273.15
    if temp_k <= 0:
        temp_k = STANDARD_SEA_LEVEL_TEMP_K

    try:
        exponent = (GRAVITATIONAL_ACCELERATION_M_S2 * MOLAR_MASS_AIR_KG_MOL) / (
            UNIVERSAL_GAS_CONSTANT_J_MOL_K * STANDARD_LAPSE_RATE_K_PER_M
        )
        base = 1.0 - (STANDARD_LAPSE_RATE_K_PER_M * elevation_m) / temp_k
        if base <= 0:
            return None
        slp = station_pressure_hpa / (base**exponent)
        return round(slp, 2)
    except (ValueError, ZeroDivisionError, OverflowError):
        return None


def is_physically_consistent_trio(
    temperature_c: Optional[float],
    dew_point_c: Optional[float],
    relative_humidity_pct: Optional[float],
    tolerance_pct: float = 5.0,
) -> Tuple[bool, Optional[str]]:
    """Check physical consistency among Temperature, Dew Point, and Relative Humidity.
    
    Rules:
    1. Dew Point cannot exceed Temperature (allowing minor instrument sensor tolerance of +0.2°C).
    2. Derived RH from (T, Td) must align with reported RH within tolerance_pct if both present.
    
    Returns:
        (is_consistent, reason_if_inconsistent)
    """
    if temperature_c is not None and dew_point_c is not None:
        if dew_point_c > temperature_c + 0.2:
            return False, f"Dew point ({dew_point_c}°C) exceeds air temperature ({temperature_c}°C)"

    if (
        temperature_c is not None
        and dew_point_c is not None
        and relative_humidity_pct is not None
    ):
        derived_rh = calculate_relative_humidity(temperature_c, dew_point_c, clamp=True)
        if derived_rh is not None:
            diff = abs(derived_rh - relative_humidity_pct)
            if diff > tolerance_pct:
                return (
                    False,
                    f"Reported RH ({relative_humidity_pct}%) diverges from derived RH ({derived_rh}%) by {diff:.1f}%",
                )

    return True, None
