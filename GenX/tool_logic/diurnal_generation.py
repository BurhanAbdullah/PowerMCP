#!/usr/bin/env python3
"""Compute weighted average generation by hour of day and technology."""
import argparse
import logging
import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from GenX.tool_logic.palette import RESOURCE_COLORS
from GenX.tool_logic.resources import classify_resource

logger = logging.getLogger(__name__)
STACK_ORDER = ["Nuclear", "Coal", "Natural Gas", "Hydro", "Wind", "Solar", "Battery", "Other", "DR"]
COLORS = RESOURCE_COLORS
INK = "#0b0b0b"
INK2 = "#52514e"
GRID = "#e1e0d9"

# Backward-compatible public name; all classification now comes from resources.py.
classify = classify_resource


def zone_set(spec):
    if spec == "all":
        return None
    return {int(z) for z in spec.split(",")}


def diurnal_by_tech(case_dir, period, zones="all", verbose=False):
    res_dir = os.path.join(case_dir, "results", f"results_p{period}")
    power = pd.read_csv(os.path.join(res_dir, "power.csv"), index_col=0)
    weights = pd.read_csv(os.path.join(res_dir, "time_weights.csv"))["Weight"].to_numpy()
    power = power.drop(columns=["Total"], errors="ignore")
    res_zone = power.loc["Zone"].astype(float).astype(int)
    data = power.drop(index=["Zone", "AnnualSum"]).astype(float)
    T = len(data)
    if T != len(weights):
        raise ValueError(f"{case_dir}: {T} timesteps but {len(weights)} weights")
    if T % 24:
        raise ValueError(f"{case_dir}: {T} timesteps is not a whole number of days")
    zf = zone_set(zones)
    if zf is not None:
        available = set(res_zone.unique())
        invalid = sorted(zf - available)
        if invalid:
            raise ValueError(f"Invalid zone(s) {invalid}. Available zones: {sorted(available)}")
        data = data[res_zone.isin(zf)]
    groups = {}
    for col in data.columns:
        groups.setdefault(classify_resource(col), []).append(col)
    if verbose:
        for group in STACK_ORDER:
            if group in groups:
                logger.info("  %-12s <- %d resources", group, len(groups[group]))
    hod = np.arange(T) % 24
    wsum = np.bincount(hod, weights, minlength=24)
    out = {}
    for group, cols in groups.items():
        x = data[cols].sum(axis=1).to_numpy()
        out[group] = np.bincount(hod, weights * x, minlength=24) / wsum
    return pd.DataFrame(out, index=range(24)).reindex(columns=STACK_ORDER, fill_value=0.0)


def _style_axis(ax):
    ax.set_facecolor("white")
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color("#c3c2b7")
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True); ax.tick_params(colors=INK2, labelsize=9)
    ax.set_xlim(0, 23); ax.set_xticks([0, 6, 12, 18, 23]); ax.margins(y=0)


def _stack(ax, df, unit_div):
    hours = df.index.to_numpy(); base = np.zeros(len(df))
    for group in df.columns:
        top = base + df[group].to_numpy() / unit_div
        ax.fill_between(hours, base, top, facecolor=COLORS[group], edgecolor="white", linewidth=0.7, hatch="///" if group == "DR" else None)
        base = top
    return base


def plot_comparison(orig_df, dr_df, labels, title, out_png):
    vmax = max(orig_df.sum(axis=1).max(), dr_df.sum(axis=1).max())
    unit_div, unit = (1000.0, "GW") if vmax > 10000 else (1.0, "MW")
    cols = [g for g in STACK_ORDER if g in set(orig_df.columns) | set(dr_df.columns)]
    orig_df = orig_df.reindex(columns=cols, fill_value=0.0); dr_df = dr_df.reindex(columns=cols, fill_value=0.0)
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.6), sharey=True, facecolor="white")
    for ax, df, label in zip(axes, (orig_df, dr_df), labels):
        _stack(ax, df, unit_div); _style_axis(ax); ax.set_title(label, fontsize=11, color=INK, pad=8); ax.set_xlabel("Hour of day", fontsize=9.5, color=INK2)
    axes[0].set_ylabel(f"Average generation ({unit})", fontsize=9.5, color=INK2)
    handles = [Patch(facecolor=COLORS[g], edgecolor="white", hatch="///" if g == "DR" else None, label=g) for g in reversed(cols)]
    fig.legend(handles=handles, loc="center left", bbox_to_anchor=(0.905, 0.5), frameon=False, fontsize=9, labelcolor=INK2)
    fig.suptitle(title, fontsize=12, color=INK, x=0.08, ha="left"); fig.subplots_adjust(left=0.08, right=0.89, top=0.84, bottom=0.13, wspace=0.08)
    fig.savefig(out_png, dpi=180); plt.close(fig); logger.info("wrote %s", out_png)


def plot_difference(orig_df, dr_df, labels, title, out_png):
    cols = [g for g in STACK_ORDER if g in set(orig_df.columns) | set(dr_df.columns)]
    delta = dr_df.reindex(columns=cols, fill_value=0.0) - orig_df.reindex(columns=cols, fill_value=0.0)
    vmax = delta.abs().to_numpy().max(); unit_div, unit = (1000.0, "GW") if vmax > 10000 else (1.0, "MW")
    fig, ax = plt.subplots(figsize=(8.5, 4.8), facecolor="white"); ax.axhline(0, color="#c3c2b7", linewidth=1)
    for g in cols: ax.plot(delta.index, delta[g].to_numpy() / unit_div, color=COLORS[g], linewidth=2, label=g)
    ax.plot(delta.index, delta.sum(axis=1).to_numpy() / unit_div, color=INK, linewidth=2.5, linestyle=(0, (4, 2)), label="Net total")
    _style_axis(ax); ax.spines["left"].set_visible(True); ax.spines["left"].set_color("#c3c2b7")
    ax.set_xlabel("Hour of day", fontsize=9.5, color=INK2); ax.set_ylabel(f"{labels[1]} − {labels[0]}  ({unit})", fontsize=9.5, color=INK2); ax.set_title(title, fontsize=12, color=INK, loc="left", pad=8)
    handles = [plt.Line2D([], [], color=COLORS[g], linewidth=2, label=g) for g in cols]; handles.append(plt.Line2D([], [], color=INK, linewidth=2.5, linestyle=(0, (4, 2)), label="Net total"))
    ax.legend(handles=handles, loc="center left", bbox_to_anchor=(1.01, 0.5), frameon=False, fontsize=9, labelcolor=INK2)
    fig.subplots_adjust(left=0.1, right=0.82, top=0.9, bottom=0.12); fig.savefig(out_png, dpi=180); plt.close(fig); logger.info("wrote %s", out_png)


def main():
    p = argparse.ArgumentParser(description=__doc__); p.add_argument("--orig", required=True); p.add_argument("--dr", required=True); p.add_argument("--period", type=int, default=1); p.add_argument("--zones", default="all"); p.add_argument("--out", required=True); p.add_argument("--labels", default="Original,Demand response"); p.add_argument("--diff", action="store_true"); args = p.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    orig = diurnal_by_tech(args.orig, args.period, args.zones, verbose=True); dr = diurnal_by_tech(args.dr, args.period, args.zones, verbose=True)
    title = f"Average day, {'difference' if args.diff else 'generation by technology'} — {'all zones' if args.zones == 'all' else f'zones {args.zones}'}, p{args.period}"
    labels = args.labels.split(",")
    (plot_difference if args.diff else plot_comparison)(orig, dr, labels, title, args.out)


if __name__ == "__main__":
    main()
