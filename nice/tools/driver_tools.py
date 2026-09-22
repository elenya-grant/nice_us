from nice import LIBRARY_DIR
from nice.tools.file_tools import load_yaml, write_yaml


def write_driver_file(design_var_to_units, driver_fpath, doe_csv_fname):
    template_fpath = LIBRARY_DIR / "h2i" / "template_driver_config.yaml"

    driver_template = load_yaml(template_fpath)
    driver_template["driver"]["parameter_sweep"]["filename"] = doe_csv_fname
    design_vars = {}
    for d_var, units in design_var_to_units.items():
        tech, tech_var = d_var.split(".")
        d_var_entry = {
            tech_var: {
                "flag": True,
                "units": units,
                "lower": None,
                "upper": None,
            }
        }
        if tech in design_vars:
            design_vars[tech][tech_var] = d_var_entry[tech_var]
        else:
            design_vars[tech] = d_var_entry

    driver_template["design_variables"] = design_vars
    write_yaml(driver_fpath, driver_template)
    # with template_fpath.open(mode="r") as file:
    #     content = file.read()
