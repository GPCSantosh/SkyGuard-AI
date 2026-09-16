"""Unit tests for configuration loading, YAML parsing, and env overrides."""

import os
from pathlib import Path
import pytest
from backend.app.core.config import get_settings, load_yaml_config


def test_default_config_loading():
    """Verify settings load cleanly with 5-minute default cadence."""
    settings = get_settings("configs/default.yaml")

    assert settings.system.project_name == "SkyGuard AI"
    assert settings.system.version == "0.1.0"
    assert settings.observation_interval_seconds == 300
    assert settings.telemetry.default_sampling_interval_seconds == 300
    assert settings.spatial.geodesic_distance_metric == "haversine"
    assert settings.spatial.default_neighbor_radius_km == 150.0


def test_thresholds_yaml_structure():
    """Verify thresholds.yaml parses and contains expected physical keys."""
    thresholds = load_yaml_config("configs/thresholds.yaml")

    assert "physical_limits" in thresholds
    assert "temperature" in thresholds["physical_limits"]
    assert thresholds["physical_limits"]["temperature"]["min"] == -50.0
    assert thresholds["physical_limits"]["temperature"]["max"] == 60.0
    assert "pressure" in thresholds["physical_limits"]
    assert thresholds["physical_limits"]["pressure"]["min"] == 500.0
    assert thresholds["physical_limits"]["pressure"]["max"] == 1080.0
    assert "humidity" in thresholds["physical_limits"]
    assert thresholds["physical_limits"]["humidity"]["min"] == 0.0
    assert thresholds["physical_limits"]["humidity"]["max"] == 100.0


def test_stations_yaml_structure():
    """Verify stations.yaml contains valid station definitions with coordinates."""
    stations_cfg = load_yaml_config("configs/stations.yaml")

    assert "stations" in stations_cfg
    stations = stations_cfg["stations"]
    assert len(stations) >= 20

    for st in stations:
        assert "station_id" in st
        assert "latitude" in st
        assert "longitude" in st
        assert -90.0 <= st["latitude"] <= 90.0
        assert -180.0 <= st["longitude"] <= 180.0


def test_env_override(monkeypatch):
    """Verify environment variables override default settings."""
    monkeypatch.setenv("SKYGUARD_OBSERVATION_INTERVAL_SECONDS", "600")
    monkeypatch.setenv("SKYGUARD_ENV", "staging")
    monkeypatch.setenv("SKYGUARD_LOG_LEVEL", "DEBUG")

    settings = get_settings()

    assert settings.observation_interval_seconds == 600
    assert settings.env == "staging"
    assert settings.log_level == "DEBUG"
