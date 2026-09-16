# Deterministic network audit

`powermcp.audit.audit_network` performs solver-independent structural checks on pandapower-compatible networks and returns deterministic, JSON-serializable findings.

The audit intentionally does not execute a power flow or mutate the supplied network. It is suitable as a pre-solver validation step in MCP and agent workflows.

## Checks

- bus service state and voltage-limit integrity
- finite/non-negative line electrical parameters
- zero-impedance lines
- positive line current ratings
- transformer rating and short-circuit parameter integrity
- disconnected in-service buses

Finding order is deterministic so callers can compare reports across runs.
