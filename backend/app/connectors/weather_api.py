"""External Weather REST API Connector (Future Phase Placeholder)."""

from __future__ import annotations

from typing import Any, Dict, Generator, Optional
from backend.app.connectors.base import BaseConnector
from backend.app.models.observation import WeatherObservation


class WeatherAPIConnector(BaseConnector):
    """Polls external weather HTTP REST APIs for station telemetry."""

    def __init__(
        self,
        api_base_url: str = "",
        api_key: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None
    ) -> None:
        super().__init__(config=config)
        self.api_base_url = api_base_url
        self.api_key = api_key

    def connect(self) -> None:
        """Validate API endpoints and credentials."""
        self.is_connected = True

    def fetch_observations(self) -> Generator[WeatherObservation, None, None]:
        """Poll API for observations (Placeholder - reserved for live API phase)."""
        return
        yield  # type: ignore

    def disconnect(self) -> None:
        """Close HTTP client session."""
        self.is_connected = False
