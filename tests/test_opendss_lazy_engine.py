"""Regression tests for lazy OpenDSS backend initialization."""

from __future__ import annotations

import importlib
import sys
import types
from pathlib import Path

import pytest


OPENDSS_DIR = Path(__file__).resolve().parents[1] / "OpenDSS"


def _load_engine(monkeypatch, dss_cls):
    """Load core.engine against controlled py_dss dependencies."""
    calls = {"update": []}
    toolkit = types.ModuleType("py_dss_toolkit")
    toolkit.dss_tools = types.SimpleNamespace(
        update_dss=lambda value: calls["update"].append(value)
    )
    interface = types.ModuleType("py_dss_interface")
    interface.DSS = dss_cls

    monkeypatch.setitem(sys.modules, "py_dss_toolkit", toolkit)
    monkeypatch.setitem(sys.modules, "py_dss_interface", interface)
    monkeypatch.syspath_prepend(str(OPENDSS_DIR))

    for name in ("core.engine",):
        sys.modules.pop(name, None)
    module = importlib.import_module("core.engine")
    return module, calls


def test_engine_import_does_not_construct_dss(monkeypatch):
    constructed = []

    class FakeDSS:
        def __init__(self):
            constructed.append(True)

    engine, calls = _load_engine(monkeypatch, FakeDSS)

    assert constructed == []
    assert calls["update"] == []


def test_get_dss_constructs_and_wires_once(monkeypatch):
    constructed = []

    class FakeDSS:
        def __init__(self):
            constructed.append(self)

    engine, calls = _load_engine(monkeypatch, FakeDSS)

    first = engine.get_dss()
    second = engine.get_dss()

    assert first is second
    assert constructed == [first]
    assert calls["update"] == [first]


def test_get_dss_returns_actionable_error_when_backend_fails(monkeypatch):
    class BrokenDSS:
        def __init__(self):
            raise OSError("native library unavailable")

    engine, calls = _load_engine(monkeypatch, BrokenDSS)

    with pytest.raises(RuntimeError, match="OpenDSS backend initialization failed: native library unavailable"):
        engine.get_dss()

    assert calls["update"] == []
    assert engine._dss is None
