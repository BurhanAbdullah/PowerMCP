"""Regression tests for OpenDSS backend initialization boundaries."""

import importlib
import sys
import types


def test_engine_import_does_not_construct_dss(monkeypatch):
    """Importing core.engine must not instantiate py-dss-interface DSS."""
    class ExplodingDSS:
        def __init__(self):
            raise RuntimeError("DSS backend should not initialize during import")

    fake_interface = types.ModuleType("py_dss_interface")
    fake_interface.DSS = ExplodingDSS
    monkeypatch.setitem(sys.modules, "py_dss_interface", fake_interface)

    fake_toolkit = types.ModuleType("py_dss_toolkit")
    fake_toolkit.dss_tools = types.SimpleNamespace(update_dss=lambda _: None)
    monkeypatch.setitem(sys.modules, "py_dss_toolkit", fake_toolkit)

    sys.modules.pop("core.engine", None)
    engine = importlib.import_module("core.engine")

    assert engine._dss is None
    assert hasattr(engine, "get_dss")


def test_lazy_dss_initializes_once(monkeypatch):
    """The compatibility proxy should construct and wire DSS only on use."""
    calls = []

    class FakeDSS:
        def __init__(self):
            calls.append("construct")
        def text(self, command):
            return command

    fake_interface = types.ModuleType("py_dss_interface")
    fake_interface.DSS = FakeDSS
    monkeypatch.setitem(sys.modules, "py_dss_interface", fake_interface)

    fake_toolkit = types.ModuleType("py_dss_toolkit")
    fake_toolkit.dss_tools = types.SimpleNamespace(
        update_dss=lambda _: calls.append("wire")
    )
    monkeypatch.setitem(sys.modules, "py_dss_toolkit", fake_toolkit)

    sys.modules.pop("core.engine", None)
    engine = importlib.import_module("core.engine")

    assert calls == []
    assert engine.dss.text("ClearAll") == "ClearAll"
    assert calls == ["construct", "wire"]
    assert engine.dss.text("Solve") == "Solve"
    assert calls == ["construct", "wire"]
