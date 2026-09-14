import numpy as np
import pandas as pd

from nice.tools.eia_860_file_tools import load_eia_860

data_year = 2025

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

# load LMP plant id to price node mapper
price_node_mapper_path = (
    "/projects/surint/campd_spheres/nationwide/facility_lmp_mapping(in).csv"
)
price_node_cols = [
    "Plant Code",
    "Generator ID",
    "Prime Mover",
    "Mapped_Price_Node",
    "Mapped_ISO_Name",
    "Mapped_Price_Node_ID",
]
price_node_mapper = pd.read_csv(price_node_mapper_path, usecols=price_node_cols)
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
    "New England ISO": "???",  # what is this?
    "New York ISO": "NYIS",
}

# rename ISOs in price node mapper
price_node_mapper.replace(
    to_replace={"Mapped_ISO_Name": price_node_mapper_iso_rename}, inplace=True
)


net_load_dir = "/projects/surint/campd_spheres/net_load/"
# for each unique plant code in generators
# net_load = pd.read_csv(path + f"EIA930_BALANCE_{data_year}_with_Net_Load.csv")
net_load1 = pd.read_csv(net_load_dir + f"EIA930_BALANCE_{data_year}_Jan_Jun.csv")
net_load2 = pd.read_csv(net_load_dir + +f"EIA930_BALANCE_{data_year}_Jul_Dec.csv")
net_load_df = pd.concat([net_load1, net_load2], axis=1)
net_load_df.set_index(keys="Balancing Authority", inplace=True)


for p in plants["Plant Code"].unique():
    inputs = {"plant_code": [p]}

    # --------- Load LMP file
    # pull energy market price per plant
    # use day-ahead LMP
    # stored on HPC in /projects/surint/campd_spheres/nationwide/
    path = "/projects/surint/campd_spheres/nationwide/"
    lmp = pd.read_csv(path + f"plant_{int(inputs['plant_code'][0])}.csv")

    lmp_da = lmp[
        "LMP_DA"
    ].values  # TODO: local time? UTC? get correct year, units MW or kw??

    # -------- Load correct BA net load
    ba_code = plants.loc[plants["Plant Code"] == p, "Balancing Authority Code"].values[
        0
    ]

    # net_load = net_load[net_load["Balancing Authority"] == ba_code]
    net_load = net_load_df.loc[ba_code].copy(deep=True)

    net_load.set_index("UTC Time at End of Hour", inplace=True)
    net_load.index = pd.to_datetime(net_load.index, utc=True)
    net_load.sort_index(inplace=True)

    # fill nans with zero
    net_load = net_load.fillna(0)

    # get net load for capacity value calculation
    net_load = net_load[
        "Net_Load"
    ].values  # TODO: local time? UTC? want net load values starting at 00:00 UTC
    # Columns UTC Time at End of Hour, Local Time at End of Hour, Hour Number, Data Date

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

    if ba_code not in net_cone:
        ba_code = "OTHER"
    # distributed the net_cone_per_kw_year over highest net load hours of the year
    capacity_value = net_cone_per_kw_year[ba_code] * net_load_ratio  # $/kw
