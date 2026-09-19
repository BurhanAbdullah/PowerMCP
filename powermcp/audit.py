"""Deterministic, solver-independent network audit helpers.

The audit layer is intentionally separate from the MCP server wrappers. It turns
common pre-solve checks into a stable JSON-serializable report that an agent can
inspect before invoking a solver.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import math
from typing import Any


@dataclass(frozen=True)
class AuditFinding:
    severity: str
    code: str
    message: str
    element: str | None = None
    index: int | None = None


@dataclass(frozen=True)
class AuditReport:
    status: str
    counts: dict[str, int]
    findings: list[AuditFinding]

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "counts": dict(self.counts),
            "findings": [asdict(f) for f in self.findings],
        }


def audit_network(net: Any) -> AuditReport:
    """Audit a pandapower network without running a power flow.

    Checks are conservative and structural: bus voltage limits, inactive buses,
    invalid line geometry/electrical parameters and ratings, transformer ratings,
    and disconnected in-service buses. The function does not mutate the network.
    """
    findings: list[AuditFinding] = []

    def add(
        severity: str,
        code: str,
        message: str,
        element: str | None = None,
        index: int | None = None,
    ) -> None:
        findings.append(AuditFinding(severity, code, message, element, index))

    def finite(value: Any) -> bool:
        try:
            return math.isfinite(float(value))
        except (TypeError, ValueError):
            return False

    buses = getattr(net, "bus", None)
    if buses is not None:
        for idx, row in buses.iterrows():
            if not bool(row.get("in_service", True)):
                add("warning", "BUS_OUT_OF_SERVICE", "Bus is out of service.", "bus", int(idx))
            for col, lo, hi, code in (
                ("min_vm_pu", 0.0, 1.1, "BUS_MIN_VM_INVALID"),
                ("max_vm_pu", 0.9, 2.0, "BUS_MAX_VM_INVALID"),
            ):
                if col in row and row[col] is not None and finite(row[col]):
                    value = float(row[col])
                    if not (lo <= value <= hi):
                        add("error", code, f"{col}={value} is outside a valid range.", "bus", int(idx))
            if "min_vm_pu" in row and "max_vm_pu" in row:
                minimum = row["min_vm_pu"]
                maximum = row["max_vm_pu"]
                if finite(minimum) and finite(maximum) and float(minimum) > float(maximum):
                    add(
                        "error",
                        "BUS_VOLTAGE_RANGE_REVERSED",
                        "min_vm_pu is greater than max_vm_pu.",
                        "bus",
                        int(idx),
                    )

    lines = getattr(net, "line", None)
    if lines is not None:
        for idx, row in lines.iterrows():
            length = row.get("length_km")
            r = row.get("r_ohm_per_km")
            x = row.get("x_ohm_per_km")
            if length is not None and (not finite(length) or float(length) <= 0):
                add("error", "LINE_NONPOSITIVE_LENGTH", "Line length must be positive.", "line", int(idx))
            if r is not None and (not finite(r) or float(r) < 0):
                add("error", "LINE_NEGATIVE_RESISTANCE", "Line resistance cannot be negative.", "line", int(idx))
            if (
                x is not None
                and r is not None
                and finite(x)
                and finite(r)
                and float(x) == 0
                and float(r) == 0
            ):
                add("error", "LINE_ZERO_IMPEDANCE", "Line has zero series impedance.", "line", int(idx))
            if "max_i_ka" in row and (not finite(row["max_i_ka"]) or float(row["max_i_ka"]) <= 0):
                add("warning", "LINE_MISSING_RATING", "Line current rating is not positive.", "line", int(idx))

    trafos = getattr(net, "trafo", None)
    if trafos is not None:
        for idx, row in trafos.iterrows():
            if "sn_mva" in row and (not finite(row["sn_mva"]) or float(row["sn_mva"]) <= 0):
                add("warning", "TRAFO_MISSING_RATING", "Transformer apparent-power rating is not positive.", "trafo", int(idx))
            if "vk_percent" in row and (not finite(row["vk_percent"]) or float(row["vk_percent"]) <= 0):
                add("error", "TRAFO_INVALID_SHORT_CIRCUIT", "Transformer vk_percent must be positive.", "trafo", int(idx))

    try:
        import networkx as nx
        import pandapower.topology as top

        out_of_service = (
            net.bus.index[~net.bus.in_service]
            if "in_service" in net.bus
            else None
        )
        graph = top.create_nxgraph(net, nogobuses=out_of_service)
        connected = (
            set().union(*(set(component) for component in nx.connected_components(graph)))
            if graph.number_of_nodes()
            else set()
        )
        in_service_buses = (
            set(net.bus.index[net.bus.in_service])
            if "in_service" in net.bus
            else set(net.bus.index)
        )
        for idx in sorted(in_service_buses - connected):
            add(
                "error",
                "DISCONNECTED_BUS",
                "In-service bus is disconnected from the network graph.",
                "bus",
                int(idx),
            )
    except Exception:
        # Topology availability is optional here; structural checks above remain
        # deterministic even when the optional graph backend is unavailable.
        pass

    errors = sum(f.severity == "error" for f in findings)
    warnings = sum(f.severity == "warning" for f in findings)
    infos = sum(f.severity == "info" for f in findings)
    status = "error" if errors else "warning" if warnings else "ok"
    return AuditReport(
        status=status,
        counts={"errors": errors, "warnings": warnings, "info": infos},
        findings=findings,
    )
