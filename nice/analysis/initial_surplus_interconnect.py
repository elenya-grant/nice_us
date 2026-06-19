from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from nice import DATA_DIR, ROOT_DIR
from nice.plotting.map_plot import plot_scatter_map_basic
from nice.tools.create_data import create_surplus_interconnect_data
from nice.tools.create_monthly_data import do_monthly_stuff
from nice.tools.eia_860_file_tools import prime_mover_to_desc
from nice.tools.geo_data_file_tools import convert_df_to_gdf, load_us_state_boundaries

figure_dir = ROOT_DIR.parent / "map_figures"

surplus_threshold_fraction = 0.80

# CF >= means no surplus interconnect
full_utilization_threshold = 1.0
include_storage_techs = True

output_data_dir = DATA_DIR / "nice_data_aggregated"
# spi_data_fpath = output_data_dir/"surplus_interconnect_data_2024.csv"
spi_data_fpath = output_data_dir / "surplus_interconnect_data_missing_is_None_2024.csv"
spi_monthly_data_fpath = (
    output_data_dir / "monthly_Netgen_surplus_interconnect_2024.csv"
)

if not output_data_dir.exists():
    Path(output_data_dir).mkdir(exist_ok=True, parents=True)

if not figure_dir.exists():
    Path(figure_dir).mkdir(exist_ok=True, parents=True)

if not spi_data_fpath.is_file():
    data = create_surplus_interconnect_data(missing_val=None)
    data.sort_index().to_csv(spi_data_fpath)
else:
    data = pd.read_csv(spi_data_fpath, index_col="Unnamed: 0")

if not spi_monthly_data_fpath.is_file():
    m12_data = do_monthly_stuff()
    m12_data.sort_index().to_csv(spi_monthly_data_fpath)
else:
    m12_data = pd.read_csv(spi_monthly_data_fpath, index_col="Unnamed: 0")

# 778 plant ids are in perf and storage,
data["Capacity Factor"] = data["Net Generation (Megawatthours)"] / (
    data["Nameplate Capacity (MW)"] * 8760
)
data.set_index(keys=["Plant Code", "Prime Mover"], inplace=True)
# 54808 has CT but not CA
# 56309 has CA but not CT (has ST, CS, and IC)

# all_pms = data["Prime Mover"].to_list()
# {p:all_pms.count(p) for p in set(all_pms)}
# Clip to 1.0
for i in data[data["Capacity Factor"] > 1.0].index.to_list():
    data.loc[i, "Capacity Factor"] = 1.0

# Clip to 0.0
for i in data[data["Capacity Factor"] < 0.0].index.to_list():
    data.loc[i, "Capacity Factor"] = 0.0

data["Surplus Interconnect Factor"] = 1.0 - data["Capacity Factor"]

# Set interconnect factor to 0.0 for fully utilized plants
for i in data[data["Capacity Factor"] >= full_utilization_threshold].index.to_list():
    data.loc[i, "Surplus Interconnect Factor"] = 0.0
for i in data[data["Capacity Factor"] > surplus_threshold_fraction].index.to_list():
    data.loc[i, "Surplus Interconnect Factor"] = 0.0

# Set Interconnect Factor to 0.0 if it Generates Nothing
for i in data[data["Net Generation (Megawatthours)"] == 0.0].index.to_list():
    data.loc[i, "Surplus Interconnect Factor"] = None

if not include_storage_techs:
    data = data[data["Is Storage"] is False]

data["Surplus Interconnect Capacity (MW)"] = (
    data["Nameplate Capacity (MW)"] * data["Surplus Interconnect Factor"]
)
data["Max Surplus Interconnect Generation (MWh)"] = (
    data["Surplus Interconnect Capacity (MW)"] * 8760
)

# 7 NERC Regions, 66 Balancing Authorities
data["NERC Region"].fillna("NA", inplace=True)
data["Balancing Authority Code"].fillna("NA", inplace=True)


cmap_name = "viridis_r"
cmap_under = "tab:olive"
cmap_over = "red"
cmap_bad = "orange"

vmax = np.nanpercentile(data["Surplus Interconnect Capacity (MW)"].values, 97.5)
vmin = np.nanpercentile(data["Surplus Interconnect Capacity (MW)"].values, 2.5)
cmap = mpl.colormaps[cmap_name]
cmap = cmap.with_extremes(over=cmap_over, under=cmap_under, bad="red")
cmap.set_bad("red", alpha=1.0)
norm = mpl.colors.Normalize(vmin=vmin, vmax=vmax, clip=False)

us_states = load_us_state_boundaries()

pm_to_desc = prime_mover_to_desc()
# Remove non-continental states
non_continental = (set(data["State"].to_list())).difference(
    set(us_states["STUSPS"].to_list())
)
for n in non_continental:
    data = data[data["State"] != n]

pm_to_tot_capac = {}
for pm in set(data.index.get_level_values("Prime Mover").to_list()):
    gdf = convert_df_to_gdf(data.xs(pm, level="Prime Mover").copy())
    pm_to_tot_capac[pm_to_desc[pm]] = data.xs(pm, level="Prime Mover")[
        "Surplus Interconnect Capacity (MW)"
    ].sum()

    fig, ax = plt.subplots(1, 1, figsize=[6, 6])

    us_states.boundary.plot(ax=ax, alpha=0.5, edgecolor="tab:gray", linewidth=0.325)

    sc = ax.scatter(
        x=gdf["Longitude"],
        y=gdf["Latitude"],
        s=0.50,
        c=gdf["Surplus Interconnect Capacity (MW)"].values,
        cmap=cmap,
        norm=norm,
        alpha=0.90,
    )
    cb = fig.colorbar(
        sc,
        ax=ax,
        label=f"{pm_to_desc[pm]} \nSurplus Interconnect Capacity (MW)",
        location="bottom",
        orientation="horizontal",
        pad=0.0,
        shrink=0.75,
        extend="both",
    )
    cb.ax.tick_params(labelsize=8.0)
    cb.ax.xaxis.label.set_fontsize(9.0)

    ax.spines[["right", "top", "bottom", "left"]].set_visible(False)
    ax.get_xaxis().set_ticks([])
    ax.get_yaxis().set_ticks([])

    figfpath = (
        figure_dir
        / f"{pm_to_desc[pm].replace(' ', '_')}_surplus_interconnect_capacity_{surplus_threshold_fraction*100:d}percent.png"
    )

    fig.savefig(figfpath, bbox_inches="tight", dpi=300, pad_inches=0.0)

    plt.close(fig)

# PLOT ALL OF THEM
plot_scatter_map_basic(
    data,
    "Surplus Interconnect Capacity (MW)",
    "Surplus Interconnect Capacity (MW)",
    cmap,
    norm,
    figure_dir
    / f"all_surplus_interconnect_capacity_{surplus_threshold_fraction*100:d}percent.png",
)

print(f"{surplus_threshold_fraction*100:.1f}% capacity factor is fully utilized")
print(pd.Series(pm_to_tot_capac).sort_index().to_latex(float_format="%.2f", index=True))
print(f"{pd.Series(pm_to_tot_capac).sum()} MW total")
