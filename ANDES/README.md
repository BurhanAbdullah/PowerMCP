# ANDES MCP Server

MCP server for ANDES (Python-based power system dynamic analysis), enabling power flow and time-domain simulation.

> **Note:** This MCP server is under active development and may need further modification to handle some internal code output and ensure full compatibility with all ANDES features.

## Requirements

- Python 3.10 or higher
- [ANDES](https://andes.readthedocs.io/)

Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

Run the MCP server:
```bash
python andes_mcp.py
```

Configure in your MCP client (e.g., Cursor, Claude Desktop):
```json
{
  "mcpServers": {
    "andes": {
      "command": "python",
      "args": ["ANDES/andes_mcp.py"]
    }
  }
}
```

## Available Tools

- **run_power_flow(file_path: str)**: Run power flow analysis on a power system case file.
- **run_time_domain_simulation(step_size: float = 0.01, t_end: float = 10.0)**: Run time domain simulation on the currently loaded power system.
- **run_eigenvalue_analysis(file_path: str)**: Run eigenvalue (small-signal) analysis on a power system case. Reloads the case fresh from `file_path` and returns:
  - `n_modes`: number of eigenvalues/modes.
  - `modes`: a list, one entry per mode, each with:
    - `eigenvalue`: `[real, imag]` parts of the eigenvalue.
    - `frequency_hz`: oscillation frequency in Hz (`0.0` for non-oscillatory/real modes).
    - `damping_ratio_pct`: damping ratio as a percentage.
    - `is_oscillatory`: whether the mode has a non-zero imaginary part.

    The list is sorted **least-damped (most concerning) first**.
  - `participation_factors`: the raw participation-factor matrix from ANDES.
  - `state_names`: state variable labels, one per mode/row.
  - `success`: whether ANDES's `EIG.run()` reported success.
- **get_system_info()**: Get information about the currently loaded power system.
- **load_network_from_json(network_json: str, out_path: str)**: Stage a powerio JSON transport string as a MATPOWER file for ANDES (pass `out_path` to `run_power_flow`).
- **load_network_from_any(file_path: str, out_path: str, source_format: Optional[str] = None)**: Stage any powerio-readable case (MATPOWER `.m`, PSS/E `.raw` v33, PowerWorld `.aux`, PowerModels JSON, egret JSON) as a MATPOWER file for ANDES.

## License note

[ANDES](https://github.com/curent/andes) is GPL-3.0; it is installed only as an optional pip extra (`andes = ["andes"]` in `pyproject.toml`), never vendored into this MIT-licensed repo.

## Prompt Example

Could you run power flow on the Kundur case at `yourpath\PowerMCP\ANDES\kundur_full.json` using ANDES and summarize the results? Then call `get_system_info` to show the system details.

## Resources

- [ANDES Documentation](https://andes.readthedocs.io/)
