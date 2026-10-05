import numpy as np
import pandas as pd

from nice import LIBRARY_DIR
from nice.analysis.add_on_tech_tools import (
    add_battery_capacities_to_sitelist,
    add_solar_capacities_to_sitelist,
    battery_add_on_units,
    get_col_renames_for_add_on_case,
    solar_add_on_units,
)
from nice.tools.df_tools import add_extra_cols, convert_to_type
from nice.tools.driver_tools import write_driver_file


def make_existing_thermal_doe(n_facilities, add_on_case, data_year=2025):
    this_existing_plant = "thermal"

    if add_on_case not in ["solar", "battery", "solar_battery"]:
        raise ValueError(f"{add_on_case} is not a valid add_on_case")

    case_dir = LIBRARY_DIR / "h2i" / f"existing_{this_existing_plant}_add_{add_on_case}"
    driver_fpath = case_dir / "driver_config.yaml"
    doe_csv_fpath = (
        case_dir
        / f"existing_{this_existing_plant}_add_{add_on_case}_doe_{n_facilities}_facilities.csv"
    )

    plant_list_fpath = (
        LIBRARY_DIR
        / "h2i"
        / f"existing_thermal_plant_sitelist_{data_year}_{n_facilities}_facilities.csv"
    )

    if plant_list_fpath.exists():
        df = pd.read_csv(plant_list_fpath)
        convert_to_type(df, "EIA Plant Code", "EIA Plant Code", int)
    else:
        msg = "Please run `make_existing_thermal_plant_sitelist.py` prior to running this!"
        raise FileNotFoundError(msg)

    if "solar" in add_on_case:
        # Filter based on distance to Rev site if using solar-add-on
        df = add_extra_cols(df, "EIA Plant Code", "INDX Plant Code")
        df.set_index(keys="INDX Plant Code")
        max_distance = np.sqrt((11.5**2) + (11.5**2)) / 2
        filter_drop_3 = list(
            set(df[df["Distance to Rev GID (km)"] > max_distance].index.to_list())
        )
        df.drop(index=filter_drop_3, inplace=True)
        df.sort_index(inplace=True)
        df.reset_index(inplace=True)

    df = add_extra_cols(df, "Nameplate Capacity (MW)", "Nameplate Capacity 2 (MW)")
    df = add_extra_cols(df, "Nameplate Capacity (MW)", "Nameplate Capacity 3 (MW)")
    df = add_extra_cols(df, "EIA Plant Code", "EIA Plant Code 2")

    print(f"starting add-on case {add_on_case}: {len(df)} sites in df")

    thermal_cols_to_units = {
        "Facility ID": "unitless",
        "Plant Latitude": "deg",
        "Plant Longitude": "deg",
    }

    thermal_col_rename = {
        "Facility ID": "existing_plant.facility_id",
        # above is specific to thermal
        "Plant Latitude": "site.latitude",
        "Plant Longitude": "site.longitude",
    }

    case_renames, case_rename_units = get_col_renames_for_add_on_case(
        "thermal", add_on_case
    )

    new_col_units = {case_renames[k]: v for k, v in case_rename_units.items()}
    new_col_units |= {
        thermal_col_rename[k]: v for k, v in thermal_cols_to_units.items()
    }

    if "solar" in add_on_case:
        df = add_solar_capacities_to_sitelist(df)
        new_col_units |= solar_add_on_units
        print(f"add_on_solar: {len(df)} rows in df")

    if "battery" in add_on_case:
        df = add_battery_capacities_to_sitelist(df)
        new_col_units |= battery_add_on_units
        print(f"add_on_battery: {len(df)} rows in df")

    if len(df.drop_duplicates()) < len(df):
        raise ValueError("df has duplicated rows.")

    # rename columns
    col_renames = case_renames | thermal_col_rename
    df.rename(columns=col_renames, inplace=True)

    # drop unused columns
    drop_cols = set(df.columns.to_list()) - set(new_col_units)
    if bool(drop_cols):
        df.drop(columns=list(drop_cols), inplace=True)

    # save csv file
    df.to_csv(doe_csv_fpath, index=False)

    # TODO: use H2I's check-csv file fpath

    # make driver_config template file
    write_driver_file(new_col_units, driver_fpath, doe_csv_fpath.name)


if __name__ == "__main__":
    make_existing_thermal_doe(616, "solar_battery")
    make_existing_thermal_doe(616, "battery")
    make_existing_thermal_doe(616, "solar")
