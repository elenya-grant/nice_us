# from h2integrate import H2Integrate
from nice import LIBRARY_DIR, ROOT_DIR
# from h2integrate.core.file_utils import load_yaml
# from h2integrate.core.inputs.validation import load_tech_yaml, load_plant_yaml, load_driver_yaml
from nice.tools.file_tools import load_yaml, check_create_folder

tech_config_folder = LIBRARY_DIR/"h2i"/"tech_config"
sql_output_dir = ROOT_DIR.parent/"doe_results"

def get_techs_from_tech_connections(tech_connections):
    techs = set()
    for connect in tech_connections:
        techs |= set(connect[0:2])

    return list(techs)

def add_tech_to_config(tech_config, tech_name, tech_filename):
    tech_params = load_yaml(tech_config_folder/tech_filename)
    if "model_inputs" in tech_params:
        tech_config[tech_name] = tech_params
    else:
        # file has tech names
        tech_config |= tech_params
    
    return tech_config

def make_tech_config(tech_names, existing_case, add_on_case, existing_pv_type="fixed"):
    if existing_case =="solar" and existing_pv_type is None:
        raise ValueError("Existing pv type is required when existing_case is solar")
    
    tech_config = {}
    always_expected_techs = ["existing_plant", "poi_demand", "grid_sell"]
    if not set(tech_names) >= set(always_expected_techs):
        missing_techs = list(set(always_expected_techs) - set(tech_names))
        # some always_expected_tech is not in techs
        raise ValueError(f"missing technologies {missing_techs}")

    tech_config = add_tech_to_config(tech_config, "grid_sell", "grid_sell.yaml")
    tech_config = add_tech_to_config(tech_config, "poi_demand", "poi_demand.yaml")
    existing_tech_fname = f"existing_{existing_pv_type}_solar.yaml" if existing_case == "solar" else f"existing_{existing_case}.yaml"
    tech_config = add_tech_to_config(tech_config, "existing_plant", existing_tech_fname)
    if add_on_case == "solar":
        tech_config = add_tech_to_config(tech_config, "solar_add_on", "add_solar.yaml")
    else:
        tech_config = add_tech_to_config(tech_config, add_on_case, f"add_{add_on_case}.yaml")

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
        msg = (
            f"Extra techs added to tech_config: {sorted(extra_techs)}"
        )
        raise ValueError(msg)
    if bool(not_found_techs):
        msg = (
            f"Missing techs: {sorted(extra_techs)} in tech_config"
        )
        raise ValueError(msg)
    
    return {"technologies":tech_config}
   

def check_format_csv_file(driver_config, doe_csv_path):
    from h2integrate.core.dict_utils import update_defaults
    from h2integrate.core.file_utils import check_file_format_for_csv_generator
    new_csv_filename = check_file_format_for_csv_generator(
        doe_csv_path,
        driver_config,
        check_only=False,
        overwrite_file=True,
    )
    # below is only needed if overwrite_file is False
    # updated_driver = update_defaults(
    #     driver_config["driver"],
    #     "filename",
    #     new_csv_filename.name,
    # )
    # driver_config["driver"].update(updated_driver)

    return driver_config

def make_h2i_input_files(existing_plant_case, add_on_case, **existing_plant_kwargs):
    existing_plant_case = "wind"  # ["wind","solar","thermal"]
    add_on_case = "solar"  # ["solar","battery","solar_battery"]

    case_folder = LIBRARY_DIR / "h2i" / f"existing_{existing_plant_case}_add_{add_on_case}"
    # plant_config = load_plant_yaml(case_folder/"plant_config.yaml")
    plant_config = load_yaml(case_folder / "plant_config.yaml")
    tech_names = get_techs_from_tech_connections(
        plant_config["technology_interconnections"]
    )

    # Make tech config file
    if existing_plant_case=="solar" and "array_type" not in existing_plant_kwargs:
        msg = (
            "Please provide array_type in kwargs if existing plant is solar"
        )
        raise ValueError(msg)
    elif existing_plant_case=="solar" and "array_type" in existing_plant_kwargs:
        tech_config = make_tech_config(tech_names, existing_plant_case, add_on_case, existing_pv_type=existing_plant_kwargs["array_type"])

    else:
        # NOTE: make_tech_config is not set-up to update the filename for the thermal plant tech yet
        tech_config = make_tech_config(tech_names, existing_plant_case, add_on_case)

    if existing_plant_case=="thermal" and "n_facilities" not in existing_plant_kwargs:
        msg = (
            "Please provide n_facilities in kwargs if existing plant is thermal"
        )
        raise ValueError(msg)
    
    # Make driver config file
    driver_config_filename = "driver_config.yaml"

    if existing_plant_case == "thermal":
        n_facilities = existing_plant_kwargs["n_facilities"]
        doe_csv_filename = f"existing_{existing_plant_case}_add_{add_on_case}_doe_{n_facilities}_facilities.csv"
        recorder_filename = f"existing_{existing_plant_case}_add_{add_on_case}_{n_facilities}_facilities.sql"
    elif existing_plant_case == "solar":
        pv_type = existing_plant_kwargs["array_type"]
        doe_csv_filename = f"existing_{pv_type}_{existing_plant_case}_add_{add_on_case}_doe.csv"
        driver_config_filename = f"driver_config_{pv_type}.yaml"
        recorder_filename = f"existing_{pv_type}_{existing_plant_case}_add_{add_on_case}.sql"
    else:
        doe_csv_filename = f"existing_{existing_plant_case}_add_{add_on_case}_doe.csv"
        recorder_filename = f"existing_{existing_plant_case}_add_{add_on_case}.sql"

    driver_config = load_yaml(case_folder/driver_config_filename)
    driver_config["general"]["folder_output"] = sql_output_dir
    driver_config["driver"]["parameter_sweep"]["filename"] = case_folder/doe_csv_filename
    driver_config["recorder"]["file"] = recorder_filename
    check_create_folder(sql_output_dir)
    check_format_csv_file(driver_config, case_folder/doe_csv_filename)

    top_level_config = {
        "driver_config":driver_config,
        "technology_config": tech_config,
        "plant_config": plant_config,
    }
    return top_level_config

# if __name__ == "__main__":    
#     existing_cases = ["thermal","solar","wind"]
#     add_on_cases = ["solar","battery","solar_battery"]
#     kwargs = {
#         "array_type": "fixed", # "fixed" or "one_axis"
#         "n_facilities": 515,
#     }
