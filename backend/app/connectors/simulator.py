"""Weather Station Telemetry Simulator Connector."""

from __future__ import annotations

from typing import Any, Dict, Generator, Optional
from backend.app.connectors.base import BaseConnector
from backend.app.models.observation import ObservationSource, WeatherObservation


class SimulatorConnector(BaseConnector):
    """Generates synthetic time-series weather telemetry for testing and simulation."""

    def __init__(
        self,
        station_id: str = "AWS_SIM_001",
        interval_seconds: int = 300,
        config: Optional[Dict[str, Any]] = None
    ) -> None:
        super().__init__(config=config)
        self.station_id = station_id
        self.interval_seconds = interval_seconds

    def connect(self) -> None:
        """Initialize simulator parameters."""
        self.is_connected = True

    def fetch_observations(self) -> Generator[WeatherObservation, None, None]:
        """Yield simulated observations (implementation placeholder for Phase 1)."""
        if not self.is_connected:
            self.connect()
        return
        yield  # type: ignore

    def disconnect(self) -> None:
        """Stop simulator."""
        self.is_connected = False
