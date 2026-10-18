"""Turn raw exports into tidy analysis tables without guessing silently.

Field names come from config/column_maps.yaml. Each loader picks the first candidate column
that exists (case-insensitive) and raises ColumnMappingError, listing the real columns, when a
required field cannot be found. That way an unexpected schema stops the run instead of
producing wrong numbers.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from src.renewable_model import TZ

CONFIG_PATH = Path(__file__).resolve().parents[1] / "config" / "column_maps.yaml"
POWER_FILL = -999.0


class ColumnMappingError(KeyError):
    pass


def load_column_maps(path: Path = CONFIG_PATH) -> dict:
    with open(path, encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def find_column(df: pd.DataFrame, candidates: list[str], field: str, required: bool = True) -> str | None:
    lookup = {str(c).strip().lower(): c for c in df.columns}
    for cand in candidates:
        if cand.lower() in lookup:
            return lookup[cand.lower()]
    if required:
        raise ColumnMappingError(
            f"no column for '{field}'; tried {candidates}; file has {list(df.columns)}")
    return None


def _label_to_measure(label: str, labels: dict[str, list[str]]) -> str | None:
    key = str(label).strip().lower()
    for measure, names in labels.items():
        if key in (n.lower() for n in names):
            return measure
    return None


def tidy_monthly_load(df: pd.DataFrame, maps: dict | None = None,
                      on_order_violation: str = "raise") -> pd.DataFrame:
    """D2 -> [date (month start), region, max, avg, min, order_violation] in the source unit (GW).

    Rows breaking min <= avg <= max raise by default; with on_order_violation="flag" they are
    kept and flagged for src.cleaning to handle explicitly.
    """
    m = (maps or load_column_maps())["monthly_load_by_region"]
    date_c = find_column(df, m["date"], "date")
    region_c = find_column(df, m["region"], "region")
    measure_c = find_column(df, m["measure"], "measure", required=False)

    base = pd.DataFrame({
        "date": pd.to_datetime(df[date_c].astype(str), errors="coerce", format="mixed"),
        "region": df[region_c].astype(str).str.strip(),
    })
    if base["date"].isna().any():
        bad = df.loc[base["date"].isna(), date_c].unique()[:5]
        raise ValueError(f"unparseable dates in '{date_c}', e.g. {list(bad)}")
    base["date"] = base["date"].dt.to_period("M").dt.to_timestamp()

    if measure_c is not None:
        value_c = find_column(df, m["value"], "value")
        base["measure"] = df[measure_c].map(lambda v: _label_to_measure(v, m["measure_labels"]))
        unknown = df.loc[base["measure"].isna(), measure_c].unique()
        if len(unknown):
            raise ValueError(f"unrecognised measure labels {list(unknown)}; extend measure_labels")
        base["value"] = pd.to_numeric(df[value_c], errors="coerce")
        dupes = base.duplicated(["date", "region", "measure"]).sum()
        if dupes:
            raise ValueError(f"{dupes} duplicate (date, region, measure) rows")
        out = base.pivot_table(index=["date", "region"], columns="measure", values="value",
                               aggfunc="first").reset_index()
    else:
        out = base.copy()
        for measure, key in (("max", "wide_max"), ("avg", "wide_avg"), ("min", "wide_min")):
            col = find_column(df, m[key], measure, required=(measure == "max"))
            out[measure] = pd.to_numeric(df[col], errors="coerce") if col else np.nan
    for measure in ("max", "avg", "min"):
        if measure not in out:
            out[measure] = np.nan
    bad_order = (out["min"] > out["avg"]) | (out["avg"] > out["max"])
    if bad_order.any() and on_order_violation == "raise":
        raise ValueError(f"{int(bad_order.sum())} rows violate min <= avg <= max")
    out["order_violation"] = bad_order
    return (out[["date", "region", "max", "avg", "min", "order_violation"]]
            .sort_values(["region", "date"]).reset_index(drop=True))


def split_kapsarc_load_indicator(df: pd.DataFrame) -> pd.DataFrame:
    """D2 stores region and measure in one string, e.g. 'Central region - Maximum - (GW)'.

    Splits it into `region` and `type` columns (verified layout, download of 2026-10-18).
    Raises if any indicator does not follow the pattern.
    """
    pat = r"^\s*(?P<region>\w+) region\s*-\s*(?P<type>Maximum|Average|Minimum)\b.*\(GW\)\s*$"
    parts = df["indicator"].astype(str).str.extract(pat)
    if parts.isna().any().any():
        bad = df.loc[parts.isna().any(axis=1), "indicator"].unique()[:5]
        raise ValueError(f"unexpected indicator labels: {list(bad)}")
    return pd.DataFrame({"date": df["date"], "region": parts["region"], "type": parts["type"],
                         "value": df["value"]})


def parse_point(value) -> tuple[float, float]:
    """Read 'lat, lon', '[lat, lon]' or {'lat':..,'lon':..}; returns (nan, nan) when absent."""
    if isinstance(value, dict):
        return float(value.get("lat", np.nan)), float(value.get("lon", np.nan))
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return np.nan, np.nan
    nums = re.findall(r"-?\d+(?:\.\d+)?", str(value))
    if len(nums) >= 2:
        return float(nums[0]), float(nums[1])
    return np.nan, np.nan


def tidy_projects(df: pd.DataFrame, source: str, maps: dict | None = None) -> pd.DataFrame:
    """D7 or GEM -> [source, name, technology, capacity_mw, status_raw, year, lat, lon, coord_accuracy, city]."""
    allm = maps or load_column_maps()
    key = "renewable_projects" if source == "kapsarc" else "gem_projects"
    m = allm[key]
    out = pd.DataFrame({
        "source": source,
        "name": df[find_column(df, m["name"], "name")].astype(str).str.strip(),
        "technology": df[find_column(df, m["technology"], "technology")].astype(str).str.strip(),
        "capacity_mw": pd.to_numeric(df[find_column(df, m["capacity_mw"], "capacity_mw")], errors="coerce"),
        "status_raw": df[find_column(df, m["status"], "status")].astype(str).str.strip(),
    })
    if source == "kapsarc":
        year_c = find_column(df, m["year"], "year", required=False)
        out["year"] = pd.to_numeric(df[year_c], errors="coerce") if year_c else np.nan
        loc_c = find_column(df, m["location"], "location", required=False)
        pts = df[loc_c].map(parse_point) if loc_c else pd.Series([(np.nan, np.nan)] * len(df))
        out["lat"] = [p[0] for p in pts]
        out["lon"] = [p[1] for p in pts]
        out["coord_accuracy"] = np.where(out["lat"].notna(), "kapsarc point (accuracy unknown)", "none")
        city_c = find_column(df, m["city"], "city", required=False)
        out["city"] = df[city_c].astype(str) if city_c else None
    else:
        out["year"] = np.nan
        out["lat"] = pd.to_numeric(df[find_column(df, m["lat"], "lat")], errors="coerce")
        out["lon"] = pd.to_numeric(df[find_column(df, m["lon"], "lon")], errors="coerce")
        acc_c = find_column(df, m["accuracy"], "accuracy", required=False)
        out["coord_accuracy"] = ("gem " + df[acc_c].astype(str).str.lower()) if acc_c else "gem unknown"
        out["city"] = None
        country_c = find_column(df, m["country"], "country", required=False)
        if country_c:
            out = out[df[country_c].astype(str).str.contains("Saudi", case=False).values]
    if (out["capacity_mw"] <= 0).any():
        raise ValueError("non-positive capacities present")
    return out.reset_index(drop=True)


def nasa_power_weather(payload: dict | str | Path) -> pd.DataFrame:
    """NASA POWER hourly JSON (time-standard=UTC) -> [ghi, dni, dhi, temp_air, wind_speed] in local time.

    Fill values (-999) become NaN and are reported, not interpolated.
    """
    if not isinstance(payload, dict):
        payload = json.loads(Path(payload).read_text(encoding="utf-8"))
    params = payload["properties"]["parameter"]
    rename = {"ALLSKY_SFC_SW_DWN": "ghi", "ALLSKY_SFC_SW_DNI": "dni", "ALLSKY_SFC_SW_DIFF": "dhi",
              "T2M": "temp_air", "WS10M": "wind_speed", "WS50M": "wind_speed_50m"}
    cols = {}
    for src, dst in rename.items():
        if src in params:
            s = pd.Series(params[src], dtype=float)
            s.index = pd.to_datetime(s.index, format="%Y%m%d%H", utc=True)
            cols[dst] = s.replace(POWER_FILL, np.nan)
    missing = {"ghi", "dni", "dhi", "temp_air"} - set(cols)
    if missing:
        raise ColumnMappingError(f"NASA POWER payload lacks {sorted(missing)}")
    df = pd.DataFrame(cols).sort_index()
    df.index = df.index.tz_convert(TZ)
    df.attrs["n_missing"] = int(df.isna().any(axis=1).sum())
    return df
