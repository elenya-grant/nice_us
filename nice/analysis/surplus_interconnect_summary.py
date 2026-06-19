from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from nice import DATA_DIR, ROOT_DIR
from nice.tools.create_data import (
    calculate_surplus_interconnect_factor,
    create_surplus_interconnect_data,
)
from nice.tools.eia_860_file_tools import make_prime_mover_cmap, prime_mover_to_desc
from nice.tools.geo_data_file_tools import load_us_state_boundaries

surplus_threshold_fractions = [0.8, 0.9, 1.0]

include_zero_generation = True
include_non_continental = True
figure_dir = ROOT_DIR.parent / "charts_figures"

output_data_dir = DATA_DIR / "nice_data_aggregated"
spi_data_fpath = output_data_dir / "surplus_interconnect_data_missing_is_None_2024.csv"
if not output_data_dir.exists():
    Path(output_data_dir).mkdir(exist_ok=True, parents=True)

if not figure_dir.exists():
    Path(figure_dir).mkdir(exist_ok=True, parents=True)

if not spi_data_fpath.is_file():
    data = create_surplus_interconnect_data(missing_val=None)
    data.sort_index().to_csv(spi_data_fpath)
else:
    data = pd.read_csv(spi_data_fpath, index_col="Unnamed: 0")

data.set_index(keys=["Plant Code", "Prime Mover"], inplace=True)

data.groupby(level="Prime Mover")["Nameplate Capacity (MW)"].sum()

surplus_interconnect_by_pm = pd.DataFrame()

for surplus_threshold_fraction in surplus_threshold_fractions:
    pm_to_desc = prime_mover_to_desc()
    data = calculate_surplus_interconnect_factor(data, surplus_threshold_fraction)

    # Do not include zero generation
    if not include_zero_generation:
        for i in data[data["Net Generation (Megawatthours)"] == 0.0].index.to_list():
            data.loc[i, "Surplus Interconnect Factor"] = None

    # Do not include non-contiguous states
    if not include_non_continental:
        us_states = load_us_state_boundaries()

        non_continental = (set(data["State"].to_list())).difference(
            set(us_states["STUSPS"].to_list())
        )
        for n in non_continental:
            data = data[data["State"] != n]

    pm_to_tot_capac = {}
    for pm in set(data.index.get_level_values("Prime Mover").to_list()):
        pm_to_tot_capac[pm_to_desc[pm]] = data.xs(pm, level="Prime Mover")[
            "Surplus Interconnect Capacity (MW)"
        ].sum()

    tmp_df = pd.Series(pm_to_tot_capac).sort_index()
    tmp_df.name = f"{int(surplus_threshold_fraction*100):d}\%"

    surplus_interconnect_by_pm = pd.concat([surplus_interconnect_by_pm, tmp_df], axis=1)

# print(surplus_interconnect_by_pm.sort_values(by = "80\%", ascending=False).to_latex(float_format="%.2f", index=True))
# print(surplus_interconnect_by_pm.sum(axis=0).to_latex(float_format="%.2f"))
si_order = surplus_interconnect_by_pm.sort_values(
    by="80\%", ascending=False
).index.to_list()

# print("Total Capacity Per Prime Mover (MW)")
total_capacity = data.groupby(level="Prime Mover")["Nameplate Capacity (MW)"].sum()
# print((total_capacity.sort_values(ascending=False).rename(index = prime_mover_to_desc()).loc[si_order]).to_latex(float_format="%.2f", index=True))

# print("Total AEP Per Prime Mover (GWh/year)")
total_gen = (
    data.groupby(level="Prime Mover")["Net Generation (Megawatthours)"].sum() / 1e3
)
# print((total_gen.sort_values(ascending=False).rename(index = prime_mover_to_desc()).loc[si_order]).to_latex(float_format="%.2f", index=True))
avg_cf = data.groupby(level="Prime Mover")["Capacity Factor"].mean() * 100

weighted_numerator = data["Nameplate Capacity (MW)"] * data["Capacity Factor"]
total_capacity.rename(index=prime_mover_to_desc()).loc[si_order]

# weighted_avg_cf.name = "Weighted Avg CF"
# weighted_avg_cf = 100*(total_gen.rename(index = prime_mover_to_desc()).loc[si_order]*1e3/(8760*total_capacity.rename(index = prime_mover_to_desc()).loc[si_order]))
# weighted_avg_cf.name = "Weighted Avg CF"

summary_df = pd.concat(
    [
        total_capacity.rename(index=prime_mover_to_desc()).loc[si_order],
        total_gen.rename(index=prime_mover_to_desc()).loc[si_order],
        avg_cf.rename(index=prime_mover_to_desc()).loc[si_order],
    ],
    axis=1,
)
print(summary_df.to_latex(float_format="%.1f", index=True))
# print(pd.concat([total_capacity.rename(index = prime_mover_to_desc()).loc[si_order], total_gen.rename(index = prime_mover_to_desc()).loc[si_order]], axis=1).to_latex(float_format="%.2f", index=True))

# Make pie chart
fig, ax = plt.subplots(1, 1)
sizes_df = 100 * total_capacity / total_capacity.sum()
sizes_df.sort_values(ascending=False)
pm_to_color = make_prime_mover_cmap()
pm_to_c = {p: c for p, c in pm_to_color.items() if p in sizes_df.index.to_list()}
colors_ordered = [pm_to_c[p] for p in sizes_df.index.to_list()]
labels_ordered = [pm_to_desc[p] for p in sizes_df.index.to_list()]
# TODO: lump the ones with less than 5% net capacity together and make as external bar
ppi = ax.pie(
    sizes_df.values, labels=labels_ordered, autopct="%1.1f%%", colors=colors_ordered
)

fig.tight_layout()
fig.savefig(figure_dir / "net_capacity_piechart.png", bbox_inches="tight")
plt.close(fig)
# rotate so that first wedge is split by the x-axis

# Make bar charts
# group_bar_var = "Prime Mover"
# back_plot_var = "Nameplate Capacity (MW)"

total_capacity = data.groupby(level="Prime Mover")["Nameplate Capacity (MW)"].sum()
total_capacity.rename(index=pm_to_desc, inplace=True)
fig, ax = plt.subplots(1, 1, figsize=[6, 3])
bw = 0.6
b_spacing = 0.2
dx = (bw + b_spacing) / 2
x0 = bw / 2
x_vals = np.arange(x0, len(total_capacity) * dx + x0, dx)

nc = ax.bar(
    x_vals, total_capacity.loc[si_order].values, width=bw, label="Total Capacity"
)
ax.bar_label(nc, label_type="edge", fmt="%d", padding=1)
ax.bar_label(nc, label_type="edge", fmt="%d", padding=1)
# Full bar is total capacity

# Second bar is 80% surplus
# Third bar is 90% surplus
# Fourth bar is 100% surplus
ax.tick_params(labelsize=8.0)
ax.xaxis.label.set_fontsize(9.0)
ax.spines[["right", "top"]].set_visible(False)
