"""Small, dependency-light helpers for PowerFactory read-only MCP tools.

These helpers keep connection acquisition and result sanitisation deterministic so
read-only handlers can be exercised without a live PowerFactory installation.
"""

from __future__ import annotations

import math
from typing import Any, Callable


def get_read_only_application(agent: Any) -> Any:
    """Acquire a PowerFactory application for a read-only operation.

    Read-only tools must not depend on a previously populated ``_shared_app``.
    The agent's normal lazy connection path is the single source of truth.
    """

    return agent._get_application(open_digsilent=False)


def read_only_error(exc: Exception) -> dict[str, Any]:
    """Return the common structured error envelope used by read-only tools."""

    return {
        "success": False,
        "error_type": type(exc).__name__,
        "message": str(exc),
    }


def clean_json_value(value: Any) -> Any:
    """Convert PowerFactory/numpy-ish values into JSON-safe primitives.

    PowerFactory can expose opaque object-list values through ``GetAttribute``.
    Unknown objects are represented by ``str(value)`` rather than escaping the
    MCP handler and failing during final JSON serialisation.
    """

    try:
        import numpy as np
    except ImportError:  # pragma: no cover - numpy is optional here
        np = None

    if np is not None:
        if isinstance(value, np.ndarray):
            return [clean_json_value(item) for item in value.tolist()]
        if isinstance(value, np.integer):
            return int(value)
        if isinstance(value, np.floating):
            number = float(value)
            return None if not math.isfinite(number) else number
        if isinstance(value, np.bool_):
            return bool(value)

    if isinstance(value, dict):
        return {str(key): clean_json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [clean_json_value(item) for item in value]
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if value is None or isinstance(value, (str, int, bool)):
        return value

    return str(value)


def call_read_only(agent: Any, operation: Callable[[Any], Any]) -> dict[str, Any]:
    """Acquire PowerFactory lazily, execute a read-only operation, and envelope errors."""

    try:
        app = get_read_only_application(agent)
        return {"success": True, "result": clean_json_value(operation(app))}
    except Exception as exc:
        return read_only_error(exc)
