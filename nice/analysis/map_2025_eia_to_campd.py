import pandas as pd

from nice import DATA_DIR
from nice.tools.eia_860_file_tools import load_eia_860
from nice.tools.eia_923_file_tools import load_eia_923

##### Check matches between the CAMPD data on HPC that was downloaded and the EIA crosswalk
# https://github.com/USEPA/camd-eia-crosswalk/tree/master
# There is a discrepancy between generators because CAMPD is meant to track emissions and
# EIA is meant to track electricity generation.
# We want to match all of the generators between CAMPD and EIA923 2025
# pull extra data for each generator from EIA 860

# read in CAMPD, EIA crosswalk, EIA 923, EIA 860
crosswalk = pd.read_csv(DATA_DIR / "epa_eia_crosswalk.csv")
campd = pd.read_csv(DATA_DIR / "summary_of_nan_profiles.csv")
# read in EIA 923
eia_923 = load_eia_923("M_12", sheet="Page 4 Generator Data", year=2025)
# read in EIA 860
eia_860 = load_eia_860("Generator", sheet="Operable", year=2025)

# check for each facility and unit in campd check if it exists in the crosswalk
# campd columns
cols = ["Facility ID", "Unit ID"]

# rename crosswalk columns to match campd columns
crosswalk.rename(
    columns={"CAMD_PLANT_ID": "Facility ID", "CAMD_UNIT_ID": "Unit ID"}, inplace=True
)

# set index for campd and crosswalk based on the key columns
campd.set_index(cols, inplace=True)
crosswalk.set_index(cols, inplace=True)

# find common indices between campd and crosswalk
common_indices = campd.index.intersection(crosswalk.index)

# join data using common indices
campd_eia_df = campd.loc[common_indices].join(crosswalk.loc[common_indices], how="left")

# count number of facilities in the common indices
num_facilities_common = (
    campd_eia_df.loc[common_indices].reset_index()["Facility ID"].nunique()
)
print(f"Number of facilities in common indices: {num_facilities_common}")

# missing in crosswalk
missing_in_crosswalk = campd.index.difference(crosswalk.index)
print(f"Number of rows missing in crosswalk: {len(missing_in_crosswalk)}")

missing_rows_in_crosswalk = campd.loc[missing_in_crosswalk]
# missing_rows_in_crosswalk.reset_index().to_csv(DATA_DIR / 'differences_campd_crosswalk.csv', index=False)

# campd_eia_df has the common indices between CAMPD and the crosswalk
campd_eia_df = campd_eia_df.reset_index()

# check if each row in campd_eia_df exists in EIA 923
# check using "Plant Id" and "Generator Id" to compare against "EIA_PLANT_ID" and "EIA_GENERATOR_ID"

# remove rows with NaN values in EIA_PLANT_ID or EIA_GENERATOR_ID
campd_eia_df = campd_eia_df.dropna(subset=["EIA_PLANT_ID", "EIA_GENERATOR_ID"])

# convert EIA_PLANT_ID and EIA_GENERATOR_ID to appropriate types before setting index
campd_eia_df["EIA_PLANT_ID"] = campd_eia_df["EIA_PLANT_ID"].astype("int64")
campd_eia_df["EIA_GENERATOR_ID"] = campd_eia_df["EIA_GENERATOR_ID"].astype("str")
campd_eia_df.set_index(["EIA_PLANT_ID", "EIA_GENERATOR_ID"], inplace=True)

# prepare EIA 923 for joining with campd_eia_df
eia_923.rename(
    columns={"Plant Id": "EIA_PLANT_ID", "Generator Id": "EIA_GENERATOR_ID"},
    inplace=True,
)
eia_923["EIA_PLANT_ID"] = eia_923["EIA_PLANT_ID"].astype("int64")
eia_923["EIA_GENERATOR_ID"] = eia_923["EIA_GENERATOR_ID"].astype("str")
eia_923.set_index(["EIA_PLANT_ID", "EIA_GENERATOR_ID"], inplace=True)

# find common and uncommon indices between campd_eia_df and eia_923
common_indices = campd_eia_df.index.intersection(eia_923.index)
uncommon_indices = campd_eia_df.index.difference(eia_923.index)
flip = eia_923.index.difference(campd_eia_df.index)
print(f"Number of rows in EIA 923 but not in campd_eia_df: {len(flip)}")
missing_rows_in_eia = eia_923.loc[flip]
# missing_rows_in_eia.reset_index().to_csv(DATA_DIR / 'differences_eia_campd.csv', index=False)

# compare missing_rows_in_eia and missing_rows_in_crosswalk save any common rows
# change missing_rows_in_eia
missing_rows_in_eia.rename(
    columns={"EIA_PLANT_ID": "Facility ID", "EIA_GENERATOR_ID": "Unit ID"}, inplace=True
)
common_missing = missing_rows_in_eia.index.intersection(missing_rows_in_crosswalk.index)
if not common_missing.empty:
    common_missing_rows = missing_rows_in_eia.loc[common_missing]
    extra_matches = common_missing_rows.copy()

    common_missing_rows.reset_index().to_csv(
        DATA_DIR / "extra_matches_eia_923_campd.csv", index=False
    )
    remaining_missing_rows = missing_rows_in_crosswalk.index.difference(common_missing)
    remaining_missing_rows = missing_rows_in_crosswalk.loc[remaining_missing_rows]
    remaining_missing_rows.reset_index().to_csv(
        DATA_DIR / "remaining_missing_rows_eia_campd.csv", index=False
    )

# save uncommon indices to CSV
uncommon_rows = campd_eia_df.loc[uncommon_indices].copy()
uncommon_rows.reset_index().to_csv(
    DATA_DIR / "differences_campd_crosswalk_923.csv", index=False
)

# Join data between CAMPD, crosswalk and EIA 923
crosswalk_eia_df = campd_eia_df.loc[common_indices].join(
    eia_923.loc[common_indices], how="left"
)

# Add extra matches to the crosswalk_eia_df but not all columns are in each df
crosswalk_eia_df = pd.concat([crosswalk_eia_df, extra_matches], axis=0)
crosswalk_eia_df.reset_index().to_csv(
    DATA_DIR / "2025_campd_eia_crosswalk.csv", index=False
)

# print number of facilities in common indices with EIA 923
num_facilities_common_eia = crosswalk_eia_df["Facility ID"].nunique()
print(
    f"Number of facilities in common indices with EIA 923: {num_facilities_common_eia}"
)


# get nameplate capacity from EIA 860
eia_860.rename(
    columns={
        "Plant Code": "EIA_PLANT_ID",
        "Generator ID": "EIA_GENERATOR_ID",
        "Nameplate Capacity (MW)": "Nameplate Capacity (MW)",
    },
    inplace=True,
)
eia_860.set_index(["EIA_PLANT_ID", "EIA_GENERATOR_ID"], inplace=True)
crosswalk_eia_df = crosswalk_eia_df.join(
    eia_860[["Nameplate Capacity (MW)"]], how="left"
)

# remove unnecessary columns from crosswalk_eia_df
crosswalk_eia_df.reset_index(inplace=True)
keep = [
    "Facility ID",
    "Unit ID",
    "EIA_PLANT_ID",
    "EIA_GENERATOR_ID",
    "Total Gross Load (MW)",
    "Net Generation Year To Date",
    "Nameplate Capacity (MW)",
]
crosswalk_eia_df = crosswalk_eia_df[keep]
crosswalk_eia_df.to_csv(
    DATA_DIR / "crosswalk_eia_per_generator_2025_cleaned.csv", index=False
)
# print number of unique facilities in crosswalk_eia_df
num_facilities_crosswalk = crosswalk_eia_df["Facility ID"].nunique()
print(f"Number of unique facilities in crosswalk_eia_df: {num_facilities_crosswalk}")

# Sum Total Gross Load (MW) and Net Generation Year To Date by Facility ID
summary = crosswalk_eia_df.groupby("Facility ID")[
    ["Total Gross Load (MW)", "Net Generation Year To Date", "Nameplate Capacity (MW)"]
].sum()
summary["ratio (net/gross)"] = (
    summary["Net Generation Year To Date"] / summary["Total Gross Load (MW)"]
)
if (summary["ratio (net/gross)"] > 1).any():
    # remove facilities with ratio > 1
    summary = summary[summary["ratio (net/gross)"] <= 1]
if (summary["ratio (net/gross)"] < 0).any():
    # set ratio to 0 for facilities with ratio < 0
    summary.loc[summary["ratio (net/gross)"] < 0, "ratio (net/gross)"] = 0
summary.rename(
    columns={"Net Generation Year To Date": "Net Generation (Megawatthours)"},
    inplace=True,
)
summary.reset_index(inplace=True)
# count number of facilities
num_facilities = summary.shape[0]
print(f"Number of facilities: {num_facilities}")
summary.to_csv(
    DATA_DIR / f"campd_ratio_sitelist_{num_facilities}_facilities.csv", index=False
)


# Need columns Facility ID,Net Generation (Megawatthours),Total Gross Load (MW),ratio (net/gross),Nameplate Capacity (MW)


# print(non_matched_in_eia)

[]
