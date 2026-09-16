"""Historical CSV Connector for SkyGuard AI."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Generator, Optional
import pandas as pd

from backend.app.connectors.base import BaseConnector
from backend.app.ingestion.noaa_parser import NOAAParser
from backend.app.models.observation import ObservationSource, WeatherObservation


class HistoricalCSVConnector(BaseConnector):
    """Data connector for batch ingestion from historical AWS / NOAA CSV datasets."""

    def __init__(self, file_path: Path | str, config: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(config=config)
        self.file_path = Path(file_path)
        self._parser = NOAAParser()

    def connect(self) -> None:
        """Verify the CSV file exists."""
        if not self.file_path.is_file():
            raise FileNotFoundError(f"Historical CSV file not found: {self.file_path}")
        self.is_connected = True

    def fetch_observations(self) -> Generator[WeatherObservation, None, None]:
        """Stream parsed records as normalized WeatherObservation instances."""
        if not self.is_connected:
            self.connect()

        # Check if NOAA ISD format (contains DATE, TMP, etc.)
        try:
            sample_df = pd.read_csv(self.file_path, nrows=5, dtype=str)
            if "TMP" in sample_df.columns and "DATE" in sample_df.columns:
                observations = self._parser.parse_file(self.file_path)
                for obs in observations:
                    yield obs
                return
        except Exception:
            pass

        # Standard fallback for generic CSV fixtures
        df = pd.read_csv(self.file_path)
        for _, row in df.iterrows():
            obs_dict = row.dropna().to_dict()
            if "source" not in obs_dict:
                obs_dict["source"] = ObservationSource.HISTORICAL_CSV
            yield WeatherObservation(**obs_dict)

    def disconnect(self) -> None:
        """Close file handles if any."""
        self.is_connected = False
