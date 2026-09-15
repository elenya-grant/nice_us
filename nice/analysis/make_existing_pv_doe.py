import pandas as pd

from nice import LIBRARY_DIR
from nice.analysis.add_on_tech_tools import (
    add_battery_capacities_to_sitelist,
    add_solar_capacities_to_sitelist,
    battery_add_on_units,
    get_col_renames_for_add_on_case,
    solar_add_on_units,
)
from nice.analysis.make_existing_pv_plant_list import make_existing_solar_plant_sitelist
from nice.tools.df_tools import add_extra_cols, convert_to_type
from nice.tools.driver_tools import write_driver_file


def make_existing_solar_doe(array_type, add_on_case, data_year=2025):
    this_existing_plant = "solar"

    if add_on_case not in ["solar", "battery", "solar_battery"]:
        raise ValueError(f"{add_on_case} is not a valid add_on_case")

    case_dir = LIBRARY_DIR / "h2i" / f"existing_{this_existing_plant}_add_{add_on_case}"
    driver_fpath = case_dir / f"driver_config_{array_type}.yaml"
    doe_csv_fpath = (
        case_dir
        / f"existing_{array_type}_{this_existing_plant}_add_{add_on_case}_doe.csv"
    )

    plant_list_fpath = (
        LIBRARY_DIR
        / "h2i"
        / f"existing_{array_type}_solar_plant_sitelist_{data_year}.csv"
    )

    if plant_list_fpath.exists():
        df = pd.read_csv(plant_list_fpath)
        convert_to_type(df, "EIA Plant Code", "EIA Plant Code", int)

    else:
        df = make_existing_solar_plant_sitelist(array_type, data_year=data_year)

    df = add_extra_cols(df, "Nameplate Capacity (MW)", "Nameplate Capacity 2 (MW)")
    df = add_extra_cols(df, "Nameplate Capacity (MW)", "Nameplate Capacity 3 (MW)")
    df = add_extra_cols(df, "EIA Plant Code", "EIA Plant Code 2")

    print(f"starting: {len(df)} sites in df")

    solar_cols_to_units = {
        "DC Capacity (MW)": "MW",
        "Tilt": "deg",
        "Azimuth": "deg",
        "dc_ac_ratio": "unitless",
        "Plant Latitude": "deg",
        "Plant Longitude": "deg",
    }

    solar_col_rename = {
        "DC Capacity (MW)": "existing_plant.system_capacity_DC",
        "Tilt": "existing_plant.tilt_angle",
        "Azimuth": "existing_plant.azimuth_angle",
        "dc_ac_ratio": "existing_plant.dc_ac_ratio",
        "Plant Latitude": "site.latitude",
        "Plant Longitude": "site.longitude",
    }

    case_renames, case_rename_units = get_col_renames_for_add_on_case(
        "solar", add_on_case
    )

    new_col_units = {case_renames[k]: v for k, v in case_rename_units.items()}
    new_col_units |= {solar_col_rename[k]: v for k, v in solar_cols_to_units.items()}

    if "solar" in add_on_case:
        df = add_solar_capacities_to_sitelist(df)
        new_col_units |= solar_add_on_units
        print(f"add_on_solar: {len(df)} rows in df")

    if len(df.drop_duplicates()) < len(df):
        raise ValueError("df has duplicated rows.")

    if "battery" in add_on_case:
        df = add_battery_capacities_to_sitelist(df)
        new_col_units |= battery_add_on_units
        print(f"add_on_battery: {len(df)} rows in df")

    if len(df.drop_duplicates()) < len(df):
        raise ValueError("df has duplicated rows.")

    # rename columns
    col_renames = case_renames | solar_col_rename
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
    make_existing_solar_doe("one_axis", "solar_battery")
    make_existing_solar_doe("one_axis", "battery")
    make_existing_solar_doe("one_axis", "solar")

    make_existing_solar_doe("fixed", "solar_battery")
    make_existing_solar_doe("fixed", "battery")
    make_existing_solar_doe("fixed", "solar")
