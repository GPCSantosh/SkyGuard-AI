"""Abstract Base Connector Interface for Weather Observation Data Sources."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Generator, Optional
from backend.app.models.observation import WeatherObservation


class BaseConnector(ABC):
    """Abstract interface that all inbound data source connectors must implement.
    
    Ensures that the ML engine and core pipeline never depend on source-specific
    protocols or formats.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        self.config: Dict[str, Any] = config or {}
        self.is_connected: bool = False

    @abstractmethod
    def connect(self) -> None:
        """Initialize connection to data source or validate resource path."""
        raise NotImplementedError

    @abstractmethod
    def fetch_observations(self) -> Generator[WeatherObservation, None, None]:
        """Stream or yield normalized WeatherObservation instances."""
        raise NotImplementedError

    @abstractmethod
    def disconnect(self) -> None:
        """Close connections and release resources."""
        raise NotImplementedError
