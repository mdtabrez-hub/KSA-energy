"""Illustrative storage sizing: how much energy must be shifted into a stated evening window.

This is a sizing bound, not an optimisation, and it is not a statement about the real grid.
Rules: charge only from the modelled renewable output (no grid charging); discharge only
inside the window; never charge and discharge in the same hour; SoC stays within
[soc_min, 1] x energy capacity; round-trip losses are split equally between charge and discharge.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class Battery:
    power_kw: float              # per kW of renewable capacity
    energy_kwh: float            # per kW of renewable capacity
    round_trip_eff: float = 0.85
    soc_min: float = 0.10
    soc_initial: float = 0.10


def dispatch_into_window(output: pd.Series, window: np.ndarray, battery: Battery) -> pd.DataFrame:
    """Hourly greedy dispatch. Returns charge, discharge, soc (kWh at end of hour) and delivered."""
    eta = np.sqrt(battery.round_trip_eff)
    e_min = battery.soc_min * battery.energy_kwh
    soc = max(battery.soc_initial * battery.energy_kwh, e_min)
    rows = []
    for out_kw, in_window in zip(output.to_numpy(), window):
        charge = discharge = 0.0
        if in_window:
            discharge = min(battery.power_kw, (soc - e_min) * eta)
            soc -= discharge / eta
        else:
            charge = min(battery.power_kw, out_kw, (battery.energy_kwh - soc) / eta)
            soc += charge * eta
        rows.append((charge, discharge, soc, out_kw - charge + discharge))
    df = pd.DataFrame(rows, index=output.index, columns=["charge", "discharge", "soc", "delivered"])
    return df


def window_firm_fraction(output: pd.Series, window: np.ndarray, battery: Battery) -> float:
    """Mean over window hours of min(1, renewable output + discharge): fraction of nameplate held."""
    d = dispatch_into_window(output, window, battery)
    firm = (output + d["discharge"]).clip(upper=1.0)[window]
    return float(firm.mean())
