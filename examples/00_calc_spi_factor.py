import calendar
from pathlib import Path

import matplotlib as mpl

from nice import ROOT_DIR
from nice.analysis.generate_spi_data import generate_annual_and_monthly_spi_from_eia
from nice.plotting.map_plot import plot_scatter_map_basic
from nice.plotting.sic_monthly_plots import plot_monthly_surplus_interconnection_factor
from nice.plotting.sic_summary_plots import stacked_bar_capacity
from nice.plotting.sic_violin_plots import violin_plot_of_sic
from nice.tools.eia_860_file_tools import (
    make_prime_mover_cmap,
    prime_mover_to_desc,
    storage_prime_mover_to_desc,
)

# Calculate SPI from 80%
include_storage_techs = False
spi_threshold = 0.8
df = generate_annual_and_monthly_spi_from_eia(surplus_threshold_fraction=spi_threshold)


# Create figures of each figure folder if needed
bar_figure_dir = ROOT_DIR.parent / "figures" / "bar_charts"

m12_figure_dir = ROOT_DIR.parent / "figures" / "monthly_figures"

violin_figure_dir = ROOT_DIR.parent / "figures" / "violin_figures"

map_figure_dir = ROOT_DIR.parent / "figures" / "map_figures"

for dir in [bar_figure_dir, m12_figure_dir, violin_figure_dir, map_figure_dir]:
    if not dir.exists():
        Path(dir).mkdir(exist_ok=True, parents=True)

# Plot bar charts
stacked_bar_capacity(df, include_storage_techs, bar_figure_dir, spi_threshold)

# Plot violin plots
make_violin_plots = True
pm_types_violin = ["ST", "GT", "WT", "PV", "CT"]
for pm in pm_types_violin:
    violin_plot_of_sic(df, pm, violin_figure_dir, spi_threshold)

# Plot maps
pm_types_map = ["ST", "GT", "WT", "PV"]
make_maps = True
vmax = 400.0
vmin = 1.0
cmap_name = "viridis_r"
cmap_under = "tab:olive"
cmap_over = "k"

pm_to_desc = prime_mover_to_desc()
cmap = mpl.colormaps[cmap_name]
cmap = cmap.with_extremes(over=cmap_over, bad="red")
cmap.set_bad("red", alpha=1.0)
norm = mpl.colors.Normalize(vmin=vmin, vmax=vmax, clip=False)
for pm in pm_types_map:
    cblabel = f"{pm_to_desc[pm]} \nSurplus Interconnect Capacity (MW)"
    map_figfpath = map_figure_dir / f"new--{pm}_{int(spi_threshold*100)}_percent"
    plot_scatter_map_basic(
        df.swaplevel().loc[pm],
        "Surplus Interconnect Capacity (MW)",
        cblabel,
        cmap,
        norm,
        map_figfpath,
    )

# Plot monthly scatters
months_to_n_days = {
    calendar.month_name[i]: calendar.monthrange(2024, i)[1] for i in range(1, 13)
}

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

plot_legend = False
plot_legend_separately = False
plot_labels_as_text = True
fig_desc = "text_labels"

plot_monthly_surplus_interconnection_factor(
    spif_per_pm,
    m12_figure_dir,
    include_storage_techs,
    plot_labels_as_text,
    plot_legend_separately,
    plot_legend,
    fig_desc,
    spi_threshold,
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
