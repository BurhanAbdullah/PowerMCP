"""R2X-backed SIENNA translation and comparison tools."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def translate_to_plexos(json_path: str, output_path: str, model_name: str = "SiennaModel") -> dict[str, Any]:
    """Translate Sienna PSY JSON to a PLEXOS XML model using R2X directly."""
    source = Path(json_path).expanduser().resolve()
    destination = Path(output_path).expanduser().resolve()
    if not source.is_file():
        return {"ok": False, "error": f"system file not found: {source}"}
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        from r2x_core import PluginContext
        from r2x_sienna import SiennaConfig, SiennaParser
        from r2x_sienna_to_plexos import SiennaToPlexosConfig, sienna_to_plexos
        from r2x_plexos import PLEXOSExporter, PLEXOSExporterConfig

        parse_ctx = PluginContext(config=SiennaConfig(fpath=str(source)))
        parse_ctx = SiennaParser.from_context(parse_ctx).run()
        plexos_system = sienna_to_plexos(parse_ctx.system, SiennaToPlexosConfig(model_name=model_name))
        export_ctx = PluginContext(
            config=PLEXOSExporterConfig(output_path=str(destination), model_name=model_name),
            system=plexos_system,
        )
        PLEXOSExporter.from_context(export_ctx).run()
        return {"ok": True, "output_path": str(destination), "model_name": model_name}
    except Exception as exc:
        return {"ok": False, "error": f"R2X translation failed: {exc}"}


def compare_solutions(json_path_a: str, json_path_b: str) -> dict[str, Any]:
    """Compare two Sienna systems by component-type counts through R2X."""
    try:
        from r2x_core import PluginContext
        from r2x_sienna import SiennaConfig, SiennaParser

        def counts(path: str) -> dict[str, int]:
            ctx = PluginContext(config=SiennaConfig(fpath=str(Path(path).expanduser().resolve())))
            ctx = SiennaParser.from_context(ctx).run()
            return {
                typ.__name__: len(list(ctx.system.get_components(typ)))
                for typ in ctx.system.get_component_types()
            }

        a = counts(json_path_a)
        b = counts(json_path_b)
    except Exception as exc:
        return {"ok": False, "error": f"R2X comparison failed: {exc}"}
    differences = {
        key: {"a": a.get(key, 0), "b": b.get(key, 0)}
        for key in sorted(set(a) | set(b))
        if a.get(key, 0) != b.get(key, 0)
    }
    return {"ok": True, "a": a, "b": b, "differences": differences, "identical": not differences}


def register_r2x_tools(mcp: Any) -> None:
    mcp.tool()(translate_to_plexos)
    mcp.tool()(compare_solutions)
