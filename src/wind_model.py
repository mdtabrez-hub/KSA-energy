"""Generic per-kW wind output. Modelled, with a generic power curve: never measured turbine output.

Turbine models for Saudi projects are not verified, so this uses a normalised generic curve
(cut-in, rated and cut-out speeds as parameters) and power-law extrapolation from the
weather-data height to hub height. Report results for at least two parameter sets.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class GenericTurbine:
    hub_height_m: float = 120.0
    cut_in_ms: float = 3.0
    rated_ms: float = 12.0
    cut_out_ms: float = 25.0
    losses: float = 0.12         # wake, availability, electrical
    shear_alpha: float = 0.14    # power-law exponent; site-specific in reality


def extrapolate_speed(speed: pd.Series, from_height_m: float, to_height_m: float, alpha: float) -> pd.Series:
    return speed * (to_height_m / from_height_m) ** alpha


def per_kw_output(speed_ref: pd.Series, ref_height_m: float = 10.0,
                  turbine: GenericTurbine = GenericTurbine()) -> pd.Series:
    """Normalised output 0..1: cubic between cut-in and rated, 1 to cut-out, 0 beyond."""
    v = extrapolate_speed(speed_ref.clip(lower=0), ref_height_m, turbine.hub_height_m, turbine.shear_alpha)
    ramp = (v**3 - turbine.cut_in_ms**3) / (turbine.rated_ms**3 - turbine.cut_in_ms**3)
    p = np.where(v < turbine.cut_in_ms, 0.0,
                 np.where(v < turbine.rated_ms, ramp,
                          np.where(v <= turbine.cut_out_ms, 1.0, 0.0)))
    return pd.Series(p * (1 - turbine.losses), index=speed_ref.index, name="per_kw_wind")
