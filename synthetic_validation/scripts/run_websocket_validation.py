"""CLI script for standalone WebSocket lifecycle and real-time event delivery validation."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
import sys

# Ensure repository root is in sys.path
root = Path(__file__).resolve().parents[2]
if str(root) not in sys.path:
    sys.path.insert(0, str(root))

from synthetic_validation.harness.ws_validator import WebSocketHarnessValidator


async def main_async() -> int:
    print("=" * 72)
    print(" SKYGUARD AI - SYNTHETIC WEBSOCKET LIFECYCLE VALIDATION ")
    print("=" * 72)

    validator = WebSocketHarnessValidator(seed=42)
    results = await validator.validate_websocket_lifecycle()

    print(f" Lifecycle Verification:    [{'PASS' if results['websocket_lifecycle_verified'] else 'FAIL'}]")
    print(f" Total Broadcasts:          {results['total_broadcasts']}")
    print(f" Initial Client Received:   {results['client1_events_received']} events")
    print(f" Reconnected Client Recv:   {results['client2_reconnect_events_received']} events")
    print(f" Dropped Messages:          {results['dropped_messages']}")
    print(f" Duplicate Events:          {results['duplicate_events_detected']}")
    print(f" Polling Fallback Ready:    {results['polling_fallback_available']}")
    print("=" * 72)

    if results["websocket_lifecycle_verified"] and results["dropped_messages"] == 0:
        print(" WEBSOCKET VALIDATION SUCCESSFUL ")
        print("=" * 72)
        return 0
    else:
        print(" WEBSOCKET VALIDATION FAILED ")
        print("=" * 72)
        return 1


def main() -> int:
    return asyncio.run(main_async())


if __name__ == "__main__":
    sys.exit(main())
