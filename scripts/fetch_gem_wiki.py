"""Fetch GEM wiki pages for Saudi solar and wind farms and parse their phase tables.

    python -m scripts.fetch_gem_wiki

Raw parsed-HTML per page goes to data/raw/gem_wiki/<stamp>/ with a SHA-256 manifest.
The phase table goes to data/processed/gem_phases.csv. GEM wiki content is licensed
CC BY-NC-SA (page footer, checked 2026-10-18): attribution required, non-commercial use, derived
data shared alike.
"""

from __future__ import annotations

import hashlib
import io
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
API = "https://www.gem.wiki/w/api.php"
CATEGORIES = {"solar": "Category:Solar farms in Saudi Arabia", "wind": "Category:Wind farms in Saudi Arabia"}


def clean(cell) -> str:
    return re.sub(r"\[\d+\]", "", str(cell)).strip()


def members(category: str) -> list[str]:
    r = requests.get(API, params={"action": "query", "list": "categorymembers", "cmtitle": category,
                                  "cmlimit": 500, "format": "json"}, timeout=60)
    r.raise_for_status()
    return [m["title"] for m in r.json()["query"]["categorymembers"]]


def parse_page(title: str, html: str, tech_category: str) -> list[dict]:
    tables = pd.read_html(io.StringIO(html))
    details = next((t for t in tables if "Status" in t.columns and "Nameplate capacity" in t.columns), None)
    loc = next((t for t in tables if any("Coordinates" in str(c) for c in t.columns)), None)
    if details is None:
        return [{"page": title, "tech_category": tech_category, "parse_note": "no phase table"}]
    coord_col = next((c for c in loc.columns if "Coordinates" in str(c)), None) if loc is not None else None
    rows = []
    for i, d in details.reset_index(drop=True).iterrows():
        cap = clean(d["Nameplate capacity"])
        m = re.search(r"([\d.,]+)\s*(MW\w*)", cap)
        coord = clean(loc.iloc[min(i, len(loc) - 1)][coord_col]) if coord_col else ""
        cm = re.search(r"(-?\d+\.\d+),\s*(-?\d+\.\d+)\s*\((\w+)\)", coord)
        location = clean(loc.iloc[min(i, len(loc) - 1)]["Location"]) if loc is not None and "Location" in loc else ""
        rows.append({
            "page": title, "tech_category": tech_category,
            "phase": clean(d.get("Phase name", d.get("Unit name", i + 1))),
            "status": clean(d["Status"]),
            "commissioning_year": pd.to_numeric(clean(d.get("Commissioning year", "")), errors="coerce"),
            "capacity_mw": float(m.group(1).replace(",", "")) if m else np.nan,
            "capacity_unit": m.group(2) if m else cap,
            "technology": clean(d.get("Technology", "")),
            "location_text": location,
            "lat": float(cm.group(1)) if cm else np.nan,
            "lon": float(cm.group(2)) if cm else np.nan,
            "coord_accuracy": cm.group(3) if cm else "none",
            "parse_note": "",
        })
    return rows


def main() -> None:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    raw = ROOT / "data" / "raw" / "gem_wiki" / stamp
    raw.mkdir(parents=True)
    manifest, rows = [], []
    for tech, cat in CATEGORIES.items():
        for title in members(cat):
            r = requests.get(API, params={"action": "parse", "page": title, "prop": "text",
                                          "format": "json", "formatversion": 2}, timeout=60)
            r.raise_for_status()
            html = r.json()["parse"]["text"]
            fname = re.sub(r"[^A-Za-z0-9]+", "_", title) + ".html"
            (raw / fname).write_text(html, encoding="utf-8")
            manifest.append({"title": title, "file": fname, "url": r.url,
                             "sha256": hashlib.sha256(html.encode()).hexdigest(),
                             "retrieved_utc": datetime.now(timezone.utc).isoformat()})
            rows.extend(parse_page(title, html, tech))
            time.sleep(0.3)
    (raw / "manifest.json").write_text(json.dumps({"license": "CC BY-NC-SA (GEM wiki)", "pages": manifest}, indent=2))
    out = pd.DataFrame(rows)
    (ROOT / "data" / "processed").mkdir(parents=True, exist_ok=True)
    out.to_csv(ROOT / "data" / "processed" / "gem_phases.csv", index=False)
    print(f"{len(manifest)} pages, {len(out)} phase rows -> data/processed/gem_phases.csv")


if __name__ == "__main__":
    main()
