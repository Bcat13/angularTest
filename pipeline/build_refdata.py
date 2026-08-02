"""Process raw reference datasets into compact JSONs committed to the repo.

Inputs (downloaded, gitignored):
  refdata/airports_raw.csv  - OurAirports (https://davidmegginson.github.io/ourairports-data/airports.csv)
  refdata/HD2023.csv        - IPEDS institution directory (nces.ed.gov)

Outputs (committed):
  refdata/airports.json         - US/CA large+medium airports with scheduled service
  refdata/us_institutions.json  - name, city, state, lat/lon, Carnegie 2021 basic code
"""
import csv
import json
import sys
from pathlib import Path

REFDATA = Path(__file__).parent / "refdata"


def build_airports():
    out = []
    with open(REFDATA / "airports_raw.csv", newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["iso_country"] not in ("US", "CA"):
                continue
            if row["type"] not in ("large_airport", "medium_airport"):
                continue
            if row["scheduled_service"] != "yes":
                continue
            out.append(
                {
                    "name": row["name"],
                    "iata": row["iata_code"],
                    "lat": round(float(row["latitude_deg"]), 4),
                    "lon": round(float(row["longitude_deg"]), 4),
                    "city": row["municipality"],
                    "country": row["iso_country"],
                    "large": row["type"] == "large_airport",
                }
            )
    (REFDATA / "airports.json").write_text(json.dumps(out, indent=0))
    print(f"airports.json: {len(out)} airports")


def build_us_institutions():
    out = []
    # IPEDS CSVs are latin-1 encoded
    with open(REFDATA / "HD2023.csv", newline="", encoding="latin-1") as f:
        for row in csv.DictReader(f):
            try:
                lat, lon = float(row["LATITUDE"]), float(row["LONGITUD"])
            except (ValueError, KeyError):
                continue
            # ICLEVEL 1 = four-year-or-above; skip 2-year/less-than-2-year
            if row.get("ICLEVEL") != "1":
                continue
            out.append(
                {
                    "name": row["INSTNM"],
                    "city": row["CITY"],
                    "state": row["STABBR"],
                    "lat": round(lat, 4),
                    "lon": round(lon, 4),
                    "c21": int(row["C21BASIC"]) if row.get("C21BASIC", "").lstrip("-").isdigit() else None,
                }
            )
    (REFDATA / "us_institutions.json").write_text(json.dumps(out, indent=0))
    print(f"us_institutions.json: {len(out)} institutions")


if __name__ == "__main__":
    build_airports()
    build_us_institutions()
    sys.exit(0)
