"""Unit tests verifying BaseConnector contract and concrete placeholders."""

from pathlib import Path
import pytest
from backend.app.connectors.base import BaseConnector
from backend.app.connectors.historical_csv import HistoricalCSVConnector
from backend.app.connectors.mqtt import MQTTConnector
from backend.app.connectors.simulator import SimulatorConnector
from backend.app.connectors.weather_api import WeatherAPIConnector


def test_base_connector_cannot_be_instantiated():
    """Verify abstract BaseConnector cannot be instantiated directly."""
    with pytest.raises(TypeError):
        BaseConnector()  # type: ignore


def test_historical_csv_connector_lifecycle(tmp_path: Path):
    """Verify HistoricalCSVConnector connect/disconnect lifecycle."""
    csv_file = tmp_path / "test_sample.csv"
    csv_file.write_text("timestamp,station_id,temperature\n2026-09-16T12:00:00Z,AWS_01,25.0")

    connector = HistoricalCSVConnector(file_path=csv_file)
    assert not connector.is_connected

    connector.connect()
    assert connector.is_connected

    connector.disconnect()
    assert not connector.is_connected


def test_historical_csv_missing_file_raises():
    """Verify FileNotFoundError if target CSV path does not exist."""
    connector = HistoricalCSVConnector(file_path="non_existent_file.csv")
    with pytest.raises(FileNotFoundError):
        connector.connect()


def test_simulator_connector_lifecycle():
    """Verify SimulatorConnector lifecycle."""
    sim = SimulatorConnector(station_id="AWS_SIM_TEST", interval_seconds=300)
    assert not sim.is_connected

    sim.connect()
    assert sim.is_connected
    assert sim.station_id == "AWS_SIM_TEST"
    assert sim.interval_seconds == 300

    sim.disconnect()
    assert not sim.is_connected


def test_weather_api_connector_lifecycle():
    """Verify WeatherAPIConnector lifecycle."""
    api_conn = WeatherAPIConnector(api_base_url="https://api.example.com")
    assert not api_conn.is_connected

    api_conn.connect()
    assert api_conn.is_connected

    api_conn.disconnect()
    assert not api_conn.is_connected


def test_mqtt_connector_lifecycle():
    """Verify MQTTConnector lifecycle."""
    mqtt_conn = MQTTConnector(broker_host="localhost", broker_port=1883)
    assert not mqtt_conn.is_connected

    mqtt_conn.connect()
    assert mqtt_conn.is_connected

    mqtt_conn.disconnect()
    assert not mqtt_conn.is_connected
