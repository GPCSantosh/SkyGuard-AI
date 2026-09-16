"""Unit tests for NOAAISDConnector lifecycle and streaming."""

from pathlib import Path
import pytest
from backend.app.connectors.noaa_isd import NOAAISDConnector


def test_noaa_connector_missing_file_raises(tmp_path):
    """Verify FileNotFoundError when local file is missing and auto_download is False."""
    connector = NOAAISDConnector(
        station_id="42182099999",
        year=2024,
        local_raw_dir=tmp_path,
        auto_download=False,
    )
    with pytest.raises(FileNotFoundError):
        connector.connect()


def test_noaa_connector_with_local_sample(tmp_path):
    """Verify connector reads and streams observations from a local raw CSV file."""
    sample_file = tmp_path / "42182099999_2024.csv"
    csv_text = (
        '"STATION","DATE","LATITUDE","LONGITUDE","TMP","DEW","SLP"\n'
        '"42182099999","2024-01-01T00:00:00","28.58","77.20","+0108,1","+0100,1","10189,1"\n'
        '"42182099999","2024-01-01T00:30:00","28.58","77.20","+0110,1","+0100,1","10188,1"\n'
    )
    sample_file.write_text(csv_text, encoding="utf-8")

    connector = NOAAISDConnector(
        station_id="42182099999",
        year=2024,
        local_raw_dir=tmp_path,
        auto_download=False,
    )
    connector.connect()
    assert connector.is_connected is True

    records = list(connector.fetch_observations())
    assert len(records) == 2
    assert records[0].temperature == 10.8
    assert records[1].temperature == 11.0

    connector.disconnect()
    assert connector.is_connected is False
