"""Unit tests for the OpenDSS compile outcome validation helper."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "OpenDSS"))

from opendss_tools.compile_validation import compiled_circuit_error


def test_rejects_explicit_not_ready_result():
    assert compiled_circuit_error({"ready": False}, {"buses": 13}) == (
        "OpenDSS circuit readiness reports ready=false."
    )


def test_rejects_redirect_diagnostics_when_exposed():
    result = compiled_circuit_error(
        {"redirect_errors": ["IEEELineCodes.dss not found"]},
        {"buses": 0},
    )
    assert result is not None
    assert "redirect_errors" in result


def test_rejects_empty_model_when_bus_count_is_available():
    result = compiled_circuit_error({"ready": True}, {"buses": 0})
    assert result is not None
    assert "compiled no buses" in result


def test_accepts_nonempty_model():
    assert compiled_circuit_error({"ready": True}, {"buses": 13}) is None


def test_unknown_summary_shape_does_not_fail_compatibility_check():
    assert compiled_circuit_error({"ready": True}, []) is None


def test_boolean_bus_count_is_not_treated_as_numeric_count():
    assert compiled_circuit_error({"ready": True}, {"buses": False}) is None



def test_13bus_redirect_target_exists_with_matching_case():
    case_dir = Path(__file__).resolve().parents[1] / "OpenDSS" / "13Bus"
    master = case_dir / "IEEE13Nodeckt.dss"
    redirect_targets = [
        line.split(None, 1)[1].strip().strip('"[]')
        for line in master.read_text(encoding="utf-8").splitlines()
        if line.strip().lower().startswith(("redirect ", "compile "))
    ]
    assert redirect_targets, "Expected the bundled 13Bus master case to include a redirect"
    for target in redirect_targets:
        assert (case_dir / target).is_file(), (
            f"Missing case-sensitive Redirect/Compile target: {target}"
        )
