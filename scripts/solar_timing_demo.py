"""Clear-sky solar timing across Saudi longitudes: an illustration that needs no external data.

    python -m scripts.solar_timing_demo

Writes results/tables/solar_timing_clearsky.csv. Everything in it is MODELLED under clear
skies with an assumed 40 C air temperature in July (15 C in January). Clear-sky output is an
upper envelope, with no dust, cloud or curtailment. The peak windows are SCENARIO assumptions,
not observed peak hours. The table shows how solar geometry and a single national clock time
interact. It does not estimate any project's real contribution.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.metrics import peak_window_capacity_factor, window_mask
from src.renewable_model import PVSystem, clearsky_weather, per_kw_ac_output, solar_noon_local

OUT = Path(__file__).resolve().parents[1] / "results" / "tables" / "solar_timing_clearsky.csv"

# Coordinates: GEM wiki pages (search log W07, exact/approximate flag as published there) and
# city centres (approximate, for operating-area load centres).
SITES = [
    ("Sudair Solar PV (project)", 25.7688, 45.5872, "GEM exact"),
    ("Tabuk Province solar I (project)", 28.1043, 35.3227, "GEM exact"),
    ("Al-Faisaliah/Shuaibah Solar (project)", 25.6243, 42.3528, "GEM approximate"),
    ("Saad Solar PV 2 (project)", 24.7117, 46.6740, "GEM approximate"),
    ("Riyadh (Central load centre)", 24.71, 46.68, "city centre, approximate"),
    ("Jeddah (Western load centre)", 21.54, 39.17, "city centre, approximate"),
    ("Dammam (Eastern load centre)", 26.43, 50.10, "city centre, approximate"),
    ("Abha (Southern load centre)", 18.22, 42.50, "city centre, approximate"),
]

# Peak windows in local clock hours (UTC+3), [start, end). Scenario assumptions.
WINDOWS = {"12-15": (12, 15), "14-17": (14, 17), "16-19": (16, 19), "19-22": (19, 22)}


def site_rows(name: str, lat: float, lon: float, source: str) -> list[dict]:
    rows = []
    for tracking in (True, False):
        system = PVSystem(tracking=tracking)
        july = pd.date_range("2023-07-01", "2023-07-31 23:00", freq="1h", tz="Asia/Riyadh")
        out = per_kw_ac_output(lat, lon, clearsky_weather(lat, lon, july, 40.0), system)
        row = {
            "site": name, "lat": lat, "lon": lon, "coord_source": source,
            "mounting": "single-axis tracker" if tracking else "fixed tilt = latitude",
            "solar_noon_jul21": solar_noon_local(lat, lon, "2023-07-21").strftime("%H:%M"),
            "solar_noon_jan21": solar_noon_local(lat, lon, "2023-01-21").strftime("%H:%M"),
            "jul_daily_cf": round(float(out.mean()), 3),
        }
        for label, (h0, h1) in WINDOWS.items():
            mask = window_mask(out.index, h0, h1)
            row[f"jul_cf_{label}"] = round(peak_window_capacity_factor(out, mask), 3)
        rows.append(row)
    return rows


def main() -> None:
    rows = [r for site in SITES for r in site_rows(*site)]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(OUT, index=False)
    print(f"wrote {OUT.relative_to(OUT.parents[2])} ({len(rows)} rows) - clear-sky model output")


if __name__ == "__main__":
    main()
