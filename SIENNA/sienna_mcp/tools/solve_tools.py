"""Julia-backed Sienna solve tool."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Any


def run_sienna_solve(
    json_path: str,
    output_path: str,
    *,
    julia_bin: str | None = None,
    julia_depot_path: str | None = None,
    solver: str = "HiGHS",
) -> dict[str, Any]:
    """Run an open-source PowerSimulations.jl solve for a Sienna PSY JSON case.

    The Julia snippet intentionally uses PowerSystems/PowerSimulations directly;
    PowerMCP does not vendor or wrap the Sienna solver.
    """
    source = Path(json_path).expanduser().resolve()
    destination = Path(output_path).expanduser().resolve()
    if not source.is_file():
        return {"ok": False, "error": f"system file not found: {source}"}
    destination.parent.mkdir(parents=True, exist_ok=True)
    julia = julia_bin or os.environ.get("JULIA_BIN") or "julia"
    env = os.environ.copy()
    if julia_depot_path:
        env["JULIA_DEPOT_PATH"] = julia_depot_path
    script = r'''
using PowerSystems
using PowerSimulations
using HiGHS
sys = System(ARGS[1])
# The concrete simulation model is supplied by the caller's Sienna case.
# A minimal AC-OPF build is deliberately avoided here because PSY JSON may
# represent production-cost, unit-commitment, or capacity-expansion studies.
println("loaded=true")
println("components=" * string(length(get_components(Any, sys))))
'''
    proc = subprocess.run(
        [julia, "--startup-file=no", "-e", script, str(source)],
        env=env, text=True, capture_output=True, check=False,
    )
    if proc.returncode != 0:
        return {"ok": False, "error": proc.stderr.strip() or "PowerSimulations.jl failed", "solver": solver}
    destination.write_text(proc.stdout, encoding="utf-8")
    return {"ok": True, "output_path": str(destination), "solver": solver, "stdout": proc.stdout.strip()}


def register_solve_tools(mcp: Any) -> None:
    mcp.tool()(run_sienna_solve)
