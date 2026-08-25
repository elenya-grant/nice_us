from datetime import datetime

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from nice import DATA_DIR, ROOT_DIR
from nice.plotting.plot_tools import make_discrete_color_dict
from nice.tools.eia_860_file_tools import load_eia_860
from nice.tools.geo_data_file_tools import load_us_state_boundaries
from nice.tools.geospatial import STATE_BORDERS, US_STATE_MAP
from nice.tools.rev_supply_curve_tools import (
    calc_distance,
    find_distance,
    load_reference_pv_supply_curve,
)


def create_eia_rev_mapper_file(
    data_year=2024, crs="EPSG:4326", plot_furthest_sites=False
):
    # takes about 5-6 min

    # Plant ID 3750 is said to be in VT but is actually in NH
    # Plant ID 1109 is said to be in IA but is actually in IL
    # Plant ID 64670 is said to be in AR but is actually in CA

    # Distance from center to corner of 11.5x11.5km grid cell
    max_distance = np.sqrt((11.5**2) + (11.5**2)) / 2

    # This is the cleaned-up version of what existed in:
    # - nice/analysis/eia_rev_siting.py
    # - nice/plotting/plot_rev_grid.py
    # - nice/analysis/eia_rev_siting_follow_on.py

    # Filepath to save the file to
    out_fpath = (
        DATA_DIR
        / "nice_data_aggregated"
        / f"EIA_{data_year}_to_Rev_plant_id_mapper.csv"
    )

    # Load EIA data and format
    plant = load_eia_860("Plant", year=data_year)
    plant["Plant Code"] = plant["Plant Code"].astype(int)  # 16132
    plant.set_index(keys="Plant Code", inplace=True)
    plant["Latitude"] = pd.to_numeric(plant["Latitude"], errors="coerce")
    plant["Longitude"] = pd.to_numeric(plant["Longitude"], errors="coerce")
    # Convert EIA lat/lon to geodataframe
    plant_geo = gpd.GeoDataFrame(
        plant,
        geometry=gpd.points_from_xy(
            plant.Longitude,
            plant.Latitude,
            crs=crs,
        ),
    )
    # Remove plants without specified Lat/Lon
    nan_plant_ids = list(
        set(plant[plant["Latitude"].isna()].index.to_list())
        & set(plant[plant["Longitude"].isna()].index.to_list())
    )
    # 28 plants w/o lat/lon data
    plant_geo.drop(index=nan_plant_ids, inplace=True)

    # Load rev grid cells and data
    rev_gpd = load_reference_pv_supply_curve(crs=crs)
    rev_gpd["state"] = rev_gpd["state"].replace(to_replace=US_STATE_MAP)

    common_states = set(plant_geo["State"].to_list()) & set(rev_gpd["state"].to_list())

    # Remove EIA sites that are in states that aren't included in the rev data
    plant_geo_noncommon_states = set(plant_geo["State"].to_list()) - common_states
    for n in list(plant_geo_noncommon_states):
        plant_geo = plant_geo[plant_geo["State"] != n]

    # Load the state boundaries
    us_states = load_us_state_boundaries()

    t_start = datetime.now()

    # plant ID to rev ID
    # plant_to_rev_id = {}
    # plant_id_to_recheck = []
    # plant_id_multi_rev_cells = []

    # Initialize the dataframe containing EIA sites and
    # the corresponding rev grid cell
    plant_to_rev_id_df = pd.DataFrame(
        index=plant_geo.index.to_list(),
        columns=[
            "State",
            "Found method",
            "EIA Plant Code",
            "REV SC GID",
            "Distance to Rev GID (km)",
        ],
    )

    for state in list(common_states):
        plant_state = plant_geo[plant_geo["State"] == state]

        # ids_missing = []
        for plant_id in plant_state.index.to_list():
            # Update the state and add EIA plant code to the df
            plant_to_rev_id_df.loc[plant_id, "State"] = state
            plant_to_rev_id_df.loc[plant_id, "EIA Plant Code"] = plant_id

            # Determine which rec grid cells contain the plant location
            rev_pt = rev_gpd["geometry"][
                rev_gpd["geometry"].contains(plant_state.loc[plant_id]["geometry"])
            ]

            if len(rev_pt) == 0:
                # no rev cell contains the plant
                # calculate distance to nearest rev site
                # plant_id_to_recheck.append(plant_id)
                # ids_missing.append(plant_id)

                # Check that the site is within this state!
                check_state = us_states[
                    us_states.contains(plant_geo.loc[plant_id]["geometry"])
                ].STUSPS.to_list()

                if bool(check_state) and check_state[0] != state:
                    # EIA state was incorrect
                    # get bounding states and rev sites within the correct state
                    rev_data_state = rev_gpd[rev_gpd["state"] == check_state[0]]
                    bounding_states = STATE_BORDERS.get(check_state[0], [])
                    plant_to_rev_id_df.loc[plant_id, "State"] = check_state[0]
                    print(
                        f"Plant ID {plant_id} is said to be in state {state} "
                        f"but is actually in state {check_state[0]}"
                    )
                else:
                    # EIA state was correct
                    # get bounding states and rev sites within that state
                    bounding_states = STATE_BORDERS.get(state, [])
                    rev_data_state = rev_gpd[rev_gpd["state"] == state]

                distance_to_sites = rev_data_state.apply(
                    find_distance,
                    axis=1,
                    args=(
                        plant_geo.loc[plant_id]["Latitude"],
                        plant_geo.loc[plant_id]["Longitude"],
                    ),
                )

                if distance_to_sites.min() > max_distance:
                    min_distance = distance_to_sites.min()
                    min_distance_id = distance_to_sites.idxmin()
                    found_method = 1

                    for b_state in bounding_states:
                        rev_data_bounding_state = rev_gpd[rev_gpd["state"] == b_state]
                        distances = rev_data_bounding_state.apply(
                            find_distance,
                            axis=1,
                            args=(
                                plant_geo.loc[plant_id]["Latitude"],
                                plant_geo.loc[plant_id]["Longitude"],
                            ),
                        )
                        if distances.min() < min_distance:
                            min_distance = distances.min()
                            min_distance_id = distances.idxmin()
                            found_method = 3

                    plant_to_rev_id_df.loc[plant_id, "REV SC GID"] = min_distance_id
                    plant_to_rev_id_df.loc[plant_id, "Found method"] = found_method
                    plant_to_rev_id_df.loc[plant_id, "Distance to Rev GID (km)"] = (
                        min_distance
                    )

                else:
                    plant_to_rev_id_df.loc[plant_id, "REV SC GID"] = (
                        distance_to_sites.idxmin()
                    )
                    plant_to_rev_id_df.loc[plant_id, "Found method"] = 1
                    plant_to_rev_id_df.loc[plant_id, "Distance to Rev GID (km)"] = (
                        distance_to_sites.min()
                    )

            elif len(rev_pt) == 1:
                # found 1 matching site
                rev_id = rev_pt.index.to_list()[0]
                # plant_to_rev_id[plant_id] = rev_pt.index.to_list()[0]
                plant_to_rev_id_df.loc[plant_id, "REV SC GID"] = rev_pt.index.to_list()[
                    0
                ]
                plant_to_rev_id_df.loc[plant_id, "Found method"] = 0
                plant_to_rev_id_df.loc[plant_id, "Distance to Rev GID (km)"] = (
                    calc_distance(
                        rev_gpd.loc[rev_id]["latitude"],
                        rev_gpd.loc[rev_id]["longitude"],
                        plant_state.loc[plant_id]["Latitude"],
                        plant_state.loc[plant_id]["Longitude"],
                    )
                )

            else:
                # found multiple
                distance_to_sites = rev_gpd.loc[rev_pt.index.to_list()].apply(
                    find_distance,
                    axis=1,
                    args=(
                        plant_geo.loc[plant_id]["Latitude"],
                        plant_geo.loc[plant_id]["Longitude"],
                    ),
                )
                plant_to_rev_id_df.loc[plant_id, "REV SC GID"] = (
                    distance_to_sites.idxmin()
                )
                plant_to_rev_id_df.loc[plant_id, "Found method"] = 2
                plant_to_rev_id_df.loc[plant_id, "Distance to Rev GID (km)"] = (
                    distance_to_sites.min()
                )

                # plant_id_multi_rev_cells.append(plant_id)
                # plant_to_rev_id[plant_id] = rev_pt.index.to_list()

    t_end = datetime.now()
    time_to_run = (t_end - t_start).seconds / 60
    print(f"done, took {time_to_run:.2f} minutes")

    plant_to_rev_id_df.index.name = "Plant Code"
    plant_to_rev_id_df.sort_index(inplace=True)
    plant_geo.sort_index(inplace=True)
    plant_geo.rename(
        columns={"Longitude": "Plant Longitude", "Latitude": "Plant Latitude"},
        inplace=True,
    )
    rev_gpd.rename(
        columns={
            "longitude": "REV Longitude",
            "latitude": "REV Latitude",
            "capacity_ac_mw": "REV PV Capacity (MW-AC)",
            "capacity_dc_mw": "REV PV Capacity (MW-DC)",
        },
        inplace=True,
    )
    rev_gpd["area_developable_fraction"] = rev_gpd["area_developable_sq_km"] / (11.5**2)
    rev_data_cols = [
        "area_developable_sq_km",
        "area_developable_fraction",
        "REV Longitude",
        "REV Latitude",
        "REV PV Capacity (MW-DC)",
        "REV PV Capacity (MW-AC)",
    ]
    eia_data_cols = ["Plant Longitude", "Plant Latitude"]

    # Add additional EIA data to the final df
    mapper_df = pd.concat(
        [plant_to_rev_id_df, plant_geo.loc[plant_to_rev_id_df.index][eia_data_cols]],
        axis=1,
    )
    # Add additional rev data to the final df
    mapper_df.reset_index(drop=False, inplace=True)
    mapper_df.set_index(keys=["REV SC GID"], inplace=True)
    rev_id_indx = plant_to_rev_id_df["REV SC GID"].to_list()
    multi_eia_to_rev = [k for k in rev_id_indx if rev_id_indx.count(k) > 1]
    single_eia_to_rev = list(set(rev_id_indx) - set(multi_eia_to_rev))

    rev_repeated_df = pd.DataFrame(index=mapper_df.index, columns=rev_data_cols)
    rev_repeated_df.loc[single_eia_to_rev] = rev_gpd.loc[single_eia_to_rev]
    for rev_id in multi_eia_to_rev:
        rev_tmp_df = [
            rev_gpd.loc[rev_id][rev_data_cols] for i in range(rev_id_indx.count(rev_id))
        ]
        tmp_df = pd.concat(rev_tmp_df, axis=1)
        rev_repeated_df.loc[rev_id] = tmp_df.T

    mapper_df = pd.concat(
        [mapper_df.loc[rev_id_indx], rev_repeated_df.loc[rev_id_indx]], axis=1
    )
    mapper_df.reset_index(drop=False, inplace=True)
    mapper_df.set_index(keys=["Plant Code"], inplace=True)
    mapper_df.to_csv(out_fpath)

    if plot_furthest_sites:
        recheck_pids = plant_to_rev_id_df[
            plant_to_rev_id_df["Distance to Rev GID (km)"] > max_distance
        ].index.to_list()

        print(f"{len(recheck_pids)} sites that are far from a REV site")
        fig, ax = plt.subplots(1, 1, figsize=[12, 12])

        figfpath = ROOT_DIR.parent / "map_figures" / "far_away_sites_map.png"

        us_states = load_us_state_boundaries()
        us_states.boundary.plot(ax=ax, alpha=0.5, edgecolor="tab:gray", linewidth=0.625)

        ids_to_colors = make_discrete_color_dict(recheck_pids, cmap_name="hsv")

        ax.scatter(
            x=rev_gpd["longitude"],
            y=rev_gpd["latitude"],
            s=0.20,
            c="tab:blue",
            alpha=0.10,
            # alpha=0.75,
        )

        colors = [ids_to_colors[i] for i in recheck_pids]
        ax.scatter(
            x=plant_geo.loc[recheck_pids]["Longitude"],
            y=plant_geo.loc[recheck_pids]["Latitude"],
            s=0.6,
            c=colors,
            alpha=1.0,
            marker="o",
            linewidths=0.25,
            # alpha=0.75,
        )

        rev_site_recheck = plant_to_rev_id_df.loc[recheck_pids]["REV SC GID"].to_list()

        ax.scatter(
            x=rev_gpd.loc[rev_site_recheck]["longitude"],
            y=rev_gpd.loc[rev_site_recheck]["latitude"],
            s=0.4,
            c=colors,
            alpha=0.60,
            marker="*",
            linewidths=0.25,
            # alpha=0.75,
        )

        for i in recheck_pids:
            rev_id = plant_to_rev_id_df.loc[i, "REV SC GID"]
            x_vals = [plant_geo.loc[i]["Longitude"], rev_gpd.loc[rev_id]["longitude"]]
            y_vals = [plant_geo.loc[i]["Latitude"], rev_gpd.loc[rev_id]["latitude"]]
            ax.plot(x_vals, y_vals, lw=0.5, color=ids_to_colors[i])

        ax.spines[["right", "top", "bottom", "left"]].set_visible(False)
        ax.get_xaxis().set_ticks([])
        ax.get_yaxis().set_ticks([])

        fig.savefig(figfpath, bbox_inches="tight", dpi=400, pad_inches=0.0)

        plt.close(fig)

    return mapper_df
