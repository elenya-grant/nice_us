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

def get_caveat_oldname(row):
    txt = row["Comment"]
    if "Unit ID change" not in txt:
        return row["Unit ID"]
    return txt.split("to")[0].split("from")[-1].strip()


def load_format_eia_923_pg1(yr=2025):
    perf = load_eia_923("M_12", sheet="Page 1 Generation and Fuel Data", year=yr)
    perf["Plant Code"] = perf["Plant Id"].astype(int)
    perf.drop(columns=["Plant Id"])
    # Netgen

    return perf

def load_format_eia_923_pg4(yr=2025):
    perf = load_eia_923("M_12", sheet="Page 4 Generator Data", year=yr)
    perf["Plant Code"] = perf["Plant Id"].astype(int)
    perf.drop(columns=["Plant Id"])

    return perf

def load_format_eia_860_gen(data_year=2025):
    gen_data = load_eia_860("Generator", sheet="Operable", year=data_year)
    gen_data["Plant Code"] = gen_data["Plant Code"].astype(int)  # 13371
    gen_data["Generator ID"] = gen_data["Generator ID"].astype(str)
    return gen_data

def load_campd_caveats():
    caveats = pd.read_excel(DATA_DIR/"data_caveats_current.xlsx", sheet_name="Sheet 1")
    
    caveats["Facility ID"] = caveats["Facility ID"].astype(int)
    all_caveat_facilities = caveats["Facility ID"].to_list()
    caveats["Old Unit ID"] = caveats.apply(get_caveat_oldname, axis=1)
    caveats.dropna(axis=0, subset=["Old Unit ID"], inplace=True)
    caveats["Unit ID"] = caveats["Unit ID"].astype(str)
    caveats["Old Unit ID"] = caveats["Old Unit ID"].astype(str)
    
    return caveats

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

# def compare_prime_movers(eia_subset, campd_subset):
#     # df for a plant that has generator ID indices
#     # should have column of "PM"

prime_movers = ["ST", "GT", "IC", "CA", "CT", "CS"]
caveats = load_campd_caveats()
caveat_plant_ids = list(set(caveats["Facility ID"].to_list()))
caveats.set_index(keys=["Facility ID"], inplace=True)

# 3726 generators in campd, 1211 facility IDs
campd = load_campd_sites()
# campd = campd[campd["Max Duration Nan block"]<8760]
campd.set_index(keys=["Facility ID", "Unit ID"],inplace=True)
campd_facids = list(set(campd.index.get_level_values("Facility ID")))

eia_cols = ["Plant Code", "Generator ID", "Prime Mover", "Status", "Nameplate Capacity (MW)", "Operating Year"]
eia_init = load_format_eia_860_gen()
eia_init_drop_cols = set(eia_init.columns.to_list()) - set(eia_cols)
eia_init.drop(columns=list(eia_init_drop_cols), inplace=True)
eia_init.set_index(keys=["Plant Code"],inplace=True)
# remove prime-movers


eia = load_format_eia_860_gen()
# remove prime-movers
eia = eia[eia["Prime Mover"].isin(prime_movers)]
eia_pids = list(set(eia["Plant Code"].to_list())) # 4387
# eia = eia[eia["Nameplate Capacity (MW)"]>=25.0] # makes 3927
# eia = eia[eia["Operating Year"]<2025] # 4338 - 50 generators (14 plants) start operating in 2025
# eia = eia[eia["Status"]=="OP"] # 4214 (173 generators are not operational)


# gen[gen["Nameplate Capacity (MW)"]>25.0] 
# gen[gen["Operating Year"]==2025] # 50 generators (14 plants) start operating in 2025
# gen[gen["Status"]!="OP"] # 173 generators are not operational

# plant generation >= 10 MW
# naics code of 22


eia.set_index(keys=["Plant Code"],inplace=True)
gen_excess_plant_ids = set(eia.index.to_list()) - set(campd_facids)
eia.drop(index=list(gen_excess_plant_ids), inplace=True)
eia.groupby(by="Plant Code")["Nameplate Capacity (MW)"].sum()
plant_capacity = eia.groupby(by="Plant Code")["Nameplate Capacity (MW)"].sum()
[]
eia.set_index(keys=["Generator ID"], append=True, inplace=True)

eia_filtered_pids = list(set(eia.index.get_level_values("Plant Code")))
# Facility 63628 has generators as status "OS"
# Facility 54333 has generator with 1.2 MW of capacity
# 26 plants in campd that arent in eia (120 generators)

shared_plant_ids = sorted(set(eia_filtered_pids) & set(campd_facids))

mismatch_n_gen = {}
n_mismatch = 0
filtered_out_pids = []
match_len = []
full_match = []
full_matches = []
partial_match_gens = {}
partial_matches = []
missing_matches = []
missing_but_same_num = []

for plant_id in campd_facids:
    if plant_id not in eia_filtered_pids:
        filtered_out_pids.append(plant_id)
        continue

    eia_gens = eia.loc[plant_id].index.to_list()
    campd_gens = campd.loc[plant_id].index.to_list()

    matching_generators = list(set(eia_gens) & set(campd_gens))

    # same length, mismatch names
    # different length, mismatch names
    if len(eia_gens) == len(campd_gens):
        # EIA and campd have same number of generators
        match_len.append(plant_id) # number of generators match
        if len(matching_generators) == len(campd_gens):
            # generator names match
            full_match.append(plant_id)
            full_matches += [(plant_id, g) for g in matching_generators]
        else:
            missing_but_same_num.append(plant_id)
    else:
        # different number of generators
        if bool(matching_generators):
            # has some matching names
            # missing_gens = set(campd_gens) - set(matching_generators)
            partial_match_gens[plant_id] = {"match": matching_generators}
            partial_matches += [(plant_id, g) for g in matching_generators]
        else:
            # has no matching names
            missing_matches.append(plant_id)


    # if plant_id in caveat_plant_ids:
    #     old_unit_ids = caveats.loc[plant_id]["Old Unit ID"].to_list()
    #     new_unit_ids = caveats.loc[plant_id]["Unit ID"].to_list()
    #     eia_caveat_ids = set(eia_gens) & set(old_unit_ids)
    #     campd_caveat_ids = set(campd_gens) & set(new_unit_ids)
    #     []


    # if len(eia_gens)!=len(campd_gens):
    #     mismatch_n_gen[plant_id] = {"CAMPD": campd_gens, "EIA": eia_gens}
    #     n_mismatch += 1

# Save off ones we have matches for
plant = load_format_eia_923_pg1() # 239 in EIA 923 Page 1
# 124 plants in 923 page 4 and full_match_plants
plant.set_index(keys="Plant Code", inplace=True)
if len(plant.columns.to_list()[0])>30:
    plant.drop(columns = plant.columns.to_list()[0], inplace=True)

plant["Reported Prime Mover"]
full_match_plants = sorted(set(campd.loc[full_matches].index.get_level_values("Facility ID").to_list()))
avail_full_match_plants = sorted(set(plant["Plant Id"].to_list()) & set(full_match_plants)) # 239 in page 1

netgen_cols = [k for k in plant.columns.to_list() if "Netgen" in k]
gross = plant.loc[avail_full_match_plants].groupby("Plant Code")["Net Generation (Megawatthours)"].sum()
net = campd.loc[avail_full_match_plants].groupby("Facility ID")["Total Gross Load (MW)"].sum()
combo = pd.concat([gross, net],axis=1)
combo["ratio (net/gross)"] = combo["Net Generation (Megawatthours)"]/combo["Total Gross Load (MW)"]
# 7 have ratio>1 (bad), 6 of those have 0 gross load. facility Ids are [203, 886, 1073, 7145, 56189, 56786, 58124]

# 564 of 592 in EIA plant data
# ---- BELOW IS WHAT WHAT USED TO MAKE LIST -----
plant.index.name = "Facility ID"
fac_ids = sorted(set(plant["Plant Id"].to_list()) & set(match_len))
plant_capacity.index.name = "Facility ID"

# gross = plant.loc[fac_ids].groupby("Plant Code")["Net Generation (Megawatthours)"].sum()
gross = plant.loc[fac_ids].groupby("Facility ID")["Net Generation (Megawatthours)"].sum()
net = campd.loc[fac_ids].groupby("Facility ID")["Total Gross Load (MW)"].sum()

combo = pd.concat([gross, net, plant_capacity.loc[fac_ids]],axis=1)
for c in netgen_cols:
    fac_id_missing_netgen = plant.loc[fac_ids][plant.loc[fac_ids][c]=="."][c].index.to_list()
    plant[c] = plant[c].replace(to_replace={".":0.0})
    # combo = pd.concat([combo,plant.loc[fac_ids].groupby("Plant Code")[c].sum()], axis=1)
    combo = pd.concat([combo,plant.loc[fac_ids].groupby("Facility ID")[c].sum()], axis=1)
combo["ratio (net/gross)"] = combo["Net Generation (Megawatthours)"]/combo["Total Gross Load (MW)"]
combo_save = combo[combo["ratio (net/gross)"]<=1] # 518
# set negative net loads to 0
idx_negative = combo_save[combo_save["ratio (net/gross)"]<0].index.to_list()
combo_save.loc[idx_negative,"ratio (net/gross)"]=0.0 # set negative ratios to 0
# combo_save = combo_save[combo_save["ratio (net/gross)"]>=0.0] # 518
cols_needed = ["Net Generation (Megawatthours)", "Total Gross Load (MW)", "ratio (net/gross)", "Nameplate Capacity (MW)"]
combo_save[cols_needed].to_csv(DATA_DIR/f"campd_ratio_sitelist_{len(combo_save)}_facilities.csv")
combo_save.to_csv(DATA_DIR/f"campd_ratio_sitelist_{len(combo_save)}_facilities_with_monthly.csv")
[]
# ---- ABOVE IS WHAT WHAT USED TO MAKE LIST -----
# 40 with ratio > 1, 22 have total gross load of 0. 

n_entries_per_plant = {k:plant["Plant Id"].to_list().count(k) for k in avail_full_match_plants}
tmp = pd.Series(n_entries_per_plant)
easy_to_match_plant_ids = tmp[tmp==1].index.to_list() # only 1 prime mover
# 75 plants with 1 Prime mover type

# 1152 facilities that are in EIA 860, EIA 923, and CAMPD
# 54 facilities in CAMPD that have total gross load of 0.0
gross_load = campd.loc[easy_to_match_plant_ids].groupby("Facility ID")["Total Gross Load (MW)"].sum()
net_gen = plant.loc[easy_to_match_plant_ids]["Net Generation (Megawatthours)"]
stuff = pd.concat([gross_load, net_gen],axis=1)
stuff["ratio (net/gross)"] = stuff["Net Generation (Megawatthours)"]/stuff["Total Gross Load (MW)"]
stuff[stuff["ratio (net/gross)"]>1] # should check that out, just 1 plant (56189)
plant.loc[56189]["Total Fuel Consumption MMBtu"]
plant.loc[56189]["Total Fuel Consumption Quantity"] # 23851
campd.loc[56189]["Total Heat Input (mmBtu)"].sum()

plant["Net Generation (Megawatthours)"]
campd.loc[full_matches]
# TODO: save off the facilities in match_len.
campd.loc[match_len]
# 250 facilities are full match
# 199 facilities with partial match
# 420 facilities with no match
# 592 facilities in match len, so 342 that have match length but not full match
# 1218 generator matches
found_matches = full_matches + partial_matches
# 2508 generator matches missing from campd
campd_missing_matches = list(set(campd.index.to_list()) - set(found_matches))
# 3619 generator matches missing from eia
eia_missing_matches = list(set(eia.index.to_list()) - set(found_matches))
eia.loc[eia_missing_matches]["Prime Mover"].sort_index()

list(set(campd.index.get_level_values("Facility ID").to_list()))

# len(list(set(caveats.index.to_list()) & set(campd_missing_matches)))
# 237 caveats have missing plant generators (may have duplicate Unit IDs, 55620)
# but 263 rows in caveats...
caveats.set_index(keys=["Unit ID"], append=True, inplace=True)
caveats_with_missing = list(set(caveats.index.to_list()) & set(campd_missing_matches))
caveats.loc[caveats_with_missing]

# 834 plants in EIA, 937 in CAMPD...
# eia_missing_plant_ids = list(set(eia.loc[eia_missing_matches].index.get_level_values("Plant Code").to_list()))

# check if all generators names match
# che
# 534 mismatch plant ids (410 if you remove the NaN profile ones)

# If you remove the generators with full NaN profiles from the campd data
# 410 plants in `missing_matches` (mismatch length and no overlapping generator names)
# 556 plants in `match_len` (238 are in `full_match`, so 318 have name mismatch)
# 238 plants in `full_match`
# 195 plants with partial matches (totalling 448 generators)
[]
# ID: 'EIA' -> 'CAMPD'
# 2048: 'A' -> 'CTA'
# 55298, 6 renames that don't match 2025 data
# Plant ID 55298 has 4 CT and 2 CA. 
# EIA names are CT1A, CT1B, CT2A, CT2B, ST1, ST2
# CAMPD has 1A, 1B, 2B
# Caveats says CAMPD unit IDS are 1A, 1B, 2A, 2B
# so multiple generators can sometimes map to the same campd generator
# Caveats says it was renamed from 1 -> 1A, CT1 -> 1A, 2-> 1B, CT2 -> 1B, 3-> 2A, 4 -> 2B