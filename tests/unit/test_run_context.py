"""Unit tests for RunContext, ProviderRegistry, and CSV Normalizer."""

import pytest
from pathlib import Path

from backend.app.connectors.provider_registry import ProviderRegistry
from backend.app.core.state import RunContextManager
from backend.app.ingestion.csv_normalizer import CSVNormalizer
from backend.app.models.run_context import DataSourceType, RunContext, RunMode, RunStatus


def test_run_context_defaults():
    """Verify default canonical RunContext initialization."""
    mgr = RunContextManager()
    ctx = mgr.get_context()
    assert ctx.run_id == "RUN-DEFAULT-001"
    assert ctx.source_type == DataSourceType.SYNTHETIC_VALIDATION
    assert ctx.mode == RunMode.SYNTHETIC_REPLAY
    assert ctx.ground_truth_available is True


def test_provider_registry_list():
    """Verify provider registry lists all four core providers with IMD AWS marked unconfigured."""
    providers = ProviderRegistry.list_providers()
    source_types = [p["source_type"] for p in providers]
    assert DataSourceType.SYNTHETIC_VALIDATION.value in source_types
    assert DataSourceType.HISTORICAL_CSV.value in source_types
    assert DataSourceType.OPEN_METEO.value in source_types
    assert DataSourceType.IMD_AWS.value in source_types

    imd = next(p for p in providers if p["source_type"] == DataSourceType.IMD_AWS.value)
    assert imd["configured"] is False


def test_source_selection_and_run_id_generation():
    """Verify selecting a new data source generates a fresh run_id and updates context."""
    mgr = RunContextManager()
    new_ctx = mgr.select_source(
        source_type=DataSourceType.OPEN_METEO.value,
        mode=RunMode.LIVE_MONITORING.value,
    )
    assert new_ctx.run_id.startswith("RUN-")
    assert new_ctx.source_type == DataSourceType.OPEN_METEO
    assert new_ctx.mode == RunMode.LIVE_MONITORING
    assert new_ctx.ground_truth_available is False


def test_csv_normalizer_column_mapping():
    """Verify CSVNormalizer detects standard meteorological column aliases."""
    columns = ["STATION", "DATE", "temp", "rhum", "MSLP", "LATITUDE", "LONGITUDE"]
    review = CSVNormalizer.infer_column_mapping(columns)
    assert review.is_valid is True
    assert review.detected_mapping["temp"] == "temperature"
    assert review.detected_mapping["rhum"] == "humidity"
    assert review.detected_mapping["MSLP"] == "pressure"
