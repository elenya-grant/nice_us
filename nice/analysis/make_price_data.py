import warnings
from pathlib import Path

import numpy as np
import pandas as pd

from nice import DATA_DIR, LIBRARY_DIR
from nice.tools.df_tools import convert_to_type
from nice.tools.eia_860_file_tools import load_eia_860
from nice.tools.file_tools import check_create_folder

run_local = False
use_sitelists = True
# unique markets currently in LMP data as of 20261009
# ["RT5AVG", "DAH", "RTH", "HA15AVG", "RT15AVG", "RUC HOURLY"]
market_type = "DAH"  # Can use "DAH" and "HA15AVG" for day-ahead markets
run_version = "v6"

# v4 is first run version to use "lmp_facility_map_ready.csv"


def calc_capacity_payment_schedule(net_load, net_cone_value_per_MW_yr):
    # Calculate capacity payment

    success = True
    # get the top percentage of net load hours to use for capacity value calculation
    percentage_net_load = 0.03
    threshold_value = np.sort(net_load)[-int(len(net_load) * percentage_net_load)]

    # find the top percentage of net load hours, retain the indices of those hours
    # top_percentage_indices = np.argwhere(net_load > threshold_value).flatten()

    # keep vals in top_percentage_indices else zero
    top_net_load = np.where(net_load > threshold_value, net_load, 0)
    # get the ratio of net load to sum of net load, distribute capacity payments over these hours
    total_peak_vals = np.sum(top_net_load)

    if total_peak_vals == 0.0:
        success = False
        # msg = f"Plant {p} in BA {ba_code} has total peak vals of 0"
        # warnings.warn(msg, UserWarning, stacklevel=3)

    net_load_ratio = top_net_load / total_peak_vals

    # if iso_name not in net_cone:  # NOTE: balancing authority or ISO?
    #     iso_name = "OTHER"
    # distributed the net_cone_per_kw_year over highest net load hours of the year
    # capacity_value = net_cone_per_MW_year[iso_name] * net_load_ratio  # $/MW
    capacity_value = net_cone_value_per_MW_yr * net_load_ratio
    return capacity_value, success


def load_facility_files(data_year=2025, n_thermal_facs=616):
    sitelist_dir = LIBRARY_DIR / "h2i"
    existing_plant_types = ["one_axis_solar", "fixed_solar", "wind", "thermal"]
    facility_ids = set()
    for existing_type in existing_plant_types:
        if existing_type == "thermal":
            fname = f"existing_{existing_type}_plant_sitelist_{data_year}_{n_thermal_facs}_facilities.csv"
        else:
            fname = f"existing_{existing_type}_plant_sitelist_{data_year}.csv"

        sitelist_fpath = sitelist_dir / fname
        df = pd.read_csv(sitelist_fpath, usecols=["Plant Code"])
        facility_ids.update(set(df["Plant Code"].astype(int).to_list()))

    return sorted(facility_ids)


if run_local:
    price_node_mapper_path = DATA_DIR / "lmp" / "facility_lmp_mapping(in).csv"
    lmp_dir = DATA_DIR / "lmp"
    net_load_dir = DATA_DIR / "net_load"
    net_load_fname = "Net_Load_subset_2025.csv"
    price_profile_output_dir = DATA_DIR / "price_profiles"
else:
    net_load_dir = Path("/projects/surint/campd_spheres/net_load")
    net_load_fname = "Net_Load.csv"
    lmp_dir = Path("/projects/surint/campd_spheres/LMP/output_by_node_year")
    # lmp_dir = Path("/projects/surint/campd_spheres/lmp_data")
    # price_node_mapper_path = lmp_dir.parent / "facility_lmp_mapping.csv"
    lmp_data_cols = []
    price_node_mapper_path = lmp_dir.parent / "lmp_facility_map_ready.csv"
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
if use_sitelists:
    facility_ids = load_facility_files(data_year=data_year)
    plants = load_eia_860(file="Plant", sheet="Plant", year=data_year)
    convert_to_type(plants, "Plant Code", "Plant Code", int)
    plant_cols = ["Plant Code", "Balancing Authority Code"]
    plants.drop(
        columns=list(set(plants.columns.to_list()) - set(plant_cols)), inplace=True
    )
    plants = plants[plants["Plant Code"].isin(facility_ids)]
    if len(plants["Plant Code"].unique()) != len(facility_ids):
        msg = (
            f"Mismatch. EIA Plant data has {len(plants['Plant Code'].unique())} facilities, "
            f"but {len(facility_ids)} facilities were found in the sitelist"
        )
        warnings.warn(msg, UserWarning, stacklevel=3)
else:
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

# -------- define net cone value for correct ISO --------
# https://www.lazard.com/research-insights/levelized-cost-of-energyplus-lcoeplus/
# $/kw-month
net_cone = {
    "MISO": 6.49,
    "PJM": 5.50,
    "CISO": 7.34,
    "ERCO": 11.67,  # no capacity market
    "SPP": 7.13,
    "NYIS": 5.80,
}
net_cone["ISNE"] = np.average(list(net_cone.values()))
net_cone_per_kw_year = {iso: value * 12 for iso, value in net_cone.items()}  # $/kw-year
# Convert to USD/MW-year
net_cone_per_MW_year = {
    iso: value * 1000 for iso, value in net_cone_per_kw_year.items()
}

# -------- load LMP plant id to price node mapper --------
# below was for "facility_lmp_mapping.csv"
# price_node_cols = [
#     "Plant Code",
#     "Generator ID",
#     "Prime Mover",
#     "Mapped_Price_Node",
#     "Mapped_ISO_Name",
#     "Mapped_Price_Node_ID",
# ]
# price_node_mapper = pd.read_csv(price_node_mapper_path, usecols=price_node_cols)
# convert_to_type(price_node_mapper, "Plant Code", "Plant Code", int)

# below is for lmp_facility_map_ready.csv
price_node_mapper = pd.read_csv(price_node_mapper_path)
convert_to_type(price_node_mapper, "Plant Code", "Plant Code", int)
price_node_mapper.rename(
    columns={
        "Price_Node": "Mapped_Price_Node",
        "Price_Node_ID": "Mapped_Price_Node_ID",
    },
    inplace=True,
)

# Filter price node mapper to only include plants that are in the filtered plants list
price_node_mapper = price_node_mapper[
    price_node_mapper["Plant Code"].isin(plants["Plant Code"].unique())
]

# Identify facilities that are missing from the price node mapper
missing_facility_ids = sorted(
    set(plants["Plant Code"].to_list()) - set(price_node_mapper["Plant Code"].to_list())
)

print(f"{len(missing_facility_ids)} facilities missing from LMP data")

# Filter plants to only include those that have a corresponding entry in the price node mapper
plants = plants[plants["Plant Code"].isin(price_node_mapper["Plant Code"].unique())]
# price_node_mapper = price_node_mapper[
#     price_node_mapper["Prime Mover"].isin(prime_movers)
# ]
# price_node_mapper = price_node_mapper[
#     price_node_mapper["Plant Code"].isin(plant_capacity.index)
# ]
# price_node_mapper = price_node_mapper[
#     price_node_mapper["Plant Code"].isin(generators["Plant Code"].unique())
# ]
# EIA_860 BA Codes
# [nan, 'SOCO', 'EPE', 'MISO', 'CISO', 'TVA', 'PJM', 'SWPP', 'WACM',
# 'NYIS', 'PSEI', 'SRP', 'AZPS', 'TEPC', 'SC', 'SEC', 'BANC', 'WALC',
# 'PACE', 'TIDC', 'SPA', 'JEA', 'PACW', 'ERCO', 'IID', 'LDWP',
# 'BPAT', 'PSCO', 'WAUW', 'ISNE', 'AVA', 'FMPP', 'FPL', 'SCL', 'FPC',
# 'TEC', 'GVL', 'HST', 'NSB', 'TAL', 'SCEG', 'SEPA', 'IPCO', 'GCPD',
# 'CPLE', 'AECI', 'LGEE', 'NBSO', 'NWMT', 'NEVP', 'PNM', 'DUK',
# 'PGE', 'CHPD', 'DOPD', 'TPWR', 'YAD', 'AVRN', 'GRIF', 'DEAA',
# 'GRID', 'HECO', 'GWA', 'WWA', 'GRIS', 'CPLW', 'CEA', 'GLHB']

# Net_Load Balancing Authorities
# ['AECI',  'AVA', 'AVRN', 'AZPS', 'BANC', 'BPAT', 'CHPD', 'CISO', 'CPLE',
#  'CPLW', 'DEAA', 'DOPD',  'DUK',  'EPE', 'ERCO', 'FMPP',  'FPC',  'FPL',
#  'GCPD', 'GRID',  'GVL',  'GWA', 'HGMA',  'HST',  'IID', 'IPCO', 'ISNE',
#   'JEA', 'LDWP', 'LGEE', 'MISO', 'NEVP', 'NWMT', 'NYIS', 'PACE', 'PACW',
#   'PGE',  'PJM',  'PNM', 'PSCO', 'PSEI',   'SC', 'SCEG',  'SCL',  'SEC',
#  'SEPA', 'SIKE', 'SOCO',  'SPA',  'SRP', 'SWPP',  'TAL',  'TEC', 'TEPC',
#  'TIDC', 'TPWR',  'TVA', 'WACM', 'WALC', 'WAUW',  'WWA',  'YAD', 'GRIF',
#  'GLHB',  'AEC',  'EEI',  'NSB']

# in EIA but not in Net_Load Balancing Authorities
# 'NBSO', 'CEA', 'HECO', 'GRIS'
# in Net_Load Balancing Authorities but not in EIA
# 'HGMA', 'SIKE', 'AEC', 'EEI'

# Facility mapper file Mapped ISO names
price_node_mapper_iso_rename = {
    "Midcontinent ISO": "MISO",
    "PJM ISO": "PJM",
    "California ISO": "CISO",
    "ERCOT ISO": "ERCO",
    "New England ISO": "ISNE",
    "New York ISO": "NYIS",
    # "Northern Maine Independent System A": "OTHER",
}

# rename ISOs in price node mapper
if "Mapped_ISO_Name" in price_node_mapper.columns.to_list():
    price_node_mapper.replace(
        to_replace={"Mapped_ISO_Name": price_node_mapper_iso_rename}, inplace=True
    )

price_node_mapper.set_index(keys=["Plant Code"], inplace=True)

# -------- load the net load profiles --------
net_load_df = pd.read_csv(net_load_dir / net_load_fname)
time_profile = pd.to_datetime(net_load_df["UTC Time at End of Hour"], utc=True)
net_load_df["Year (UTC)"] = [
    time_profile.iloc[i].year for i in range(len(time_profile))
]
net_load_df["Time Profile (UTC)"] = time_profile
# Remove data from years that aren't the data-year
net_load_df = net_load_df[net_load_df["Year (UTC)"] == data_year]

# fill nans with zero
# net_load_df["Net_Load"] = net_load_df["Net_Load"].fillna(0)
# ts = pd.date_range(start=f"{data_year}-01-01 00:00:00", end=f"{data_year}-12-31 23:00:00", freq="1h")


# Get list of balancing authorities that don't have full timeseries data
load_bas = net_load_df["Balancing Authority"].unique()
net_load_df.set_index(keys="Balancing Authority", inplace=True)
non_yearly_bas = {
    k: len(net_load_df.loc[k]) for k in load_bas if len(net_load_df.loc[k]) != 8760
}
# Generation only BAs: AVRN, DEAA, EEI, GLHB, GRID, GRIF, GWA, HGMA, SEPA, SIKE, WWA, YAD
gen_only_bas = [
    "AVRN",
    "DEAA",
    "EEI",
    "GLHB",
    "GRID",
    "GRIF",
    "GWA",
    "HGMA",
    "SEPA",
    "SIKE",
    "WWA",
    "YAD",
]
non_conus_bas = ["NBSO", "CEA", "HECO", "GRIS"]
[
    "CISO",
    "CPLE",
    "CPLW",
    "DUK",
    "ERCO",
    "FMPP",
    "FPC",
    "FPL",
    "GVL",
    "IID",
    "JEA",
    "LDWP",
    "LGEE",
    "PJM",
    "SC",
    "SEC",
    "TEC",
]
print(f"BAS with non-yearly data are: {list(non_yearly_bas.keys())}")
buggy_facility_ids = []
facilties_saved = []
facilities_wrong_lmp_length = []
n_capacity_payment_warnings = 0
n_wrong_length_lmp = 0
# NOTE: only Balancing authority that does not have yearly net load
# info and is in the `plants`` dataframe is 'WWA'
# and its only for 1 site (plant code 57995), which is a wind plant
# plant_codes = [879]
for p in plants["Plant Code"].unique():
    # Get balancing authority code for this plant (for net-load data)
    ba_code = plants.loc[plants["Plant Code"] == p, "Balancing Authority Code"].values[
        0
    ]

    # ----- Get Capacity Payment Value For Balancing Authority-----
    if ba_code in net_cone_per_MW_year:
        net_cone_cost_for_plant_per_MW_year = net_cone_per_MW_year[ba_code]
    else:
        net_cone_cost_for_plant_per_MW_year = None  # net_cone_per_MW_year["OTHER"]
        buggy_facility_ids.append(p)
        continue

    # ----- Get Net Load For Balancing Authority-----
    if (ba_code in gen_only_bas) or (ba_code in non_conus_bas):
        # GRIS is grid force south (new mexico), could pretend its GRID which is gen_only_bas
        # generation only BAS have zero capacity payment value
        net_load = np.zeros(8760)
        capacity_value = np.zeros(8760)
        time_index = pd.date_range(
            start=f"{data_year}-01-01 00:00:00",
            end=f"{data_year}-12-31 23:00:00",
            freq="1h",
        )

    elif (ba_code in load_bas) and (ba_code not in non_yearly_bas):
        # we have the data and its the right length
        # non-generation only, we use the load
        net_load = net_load_df.loc[ba_code].copy(deep=True)
        net_load.set_index("Time Profile (UTC)", inplace=True)
        net_load.sort_index(inplace=True)
        # fix the nans
        net_load_mw = net_load["Net_Load"].interpolate(
            method="time"
        )  # to get rid of nans
        # if len(net_load_mw)!=8760:
        #     # had nans that were dropped
        #     net_load_interp = pd.DataFrame(columns=["Net Load (MW)"], index=ts)
        #     net_load_interp = net_load_interp.index.map(lambda x: net_load_mw)
        time_index = net_load.index.to_list()
        # get net load for capacity value calculation
        net_load_kW = net_load_mw.values * 1000  # MW -> kW
        capacity_value, run_successful = calc_capacity_payment_schedule(
            net_load_kW, net_cone_cost_for_plant_per_MW_year
        )
        if not run_successful:
            # also unexpected
            msg = f"Plant {p} in BA {ba_code} has total peak vals of 0"
            warnings.warn(msg, UserWarning, stacklevel=3)
            n_capacity_payment_warnings += 1

    elif ba_code in non_yearly_bas:
        # dont expect to get into this situation
        # load profile does not have all time indices
        buggy_facility_ids.append(p)
        msg = (
            f"Plant {p}: Balancing Authority {ba_code} has non-yearly net_load "
            f"(only has {non_yearly_bas[ba_code]} time values)"
        )
        warnings.warn(msg, UserWarning, stacklevel=3)
        n_capacity_payment_warnings += 1

    elif ba_code not in load_bas:
        # dont expect to get into this situation
        # balancing authority not in net load dataframe
        buggy_facility_ids.append(p)
        print(f"Plant {p} has invalid balancing authority {ba_code}")
        n_capacity_payment_warnings += 1
        # continue

    else:
        # dont expect to get into this situation
        buggy_facility_ids.append(p)
        print(f"Unexpected situation for plant {p} with balancing authority {ba_code}")
        n_capacity_payment_warnings += 1

    # match EIA_860 BA to Net_Load Balancing Authorities for the "Plant Code"
    # use "Mapped_Price_Node_ID" to find the correct LMP file for the "Plant Code"
    # if the BA is in the gen_only BAs we skip the net load process

    if isinstance(
        price_node_mapper.loc[p, "Mapped_Price_Node_ID"], int | str | float | bool
    ):
        # just one generator in the price_node_mapper
        # iso_name = price_node_mapper.loc[p, "Mapped_ISO_Name"]
        price_node_id = price_node_mapper.loc[p, "Mapped_Price_Node_ID"]
    else:
        # Get ISO name
        # iso_name = price_node_mapper.loc[p, "Mapped_ISO_Name"].values[0]
        price_node_id = price_node_mapper.loc[p, "Mapped_Price_Node_ID"].values[0]

    # if iso_name not in net_cone:
    #     iso_name = "OTHER"
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

        if "Market" in lmp.columns.to_list():
            if market_type in lmp["Market"].to_list():
                lmp = lmp[lmp["Market"] == market_type]
            elif "HA15AVG" in lmp["Market"].to_list():
                lmp = lmp[lmp["Market"] == "HA15AVG"]
            else:
                buggy_facility_ids.append(p)
            #     if len(lmp)!=8760:
            #         buggy_facility_ids.append(lmp)
        else:
            buggy_facility_ids.append(p)
        # if len(lmp)!=8760:
        #     buggy_facility_ids.append(p)

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
        lmp_da = lmp["Price $/MWh"].values

        # Check the length of the LMP data
        if len(lmp_da) != 8760:
            msg = (
                f"Facility ID {p} (with LMP Price Node ID {price_node_id}) "
                f"for {data_year} has price of length {len(lmp_da)}"
            )
            # print(msg)
            # warnings.warn(msg, UserWarning, stacklevel=3)
            buggy_facility_ids.append(p)
            n_wrong_length_lmp += 1
            facilities_wrong_lmp_length.append(p)

    else:
        lmp_da = np.zeros(8760)
        msg = f"LMP file {lmp_fpath} does not exist."
        # print(msg)
        # warnings.warn(msg, UserWarning, stacklevel=3)
        buggy_facility_ids.append(p)

    if p in buggy_facility_ids:
        # dont save data if its buggy
        continue

    # Combine capacity value with lmp_da, price
    # price_profile = capacity_value + lmp_da

    if p not in buggy_facility_ids:
        # print(f"SUCCESS FOR FACILITY ID {p}")
        price_profile_df = pd.DataFrame(
            {
                "LMP ($/MWh)": lmp_da,
                "Capacity Payment ($/MWh)": capacity_value,
                "Time (UTC)": time_index,
            }
        )

        # Only save it if not buggy
        price_profile_output_fpath = (
            price_profile_output_dir / f"{p}_{data_year}_price_profile.csv"
        )
        price_profile_df.to_csv(price_profile_output_fpath)
        facilties_saved.append(p)

    # TODO: save capacity_value + lmp_da to a csv file named as the facility name

if bool(buggy_facility_ids) or bool(missing_facility_ids):
    skip_ids = sorted(set(buggy_facility_ids) | set(missing_facility_ids))
    srs = pd.Series(skip_ids, name="Plant Code")
    srs.to_csv(LIBRARY_DIR / "h2i" / f"missing_price_data_facilities_{run_version}.csv")
    print(f"{len(skip_ids)} facilities have missing or incomplete data")
if bool(facilties_saved):
    good = pd.Series(sorted(set(facilties_saved)), name="Plant Code")
    # dont need to save below because its the same
    # good.to_csv(LIBRARY_DIR / "h2i" / f"saved_price_data_facilities_{run_version}.csv")
    print(f"{len(good)} facilities have complete data")

if bool(facilities_wrong_lmp_length):
    wl = pd.Series(sorted(set(facilities_wrong_lmp_length)), name="Plant Code")
    wl.to_csv(
        LIBRARY_DIR / "h2i" / f"wrong_length_price_data_facilities_{run_version}.csv"
    )
    print(f"{n_wrong_length_lmp} facilities have wrong length")

if bool(facilties_saved):
    facs_included = set(plants["Plant Code"].to_list()) - (
        set(buggy_facility_ids) | set(missing_facility_ids)
    )
    sv = pd.Series(sorted(set(facs_included)), name="Plant Code")
    sv.to_csv(LIBRARY_DIR / "h2i" / f"valid_price_data_facilities_{run_version}.csv")
    print(f"{len(sv)} facilities have recently saved price data")

# print(f"{len(missing_market)} facilities missing 'Market' column: {missing_market}")
print(f"Capacity payment related warnings occurred {n_capacity_payment_warnings} times")
