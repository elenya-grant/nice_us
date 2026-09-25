import os
from pathlib import Path

from h2integrate import H2IntegrateModel, load_yaml

# uncomment below if nice_us is installed and so is H2I
# (using Elenya's H2I branch called 'spheres/arbitrage')
# from nice import DATA_DIR, ROOT_DIR

# below is used if nice_us isn't installed, but H2I is
this_dir = Path(__file__).parent
ROOT_DIR = this_dir.parent.parent / "nice"
DATA_DIR = this_dir.parent.parent / "data"

os.chdir(this_dir)

tech_config = load_yaml(this_dir / "tech_config.yaml")

tech_config["technologies"]["grid_sell"]["model_inputs"]["cost_parameters"][
    "data_directory"
] = str(this_dir)
tech_config["technologies"]["grid_buy"]["model_inputs"]["cost_parameters"][
    "data_directory"
] = str(this_dir)
tech_config["technologies"]["existing_plant"]["model_inputs"]["performance_parameters"][
    "data_directory"
] = str(this_dir)
tech_config["technologies"]["existing_plant"]["model_inputs"]["performance_parameters"][
    "campd_eia_filepath"
] = str(DATA_DIR / "campd_ratio_sitelist_518_facilities.csv")

custom_grid_model_path = ROOT_DIR / "simulation" / "h2i_models" / "custom_grid.py"
tech_config["technologies"]["grid_sell"]["cost_model"]["model_location"] = str(
    custom_grid_model_path
)
tech_config["technologies"]["grid_buy"]["cost_model"]["model_location"] = str(
    custom_grid_model_path
)

campd_model_path = ROOT_DIR / "simulation" / "h2i_models" / "campd.py"
tech_config["technologies"]["existing_plant"]["performance_model"]["model_location"] = (
    str(campd_model_path)
)

plant_config = load_yaml(this_dir / "plant_config.yaml")
driver_config = load_yaml(this_dir / "driver_config.yaml")

config = {
    "plant_config": plant_config,
    "technology_config": tech_config,
    "driver_config": driver_config,
}

h2i = H2IntegrateModel(config)
h2i.setup()
h2i.run()
