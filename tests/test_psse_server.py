"""PSS/E server tools against a fake psspy and dyntools.

PSS/E is commercial and Windows only, so CI never has it. These tests stand in
fakes for the parts of the server that are plain Python: what a tool does with
the error codes psspy hands back and the channels dyntools reads. The
live-engine counterparts are in PSSE/tests and skip themselves without an
installation.
"""

from __future__ import annotations

import sys
import types

import pytest

from PSSE import psse_mcp


class FakePsspy:
    """Records calls; each method returns what the test configured."""

    def __init__(self, case=0, abuscount=(0, 23), abrncount=(0, 34), amachcount=(0, 6)):
        self.calls = []
        self._returns = {
            "case": case,
            "abuscount": abuscount,
            "abrncount": abrncount,
            "amachcount": amachcount,
        }

    def __getattr__(self, name):
        if name not in self._returns:
            raise AttributeError(name)

        def call(*args, **kwargs):
            self.calls.append(name)
            return self._returns[name]

        return call


@pytest.fixture
def case_file(tmp_path, monkeypatch):
    monkeypatch.setenv("POWERIO_MCP_ALLOWED_ROOTS", str(tmp_path))
    path = tmp_path / "savnw.sav"
    path.write_bytes(b"")
    return path


def _use(monkeypatch, fake):
    monkeypatch.setattr(psse_mcp, "psspy", fake)
    monkeypatch.setattr(psse_mcp, "_ensure_psse", lambda: fake)


def test_open_case_returns_the_counts_of_the_loaded_case(monkeypatch, case_file):
    fake = FakePsspy()
    _use(monkeypatch, fake)

    result = psse_mcp.open_case(str(case_file))

    assert result == {
        "status": "success",
        "case_info": {
            "path": str(case_file),
            "num_buses": 23,
            "num_branches": 34,
            "num_generators": 6,
        },
    }


def test_open_case_reports_a_failed_load_instead_of_the_previous_case(
    monkeypatch, case_file
):
    """psspy.case leaves the previous case in memory when it fails.

    Counting after a failed load describes that earlier case, so the tool used
    to report success with another network's sizes under the new path.
    """
    fake = FakePsspy(case=3)
    _use(monkeypatch, fake)

    result = psse_mcp.open_case(str(case_file))

    assert result["status"] == "error"
    assert result["ierr"] == 3
    assert "psspy.case" in result["message"]
    assert fake.calls == ["case"]


@pytest.mark.parametrize("failing", ["abuscount", "abrncount", "amachcount"])
def test_open_case_reports_whichever_count_fails(monkeypatch, case_file, failing):
    fake = FakePsspy(**{failing: (1, None)})
    _use(monkeypatch, fake)

    result = psse_mcp.open_case(str(case_file))

    assert result["status"] == "error"
    assert result["ierr"] == 1
    assert f"psspy.{failing}" in result["message"]


CHANNELS = {
    "time": "Time(s)",
    1: "POWR 101[NUC-A 21.600]1",
    2: "POWR 102[NUC-B 21.600]1",
}
DATA = {
    "time": [-0.0167, 0.0, 0.0083],
    1: [750.0, 750.0, 749.8],
    2: [750.0, 750.0, 749.6],
}


@pytest.fixture
def outfile(tmp_path, monkeypatch):
    monkeypatch.setenv("POWERIO_MCP_ALLOWED_ROOTS", str(tmp_path))
    path = tmp_path / "fault.out"
    path.write_bytes(b"")
    return path


@pytest.fixture
def dyntools(monkeypatch):
    """A fake dyntools that, like the real one, imports only after PSS/E starts.

    dyntools lives in the PSSPY directory, which _ensure_psse puts on sys.path.
    The fake engine start registers the module, so a tool that imports it
    before starting the engine fails here as it does in a fresh session.
    """
    opened = []

    class CHNF:
        def __init__(self, outfile, outvrsn=0):
            opened.append((outfile, outvrsn))

        def get_data(self):
            return "SAVNW FAULT", dict(CHANNELS), {k: list(v) for k, v in DATA.items()}

    module = types.ModuleType("dyntools")
    module.CHNF = CHNF
    module.opened = opened
    module.engine_starts = 0

    def ensure_psse():
        module.engine_starts += 1
        monkeypatch.setitem(sys.modules, "dyntools", module)

    monkeypatch.delitem(sys.modules, "dyntools", raising=False)
    monkeypatch.setattr(psse_mcp, "_ensure_psse", ensure_psse)
    return module


def test_listing_channels_works_in_a_fresh_session(dyntools, outfile):
    result = psse_mcp.list_dynamic_output_channels(str(outfile))

    assert result == {
        "status": "success",
        "outfile": str(outfile),
        "title": "SAVNW FAULT",
        "channels": {
            "time": "Time(s)",
            "1": "POWR 101[NUC-A 21.600]1",
            "2": "POWR 102[NUC-B 21.600]1",
        },
    }
    assert dyntools.opened == [(str(outfile), 0)]


def test_reading_selected_channels_includes_time(dyntools, outfile):
    result = psse_mcp.read_dynamic_output(str(outfile), channels=[2], outvrsn=1)

    assert result["status"] == "success", result
    assert result["channels"] == {"time": "Time(s)", "2": "POWR 102[NUC-B 21.600]1"}
    assert result["data"] == {"time": DATA["time"], "2": DATA[2]}
    assert result["num_points"] == 3
    assert result["total_points"] == 3
    assert result["downsampled"] is False
    assert result["max_points"] == 10_000
    assert result["max_cells"] == 100_000
    assert result["effective_points"] == 10_000
    assert result["returned_cells"] == 6
    assert dyntools.opened == [(str(outfile), 1)]


def test_reading_without_a_selection_returns_every_channel(dyntools, outfile):
    result = psse_mcp.read_dynamic_output(str(outfile))

    assert result["status"] == "success", result
    assert set(result["data"]) == {"time", "1", "2"}
    assert result["num_points"] == 3
    assert result["total_points"] == 3
    assert result["downsampled"] is False
    assert result["max_cells"] == 100_000
    assert result["effective_points"] == 10_000


def test_reading_dynamic_output_can_be_deterministically_capped(dyntools, outfile):
    result = psse_mcp.read_dynamic_output(
        str(outfile), channels=[1, 2], max_points=2
    )

    assert result["status"] == "success", result
    assert result["num_points"] == 2
    assert result["total_points"] == 3
    assert result["downsampled"] is True
    assert result["max_points"] == 2
    assert result["max_cells"] == 100_000
    assert result["effective_points"] == 2
    assert result["data"]["time"] == [DATA["time"][0], DATA["time"][-1]]
    assert result["data"]["1"] == [DATA[1][0], DATA[1][-1]]
    assert result["data"]["2"] == [DATA[2][0], DATA[2][-1]]


def test_cell_budget_reduces_effective_points_for_many_channels(dyntools, outfile):
    point_count = 12_001
    channels = {"time": "Time(s)"}
    large_data = {"time": list(range(point_count))}
    for channel in range(1, 5):
        channels[channel] = f"CHANNEL {channel}"
        large_data[channel] = list(range(point_count))

    class LargeCHNF:
        def __init__(self, outfile, outvrsn=0):
            dyntools.opened.append((outfile, outvrsn))

        def get_data(self):
            return "LARGE RUN", channels, large_data

    dyntools.CHNF = LargeCHNF

    result = psse_mcp.read_dynamic_output(
        str(outfile), max_points=10_000, max_cells=10
    )

    assert result["status"] == "success", result
    assert result["total_points"] == point_count
    assert result["effective_points"] == 2
    assert result["num_points"] == 2
    assert result["returned_cells"] == 10
    assert result["downsampled"] is True


def test_downsampled_output_reports_full_resolution_extrema(dyntools, outfile):
    data = {"time": [0, 1, 2, 3, 4], 1: [10.0, 8.0, 2.0, 9.0, 7.0]}

    class ExtremaCHNF:
        def __init__(self, outfile, outvrsn=0):
            dyntools.opened.append((outfile, outvrsn))

        def get_data(self):
            return "EXTREMA RUN", {"time": "Time(s)", 1: "VOLTAGE"}, data

    dyntools.CHNF = ExtremaCHNF
    result = psse_mcp.read_dynamic_output(str(outfile), channels=[1], max_points=3)

    assert result["status"] == "success", result
    assert result["data"]["1"] == [10.0, 2.0, 7.0]
    assert result["extrema"]["1"] == {
        "min": 2.0,
        "min_index": 2,
        "min_time": 2,
        "max": 10.0,
        "max_index": 0,
        "max_time": 0,
    }


def test_mismatched_dynamic_channel_is_rejected_without_sampling(dyntools, outfile):
    data = {"time": [0, 1, 2], 1: [10.0, 9.0]}

    class MismatchCHNF:
        def __init__(self, outfile, outvrsn=0):
            dyntools.opened.append((outfile, outvrsn))

        def get_data(self):
            return "BAD RUN", {"time": "Time(s)", 1: "VOLTAGE"}, data

    dyntools.CHNF = MismatchCHNF
    result = psse_mcp.read_dynamic_output(str(outfile))

    assert result["status"] == "error"
    assert "expected 3 to match the time vector" in result["message"]


def test_missing_dynamic_time_vector_is_rejected(dyntools, outfile):
    data = {1: [1.0, 2.0, 3.0]}

    class MissingTimeCHNF:
        def __init__(self, outfile, outvrsn=0):
            dyntools.opened.append((outfile, outvrsn))

        def get_data(self):
            return "BAD RUN", {1: "VOLTAGE"}, data

    dyntools.CHNF = MissingTimeCHNF
    result = psse_mcp.read_dynamic_output(str(outfile))

    assert result["status"] == "error"
    assert "missing a non-empty time vector" in result["message"]


@pytest.mark.parametrize("max_cells", [0, 1, True, 1.5, "10"])
def test_invalid_dynamic_output_cell_caps_are_rejected_before_engine_start(
    dyntools, outfile, max_cells
):
    result = psse_mcp.read_dynamic_output(str(outfile), max_cells=max_cells)

    assert result["status"] == "error"
    assert "max_cells must be an integer of at least 2" in result["message"]
    assert dyntools.engine_starts == 0


def test_default_point_cap_bounds_a_large_dynamic_output(dyntools, outfile):
    point_count = 12_001
    large_data = {
        "time": list(range(point_count)),
        1: list(range(point_count)),
        2: list(range(point_count)),
    }

    class LargeCHNF:
        def __init__(self, outfile, outvrsn=0):
            dyntools.opened.append((outfile, outvrsn))

        def get_data(self):
            return "LARGE RUN", dict(CHANNELS), large_data

    dyntools.CHNF = LargeCHNF

    result = psse_mcp.read_dynamic_output(str(outfile))

    assert result["status"] == "success", result
    assert result["total_points"] == point_count
    assert result["num_points"] == 10_000
    assert result["downsampled"] is True
    assert result["max_points"] == 10_000
    assert result["max_cells"] == 100_000
    assert result["effective_points"] == 10_000
    assert result["returned_cells"] == 30_000
    assert result["data"]["time"][0] == 0
    assert result["data"]["time"][-1] == point_count - 1
    assert len(result["data"]["1"]) == 10_000
    assert len(result["data"]["2"]) == 10_000


@pytest.mark.parametrize("max_points", [0, 1, True, 1.5, "10"])
def test_invalid_dynamic_output_point_caps_are_rejected_before_engine_start(
    dyntools, outfile, max_points
):
    result = psse_mcp.read_dynamic_output(
        str(outfile), max_points=max_points
    )

    assert result["status"] == "error"
    assert "max_points must be an integer of at least 2" in result["message"]
    assert dyntools.engine_starts == 0


def test_reading_an_unknown_channel_names_it(dyntools, outfile):
    result = psse_mcp.read_dynamic_output(str(outfile), channels=[1, 99])

    assert result["status"] == "error"
    assert "[99]" in result["message"]


@pytest.mark.parametrize("channels", [[], [0], [-1], [True]])
def test_malformed_channel_selections_are_refused_before_engine_start(
    dyntools, outfile, channels
):
    result = psse_mcp.read_dynamic_output(str(outfile), channels=channels)

    assert result["status"] == "error"
    assert dyntools.engine_starts == 0


@pytest.mark.parametrize(
    "tool", [psse_mcp.list_dynamic_output_channels, psse_mcp.read_dynamic_output]
)
def test_a_missing_output_file_is_reported_before_engine_start(
    dyntools, outfile, tool
):
    result = tool(str(outfile.with_name("missing.out")))

    assert result["status"] == "error"
    assert "does not exist" in result["message"]
    assert dyntools.engine_starts == 0


@pytest.mark.parametrize(
    "tool", [psse_mcp.list_dynamic_output_channels, psse_mcp.read_dynamic_output]
)
def test_an_output_file_outside_the_roots_is_refused(
    dyntools, tmp_path, monkeypatch, tool
):
    allowed = tmp_path / "allowed"
    allowed.mkdir()
    outside = tmp_path / "outside.out"
    outside.write_bytes(b"")
    monkeypatch.setenv("POWERIO_MCP_ALLOWED_ROOTS", str(allowed))

    result = tool(str(outside))

    assert result["status"] == "error"
    assert "outside allowed MCP roots" in result["message"]
    assert dyntools.engine_starts == 0



def test_resolve_psse_paths_prefers_configured_install(monkeypatch, tmp_path):
    """Configured paths take precedence over registry/filesystem discovery."""
    import powermcp.config

    python_lib = tmp_path / "PSSE37" / "37.1" / "PSSPY312"
    bin_dir = tmp_path / "PSSE37" / "37.1" / "PSSBIN"
    python_lib.mkdir(parents=True)
    bin_dir.mkdir(parents=True)
    (python_lib / "psspy.pyd").write_bytes(b"fake")
    monkeypatch.setattr(
        powermcp.config,
        "get_path",
        lambda product, key, must_exist=False: (
            str(python_lib) if key == "python_lib" else str(bin_dir)
        ),
    )
    monkeypatch.setattr(psse_mcp, "_psse_candidates_from_registry", lambda pyver: [])
    monkeypatch.setattr(psse_mcp, "_psse_candidates_from_filesystem", lambda pyver: [])

    assert psse_mcp._resolve_psse_paths() == (
        str(python_lib), str(bin_dir), "psse37"
    )


def test_resolve_psse_paths_discovers_highest_major_without_fixed_cap(monkeypatch):
    """A discovered PSS/E 37 install must beat 36 and 35."""
    import powermcp.config
    monkeypatch.setattr(
        powermcp.config, "get_path",
        lambda product, key, must_exist=False: None,
    )
    monkeypatch.setattr(
        psse_mcp, "_psse_candidates_from_registry",
        lambda pyver: [
            ((36, 2), 36, "36.2", r"C:\PSSE36\PSSPY", r"C:\PSSE36\PSSBIN"),
            ((37, 1), 37, "37.1", r"C:\PSSE37\PSSPY", r"C:\PSSE37\PSSBIN"),
            ((35, 6), 35, "35.6", r"C:\PSSE35\PSSPY", r"C:\PSSE35\PSSBIN"),
        ],
    )
    monkeypatch.setattr(psse_mcp, "_psse_candidates_from_filesystem", lambda pyver: [])
    monkeypatch.setattr(psse_mcp, "_is_valid_psspy_dir", lambda *args: False)

    python_lib, bin_dir, module = psse_mcp._resolve_psse_paths()
    assert python_lib == r"C:\PSSE37\PSSPY"
    assert bin_dir == r"C:\PSSE37\PSSBIN"
    assert module == "psse37"


def test_resolve_psse_paths_reports_partial_manual_override(monkeypatch):
    import powermcp.config
    monkeypatch.setattr(
        powermcp.config, "get_path",
        lambda product, key, must_exist=False: None,
    )
    monkeypatch.setenv("PSSE_PSSPY_PATH", r"C:\PSSE37\PSSPY312")
    monkeypatch.delenv("PSSE_EXE_PATH", raising=False)
    monkeypatch.setattr(psse_mcp, "_psse_candidates_from_registry", lambda pyver: [])
    monkeypatch.setattr(psse_mcp, "_psse_candidates_from_filesystem", lambda pyver: [])

    with pytest.raises(RuntimeError, match="requires both PSSE_PSSPY_PATH and PSSE_EXE_PATH"):
        psse_mcp._resolve_psse_paths()


def test_run_psspy_command_returns_captured_console_output(monkeypatch, tmp_path):
    """PSS/E's report output is returned to the caller, not leaked to stdout."""
    import json

    spec_dir = tmp_path / "specs"
    spec_dir.mkdir()
    (spec_dir / "diff.json").write_text(
        json.dumps({
            "function_name": "diff",
            "return_type": "void",
            "parameters": [],
            "return_values": [],
        }),
        encoding="utf-8",
    )
    monkeypatch.setattr(psse_mcp, "JSON_DIR", spec_dir)

    class PrintingPsspy:
        def diff(self):
            print("PSS/E difference report")

    monkeypatch.setattr(psse_mcp, "psspy", PrintingPsspy())
    monkeypatch.setattr(psse_mcp, "_ensure_psse", lambda: psse_mcp.psspy)
    monkeypatch.setattr(psse_mcp, "_command_spec_path", lambda name: spec_dir / f"{name}.json")

    result = psse_mcp.run_psspy_command("diff", {})
    assert result["status"] == "success"
    assert result["_console_output"] == "PSS/E difference report\n"
    assert result["_function"] == "diff"



def test_psse_version_override_accepts_full_version(monkeypatch):
    monkeypatch.setenv("PSSE_VERSION", "36.2")
    assert psse_mcp._major_from_paths(r"C:\custom\PSSPY311") == 36


def test_python_library_path_must_match_interpreter_when_version_is_encoded():
    assert psse_mcp._python_lib_matches_interpreter(r"C:\PSSE37\37.1\PSSPY312", "312")
    assert not psse_mcp._python_lib_matches_interpreter(r"C:\PSSE36\36.2\PSSPY311", "312")
    # Custom directory names are accepted; the caller's explicit configuration
    # may legitimately use a nonstandard folder name.
    assert psse_mcp._python_lib_matches_interpreter(r"C:\custom\psspy", "312")
