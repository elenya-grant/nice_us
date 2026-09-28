import argparse

from h2integrate import H2IntegrateModel

from nice import LIBRARY_DIR
from nice.tools.file_tools import load_yaml


def main():
    """Command-line entry point for run_plants.py"""
    parser = argparse.ArgumentParser(
        description="Run plants",
        epilog=(
            "Example: "
            "python nice/simulation/run_plants.py --existing_plant wind --add_on_plant pv_bess"
        ),
    )
    # python nice/simulation/run_plants.py --existing_plant wind --add_on_plant pv_bess
    # parser.add_argument(
    #     "--existing_plant",
    #     "--e",
    #     type=str,
    #     help="Existing plant type (either 'wind', 'pv', 'campd')",
    # )
    # parser.add_argument(
    #     "--add_on_plant",
    #     "--a",
    #     type=str,
    #     help="Add on plant type (either 'pv','bess', or 'pv_bess')",
    # )

    # python nice/simulation/run_plants.py  wind  pv_bess
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

    if (LIBRARY_DIR / args.library_subdir).exists():
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

    driver_config["driver"]["parameter_sweep"]["run_parallel"] = True
    driver_config["driver"]["parameter_sweep"]["debug_print"] = False

    config = {
        "plant_config": plant_config,
        "technology_config": tech_config,
        "driver_config": driver_config,
    }

    h2i = H2IntegrateModel(config)
    h2i.setup()
    h2i.run()
