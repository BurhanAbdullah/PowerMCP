"""Lazily initialized py-dss-interface engine and toolkit wiring.

Importing the OpenDSS MCP server must not construct a DSS engine.  In
particular, py-dss-interface can fail on platforms where the native OpenDSS
runtime is unavailable (for example macOS arm64).  The MCP server should still
be able to start and expose its tools; backend initialization is deferred until
a tool actually needs DSS.
"""

from __future__ import annotations

from typing import Any

_dss: Any | None = None
_dss_tools: Any | None = None


def get_dss() -> Any:
    """Return the shared DSS instance, creating it on first use."""
    global _dss, _dss_tools
    if _dss is None:
        from py_dss_interface import DSS
        from py_dss_toolkit import dss_tools

        _dss = DSS()
        dss_tools.update_dss(_dss)
        _dss_tools = dss_tools
    return _dss


def get_dss_tools() -> Any:
    """Return the toolkit module after ensuring the DSS backend is initialized."""
    get_dss()
    return _dss_tools


class _LazyDSS:
    """Compatibility proxy preserving the historical ``dss.foo`` API."""

    def __getattr__(self, name: str) -> Any:
        return getattr(get_dss(), name)

    def __dir__(self) -> list[str]:
        if _dss is None:
            return []
        return dir(_dss)


# Existing tool modules import ``dss`` directly. Keep that API while making
# attribute access, rather than module import, the initialization boundary.
dss = _LazyDSS()
