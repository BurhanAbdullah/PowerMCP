from __future__ import annotations

import math
import sys
import types

from PowerFactory.read_only_utils import (
    call_read_only,
    clean_json_value,
    get_read_only_application,
    read_only_error,
)


class FakeAgent:
    def __init__(self, app=None, error=None):
        self.app = app
        self.error = error
        self.calls = []

    def _get_application(self, open_digsilent=True):
        self.calls.append(open_digsilent)
        if self.error:
            raise self.error
        return self.app


def test_read_only_acquires_lazy_application_without_showing_gui():
    app = object()
    agent = FakeAgent(app=app)

    assert get_read_only_application(agent) is app
    assert agent.calls == [False]


def test_read_only_errors_are_structured():
    result = call_read_only(FakeAgent(error=RuntimeError("PowerFactory unavailable")), lambda _: 1)

    assert result == {
        "success": False,
        "error_type": "RuntimeError",
        "message": "PowerFactory unavailable",
    }


def test_read_only_success_sanitises_opaque_values():
    class Opaque:
        def __str__(self):
            return "PF object"

    result = call_read_only(
        FakeAgent(app=object()),
        lambda _: {"object": Opaque(), "nested": (1, {2, 3})},
    )

    assert result["success"] is True
    assert result["result"]["object"] == "PF object"
    assert sorted(result["result"]["nested"][1]) == [2, 3]


def test_clean_json_value_handles_non_finite_floats():
    assert clean_json_value(math.nan) is None
    assert clean_json_value(math.inf) is None
    assert clean_json_value(-math.inf) is None


def test_read_only_error_preserves_exception_type_and_message():
    result = read_only_error(ValueError("bad attribute"))

    assert result["success"] is False
    assert result["error_type"] == "ValueError"
    assert result["message"] == "bad attribute"


def test_read_only_fallback_connects_without_agent_lazy_hook(monkeypatch):
    class FakePowerFactory:
        def __init__(self):
            self.app = object()
            self.calls = 0

        def GetApplicationExt(self):
            self.calls += 1
            return self.app

    fake_pf = FakePowerFactory()
    module = types.ModuleType("fake_powerfactory_agent")
    module.pf = fake_pf
    module._ensure_powerfactory_on_path = lambda: None
    monkeypatch.setitem(sys.modules, module.__name__, module)

    class LegacyAgent:
        __module__ = module.__name__
        _shared_app = None

    assert get_read_only_application(LegacyAgent) is fake_pf.app
    assert LegacyAgent._shared_app is fake_pf.app
    assert fake_pf.calls == 1
