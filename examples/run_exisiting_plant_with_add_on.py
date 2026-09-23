import shutil
from pathlib import Path

import pandas as pd

from nice import LIBRARY_DIR
from nice.simulation.setup_tools import (
    get_techs_from_tech_connections,
    make_tech_config,
)
from nice.tools.file_tools import check_create_folder, load_yaml, write_yaml

example_main_folder = LIBRARY_DIR / "h2i"  # / "tech_config"
example_copy_dir = LIBRARY_DIR / "h2i_single_site"

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


def make_copy_of_example(
    case_subfolder_name, copy_case_subfolder_name, case_facility_id
):
    original = example_main_folder / case_subfolder_name
    new_dir = example_copy_dir / copy_case_subfolder_name

    check_create_folder(new_dir)

    # make doe csv file
    new_doe_fpath = new_dir / f"design_sweep_facility_{case_facility_id}.csv"
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
        doe_fpath = list(original.glob("*.csv"))[0]
    if not doe_fpath.name.startswith("design_sweep_facility_"):
        make_single_site_doe_csv(case_facility_id, doe_fpath, new_doe_fpath)

    # copy the driver config file, update the path to the new doe csv file
    driver_file = list(original.glob(f"driver_config{driver_desc}*"))[0]
    driver_config = load_yaml(driver_file)
    driver_config["driver"]["parameter_sweep"]["filename"] = str(new_doe_fpath)
    driver_config["general"]["folder_output"] = str(new_dir / "outputs")
    write_yaml(str(new_dir / "driver_config.yaml"), driver_config)
    # shutil.copy(original/driver_file, new_dir/"driver_config.yaml")

    # copy finance_groups file
    shutil.copy(
        example_main_folder / "finance_groups.yaml", new_dir / "finance_groups.yaml"
    )

    # copy plant config file, updating the path to the finance_groups.yaml file
    with Path(original / "plant_config.yaml").open(mode="r", encoding="utf-8") as file:
        lines = file.readlines()
        txt = "".join(l for l in lines)

    old_line = "finance_groups: !include ./finance_groups.yaml"
    finance_group_fpath = str(new_dir / "finance_groups.yaml")
    new_line = f"finance_groups: !include {finance_group_fpath}"
    new_txt = txt.replace(old_line, new_line)
    new_txt = new_txt.replace(
        "resource_to_tech_connections", "site_to_tech_connections"
    )

    with Path(new_dir / "plant_config.yaml").open(mode="w", encoding="utf-8") as file:
        file.write(new_txt)

    # shutil.copytree(original, new_dir, dirs_exist_ok=True)


if __name__ == "__main__":
    from h2integrate import H2IntegrateModel
    from h2integrate.core.file_utils import check_file_format_for_csv_generator

    run_parallel = False
    debug_print = True
    run_h2i = True
    save_debug_config_files = False
    # example_facilities = [1355, 7526, 7790, 9]
    # 7790_2025_price_profile.csv
    # thermal facility: 9
    # fixed PV facility: 1355
    # one-axis facility: 7790
    # wind facility: 7526

    existing_cases_to_facilities = {
        "one_axis_solar": 7790,
        "fixed_solar": 1355,
        "thermal": 9,
        "wind": 7526,
    }

    # /projects/surint/campd_spheres/national_analysis
    existing_cases = {
        "thermal": "thermal",
        "one_axis_solar": "solar",
        "fixed_solar": "solar",
        "wind": "wind",
    }

    add_on_cases = ["solar", "battery", "solar_battery"]
    # add_on_cases = ["solar"]

    for existing_case_desc, existing_plant_type in existing_cases.items():
        case_fac_id = existing_cases_to_facilities[existing_case_desc]

        if existing_plant_type == "solar":
            existing_pv_type = existing_case_desc.replace("_solar", "")
        else:
            existing_pv_type = "one_axis"
        for add_on_case in add_on_cases:
            print(f"Starting existing {existing_case_desc} add-on {add_on_case}")

            original_subdir_name = f"existing_{existing_plant_type}_add_{add_on_case}"
            new_subdir_name = f"existing_{existing_case_desc}_add_{add_on_case}"

            make_copy_of_example(original_subdir_name, new_subdir_name, case_fac_id)

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

            driver_config = load_yaml(case_folder / "driver_config.yaml")

            driver_config["driver"]["parameter_sweep"]["run_parallel"] = run_parallel
            driver_config["driver"]["parameter_sweep"]["debug_print"] = debug_print

            for tech_name, tech_vars in driver_config["design_variables"].items():
                for tech_var, tech_var_stuff in tech_vars.items():
                    if (
                        "lower" in tech_var_stuff
                        and tech_var_stuff.get("lower") is None
                    ):
                        driver_config["design_variables"][tech_name][tech_var][
                            "lower"
                        ] = -1e6
                    if (
                        "upper" in tech_var_stuff
                        and tech_var_stuff.get("upper") is None
                    ):
                        driver_config["design_variables"][tech_name][tech_var][
                            "upper"
                        ] = 1e6

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

            print(f"Done setting-up {existing_case_desc} add-on {add_on_case}")

            # TODO: add H2I run in!
            # print(f"Starting existing {existing_case_desc} add-on {add_on_case}")

            if run_h2i:
                print(f"Running H2I for {existing_case_desc} add-on {add_on_case}")
                h2i = H2IntegrateModel(config)
                h2i.setup()
                h2i.run()
