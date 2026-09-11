# from h2integrate import H2Integrate
from nice import LIBRARY_DIR

# from h2integrate.core.file_utils import load_yaml
# from h2integrate.core.inputs.validation import load_tech_yaml, load_plant_yaml, load_driver_yaml
from nice.tools.file_tools import load_yaml

tech_config_folder = LIBRARY_DIR / "h2i" / "tech_config"


def get_techs_from_tech_connections(tech_connections):
    techs = set()
    for connect in tech_connections:
        techs |= set(connect[0:2])

    return list(techs)


def add_tech_to_config(tech_config, tech_name, tech_filename):
    tech_params = load_yaml(tech_config_folder / tech_filename)
    if "model_inputs" in tech_params:
        tech_config[tech_name] = tech_params
    else:
        # file has tech names
        tech_config |= tech_params

    return tech_config


def make_tech_config(tech_names, existing_case, add_on_case, existing_pv_type="fixed"):
    tech_config = {}
    always_expected_techs = ["existing_plant", "poi_demand", "grid_sell"]
    if not set(tech_names) >= set(always_expected_techs):
        missing_techs = list(set(always_expected_techs) - set(tech_names))
        # some always_expected_tech is not in techs
        raise ValueError(f"missing technologies {missing_techs}")

    tech_config = add_tech_to_config(tech_config, "grid_sell", "grid_sell.yaml")
    tech_config = add_tech_to_config(tech_config, "poi_demand", "poi_demand.yaml")
    existing_tech_fname = (
        f"existing_{existing_pv_type}_solar.yaml"
        if existing_case == "solar"
        else f"existing_{existing_case}.yaml"
    )
    tech_config = add_tech_to_config(tech_config, "existing_plant", existing_tech_fname)
    if add_on_case == "solar":
        tech_config = add_tech_to_config(tech_config, "solar_add_on", "add_solar.yaml")
    else:
        tech_config = add_tech_to_config(
            tech_config, add_on_case, f"add_{add_on_case}.yaml"
        )

    demand_techs = [k for k in tech_names if "demand" in k]
    combiner_techs = [k for k in tech_names if "combiner" in k]
    for dmd_tech in demand_techs:
        tech_config = add_tech_to_config(tech_config, dmd_tech, "poi_demand.yaml")
    for combiner_tech in combiner_techs:
        tech_config = add_tech_to_config(tech_config, combiner_tech, "combiner.yaml")

    techs_included = set(tech_config)

    extra_techs = techs_included - set(tech_names)
    not_found_techs = set(tech_names) - techs_included
    if bool(extra_techs):
        msg = f"Extra techs added to tech_config: {sorted(extra_techs)}"
        raise ValueError(msg)
    if bool(not_found_techs):
        msg = f"Missing techs: {sorted(extra_techs)} in tech_config"
        raise ValueError(msg)

    return {"technologies": tech_config}


def run_h2i(plant_config, tech_config, driver_config):
    from h2integrate import H2Integrate
    from h2integrate.core.inputs.validation import (
        load_driver_yaml,
        load_plant_yaml,
        load_tech_yaml,
    )

    config = {
        "plant_config": load_plant_yaml(plant_config),
        "technology_config": load_tech_yaml(tech_config),
        "driver_config": load_driver_yaml(driver_config),
    }

    h2i = H2Integrate(config)

    h2i.setup()

    h2i.run()


existing_plant_case = "wind"  # ["wind","solar","thermal"]
add_on_case = "solar"  # ["solar","battery","solar_battery"]

case_folder = LIBRARY_DIR / "h2i" / f"existing_{existing_plant_case}_add_{add_on_case}"
# plant_config = load_plant_yaml(case_folder/"plant_config.yaml")
plant_config = load_yaml(case_folder / "plant_config.yaml")
tech_names = get_techs_from_tech_connections(
    plant_config["technology_interconnections"]
)
tech_config = make_tech_config(tech_names, existing_plant_case, add_on_case)

# TODO: still need to add driver update stuff
[]
