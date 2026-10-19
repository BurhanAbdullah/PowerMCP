"""OpenDSS compile result verification.

The compilation command returning without a Python exception does not guarantee
that every Redirect/Compile statement succeeded. This helper inspects only the
stable, structured readiness/summary information exposed by the toolkit; it
does not attempt to parse vendor-specific diagnostic text.
"""

from __future__ import annotations

from typing import Any


def compiled_circuit_error(readiness: Any, summary: Any) -> str | None:
    """Return a diagnostic when exposed circuit metadata proves compile failed."""
    if isinstance(readiness, dict):
        for key in ("success", "ready", "is_ready", "circuit_ready"):
            if readiness.get(key) is False:
                return f"OpenDSS circuit readiness reports {key}=false."
        for key in ("error", "errors", "compile_error", "redirect_errors"):
            value = readiness.get(key)
            if value:
                return f"OpenDSS circuit readiness reports {key}: {value}"

    bus_count = _bus_count(summary)
    if bus_count is not None and bus_count <= 0:
        return (
            "OpenDSS compiled no buses; check Redirect/Compile paths "
            "and engine diagnostics."
        )
    return None


def _bus_count(summary: Any) -> int | float | None:
    """Extract bus count only from known dictionary-shaped summary metadata."""
    if not isinstance(summary, dict):
        return None
    counts = summary.get("counts", summary)
    if not isinstance(counts, dict):
        return None
    value = counts.get("buses", counts.get("bus_count"))
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return value
