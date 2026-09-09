"""Pure helpers for deterministic power-system security screening."""

from __future__ import annotations

from math import isfinite
from typing import Any, Mapping


def validate_limits(voltage_min_pu: float, voltage_max_pu: float, loading_limit_pct: float) -> None:
    """Validate screening limits before a backend is touched."""
    values = (voltage_min_pu, voltage_max_pu, loading_limit_pct)
    if not all(isinstance(value, (int, float)) and isfinite(float(value)) for value in values):
        raise ValueError("screening limits must be finite numbers")
    if not 0.0 < float(voltage_min_pu) < float(voltage_max_pu):
        raise ValueError("voltage limits must satisfy 0 < min < max")
    if float(loading_limit_pct) <= 0.0:
        raise ValueError("loading_limit_pct must be > 0")


def summarize_numeric_violations(
    values: Mapping[str, float],
    lower: float,
    upper: float,
) -> dict[str, Any]:
    """Return deterministic violation counts and extrema for a scalar metric."""
    bad = {name: float(value) for name, value in values.items() if value < lower or value > upper}
    ordered = sorted(bad.items(), key=lambda item: item[0])
    return {
        "violations": len(ordered),
        "worst": {"name": name, "value": value} if ordered else None,
    }


def contingency_record(
    *,
    contingency: str,
    element_type: str,
    element_index: Any,
    converged: bool,
    voltage_violations: int = 0,
    thermal_violations: int = 0,
    **metrics: Any,
) -> dict[str, Any]:
    """Build a stable, JSON-friendly contingency record."""
    return {
        "contingency": str(contingency),
        "element_type": str(element_type),
        "element_index": str(element_index),
        "converged": bool(converged),
        "voltage_violations": int(voltage_violations),
        "thermal_violations": int(thermal_violations),
        **metrics,
    }
