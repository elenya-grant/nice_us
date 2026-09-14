import numpy as np
import pandas as pd

from nice import DATA_DIR, LIBRARY_DIR
from nice.tools.eia_860_file_tools import load_eia_860


def convert_to_type(df, new_col, old_col, data_type):
    df[new_col] = df[old_col].astype(data_type)
    return df


def make_existing_wind_plant_sitelist(data_year=2025):
    # sitelist_desc = "rev_pv_capac"
    output_sitelist_fpath = (
        LIBRARY_DIR / "h2i" / f"existing_wind_plant_sitelist_{data_year}.csv"
    )

    # Load EIA/REV site mapping
    rev_mapper_fpath = (
        DATA_DIR
        / "nice_data_aggregated"
        / f"EIA_{data_year}_to_Rev_plant_id_mapper.csv"
    )
    rev_df = pd.read_csv(rev_mapper_fpath)
    rev_df.drop_duplicates(inplace=True)
    convert_to_type(rev_df, "Plant Code", "Plant Code", int)
    convert_to_type(rev_df, "EIA Plant Code", "EIA Plant Code", int)

    # Load the Wind Generator Data from EIA 860
    wind_data = load_eia_860(file="Wind", sheet="Operable", year=data_year)
    wind_data["turb_size_mw"] = (
        wind_data["Nameplate Capacity (MW)"] / wind_data["Number of Turbines"]
    )
    convert_to_type(wind_data, "Plant Code", "Plant Code", int)
    convert_to_type(wind_data, "Generator ID", "Generator ID", str)
    wind_data["Turbine Hub Height (m)"] = (
        wind_data["Turbine Hub Height (Feet)"] / 3.28084
    )
    wind_data["Design Wind Speed (m/s)"] = (
        wind_data["Design Wind Speed (mph)"] / 2.23694
    )
    # specific area is lower for 2024 than 2025 (maybe because 2025 is incomplete)
    rd_to_hh_ratio = (
        1.385 if data_year == 2025 else 1.28936346
    )  # ratio of rotor diam/hub-height, from KB
    wind_data["Estimated Rotor Diameter (m)"] = (
        wind_data["Turbine Hub Height (m)"] * rd_to_hh_ratio
    )

    # Remove sites from the rev mapper df that aren't for sites in `wind_data`
    wind_data.set_index(keys=["Plant Code"], inplace=True)
    rev_df.set_index(keys=["Plant Code"], inplace=True)

    shared_plant_ids = set(wind_data.index.to_list()) & set(rev_df.index.to_list())
    wind_data_drop_ids = set(wind_data.index.to_list()) - shared_plant_ids
    rev_df_drop_ids = set(rev_df.index.to_list()) - shared_plant_ids
    rev_df.drop(index=list(rev_df_drop_ids), inplace=True)
    wind_data.drop(index=list(wind_data_drop_ids), inplace=True)

    # Aggregate wind data to the plant-level, make sure hub-height is the same for wind plants with multiple wind generators
    # Add number of turbines and nameplate capacity, average other stuff
    wind_data_cols = [
        "Turbine Hub Height (m)",
        "Estimated Rotor Diameter (m)",
        "Nameplate Capacity (MW)",
        "turb_size_mw",
        "Number of Turbines",
    ]

    wind_data_agg = pd.DataFrame(index=list(shared_plant_ids), columns=wind_data_cols)
    wind_data_agg.index.name = "Plant Code"
    # ---> TODO: check whats different for plants that have multiple rows ---
    wind_data_agg["Turbine Hub Height (m)"] = wind_data.groupby(level="Plant Code")[
        "Turbine Hub Height (m)"
    ].mean()
    wind_data_agg["Estimated Rotor Diameter (m)"] = wind_data.groupby(
        level="Plant Code"
    )["Estimated Rotor Diameter (m)"].mean()
    wind_data_agg["Nameplate Capacity (MW)"] = wind_data.groupby(level="Plant Code")[
        "Nameplate Capacity (MW)"
    ].sum()
    wind_data_agg["turb_size_mw"] = wind_data.groupby(level="Plant Code")[
        "turb_size_mw"
    ].mean()
    wind_data_agg["Number of Turbines"] = wind_data.groupby(level="Plant Code")[
        "Number of Turbines"
    ].sum()
    # wind_data_agg["Prime Mover"] = wind_data.groupby(level="Plant Code")

    # Filter by capacity
    filter_drop_1 = list(
        set(
            wind_data_agg[
                wind_data_agg["Nameplate Capacity (MW)"] <= 10
            ].index.to_list()
        )
    )
    wind_data_agg.drop(index=filter_drop_1, inplace=True)
    rev_df.drop(index=filter_drop_1, inplace=True)

    # Filter by prime mover
    filter_drop_2 = list(
        set(wind_data[wind_data["Prime Mover"] == "WS"].index.to_list())
    )  # drop offshore
    wind_data_agg.drop(index=filter_drop_2, inplace=True)
    rev_df.drop(index=filter_drop_2, inplace=True)

    # Filter by distance to nearest rev site
    max_distance = np.sqrt((11.5**2) + (11.5**2)) / 2
    filter_drop_3 = list(
        set(rev_df[rev_df["Distance to Rev GID (km)"] > max_distance].index.to_list())
    )
    wind_data_agg.drop(index=filter_drop_3, inplace=True)
    rev_df.drop(index=filter_drop_3, inplace=True)

    wind_data_agg.sort_index(inplace=True)
    rev_df.sort_index(inplace=True)

    rev_cols = [
        "Plant Latitude",
        "Plant Longitude",
        "area_developable_fraction",
        "REV PV Capacity (MW-DC)",
        "EIA Plant Code",
    ]

    sitelist = pd.concat([wind_data_agg, rev_df[rev_cols]], axis=1)
    sitelist.to_csv(output_sitelist_fpath)
    return sitelist


if __name__ == "__main__":
    make_existing_wind_plant_sitelist(data_year=2025)
