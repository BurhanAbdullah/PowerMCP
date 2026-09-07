# SIENNA — PowerMCP connector

Open-source Sienna/PowerSystems.jl integration for PowerMCP. The connector exposes four MCP tools:

- `load_system` — validate a Sienna PSY JSON file and deserialize it with `PowerSystems.jl`.
- `translate_to_plexos` — translate PSY JSON to PLEXOS through the public `r2x` API.
- `run_sienna_solve` — invoke the local Julia/PowerSimulations.jl runtime.
- `compare_solutions` — compare two Sienna systems by component-type counts through `r2x`.

No PLEXOS installation or license is required.

## Runtime setup

Install the Python connector through the `sienna` extra:

```bash
pip install 'powermcp[sienna]'
```

Install Julia separately, then add the Sienna packages to the Julia environment:

```julia
using Pkg
Pkg.add(["PowerSystems", "PowerSimulations", "HiGHS"])
```

Set `julia_bin` to the Julia executable and, optionally, `julia_depot_path` in the PowerMCP configuration. The same values can be supplied to `load_system`/`run_sienna_solve` explicitly or through `JULIA_BIN`/`JULIA_DEPOT_PATH`.

## PLEXOS interoperability

The paired `PLEXOSDB` connector's `translate_to_sienna` tool produces Sienna PSY JSON. Pass that JSON directly to `load_system`, then use `run_sienna_solve` with the local Julia runtime.

`translate_to_plexos` performs the reverse conversion by calling R2X directly; it does not depend on the PLEXOSDB connector being installed.

## Solve note

Sienna is a Julia framework rather than a single fixed solver. `run_sienna_solve` loads the supplied PSY system and initializes the open-source PowerSimulations/HiGHS runtime; the exact study formulation (production cost, unit commitment, or another supported formulation) belongs to the supplied Sienna case. The tool therefore does not fabricate a generic study template or claim PLEXOS parity.

For a real solve, use a PSY JSON case that contains the data and study formulation expected by your PowerSimulations workflow. The repository tests mock the Julia boundary so they remain license-free and deterministic; a real Julia solve should be recorded separately with Julia and package versions.
