"""Unit tests for meteorological formulas, RH derivation, and pressure hypsometric conversions."""

import math
import pytest
from backend.app.core.meteorology import (
    calculate_actual_vapor_pressure,
    calculate_relative_humidity,
    calculate_saturation_vapor_pressure,
    is_physically_consistent_trio,
    sea_level_to_station_pressure,
    station_to_sea_level_pressure,
)


def test_saturation_vapor_pressure():
    """Verify saturation vapor pressure calculation at standard benchmark temperatures."""
    # At 0°C, e_s(0) should be approx 6.1078 hPa
    es_0 = calculate_saturation_vapor_pressure(0.0)
    assert pytest.approx(es_0, rel=1e-3) == 6.1078

    # At 20°C, e_s(20) should be approx 23.38 hPa
    es_20 = calculate_saturation_vapor_pressure(20.0)
    assert pytest.approx(es_20, rel=1e-2) == 23.38

    # At 35°C, e_s(35) should be approx 56.22 hPa
    es_35 = calculate_saturation_vapor_pressure(35.0)
    assert pytest.approx(es_35, rel=1e-2) == 56.22


def test_rh_derivation_standard_scenarios():
    """Verify RH calculation across distinct climatic regimes."""
    # 1. 100% Saturation: T == Td
    rh_sat = calculate_relative_humidity(25.0, 25.0)
    assert rh_sat == 100.0

    # 2. Hot and Humid: T=30°C, Td=20°C -> RH ~55%
    rh_hot_humid = calculate_relative_humidity(30.0, 20.0)
    assert pytest.approx(rh_hot_humid, abs=0.5) == 55.08

    # 3. Extreme Desert Heat: T=45°C, Td=10°C -> RH ~12.8%
    rh_desert = calculate_relative_humidity(45.0, 10.0)
    assert pytest.approx(rh_desert, abs=0.5) == 12.78

    # 4. Cold Foggy Morning: T=10°C, Td=9°C -> RH ~93.5%
    rh_cold_fog = calculate_relative_humidity(10.0, 9.0)
    assert pytest.approx(rh_cold_fog, abs=0.5) == 93.50

    # 5. Sub-zero Winter: T=5°C, Td=-2°C -> RH ~60.6%
    rh_winter = calculate_relative_humidity(5.0, -2.0)
    assert pytest.approx(rh_winter, abs=0.5) == 60.56


def test_rh_derivation_missing_and_invalid():
    """Verify missing and invalid inputs return None."""
    assert calculate_relative_humidity(None, 20.0) is None
    assert calculate_relative_humidity(25.0, None) is None
    assert calculate_relative_humidity(None, None) is None
    assert calculate_relative_humidity(float("nan"), 20.0) is None
    assert calculate_relative_humidity(25.0, float("nan")) is None
    assert calculate_relative_humidity(float("inf"), 20.0) is None

    # Unphysical extremes out of Magnus range
    assert calculate_relative_humidity(120.0, 20.0) is None
    assert calculate_relative_humidity(25.0, -110.0) is None


def test_rh_clamping_and_dew_point_exceedance():
    """Verify handling when dew point exceeds temperature (sensor calibration offset)."""
    # When Td > T (e.g. T=20.0, Td=20.5), mathematically RH > 100%
    # With clamp=True, it should clamp to 100.0%
    rh_clamped = calculate_relative_humidity(20.0, 20.5, clamp=True)
    assert rh_clamped == 100.0

    # With clamp=False, returns mathematical value
    rh_raw = calculate_relative_humidity(20.0, 20.5, clamp=False)
    assert rh_raw is not None
    assert rh_raw > 100.0


def test_pressure_hypsometric_conversions():
    """Verify sea-level to station pressure conversion and inverse."""
    # Sea-level station (elev = 0m): P_stn == SLP
    p_sea = sea_level_to_station_pressure(1013.25, 0.0)
    assert p_sea == 1013.25

    # Bangalore (elev = 888m): P_stn ~ 915 hPa when SLP = 1013.25 hPa
    p_bglr = sea_level_to_station_pressure(1013.25, 888.0, temperature_c=25.0)
    assert p_bglr is not None
    assert 900.0 < p_bglr < 930.0

    # Invert back to SLP
    slp_inv = station_to_sea_level_pressure(p_bglr, 888.0, temperature_c=25.0)
    assert slp_inv is not None
    assert pytest.approx(slp_inv, abs=0.5) == 1013.25

    # Srinagar (elev = 1587m): P_stn ~ 840 hPa
    p_sri = sea_level_to_station_pressure(1015.0, 1587.0, temperature_c=10.0)
    assert p_sri is not None
    assert 820.0 < p_sri < 860.0


def test_physical_consistency_trio_checks():
    """Verify detection of multivariate inconsistencies among T, Td, and reported RH."""
    # Consistent trio
    ok, msg = is_physically_consistent_trio(temperature_c=30.0, dew_point_c=20.0, relative_humidity_pct=55.0)
    assert ok is True
    assert msg is None

    # Inconsistent: Td > T by more than tolerance
    ok, msg = is_physically_consistent_trio(temperature_c=20.0, dew_point_c=25.0, relative_humidity_pct=100.0)
    assert ok is False
    assert "exceeds air temperature" in str(msg)

    # Inconsistent: reported RH diverges by >5% from derived RH
    ok, msg = is_physically_consistent_trio(temperature_c=30.0, dew_point_c=20.0, relative_humidity_pct=85.0)
    assert ok is False
    assert "diverges from derived RH" in str(msg)
