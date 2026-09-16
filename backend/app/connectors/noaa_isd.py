"""NOAA NCEI Integrated Surface Database (ISD) Connector for SkyGuard AI.

Implements streaming and batch ingestion from local raw NOAA ISD CSV files
or remote NOAA NCEI HTTPS endpoints.
"""

from __future__ import annotations

import io
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional, Union
import urllib.request
import pandas as pd

from backend.app.connectors.base import BaseConnector
from backend.app.ingestion.noaa_parser import NOAAParser, NOAAParserConfig
from backend.app.models.observation import WeatherObservation

NOAA_BASE_URL = "https://www.ncei.noaa.gov/data/global-hourly/access"


class NOAAISDConnector(BaseConnector):
    """Connector for streaming NOAA NCEI Global Hourly / ISD observations."""

    def __init__(
        self,
        station_id: str,
        year: int,
        local_raw_dir: Optional[Union[str, Path]] = None,
        config: Optional[Dict[str, Any]] = None,
        auto_download: bool = True,
    ) -> None:
        super().__init__(config=config)
        self.station_id = station_id
        self.year = year
        self.local_raw_dir = Path(local_raw_dir or "data/raw")
        self.auto_download = auto_download
        self.raw_file_path = self.local_raw_dir / f"{self.station_id}_{self.year}.csv"
        self._parser = NOAAParser(
            config=NOAAParserConfig(
                default_station_id=self.station_id,
                filter_report_types=self.config.get("filter_report_types"),
                derive_rh=self.config.get("derive_rh", True),
                clamp_rh=self.config.get("clamp_rh", True),
            )
        )
        self._cached_observations: Optional[List[WeatherObservation]] = None

    def connect(self) -> None:
        """Verify local raw file exists or download from NOAA NCEI if enabled."""
        self.local_raw_dir.mkdir(parents=True, exist_ok=True)

        if self.raw_file_path.is_file():
            self.is_connected = True
            return

        if not self.auto_download:
            raise FileNotFoundError(
                f"Raw NOAA file not found at {self.raw_file_path} and auto_download is disabled."
            )

        # Download from NOAA NCEI
        url = f"{NOAA_BASE_URL}/{self.year}/{self.station_id}.csv"
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "SkyGuardAI-NOAAConnector/1.0"},
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = resp.read()
                # Write to immutable raw storage
                with open(self.raw_file_path, "wb") as f:
                    f.write(data)
            self.is_connected = True
        except Exception as e:
            raise ConnectionError(
                f"Failed to fetch NOAA ISD data from {url}: {e}"
            ) from e

    def fetch_observations(self) -> Generator[WeatherObservation, None, None]:
        """Stream parsed records as normalized WeatherObservation instances."""
        if not self.is_connected:
            self.connect()

        if self._cached_observations is None:
            self._cached_observations = self._parser.parse_file(self.raw_file_path)

        for obs in self._cached_observations:
            yield obs

    def disconnect(self) -> None:
        """Release cached observations."""
        self._cached_observations = None
        self.is_connected = False
