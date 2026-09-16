"""NOAA NCEI Integrated Surface Database (ISD) Ingestion CLI Script for SkyGuard AI.

Usage:
    # Ingest local sample file
    python scripts/ingest_noaa.py --input-file data/external/sample_noaa_isd_42182099999.csv

    # Download, ingest, and profile a station for a specific year
    python scripts/ingest_noaa.py --station 42182099999 --year 2024 --download-if-missing

    # Profile only (dry-run)
    python scripts/ingest_noaa.py --input-file data/raw/42182099999_2024.csv --profile-only
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

# Ensure repository root is on Python search path
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import pandas as pd

from backend.app.connectors.noaa_isd import NOAAISDConnector
from backend.app.ingestion.noaa_parser import NOAAParser, NOAAParserConfig
from backend.app.ingestion.profiler import DatasetProfiler


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="SkyGuard AI — NOAA ISD Historical Telemetry Ingestion Pipeline"
    )
    parser.add_argument(
        "--station",
        type=str,
        default=None,
        help="NOAA USAF-WBAN Station ID (e.g. 42182099999)",
    )
    parser.add_argument(
        "--year",
        type=int,
        default=2024,
        help="Observation year to ingest (default: 2024)",
    )
    parser.add_argument(
        "--input-file",
        type=str,
        default=None,
        help="Direct path to an existing raw NOAA ISD CSV file",
    )
    parser.add_argument(
        "--raw-dir",
        type=str,
        default="data/raw",
        help="Directory to store immutable raw CSV downloads (default: data/raw)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="data/processed",
        help="Directory to store normalized processed observations (default: data/processed)",
    )
    parser.add_argument(
        "--output-format",
        choices=["csv", "jsonl", "all"],
        default="all",
        help="Processed export format (default: all)",
    )
    parser.add_argument(
        "--download-if-missing",
        action="store_true",
        help="Download raw file from NOAA NCEI if not found locally",
    )
    parser.add_argument(
        "--profile-only",
        action="store_true",
        help="Run dataset profiling without writing processed files",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    print("=" * 75)
    print("SkyGuard AI — NOAA ISD Ingestion Pipeline (Phase 1B)")
    print("=" * 75)

    raw_dir = Path(args.raw_dir)
    output_dir = Path(args.output_dir)
    raw_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    parser = NOAAParser()

    # Determine input source
    if args.input_file:
        input_path = Path(args.input_file)
        if not input_path.is_file():
            print(f"[ERROR] Input file not found: {input_path}", file=sys.stderr)
            return 1
        print(f"[*] Parsing local file: {input_path}")
        observations = parser.parse_file(input_path)
        station_id = observations[0].station_id if observations else "UNKNOWN"
        year = args.year
    elif args.station:
        station_id = args.station
        year = args.year
        print(f"[*] Ingesting station: {station_id} for year: {year}")
        connector = NOAAISDConnector(
            station_id=station_id,
            year=year,
            local_raw_dir=raw_dir,
            auto_download=args.download_if_missing,
        )
        try:
            observations = list(connector.fetch_observations())
        except Exception as e:
            print(f"[ERROR] Ingestion failed for station {station_id}: {e}", file=sys.stderr)
            return 1
    else:
        print("[ERROR] Must specify either --input-file or --station", file=sys.stderr)
        return 1

    print(f"[+] Successfully parsed {len(observations):,} normalized records.")

    if not observations:
        print("[WARN] No observations found in input.")
        return 0

    # 1. Dataset Profiling
    print("\n[*] Profiling dataset quality and cadence...")
    profile = DatasetProfiler.profile_observations(observations)
    print("\n" + profile.summary_markdown() + "\n")

    if args.profile_only:
        print("[*] Dry-run/profile-only mode enabled. Skipping file export.")
        return 0

    # 2. Export Normalized Observations to data/processed
    base_name = f"{station_id}_{year}_normalized"
    
    # Convert observations to list of dicts for export
    records_data = []
    for obs in observations:
        rec = {
            "station_id": obs.station_id,
            "station_name": obs.station_name,
            "timestamp": obs.timestamp.isoformat(),
            "latitude": obs.latitude,
            "longitude": obs.longitude,
            "elevation_m": obs.elevation,
            "temperature_c": obs.temperature,
            "dew_point_c": obs.dew_point_c,
            "sea_level_pressure_hpa": obs.pressure,
            "station_pressure_hpa": obs.station_pressure_hpa,
            "relative_humidity_pct": obs.humidity,
            "relative_humidity_source": obs.relative_humidity_source,
            "source": obs.source,
            "report_type": obs.report_type,
            "data_quality_status": obs.data_quality_status,
            "raw_quality_flags": obs.raw_quality_flags,
            "is_synthetic": obs.is_synthetic,
            "ingestion_timestamp": obs.ingestion_timestamp.isoformat(),
        }
        records_data.append(rec)

    df_norm = pd.DataFrame(records_data)

    if args.output_format in ("csv", "all"):
        csv_path = output_dir / f"{base_name}.csv"
        df_norm.to_csv(csv_path, index=False)
        print(f"[+] Exported normalized CSV: {csv_path} ({len(df_norm):,} rows)")

    if args.output_format in ("jsonl", "all"):
        jsonl_path = output_dir / f"{base_name}.jsonl"
        with open(jsonl_path, "w", encoding="utf-8") as f:
            for rec in records_data:
                f.write(json.dumps(rec) + "\n")
        print(f"[+] Exported normalized JSONL: {jsonl_path} ({len(records_data):,} records)")

    # Save profile JSON artifact
    profile_path = output_dir / f"{station_id}_{year}_profile.json"
    with open(profile_path, "w", encoding="utf-8") as f:
        f.write(profile.model_dump_json(indent=2))
    print(f"[+] Exported dataset profile JSON: {profile_path}")

    print("\n[SUCCESS] Ingestion and quality normalization complete.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
