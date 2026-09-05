"""Cross-server safety and reproducibility diagnostics.

The audit is deliberately backend-agnostic.  It consumes the structured result
returned by a PowerMCP tool and classifies operational findings before an agent
uses the result for a follow-on action.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping


@dataclass(frozen=True)
class DiagnosticFinding:
    """One normalized finding extracted from a server result."""

    code: str
    severity: str
    message: str
    source: str = "unknown"
    details: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class DiagnosticAudit:
    """Immutable audit summary suitable for MCP tool responses."""

    findings: tuple[DiagnosticFinding, ...]

    @property
    def errors(self) -> tuple[DiagnosticFinding, ...]:
        return tuple(f for f in self.findings if f.severity.lower() == "error")

    @property
    def warnings(self) -> tuple[DiagnosticFinding, ...]:
        return tuple(f for f in self.findings if f.severity.lower() == "warning")

    @property
    def safe_to_proceed(self) -> bool:
        return not self.errors

    def as_dict(self) -> dict[str, Any]:
        return {
            "safe_to_proceed": self.safe_to_proceed,
            "error_count": len(self.errors),
            "warning_count": len(self.warnings),
            "findings": [
                {
                    "code": f.code,
                    "severity": f.severity,
                    "message": f.message,
                    "source": f.source,
                    "details": dict(f.details),
                }
                for f in self.findings
            ],
        }


_ERROR_TOKENS = ("error", "failed", "failure", "invalid", "not converged", "non-converged")
_WARNING_TOKENS = ("warning", "defaulted", "skipped", "approx", "degraded")


def _classify_severity(value: Any, message: str) -> str:
    if value is not None:
        text = str(value).lower()
        if text in {"error", "critical", "fatal"}:
            return "error"
        if text in {"warning", "warn"}:
            return "warning"
        if text in {"info", "remark", "notice"}:
            return "info"
    lowered = message.lower()
    if any(token in lowered for token in _ERROR_TOKENS):
        return "error"
    if any(token in lowered for token in _WARNING_TOKENS):
        return "warning"
    return "info"


def _iter_findings(payload: Any, source: str = "tool") -> Iterable[DiagnosticFinding]:
    if isinstance(payload, Mapping):
        diagnostics = payload.get("diagnostics")
        if isinstance(diagnostics, list):
            for item in diagnostics:
                yield from _iter_findings(item, source)

        status = payload.get("status")
        if isinstance(status, str) and status.lower() not in {"ok", "success", "completed"}:
            message = str(payload.get("message") or status)
            yield DiagnosticFinding(
                code="POWER.MCP.STATUS",
                severity=_classify_severity(status, message),
                message=message,
                source=source,
            )

        for key in ("error", "errors", "warning", "warnings"):
            value = payload.get(key)
            if value is None:
                continue
            values = value if isinstance(value, list) else [value]
            for item in values:
                message = item if isinstance(item, str) else str(item)
                severity = "error" if key.startswith("error") else "warning"
                yield DiagnosticFinding(
                    code=f"POWER.MCP.{key.upper()}",
                    severity=severity,
                    message=message,
                    source=source,
                )

        if payload.get("converged") is False:
            yield DiagnosticFinding(
                code="POWER.FLOW.NOT_CONVERGED",
                severity="error",
                message="Power-flow result reports non-convergence.",
                source=source,
            )

        if payload.get("safe_to_proceed") is False:
            yield DiagnosticFinding(
                code="POWER.MCP.UNSAFE_RESULT",
                severity="error",
                message="Upstream tool explicitly marked its result unsafe to use.",
                source=source,
            )

    elif isinstance(payload, list):
        for item in payload:
            yield from _iter_findings(item, source)


def audit_result(payload: Any, *, source: str = "tool") -> DiagnosticAudit:
    """Normalize structured tool output into a fail-closed audit."""
    findings = tuple(_iter_findings(payload, source))
    return DiagnosticAudit(findings=findings)


def require_safe(payload: Any, *, source: str = "tool") -> dict[str, Any]:
    """Return the original payload plus an audit, refusing unsafe results.

    Raises ``ValueError`` when an upstream tool reports a blocking condition.
    """
    audit = audit_result(payload, source=source)
    if not audit.safe_to_proceed:
        raise ValueError(
            "PowerMCP diagnostic audit blocked follow-on use: "
            + "; ".join(f.message for f in audit.errors)
        )
    result = dict(payload) if isinstance(payload, Mapping) else {"result": payload}
    result["diagnostic_audit"] = audit.as_dict()
    return result
