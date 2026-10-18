"""Map administrative regions to SEC operating areas under every plausible assignment.

The mapping is an unverified assumption (see config/region_mapping.yaml), so analysis code
should iterate over `scenarios()` and report the spread of results, not just the base case.
"""

from __future__ import annotations

from itertools import product
from pathlib import Path

import pandas as pd
import yaml

CONFIG_PATH = Path(__file__).resolve().parents[1] / "config" / "region_mapping.yaml"


def load_mapping(path: Path = CONFIG_PATH) -> dict:
    with open(path, encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh)
    areas = set(cfg["operating_areas"])
    for region, area in cfg["base"].items():
        if area not in areas:
            raise ValueError(f"{region}: unknown operating area {area!r}")
    for region, alts in cfg.get("alternatives", {}).items():
        if region not in cfg["base"]:
            raise ValueError(f"alternative given for unmapped region {region!r}")
        unknown = set(alts) - areas
        if unknown:
            raise ValueError(f"{region}: unknown operating areas {sorted(unknown)}")
    return cfg


def scenarios(cfg: dict | None = None) -> list[dict[str, str]]:
    """Every mapping obtained by giving each ambiguous region its base or an alternative area."""
    cfg = cfg or load_mapping()
    ambiguous = list(cfg.get("alternatives", {}))
    choices = [[cfg["base"][r], *cfg["alternatives"][r]] for r in ambiguous]
    out = []
    for combo in product(*choices):
        mapping = dict(cfg["base"])
        mapping.update(zip(ambiguous, combo))
        out.append(mapping)
    return out


def aggregate_to_areas(values: pd.Series, mapping: dict[str, str]) -> pd.Series:
    """Sum region-indexed values into operating areas; unmapped regions raise rather than vanish."""
    missing = sorted(set(values.index) - set(mapping))
    if missing:
        raise KeyError(f"regions without a mapping: {missing}")
    return values.groupby(values.index.map(mapping)).sum()
