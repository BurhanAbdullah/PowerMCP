"""Tests for the structured PSS/E analysis tools using a fake engine."""

from __future__ import annotations

from PSSE import psse_mcp


class FakePsspy:
    def nsol(self):
        return 0

    def abuscount(self, flag):
        assert flag == 2
        return 0, 3

    def abrncount(self, flag):
        assert flag == 4
        return 0, 2

    def amachcount(self, flag):
        assert flag == 4
        return 0, 1

    def abusint(self, *, sid, flag, string):
        assert (sid, flag, string) == (-1, 2, ["NUMBER"])
        return 0, [[1, 2, 3]]

    def abusreal(self, *, sid, flag, string):
        assert (sid, flag, string) == (-1, 2, ["PU"])
        return 0, [[0.94, 1.00, 1.06]]

    def abrnint(self, *, sid, owner, ties, flag, entry, string):
        assert (sid, owner, ties, flag, entry) == (-1, 1, 3, 3, 1)
        if string == ["FROMNUMBER"]:
            return 0, [[1, 2]]
        if string == ["TONUMBER"]:
            return 0, [[2, 3]]
        raise AssertionError(string)

    def abrnchar(self, *, sid, owner, ties, flag, entry, string):
        assert (sid, owner, ties, flag, entry) == (-1, 1, 3, 3, 1)
        assert string == ["ID"]
        return 0, [["1", "2"]]

    def abrnreal(self, *, sid, owner, ties, flag, entry, string):
        assert (sid, owner, ties, flag, entry) == (-1, 1, 3, 3, 1)
        assert string == ["MAXPCTRATE"]
        return 0, [[80.0, 125.0]]


def _use_fake(monkeypatch, fake=None):
    fake = fake or FakePsspy()
    monkeypatch.setattr(psse_mcp, "psspy", fake)
    monkeypatch.setattr(psse_mcp, "_psse_ready", True)
    return fake


def test_inspect_case_returns_counts(monkeypatch):
    _use_fake(monkeypatch)

    result = psse_mcp.inspect_case()

    assert result == {
        "status": "success",
        "case_info": {
            "num_buses": 3,
            "num_branches": 2,
            "num_generators": 1,
        },
    }


def test_run_power_flow_returns_structured_violations(monkeypatch):
    _use_fake(monkeypatch)

    result = psse_mcp.run_power_flow(top_n=5)

    assert result["status"] == "success"
    assert result["solve"] == {"status": "success", "ierr": 0}
    assert result["buses"]["min_voltage_pu"] == 0.94
    assert result["buses"]["min_voltage_bus"] == 1
    assert result["buses"]["max_voltage_pu"] == 1.06
    assert result["buses"]["max_voltage_bus"] == 3
    assert result["buses"]["low_voltage_count"] == 1
    assert result["buses"]["high_voltage_count"] == 1
    assert result["branches"]["max_loading_pct"] == 125.0
    assert result["branches"]["overloaded_count"] == 1
    assert result["branches"]["overloaded"][0] == {
        "from_bus": 2,
        "to_bus": 3,
        "id": "2",
        "loading_pct": 125.0,
    }


def test_run_power_flow_rejects_invalid_top_n(monkeypatch):
    _use_fake(monkeypatch)

    result = psse_mcp.run_power_flow(top_n=-1)

    assert result["status"] == "error"
    assert "top_n" in result["message"]


def test_run_power_flow_stops_after_solve_failure(monkeypatch):
    class FailingSolve(FakePsspy):
        def nsol(self):
            return 5

    _use_fake(monkeypatch, FailingSolve())

    result = psse_mcp.run_power_flow()

    assert result["status"] == "error"
    assert result["stage"] == "solve"
    assert result["solve"]["ierr"] == 5
