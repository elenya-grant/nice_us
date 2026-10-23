import pandas as pd
from nice import LIBRARY_DIR

from pathlib import Path

outputs_dir = Path(LIBRARY_DIR) / "h2i_sweep_0/outputs"

existing_plant_types = [
    # "fixed_solar",
    # "one_axis_solar",
    # "thermal",
    "wind"
]

add_on = [
    # "solar",
    # "battery",
    "solar_battery"
]

for plant_type in existing_plant_types:
    for added in add_on:
        df = pd.read_csv(outputs_dir / f"existing_{plant_type}_add_{added}/cases.csv")
        
        # count the number of cases where the value in the "finance_subgroup_added_electricity.NPV_electricity (USD)" column is greater than 0
        count_positive_npv = (df["finance_subgroup_added_electricity.NPV_electricity (USD)"] > 0).sum()
        print(f"Number of positive NPV cases for existing {plant_type} with add-on {added}: {count_positive_npv}")
        
        # what's the least negative NPV
        
        df_positive_npv = df[df["finance_subgroup_added_electricity.NPV_electricity (USD)"] > 0]
        # df_negative_npv = df[df["finance_subgroup_added_electricity.NPV_electricity (USD)"] <= 0]
        # least_negative_npv = df_negative_npv["finance_subgroup_added_electricity.NPV_electricity (USD)"].max()
        # print(f"Least negative NPV for existing {plant_type} with add-on {added}: {least_negative_npv}")
        
        # print the facility with the largest positive NPV
        if not df_positive_npv.empty:
            max_npv_facility = df_positive_npv.loc[df_positive_npv["finance_subgroup_added_electricity.NPV_electricity (USD)"].idxmax()]["grid_sell.plant_code (unitless)"]
            print(f"Facility with the largest positive NPV for existing {plant_type} with add-on {added}: {max_npv_facility}")
        
        # count number of unique "grid_sell.plant_code (uniteless)"
        unique_plant_codes = df_positive_npv["grid_sell.plant_code (unitless)"].nunique()
        print(f"Number of unique plant codes for positive NPV cases for existing {plant_type} with add-on {added}: {unique_plant_codes}")
        
        # # save the positive NPV cases to a new CSV file
        df_positive_npv.to_csv(outputs_dir / f"existing_{plant_type}_add_{added}/cases_positive_npv.csv", index=False)
