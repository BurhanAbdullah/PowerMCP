"""Unit tests for the OpenDSS compile outcome validation helper."""

from __future__ import annotations

from opendss_tools.compile_validation import compiled_circuit_error


def test_rejects_explicit_not_ready_result():
    assert compiled_circuit_error({"ready": False}, {"counts": {"buses": 13}}) == (
        "OpenDSS circuit readiness reports ready=false."
    )


def test_rejects_redirect_diagnostics_when_exposed():
    result = compiled_circuit_error(
        {"redirect_errors": ["IEEELineCodes.dss not found"]},
        {"counts": {"buses": 0}},
    )
    assert result is not None
    assert "redirect_errors" in result


def test_rejects_empty_model_when_bus_count_is_available():
    result = compiled_circuit_error({"ready": True}, {"counts": {"buses": 0}})
    assert result is not None
    assert "compiled no buses" in result


def test_accepts_nonempty_model():
    assert compiled_circuit_error({"ready": True}, {"counts": {"buses": 13}}) is None


def test_unknown_summary_shape_does_not_fail_compatibility_check():
    assert compiled_circuit_error({"ready": True}, []) is None


def test_boolean_bus_count_is_not_treated_as_numeric_count():
    assert compiled_circuit_error({"ready": True}, {"counts": {"buses": False}}) is None
