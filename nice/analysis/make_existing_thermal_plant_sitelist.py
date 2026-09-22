import numpy as np
import pandas as pd

from nice import DATA_DIR, LIBRARY_DIR


def convert_to_type(df, new_col, old_col, data_type):
    df[new_col] = df[old_col].astype(data_type)
    return df


def make_existing_thermal_plant_sitelist(campd_sitelist_fpath, data_year=2025):
    # sitelist_desc = "rev_pv_capac"

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

    # Load the Generator Data from EIA 860
    # thermal_data = load_eia_860(file="Generator", sheet="Operable", year=data_year)
    # convert_to_type(thermal_data, "Plant Code", "Plant Code", int)
    # convert_to_type(thermal_data, "Generator ID", "Generator ID", str)
    # thermal_data.set_index(keys=["Plant Code"], inplace=True)

    thermal_data = pd.read_csv(campd_sitelist_fpath)
    convert_to_type(thermal_data, "Plant Code", "Facility ID", int)

    thermal_data.set_index(keys=["Plant Code"], inplace=True)
    rev_df.set_index(keys=["Plant Code"], inplace=True)

    shared_plant_ids = set(thermal_data.index.to_list()) & set(rev_df.index.to_list())
    thermal_data_drop_ids = set(thermal_data.index.to_list()) - shared_plant_ids
    rev_df_drop_ids = set(rev_df.index.to_list()) - shared_plant_ids
    if bool(rev_df_drop_ids):
        rev_df.drop(index=list(rev_df_drop_ids), inplace=True)
    if bool(thermal_data_drop_ids):
        thermal_data.drop(index=list(thermal_data_drop_ids), inplace=True)

    thermal_data_cols = ["Facility ID", "Nameplate Capacity (MW)"]

    rev_cols = [
        "Plant Latitude",
        "Plant Longitude",
        "area_developable_fraction",
        "REV PV Capacity (MW-DC)",
        "EIA Plant Code",
    ]

    # Filter by capacity
    filter_drop_1 = list(
        set(thermal_data[thermal_data["Nameplate Capacity (MW)"] <= 10].index.to_list())
    )
    if bool(filter_drop_1):
        thermal_data.drop(index=filter_drop_1, inplace=True)
        rev_df.drop(index=filter_drop_1, inplace=True)

    # Filter by distance to nearest rev site
    max_distance = np.sqrt((11.5**2) + (11.5**2)) / 2
    filter_drop_3 = list(
        set(rev_df[rev_df["Distance to Rev GID (km)"] > max_distance].index.to_list())
    )
    if bool(filter_drop_3):
        thermal_data.drop(index=filter_drop_3, inplace=True)
        rev_df.drop(index=filter_drop_3, inplace=True)

    thermal_data.sort_index(inplace=True)
    rev_df.sort_index(inplace=True)

    sitelist = pd.concat([thermal_data[thermal_data_cols], rev_df[rev_cols]], axis=1)

    output_sitelist_fpath = (
        LIBRARY_DIR
        / "h2i"
        / f"existing_thermal_plant_sitelist_{data_year}_{len(thermal_data)}_facilities.csv"
    )

    sitelist.to_csv(output_sitelist_fpath)
    return sitelist


if __name__ == "__main__":
    campd_eia_fpath = DATA_DIR / "campd_ratio_sitelist_518_facilities.csv"
    make_existing_thermal_plant_sitelist(campd_eia_fpath, data_year=2025)
