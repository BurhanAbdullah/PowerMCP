"""PowerMCP SIENNA MCP server."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

_repo_root = str(Path(__file__).resolve().parents[2])
_repo_root_added = _repo_root not in sys.path
if _repo_root_added:
    sys.path.insert(0, _repo_root)
try:
    from powermcp.sandbox import PathNotAllowed, checked_path
finally:
    if _repo_root_added:
        sys.path.remove(_repo_root)
del _repo_root, _repo_root_added

from mcp.server.fastmcp import FastMCP

from .tools.load_tools import register_load_tools
from .tools.r2x_tools import register_r2x_tools
from .tools.solve_tools import register_solve_tools

mcp = FastMCP("powermcp-sienna")
register_load_tools(mcp)
register_r2x_tools(mcp)
register_solve_tools(mcp)

__all__ = ["mcp"]


if __name__ == "__main__":
    mcp.run(transport="stdio")
