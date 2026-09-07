from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from sienna_mcp.tools.load_tools import load_system
from sienna_mcp.tools.r2x_tools import compare_solutions, translate_to_plexos
from sienna_mcp.tools.solve_tools import run_sienna_solve


def test_load_system_validates_json_before_julia(tmp_path: Path):
    case = tmp_path / "case.json"
    case.write_text(json.dumps({"name": "case"}), encoding="utf-8")
    with patch("sienna_mcp.tools.load_tools.subprocess.run") as run:
        run.return_value.returncode = 0
        run.return_value.stdout = "3\n"
        run.return_value.stderr = ""
        result = load_system(str(case), julia_bin="julia")
    assert result["ok"] is True
    assert result["component_count"] == 3
    run.assert_called_once()


def test_load_system_missing_file():
    result = load_system("/does/not/exist.json")
    assert result["ok"] is False


def test_r2x_translation_is_mockable_without_importing_r2x():
    source = Path("case.json")
    fake_parser = type("FakeParser", (), {})
    with patch.dict("sys.modules", {
        "r2x_core": type("M", (), {"PluginContext": object}),
        "r2x_sienna": type("M", (), {"SiennaConfig": object, "SiennaParser": fake_parser}),
    }):
        # Missing source is rejected before the optional dependency boundary.
        result = translate_to_plexos(str(source), "/tmp/out.xml")
    assert result["ok"] is False


def test_compare_missing_input():
    result = compare_solutions("/missing/a.json", "/missing/b.json")
    assert result["ok"] is False


def test_solve_reports_julia_failure(tmp_path: Path):
    case = tmp_path / "case.json"
    case.write_text("{}", encoding="utf-8")
    with patch("sienna_mcp.tools.solve_tools.subprocess.run") as run:
        run.return_value.returncode = 1
        run.return_value.stdout = ""
        run.return_value.stderr = "PowerSimulations unavailable"
        result = run_sienna_solve(str(case), str(tmp_path / "result.txt"), julia_bin="julia")
    assert result["ok"] is False
    assert "unavailable" in result["error"]
