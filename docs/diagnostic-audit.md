# Cross-server diagnostic audit

PowerMCP connects language-model agents to multiple power-system backends. A backend result should not automatically become an input to the next tool: convergence failures, malformed responses, or explicit safety flags need to remain visible at the orchestration boundary.

`powermcp.diagnostic_audit` provides a backend-neutral, read-only normalization layer for that boundary.

## Design goals

- **Fail closed for blocking conditions.** A reported error, non-converged result, or explicit `safe_to_proceed=false` is blocking.
- **Preserve backend detail.** Existing payloads are not rewritten; an additive `diagnostic_audit` object summarizes the findings.
- **Provider independent.** No LLM SDK or solver dependency is required.
- **Deterministic.** The audit performs no I/O and does not modify global state.
- **Composable.** It can be used after a tool call and before an agent is allowed to trigger a dependent operation.

## Example

```python
from powermcp.diagnostic_audit import require_safe

result = backend_tool(...)
checked = require_safe(result, source="pandapower")
# Only continue with dependent actions when this returns successfully.
```

This complements, rather than replaces, backend-specific diagnostics. The goal is a common orchestration contract across PowerWorld, PyPSA, pandapower, ANDES, PowerIO, and the other bundled servers.

The module intentionally does not execute a follow-on tool itself. A future orchestration layer can use `diagnostic_audit.safe_to_proceed` as a policy gate without coupling that policy to any particular solver.
