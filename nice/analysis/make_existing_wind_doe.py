import pandas as pd

from nice import LIBRARY_DIR
from nice.analysis.add_on_tech_tools import (
    add_battery_capacities_to_sitelist,
    add_solar_capacities_to_sitelist,
    battery_add_on_units,
    get_col_renames_for_add_on_case,
    solar_add_on_units,
)
from nice.analysis.make_existing_wind_plant_list import (
    make_existing_wind_plant_sitelist,
)
from nice.tools.df_tools import add_extra_cols, convert_to_type
from nice.tools.driver_tools import write_driver_file


def make_existing_wind_doe(add_on_case, data_year=2025):
    this_existing_plant = "wind"

    if add_on_case not in ["solar", "battery", "solar_battery"]:
        raise ValueError(f"{add_on_case} is not a valid add_on_case")

    case_dir = LIBRARY_DIR / "h2i" / f"existing_{this_existing_plant}_add_{add_on_case}"
    driver_fpath = case_dir / "driver_config.yaml"
    doe_csv_fpath = (
        case_dir / f"existing_{this_existing_plant}_add_{add_on_case}_doe.csv"
    )

    plant_list_fpath = (
        LIBRARY_DIR / "h2i" / f"existing_wind_plant_sitelist_{data_year}.csv"
    )

    if plant_list_fpath.exists():
        df = pd.read_csv(plant_list_fpath)
        convert_to_type(df, "EIA Plant Code", "EIA Plant Code", int)

    else:
        df = make_existing_wind_plant_sitelist(data_year=data_year)

    df = add_extra_cols(df, "Nameplate Capacity (MW)", "Nameplate Capacity 2 (MW)")
    df = add_extra_cols(df, "Nameplate Capacity (MW)", "Nameplate Capacity 3 (MW)")
    df = add_extra_cols(df, "EIA Plant Code", "EIA Plant Code 2")

    print(f"starting: {len(df)} sites in df")

    wind_cols_to_units = {
        "Turbine Hub Height (m)": "m",
        "Estimated Rotor Diameter (m)": "m",
        "Number of Turbines": "unitless",
        "turb_size_mw": "MW",
        "Plant Latitude": "deg",
        "Plant Longitude": "deg",
    }

    wind_col_rename = {
        # "Turbine Hub Height (m)": "existing_plant.wind_turbine_hub_ht",
        "Turbine Hub Height (m)": "existing_plant.hub_height",
        # "Estimated Rotor Diameter (m)": "existing_plant.wind_turbine_rotor_diameter",
        "Estimated Rotor Diameter (m)": "existing_plant.rotor_diameter",
        "Number of Turbines": "existing_plant.num_turbines",
        "turb_size_mw": "existing_plant.wind_turbine_rating",
        # above is specific to wind
        "Plant Latitude": "site.latitude",
        "Plant Longitude": "site.longitude",
    }

    case_renames, case_rename_units = get_col_renames_for_add_on_case(
        "wind", add_on_case
    )

    new_col_units = {case_renames[k]: v for k, v in case_rename_units.items()}
    new_col_units |= {wind_col_rename[k]: v for k, v in wind_cols_to_units.items()}

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
    col_renames = case_renames | wind_col_rename
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

    []
    # add_on_case_renames = {
    #     # plant lat/lon is not needed if thermal plant with add on battery
    #     "Nameplate Capacity (MW)": "poi_demand.electricity_demand",
    #     "Nameplate Capacity 2 (MW)": "grid_sell.interconnection_size",
    #     "EIA Plant Code": "grid_sell.plant_code",
    #     "REV PV Capacity (MW-DC)": "add_on_solar.system_capacity_DC",
    # }


if __name__ == "__main__":
    make_existing_wind_doe("solar_battery")
    make_existing_wind_doe("battery")
    make_existing_wind_doe("solar")
