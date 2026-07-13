'''This is the tooling to plot the average generation of each resource type
across all specified zones as a stacked area chart vs time.

Namely, this tool will re-weight the power.csv file according to the period
map used in time domain reduction, then find the average generation
for each hour of day across the entire year. The plot outputs as a PNG file
to the specified directory to save plots.

Further, this tool enables pairwise comparison of two scenarios,
where an additional line chart is plotted separately to show the difference
in average generation of Case 1 - Case 2.
'''

