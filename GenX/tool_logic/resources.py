"""Canonical GenX resource classification shared by plotting tools."""

from __future__ import annotations

RESOURCE_GROUPS = (
    "Nuclear", "Coal", "Natural Gas", "Hydro", "Wind", "Solar",
    "Battery", "Biomass", "Other", "DR",
)


def classify_resource(resource: object) -> str:
    """Map a GenX resource name to one canonical technology group."""
    name = str(resource).strip().lower()
    if name == "total":
        return "Other"
    if name.endswith("_dr") or "_dr_" in name:
        return "DR"
    if "nuclear" in name:
        return "Nuclear"
    if "coal" in name:
        return "Coal"
    if ("combined_cycle" in name or name.endswith("_cc_new")
            or "combustion_turbine" in name or name.endswith("_ct_new")
            or "natural_gas" in name or "naturalgas" in name
            or "petroleum" in name or "oil" in name):
        return "Natural Gas"
    if "hydroelectric" in name or "hydro" in name:
        return "Hydro"
    if "wind" in name:
        return "Wind"
    if "distributed_generation" in name or "distributed generation" in name:
        return "Solar"
    if "pv" in name or "solar" in name or "photovoltaic" in name:
        return "Solar"
    if "batt" in name:
        return "Battery"
    if "biomass" in name:
        return "Biomass"
    return "Other"
