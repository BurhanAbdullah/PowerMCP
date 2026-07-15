## Disclaimer

These functionalities are for after a GenX run has been manually configured.

## Available Tools
- [x] `plot_capacity` (with helpers `check_capacity_setting` and `summarize_capacity`)
<br>
Takes a capacity.csv file (one of GenX's default output CSV files), aggregates individual generation resources by type across a user-specified list of zones, plots capacity as a bar chart, and saves as a .png to the directory the user specifies to store plots. Resources are classified into Coal, Natural Gas (incl. petroleum/oil), Solar, Wind, Battery, Hydro, Nuclear, and Biomass, and always plotted in that order. Aggregates under 10 MW in magnitude are dropped as solver noise. `check_capacity_setting` detects whether a case is brownfield or greenfield, and `summarize_capacity` returns the aggregated table without plotting.
- [x] `submit_genx_case` (with dry-run counterpart `preview_genx_case`)
<br>
Scaffolds submission of a user configured GenX case to the high performance cluster they are using to run the optimization model. The cluster must use SLURM.
This is the culminating function that does the final send-out of a run, after
confirming which scenario folder to send (full absolute path) and the amount
of cluster resources to allocate. Namely, wallclock time, number of cores, and memory (in GB). `preview_genx_case` generates the same SLURM script without submitting it.
- [x] `plot_diurnal_generation`
<br>
Uses the `power.csv` file and timeweights from results_pN/time_weights.csv (where N is the relevant period) to create the annual average of each resource type's generation versus hour of day for the full representative output year. Plots as an area chart, and saves as a .png to the directory the user specifies to store plots. Optionally compares two scenarios side by side, or plots their difference (Case 1 − Case 2) as a line chart with `diff=True`.
<br>
- [x] `compute_capacity_cost`
Below is the computation calling this skill executes.

    ### Capacity Cost Calculation

    The table below defines the variables required to compute the capacity cost:

    | Notation | Description |
    | :--- | :--- |
    | $D_{t,z}$ | Demand at timestep $t$ in zone $z$ |
    | $\omega_t$ | Timeweight for timestep $t$ |
    | $\lambda_{r,t}$ | Shadow price ($/MWh) from the capacity reserve margin constraint for capacity reserve zone $r$ at timestep $t$ |
    | $Z_r$ | Set of sub-zones in capacity reserve zone $r$ |
    | subzones | Set of sub-zones the user seeks to find capacity cost among |

    *Table: Capacity Cost Variables*

    ### Total Annual Capacity Cost

    $$
    \text{TotalAnnualCapacityCost}_r = \sum_{t \in \mathcal{T}} \left( \lambda_{t,r} \cdot \sum_{z \in Z_r} D_{t,z} \cdot \omega_t \right)
    $$

    $$
    \text{TotalAnnualCapacityCost}_{\text{subzones}} = \sum_{r \in \mathcal{Z}^{\text{PJM}}_{\text{CapRes}}} \text{TotalAnnualCapacityCost}_r
    $$

    ### Annual Cost ($/MW-yr)

    $$
    \text{Price}_r^{\text{annual}} = \frac{\text{TotalAnnualCapacityCost}_r}{\displaystyle \max_{t \in \mathcal{T}} \left(\displaystyle \sum_{z \in Z_r} D_{t,z} \right)}
    $$

    $$
    \text{Price}_{\text{subzones}}^{\text{annual}} = \frac{\text{TotalAnnualCapacityCost}_{\text{subzones}}}{\displaystyle\max_{t \in \mathcal{T}} \left( \sum_{z \in Z^{\mathcal{subzones}}} D_{t,z}\right)}
    $$

    where the denominator in $\text{Price}_{\text{subzones}}^{\text{annual}}$ is the sum of demand across all subzones zones at the timestep where total subzone-wide demand is at a maximum.

    ### Daily Cost ($/MW-day)

    $$
    \text{Price}_r^{\text{day}} = \frac{\text{Price}_r^{\text{annual}}}{365}
    $$

    $$
    \text{Price}_{\text{PJM}}^{\text{day}} = \frac{\text{Price}_{\text{subzones}}^{\text{annual}}}{365}
    $$

    We map GenX results to a $/MW-day price that is comparable to ISO capacity auction convention -- like in the PJM market. This is achieved by normalizing total annual capacity cost by the coincident peak demand of all relevant capacity reserve zones and scaling down to a per-day value.

## Setup

Requires Python ≥ 3.10 and (for submission) a SLURM cluster with `sbatch` on
`PATH` plus a local GenX.jl checkout.

```bash
git clone <this-repo> genx_agent
cd genx_agent

# install dependencies
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# configure your environment
cp .env.example .env
#   then edit .env — at minimum set GENX_DIR
```

### Configuration (`.env`)

All personal/cluster-specific settings come from environment variables, loaded
from `.env` at startup. **`.env` is gitignored — never commit it.** `.env.example`
is the public template; copy it and fill in your own values.

| Variable | Required | Default | Notes |
|---|---|---|---|
| `GENX_DIR` | **yes** | — | Absolute path to your GenX.jl checkout. Server won't start if unset. |
| `SLURM_CPUS_DEFAULT` | no | `4` | CPUs per task when the caller doesn't specify. |
| `SLURM_MAIL_USER` | no | _(none)_ | Email for job notifications. Blank → no mail directives. |
| `GENX_LOG_DIR` | no | `<GENX_DIR>/run_logs` | Where `.out`/`.err` logs go. |
| `JULIA_MODULE` | no | _(none)_ | e.g. `julia/1.10.5`. Blank → no `module load`. |
| `GUROBI_MODULE` | no | _(none)_ | e.g. `gurobi/9.0.1`. Blank → no `module load`. |
| `JULIA_CPU_TARGET` | no | _(none)_ | Optional multi-arch build target. |

Run `module avail` on your cluster to find the correct module names.

## Establish Claude Code Connection

> Use **absolute paths** for both the Python interpreter and `server.py`.

### Claude Code

Register the server (run on the cluster, from any directory):

```bash
claude mcp add genx_agent -- /ABSOLUTE/PATH/TO/.venv/bin/python /ABSOLUTE/PATH/TO/genx_agent/server.py
```

Or copy `.mcp.json.example` to `.mcp.json` and edit the paths:

```json
{
  "mcpServers": {
    "genx_agent": {
      "command": "/ABSOLUTE/PATH/TO/.venv/bin/python",
      "args": ["/ABSOLUTE/PATH/TO/genx_agent/server.py"]
    }
  }
}
```

Then run `/mcp` inside Claude Code to verify it connected. Reconnect whenever you
edit the server code.

## Usage

Ask Claude in plain language:

- *"Preview the SLURM script for `scenarios/PJM_Baseline_Example` at 12h, 3 cores, 128GB"* → dry run
- *"Submit that case"* → `sbatch`, returns job ID
- *"Summarize the capacity in `.../results/capacity.csv` for zones 10 and 23"*
- *"Plot NewCap for the baseline scenario, period 1, into `./plots`"*

Walltime and memory are **required** for submission — the tools ask for them if
you don't provide them rather than guessing. Plots are named by plot type only
(`{PlotType}.png`), so plotting a different scenario into the same directory
overwrites earlier PNGs.