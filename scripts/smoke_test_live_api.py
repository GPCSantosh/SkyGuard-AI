#!/usr/bin/env python3
"""SkyGuard AI — Live Weather API Smoke Test Utility.

Executes a live or mocked smoke test against Open-Meteo WMO surface feeds,
validating HTTP transport, response parsing, unit normalization, and qualification gates.

Usage:
    python scripts/smoke_test_live_api.py --mock
    python scripts/smoke_test_live_api.py --live
    python scripts/smoke_test_live_api.py --live --lat 28.585 --lon 77.206 --station-id AWS_DELHI_001
"""

import argparse
import json
from pathlib import Path
import sys
import time

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.connectors.live_qualification import (
    LiveSourceQualificationGate,
    OpenMeteoQualificationAdapter,
    PressureSemantics,
)
from backend.app.connectors.weather_api import OpenMeteoLiveConnector
from backend.app.core.config import get_settings


def run_smoke_test(
    is_live: bool,
    station_id: str,
    lat: float,
    lon: float,
    elevation: float,
) -> bool:
    mode_str = "LIVE API TEST (Real Outbound HTTP Request)" if is_live else "MOCK TEST (Deterministic Local Fixture)"
    
    print("=" * 70)
    print("SKYGUARD AI — LIVE WEATHER SOURCE SMOKE TEST")
    print(f"MODE: {mode_str}")
    print("=" * 70)
    print(f"Target Station ID : {station_id}")
    print(f"Coordinates       : Lat {lat:.4f}, Lon {lon:.4f} (Elev: {elevation:.1f}m)")
    print("-" * 70)

    settings = get_settings()

    if is_live:
        connector = OpenMeteoLiveConnector(
            base_url=settings.live_source.base_url,
            api_key=settings.live_source.api_key,
            timeout_seconds=settings.live_source.timeout_seconds,
            pressure_semantics=PressureSemantics.MEAN_SEA_LEVEL_PRESSURE,
        )
        print(f"Querying Endpoint : {connector.base_url}/forecast")
        t0 = time.perf_counter()
        obs = connector.fetch_station_observation(
            station_id=station_id,
            latitude=lat,
            longitude=lon,
            elevation=elevation,
            station_name="Smoke Test Station",
        )
        elapsed_ms = (time.perf_counter() - t0) * 1000.0

        if obs is None:
            print("[FAILED] Live API fetch failed or was rejected by Quality Gate.")
            print(f"Health Status     : {connector.health.model_dump_json(indent=2)}")
            return False

        print(f"[SUCCESS] Received observation in {elapsed_ms:.2f} ms")
        print(f"Timestamp (UTC)   : {obs.timestamp.isoformat()}")
        print(f"Ingestion (UTC)   : {obs.ingestion_timestamp.isoformat()}")
        print(f"Temperature       : {obs.temperature} °C")
        print(f"Relative Humidity : {obs.humidity} %")
        print(f"Sea-Level Pressure: {obs.pressure} hPa (MSLP)")
        print(f"Station Pressure  : {obs.station_pressure_hpa} hPa (Surface)")
        print(f"Quality Status    : {obs.data_quality_status}")
        print(f"Supplementary     : {obs.metadata.get('source_supplementary', {})}")
        print("-" * 70)
        print("Live Source Health Summary:")
        print(f"  Reachable       : {connector.health.is_reachable}")
        print(f"  Consecutive Fails: {connector.health.consecutive_failures}")
        print(f"  Latency (ms)    : {connector.health.last_response_latency_ms}")
        print(f"  Auth Status     : {connector.health.authentication_status}")
        return True

    else:
        # Mock mode
        fixture_path = PROJECT_ROOT / "data" / "external" / "live_api" / "01_valid_observation.json"
        print(f"Loading Mock Fixture : {fixture_path.relative_to(PROJECT_ROOT)}")
        if not fixture_path.exists():
            print(f"[FAILED] Fixture not found at {fixture_path}")
            return False

        with open(fixture_path, "r", encoding="utf-8") as f:
            raw_data = json.load(f)

        adapter = OpenMeteoQualificationAdapter()
        observations = adapter.normalize(
            raw_payload=raw_data,
            station_id=station_id,
            station_name="Smoke Test Station (Mock)",
            pressure_semantics=PressureSemantics.MEAN_SEA_LEVEL_PRESSURE,
        )

        if not observations:
            print("[FAILED] Adapter returned 0 observations.")
            return False

        obs = observations[0]
        gate_res = LiveSourceQualificationGate.evaluate(obs, expected_station_id=station_id)

        print("[SUCCESS] Mock Observation Normalized and Verified:")
        print(f"Timestamp (UTC)   : {obs.timestamp.isoformat()}")
        print(f"Temperature       : {obs.temperature} °C")
        print(f"Relative Humidity : {obs.humidity} %")
        print(f"Sea-Level Pressure: {obs.pressure} hPa (MSLP)")
        print(f"Station Pressure  : {obs.station_pressure_hpa} hPa (Surface)")
        print(f"Quality Gate      : {'PASSED' if gate_res.is_qualified else 'FAILED'}")
        if not gate_res.is_qualified:
            print(f"Gate Reasons      : {gate_res.reasons}")
        return gate_res.is_qualified


def main():
    parser = argparse.ArgumentParser(description="SkyGuard AI — Live Weather API Smoke Test")
    parser.add_argument("--live", action="store_true", help="Execute real outbound HTTP query to Open-Meteo API")
    parser.add_argument("--mock", action="store_true", help="Execute local deterministic mock fixture test (default)")
    parser.add_argument("--station-id", default="42182099999", help="Target Station ID (default: New Delhi Safdarjung)")
    parser.add_argument("--lat", type=float, default=28.5845, help="Latitude (default: 28.5845)")
    parser.add_argument("--lon", type=float, default=77.2058, help="Longitude (default: 77.2058)")
    parser.add_argument("--elevation", type=float, default=214.9, help="Elevation in meters (default: 214.9)")

    args = parser.parse_args()
    is_live = bool(args.live)

    success = run_smoke_test(
        is_live=is_live,
        station_id=args.station_id,
        lat=args.lat,
        lon=args.lon,
        elevation=args.elevation,
    )

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
