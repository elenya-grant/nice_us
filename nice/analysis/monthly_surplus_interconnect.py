import calendar
from pathlib import Path

import matplotlib as mpl
import pandas as pd

from nice import DATA_DIR, ROOT_DIR
from nice.plotting.map_plot import plot_scatter_map_basic
from nice.plotting.sic_monthly_plots import plot_monthly_surplus_interconnection_factor
from nice.plotting.sic_summary_plots import stacked_bar_capacity
from nice.plotting.sic_violin_plots import violin_plot_of_sic
from nice.tools.create_data import create_surplus_interconnect_data
from nice.tools.create_monthly_data import do_monthly_stuff
from nice.tools.eia_860_file_tools import (
    make_prime_mover_cmap,
    prime_mover_to_desc,
    storage_prime_mover_to_desc,
)
from nice.tools.spi_tools import calc_spi_factor

bar_figure_dir = ROOT_DIR.parent / "bar_charts"

figure_dir = ROOT_DIR.parent / "monthly_figures"

violin_figure_dir = ROOT_DIR.parent / "violin_figures"

map_figure_dir = ROOT_DIR.parent / "map_figures"

surplus_threshold_fraction = 1.0  # 0.80

# CF >= means no surplus interconnect
full_utilization_threshold = 1.0
include_storage_techs = False


# --- BELOW IS FOR MONTHLY SCATTERS ---
make_monthly_scatters = True
# below is to make a separate legend
# plot_legend = False
# plot_legend_separately = True
# plot_labels_as_text = False
# fig_desc = "no_legend"

# below is so that the label is next to the plot
plot_legend = False
plot_legend_separately = False
plot_labels_as_text = True
fig_desc = "text_labels"

# --- BELOW IS FOR violins ---
make_violin_plots = True
pm_types_violin = ["ST", "GT", "WT", "PV", "CT"]

# --- BELOW IS FOR BAR CHART ---
make_bar_chart = True

# --- BELOW IS FOR MAPS ---
pm_types_map = ["ST", "GT", "WT", "PV"]
make_maps = True
vmax = 400.0
vmin = 1.0
cmap_name = "viridis_r"
cmap_under = "tab:olive"
cmap_over = "k"


output_data_dir = DATA_DIR / "nice_data_aggregated"
spi_data_fpath = output_data_dir / "summary_data_missing_is_None_2024.csv"
spi_monthly_data_fpath = (
    output_data_dir / "monthly_Netgen_surplus_interconnect_2024.csv"
)

if not output_data_dir.exists():
    Path(output_data_dir).mkdir(exist_ok=True, parents=True)

if not figure_dir.exists():
    Path(figure_dir).mkdir(exist_ok=True, parents=True)

if not violin_figure_dir.exists():
    Path(violin_figure_dir).mkdir(exist_ok=True, parents=True)

if not bar_figure_dir.exists():
    Path(bar_figure_dir).mkdir(exist_ok=True, parents=True)

if not spi_monthly_data_fpath.is_file():
    print("Running monthly")
    m12_data = do_monthly_stuff()
    m12_data.sort_index().to_csv(spi_monthly_data_fpath)
    print("Completed monthly")
else:
    m12_data = pd.read_csv(spi_monthly_data_fpath, index_col="Unnamed: 0")


if not spi_data_fpath.is_file():
    print("Running summary")
    data = create_surplus_interconnect_data(missing_val=None)
    data.sort_index().to_csv(spi_data_fpath)
    print("Completed summary")
else:
    data = pd.read_csv(spi_data_fpath, index_col="Unnamed: 0")

m12_data.index.name = "Plant Code"
m12_data.reset_index(drop=False, inplace=True)
m12_data.set_index(keys=["Plant Code", "Prime Mover"], inplace=True)
data.set_index(keys=["Plant Code", "Prime Mover"], inplace=True)


data["Capacity Factor"] = data["Net Generation (Megawatthours)"] / (
    data["Nameplate Capacity (MW)"] * 8760
)

for i in data[data["Capacity Factor"] > 1.0].index.to_list():
    data.loc[i, "Capacity Factor"] = 1.0

# Clip to 0.0
for i in data[data["Capacity Factor"] < 0.0].index.to_list():
    data.loc[i, "Capacity Factor"] = 0.0

data["Surplus Interconnect Factor"] = 1.0 - data["Capacity Factor"]

for i in data[data["Capacity Factor"] >= full_utilization_threshold].index.to_list():
    data.loc[i, "Surplus Interconnect Factor"] = 0.0
for i in data[data["Capacity Factor"] > surplus_threshold_fraction].index.to_list():
    data.loc[i, "Surplus Interconnect Factor"] = 0.0

data["Surplus Interconnect Capacity (MW)"] = (
    data["Nameplate Capacity (MW)"] * data["Surplus Interconnect Factor"]
)


shared_indices = (set(m12_data.index.to_list())).intersection(set(data.index.to_list()))
shared_indx = (
    pd.MultiIndex.from_tuples(list(shared_indices), names=["Plant Code", "Prime Mover"])
).sort_values()
df = pd.concat([data.loc[shared_indx], m12_data.loc[shared_indx]], axis=1)

column_fmt = "Netgen {month}"
months_to_n_days = {
    calendar.month_name[i]: calendar.monthrange(2024, i)[1] for i in range(1, 13)
}
m12_cols = [column_fmt.format(month=m) for m in list(months_to_n_days.keys())]

for month, n_days in months_to_n_days.items():
    hours_per_month = n_days * 24
    df[f"{month} Capacity Factor"] = df[column_fmt.format(month=month)] / (
        df["Nameplate Capacity (MW)"] * hours_per_month
    )

    calc_spi_factor(
        df,
        f"{month} Capacity Factor",
        f"{month} Surplus Interconnect Factor",
        surplus_threshold_fraction,
        full_utilization_threshold=full_utilization_threshold,
    )

    df[f"{month} Surplus Interconnect Capacity (MW)"] = (
        df["Nameplate Capacity (MW)"] * df[f"{month} Surplus Interconnect Factor"]
    )


if make_bar_chart:
    stacked_bar_capacity(
        df, include_storage_techs, bar_figure_dir, surplus_threshold_fraction
    )

if make_violin_plots:
    pm_types_violin = ["ST", "GT", "WT", "PV", "CT"]
    for pm in pm_types_violin:
        violin_plot_of_sic(df, pm, violin_figure_dir, surplus_threshold_fraction)

if make_maps:
    pm_to_desc = prime_mover_to_desc()
    cmap = mpl.colormaps[cmap_name]
    cmap = cmap.with_extremes(over=cmap_over, bad="red")
    cmap.set_bad("red", alpha=1.0)
    norm = mpl.colors.Normalize(vmin=vmin, vmax=vmax, clip=False)
    for pm in pm_types_map:
        cblabel = f"{pm_to_desc[pm]} \nSurplus Interconnect Capacity (MW)"
        map_figfpath = (
            map_figure_dir / f"new--{pm}_{int(surplus_threshold_fraction*100)}_percent"
        )
        plot_scatter_map_basic(
            df.swaplevel().loc[pm],
            "Surplus Interconnect Capacity (MW)",
            cblabel,
            cmap,
            norm,
            map_figfpath,
        )


if make_monthly_scatters:
    m12_cf_cols = [f"{m} Capacity Factor" for m in list(months_to_n_days.keys())]
    m12_spif_cols = [
        f"{m} Surplus Interconnect Factor" for m in list(months_to_n_days.keys())
    ]
    m12_spi_cap_cols = [
        f"{m} Surplus Interconnect Capacity (MW)" for m in list(months_to_n_days.keys())
    ]

    pm_cmap = make_prime_mover_cmap()
    pm_to_desc = prime_mover_to_desc()
    storage_pm_to_desc = storage_prime_mover_to_desc()

    spif_per_pm = df.groupby(level="Prime Mover")[m12_spif_cols].mean().copy()
    spi_cap_per_pm = df.groupby(level="Prime Mover")[m12_spi_cap_cols].sum().copy()

    plot_monthly_surplus_interconnection_factor(
        spif_per_pm,
        figure_dir,
        include_storage_techs,
        plot_labels_as_text,
        plot_legend_separately,
        plot_legend,
        fig_desc,
        surplus_threshold_fraction,
    )

# Estimate total surplus
storage_pm_to_desc = storage_prime_mover_to_desc()
if include_storage_techs:
    installed_capac = df["Nameplate Capacity (MW)"].sum()
    tot_surp = df["Surplus Interconnect Capacity (MW)"].sum()

else:
    sic = (
        df.groupby(level="Prime Mover")["Surplus Interconnect Capacity (MW)"]
        .sum()
        .copy()
    )
    tot_capac = df.groupby(level="Prime Mover")["Nameplate Capacity (MW)"].sum().copy()
    pm_list = [k for k in sic.index.to_list() if k not in storage_pm_to_desc]
    tot_surp = sic.loc[pm_list].sum()
    installed_capac = tot_capac.loc[pm_list].sum()

print(f"{installed_capac/1e3:.1f} GW of installed capacity")
print(f"{tot_surp/1e3:.1f} GW of surplus interconnection")
print(f"{100*(tot_surp/installed_capac):.1f} percent")
