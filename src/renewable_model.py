"""Modelled per-kW PV output at a site. Outputs are model estimates, never measured plant output.

Two irradiance sources are supported:
  * clear-sky (pvlib Ineichen with bundled Linke turbidity): an upper envelope with no cloud,
    dust storms or soiling, used only for timing and geometry analysis;
  * user-supplied weather (GHI/DNI/DHI and air temperature, e.g. NASA POWER or ERA5) for the
    main analysis once those data can be downloaded.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
import pvlib

TZ = "Asia/Riyadh"  # UTC+3 all year: Saudi Arabia does not observe daylight saving


@dataclass(frozen=True)
class PVSystem:
    tracking: bool = True           # single-axis N-S tracker; False = fixed, equator-facing
    tilt_deg: float | None = None   # fixed systems only; defaults to site latitude
    gamma_pdc: float = -0.0035      # power temperature coefficient (1/K), PVWatts default range
    system_loss: float = 0.14       # PVWatts lumped losses (soiling, wiring, mismatch, availability)
    dc_ac_ratio: float = 1.25
    inverter_eff: float = 0.96


def clearsky_weather(lat: float, lon: float, times: pd.DatetimeIndex,
                     air_temp_c: float | pd.Series = 35.0) -> pd.DataFrame:
    """Clear-sky irradiance plus an assumed air temperature (a scenario input, not an observation)."""
    loc = pvlib.location.Location(lat, lon, tz=TZ)
    cs = loc.get_clearsky(times, model="ineichen")
    cs["temp_air"] = air_temp_c
    return cs


def per_kw_ac_output(lat: float, lon: float, weather: pd.DataFrame,
                     system: PVSystem = PVSystem(), wind_speed: float = 2.0) -> pd.Series:
    """AC output per kW of AC rating (0..1) for one site and a weather frame.

    `weather` must have columns ghi, dni, dhi, temp_air on a tz-aware index.
    """
    loc = pvlib.location.Location(lat, lon, tz=TZ)
    sp = loc.get_solarposition(weather.index)
    if system.tracking:
        trk = pvlib.tracking.singleaxis(sp["apparent_zenith"], sp["azimuth"],
                                        axis_tilt=0, axis_azimuth=180, max_angle=60, backtrack=True,
                                        gcr=0.35)
        surface_tilt = trk["surface_tilt"].fillna(0)
        surface_azimuth = trk["surface_azimuth"].fillna(180)
    else:
        surface_tilt = system.tilt_deg if system.tilt_deg is not None else abs(lat)
        surface_azimuth = 180
    poa = pvlib.irradiance.get_total_irradiance(
        surface_tilt, surface_azimuth, sp["apparent_zenith"], sp["azimuth"],
        weather["dni"], weather["ghi"], weather["dhi"], model="isotropic")
    poa_global = poa["poa_global"].clip(lower=0).fillna(0)
    cell_t = pvlib.temperature.pvsyst_cell(poa_global, weather["temp_air"], wind_speed)
    pdc0 = system.dc_ac_ratio  # DC nameplate per kW AC
    pdc = pvlib.pvsystem.pvwatts_dc(poa_global, cell_t, pdc0, system.gamma_pdc)
    pdc = pdc * (1 - system.system_loss)
    pac = pvlib.inverter.pvwatts(pdc, pdc0=1.0 / system.inverter_eff, eta_inv_nom=system.inverter_eff)
    return pac.clip(lower=0, upper=1.0).fillna(0).rename("per_kw_ac")


def solar_noon_local(lat: float, lon: float, date: str) -> pd.Timestamp:
    """Local clock time (UTC+3) of solar transit on a given date."""
    day = pd.DatetimeIndex([pd.Timestamp(date, tz=TZ)])
    transit = pvlib.solarposition.sun_rise_set_transit_spa(day, lat, lon)["transit"].iloc[0]
    return transit.tz_convert(TZ)
