"""Unit tests for the PowerMCP Security Audit server."""

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
