"""Tests for the ANDES MCP server's simulation tools (power flow, time-domain,
and eigenvalue/small-signal analysis).

andes is an optional pip extra (`pip install "powermcp[andes]"`), not a core
dependency, so every test in this module goes through the `andes_mcp` fixture
in conftest.py, which calls `pytest.importorskip("andes")`. In this repo's
base CI job (.github/workflows/test.yml installs no extras), these tests
therefore show as SKIPPED, not run -- verified locally by installing andes
into a venv and running this file directly (`pip install andes && pytest
tests/test_andes_server.py -v`), matching the existing ANDES-bridge tests'
posture in test_powerio_server.py.

ANDES/kundur_full.json is the repo's only ANDES fixture: a Kundur two-area
four-machine system with its own embedded dynamic models (GENROU, exciters,
governors), so it exercises power flow, time-domain simulation, and
eigenvalue analysis all in one case with no fixture authoring needed here.

The raw+dyr dynamic-model-loading tests further down this file use ANDES's
own bundled ieee14 PSS/E case (raw + dyr), resolved via andes.get_case(...)
at test-call time -- see the comment above _ieee14_raw_dyr_paths() for why.
"""

from __future__ import annotations

from pathlib import Path

KUNDUR_FULL = Path(__file__).resolve().parents[1] / "ANDES" / "kundur_full.json"


def test_run_power_flow_converges(andes_mcp):
    r = andes_mcp.run_power_flow(str(KUNDUR_FULL))
    assert r["status"] == "success", r
    assert r["power_flow"]["converged"] is True


def test_get_system_info_reports_plausible_counts(andes_mcp):
    # get_system_info reads from the module-level system_state, which the
    # power flow run above populates.
    r = andes_mcp.run_power_flow(str(KUNDUR_FULL))
    assert r["status"] == "success", r

    info = andes_mcp.get_system_info()
    assert info["status"] == "success", info
    assert info["num_buses"] > 0
    assert info["num_generators"] > 0


def test_run_time_domain_simulation_completes(andes_mcp):
    pf = andes_mcp.run_power_flow(str(KUNDUR_FULL))
    assert pf["status"] == "success", pf

    r = andes_mcp.run_time_domain_simulation(step_size=0.01, t_end=1.0)
    assert r["status"] == "success", r
    sim = r["simulation"]
    assert sim["success"] is True
    assert sim["status"] == "completed"
    assert sim["t_end"] == 1.0
    assert sim["step_size"] == 0.01
    # Not asserting on t_array's shape here: this installed ANDES version
    # returns ss.dae.t as a 0-d array (final sim time) rather than a full
    # per-step series, which is a pre-existing quirk of
    # run_time_domain_simulation orthogonal to the eigenvalue-analysis fix
    # this PR targets, so it's left alone (out of scope).
    assert "t_array" in sim


def test_run_eigenvalue_analysis_returns_modes(andes_mcp):
    r = andes_mcp.run_eigenvalue_analysis(str(KUNDUR_FULL))
    assert r["status"] == "success", r
    analysis = r["analysis"]
    assert analysis["success"] is True
    assert analysis["n_modes"] > 0

    modes = analysis["modes"]
    assert len(modes) == analysis["n_modes"]
    for mode in modes:
        assert isinstance(mode["frequency_hz"], (int, float))
        assert isinstance(mode["damping_ratio_pct"], (int, float))
        assert isinstance(mode["is_oscillatory"], bool)
        assert len(mode["eigenvalue"]) == 2

    # Regression check for the original bug: run_eigenvalue_analysis used to
    # read ss.EIG.vectors/state_desc, attributes that don't exist on the real
    # EIG object, so hasattr() guards silently returned [] for these fields.
    # The real attribute is x_name (state labels); it must be non-empty now.
    assert len(analysis["state_names"]) > 0
    assert len(analysis["participation_factors"]) > 0

    # Modes are sorted least-damped (most concerning) first.
    damping_values = [m["damping_ratio_pct"] for m in modes]
    assert damping_values == sorted(damping_values)


def test_run_eigenvalue_analysis_missing_file(andes_mcp, tmp_path):
    r = andes_mcp.run_eigenvalue_analysis(str(tmp_path / "nope.json"))
    assert r["status"] == "error"
    assert "not found" in r["message"].lower()


# ---------------------------------------------------------------------------
# PSS/E raw+dyr dynamic-model loading (fungible-farm/PowerMCP#2)
#
# These tests use ANDES's own bundled ieee14 example case (raw + dyr),
# resolved at test-call time via andes.get_case(...), which reads from the
# installed andes package's own andes/cases/ directory (andes declares these
# as package-data in its own pyproject.toml). No .raw/.dyr fixture is
# authored or vendored into this repo: ieee14.raw/.dyr are GPL-3.0 ANDES
# files, and this repo is MIT, so referencing the installed dependency's own
# copy avoids any vendoring question entirely.
#
# andes must not be imported at module scope (it may not be installed), so
# the get_case() calls happen inside a helper invoked from within each test
# body, after the andes_mcp fixture parameter has already run
# pytest.importorskip("andes").
# ---------------------------------------------------------------------------


def _ieee14_raw_dyr_paths():
    import andes

    raw_path = andes.get_case("ieee14/ieee14.raw")
    dyr_path = andes.get_case("ieee14/ieee14.dyr")
    return raw_path, dyr_path


def test_run_power_flow_without_dyr_has_no_dynamic_models(andes_mcp):
    raw_path, _ = _ieee14_raw_dyr_paths()

    r = andes_mcp.run_power_flow(raw_path)
    assert r["status"] == "success", r
    pf = r["power_flow"]
    assert pf["converged"] is True
    assert pf["dynamic_models_loaded"] is False
    assert pf["n_dynamic_generators"] == 0


def test_run_power_flow_with_dyr_attaches_dynamic_models(andes_mcp):
    raw_path, dyr_path = _ieee14_raw_dyr_paths()

    r = andes_mcp.run_power_flow(raw_path, dyr_path=dyr_path)
    assert r["status"] == "success", r
    pf = r["power_flow"]
    assert pf["converged"] is True
    assert pf["dynamic_models_loaded"] is True
    # Not asserting an exact count (e.g. == 5): stay robust to upstream ANDES
    # case-file changes across versions -- only assert that dynamics
    # actually attached.
    assert pf["n_dynamic_generators"] > 0


def test_run_power_flow_with_dyr_enables_time_domain_simulation(andes_mcp):
    # The actual motivating scenario from the issue: without a .dyr there are
    # no real dynamics to simulate.
    raw_path, dyr_path = _ieee14_raw_dyr_paths()

    pf = andes_mcp.run_power_flow(raw_path, dyr_path=dyr_path)
    assert pf["status"] == "success", pf
    assert pf["power_flow"]["n_dynamic_generators"] > 0

    r = andes_mcp.run_time_domain_simulation(step_size=0.01, t_end=1.0)
    assert r["status"] == "success", r
    sim = r["simulation"]
    assert sim["success"] is True
    assert sim["status"] == "completed"


def test_run_power_flow_missing_dyr_file(andes_mcp, tmp_path):
    raw_path, _ = _ieee14_raw_dyr_paths()

    r = andes_mcp.run_power_flow(raw_path, dyr_path=str(tmp_path / "nope.dyr"))
    assert r["status"] == "error"
    assert "not found" in r["message"].lower()
