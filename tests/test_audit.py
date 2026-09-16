from __future__ import annotations

import copy

import pandapower as pp

from powermcp.audit import audit_network


def test_clean_network_is_ok_and_json_ready():
    net = pp.create_empty_network()
    pp.create_bus(net, vn_kv=110, min_vm_pu=0.95, max_vm_pu=1.05)
    report = audit_network(net)
    assert report.status == "ok"
    assert report.counts == {"errors": 0, "warnings": 0, "info": 0}
    assert report.to_dict()["status"] == "ok"


def test_reversed_voltage_limits_are_error():
    net = pp.create_empty_network()
    pp.create_bus(net, vn_kv=110, min_vm_pu=1.10, max_vm_pu=1.00)
    report = audit_network(net)
    assert report.status == "error"
    assert any(f.code == "BUS_VOLTAGE_RANGE_REVERSED" for f in report.findings)


def test_nan_and_infinite_values_are_detected():
    net = pp.create_empty_network()
    b0 = pp.create_bus(net, vn_kv=110, min_vm_pu=float("nan"))
    b1 = pp.create_bus(net, vn_kv=110, max_vm_pu=float("inf"))
    pp.create_line_from_parameters(net, b0, b1, 1.0, 0.1, float("nan"), 0.0, 1.0)
    report = audit_network(net)
    codes = {f.code for f in report.findings}
    assert "BUS_MIN_VM_INVALID" in codes
    assert "BUS_MAX_VM_INVALID" in codes
    assert "LINE_INVALID_REACTANCE" in codes


def test_invalid_line_and_transformer_parameters_are_reported():
    net = pp.create_empty_network()
    b0 = pp.create_bus(net, vn_kv=110)
    b1 = pp.create_bus(net, vn_kv=110)
    pp.create_line_from_parameters(net, b0, b1, 0, -0.1, 0, 0, 0)
    pp.create_transformer_from_parameters(net, b0, b1, sn_mva=0, vn_hv_kv=110, vn_lv_kv=110, vk_percent=0, vkr_percent=0.1, pfe_kw=0, i0_percent=0.1)
    report = audit_network(net)
    codes = {f.code for f in report.findings}
    assert "LINE_INVALID_LENGTH" in codes
    assert "LINE_INVALID_RESISTANCE" in codes
    assert "LINE_ZERO_IMPEDANCE" in codes
    assert "LINE_INVALID_RATING" in codes
    assert "TRAFO_INVALID_RATING" in codes
    assert "TRAFO_INVALID_SHORT_CIRCUIT" in codes


def test_disconnected_in_service_bus_is_reported():
    net = pp.create_empty_network()
    b0 = pp.create_bus(net, vn_kv=110)
    b1 = pp.create_bus(net, vn_kv=110)
    pp.create_ext_grid(net, b0)
    report = audit_network(net)
    assert any(f.code == "DISCONNECTED_BUS" and f.index == b1 for f in report.findings)


def test_out_of_service_bus_is_warning():
    net = pp.create_empty_network()
    pp.create_bus(net, vn_kv=110, in_service=False)
    report = audit_network(net)
    assert report.status == "warning"
    assert report.findings[0].code == "BUS_OUT_OF_SERVICE"


def test_audit_does_not_mutate_or_run_power_flow():
    net = pp.create_empty_network()
    pp.create_bus(net, vn_kv=110)
    before = copy.deepcopy(net)
    original_converged = net.converged
    report = audit_network(net)
    assert report.status == "ok"
    assert net.converged == original_converged
    assert net.bus.equals(before.bus)
    assert net.line.equals(before.line)
    assert net.trafo.equals(before.trafo)
