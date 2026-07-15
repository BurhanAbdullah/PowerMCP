# genx_agent MCP server.

'''
Loads configuration from a .env file (see .env.example) before importing
anything that reads environment variables, so personal/cluster settings are
never hardcoded.
'''

import sys
from pathlib import Path
from dotenv import load_dotenv

# Make the repo root importable so `from GenX.tool_logic...` works when the
# MCP client launches this file directly (sys.path[0] is GenX/, not the root).
_REPO_ROOT = str(Path(__file__).resolve().parent.parent)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

# Load .env sitting next to this file (no-op if it doesn't exist).
load_dotenv(Path(__file__).resolve().parent / ".env")

from typing import Optional

from mcp.server.fastmcp import FastMCP

# Analytics tools
from GenX.tool_logic.plot_capacity import (
    resource_colors,
    column_titles,
    classify_resource,
    load_capacity_csv,
    filter_by_zones,
    check_existing,
    aggregate_capacity_by_resource,
    plot_capacity_bar,
)

from GenX.tool_logic.compute_capacity_cost import compute_capacity_cost as _compute_capacity_cost
from GenX.tool_logic.plot_avg_generation import plot_diurnal_generation as _plot_diurnal_generation

# SLURM submission (imports os.environ at module load, hence after load_dotenv).
from GenX.tool_logic.slurm import preview_case as _preview_case, submit_case as _submit_case

mcp = FastMCP("genx_agent")


@mcp.tool()
def check_capacity_setting(csv_path: str) -> dict:
    """Detect whether a GenX capacity.csv is a brownfield or greenfield case."""
    df = load_capacity_csv(csv_path)
    # check_existing: whether StartCap > 0 (brownfield) or all StartCap = 0 (greenfield)
    return check_existing(df)


@mcp.tool()
def summarize_capacity(csv_path: str, zones: list[int] | None = None) -> dict:
    """
    Aggregate StartCap, RetCap, NewCap, EndCap, and NetCap by resource type.

    Args:
        csv_path: Path to the capacity.csv file
        zones: Optional list of zone numbers (e.g., [2, 5, 7, 9]) to filter to
        before aggregating. Omit to aggregate over all zones.
    """
    df = load_capacity_csv(csv_path)
    if zones:
        try:
            df = filter_by_zones(df, zones)
        except ValueError as e:
            return {"success": False, "message": str(e)}
    return aggregate_capacity_by_resource(df)


@mcp.tool()
def plot_capacity(
    csv_path: str,
    output_dir: str,
    plot_type: str,
    scenario_name: str,
    period: str,
    zones: list[int] | None = None
) -> dict:
    """
    Plot capacity data and save to PNG file.

    Before calling this tool, ask user:
    1. Whether they want to specify zones to aggregate over. If they don't
       have specific zones, tell them the default is all zones in the
       capacity.csv file.
    2. The scenario folder to plot and the period, which go in the plot title.
    """
    valid_types = ["StartCap", "RetCap", "NewCap", "EndCap", "NetCap"]

    if plot_type not in valid_types:
        return {
            "success": False,
            "message": f"Invalid plot_type '{plot_type}'. Must be one of: {valid_types}",
            "file_path": None
        }

    df = load_capacity_csv(csv_path)
    if zones:
        try:
            df = filter_by_zones(df, zones)
        except ValueError as e:
            return {
                "success": False,
                "message": str(e),
                "file_path": None
            }
    aggregated = aggregate_capacity_by_resource(df)

    setting_info = check_existing(df)
    is_brownfield = setting_info["is_brownfield"]

    if not is_brownfield:
        if plot_type in ["StartCap", "RetCap"]:
            return {
                "success": False,
                "message": f"Note that in this case where all StartCap = 0, NewCap = EndCap = NetCap.",
                "setting": "greenfield"
            }
        elif plot_type == "NetCap":
            plot_type = "EndCap"
            message_suffix = " Note that NewCap = EndCap = NetCap in this case"
        else:
            message_suffix = ""
    else:
        message_suffix = ""

    output_path = Path(output_dir) / f"{plot_type}.png"
    title = f"{column_titles[plot_type]} {scenario_name} Period {period}"

    result = plot_capacity_bar(
        df=aggregated,
        capacity_column=plot_type,
        output_path=output_path,
        title=title
    )

    if result["success"]:
        result["message"] += message_suffix
        result["setting"] = "greenfield" if not is_brownfield else "brownfield"

    return result


@mcp.tool()
def preview_genx_case(
    case_dir: str,
    time_hours: int,
    mem_gb: int,
    cpus: Optional[int] = None,
    case_name: Optional[str] = None,
) -> dict:
    """
    Generate the SLURM submission script for a GenX case.
    """
    return _preview_case(case_dir, time_hours, mem_gb, cpus, case_name)


@mcp.tool()
def submit_genx_case(
    case_dir: str,
    time_hours: int,
    mem_gb: int,
    cpus: Optional[int] = None,
    case_name: Optional[str] = None,
) -> dict:
    """
    Submit a GenX case to SLURM via sbatch.

    Resolves the case from the given directory path and submits the job. Returns
    the SLURM job ID and the resource values used. Have the user submit walltime
    and memory requirements (#  cores and memory in gb).

    If the user has not stated this, ask before calling this tool.
    """
    return _submit_case(case_dir, time_hours, mem_gb, cpus, case_name)

@mcp.tool()
def compute_capacity_cost(scenario_path: str, period: int = 1) -> dict:
    """
    Compute the PJM-wide capacity cost ($/MW-day and $/MW-yr) for a completed
    GenX scenario period, from the binding capacity reserve margin duals
    (ReserveMargin_w.csv). PJM CapRes regions 3-5 are included; the DC Island
    (CapRes_8 / z28) is excluded.

    Args:
        scenario_path: Scenario directory (absolute, or relative to GENX_DIR
            or the current working directory).
        period: Model period number (default 1).
    """
    return _compute_capacity_cost(scenario_path, period)


@mcp.tool()
def plot_diurnal_generation(
    case_dir: str,
    output_path: str,
    period: int,
    zones: str,
    labels: str,
    compare_case_dir: Optional[str] = None,
    diff: bool = False,
) -> dict:
    """
    Plot the time-weighted average-day generation profile as a stacked area
    chart: MW of generation per resource type on the y-axis, hour of day
    (0-23) on the x-axis. Saves a PNG to output_path.

    Optionally compare two scenarios: pass compare_case_dir to plot both
    side by side, and set diff=True to instead plot the difference
    (Case 1 - Case 2) as a line chart.

    Args:
        case_dir: Case directory (absolute, or relative to GENX_DIR or cwd).
        output_path: Path of the PNG file to write.
        period: Model period number.
        zones: "pjm", "island", "all", or an explicit zone list string.
        labels: Comma-separated plot label(s), e.g. "Base" or "Base, No CCS".
        compare_case_dir: Optional second case for pairwise comparison.
        diff: Plot Case 1 - Case 2 difference (requires compare_case_dir).
    """
    return _plot_diurnal_generation(
        case_dir, output_path, period, zones, labels, compare_case_dir, diff
    )

if __name__ == "__main__":
    mcp.run()