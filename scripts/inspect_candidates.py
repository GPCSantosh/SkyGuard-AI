"""Candidate Dataset Discovery and Inspection Script for SkyGuard AI (Phase 1A).

Performs lightweight verification and schema inspection of historical weather datasets:
1. NOAA NCEI Global Hourly / ISD (Integrated Surface Database)
2. Meteostat Python / Bulk API
3. Open-Meteo Historical Archive (Reanalysis ERA5)
4. IMD AWS / MOSDAC / Open Government Data portals
"""

import io
import json
import os
import urllib.request
from pathlib import Path
import pandas as pd

OUTPUT_DIR = Path(__file__).resolve().parents[1] / "data" / "external"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Candidate Indian WMO / ISD Station IDs across diverse climate zones
INDIAN_STATIONS = {
    "42182099999": {"name": "New Delhi (Safdarjung)", "lat": 28.58, "lon": 77.20, "elev": 215},
    "42181099999": {"name": "New Delhi (IGI Airport/Palam)", "lat": 28.56, "lon": 77.10, "elev": 237},
    "43003099999": {"name": "Mumbai (Santacruz)", "lat": 19.12, "lon": 72.85, "elev": 14},
    "43057099999": {"name": "Mumbai (Colaba)", "lat": 18.90, "lon": 72.82, "elev": 11},
    "43295099999": {"name": "Bengaluru (HAL Airport)", "lat": 12.95, "lon": 77.67, "elev": 888},
    "42809099999": {"name": "Kolkata (Dum Dum/NSCBI)", "lat": 22.65, "lon": 88.45, "elev": 5},
    "43279099999": {"name": "Chennai (Meenambakkam)", "lat": 12.99, "lon": 80.18, "elev": 16},
    "42027099999": {"name": "Srinagar", "lat": 34.08, "lon": 74.83, "elev": 1587},
    "42867099999": {"name": "Nagpur (Sonegaon)", "lat": 21.09, "lon": 79.06, "elev": 310},
    "43192099999": {"name": "Goa (Dabolim)", "lat": 15.38, "lon": 73.83, "elev": 56},
    "43371099999": {"name": "Thiruvananthapuram", "lat": 8.48, "lon": 76.95, "elev": 64},
    "43128099999": {"name": "Hyderabad (Begumpet)", "lat": 17.45, "lon": 78.47, "elev": 531},
    "43063099999": {"name": "Pune", "lat": 18.53, "lon": 73.85, "elev": 560},
    "42314099999": {"name": "Dibrugarh (Mohanbari)", "lat": 27.48, "lon": 95.02, "elev": 110},
    "42647099999": {"name": "Ahmedabad", "lat": 23.07, "lon": 72.63, "elev": 55},
    "42410099999": {"name": "Guwahati (Borjhar)", "lat": 26.11, "lon": 91.59, "elev": 54},
    "42754099999": {"name": "Indore", "lat": 22.72, "lon": 75.80, "elev": 567},
    "42101099999": {"name": "Patiala", "lat": 30.33, "lon": 76.47, "elev": 251},
    "42339099999": {"name": "Jodhpur", "lat": 26.25, "lon": 73.05, "elev": 224},
    "42475099999": {"name": "Allahabad (Bamrauli)", "lat": 25.45, "lon": 81.73, "elev": 98},
    "43369099999": {"name": "Minicoy (Lakshadweep)", "lat": 8.30, "lon": 73.15, "elev": 2},
    "43346099999": {"name": "Port Blair (Andaman)", "lat": 11.67, "lon": 92.72, "elev": 16},
    "42071099999": {"name": "Amritsar (Rajasansi)", "lat": 31.71, "lon": 74.80, "elev": 230}
}


def test_noaa_ncei_isd():
    print("=" * 70)
    print("1. INSPECTING NOAA NCEI GLOBAL HOURLY (ISD)")
    print("=" * 70)
    year = 2024
    found = 0
    sample_df = None
    
    for st_id, meta in list(INDIAN_STATIONS.items()):
        url = f"https://www.ncei.noaa.gov/data/global-hourly/access/{year}/{st_id}.csv"
        req = urllib.request.Request(url, headers={"User-Agent": "SkyGuardAI-Research/1.0"})
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = resp.read()
                df = pd.read_csv(io.BytesIO(data))
                found += 1
                print(f"  [OK] {st_id} ({meta['name']}): {len(df)} records in {year}")
                if sample_df is None:
                    sample_df = df
                    sample_path = OUTPUT_DIR / f"sample_noaa_isd_{st_id}.csv"
                    df.head(50).to_csv(sample_path, index=False)
                    print(f"       -> Saved 50-row inspection sample to {sample_path.name}")
        except Exception as e:
            print(f"  [FAIL] {st_id} ({meta['name']}): {e}")
            
    print(f"\nNOAA NCEI ISD Summary: {found}/{len(INDIAN_STATIONS)} stations verified accessible for {year}.\n")
    if sample_df is not None:
        print("Sample NOAA Columns:", list(sample_df.columns[:15]))
        print("\nSample TMP, DEW, SLP rows:")
        print(sample_df[["DATE", "STATION", "LATITUDE", "LONGITUDE", "ELEVATION", "TMP", "DEW", "SLP", "WND"]].head(5).to_string())


def test_open_meteo_archive():
    print("\n" + "=" * 70)
    print("2. INSPECTING OPEN-METEO HISTORICAL (ERA5 REANALYSIS)")
    print("=" * 70)
    lat, lon = 28.58, 77.20 # Delhi
    url = f"https://archive-api.open-meteo.com/v1/archive?latitude={lat}&longitude={lon}&start_date=2024-01-01&end_date=2024-01-07&hourly=temperature_2m,relative_humidity_2m,surface_pressure,pressure_msl,dew_point_2m,precipitation,wind_speed_10m&timezone=UTC"
    req = urllib.request.Request(url, headers={"User-Agent": "SkyGuardAI-Research/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            hourly = data.get("hourly", {})
            df = pd.DataFrame(hourly)
            print(f"  [OK] Open-Meteo Archive fetched: {len(df)} hourly timestamps (Jan 1-7, 2024)")
            print("  Columns:", list(df.columns))
            print(df.head(4).to_string())
            sample_path = OUTPUT_DIR / "sample_open_meteo_delhi.csv"
            df.head(50).to_csv(sample_path, index=False)
            print(f"  -> Saved 50-row inspection sample to {sample_path.name}")
    except Exception as e:
        print(f"  [FAIL] Open-Meteo fetch failed: {e}")


def test_rh_derivation_equation():
    print("\n" + "=" * 70)
    print("3. RELATIVE HUMIDITY DERIVATION FROM TEMPERATURE & DEW POINT")
    print("=" * 70)
    # Using August-Roche-Magnus approximation:
    # Es(T) = 6.112 * exp((17.67 * T) / (T + 243.5))
    # E(Td) = 6.112 * exp((17.67 * Td) / (Td + 243.5))
    # RH = 100 * (E(Td) / Es(T))
    import math

    def compute_rh(t: float, td: float) -> float:
        a = 17.625
        b = 243.04
        alpha = ((a * td) / (b + td))
        beta = ((a * t) / (b + t))
        return 100.0 * math.exp(alpha - beta)

    test_cases = [
        (30.0, 20.0), # Hot humid
        (45.0, 10.0), # Extreme dry heat
        (10.0, 9.0),  # Cold fog
        (25.0, 25.0), # Saturated 100%
        (5.0, -2.0)   # Winter dry
    ]
    print(f"  {'Temp (°C)':<10} | {'Dew Point (°C)':<15} | {'Derived RH (%)':<15}")
    print("  " + "-" * 45)
    for t, td in test_cases:
        rh = compute_rh(t, td)
        print(f"  {t:<10.1f} | {td:<15.1f} | {rh:<15.2f}")


if __name__ == "__main__":
    test_noaa_ncei_isd()
    test_open_meteo_archive()
    test_rh_derivation_equation()
