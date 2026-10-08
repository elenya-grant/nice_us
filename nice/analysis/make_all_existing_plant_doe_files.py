from nice import DATA_DIR
import types
from nice.analysis.make_existing_pv_plant_list import make_existing_solar_plant_sitelist
from nice.analysis.make_existing_wind_plant_list import make_existing_wind_plant_sitelist
from nice.analysis.make_existing_thermal_plant_sitelist import make_existing_thermal_plant_sitelist
from nice.analysis.make_existing_pv_doe import make_existing_solar_doe
from nice.analysis.make_existing_wind_doe import make_existing_wind_doe
from nice.analysis.make_existing_thermal_doe import make_existing_thermal_doe

remake_existing_plant_list = True
remake_doe_files = True
prep_simulation_folder_for_all_sites = True



## inputs ##
n_thermal_facs = 616

## below are inputs for prepping sites ##
make_price_run_version = "v2"
max_n_sites = 2000 
lib_subdir = "h2i_sweep_0"
driver_subset_desc = "subset0"

# below are output from `make_price_data`
exlcusion_file = f"missing_price_data_facilities_{make_price_run_version}.csv"
inclusion_file = f"valid_price_data_facilities_{make_price_run_version}.csv"



if remake_existing_plant_list:
    campd_eia_fpath = DATA_DIR / "campd_ratio_sitelist_619_facilities.csv"
    _, n_thermal_facs = make_existing_thermal_plant_sitelist(campd_eia_fpath, data_year=2025)
    make_existing_solar_plant_sitelist("one_axis", data_year=2025)
    make_existing_solar_plant_sitelist("fixed", data_year=2025)
    make_existing_wind_plant_sitelist(data_year=2025)

if remake_existing_plant_list or remake_doe_files:
    make_existing_wind_doe("solar_battery")
    make_existing_wind_doe("battery")
    make_existing_wind_doe("solar")

    make_existing_solar_doe("one_axis", "solar_battery")
    make_existing_solar_doe("one_axis", "battery")
    make_existing_solar_doe("one_axis", "solar")

    make_existing_solar_doe("fixed", "solar_battery")
    make_existing_solar_doe("fixed", "battery")
    make_existing_solar_doe("fixed", "solar")

    make_existing_thermal_doe(n_thermal_facs, "solar_battery")
    make_existing_thermal_doe(n_thermal_facs, "battery")
    make_existing_thermal_doe(n_thermal_facs, "solar")


if prep_simulation_folder_for_all_sites:
    from nice.simulation.prep_simulation_folders_cmd import main
    args_obj = types.SimpleNamespace()
    args_obj.missing_plant_ids_fname = exlcusion_file
    args_obj.valid_plant_ids_fname = inclusion_file
    args_obj.n_facilities = max_n_sites
    args_obj.n_fac_start = 0
    args_obj.library_subdir = lib_subdir
    args_obj.driver_subset_desc = driver_subset_desc
    args_obj.add_on_plants = ["solar", "battery", "solar_battery"]
    args_obj.existing_plants = ["wind", "one_axis_solar", "fixed_solar", "thermal"]

    main(args_obj)