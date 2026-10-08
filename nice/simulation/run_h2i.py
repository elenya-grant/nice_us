import argparse

from h2integrate import H2IntegrateModel

from nice import LIBRARY_DIR
from nice.tools.file_tools import load_yaml
from datetime import datetime
from pathlib import Path
import os
import openmdao.api as om

import faulthandler
faulthandler.enable()

def main():
    

    """Command-line entry point for run_plants.py"""
    parser = argparse.ArgumentParser(
        description="Run plants",
        epilog=(
            "Example: "
            "python nice/simulation/run_plants.py --existing_plant wind --add_on_plant pv_bess"
        ),
    )

    parser.add_argument(
        "existing_plant",
        type=str,
        help="Existing plant type (either 'wind', 'fixed_solar', 'one_axis_solar', 'thermal')",
    )
    parser.add_argument(
        "add_on_plant",
        type=str,
        help="Add on plant type (either 'solar','battery', or 'solar_battery')",
    )

    parser.add_argument(
        "--library_subdir",
        type=str,
        # default=False,
        help="Subdirectory in 'libary' containing folders for runs (ex: 'h2i_sweep_0')",
    )

    parser.add_argument(
        "--driver_subset_desc",
        "--d",
        type=str,
        # default=None,
        help="Driver file description, like 'subset0'.",
    )

    args = parser.parse_args()

    # print(f"existing_plant: {args.existing_plant}")
    # print(f"add_on_plant: {args.add_on_plant}")
    # print(f"library subdir {args.library_subdir}")
    # print(f"driver desc {args.driver_subset_desc}")

    if args.existing_plant not in ["wind", "one_axis_solar", "fixed_solar", "thermal"]:
        msg = (
            f"invalid existing_plant type of '{args.existing_plant}'. "
            "Options are 'wind','one_axis_solar','fixed_solar' or 'thermal'"
        )
        raise ValueError(msg)

    if args.add_on_plant not in ["solar", "battery", "solar_battery"]:
        msg = (
            f"invalid existing_plant type of '{args.add_on_plant}'. "
            "Options are 'solar','battery', or 'solar_battery'"
        )
        raise ValueError(msg)

    if not (LIBRARY_DIR / args.library_subdir).exists():
        msg = f"Folder {args.library_subdir} does not exist in 'library'"
        raise FileNotFoundError(msg)

    case_dir = (
        LIBRARY_DIR
        / args.library_subdir
        / f"existing_{args.existing_plant}_add_{args.add_on_plant}"
    )
    if not case_dir.exists():
        msg = f"Folder {case_dir} does not exist"
        raise FileNotFoundError(msg)

    driver_fpath = case_dir / f"driver_config_{args.driver_subset_desc}.yaml"
    if not driver_fpath.exists():
        msg = f"Drive filename {driver_fpath.name} does not exist"
        raise FileNotFoundError(msg)

    plant_config = load_yaml(case_dir / "plant_config.yaml")
    driver_config = load_yaml(driver_fpath)
    tech_config = load_yaml(case_dir / "tech_config.yaml")

    output_dir = Path(driver_config["general"]["folder_output"])
    if not output_dir.exists():
        Path.mkdir(Path(output_dir), parents=True, exist_ok=True)

    # os.chdir(output_dir)

    # driver_config["recorder"]["flag"] = False
    # driver_config["recorder"]["file"] = "cases_output_v3.sql"
    driver_config["recorder"]["recorder_attachment"] = "driver" # connect to driver when running in parallel
    driver_config["driver"]["parameter_sweep"]["run_parallel"] = True
    driver_config["driver"]["parameter_sweep"]["debug_print"] = False

    config = {
        "plant_config": plant_config,
        "technology_config": tech_config,
        "driver_config": driver_config,
    }

    h2i = H2IntegrateModel(config)

    # h2i.prob.driver.add_recorder(om.SqliteRecorder("cases.sql"))
    # h2i.prob.driver.recording_options["record_inputs"] = True
    # h2i.prob.driver.recording_options["record_outputs"] = True
    # h2i.prob.driver.recording_options["includes"] = ["*"]
    # h2i.prob.driver.recording_options["excludes"] = ["*resource_data*"]

    h2i.setup()
    h2i.run()


if __name__ == "__main__":
    # starting_cwd = Path.cwd()

    t_start = datetime.now()

    main()

    t_end = datetime.now()
    time_to_run = (t_end-t_start).seconds/60
    print(f"took {time_to_run:.2f} min to run H2I")
    # os.chdir(starting_cwd)
    
