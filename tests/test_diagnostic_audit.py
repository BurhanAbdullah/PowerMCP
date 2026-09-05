import unittest

from powermcp.diagnostic_audit import audit_result, require_safe


class DiagnosticAuditTests(unittest.TestCase):
    def test_nested_diagnostics_are_normalized(self):
        result = audit_result(
            {
                "diagnostics": [
                    {"severity": "warning", "message": "value defaulted"},
                    {"severity": "error", "message": "power flow failed"},
                ]
            },
            source="pandapower",
        )
        self.assertEqual(len(result.errors), 1)
        self.assertEqual(len(result.warnings), 1)
        self.assertFalse(result.safe_to_proceed)

    def test_non_converged_is_blocking(self):
        result = audit_result({"converged": False, "message": "solver stopped"})
        self.assertFalse(result.safe_to_proceed)
        self.assertEqual(result.errors[0].code, "POWER.FLOW.NOT_CONVERGED")

    def test_explicit_safe_result_gets_audit(self):
        result = require_safe(
            {"status": "success", "converged": True, "summary": {"buses": 39}},
            source="pypsa",
        )
        self.assertTrue(result["diagnostic_audit"]["safe_to_proceed"])
        self.assertEqual(result["diagnostic_audit"]["error_count"], 0)

    def test_blocking_result_raises(self):
        with self.assertRaises(ValueError):
            require_safe({"error": "invalid action"})

    def test_boolean_unsafe_flag_is_blocking(self):
        result = audit_result({"safe_to_proceed": False})
        self.assertFalse(result.safe_to_proceed)
        self.assertEqual(result.errors[0].code, "POWER.MCP.UNSAFE_RESULT")


if __name__ == "__main__":
    unittest.main()
