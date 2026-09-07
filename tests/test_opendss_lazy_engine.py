"""Regression tests for the OpenDSS backend initialization boundary."""

import importlib
import sys
import types
from pathlib import Path


OPEN_DSS_ROOT = Path(__file__).parents[1] / "OpenDSS"


def _import_engine(monkeypatch, interface_module, toolkit_module):
    monkeypatch.setitem(sys.modules, "py_dss_interface", interface_module)
    monkeypatch.setitem(sys.modules, "py_dss_toolkit", toolkit_module)
    monkeypatch.syspath_prepend(str(OPEN_DSS_ROOT))
    sys.modules.pop("core.engine", None)
    return importlib.import_module("core.engine")


def test_engine_import_does_not_construct_dss(monkeypatch):
    """Importing core.engine must not instantiate py-dss-interface DSS."""
    class ExplodingDSS:
        def __init__(self):
            raise RuntimeError("DSS backend should not initialize during import")

    interface = types.ModuleType("py_dss_interface")
    interface.DSS = ExplodingDSS
    toolkit = types.ModuleType("py_dss_toolkit")
    toolkit.dss_tools = types.SimpleNamespace(update_dss=lambda _: None)

    engine = _import_engine(monkeypatch, interface, toolkit)

    assert engine._dss is None
    assert hasattr(engine, "get_dss")


def test_lazy_dss_initializes_once(monkeypatch):
    """The compatibility proxy constructs and wires DSS only on first use."""
    calls = []

    class FakeDSS:
        def __init__(self):
            calls.append("construct")

        def text(self, command):
            return command

    interface = types.ModuleType("py_dss_interface")
    interface.DSS = FakeDSS
    toolkit = types.ModuleType("py_dss_toolkit")
    toolkit.dss_tools = types.SimpleNamespace(
        update_dss=lambda _: calls.append("wire")
    )

    engine = _import_engine(monkeypatch, interface, toolkit)

    assert calls == []
    assert engine.dss.text("ClearAll") == "ClearAll"
    assert calls == ["construct", "wire"]
    assert engine.dss.text("Solve") == "Solve"
    assert calls == ["construct", "wire"]
