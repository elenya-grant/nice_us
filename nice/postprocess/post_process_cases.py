import pandas as pd
from nice import LIBRARY_DIR

from pathlib import Path

existing_plant_types = [
    "fixed_solar",
    "one_axis_solar",
    "thermal",
    "wind"
]

add_on = [
    "solar",
    "battery",
    "solar_battery"
]


filtered_results = pd.DataFrame()
for plant_type in existing_plant_types:
    for added in add_on:
        print(f"\n\nProcessing existing {plant_type} with add-on {added}")
        if added == "solar_battery":
            output_dirs = {
                "fixed_solar": "outputs_subset0",
                "one_axis_solar": "outputs_subset0_abcd",
                "wind": "outputs_subset_abcd",
                "thermal": "outputs_subset0_ab"
            }
            output_path = Path(LIBRARY_DIR) / "h2i_sweep_0" / f"existing_{plant_type}_add_{added}"/output_dirs[plant_type]
            df = pd.read_csv(output_path / "cases.csv")
        else:
            output_path = Path(LIBRARY_DIR) / "h2i_sweep_0" / f"existing_{plant_type}_add_{added}/outputs_subset0/"
            df = pd.read_csv(output_path / "cases.csv")
            
        input_df = pd.read_csv(Path(LIBRARY_DIR) / f"h2i_sweep_0/existing_{plant_type}_add_{added}/design_sweep_facilities_subset_subset0.csv")
        
        # compare the cases in the output CSV with the input design sweep facilities CSV
        print(f"Input n_facilities: ", input_df["grid_sell.plant_code"].nunique(), "Output n_facilities: ", df["grid_sell.plant_code (unitless)"].nunique())
        
        # save the different plant codes between input and output
        different_plant_codes = set(input_df["grid_sell.plant_code"]) - set(df["grid_sell.plant_code (unitless)"])
        if different_plant_codes:
            print(f"Different plant codes for existing {plant_type} with add-on {added}: {different_plant_codes}")
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
        if not df_positive_npv.empty:
            df_positive_npv.to_csv(output_path / "cases_positive_npv.csv", index=False)