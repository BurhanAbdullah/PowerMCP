"""Lazy py_dss_interface DSS instance and dss_tools wiring."""

from __future__ import annotations

from py_dss_interface import DSS
from py_dss_toolkit import dss_tools

_dss = None


def get_dss():
    """Return the shared DSS instance, creating it on first use.

    Keeping construction out of module import lets the MCP server initialize
    and expose its tools even when the OpenDSS native backend is unavailable.
    """
    global _dss
    if _dss is None:
        try:
            _dss = DSS()
            dss_tools.update_dss(_dss)
        except Exception as exc:
            _dss = None
            raise RuntimeError(
                f"OpenDSS backend initialization failed: {exc}"
            ) from exc
    return _dss
