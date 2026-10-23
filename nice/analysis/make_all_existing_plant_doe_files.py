import types

from nice import DATA_DIR
from nice.analysis.make_existing_pv_doe import make_existing_solar_doe
from nice.analysis.make_existing_pv_plant_list import make_existing_solar_plant_sitelist
from nice.analysis.make_existing_thermal_doe import make_existing_thermal_doe
from nice.analysis.make_existing_thermal_plant_sitelist import (
    make_existing_thermal_plant_sitelist,
)
from nice.analysis.make_existing_wind_doe import make_existing_wind_doe
from nice.analysis.make_existing_wind_plant_list import (
    make_existing_wind_plant_sitelist,
)

remake_existing_plant_list = False
remake_doe_files = False
prep_simulation_folder_for_all_sites = True

# updated so you can modify this up here instead of later in the code
existing_plants_to_run = [
    "wind"
]  # ["wind", "one_axis_solar", "fixed_solar", "thermal"]
add_on_plants_to_run = ["solar_battery"]  # ["solar", "battery", "solar_battery"]

## inputs ##
n_thermal_facs = 616

## below are inputs for prepping sites ##
make_price_run_version = "v4"
lib_subdir = "h2i_sweep_0"
## below is for chunking sites if needed

# below is what was used for add solar and add battery cases
n_fac0 = 0  # starting number of sites
max_n_sites = 2000
driver_subset_desc = "subset0"

# below is what was used for add solar_battery case
# n_fac0 = 750 # starting number of sites
# max_n_sites = 250
# driver_subset_desc = "subset0d"

# notes on site chunking for add solar_battery
# thermal has 2 subsets (subset0a and subset0b) each with about 260 sites
# wind has 4 subsets (subset0a, subset0b, subset0c, subset0d), each with about 250 sites
# one_axis_solar has 4 subsets (subset0a, subset0b, subset0c, subset0d), each with 279 sites

# below are output from `make_price_data`
exlcusion_file = f"missing_price_data_facilities_{make_price_run_version}.csv"
inclusion_file = f"valid_price_data_facilities_{make_price_run_version}.csv"


if remake_existing_plant_list:
    if "thermal" in existing_plants_to_run:
        campd_eia_fpath = DATA_DIR / "campd_ratio_sitelist_619_facilities.csv"
        _, n_thermal_facs = make_existing_thermal_plant_sitelist(
            campd_eia_fpath, data_year=2025
        )
    if "one_axis_solar" in existing_plants_to_run:
        make_existing_solar_plant_sitelist("one_axis", data_year=2025)
    if "fixed_solar" in existing_plants_to_run:
        make_existing_solar_plant_sitelist("fixed", data_year=2025)
    if "wind" in existing_plants_to_run:
        make_existing_wind_plant_sitelist(data_year=2025)

if remake_existing_plant_list or remake_doe_files:
    print("remaking doe \n \n ")

    if "wind" in existing_plants_to_run:
        print("existing wind: ")
        for add_on_plant in add_on_plants_to_run:
            make_existing_wind_doe(add_on_plant)
        # make_existing_wind_doe("solar_battery")
        # make_existing_wind_doe("battery")
        # make_existing_wind_doe("solar")
        print("\n")

    if "one_axis_solar" in existing_plants_to_run:
        print("existing one_axis_solar: ")
        for add_on_plant in add_on_plants_to_run:
            make_existing_solar_doe("one_axis", add_on_plant)
        # make_existing_solar_doe("one_axis", "solar_battery")
        # make_existing_solar_doe("one_axis", "battery")
        # make_existing_solar_doe("one_axis", "solar")
        print("\n")

    if "fixed_solar" in existing_plants_to_run:
        print("existing fixed_solar: ")
        for add_on_plant in add_on_plants_to_run:
            make_existing_solar_doe("fixed", add_on_plant)
        # make_existing_solar_doe("fixed", "solar_battery")
        # make_existing_solar_doe("fixed", "battery")
        # make_existing_solar_doe("fixed", "solar")
        print("\n")

    if "thermal" in existing_plants_to_run:
        print("existing thermal: ")
        for add_on_plant in add_on_plants_to_run:
            make_existing_thermal_doe(n_thermal_facs, add_on_plant)
        # make_existing_thermal_doe(n_thermal_facs, "solar_battery")
        # make_existing_thermal_doe(n_thermal_facs, "battery")
        # make_existing_thermal_doe(n_thermal_facs, "solar")
        print("\n")


if prep_simulation_folder_for_all_sites:
    from nice.simulation.prep_simulation_folders_cmd import main

    args_obj = types.SimpleNamespace()
    args_obj.missing_plant_ids_fname = exlcusion_file
    args_obj.valid_plant_ids_fname = inclusion_file
    args_obj.n_facilities = max_n_sites
    args_obj.n_thermal_facilities = n_thermal_facs
    args_obj.n_fac_start = n_fac0
    args_obj.library_subdir = lib_subdir
    args_obj.driver_subset_desc = driver_subset_desc
    args_obj.add_on_plants = (
        add_on_plants_to_run  # ["solar", "battery", "solar_battery"]
    )
    args_obj.existing_plants = existing_plants_to_run  # ["wind"] #["thermal"] # ["wind", "one_axis_solar", "fixed_solar", "thermal"]

    main(args_obj)
