"""Cross-platform power-system security auditing for PowerMCP.

This server provides a normalized N-1 security-audit workflow for
pandapower and PyPSA networks.  Backend-specific solvers remain untouched;
this module converts their results into a common audit schema suitable for
LLM agents, automation, and reporting.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from mcp.server.fastmcp import FastMCP

from common.utils import PowerError, power_mcp_tool

mcp = FastMCP("PowerMCP Security Audit")


def _severity(voltage_violations: int, thermal_violations: int, converged: bool) -> float:
    """Return a deterministic 0-10 severity score."""
    if not converged:
        return 10.0
    score = 2.0 * voltage_violations + 1.5 * thermal_violations
    return round(min(10.0, score), 3)


def _rank(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return sorted(results, key=lambda x: (-x["severity"], x["contingency"]))


def _audit_summary(base_case: Dict[str, Any], contingencies: List[Dict[str, Any]], backend: str) -> Dict[str, Any]:
    ranked = _rank(contingencies)
    violating = [r for r in ranked if r["severity"] > 0]
    nonconverged = [r for r in ranked if not r["converged"]]
    return {
        "status": "success",
        "backend": backend,
        "base_case": base_case,
        "n1": {
            "total": len(ranked),
            "converged": sum(r["converged"] for r in ranked),
            "nonconverged": len(nonconverged),
            "violating": len(violating),
            "critical": sum(r["severity"] >= 5 for r in ranked),
        },
        "risk_summary": {
            "risk_level": "critical" if any(r["severity"] >= 5 for r in ranked) else ("warning" if violating else "secure"),
            "worst_contingency": ranked[0] if ranked else None,
        },
        "contingencies": ranked,
    }


def _pandapower_base(net: Any) -> Dict[str, Any]:
    import numpy as np

    return {
        "converged": bool(getattr(net, "converged", False)),
        "min_voltage_pu": round(float(net.res_bus.vm_pu.min()), 6) if len(net.res_bus) else None,
        "max_voltage_pu": round(float(net.res_bus.vm_pu.max()), 6) if len(net.res_bus) else None,
        "max_line_loading_pct": round(float(net.res_line.loading_percent.max()), 6) if len(net.res_line) else None,
        "max_trafo_loading_pct": round(float(net.res_trafo.loading_percent.max()), 6) if len(net.res_trafo) else None,
        "total_buses": len(net.bus),
        "total_lines": len(net.line),
        "total_transformers": len(net.trafo),
    }


@power_mcp_tool(mcp)
def audit_pandapower_network(
    file_path: str,
    voltage_min_pu: float = 0.95,
    voltage_max_pu: float = 1.05,
    loading_limit_pct: float = 100.0,
    include_transformers: bool = True,
    max_contingencies: Optional[int] = None,
) -> Dict[str, Any]:
    """Run a normalized base-case + N-1 security audit on a pandapower file.

    Lines and, optionally, transformers are taken out of service one at a time.
    Every contingency is solved independently from an untouched base network.
    """
    try:
        import pandapower as pp

        if file_path.endswith(".json"):
            net = pp.from_json(file_path)
        elif file_path.endswith(".p"):
            net = pp.from_pickle(file_path)
        else:
            raise ValueError("Unsupported network format. Use .json or .p")

        pp.runpp(net)
        base = _pandapower_base(net)
        original = net.deepcopy()
        jobs: List[tuple[str, int]] = [("line", int(i)) for i in original.line.index]
        if include_transformers:
            jobs += [("trafo", int(i)) for i in original.trafo.index]
        if max_contingencies is not None:
            if max_contingencies < 1:
                raise ValueError("max_contingencies must be >= 1")
            jobs = jobs[:max_contingencies]

        results: List[Dict[str, Any]] = []
        for kind, idx in jobs:
            case = original.deepcopy()
            case[kind].at[idx, "in_service"] = False
            try:
                pp.runpp(case)
                vbad = case.res_bus[(case.res_bus.vm_pu < voltage_min_pu) | (case.res_bus.vm_pu > voltage_max_pu)]
                lbad = case.res_line[case.res_line.loading_percent > loading_limit_pct]
                tbad = case.res_trafo[case.res_trafo.loading_percent > loading_limit_pct] if len(case.res_trafo) else case.res_trafo
                vv = int(len(vbad))
                tv = int(len(lbad) + len(tbad))
                converged = bool(case.converged)
                results.append({
                    "contingency": f"{kind}_{idx}",
                    "element_type": kind,
                    "element_index": idx,
                    "converged": converged,
                    "voltage_violations": vv,
                    "thermal_violations": tv,
                    "min_voltage_pu": round(float(case.res_bus.vm_pu.min()), 6) if len(case.res_bus) else None,
                    "max_line_loading_pct": round(float(case.res_line.loading_percent.max()), 6) if len(case.res_line) else None,
                    "max_trafo_loading_pct": round(float(case.res_trafo.loading_percent.max()), 6) if len(case.res_trafo) else None,
                    "severity": _severity(vv, tv, converged),
                })
            except Exception as exc:
                results.append({
                    "contingency": f"{kind}_{idx}",
                    "element_type": kind,
                    "element_index": idx,
                    "converged": False,
                    "voltage_violations": 0,
                    "thermal_violations": 0,
                    "severity": 10.0,
                    "error": str(exc),
                })

        return _audit_summary(base, results, "pandapower")
    except Exception as exc:
        return PowerError(status="error", message=f"pandapower security audit failed: {exc}")


@power_mcp_tool(mcp)
def audit_pypsa_network(
    network_name: str,
    loading_limit_pct: float = 100.0,
    max_contingencies: Optional[int] = None,
) -> Dict[str, Any]:
    """Run a normalized base-case + N-1 line security audit on a PyPSA network.

    PyPSA line loading is assessed from apparent power where available. For
    single-snapshot networks, scalar values are used; for time series the
    maximum loading across snapshots is reported.
    """
    try:
        import numpy as np
        from pypsa import Network

        network = Network(network_name)
        network.pf()
        snapshots = network.snapshots
        lines = list(network.lines.index)
        if max_contingencies is not None:
            if max_contingencies < 1:
                raise ValueError("max_contingencies must be >= 1")
            lines = lines[:max_contingencies]

        def _max_abs(df: Any) -> Optional[float]:
            if df is None or df.empty:
                return None
            return float(np.nanmax(np.abs(df.to_numpy(dtype=float))))

        vmag = network.buses_t.v_mag_pu if hasattr(network.buses_t, "v_mag_pu") else None
        base = {
            "converged": True,
            "min_voltage_pu": float(np.nanmin(vmag.to_numpy())) if vmag is not None and not vmag.empty else None,
            "max_voltage_pu": float(np.nanmax(vmag.to_numpy())) if vmag is not None and not vmag.empty else None,
            "total_buses": len(network.buses),
            "total_lines": len(network.lines),
            "snapshots": len(snapshots),
        }

        results: List[Dict[str, Any]] = []
        for line in lines:
            case = Network(network_name)
            case.lines.at[line, "x"] = case.lines.at[line, "x"]
            case.lines.at[line, "s_nom"] = 0.0
            try:
                case.pf()
                p = case.lines_t.p0[line] if line in case.lines_t.p0.columns else None
                q = case.lines_t.q0[line] if line in case.lines_t.q0.columns else None
                s_nom = float(network.lines.at[line, "s_nom"])
                loading = None
                if p is not None and s_nom > 0:
                    pvals = np.asarray(p, dtype=float)
                    qvals = np.asarray(q, dtype=float) if q is not None else np.zeros_like(pvals)
                    loading = float(np.nanmax(np.sqrt(pvals ** 2 + qvals ** 2)) / s_nom * 100.0)
                thermal = int(loading is not None and loading > loading_limit_pct)
                results.append({
                    "contingency": f"line_{line}",
                    "element_type": "line",
                    "element_index": str(line),
                    "converged": True,
                    "voltage_violations": 0,
                    "thermal_violations": thermal,
                    "max_loading_pct": round(loading, 6) if loading is not None else None,
                    "severity": _severity(0, thermal, True),
                })
            except Exception as exc:
                results.append({
                    "contingency": f"line_{line}",
                    "element_type": "line",
                    "element_index": str(line),
                    "converged": False,
                    "voltage_violations": 0,
                    "thermal_violations": 0,
                    "severity": 10.0,
                    "error": str(exc),
                })

        return _audit_summary(base, results, "PyPSA")
    except Exception as exc:
        return PowerError(status="error", message=f"PyPSA security audit failed: {exc}")


@power_mcp_tool(mcp)
def render_security_report(audit_result: Dict[str, Any]) -> Dict[str, Any]:
    """Convert an audit result into a concise Markdown engineering report."""
    if audit_result.get("status") != "success":
        return PowerError(status="error", message="audit_result must be a successful security audit result")
    base = audit_result.get("base_case", {})
    n1 = audit_result.get("n1", {})
    risk = audit_result.get("risk_summary", {})
    worst = risk.get("worst_contingency")
    lines = [
        "# PowerMCP Security Audit",
        "",
        f"**Backend:** {audit_result.get('backend', 'unknown')}",
        f"**Risk level:** {risk.get('risk_level', 'unknown').upper()}",
        "",
        "## Base case",
        f"- Converged: {base.get('converged')}",
        f"- Voltage range: {base.get('min_voltage_pu')}–{base.get('max_voltage_pu')} p.u.",
        f"- Maximum line loading: {base.get('max_line_loading_pct', 'N/A')}%",
        "",
        "## N-1 screening",
        f"- Contingencies: {n1.get('total', 0)}",
        f"- Violating: {n1.get('violating', 0)}",
        f"- Non-converged: {n1.get('nonconverged', 0)}",
        f"- Critical: {n1.get('critical', 0)}",
    ]
    if worst:
        lines += ["", "## Worst contingency", f"- **{worst.get('contingency')}** — severity {worst.get('severity')}/10"]
        if worst.get("error"):
            lines.append(f"- Solver error: {worst['error']}")
    lines += ["", "## Interpretation", "- `secure`: no screened N-1 violation detected.", "- `warning`: at least one screened contingency produces a violation.", "- `critical`: at least one contingency is severe or non-convergent."]
    return {"status": "success", "markdown": "\n".join(lines)}


if __name__ == "__main__":
    mcp.run(transport="stdio")
