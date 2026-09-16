"""Inspect the 23-station network topology and geodesic neighbor relationships."""

from __future__ import annotations

from pathlib import Path
import sys
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ml.features.spatial import SpatialNeighborExtractor


def main() -> int:
    stations_path = REPO_ROOT / "configs" / "stations.yaml"
    with open(stations_path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    stations = cfg.get("stations", [])
    print("=" * 80)
    print(f"SkyGuard AI — 23-Station Geodesic Spatial Topology Analysis")
    print(f"Total Configured Target Stations: {len(stations)}")
    print("=" * 80)

    meta = {
        str(s["station_id"]): {
            "latitude": float(s["latitude"]),
            "longitude": float(s["longitude"]),
            "elevation_m": float(s.get("elevation", 0.0)),
            "name": s["name"],
            "state": s.get("state", "India"),
        }
        for s in stations
    }

    extractor = SpatialNeighborExtractor(station_metadata=meta, max_distance_km=600.0, max_neighbors=5)
    
    print(f"\n{'Station ID':<13} | {'Station Name':<32} | {'Elev(m)':<7} | Neighbors (within 600 km)")
    print("-" * 105)

    isolated_count = 0
    for s_id, s_data in meta.items():
        neighbors = extractor.find_nearest_neighbors(s_id)
        if not neighbors:
            isolated_count += 1
            n_str = "None (Isolated / Maritime Island)"
        else:
            n_str = ", ".join([f"{meta[n[0]]['name']} ({n[1]:.0f} km)" for n in neighbors])

        print(f"{s_id:<13} | {s_data['name']:<32} | {s_data['elevation_m']:<7.1f} | {n_str}")

    print("-" * 105)
    print(f"\n[+] Total Network Stations: {len(stations)}")
    print(f"[+] Connected Stations:     {len(stations) - isolated_count}")
    print(f"[+] Isolated/Island Nodes:  {isolated_count} (Minicoy Island, Port Blair)")
    print("=" * 80)
    return 0


if __name__ == "__main__":
    sys.exit(main())
