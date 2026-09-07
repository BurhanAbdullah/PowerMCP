"""Tools for loading and validating Sienna PowerSystems JSON."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any


def _julia_executable(config: dict[str, Any]) -> str:
    return str(config.get("julia_bin") or os.environ.get("JULIA_BIN") or "julia")


def _depot_env(config: dict[str, Any]) -> dict[str, str]:
    env = os.environ.copy()
    depot = config.get("julia_depot_path") or os.environ.get("JULIA_DEPOT_PATH")
    if depot:
        env["JULIA_DEPOT_PATH"] = str(depot)
    return env


def load_system(json_path: str, *, julia_bin: str | None = None, julia_depot_path: str | None = None) -> dict[str, Any]:
    """Validate and load a Sienna PSY JSON file with PowerSystems.jl.

    The Python side first validates that the input is JSON and then delegates the
    actual deserialization to PowerSystems.jl, avoiding a second Python model of
    Sienna's schema.
    """
    path = Path(json_path).expanduser().resolve()
    if not path.is_file():
        return {"ok": False, "error": f"system file not found: {path}"}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {"ok": False, "error": f"invalid JSON: {exc}"}
    if not isinstance(data, dict):
        return {"ok": False, "error": "Sienna PSY JSON root must be an object"}

    config = {"julia_bin": julia_bin, "julia_depot_path": julia_depot_path}
    julia = _julia_executable(config)
    script = (
        "using PowerSystems; "
        "sys = System(ARGS[1]); "
        "println(length(get_components(Any, sys)))"
    )
    try:
        proc = subprocess.run(
            [julia, "--startup-file=no", "-e", script, str(path)],
            env=_depot_env(config), text=True, capture_output=True, check=False,
        )
    except OSError as exc:
        return {"ok": False, "error": f"unable to start Julia: {exc}"}
    if proc.returncode != 0:
        return {"ok": False, "error": proc.stderr.strip() or "PowerSystems.jl failed to load system"}
    return {"ok": True, "path": str(path), "component_count": int(proc.stdout.strip().splitlines()[-1]) if proc.stdout.strip().splitlines()[-1].isdigit() else None}


def register_load_tools(mcp: Any) -> None:
    mcp.tool()(load_system)
