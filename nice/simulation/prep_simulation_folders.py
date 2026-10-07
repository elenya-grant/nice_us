import shutil
from pathlib import Path

import pandas as pd

from nice import LIBRARY_DIR
from nice.simulation.setup_tools import (
    get_techs_from_tech_connections,
    make_tech_config,
)
from nice.tools.file_tools import check_create_folder, load_yaml, write_yaml

example_main_folder = LIBRARY_DIR / "h2i"  # don't change this is
example_copy_dir = LIBRARY_DIR / "h2i_sweep_0"  #

check_create_folder(example_copy_dir)


def make_single_site_doe_csv(fac_id, original_doe_csv_fpath, copy_doe_csv_fpath):
    df = pd.read_csv(original_doe_csv_fpath)
    fac_id_cols = [
        k for k in df.columns.to_list() if ".plant_code" in k or ".facility_id" in k
    ]
    fac_id_col = fac_id_cols[0]
    df[fac_id_col] = df[fac_id_col].astype(int)
    sub_df = df[df[fac_id_col] == fac_id]
    sub_df.to_csv(copy_doe_csv_fpath, index=False)


def make_facility_subset_doe_csv(
    n_facilities_start,
    n_facilities,
    original_doe_csv_fpath,
    copy_doe_csv_fpath,
    facilities_to_exclude,
):
    df = pd.read_csv(original_doe_csv_fpath)
    fac_id_cols = [
        k for k in df.columns.to_list() if ".plant_code" in k or ".facility_id" in k
    ]

    fac_id_col = fac_id_cols[0]
    df[fac_id_col] = df[fac_id_col].astype(int)
    fac_ids_sorted = sorted(set(df[fac_id_col].to_list()))

    if bool(facilities_to_exclude):
        fac_ids_include = list(set(fac_ids_sorted) - set(facilities_to_exclude))
        df = df[df[fac_id_col].isin(fac_ids_include)]
        fac_ids_sorted = sorted(fac_ids_include)

    end_facid = n_facilities_start + n_facilities
    if end_facid >= len(fac_ids_sorted):
        fac_ids_subset = fac_ids_sorted[n_facilities_start:]
    else:
        fac_ids_subset = fac_ids_sorted[n_facilities_start:end_facid]

    sub_df = df[df[fac_id_col].isin(fac_ids_subset)].copy(deep=True)
    sub_df.to_csv(copy_doe_csv_fpath, index=False)

    print(
        f"df has {len(sub_df[fac_id_col].unique())} sites after exlcuding (from file {original_doe_csv_fpath.name}) \n"
    )


def make_copy_of_example(
    case_subfolder_name,
    copy_case_subfolder_name,
    add_on_case,
    n_facility_start,
    n_facilities,
    facility_subset_desc,
    fac_ids_to_exclude=[],
    n_thermal_facs=616,
):
    original = example_main_folder / case_subfolder_name
    new_dir = example_copy_dir / copy_case_subfolder_name

    check_create_folder(new_dir)

    # make doe csv file
    new_doe_fpath = (
        new_dir / f"design_sweep_facilities_subset_{facility_subset_desc}.csv"
    )
    if "one_axis" in copy_case_subfolder_name:
        driver_desc = "_one_axis"
        doe_filenames = [f for f in original.glob("*.csv") if "_one_axis_" in f.name]
        doe_fpath = doe_filenames[0]
    elif "fixed" in copy_case_subfolder_name:
        driver_desc = "_fixed"
        doe_filenames = [f for f in original.glob("*.csv") if "_fixed_" in f.name]
        doe_fpath = doe_filenames[0]
    else:
        driver_desc = ""
        doe_filenames = [
            f for f in original.glob("*.csv") if f.name.startswith("existing_")
        ]
        doe_filenames_thermal = [
            f
            for f in doe_filenames
            if f.name.endswith(f"_{n_thermal_facs}_facilities.csv")
        ]
        doe_filenames_thermal_style = [
            f for f in doe_filenames if f.name.endswith("_facilities.csv")
        ]
        if len(doe_filenames_thermal) > 0:
            doe_fpath = doe_filenames_thermal[0]
        else:
            doe_fpath = doe_filenames[0]
        if len(doe_filenames_thermal) == 0 and len(doe_filenames_thermal_style) > 0:
            raise ValueError(
                f"Could not find driver file for thermal plant ending in {n_thermal_facs}_facilities.csv. Found files {doe_filenames_thermal_style}"
            )

    make_facility_subset_doe_csv(
        n_facility_start, n_facilities, doe_fpath, new_doe_fpath, fac_ids_to_exclude
    )
    # if not doe_fpath.name.startswith("design_sweep_facilities_subest_"):
    #     make_single_site_doe_csv(case_facility_id, doe_fpath, new_doe_fpath)

    # copy the driver config file, update the path to the new doe csv file
    driver_file = list(original.glob(f"driver_config{driver_desc}*"))[0]
    driver_config = load_yaml(driver_file)
    driver_config["driver"]["parameter_sweep"]["filename"] = str(new_doe_fpath)
    driver_config["general"]["folder_output"] = str(
        new_dir / f"outputs_{facility_subset_desc}"
    )
    driver_config["driver"]["parameter_sweep"]["run_parallel"] = True
    driver_config["driver"]["parameter_sweep"]["debug_print"] = False

    write_yaml(
        str(new_dir / f"driver_config_{facility_subset_desc}.yaml"), driver_config
    )

    # driver_config["general"]["folder_output"] = str(new_dir / "outputs")
    # write_yaml(str(new_dir / "driver_config.yaml"), driver_config)

    # copy finance_groups file
    shutil.copy(
        example_main_folder / f"finance_groups_add_{add_on_case}.yaml",
        new_dir / f"finance_groups_add_{add_on_case}.yaml",
    )

    # copy plant config file, updating the path to the finance_groups.yaml file
    with Path(original / "plant_config.yaml").open(mode="r", encoding="utf-8") as file:
        lines = file.readlines()
        txt = "".join(l for l in lines)

    old_line = "finance_groups: !include ./finance_groups.yaml"
    finance_group_fpath = str(new_dir / f"finance_groups_add_{add_on_case}.yaml")
    new_line = f"finance_groups: !include {finance_group_fpath}"
    new_txt = txt.replace(old_line, new_line)
    new_txt = new_txt.replace(
        "resource_to_tech_connections", "site_to_tech_connections"
    )

    with Path(new_dir / "plant_config.yaml").open(mode="w", encoding="utf-8") as file:
        file.write(new_txt)

    # shutil.copytree(original, new_dir, dirs_exist_ok=True)


if __name__ == "__main__":
    from h2integrate.core.file_utils import check_file_format_for_csv_generator

    facility_exclusion_fpath = LIBRARY_DIR / "h2i" / "missing_price_data_facilities.csv"
    fac_exclusions = pd.read_csv(facility_exclusion_fpath)
    fac_ids_to_exclude = fac_exclusions["Plant Code"].astype(int).to_list()

    run_parallel = False
    debug_print = False
    run_h2i = False
    save_debug_config_files = False
    # example_facilities = [1355, 7526, 7790, 9]
    # 7790_2025_price_profile.csv
    # thermal facility: 9
    # fixed PV facility: 1355
    # one-axis facility: 7790
    # wind facility: 7526

    # existing_cases_to_facilities = {
    #     "one_axis_solar": 7790,
    #     "fixed_solar": 1355,
    #     "thermal": 9,
    #     "wind": 7526,
    # }

    # /projects/surint/campd_spheres/national_analysis
    existing_cases = {
        "thermal": "thermal",
        "one_axis_solar": "solar",
        "fixed_solar": "solar",
        "wind": "wind",
    }

    add_on_cases = ["solar", "battery", "solar_battery"]
    # add_on_cases = ["solar_battery"]

    fac_n0 = 0
    # below is for all the facilities
    # n_facs = 2000  # all the facilities
    # fac_subset_desc = "subset0"
    # below is for a subset of facilities
    n_facs = 6  # all the facilities
    fac_subset_desc = "test_subset_6sites"

    for existing_case_desc, existing_plant_type in existing_cases.items():
        # case_fac_id = existing_cases_to_facilities[existing_case_desc]

        if existing_plant_type == "solar":
            existing_pv_type = existing_case_desc.replace("_solar", "")
        else:
            existing_pv_type = "one_axis"
        for add_on_case in add_on_cases:
            print(f"Starting existing {existing_case_desc} add-on {add_on_case}")

            original_subdir_name = f"existing_{existing_plant_type}_add_{add_on_case}"
            new_subdir_name = f"existing_{existing_case_desc}_add_{add_on_case}"

            make_copy_of_example(
                original_subdir_name,
                new_subdir_name,
                add_on_case,
                0,
                n_facs,
                fac_subset_desc,
                fac_ids_to_exclude=fac_ids_to_exclude,
            )

            case_folder = example_copy_dir / new_subdir_name

            plant_config = load_yaml(case_folder / "plant_config.yaml")
            tech_names = get_techs_from_tech_connections(
                plant_config["technology_interconnections"]
            )
            tech_config = make_tech_config(
                tech_names,
                existing_plant_type,
                add_on_case,
                existing_pv_type=existing_pv_type,
            )

            # save tech config file, for debugging purposes
            tech_config_fpath = case_folder / "tech_config.yaml"
            write_yaml(str(tech_config_fpath), tech_config)

            driver_config = load_yaml(
                case_folder / f"driver_config_{fac_subset_desc}.yaml"
            )

            driver_config["driver"]["parameter_sweep"]["run_parallel"] = run_parallel
            driver_config["driver"]["parameter_sweep"]["debug_print"] = debug_print

            for tech_name, tech_vars in driver_config["design_variables"].items():
                # could remove this eventually ...
                for tech_var, tech_var_stuff in tech_vars.items():
                    if (
                        "lower" in tech_var_stuff
                        and tech_var_stuff.get("lower") is None
                    ):
                        driver_config["design_variables"][tech_name][tech_var][
                            "lower"
                        ] = -1e12
                    if (
                        "upper" in tech_var_stuff
                        and tech_var_stuff.get("upper") is None
                    ):
                        driver_config["design_variables"][tech_name][tech_var][
                            "upper"
                        ] = 1e12

            # Save updated driver config
            write_yaml(
                str(case_folder / f"driver_config_{fac_subset_desc}.yaml"),
                driver_config,
            )

            if save_debug_config_files:
                write_yaml(str(case_folder / "check_driver_cnfg.yaml"), driver_config)
                write_yaml(str(case_folder / "check_plnt_cnfg.yaml"), plant_config)

            config = {
                "plant_config": plant_config,
                "technology_config": tech_config,
                "driver_config": driver_config,
            }

            # Update formatting for CSV file

            check_file_format_for_csv_generator(
                Path(driver_config["driver"]["parameter_sweep"]["filename"]),
                driver_config,
                check_only=False,
                overwrite_file=True,
            )

            # TODO: add H2I run in!
            # print(f"Starting existing {existing_case_desc} add-on {add_on_case}")
            if run_h2i:
                from h2integrate import H2IntegrateModel

                print(f"Running H2I for {existing_case_desc} add-on {add_on_case}")
                h2i = H2IntegrateModel(config)
                h2i.setup()
                h2i.run()
