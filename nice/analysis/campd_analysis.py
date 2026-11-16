
import numpy as np
import pandas as pd
from nice import DATA_DIR
from nice.tools.eia_860_file_tools import load_eia_860
from nice.tools.eia_923_file_tools import load_eia_923

def convert_to_list(row):
    txt = row["Gross Load nan profile"]
    lst = [int(k) for k in txt.strip("[]").split(" ") if len(k)>0]
    return lst
def count_nans(row):
    if len(row["Nan Profile"])==0:
        return 0
    return sum(row["Nan Profile"])

def n_nan_blocks(row):
    if len(row["Nan Profile"])==0:
        return 0
    return len(row["Nan Profile"])

def max_nan_block(row):
    if len(row["Nan Profile"])==0:
        return 0
    return max(row["Nan Profile"])    

def load_campd_sites():
    fpath = DATA_DIR/"summary_of_nan_profiles.csv"

    df = pd.read_csv(fpath, index_col="Unnamed: 0")
    df["Nan Profile"] = df.apply(convert_to_list, axis=1)
    df.drop(columns=["Gross Load nan profile"],inplace=True)
    df["Hours Nan"] = df.apply(count_nans, axis=1)
    df["Num Nan blocks"] = df.apply(n_nan_blocks, axis=1)
    df["Max Duration Nan block"] = df.apply(max_nan_block, axis=1)
    df["Facility ID"] = df["Facility ID"].astype(int)
    df["Unit ID"] = df["Unit ID"].astype(str)
    df["EIA Unit ID"] = df["Unit ID"].to_list()

    return df
def load_format_eia_860_gen(data_year=2025):
    gen_data = load_eia_860("Generator", sheet="Operable", year=data_year)
    gen_data["Plant Code"] = gen_data["Plant Code"].astype(int)  # 13371
    gen_data["Generator ID"] = gen_data["Generator ID"].astype(str)
    return gen_data

def load_format_eia_923_pg1(yr=2025):
    perf = load_eia_923("M_12", sheet="Page 1 Generation and Fuel Data", year=yr)
    perf["Plant Code"] = perf["Plant Id"].astype(int)
    perf.drop(columns=["Plant Id"], inplace=True)
    # Netgen

    return perf

# 3726 generators in campd, 1211 facility IDs
campd = load_campd_sites()
campd.set_index(keys=["Facility ID", "Unit ID"],inplace=True)
campd.sort_index(inplace=True)
campd_facids = list(set(campd.index.get_level_values("Facility ID")))
campd_plant_gross = campd.groupby(level="Facility ID")["Total Gross Load (MW)"].sum()

eia_cols = ["Plant Code", "Generator ID", "Prime Mover", "Status", "Nameplate Capacity (MW)", "Operating Year"]
eia_860 = load_format_eia_860_gen()
eia_860_drop_cols = set(eia_860.columns.to_list()) - set(eia_cols)
eia_860.drop(columns=list(eia_860_drop_cols), inplace=True)
eia_860.set_index(keys=["Plant Code"],inplace=True)
eia_860.sort_index(inplace=True)
gen_excess_plant_ids = set(eia_860.index.to_list()) - set(campd_facids)
eia_860.drop(index=list(gen_excess_plant_ids), inplace=True)

# EIA 860 Generator: 1211 plant ids in EIA, 4424 generators
eia_plant_capacity = eia_860.groupby(level="Plant Code")["Nameplate Capacity (MW)"].sum()

# EIA 923: Plant
# eia_923["Reported Fuel Type Code"].unique()
["Net Generation (Megawatthours)"]
eia_923 = load_format_eia_923_pg1()
eia_923_plant_ids = set(eia_923["Plant Code"].to_list())
eia_923_excess_plant_ids = sorted(eia_923_plant_ids - set(campd_facids))
shared_plant_ids = sorted(set(campd_facids) & eia_923_plant_ids)
eia_923_missing_plant_ids = sorted(set(campd_facids) - eia_923_plant_ids)

# EIA 923 has 1208 shared plant ids, 3 are missing ([2521, 10743, 10803])
eia_923.set_index(keys = ["Plant Code"], inplace=True)
eia_923.sort_index(inplace=True)
# EIA 923 now has 1208 plant ids, 3141 generators
eia_923.drop(index=eia_923_excess_plant_ids, inplace=True)



# Get all the shared plant ids
eia_860_excess_plant_ids = sorted(set(eia_860.index.to_list()) - set(eia_923.index.to_list()))
campd_excess_plant_ids = sorted(set(campd_facids) - set(eia_923.index.to_list()))

eia_860.drop(index=eia_860_excess_plant_ids, inplace=True)
campd.drop(index=campd_excess_plant_ids, inplace=True)

final_plant_id_list = sorted(set(eia_860.index.to_list()))

gross_load = campd.groupby(level="Facility ID")["Total Gross Load (MW)"].sum()
capacity = eia_860.groupby(level="Plant Code")["Nameplate Capacity (MW)"].sum()
net_gen = eia_923.groupby(level="Plant Code")["Net Generation (Megawatthours)"].sum()

# Want Net/gross
ratio = net_gen.loc[final_plant_id_list]/gross_load.loc[final_plant_id_list]
ratio.name = "net/gross"
ratio[ratio>1] # 195 have ratio > 1
ratio[ratio>1e3] # 41 of those 195 have a ratio of infinity (meaning gross_load is 0)
ratio[ratio<=1] # 1006 have a ratio <=1
# 13 have a ratio < 0, 16 have ratio<=0. 
ratio[ratio<0] # This is because they have 0 or negative net generation 
# (but have zero or positive gross load)
valid_capacity = capacity.loc[ratio[ratio<=1].index.to_list()]
# len(ratio[ratio<=0.6]) # 58 
# len(ratio[ratio<=0.9]) # 304
# include ones >= 0.6 and <= 1.0: 948 sites
rt = ratio[ratio>=0.6]
plants_to_use = rt[rt<=1.0] #make list of these 948 sites
plants_to_use.name = "ratio (net/gross)"
gross_load.index.name = "Plant Code"
summary = pd.concat([plants_to_use, net_gen.loc[plants_to_use.index.to_list()], gross_load.loc[plants_to_use.index.to_list()], capacity.loc[plants_to_use.index.to_list()]],axis=1)
summary.index.name = "Facility ID"

n_sites = len(plants_to_use)
output_fpath = DATA_DIR/f"campd_ratio_sitelist_{n_sites}_facilities.csv"
summary.to_csv(output_fpath)
print(f"saved {n_sites} sites")

# ["Facility ID","Net Generation (Megawatthours)","Total Gross Load (MW)","ratio (net/gross)","Nameplate Capacity (MW)"]
# eia_923_fuel_consump = eia_923.groupby(level="Plant Code")['Total Fuel Consumption MMBtu'].sum()
# campd_fuel_input = campd.groupby(level="Facility ID")["Total Heat Input (mmBtu)"].sum()
# fuel_consump_ratio = eia_923_fuel_consump.loc[shared_plant_ids]/campd_fuel_input.loc[shared_plant_ids]
# 5 have fuel_consump_ratio is


[]