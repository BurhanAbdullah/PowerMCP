"""Unit tests for the PowerMCP Security Audit server."""

import pytest

from SecurityAudit.audit_utils import contingency_record, validate_limits
from SecurityAudit.security_audit_mcp import _audit_summary, _rank, _severity, render_security_report


def test_severity_nonconverged_is_critical():
    assert _severity(0, 0, False) == 10.0


def test_severity_counts_voltage_and_thermal_violations():
    assert _severity(1, 2, True) == 5.0


def test_rank_orders_worst_first_and_is_deterministic():
    results = [
        {"contingency": "line_b", "severity": 1.5, "converged": True},
        {"contingency": "line_a", "severity": 5.0, "converged": True},
        {"contingency": "line_c", "severity": 5.0, "converged": True},
    ]
    ranked = _rank(results)
    assert [r["contingency"] for r in ranked] == ["line_a", "line_c", "line_b"]


def test_summary_classifies_critical_and_nonconverged():
    result = _audit_summary(
        {"converged": True, "min_voltage_pu": 0.99},
        [
            {"contingency": "line_1", "severity": 0, "converged": True},
            {"contingency": "line_2", "severity": 10, "converged": False},
        ],
        "test-backend",
    )
    assert result["status"] == "success"
    assert result["n1"]["total"] == 2
    assert result["n1"]["nonconverged"] == 1
    assert result["n1"]["critical"] == 1
    assert result["risk_summary"]["risk_level"] == "critical"


def test_report_contains_engineering_summary():
    audit = _audit_summary(
        {"converged": True, "min_voltage_pu": 0.98, "max_voltage_pu": 1.03},
        [{"contingency": "line_7", "severity": 1.5, "converged": True}],
        "test-backend",
    )
    report = render_security_report(audit)
    assert report["status"] == "success"
    assert "PowerMCP Security Audit" in report["markdown"]
    assert "line_7" in report["markdown"]


def test_validate_limits_rejects_non_finite_values():
    with pytest.raises(ValueError, match="finite"):
        validate_limits(float("nan"), 1.05, 100.0)


def test_validate_limits_rejects_invalid_ranges():
    with pytest.raises(ValueError, match="0 < min < max"):
        validate_limits(1.05, 0.95, 100.0)
    with pytest.raises(ValueError, match="loading_limit_pct must be > 0"):
        validate_limits(0.95, 1.05, 0.0)


def test_contingency_record_normalizes_identity_and_defaults():
    record = contingency_record(
        contingency=123,
        element_type="line",
        element_index=7,
        converged=False,
        voltage_violations=2,
        thermal_violations=3,
        error="solver failed",
    )
    assert record == {
        "contingency": "123",
        "element_type": "line",
        "element_index": "7",
        "converged": False,
        "voltage_violations": 2,
        "thermal_violations": 3,
        "error": "solver failed",
    }


def test_contingency_record_is_json_friendly_for_index_types():
    record = contingency_record(
        contingency="line_1",
        element_type="line",
        element_index="L1",
        converged=True,
    )
    assert record["element_index"] == "L1"
    assert isinstance(record["converged"], bool)


def test_audit_summary_does_not_mutate_input_order():
    original = [
        {"contingency": "b", "severity": 1.0, "converged": True},
        {"contingency": "a", "severity": 2.0, "converged": True},
    ]
    snapshot = [dict(item) for item in original]
    _audit_summary({"converged": True}, original, "test")
    assert original == snapshot
