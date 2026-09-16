"""Unit tests for Multivariate Consistency Checker and Bundle Evaluation."""

import pytest

from ml.decision.schema import HybridDecisionType
from ml.imputation.consistency import MultivariateConsistencyChecker
from ml.imputation.correction_engine import CorrectionRecommendationEngine
from ml.imputation.schema import RecommendationStatus
from ml.spatial.engine import SpatialContextEngine
from ml.spatial.topology import SpatialNetworkTopology, StationNode


def test_thermodynamic_trio_validation():
    checker = MultivariateConsistencyChecker()

    # Valid physical state
    valid_state = {
        "temperature_c": 25.0,
        "dew_point_c": 18.0,
        "relative_humidity_pct": 65.0,
    }
    is_valid, violations = checker.validate_state(valid_state)
    assert is_valid is True
    assert len(violations) == 0

    # Inconsistent state: Dew point exceeds temperature
    inconsistent_td = {
        "temperature_c": 20.0,
        "dew_point_c": 25.0,  # 25°C > 20°C
        "relative_humidity_pct": 95.0,
    }
    is_valid, violations = checker.validate_state(inconsistent_td)
    assert is_valid is False
    assert any("Dew point" in v for v in violations)


def test_hypsometric_pressure_validation():
    checker = MultivariateConsistencyChecker()

    # Elevation 200m: SLP = 1013.25, expected station pressure ~ 989 hPa
    valid_pressure_state = {
        "temperature_c": 15.0,
        "sea_level_pressure_hpa": 1013.25,
        "station_pressure_hpa": 989.5,
    }
    is_valid, violations = checker.validate_state(valid_pressure_state, elevation_m=200.0)
    assert is_valid is True

    # Violating pressure: station pressure > SLP at +500m elevation
    invalid_pressure_state = {
        "temperature_c": 15.0,
        "sea_level_pressure_hpa": 1000.0,
        "station_pressure_hpa": 1025.0,
    }
    is_valid, violations = checker.validate_state(invalid_pressure_state, elevation_m=500.0)
    assert is_valid is False
    assert any("Station pressure" in v for v in violations)


def test_evaluate_bundle_downgrades_on_physical_violation():
    topo = SpatialNetworkTopology()
    topo.add_station(StationNode(station_id="TARGET", name="Target", latitude=28.6, longitude=77.2, elevation_m=200.0))
    topo.add_station(StationNode(station_id="N1", name="N1", latitude=28.58, longitude=77.23, elevation_m=200.0))
    topo.add_station(StationNode(station_id="N2", name="N2", latitude=28.65, longitude=77.19, elevation_m=200.0))

    spatial_engine = SpatialContextEngine(topology=topo)
    engine = CorrectionRecommendationEngine(spatial_engine=spatial_engine)

    # Inconsistent neighbors where T recommended is 20°C and Td recommended is 25°C
    neighbors = [
        {"station_id": "N1", "timestamp": "2026-09-17T12:00:00Z", "temperature_c": 20.0, "dew_point_c": 25.0, "relative_humidity_pct": 90.0},
        {"station_id": "N2", "timestamp": "2026-09-17T12:00:00Z", "temperature_c": 20.2, "dew_point_c": 24.8, "relative_humidity_pct": 90.0},
    ]

    bundle = engine.evaluate_bundle(
        station_id="TARGET",
        timestamp="2026-09-17T12:00:00Z",
        observed_payload={"temperature_c": 40.0, "dew_point_c": 26.0, "relative_humidity_pct": 90.0},
        neighbor_observations=neighbors,
        elevation_m=200.0,
    )

    # Because candidate T (~20.1°C) and Td (~24.9°C) produce Td > T, bundle should catch inconsistency
    assert bundle.is_jointly_consistent is False
    assert len(bundle.inconsistency_reasons) > 0
    # Any recommendation that would have been CANDIDATE is forced to REVIEW_RECOMMENDED
    for rec in bundle.recommendations.values():
        assert rec.status != RecommendationStatus.CORRECTION_CANDIDATE
        assert rec.multivariate_consistent is False
