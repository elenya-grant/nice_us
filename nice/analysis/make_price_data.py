import warnings
from pathlib import Path

import numpy as np
import pandas as pd

from nice import DATA_DIR
from nice.tools.df_tools import convert_to_type
from nice.tools.eia_860_file_tools import load_eia_860
from nice.tools.file_tools import check_create_folder

run_local = True

if run_local:
    price_node_mapper_path = DATA_DIR / "lmp" / "facility_lmp_mapping(in).csv"
    lmp_dir = DATA_DIR / "lmp"
    net_load_dir = DATA_DIR / "net_load"
    net_load_fname = "Net_Load_subset_2025.csv"
    price_profile_output_dir = DATA_DIR / "price_profiles"
else:
    net_load_dir = Path("/projects/surint/campd_spheres/net_load")
    net_load_fname = "Net_Load.csv"
    lmp_dir = Path("/projects/surint/campd_spheres/lmp_data")
    price_node_mapper_path = lmp_dir / "facility_lmp_mapping(in).csv"
    price_profile_output_dir = Path("/projects/surint/campd_spheres/price_profiles")

check_create_folder(price_profile_output_dir)

data_year = 2025
# load_year = 2025

"""
This script processes EIA 860 generator and plant data to calculate capacity value based on net load and LMP data.
It filters plants by size and prime mover, and distributes net cone values over the highest net load hours.
Load the LMP data based on the PRICE NODE for each plant. Combine day ahead price with the calculated "capacity value".
The calculated capacity value is distributed over the highest net load hours. The value is the net cone value per kW per year.
The annual net cone is then multiplied across the top 3% of the hours. The highest hour gets the highest portion of the value
that's calculated using the ratio of the net load in that hour to the total net load across the top 3% of hours.
The resulting value is then added to the day-ahead LMP to get the final price signal for each hour.
This should be output for each facility as a time series of hourly prices.
"""
# only need data for plants that are > 10 MW
generators = load_eia_860(file="Generator", sheet="Operable", year=data_year)
convert_to_type(generators, "Plant Code", "Plant Code", int)


# sum "Nameplate Capacity (MW)" for each "Plant Code"
plant_capacity = generators.groupby("Plant Code")["Nameplate Capacity (MW)"].sum()
# filter out plants that are <= 10 MW
plant_capacity = plant_capacity[plant_capacity > 10]

# only keep "Prime Movers" == "ST", "GT", "IC", "CA", "CT", "CS", "PV", "WT"
# ST = Steam turbine, including nuclear, geothermal, and solar steam
# GT = Combustion (Gas) Turbine (does not include the combustion turbine part of a combined cycle; see code CT, below
# IC = Internal Combustion Engine  (diesel, piston, reciprocating)
# CA = Combined Cycle Steam Part
# CT = Combined Cycle Combustion Turbine Part
# CS = Combined Cycle Single Shaft (combustion turbine and steam turbine share a single generator)
# CC = Combined Cycle Total Unit (use only for plants/generators that are in planning stage
# PV = Photovoltaic
# WT = Wind Turbine, Onshore
prime_movers = ["ST", "GT", "IC", "CA", "CT", "CS", "PV", "WT"]
generators = generators[generators["Prime Mover"].isin(prime_movers)]

# only keep plants that are > 10 MW
generators = generators[generators["Plant Code"].isin(plant_capacity.index)]

# Use plant file to get BA Code
plants = load_eia_860(file="Plant", sheet="Plant", year=data_year)
convert_to_type(plants, "Plant Code", "Plant Code", int)
# convert_to_type(plants, "Primary Purpose (NAICS Code)", "Primary Purpose (NAICS Code)", int)

# Primary Purpose (NAICS Code) only keep plants with code 22
plants = plants[plants["Primary Purpose (NAICS Code)"] == 22]

# only keep plants that have the same "Plant Code" that are in generators
plants = plants[plants["Plant Code"].isin(generators["Plant Code"].unique())]

# get net cone value for correct ISO
# https://www.lazard.com/research-insights/levelized-cost-of-energyplus-lcoeplus/
# $/kw-month
net_cone = {
    "MISO": 6.49,
    "PJM": 5.50,
    "CISO": 7.34,
    "ERCO": 11.67,
    "SPP": 7.13,
    "NYIS": 5.80,
}
net_cone["OTHER"] = np.average(list(net_cone.values()))
net_cone_per_kw_year = {iso: value * 12 for iso, value in net_cone.items()}  # $/kw-year
# Convert to USD/MW-year
net_cone_per_MW_year = {
    iso: value * 1000 for iso, value in net_cone_per_kw_year.items()
}

# load LMP plant id to price node mapper
price_node_cols = [
    "Plant Code",
    "Generator ID",
    "Prime Mover",
    "Mapped_Price_Node",
    "Mapped_ISO_Name",
    "Mapped_Price_Node_ID",
]
price_node_mapper = pd.read_csv(price_node_mapper_path, usecols=price_node_cols)
convert_to_type(price_node_mapper, "Plant Code", "Plant Code", int)
price_node_mapper = price_node_mapper[
    price_node_mapper["Prime Mover"].isin(prime_movers)
]
price_node_mapper = price_node_mapper[
    price_node_mapper["Plant Code"].isin(plant_capacity.index)
]
price_node_mapper = price_node_mapper[
    price_node_mapper["Plant Code"].isin(generators["Plant Code"].unique())
]

price_node_mapper_iso_rename = {
    "Midcontinent ISO": "MISO",
    "PJM ISO": "PJM",
    "California ISO": "CISO",
    "ERCOT ISO": "ERCO",
    "New England ISO": "OTHER",  # what is this?
    "New York ISO": "NYIS",
    "Northern Maine Independent System A": "OTHER",
}

# rename ISOs in price node mapper
price_node_mapper.replace(
    to_replace={"Mapped_ISO_Name": price_node_mapper_iso_rename}, inplace=True
)

price_node_mapper.set_index(keys=["Plant Code"], inplace=True)


# for each unique plant code in generators
# net_load = pd.read_csv(path + f"EIA930_BALANCE_{data_year}_with_Net_Load.csv")
# NOTE: or should we be using Net_Load.csv?
# net_load1 = pd.read_csv(net_load_dir + f"EIA930_BALANCE_{data_year}_Jan_Jun.csv")
# net_load2 = pd.read_csv(net_load_dir + +f"EIA930_BALANCE_{data_year}_Jul_Dec.csv")
# net_load_df = pd.concat([net_load1, net_load2], axis=1)
net_load_df = pd.read_csv(net_load_dir / net_load_fname)
time_profile = pd.to_datetime(net_load_df["UTC Time at End of Hour"], utc=True)
net_load_df["Year (UTC)"] = [
    time_profile.iloc[i].year for i in range(len(time_profile))
]
net_load_df["Time Profile (UTC)"] = time_profile
# Remove data from years that aren't the data-year
net_load_df = net_load_df[net_load_df["Year (UTC)"] == data_year]

# fill nans with zero
net_load_df["Net_Load"] = net_load_df["Net_Load"].fillna(0)

# Get list of balancing authorities that don't have full timeseries data
load_bas = net_load_df["Balancing Authority"].unique()
net_load_df.set_index(keys="Balancing Authority", inplace=True)
non_yearly_bas = {
    k: len(net_load_df.loc[k]) for k in load_bas if len(net_load_df.loc[k]) != 8760
}

# NOTE: only Balancing authority that does not have yearly net load
# info and is in the `plants`` dataframe is 'WWA'
# and its only for 1 site (plant code 57995), which is a wind plant
# plant_codes = [879]
for p in plants["Plant Code"].unique():
    # plant id 69875 has 1 generatior, so does 69748
    # Get balancing authority code for this plant (for net-load data)
    ba_code = plants.loc[plants["Plant Code"] == p, "Balancing Authority Code"].values[
        0
    ]

    if ba_code in non_yearly_bas:
        warnings.warn(
            f"Balancing Authority {ba_code} has non-yearly net_load",
            UserWarning,
            stacklevel=3,
        )

    if isinstance(price_node_mapper.loc[p, "Mapped_ISO_Name"], str):
        # just one generator in the price_node_mapper
        iso_name = price_node_mapper.loc[p, "Mapped_ISO_Name"]
        price_node_id = price_node_mapper.loc[p, "Mapped_Price_Node_ID"]
    else:
        # Get ISO name
        iso_name = price_node_mapper.loc[p, "Mapped_ISO_Name"].values[0]
        price_node_id = price_node_mapper.loc[p, "Mapped_Price_Node_ID"].values[0]

    # inputs = {"plant_code": [p]}

    # --------- Load LMP file
    # pull energy market price per plant
    # use day-ahead LMP
    # stored on HPC in /projects/surint/campd_spheres/nationwide/
    # path = "/projects/surint/campd_spheres/nationwide/"
    # Get LMP Price node name from price_node_mapper
    # Get LMP Price node number from price node mapper
    # lmp = pd.read_csv(lmp_dir + f"plant_{int(inputs['plant_code'][0])}.csv")

    lmp_fpath = lmp_dir / f"{price_node_id}_{data_year}.csv"
    if lmp_fpath.exists():
        # Load LMP File
        lmp = pd.read_csv(lmp_fpath)
        lmp_time_profile = pd.to_datetime(lmp["GMT Datetime (Hour Ending)"], utc=True)
        lmp["Year (UTC)"] = [
            lmp_time_profile.iloc[i].year for i in range(len(lmp_time_profile))
        ]
        # Filter data to data_year
        lmp = lmp[lmp["Year (UTC)"] == data_year]
        lmp["Time Profile (UTC)"] = lmp_time_profile
        # Set index to time profile and sort
        lmp.set_index(keys=["Time Profile (UTC)"], inplace=True)
        lmp.sort_index(inplace=True)

        # Get the lmp price data
        lmp_da = lmp["Price ($/MWh)"].values

        # Check the length of the LMP data
        if len(lmp_da) != 8760:
            msg = (
                f"Facility ID {p} (with LMP Price Node ID {price_node_id}) "
                f"for {data_year} has price of length {len(lmp_da)}"
            )
            warnings.warn(msg, UserWarning, stacklevel=3)
    else:
        lmp_da = np.zeros(8760)
        msg = f"LMP file {lmp_fpath} does not exist."
        warnings.warn(msg, UserWarning, stacklevel=3)

    # ----- Get Net Load For Balancing Authority-----
    net_load = net_load_df.loc[ba_code].copy(deep=True)
    net_load.set_index("Time Profile (UTC)", inplace=True)
    net_load.sort_index(inplace=True)
    time_index = net_load.index.to_list()

    # get net load for capacity value calculation
    net_load = net_load["Net_Load"].values * 1000  # MW -> kW
    # TODO: local time? UTC? want net load values starting at 00:00 UTC
    # Columns UTC Time at End of Hour, Local Time at End of Hour, Hour Number, Data Date

    if len(net_load) != 8760:
        msg = (
            f"Facility ID {p} (in Balancing Authority {ba_code}) "
            f"has Net_Load of length {len(net_load)}"
        )
        warnings.warn(msg, UserWarning, stacklevel=3)

    # get the top percentage of net load hours to use for capacity value calculation
    percentage_net_load = 0.03
    threshold_value = np.sort(net_load)[-int(len(net_load) * percentage_net_load)]

    # find the top percentage of net load hours, retain the indices of those hours
    top_percentage_indices = np.argwhere(net_load > threshold_value).flatten()

    # keep vals in top_percentage_indices else zero
    top_net_load = np.where(net_load > threshold_value, net_load, 0)
    # get the ratio of net load to sum of net load, distribute capacity payments over these hours
    total_peak_vals = np.sum(top_net_load)
    net_load_ratio = top_net_load / total_peak_vals

    if iso_name not in net_cone:  # NOTE: balancing authority or ISO?
        iso_name = "OTHER"
    # distributed the net_cone_per_kw_year over highest net load hours of the year
    capacity_value = net_cone_per_MW_year[iso_name] * net_load_ratio  # $/MW

    # Combine capacity value with lmp_da, price
    # price_profile = capacity_value + lmp_da

    price_profile_df = pd.DataFrame(
        {
            "LMP ($/MWh)": lmp_da,
            "Capacity Payment ($/MWh)": capacity_value,
            "Time (UTC)": time_index,
        }
    )
    price_profile_output_fpath = (
        price_profile_output_dir / f"{p}_{data_year}_price_profile.csv"
    )
    price_profile_df.to_csv(price_profile_output_fpath)

    # TODO: save capacity_value + lmp_da to a csv file named as the facility name
