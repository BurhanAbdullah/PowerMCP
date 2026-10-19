"""OpenDSS compile result verification.

OpenDSS can leave a partial circuit when a Redirect/Compile command fails.
This helper inspects stable structured metadata exposed by py-dss-toolkit;
it deliberately avoids parsing free-form vendor diagnostics.
"""

from __future__ import annotations

from typing import Any


def compiled_circuit_error(readiness: Any, summary: Any) -> str | None:
    """Return an error when structured readiness or model counts prove failure."""
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
    """Extract bus count from py-dss-toolkit's summary-record mapping."""
    if not isinstance(summary, dict):
        return None
    value = summary.get("buses", summary.get("bus_count"))
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return value
