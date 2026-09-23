# add-on solar: existing_plant, poi_demand, solar_add_on, grid_sell
# add-on battery: existing_plant, poi_demand, battery, grid_sell, grid_buy
# add-on solar_battery: existing_plant, poi_demand, solar_add_on, battery, grid_sell, grid_buy
# grid-buy only needed if battery is added on

import numpy as np
import pandas as pd

from nice.tools.df_tools import add_extra_cols

solar_add_on_units = {
    "add_on_solar.system_capacity_DC": "MW",
}

solar_capacity_multiplier_cases = {
    1: {
        "multipliers": [2.0, 1.5, 1.25, 1.1, 1.0, 0.9, 0.75, 0.5, 0.25],
        "column": "Nameplate Capacity (MW)",
        "flat_multiplier": 1.34,  # so solar capacity is in DC
    },
    2: {
        "multipliers": [1.0],
        "column": "REV PV Capacity (MW-DC)",
        "flat_multiplier": 1.0,
    },
}

solar_capacity_multiplier_upper_bound_case = 2
# TODO: update so that we only use solar capacity <= REV PV Capacity (MW-DC)

battery_charge_rates_mw = [10.0, 25.0, 60.0, 100.0]
battery_durations_hrs = [4.0]
battery_add_on_units = {
    "battery.max_charge_rate": "MW",
    "battery.storage_capacity": "MW*h",
}


add_on_cases = ["solar", "battery", "solar_battery"]
existing_plant_cases = ["thermal", "wind", "solar", "solar"]
add_on_solar_cases = ["fixed", "one_axis"]


base_required_techs = ["existing_plant", "poi_demand", "grid_sell"]
add_on_cases_to_techs = {
    "solar": ["add_on_solar"],
    "battery": ["battery", "grid_buy"],
    "solar_battery": ["add_on_solar", "battery", "grid_buy"],
}


def get_all_cases():
    cases = []
    for add_on in add_on_cases:
        for existing_case in existing_plant_cases:
            cases.append(f"existing_{existing_case}_add_{add_on}")
    return cases


def get_col_renames_for_add_on_case(existing_plant_case, add_on_case):
    case_renames = {
        # plant lat/lon is not needed if thermal plant with add on battery
        "Nameplate Capacity (MW)": "poi_demand.electricity_demand",
        "Nameplate Capacity 2 (MW)": "grid_sell.interconnection_size",
        "EIA Plant Code": "grid_sell.plant_code",
    }
    case_rename_units = {
        "Nameplate Capacity (MW)": "MW",
        "Nameplate Capacity 2 (MW)": "MW",
        "EIA Plant Code": "unitless",
    }

    if "battery" in add_on_case:
        case_renames |= {
            "Nameplate Capacity 3 (MW)": "grid_buy.interconnection_size",
            "EIA Plant Code 2": "grid_buy.plant_code",
        }
        case_rename_units |= {
            "Nameplate Capacity 3 (MW)": "MW",
            "EIA Plant Code 2": "unitless",
        }

    if existing_plant_case == "thermal" and add_on_case != "battery":
        case_renames |= {
            "Plant Latitude": "site.latitude",
            "Plant Longitude": "site.longitude",
        }
        case_rename_units |= {"Plant Latitude": "deg", "Plant Longitude": "deg"}

    # if "solar" in add_on_case:
    #     case_renames |= {"REV PV Capacity (MW-DC)": "add_on_solar.system_capacity_DC"}

    return case_renames, case_rename_units


def add_battery_capacities_to_sitelist(df):
    df_len_init = len(df)
    df = add_extra_cols(df, "EIA Plant Code", "ref_plant_id")
    df.set_index(keys=["ref_plant_id"], inplace=True)
    plant_ids = df["EIA Plant Code"].unique()
    n_rep_per_plant = int(df_len_init / len(plant_ids))

    n_battery_cases = len(battery_charge_rates_mw) * len(battery_durations_hrs)
    new_cols = ["battery.max_charge_rate", "battery.storage_capacity"]
    # for new_col in new_cols:
    #     df[new_col] = [1.0]*len(df)

    indexer_info = ["ref_plant_id"]
    if n_rep_per_plant > 1:
        df = add_extra_cols(df, "add_on_solar.system_capacity_DC", "solar_size")
        df.set_index(keys=["solar_size"], append=True, inplace=True)
        indexer_info += ["solar_size"]

    df_concat_ls = [df for i in range(n_battery_cases)]
    df_add_on = pd.concat(df_concat_ls, axis=0)

    # sort by index
    df_add_on.sort_index(inplace=True)

    # make dataframe of battery cases
    battery_cases = pd.DataFrame(
        columns=new_cols, index=np.arange(0, n_battery_cases, 1)
    )
    cnt = 0
    for battery_charge_rate in battery_charge_rates_mw:
        for storage_hrs in battery_durations_hrs:
            battery_cases.loc[cnt, "battery.max_charge_rate"] = battery_charge_rate
            battery_cases.loc[cnt, "battery.storage_capacity"] = (
                battery_charge_rate * storage_hrs
            )
            cnt += 1

    battery_df_ls = [battery_cases for i in range(df_len_init)]
    battery_cases_df = pd.concat(battery_df_ls, axis=0)
    battery_cases_df["ref_plant_id"] = df_add_on.index.get_level_values("ref_plant_id")
    if "solar_size" in indexer_info:
        battery_cases_df["solar_size"] = df_add_on.index.get_level_values("solar_size")
    battery_cases_df.set_index(keys=indexer_info, inplace=True)

    battery_cases_df.sort_index(inplace=True)

    df_add_on = pd.concat([df_add_on, battery_cases_df], axis=1)

    # battery_multiplier_indx = np.tile(np.arange(0, n_battery_cases, 1), df_len_init)
    # df_add_on["battery_add_on_indx"] = battery_multiplier_indx.tolist()

    # df_add_on.set_index(keys=["battery_add_on_indx"], inplace=True)

    # cnt = 0
    # ref_colname = pv_capac_mult_case["column"]
    # multiplier_vals = np.array(pv_capac_mult_case["multipliers"])*pv_capac_mult_case["flat_multiplier"]
    # for m in multiplier_vals:
    #     df_add_on.loc[cnt, "add_on_solar.system_capacity_DC"] = df_add_on.loc[cnt,ref_colname]*m
    #     cnt += 1

    df_add_on.reset_index(drop=True, inplace=True)
    df_add_on.sort_values(by="EIA Plant Code", inplace=True)
    return df_add_on


# def add_solar_capacity_to_sitelist(df, solar_capacity_mult_case):


def add_solar_capacities_to_sitelist(df):
    df_len_init = len(df)
    df = add_extra_cols(df, "EIA Plant Code", "ref_plant_id")
    df.set_index(keys=["ref_plant_id"], inplace=True)
    # plant_ids = df['EIA Plant Code'].unique()

    new_cols = ["add_on_solar.system_capacity_DC"]
    n_pv_capacities = sum(
        len(v["multipliers"]) for _, v in solar_capacity_multiplier_cases.items()
    )
    df_concat_ls = [df for i in range(n_pv_capacities)]
    df_add_on = pd.concat(df_concat_ls, axis=0)

    df_add_on.sort_index(inplace=True)

    solar_multiplier_indx = np.tile(np.arange(0, n_pv_capacities, 1), df_len_init)
    df_add_on["solar_add_on_indx"] = solar_multiplier_indx.tolist()

    for new_col in new_cols:
        df_add_on[new_col] = [1.0] * len(df_add_on)

    # df_add_on.set_index(keys=["solar_add_on_indx"], append=True, inplace=True)
    df_add_on.set_index(keys=["solar_add_on_indx"], inplace=True)

    cnt = 0
    ub_casei = None  # only used for upper-bound capacity
    for casei, pv_capac_mult_case in solar_capacity_multiplier_cases.items():
        ref_colname = pv_capac_mult_case["column"]
        multiplier_vals = (
            np.array(pv_capac_mult_case["multipliers"])
            * pv_capac_mult_case["flat_multiplier"]
        )

        if casei == solar_capacity_multiplier_upper_bound_case:
            ub_casei = cnt
        for m in multiplier_vals:
            df_add_on.loc[cnt, "add_on_solar.system_capacity_DC"] = (
                df_add_on.loc[cnt, ref_colname] * m
            )
            cnt += 1

    if solar_capacity_multiplier_upper_bound_case is None:
        df_add_on.reset_index(drop=True, inplace=True)
        df_add_on.sort_values(by="EIA Plant Code", inplace=True)

        return df_add_on

    # Need to limit the number of add-on solar cases

    # ub_df = df_add_on.loc[ub_casei].copy(deep=True)
    upper_bound_df = df_add_on.loc[ub_casei].copy(deep=True)
    other_case_indx = list(
        set(df_add_on.index.get_level_values("solar_add_on_indx").to_list())
        - set([ub_casei])
    )
    lower_bound_df = df_add_on.loc[other_case_indx].copy(deep=True)

    # tmp = [ub_df for i in range(len(other_case_indx))]
    # upper_bound_df = pd.concat(tmp, axis=0)

    lower_bound_df.reset_index(drop=False, inplace=True)
    upper_bound_df.set_index(keys="Plant Code", inplace=True)
    lower_bound_df.set_index(keys="Plant Code", inplace=True)

    upper_bound_df.sort_index(inplace=True)
    lower_bound_df.sort_index(inplace=True)

    lb_df = lower_bound_df[
        lower_bound_df["add_on_solar.system_capacity_DC"].le(
            upper_bound_df["add_on_solar.system_capacity_DC"],
            axis=0,
            level="Plant Code",
        )
    ].copy(deep=True)
    lb_df.drop(columns=["solar_add_on_indx"], inplace=True)

    add_on_df = pd.concat([lb_df, upper_bound_df], axis=0)
    add_on_df.sort_index(inplace=True)
    add_on_df.reset_index(drop=False, inplace=True)
    return df_add_on

    # df_add_on.reset_index(drop=True, inplace=True)
    # df_add_on.sort_values(by="EIA Plant Code", inplace=True)

    # return df_add_on
