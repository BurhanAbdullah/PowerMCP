"""Dependency compatibility helpers for PowerMCP server launch preflight."""

from __future__ import annotations

import importlib.metadata
from packaging.requirements import Requirement
from packaging.version import InvalidVersion, Version


def _canonical(name: str) -> str:
    return name.lower().replace("-", "_").replace(".", "_")


def requirement_for_probe(probe: str, distribution: str = "powermcp") -> Requirement | None:
    try:
        declared = importlib.metadata.requires(distribution) or ()
    except importlib.metadata.PackageNotFoundError:
        return None

    candidates = {
        _canonical(probe),
        _canonical(probe.split(".", 1)[0]),
    }
    for raw in declared:
        req = Requirement(raw)
        if _canonical(req.name) in candidates and req.specifier:
            return req
    return None


def incompatible_requirement(probe: str) -> tuple[str, str] | None:
    req = requirement_for_probe(probe)
    if req is None:
        return None

    try:
        installed = importlib.metadata.version(req.name)
        parsed = Version(installed)
    except (importlib.metadata.PackageNotFoundError, InvalidVersion):
        return None

    if parsed in req.specifier:
        return None

    return req.name, f"{req.name} {installed} does not satisfy {req.specifier}"
