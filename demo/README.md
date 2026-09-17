# SkyGuard AI — Hackathon Demonstration Suite

This directory contains deterministic demo datasets, scenario definitions, generator scripts, and pre-demo automated health verification tools.

## Directory Layout
```
demo/
├── README.md                          # This file
├── replay/
│   ├── narrative_replay_dataset.csv   # 384 deterministic observations across 8 stations (seed=42)
│   └── scenario_registry.json         # Scenario registry with step markers and expectations
└── scripts/
    ├── build_demo_scenarios.py        # Generates deterministic replay dataset and scenario registry
    └── demo_health_check.py           # Pre-demo 9-point integrity and readiness test suite
```

## Quick Start: Running the Pre-Demo Health Check
```bash
python demo/scripts/demo_health_check.py
```

## Re-generating Scenario Datasets (Deterministic Seed 42)
```bash
python demo/scripts/build_demo_scenarios.py
```

## Available Scenarios
1. **Flagship 8-12 Min Presentation (`flagship_narrative`)**:
   - Step 0–7: Nominal baseline network operation.
   - Step 8–15: Isolated +18.5°C temperature spike on Safdarjung (`42182099999`).
   - Step 16–24: Frozen stuck relative humidity flatline on Santacruz (`43003099999`).
   - Step 25–36: Regional squall front (85% consensus) with zero false-alarm penalty.
   - Step 37–48: Live source outage simulation and network decoupling.

2. **Isolated Hardware Spike (`sensor_spike_demo`)**:
   - Targeted hardware fault demonstration.

3. **Regional Squall Front (`regional_event_demo`)**:
   - Severe convective storm consensus demonstration.

4. **Live Source Outage & Decoupling (`source_outage_demo`)**:
   - Upstream telemetry failure and recovery state transitions.
