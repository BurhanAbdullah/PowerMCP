"""Configuration-domain MCP tools (compile, clear)."""

from pathlib import Path
from typing import Any, Dict

from mcp.server.mcpserver import MCPServer as FastMCP
from py_dss_toolkit import dss_tools

from core import state
import core.engine as engine
from opendss_tools.compile_validation import compiled_circuit_error
from powermcp.sandbox import (
    PathNotAllowed,
    allowed_roots,
    checked_path,
    checked_read_tree,
)
from utils.responses import _err, _ok


def _compiled_readiness_and_error() -> tuple[Any, str | None]:
    """Read readiness plus optional model summary and validate stable metadata."""
    readiness = dss_tools.configuration.circuit_readiness()
    try:
        summary = dss_tools.model._summary_model_records
        if callable(summary):
            summary = summary()
    except (AttributeError, TypeError, ValueError):
        # Summary records differ between toolkit versions. Readiness remains
        # authoritative where model metadata is not exposed.
        summary = None
    return readiness, compiled_circuit_error(readiness, summary)


def _reset_compile_state() -> None:
    state.circuit_loaded = False
    state.solution_available = False
    state.last_compiled_dss_file = None


def compile_opendss_file(dss_file: str, force_recompile: bool = False) -> Dict[str, Any]:
    """Compile a master DSS file and validate exposed readiness metadata.

    A successful Python call to the engine wrapper is not enough to prove the
    model is usable: Redirect/Compile failures can leave a partial circuit.
    When the toolkit exposes explicit readiness errors or a zero bus count,
    return an error and leave this session marked as unloaded.
    """
    try:
        dss_file = checked_path(dss_file, purpose="dss_file")
        # A DSS model may Redirect/Compile sibling files. Preflight the whole
        # project tree when containment is enabled.
        if allowed_roots():
            checked_read_tree(str(Path(dss_file).parent), purpose="DSS input tree")
    except PathNotAllowed as exc:
        return _err(str(exc))

    resolved = str(Path(dss_file).resolve())
    if (
        state.circuit_loaded
        and state.last_compiled_dss_file is not None
        and resolved == state.last_compiled_dss_file
        and not force_recompile
    ):
        try:
            readiness, validation_error = _compiled_readiness_and_error()
            if validation_error:
                _reset_compile_state()
                return _err(validation_error)
            return _ok(
                {
                    "dss_file": dss_file,
                    "resolved_dss_file": resolved,
                    "skipped": True,
                    "already_compiled": True,
                    "circuit_readiness": readiness,
                    "circuit_loaded": True,
                    "solution_available": state.solution_available,
                }
            )
        except Exception as exc:
            _reset_compile_state()
            return _err(f"Unable to verify the previously compiled circuit: {exc}")

    try:
        dss_tools.configuration.compile_dss(dss_file)
        readiness, validation_error = _compiled_readiness_and_error()
        if validation_error:
            _reset_compile_state()
            return _err(validation_error)
        state.circuit_loaded = True
        state.solution_available = False
        state.last_compiled_dss_file = resolved
        return _ok(
            {
                "dss_file": dss_file,
                "resolved_dss_file": resolved,
                "skipped": False,
                "circuit_readiness": readiness,
                "circuit_loaded": True,
                "solution_available": False,
            }
        )
    except Exception as exc:
        _reset_compile_state()
        return _err(str(exc))


def clear_all_opendss_memory() -> Dict[str, Any]:
    """Clear OpenDSS engine memory and reset circuit state."""
    try:
        engine.ensure_engine().text("ClearAll")
        _reset_compile_state()
        return _ok(
            {"cleared": True, "circuit_loaded": False, "solution_available": False}
        )
    except Exception as exc:
        return _err(str(exc))


def register_configuration_tools(mcp: FastMCP) -> None:
    mcp.tool()(compile_opendss_file)
    mcp.tool()(clear_all_opendss_memory)
