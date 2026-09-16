"""Verify clean imports across backend and module namespaces."""

import pytest


def test_import_core_modules():
    """Verify core constants, config, and logging imports."""
    from backend.app.core.constants import (
        DEFAULT_SAMPLING_INTERVAL_SECONDS,
        HUMIDITY_PHYSICAL_MAX_PCT,
        PRESSURE_PHYSICAL_MIN_HPA,
        TEMP_PHYSICAL_MAX_C,
    )
    from backend.app.core.config import AppSettings, get_settings
    from backend.app.core.logging import get_logger, setup_logging

    assert DEFAULT_SAMPLING_INTERVAL_SECONDS == 300
    assert TEMP_PHYSICAL_MAX_C == 60.0
    assert PRESSURE_PHYSICAL_MIN_HPA == 500.0
    assert HUMIDITY_PHYSICAL_MAX_PCT == 100.0

    logger = get_logger("test")
    assert logger.name == "skyguard.test"


def test_import_models():
    """Verify domain schema imports."""
    from backend.app.models import (
        AnomalyCategory,
        AnomalyRecord,
        AnomalySeverity,
        HealthTier,
        ObservationSource,
        SensorHealthStatus,
        StationMetadata,
        StationStatus,
        WeatherObservation,
    )

    # Check 15-category taxonomy completeness
    assert len(AnomalyCategory) == 15
    assert AnomalyCategory.NORMAL == "NORMAL"
    assert AnomalyCategory.SPIKE == "SPIKE"
    assert AnomalyCategory.DRIFT == "DRIFT"
    assert AnomalyCategory.FROZEN_SENSOR == "FROZEN_SENSOR"
    assert AnomalyCategory.POSSIBLE_GENUINE_EVENT == "POSSIBLE_GENUINE_EVENT"
    assert AnomalyCategory.UNCERTAIN == "UNCERTAIN"


def test_import_connectors():
    """Verify connector imports and hierarchy."""
    from backend.app.connectors import (
        BaseConnector,
        HistoricalCSVConnector,
        MQTTConnector,
        SimulatorConnector,
        WeatherAPIConnector,
    )

    assert issubclass(HistoricalCSVConnector, BaseConnector)
    assert issubclass(SimulatorConnector, BaseConnector)
    assert issubclass(WeatherAPIConnector, BaseConnector)
    assert issubclass(MQTTConnector, BaseConnector)


def test_import_fastapi_app():
    """Verify FastAPI application instantiates."""
    from backend.app.main import app

    assert app.title.startswith("SkyGuard AI")
