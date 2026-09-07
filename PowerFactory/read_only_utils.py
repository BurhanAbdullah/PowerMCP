"""Small, dependency-light helpers for PowerFactory read-only MCP tools.

These helpers keep connection acquisition and result sanitisation deterministic so
read-only handlers can be exercised without a live PowerFactory installation.
"""

from __future__ import annotations

import importlib
import math
from typing import Any, Callable


def get_read_only_application(agent: Any) -> Any:
    """Acquire a PowerFactory application without requiring a prior connection.

    Prefer the agent's explicit lazy-connection hook when available.  The
    compatibility fallback is intentionally read-only: it obtains the vendor
    application handle but does not activate a project or show the GUI.
    """

    get_application = getattr(agent, "_get_application", None)
    if callable(get_application):
        return get_application(open_digsilent=False)

    shared_app = getattr(agent, "_shared_app", None)
    if shared_app is not None:
        return shared_app

    module = importlib.import_module(agent.__module__)
    ensure_path = getattr(module, "_ensure_powerfactory_on_path", None)
    if callable(ensure_path):
        ensure_path()

    pf = getattr(module, "pf", None)
    if pf is None:
        pf = importlib.import_module("powerfactory")
        setattr(module, "pf", pf)

    app = pf.GetApplicationExt()
    if app is None:
        raise RuntimeError("GetApplicationExt() returned None")

    # Keep the process-level handle aligned with the normal agent connection
    # path so subsequent read/write operations can reuse the same application.
    try:
        setattr(agent, "_shared_app", app)
    except Exception:
        pass
    return app


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
