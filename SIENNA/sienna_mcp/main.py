"""PowerMCP SIENNA MCP server."""

from __future__ import annotations

import logging
import os
import sys
from mcp.server.mcpserver import MCPServer as FastMCP

script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(script_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from sienna_mcp.tools.load_tools import register_load_tools
from sienna_mcp.tools.r2x_tools import register_r2x_tools
from sienna_mcp.tools.solve_tools import register_solve_tools

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("sienna-mcp")


def create_server() -> FastMCP:
    mcp = FastMCP("SIENNA")
    register_load_tools(mcp)
    register_r2x_tools(mcp)
    register_solve_tools(mcp)
    return mcp


def main() -> None:
    create_server().run()


if __name__ == "__main__":
    main()
