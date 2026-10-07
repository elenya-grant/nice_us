import argparse
import copy
import faulthandler
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
from h2integrate import H2IntegrateModel
from h2integrate.core.file_utils import check_file_format_for_csv_generator
from mpi4py import MPI

from nice import LIBRARY_DIR
from nice.tools.file_tools import load_yaml

faulthandler.enable()


def run_chunks(
    plant_code_subset, full_csv_doe, plant_code_colname, rank_number, input_config
):
    # step 1: read the full sitelist and save-off the chunks for the number of sites
    doe_subset = full_csv_doe[
        full_csv_doe[plant_code_colname].isin(plant_code_subset)
    ].copy()
    if len(doe_subset) == 0:
        msg = (
            f"Rank {rank_number}: No sites in column {plant_code_colname} "
            f"from list {plant_code_subset}"
        )
        raise ValueError(msg)

    # copy the driver config
    driver_cnfg = copy.deepcopy(input_config["driver_config"])
    subset_fpath = (
        Path(driver_cnfg["driver"]["parameter_sweep"]["filename"]).parent
        / f"doe_cases_rank_{rank_number}_doe.csv"
    )
    doe_subset.to_csv(subset_fpath)
    driver_cnfg["driver"]["parameter_sweep"]["filename"] = str(subset_fpath)
    driver_cnfg["driver"]["recorder"]["file"] = f"cases.sql_{rank_number}"

    # reformat the file as needed
    check_file_format_for_csv_generator(
        subset_fpath,
        driver_cnfg,
        check_only=False,
        overwrite_file=True,
    )
    driver_cnfg["parameter_sweep"]["filename"]

    config = {
        "plant_config": copy.deepcopy(input_config["plant_config"]),
        "technology_config": copy.deepcopy(input_config["technology_config"]),
        "driver_config": driver_cnfg,
    }

    h2i = H2IntegrateModel(config)

    h2i.setup()

    h2i.run()


start_time = datetime.now()

comm = MPI.COMM_WORLD
size = MPI.COMM_WORLD.Get_size()
rank = MPI.COMM_WORLD.Get_rank()
name = MPI.Get_processor_name()


def main(full_site_df, h2i_input_config, verbose=True):
    if rank == 0:
        if verbose:
            print("i'm rank {}:".format(rank))
        ################################ split site_idx's
        fac_id_cols = [
            k
            for k in full_site_df.columns.to_list()
            if ".plant_code" in k or ".facility_id" in k
        ]
        fac_id_col = fac_id_cols[0]
        s_list = sorted(set(full_site_df[fac_id_col].to_list()))

        # check if number of ranks <= number of tasks
        if size > len(s_list):
            print(
                "number of scenarios {} < number of ranks {}, abborting...".format(
                    len(s_list), size
                )
            )
            sys.exit()

        # split them into chunks (number of chunks = number of ranks)
        chunk_size = len(s_list) // size

        remainder_size = len(s_list) % size

        s_list_chunks = [
            s_list[i : i + chunk_size] for i in range(0, size * chunk_size, chunk_size)
        ]

        # distribute remainder to chunks
        for i in range(-remainder_size, 0):
            s_list_chunks[i].append(s_list[i])

        if verbose:
            print(f"\n s_list_chunks {s_list_chunks}")
    else:
        s_list_chunks = None

    ### scatter
    s_list_chunks = comm.scatter(s_list_chunks, root=0)

    if verbose:
        print(f"\n rank {rank} has {len(s_list_chunks)} files to process")

    # run post-processing code for chunks
    # do_something(s_list_chunks, f"{rank}")
    run_chunks(
        s_list_chunks,
        copy.deepcopy(full_site_df),
        fac_id_col,
        f"{rank}",
        copy.deepcopy(h2i_input_config),
    )

    if verbose:
        time_to_run = (datetime.now() - start_time).seconds / 60
        print(f"rank {rank}: ellapsed time: {time_to_run} minutes")


if __name__ == "__main__":
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

    parser.add_argument(
        "--iprint_setting",
        "--i",
        type=int,
        default=0,
        help="0 to not have print in SLC, 2 to enable printing",
    )

    parser.add_argument(
        "--debug_print",
        "--p",
        type=int,
        default=0,
        help="0 to not have debug print on, 1 to have debug print on",
    )

    parser.add_argument(
        "--verbose",
        "--v",
        type=int,
        default=0,
        help="0 to not have verbose, 1 to have it verbose",
    )

    parser.add_argument(
        "--overwrite_recorder",
        "--o",
        type=int,
        default=0,
        help="0 to not overwrite recorder, 1 to have it overwrite recorder",
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

    if "system_level_control" in plant_config:
        # dont print solver loops
        plant_config["system_level_control"]["solver_options"]["iprint"] = (
            args.iprint_setting
        )
    output_dir = Path(driver_config["general"]["folder_output"])
    if not output_dir.exists():
        Path.mkdir(Path(output_dir), parents=True, exist_ok=True)

    # os.chdir(output_dir)

    driver_config["recorder"]["flag"] = True
    # driver_config["recorder"]["file"] = "cases_output_v3.sql"
    driver_config["recorder"]["recorder_attachment"] = (
        "driver"  # connect to driver when running in parallel
    )
    driver_config["driver"]["parameter_sweep"]["run_parallel"] = False
    driver_config["driver"]["parameter_sweep"]["debug_print"] = bool(args.debug_print)
    # don't overwrite the recorder, since doing manual parallelization
    driver_config["recorder"]["overwrite_recorder"] = bool(args.overwrite_recorder)

    initial_site_list_fpath = driver_config["driver"]["parameter_sweep"]["filename"]
    site_df = pd.read_csv(initial_site_list_fpath)
    # fac_id_cols = [
    #     k for k in site_df.columns.to_list() if ".plant_code" in k or ".facility_id" in k
    # ]
    # site_code_list = sorted(set(site_df[fac_id_cols[0]].to_list()))

    config = {
        "plant_config": copy.deepcopy(plant_config),
        "technology_config": copy.deepcopy(tech_config),
        "driver_config": copy.deepcopy(driver_config),
    }

    main(copy.deepcopy(site_df), copy.deepcopy(config), verbose=bool(args.verbose))
