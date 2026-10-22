"""Plot illustrative site NPV and battery size on a contiguous-US map.

Run with ``python plot_npv_battery_map.py``. Edit ``SITES`` to use different
coordinates, NPV values (USD millions), or battery ratings (MW).
"""

from pathlib import Path

import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D
from nice import LIBRARY_DIR

from pathlib import Path

ROOT = Path(__file__).resolve().parent
BASEMAP = ROOT / "figures" / "basemap" / "cb_2022_us_state_20m.zip"
MAP_CRS = 5070
NON_CONTIGUOUS_STATES = {"AK", "HI", "PR", "GU", "VI", "MP", "AS"}

# read in site data
plant_types = [
    "thermal",
    "one_axis_solar",
    "fixed_solar",
    "wind"
    ]
added = "battery"

outputs_dir = Path(LIBRARY_DIR) / "h2i_sweep_0/"
            

def plot_sites_on_map(SITES, plot_variable)->None:
    sites = gpd.GeoDataFrame(
        SITES,
        geometry=gpd.points_from_xy(
            [site["longitude"] for site in SITES],
            [site["latitude"] for site in SITES],
        ),
        crs="EPSG:4326",
    ).to_crs(MAP_CRS)
    states = gpd.read_file(BASEMAP)
    states = states[~states["STUSPS"].isin(NON_CONTIGUOUS_STATES)].to_crs(MAP_CRS)

    figure, axis = plt.subplots(figsize=(9, 6), constrained_layout=True)
    states.plot(ax=axis, facecolor="#F4F4F2", edgecolor="#9A9A9A", linewidth=0.45)

    marker_area_per_mw = 2.0
    scatter = axis.scatter(
        sites.geometry.x,
        sites.geometry.y,
        c=[site[plot_variable] for site in SITES],
        s=[site["battery_mw"] * marker_area_per_mw for site in SITES],
        cmap="viridis",
        edgecolor="gray",
        linewidth=0.1,
        zorder=3,
    )
    colorbar = figure.colorbar(scatter, ax=axis, fraction=0.03, pad=0.02, shrink=0.72)
    colorbar.set_label(plot_variable)

    # for point, site in zip(sites.geometry, SITES):
    #     axis.annotate(
    #         site["facility"],
    #         (point.x, point.y),
    #         xytext=(6, 5),
    #         textcoords="offset points",
    #         fontsize=8,
    #         color="#222222",
    #     )

    size_examples = (10, 50, 150, 200)
    size_handles = [
        Line2D(
            [],
            [],
            marker="o",
            linestyle="none",
            markerfacecolor="#777777",
            markeredgecolor="black",
            markersize=np.sqrt(rating * marker_area_per_mw),
            label=f"{rating} MW",
        )
        for rating in size_examples
    ]

    # circles in ledgend are overlapping spread out legend
    axis.legend(
        handles=size_handles,
        title="Battery rating",
        loc="lower left",
        frameon=True,
        facecolor="white",
        edgecolor="#D8D8D8",
        labelspacing=1.1,  # increase spacing between legend entries
    )
    # axis.legend(
    #     handles=size_handles,
    #     title="Battery rating",
    #     title_fontsize='12',
    #     loc="lower left",
    #     frameon=True,
    #     facecolor="white",
    #     edgecolor="#D8D8D8",
    # )
    axis.set_title(f"{plot_variable}: {plant_type} with {added}")
    axis.set_axis_off()
    axis.set_aspect("equal")

    # plt.show()
    plt.savefig(outputs_dir / f"existing_{plant_type}_add_{added}/{plot_variable}_{plant_type}_{added}.png")

for plant_type in plant_types:
    output_dirs = {
    "fixed_solar": "outputs_subset0",
    "one_axis_solar": "outputs_subset0_abcd",
    "wind": "outputs_subset_abcd",
    "thermal": "outputs_subset0_ab"
    }
    output_path = Path(LIBRARY_DIR) / "h2i_sweep_0" / f"existing_{plant_type}_add_{added}"/output_dirs[plant_type] / "cases_positive_npv.csv"
    if not output_path.exists():
        continue
    df = pd.read_csv(output_path)
# column "site.latitude (deg)" --> "latitude"
# column "site.longitude (deg)" --> "longitude"
# column "finance_subgroup_added_electricity.NPV_electricity (USD)" --> "npv_musd" (divide by 1e6 to convert to USD millions)
# column "battery.max_charge_rate (kW)" --> "battery_mw" (divide by 1000 to convert to MW)

    df = df.rename(
        columns={
            "site.latitude (deg)": "latitude",
            "site.longitude (deg)": "longitude",
            "finance_subgroup_added_electricity.NPV_electricity (USD)": "npv_musd",
            "battery.max_charge_rate (kW)": "battery_mw",
            "grid_sell.plant_code (unitless)": "facility",
            "finance_subgroup_added_electricity.irr_electricity (percent)": "irr_electricity",
        }
    )
    df["battery_mw"] = df["battery_mw"] / 1000
    df["npv_musd"] = df["npv_musd"] / 1e6
    df["irr_electricity"] = df["irr_electricity"] * 100
    
    # remove any duplicate facilities with the smaller battery rating
    df = df.sort_values("npv_musd", ascending=False).drop_duplicates("facility")

    # SITES = [
    #     {"site": "Duluth", "latitude": 46.7867, "longitude": -92.1005, "npv_musd": 42, "battery_mw": 80},
    #     {"site": "Phoenix", "latitude": 33.4484, "longitude": -112.0740, "npv_musd": 61, "battery_mw": 150},
    # ]

    SITES = df.to_dict(orient="records")
    plot_sites_on_map(SITES, "npv_musd")
    plot_sites_on_map(SITES, "irr_electricity")
