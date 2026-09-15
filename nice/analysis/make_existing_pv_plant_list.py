import numpy as np
import pandas as pd

from nice import DATA_DIR, LIBRARY_DIR
from nice.tools.df_tools import convert_to_type
from nice.tools.eia_860_file_tools import load_eia_860


def find_tracking_type(row):
    # `array_type`:
    # 1 is fixed, 2, is 1-axis tracking, 4 is 2-axis tracking
    yes_to_array_type = {
        "Fixed Tilt?": 1,
        "Single-Axis Tracking?": 2,
        "Dual-Axis Tracking?": 4,
    }
    array_type = [v for k, v in yes_to_array_type.items() if row[k] == "Y"]
    if bool(array_type):
        return array_type[0]
    return -1


def find_is_bifacial(row):
    if row["Bifacial?"] == "Y":
        return True
    return False


def dc_capacity(row):
    if row["DC Net Capacity (MW)"] == " ":
        return row["Nameplate Capacity (MW)"] * 1.34
    return float(row["DC Net Capacity (MW)"])


def azimuth(row):
    if row["Azimuth Angle"] == " ":
        return 180.0
    return float(row["Azimuth Angle"])


def tilt(row):
    if row["Tilt Angle"] == " ":
        return 45.0
    return float(row["Tilt Angle"])


def make_existing_solar_plant_sitelist(array_type, data_year=2025):
    if array_type not in ["one_axis", "fixed"]:
        raise ValueError("array_type_type must be either 'one_axis' or 'fixed'. ")

    output_sitelist_fpath = (
        LIBRARY_DIR
        / "h2i"
        / f"existing_{array_type}_solar_plant_sitelist_{data_year}.csv"
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

    # Load the Solar Generator Data from EIA 860
    solar_data = load_eia_860(file="Solar", sheet="Operable", year=data_year)

    convert_to_type(solar_data, "Plant Code", "Plant Code", int)
    convert_to_type(solar_data, "Generator ID", "Generator ID", str)
    # TODO: Add/summarize information to solar_data
    solar_data["Array Type"] = solar_data.apply(find_tracking_type, axis=1)
    # solar_data["Cell Design Type"] = solar_data.apply(find_cell_type, axis=1)
    solar_data["Bifacial"] = solar_data.apply(find_is_bifacial, axis=1)

    solar_data["Tilt"] = solar_data.apply(tilt, axis=1)
    solar_data["DC Capacity (MW)"] = solar_data.apply(dc_capacity, axis=1)
    solar_data["Azimuth"] = solar_data.apply(azimuth, axis=1)

    # solar_data[solar_data["DC Net Capacity (MW)"]==" "].index.to_list()
    # solar_data[solar_data["Azimuth Angle"]==" "].index.to_list()
    # solar_data[solar_data["Tilt Angle"]==" "]

    # solar_data["dc_ac_ratio"] = (
    #     solar_data["DC Net Capacity (MW)"] / solar_data["Nameplate Capacity (MW)"]
    # )
    solar_data["dc_ac_ratio"] = (
        solar_data["DC Capacity (MW)"] / solar_data["Nameplate Capacity (MW)"]
    )

    # Drop solar sites that have wrong tracking type:
    if array_type == "one_axis":
        # array type of 2 or 4
        solar_data = solar_data[solar_data["Array Type"] > 1]
    if array_type == "fixed":
        # array type of 1
        solar_data = solar_data[solar_data["Array Type"] == 1]

    # Remove sites from the rev mapper df that aren't for sites in `solar_data`
    solar_data.set_index(keys=["Plant Code"], inplace=True)
    rev_df.set_index(keys=["Plant Code"], inplace=True)

    shared_plant_ids = set(solar_data.index.to_list()) & set(rev_df.index.to_list())
    solar_data_drop_ids = set(solar_data.index.to_list()) - shared_plant_ids
    rev_df_drop_ids = set(rev_df.index.to_list()) - shared_plant_ids
    rev_df.drop(index=list(rev_df_drop_ids), inplace=True)
    solar_data.drop(index=list(solar_data_drop_ids), inplace=True)

    # Aggregate solar data to the plant-level
    # Add xxx
    solar_data_cols = [
        "Array Type",
        # "Azimuth Angle",
        # "Tilt Angle",
        "Azimuth",
        "Tilt",
        # "Cell Design Type",
        # "Bifacial",
        "dc_ac_ratio",
        "DC Capacity (MW)",
        "Nameplate Capacity (MW)",
    ]

    solar_data_agg = pd.DataFrame(index=list(shared_plant_ids), columns=solar_data_cols)
    solar_data_agg.index.name = "Plant Code"

    # Filter data

    # TODO: add other filters (such as capacity)
    filter_drop_1 = list(
        set(
            solar_data_agg[
                solar_data_agg["Nameplate Capacity (MW)"] <= 10
            ].index.to_list()
        )
    )
    solar_data_agg.drop(index=filter_drop_1, inplace=True)
    rev_df.drop(index=filter_drop_1, inplace=True)

    max_distance = np.sqrt((11.5**2) + (11.5**2)) / 2
    filter_drop_3 = list(
        set(rev_df[rev_df["Distance to Rev GID (km)"] > max_distance].index.to_list())
    )
    solar_data_agg.drop(index=filter_drop_3, inplace=True)
    rev_df.drop(index=filter_drop_3, inplace=True)

    solar_data_agg.sort_index(inplace=True)
    rev_df.sort_index(inplace=True)

    rev_cols = [
        "Plant Latitude",
        "Plant Longitude",
        "area_developable_fraction",
        "REV PV Capacity (MW-DC)",
        "EIA Plant Code",
    ]

    sitelist = pd.concat([solar_data_agg, rev_df[rev_cols]], axis=1)
    sitelist.to_csv(output_sitelist_fpath)
    return sitelist


if __name__ == "__main__":
    make_existing_solar_plant_sitelist("one_axis", data_year=2025)
    make_existing_solar_plant_sitelist("fixed", data_year=2025)
