## Disclaimer

These functionalities are for after a GenX run has been manually configured.

## Available Tools
- [x] `plot_capacity_bar`
<br>
Takes a capacity.csv file (one of GenX's default output CSV files), aggregates individual generation resources by type across a user-specified list of zones, plots capacity as a bar chart, and saves as a .png to the directory the user specifies to store plots.
- [x] `submit_case`
<br>
Scaffolds submission of a user configured GenX case to the high performance cluster they are using to run the optimization model. The cluster must use SLURM.
This is the culminating function that does the final send-out of a run, after
confirming which scenario folder to send (full absolute path) and the amount
of cluster resources to allocate. Namely, wallclock time, number of cores, and memory (in GB).
- [x] `plot_average_generation`

