"""Time-windowed historical observation and decision buffer for health monitoring."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union
import numpy as np
import pandas as pd

from ml.decision.schema import HybridDecision


class HealthHistoryBuffer:
    """Manages windowed chronological buffers of hybrid decisions with recency weighting."""

    def __init__(
        self,
        default_window: str = "24h",
        window_definitions: Optional[Dict[str, float]] = None,
        recency_lambda: float = 1.5,
    ) -> None:
        """Initialize history buffer.
        
        Args:
            default_window: Default lookback window tag ('24h', '7d', '30d').
            window_definitions: Mapping of window name to duration in hours.
            recency_lambda: Exponential decay rate parameter.
        """
        self.default_window = default_window
        self.windows = window_definitions or {
            "24h": 24.0,
            "7d": 168.0,
            "30d": 720.0,
        }
        self.recency_lambda = recency_lambda
        # Store records as station_id -> List[HybridDecision]
        self._buffer: Dict[str, List[HybridDecision]] = {}

    def add_decision(self, decision: HybridDecision) -> None:
        """Append a decision to station buffer."""
        st = decision.station_id
        if st not in self._buffer:
            self._buffer[st] = []
        self._buffer[st].append(decision)

    def add_decisions(self, decisions: Sequence[HybridDecision]) -> None:
        """Batch append decisions."""
        for d in decisions:
            self.add_decision(d)

    def clear(self, station_id: Optional[str] = None) -> None:
        """Clear buffer for specific station or all stations."""
        if station_id:
            self._buffer.pop(station_id, None)
        else:
            self._buffer.clear()

    def get_window_decisions(
        self,
        station_id: str,
        end_timestamp: Optional[Union[str, datetime]] = None,
        window: Optional[str] = None,
        custom_hours: Optional[float] = None,
    ) -> Tuple[List[HybridDecision], np.ndarray]:
        """Retrieve chronological slice of decisions within the specified window with recency weights.
        
        Args:
            station_id: Target AWS station.
            end_timestamp: Latest timestamp of window (defaults to latest available record).
            window: Named window key ('24h', '7d', '30d').
            custom_hours: Explicit window duration in hours overriding named window.
            
        Returns:
            Tuple of (List of HybridDecisions sorted chronologically, np.ndarray of recency weights).
        """
        records = self._buffer.get(station_id, [])
        if not records:
            return [], np.array([], dtype=float)

        # Parse timestamps and sort
        parsed_records: List[Tuple[pd.Timestamp, HybridDecision]] = []
        for r in records:
            try:
                t = pd.to_datetime(r.timestamp)
                parsed_records.append((t, r))
            except Exception:
                continue

        if not parsed_records:
            return [], np.array([], dtype=float)

        parsed_records.sort(key=lambda x: x[0])

        if end_timestamp is not None:
            t_end = pd.to_datetime(end_timestamp)
        else:
            t_end = parsed_records[-1][0]

        hours = custom_hours if custom_hours is not None else self.windows.get(window or self.default_window, 24.0)
        t_start = t_end - pd.Timedelta(hours=hours)

        # Filter window slice [t_start, t_end]
        window_slice = [r for t, r in parsed_records if t_start <= t <= t_end]
        if not window_slice:
            return [], np.array([], dtype=float)

        # Calculate recency weights
        timestamps = [pd.to_datetime(r.timestamp) for r in window_slice]
        total_seconds = max(1.0, (t_end - t_start).total_seconds())
        
        weights = []
        for t in timestamps:
            age_fraction = max(0.0, min(1.0, (t_end - t).total_seconds() / total_seconds))
            # Weight = exp(-lambda * age_fraction), age_fraction=0 at t_end (weight=1.0), age_fraction=1 at t_start
            w = float(np.exp(-self.recency_lambda * age_fraction))
            weights.append(w)

        weights_arr = np.array(weights, dtype=float)
        # Normalize so mean weight is 1.0 (preserves effective count scale)
        if len(weights_arr) > 0 and np.mean(weights_arr) > 0:
            weights_arr = weights_arr / np.mean(weights_arr)

        return window_slice, weights_arr

    def get_comparison_windows(
        self,
        station_id: str,
        current_timestamp: Optional[Union[str, datetime]] = None,
        window: Optional[str] = None,
    ) -> Tuple[List[HybridDecision], List[HybridDecision]]:
        """Retrieve current window and preceding comparison window for trend calculation.
        
        Returns:
            Tuple of (current_window_decisions, previous_window_decisions).
        """
        records = self._buffer.get(station_id, [])
        if not records:
            return [], []

        hours = self.windows.get(window or self.default_window, 24.0)
        t_end = pd.to_datetime(current_timestamp) if current_timestamp else pd.to_datetime(records[-1].timestamp)
        t_mid = t_end - pd.Timedelta(hours=hours)
        t_prev_start = t_mid - pd.Timedelta(hours=hours)

        curr_slice: List[HybridDecision] = []
        prev_slice: List[HybridDecision] = []

        for r in records:
            t = pd.to_datetime(r.timestamp)
            if t_mid < t <= t_end:
                curr_slice.append(r)
            elif t_prev_start < t <= t_mid:
                prev_slice.append(r)

        return curr_slice, prev_slice
