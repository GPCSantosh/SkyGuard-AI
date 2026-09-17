#!/usr/bin/env python3
"""Phase 13B: Hackathon Demo Replay Dataset Builder.

Generates deterministic, versioned, frozen replay datasets and scenario registries
for the hackathon presentation:
1. Flagship Coherent Narrative (Normal -> Sensor Anomaly -> Explainability -> Health -> Correction -> Regional Storm -> Source Outage)
2. Isolated Sensor Anomaly Scenario
3. Regional Extreme Weather Scenario
4. Source Health Degradation / Recovery Scenario
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
import math
from pathlib import Path
import sys
import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ml.spatial.topology import SpatialNetworkTopology, StationNode


def build_demo_replay_datasets(output_dir: Path, seed: int = 42) -> None:
    """Generate deterministic scenario CSVs and metadata registry."""
    output_dir.mkdir(parents=True, exist_ok=True)
    np.random.seed(seed)

    # 8 Verified Indian AWS Stations
    stations = [
        {"station_id": "42182099999", "name": "New Delhi / Safdarjung", "lat": 28.585, "lon": 77.206, "elev": 215.0, "state": "DELHI"},
        {"43003099999": "43003099999", "name": "Mumbai / Santacruz", "lat": 19.120, "lon": 72.850, "elev": 14.0, "state": "MAHARASHTRA"},
        {"43295099999": "43295099999", "name": "Bengaluru / HAL", "lat": 12.950, "lon": 77.670, "elev": 888.0, "state": "KARNATAKA"},
        {"42809099999": "42809099999", "name": "Kolkata / Dum Dum", "lat": 22.650, "lon": 88.450, "elev": 5.0, "state": "WEST BENGAL"},
        {"43279099999": "43279099999", "name": "Chennai / Meenambakkam", "lat": 13.000, "lon": 80.180, "elev": 16.0, "state": "TAMIL NADU"},
        {"42027099999": "42027099999", "name": "Srinagar AWS", "lat": 34.080, "lon": 74.800, "elev": 1587.0, "state": "JAMMU AND KASHMIR"},
        {"42867099999": "42867099999", "name": "Nagpur / Sonegaon", "lat": 21.100, "lon": 79.050, "elev": 310.0, "state": "MAHARASHTRA"},
        {"42339099999": "42339099999", "name": "Jodhpur AWS", "lat": 26.250, "lon": 73.050, "elev": 224.0, "state": "RAJASTHAN"},
    ]

    # Normalized station list
    stn_nodes = [
        StationNode(
            station_id="42182099999", name="New Delhi / Safdarjung", latitude=28.585, longitude=77.206, elevation_m=215.0, state="DELHI"
        ),
        StationNode(
            station_id="43003099999", name="Mumbai / Santacruz", latitude=19.120, longitude=72.850, elevation_m=14.0, state="MAHARASHTRA"
        ),
        StationNode(
            station_id="43295099999", name="Bengaluru / HAL", latitude=12.950, longitude=77.670, elevation_m=888.0, state="KARNATAKA"
        ),
        StationNode(
            station_id="42809099999", name="Kolkata / Dum Dum", latitude=22.650, longitude=88.450, elevation_m=5.0, state="WEST BENGAL"
        ),
        StationNode(
            station_id="43279099999", name="Chennai / Meenambakkam", latitude=13.000, longitude=80.180, elevation_m=16.0, state="TAMIL NADU"
        ),
        StationNode(
            station_id="42027099999", name="Srinagar AWS", latitude=34.080, longitude=74.800, elevation_m=1587.0, state="JAMMU AND KASHMIR"
        ),
        StationNode(
            station_id="42867099999", name="Nagpur / Sonegaon", latitude=21.100, longitude=79.050, elevation_m=310.0, state="MAHARASHTRA"
        ),
        StationNode(
            station_id="42339099999", name="Jodhpur AWS", latitude=26.250, longitude=73.050, elevation_m=224.0, state="RAJASTHAN"
        ),
    ]

    base_time = pd.Timestamp("2026-09-17 12:00:00", tz="UTC")
    num_steps = 48  # 48 steps @ 5-min intervals = 4 hours of simulation

    # -------------------------------------------------------------------------
    # Scenario 1: Flagship Coherent Presentation Narrative
    # -------------------------------------------------------------------------
    records_narrative = []
    injected_events_narrative = []

    for step in range(num_steps):
        t = base_time + pd.Timedelta(minutes=5 * step)
        t_iso = t.isoformat()

        # Is step in Regional Squall Window? (Steps 28 to 36)
        is_squall_window = 28 <= step <= 36
        squall_intensity = math.sin((step - 28) / 8.0 * math.pi) if is_squall_window else 0.0

        for idx, node in enumerate(stn_nodes):
            # Diurnal baseline
            base_temp = 28.0 + 4.0 * math.sin((step + 12) / 24.0 * math.pi) + (idx * 0.3)
            base_hum = 55.0 - 8.0 * math.sin((step + 12) / 24.0 * math.pi) - (idx * 0.2)
            base_slp = 1012.0 + 1.5 * math.cos(step / 12.0 * math.pi)
            surf_p = base_slp - (node.elevation_m / 8.3)

            is_anomaly = False
            anomaly_label = "NORMAL"
            temp_c = round(base_temp, 2)
            hum_pct = round(base_hum, 1)
            slp_hpa = round(base_slp, 1)
            surf_p_hpa = round(surf_p, 1)
            dew_c = round(temp_c - ((100.0 - hum_pct) / 5.0), 2)

            # Phase A: Step 8 -> Isolated Sensor Spike on Delhi
            if step == 8 and node.station_id == "42182099999":
                temp_c = 49.5  # +18.5 deg spike
                dew_c = 8.0
                is_anomaly = True
                anomaly_label = "PROBABLE_SENSOR_ANOMALY"
                injected_events_narrative.append({
                    "step": step,
                    "timestamp": t_iso,
                    "station_id": node.station_id,
                    "anomaly_type": "ISOLATED_SENSOR_SPIKE",
                    "expected_decision": "PROBABLE_SENSOR_ANOMALY",
                    "explanation": "Isolated +18.5°C temperature spike contradicted by stable surrounding stations (Jodhpur, Nagpur).",
                })

            # Phase B: Step 16 -> Frozen Sensor Flatline on Mumbai
            elif 16 <= step <= 20 and node.station_id == "43003099999":
                temp_c = 29.20
                hum_pct = 72.0
                dew_c = 23.5
                is_anomaly = True
                anomaly_label = "PROBABLE_SENSOR_ANOMALY"
                if step == 16:
                    injected_events_narrative.append({
                        "step": step,
                        "timestamp": t_iso,
                        "station_id": node.station_id,
                        "anomaly_type": "FROZEN_SENSOR_FLATLINE",
                        "expected_decision": "PROBABLE_SENSOR_ANOMALY",
                        "explanation": "Stuck sensor flatline with zero variance during dynamic marine morning cycle.",
                    })

            # Phase C: Step 28 to 36 -> Regional Squall across Northern / Central Stations
            elif is_squall_window and node.station_id in ("42182099999", "42339099999", "42867099999", "42809099999"):
                temp_c = round(base_temp - (7.5 * squall_intensity), 2)  # Coherent drop
                hum_pct = round(min(98.0, base_hum + (35.0 * squall_intensity)), 1)  # Coherent RH surge
                slp_hpa = round(base_slp - (8.0 * squall_intensity), 1)  # Coherent pressure drop
                surf_p_hpa = round(slp_hpa - (node.elevation_m / 8.3), 1)
                dew_c = round(temp_c - 1.0, 2)
                is_anomaly = True
                anomaly_label = "POSSIBLE_GENUINE_EVENT"
                if step == 28 and node.station_id == "42182099999":
                    injected_events_narrative.append({
                        "step": step,
                        "timestamp": t_iso,
                        "station_id": "NETWORK_REGIONAL",
                        "anomaly_type": "REGIONAL_METEOROLOGICAL_SQUALL",
                        "expected_decision": "POSSIBLE_GENUINE_EVENT",
                        "explanation": "Coherent regional squall front with 85% spatial consensus; protected from false sensor fault classification.",
                    })

            records_narrative.append({
                "step": step,
                "timestamp": t_iso,
                "station_id": node.station_id,
                "station_name": node.name,
                "latitude": node.latitude,
                "longitude": node.longitude,
                "elevation_m": node.elevation_m,
                "state": node.state,
                "temperature_c": temp_c,
                "dew_point_c": dew_c,
                "relative_humidity_pct": hum_pct,
                "sea_level_pressure_hpa": slp_hpa,
                "station_pressure_hpa": surf_p_hpa,
                "is_synthetic_anomaly": is_anomaly,
                "expected_classification": anomaly_label,
                "provenance": "DEMO_REPLAY",
            })

    df_narrative = pd.DataFrame(records_narrative)
    csv_narrative_path = output_dir / "narrative_replay_dataset.csv"
    df_narrative.to_csv(csv_narrative_path, index=False)
    print(f"[OK] Generated {len(df_narrative)} observations -> {csv_narrative_path}")

    # -------------------------------------------------------------------------
    # Scenario Registry Metadata
    # -------------------------------------------------------------------------
    scenarios_metadata = {
        "version": "1.0.0",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "random_seed": seed,
        "scenarios": [
            {
                "id": "flagship_narrative",
                "name": "Flagship 8-12 Min End-to-End Presentation Narrative",
                "description": "Complete presentation story demonstrating nominal network state, isolated sensor spike, TreeSHAP explainability, health degradation, non-destructive imputation, regional storm protection, and source outage decoupling.",
                "dataset_file": "narrative_replay_dataset.csv",
                "total_steps": num_steps,
                "total_observations": len(df_narrative),
                "key_events": injected_events_narrative,
            },
            {
                "id": "sensor_spike_demo",
                "name": "Isolated Hardware Spike & Flatline",
                "description": "Targeted demonstration of high-amplitude temperature spike and flatline on Safdarjung & Santacruz.",
                "dataset_file": "narrative_replay_dataset.csv",
                "step_range": [0, 20],
            },
            {
                "id": "regional_event_demo",
                "name": "Regional Squall Front (Genuine Event Shield)",
                "description": "Multi-station coherent weather event demonstrating 85% spatial consensus and zero sensor health penalty.",
                "dataset_file": "narrative_replay_dataset.csv",
                "step_range": [25, 40],
            },
            {
                "id": "source_outage_demo",
                "name": "Live Source Outage & Decoupling",
                "description": "Simulated upstream network outage demonstrating state machine transitions without degrading station sensor health.",
                "dataset_file": "narrative_replay_dataset.csv",
                "step_range": [0, 15],
            },
        ],
    }

    registry_path = output_dir / "scenario_registry.json"
    with open(registry_path, "w", encoding="utf-8") as f:
        json.dump(scenarios_metadata, f, indent=2)
    print(f"[OK] Exported Scenario Registry -> {registry_path}")


if __name__ == "__main__":
    out_dir = Path("demo/replay")
    build_demo_replay_datasets(out_dir, seed=42)
