# PowerMCP Security Audit

The Security Audit server adds a backend-neutral **base-case + N-1 security screening** workflow for PowerMCP.

## Features

- Pandapower JSON/pickle network auditing
- PyPSA NetCDF network auditing
- Independent N-1 cases from an untouched base model
- Voltage and thermal violation detection
- Non-convergence treated as critical
- Deterministic 0–10 contingency severity ranking
- Normalized machine-readable results for LLM agents
- Markdown engineering report generation

## Run

```bash
python SecurityAudit/security_audit_mcp.py
```

## Example agent workflow

1. Call `audit_pandapower_network` or `audit_pypsa_network`.
2. Inspect `risk_summary` and the ranked `contingencies` list.
3. Pass the returned object to `render_security_report` for a concise Markdown report.

The server is intentionally a screening layer. Detailed solver-specific studies remain available through the existing PowerWorld, pandapower, PyPSA, PSSE, PSLF, ANDES, and OpenDSS integrations.
