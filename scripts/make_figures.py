"""Figures for RQ1-RQ3 from results/tables and data/processed.

    python -m scripts.make_figures      # writes results/figures/*.png

Region colours follow the entity in every figure (validated categorical palette, light mode):
Central blue, Eastern orange, Southern aqua, Western yellow.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
P, T, F = ROOT / "data/processed", ROOT / "results/tables", ROOT / "results/figures"
AREAS = ["Central", "Eastern", "Southern", "Western"]
COLOR = {"Central": "#2a78d6", "Eastern": "#eb6834", "Southern": "#1baf7a", "Western": "#eda100"}
INK, INK2, GRID, SURF = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"

plt.rcParams.update({
    "figure.facecolor": SURF, "axes.facecolor": SURF, "axes.edgecolor": GRID, "axes.labelcolor": INK2,
    "xtick.color": INK2, "ytick.color": INK2, "text.color": INK, "font.size": 9,
    "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "grid.color": GRID,
    "grid.linewidth": 0.6, "axes.axisbelow": True, "savefig.dpi": 200, "savefig.bbox": "tight",
})


def fig1_monthly_load() -> None:
    load = pd.read_csv(P / "monthly_load.csv", parse_dates=["date"])
    dups = pd.read_csv(T / "d2_duplicate_years.csv")
    fig, axes = plt.subplots(2, 2, figsize=(9, 5.2), sharex=True, sharey=True)
    for ax, area in zip(axes.flat, AREAS):
        g = load[load.region == area]
        for y in sorted(set(dups[dups.region == area][["year_a", "year_b"]].to_numpy().ravel())):
            ax.axvspan(pd.Timestamp(f"{y}-01-01"), pd.Timestamp(f"{y}-12-31"), color=GRID, lw=0)
        ax.fill_between(g.date, g["min"], g["max"], color=COLOR[area], alpha=0.18, lw=0)
        ax.plot(g.date, g["max"], color=COLOR[area], lw=2)
        ax.set_title(f"{area}", loc="left", fontsize=10, color=INK)
    for ax in axes[:, 0]:
        ax.set_ylabel("Load (GW)")
    fig.suptitle("Monthly maximum load by operating area, 2009–2019 (band: monthly min–max)",
                 x=0.01, ha="left", fontsize=11)
    fig.text(0.01, -0.02, "Grey years: values duplicated in the source (2010 = 2009 all areas; 2018 = 2017 Eastern, Southern). "
             "Source: KAPSARC 'Saudi Arabia Electricity Load Monthly by Region' (ECRA), corrected per d2_corrections_log.csv.",
             fontsize=7, color=INK2, wrap=True)
    fig.savefig(F / "fig1_monthly_load_by_area.png")
    plt.close(fig)


def fig2_alignment() -> None:
    s = pd.read_csv(T / "rq2_alignment_scenarios.csv")
    refs = pd.read_csv(T / "rq2_reference_shares.csv", index_col=0)
    sets = [("GEM", "installed", "Installed (GEM, 12 GW)"),
            ("GEM", "installed+construction", "Installed + under construction (22 GW)"),
            ("GEM", "all_pipeline", "Full pipeline (GEM, 54 GW)")]
    fig, axes = plt.subplots(1, 3, figsize=(10, 3.4), sharey=True)
    for ax, (src, st, title) in zip(axes, sets):
        d = s[(s.source == src) & (s.status_set == st)]
        for i, a in enumerate(AREAS):
            lo, hi = d[f"share_{a}"].min(), d[f"share_{a}"].max()
            ax.plot([lo, hi], [i, i], color=COLOR[a], lw=6, solid_capstyle="round", alpha=0.85)
            ax.plot(refs.loc[a, "peak_2019"], i, marker="|", ms=16, mew=2.5, color=INK)
            ax.text(max(hi, refs.loc[a, "peak_2019"]) + 0.02, i, f"{lo:.0%}–{hi:.0%}", va="center", fontsize=7.5, color=INK2)
        ax.set_title(title, loc="left", fontsize=9)
        ax.set_xlim(0, 0.85)
        ax.xaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0))
        ax.set_xlabel("Share of RE capacity")
    axes[0].set_yticks(range(4), AREAS)
    axes[0].invert_yaxis()
    fig.suptitle("Regional share of renewable capacity (bar: range over 36 region mappings) vs share of 2019 peak (black tick)",
                 x=0.01, y=1.06, ha="left", fontsize=10.5)
    fig.savefig(F / "fig2_capacity_vs_peak_shares.png")
    plt.close(fig)


def fig3_window_heatmap() -> None:
    d = pd.read_csv(T / "rq3_window_cf_by_mounting.csv")
    wins = ["12-15", "14-17", "16-19", "19-22", "all_hours"]
    fig, axes = plt.subplots(1, 2, figsize=(9, 2.8), sharey=True)
    for ax, var in zip(axes, ["tracker", "fixed"]):
        m = (d[(d.status_set == "all_pipeline") & (d.variant == var)]
             .pivot(index="area", columns="window", values="median").reindex(AREAS)[wins])
        lo = (d[(d.status_set == "all_pipeline") & (d.variant == var)]
              .pivot(index="area", columns="window", values="min").reindex(AREAS)[wins])
        hi = (d[(d.status_set == "all_pipeline") & (d.variant == var)]
              .pivot(index="area", columns="window", values="max").reindex(AREAS)[wins])
        ax.imshow(m.to_numpy(), cmap="Blues", vmin=0, vmax=1, aspect="auto")
        for i in range(m.shape[0]):
            for j in range(m.shape[1]):
                v = m.iat[i, j]
                ax.text(j, i, f"{v:.2f}\n({lo.iat[i, j]:.2f}–{hi.iat[i, j]:.2f})", ha="center", va="center",
                        fontsize=7, color="white" if v > 0.55 else INK)
        ax.set_xticks(range(len(wins)), [w.replace("all_hours", "all hours") for w in wins])
        ax.set_title(f"PV, {'single-axis tracker' if var == 'tracker' else 'fixed tilt'}", loc="left", fontsize=9)
        ax.grid(False)
    axes[0].set_yticks(range(4), AREAS)
    fig.suptitle("Modelled PV capacity factor in each area's observed peak months, by assumed peak window "
                 "(median; range over 5 weather years × 36 mappings)", x=0.01, y=1.06, ha="left", fontsize=10)
    fig.text(0.01, -0.06, "Full GEM pipeline, 102 projects; NASA POWER 2019–2023 hourly; pvlib PVWatts. Modelled, not measured. "
             "Windows are local clock hours (UTC+3) and are scenarios, not observed peak hours.", fontsize=7, color=INK2)
    fig.savefig(F / "fig3_pv_window_cf_heatmap.png")
    plt.close(fig)


def fig4_pv_vs_wind() -> None:
    d = pd.read_csv(T / "rq3_window_cf_scenarios.csv.gz")
    d = d[(d.status_set == "all_pipeline") & (d.window != "all_hours")]
    wins = ["12-15", "14-17", "16-19", "19-22"]
    groups = {"PV tracker": d[d.variant == "tracker"], "PV fixed": d[d.variant == "fixed"],
              "Wind (shear 0.10–0.20)": d[d.tech == "wind"]}
    colors = {"PV tracker": "#2a78d6", "PV fixed": "#86b6ef", "Wind (shear 0.10–0.20)": "#eb6834"}
    fig, ax = plt.subplots(figsize=(6.5, 3.2))
    x = np.arange(len(wins))
    for k, (name, g) in enumerate(groups.items()):
        q = g.groupby("window")["cf"].agg(["min", "median", "max"]).reindex(wins)
        xs = x + (k - 1) * 0.25
        ax.bar(xs, q["median"], width=0.22, color=colors[name], label=name)
        ax.vlines(xs, q["min"], q["max"], color=INK2, lw=1)
    ax.set_xticks(x, [f"{w} h" for w in wins])
    ax.set_ylabel("Capacity factor in peak months")
    ax.set_ylim(0, 1)
    ax.legend(frameon=False, fontsize=8, loc="upper right")
    ax.set_title("PV vs wind by assumed peak window (all areas; bar = median, line = range)", loc="left", fontsize=10)
    fig.text(0.01, -0.04, "Wind: 11 GW pipeline, 0.4 GW operating; generic power curve on NASA POWER 50 m wind. Modelled.",
             fontsize=7, color=INK2)
    fig.savefig(F / "fig4_pv_vs_wind_windows.png")
    plt.close(fig)


if __name__ == "__main__":
    F.mkdir(parents=True, exist_ok=True)
    fig1_monthly_load()
    fig2_alignment()
    fig3_window_heatmap()
    fig4_pv_vs_wind()
    print(sorted(p.name for p in F.glob("*.png")))
