"""Historical CSV Connector for SkyGuard AI."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Generator, Optional
from backend.app.connectors.base import BaseConnector
from backend.app.models.observation import ObservationSource, WeatherObservation


class HistoricalCSVConnector(BaseConnector):
    """Data connector for batch ingestion from historical AWS CSV datasets."""

    def __init__(self, file_path: Path | str, config: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(config=config)
        self.file_path = Path(file_path)

    def connect(self) -> None:
        """Verify the CSV file exists."""
        if not self.file_path.is_file():
            raise FileNotFoundError(f"Historical CSV file not found: {self.file_path}")
        self.is_connected = True

    def fetch_observations(self) -> Generator[WeatherObservation, None, None]:
        """Stream parsed records as normalized WeatherObservation instances."""
        if not self.is_connected:
            self.connect()
        # CSV parsing and streaming logic will be implemented in Phase 1 with the selected dataset
        # Yields nothing in Phase 0 foundation
        return
        yield  # type: ignore

    def disconnect(self) -> None:
        """Close file handles if any."""
        self.is_connected = False
