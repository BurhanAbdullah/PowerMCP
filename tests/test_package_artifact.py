"""Release-artifact smoke tests for the single-package distribution."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
import zipfile


ROOT = Path(__file__).resolve().parents[1]

# These are the server entry points that the wheel must carry.  Keeping this
# list here makes a packaging regression fail in CI instead of surfacing only
# after a published wheel is installed by a user.
REQUIRED_WHEEL_PATHS = (
    "powermcp/_servers/pandapower/panda_mcp.py",
    "powermcp/_servers/PyPSA/pypsa_mcp.py",
    "powermcp/_servers/ANDES/andes_mcp.py",
    "powermcp/_servers/OpenDSS/opendss_mcp.py",
    "powermcp/_servers/HOPE/hope_mcp.py",
    "powermcp/_servers/GenX/genx_mcp.py",
    "powermcp/_servers/PLEXOSDB/plexosdb_mcp.py",
)


def test_wheel_contains_bundled_server_entry_points(tmp_path: Path) -> None:
    """Build the real wheel and verify force-included server files survive."""
    dist = tmp_path / "dist"
    subprocess.run(
        [
            sys.executable,
            "-m",
            "build",
            "--wheel",
            "--no-isolation",
            "--outdir",
            str(dist),
        ],
        cwd=ROOT,
        check=True,
    )

    wheels = sorted(dist.glob("*.whl"))
    assert len(wheels) == 1

    with zipfile.ZipFile(wheels[0]) as wheel:
        members = set(wheel.namelist())

    missing = [path for path in REQUIRED_WHEEL_PATHS if path not in members]
    assert not missing, f"wheel is missing bundled server files: {missing}"


def test_wheel_exposes_console_script_metadata(tmp_path: Path) -> None:
    """The built wheel must retain the public ``powermcp`` CLI entry point."""
    dist = tmp_path / "dist"
    subprocess.run(
        [
            sys.executable,
            "-m",
            "build",
            "--wheel",
            "--no-isolation",
            "--outdir",
            str(dist),
        ],
        cwd=ROOT,
        check=True,
    )

    wheels = sorted(dist.glob("*.whl"))
    assert len(wheels) == 1

    with zipfile.ZipFile(wheels[0]) as wheel:
        metadata = "\n".join(
            wheel.read(name).decode("utf-8")
            for name in wheel.namelist()
            if name.endswith("/METADATA") or name.endswith("/entry_points.txt")
        )

    assert "powermcp.cli:main" in metadata
