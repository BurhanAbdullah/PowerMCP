"""Deterministic, solver-independent network validation for pandapower networks."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from math import isfinite
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
        return {"status": self.status, "counts": dict(self.counts), "findings": [asdict(f) for f in self.findings]}


def _finite(value: Any) -> bool:
    try:
        return isfinite(float(value))
    except (TypeError, ValueError):
        return False


def audit_network(net: Any) -> AuditReport:
    """Audit structural network data without solving or mutating ``net``."""
    findings: list[AuditFinding] = []

    def add(severity: str, code: str, message: str, element: str | None = None, index: int | None = None) -> None:
        findings.append(AuditFinding(severity, code, message, element, index))

    buses = getattr(net, "bus", None)
    if buses is not None:
        for idx, row in buses.sort_index().iterrows():
            if not bool(row.get("in_service", True)):
                add("warning", "BUS_OUT_OF_SERVICE", "Bus is out of service.", "bus", int(idx))
            min_vm, max_vm = row.get("min_vm_pu"), row.get("max_vm_pu")
            if min_vm is not None and not _finite(min_vm):
                add("error", "BUS_MIN_VM_INVALID", "min_vm_pu must be finite.", "bus", int(idx))
            elif min_vm is not None and float(min_vm) < 0:
                add("error", "BUS_MIN_VM_INVALID", "min_vm_pu must be non-negative.", "bus", int(idx))
            if max_vm is not None and not _finite(max_vm):
                add("error", "BUS_MAX_VM_INVALID", "max_vm_pu must be finite.", "bus", int(idx))
            elif max_vm is not None and float(max_vm) <= 0:
                add("error", "BUS_MAX_VM_INVALID", "max_vm_pu must be positive.", "bus", int(idx))
            if min_vm is not None and max_vm is not None and _finite(min_vm) and _finite(max_vm) and float(min_vm) > float(max_vm):
                add("error", "BUS_VOLTAGE_RANGE_REVERSED", "min_vm_pu is greater than max_vm_pu.", "bus", int(idx))

    lines = getattr(net, "line", None)
    if lines is not None:
        for idx, row in lines.sort_index().iterrows():
            length, resistance, reactance, rating = (row.get(c) for c in ("length_km", "r_ohm_per_km", "x_ohm_per_km", "max_i_ka"))
            if length is not None and (not _finite(length) or float(length) <= 0):
                add("error", "LINE_INVALID_LENGTH", "Line length must be finite and positive.", "line", int(idx))
            if resistance is not None and (not _finite(resistance) or float(resistance) < 0):
                add("error", "LINE_INVALID_RESISTANCE", "Line resistance must be finite and non-negative.", "line", int(idx))
            if reactance is not None and not _finite(reactance):
                add("error", "LINE_INVALID_REACTANCE", "Line reactance must be finite.", "line", int(idx))
            if resistance is not None and reactance is not None and _finite(resistance) and _finite(reactance) and float(resistance) == 0 and float(reactance) == 0:
                add("error", "LINE_ZERO_IMPEDANCE", "Line has zero series impedance.", "line", int(idx))
            if rating is not None and (not _finite(rating) or float(rating) <= 0):
                add("warning", "LINE_INVALID_RATING", "Line current rating must be finite and positive.", "line", int(idx))

    trafos = getattr(net, "trafo", None)
    if trafos is not None:
        for idx, row in trafos.sort_index().iterrows():
            sn, vk = row.get("sn_mva"), row.get("vk_percent")
            if sn is not None and (not _finite(sn) or float(sn) <= 0):
                add("warning", "TRAFO_INVALID_RATING", "Transformer apparent-power rating must be finite and positive.", "trafo", int(idx))
            if vk is not None and (not _finite(vk) or float(vk) <= 0):
                add("error", "TRAFO_INVALID_SHORT_CIRCUIT", "Transformer vk_percent must be finite and positive.", "trafo", int(idx))

    try:
        import networkx as nx
        import pandapower.topology as top
        out = net.bus.index[~net.bus.in_service] if "in_service" in net.bus else None
        graph = top.create_nxgraph(net, nogobuses=out)
        connected = set().union(*(set(c) for c in nx.connected_components(graph))) if graph.number_of_nodes() else set()
        active = set(net.bus.index[net.bus.in_service]) if "in_service" in net.bus else set(net.bus.index)
        for idx in sorted(active - connected):
            add("error", "DISCONNECTED_BUS", "In-service bus is disconnected from the network graph.", "bus", int(idx))
    except ImportError:
        add("info", "CONNECTIVITY_CHECK_UNAVAILABLE", "Connectivity check unavailable because topology dependencies are not installed.")

    findings.sort(key=lambda f: (f.element or "", -1 if f.index is None else f.index, f.code, f.severity, f.message))
    errors = sum(f.severity == "error" for f in findings)
    warnings = sum(f.severity == "warning" for f in findings)
    infos = sum(f.severity == "info" for f in findings)
    return AuditReport("error" if errors else "warning" if warnings else "ok", {"errors": errors, "warnings": warnings, "info": infos}, findings)
