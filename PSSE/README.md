# PSSE MCP Server

MCP server for PSS/E (Siemens PTI) power system analysis. Supports PSSE 35+ with Python 3.

## Requirements

- Python 3.10 or higher
- PSSE 35+ installed with Python API (PSSPY)
- [mcp](https://pypi.org/project/mcp/)

Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

Run the MCP server:
```bash
python psse_mcp.py
```

Configure in your MCP client (e.g., Cursor, Claude Desktop):
```json
{
  "mcpServers": {
    "psse": {
      "command": "python",
      "args": ["PSSE/psse_mcp.py"]
    }
  }
}
```

## Available Tools

- **open_case(case: str)**: Open a PSSE case file.
- **solve_case()**: Solve power flow using PSSE Newton-Raphson method.
- **inspect_case()**: Inspect the loaded case and return bus, branch, and generator counts.
- **run_power_flow(voltage_min, voltage_max, loading_limit, top_n)**: Solve the case and return structured voltage-violation and branch-overload summaries using PSS/E post-solve queries.
- **run_psspy_command(function_name, arguments)**: Execute an allowed psspy API command by name using the JSON reference spec. Commands that load or execute external code are excluded.
- **lookup_psspy_command(function_name)**: Look up the API reference for a psspy function without executing it.
- **search_psspy_commands(query, category)**: Search the psspy API index for functions matching a query.

## Prompt Example

- use psse run power flow of "yourpath\PowerMCP\PSSE\savnw.sav"

## Resources

- [PSS/E Documentation](https://www.siemens-energy.com/)

### Licensing boundary

PSS/E is proprietary software. The MCP server is an adapter around the user's separately installed and licensed PSS/E/PSSPY environment; no PSS/E executable, runtime, license, or proprietary vendor files are distributed by this repository.
