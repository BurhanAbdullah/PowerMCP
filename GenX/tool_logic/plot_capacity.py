from pathlib import Path
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from GenX.tool_logic.palette import RESOURCE_COLORS
from GenX.tool_logic.resources import classify_resource

resource_labels = {g: g for g in RESOURCE_COLORS}
resource_colors = dict(RESOURCE_COLORS)
column_titles = {"StartCap": "Start Capacity", "RetCap": "Retired Capacity", "NewCap": "New Capacity", "EndCap": "End Capacity", "NetCap": "Net Capacity Change"}

# Backward-compatible public name; classification is canonical in resources.py.
classify = classify_resource


def filter_by_zones(df: pd.DataFrame, zones: list[int]) -> pd.DataFrame:
    available_zones = sorted(int(z) for z in df["Zone"].dropna().unique())
    invalid = sorted(set(int(z) for z in zones) - set(available_zones))
    if invalid:
        raise ValueError(f"Invalid zone(s) {invalid}. Available zones: {available_zones}")
    return df[df["Zone"].isin(zones)].copy()


def load_capacity_csv(csv_path: str | Path) -> pd.DataFrame:
    csv_path = Path(csv_path)
    df = pd.read_csv(csv_path)
    required_cols = {"Resource", "StartCap", "RetCap", "NewCap", "EndCap"}
    missing = required_cols - set(df.columns)
    if missing:
        raise ValueError(f"Missing required column(s) in capacity CSV {csv_path}: {sorted(missing)}. Found: {sorted(df.columns)}")
    df["resource_group"] = df["Resource"].apply(classify_resource)
    for col in ["StartCap", "RetCap", "NewCap", "EndCap"]:
        df[col] = pd.to_numeric(df[col])
    df["NetCap"] = df["EndCap"] - df["StartCap"]
    return df


def check_existing(df: pd.DataFrame) -> dict:
    start_cap_by_resource = df.groupby("resource_group", as_index=False)["StartCap"].sum()
    total_start_cap = start_cap_by_resource["StartCap"].sum()
    is_brownfield = total_start_cap > 0
    return {"is_brownfield": bool(is_brownfield), "setting": "brownfield" if is_brownfield else "greenfield", "total_start_cap": float(total_start_cap), "start_cap_by_resource": start_cap_by_resource.to_dict(orient="records"), "message": f"Brownfield case detected: existing StartCap totals {total_start_cap:,.0f} MW." if is_brownfield else "Greenfield case detected: all StartCap values are zero."}


def aggregate_capacity_by_resource(df: pd.DataFrame) -> pd.DataFrame:
    return df.groupby("resource_group").agg({"StartCap": "sum", "RetCap": "sum", "NewCap": "sum", "EndCap": "sum", "NetCap": "sum"}).reset_index()


def plot_capacity_bar(df: pd.DataFrame, capacity_column: str, output_path: str | Path, title: str | None = None) -> dict:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plot_df = df[df[capacity_column].abs() >= 10].copy()
    resource_order = list(RESOURCE_COLORS)
    plot_df["_order"] = plot_df["resource_group"].apply(lambda rg: resource_order.index(rg) if rg in resource_order else len(resource_order))
    plot_df = plot_df.sort_values("_order").drop(columns="_order")
    _, ax = plt.subplots(figsize=(10, 6))
    bars = ax.bar(range(len(plot_df)), plot_df[capacity_column], width=1.0, color=[resource_colors.get(rg, resource_colors["Other"]) for rg in plot_df["resource_group"]])
    ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
    ax.set_xticks(range(len(plot_df))); ax.set_xticklabels([resource_labels.get(rg, rg) for rg in plot_df["resource_group"]])
    ax.set_ylabel("Capacity (MW)", fontsize=12); ax.set_title(title or column_titles.get(capacity_column, capacity_column), fontsize=14, fontweight="bold")
    for bar in bars:
        height = bar.get_height()
        ax.annotate(f"{int(round(height)):,}", (bar.get_x() + bar.get_width()/2, max(height, 0)), xytext=(0, 3), textcoords="offset points", ha="center", va="bottom", fontsize=9)
    plt.tight_layout(); plt.savefig(output_path, dpi=300, bbox_inches="tight"); plt.close()
    return {"success": True, "message": f"Plot saved successfully: {capacity_column}", "file_path": str(output_path)}
