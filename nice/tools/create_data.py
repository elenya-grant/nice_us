import pandas as pd

import nice.tools.create_data_tools as cd_tools
from nice.tools.eia_860_file_tools import load_eia_860
from nice.tools.eia_923_file_tools import load_eia_923

# 13370 plant IDs in generator and plant
# 13071 plant IDS in generator and plant and perf
# 778 plant IDs in generator and plant and storage
# 788 plant IDs in perf and storage


def create_surplus_interconnect_data(missing_val=0.0):
    data_year = 2024
    plant = load_eia_860("Plant", year=data_year)
    gen = load_eia_860("Generator", year=data_year)
    perf = load_eia_923("M_12", sheet="Page 1 Generation and Fuel Data", year=data_year)
    storage = load_eia_923("M_12", sheet="Page 1 Energy Storage", year=data_year)

    plant["Plant Code"] = plant["Plant Code"].astype(int)  # 16132
    gen["Plant Code"] = gen["Plant Code"].astype(int)  # 13371
    storage["Plant Code"] = storage["Plant Id"].astype(int)
    perf["Plant Code"] = perf["Plant Id"].astype(int)

    perf_pid = set(perf["Plant Code"].to_list())
    gen_pid = set(gen["Plant Code"].to_list())
    plant_pid = set(plant["Plant Code"].to_list())
    storage_pid = set(storage["Plant Code"].to_list())
    # state_centroids = pd.DataFrame()

    # common_pid = (plant_pid.intersection(perf_pid)).intersection(gen_pid)
    # # id missing from gen but exists in plant
    # plant_pid.difference(gen_pid) # 2762 missing from gen

    gen.set_index(keys="Plant Code", inplace=True)
    plant.set_index(keys="Plant Code", inplace=True)
    perf.set_index(keys="Plant Code", inplace=True)
    storage.set_index(keys="Plant Code", inplace=True)

    plant_data_cols = [
        "Latitude",
        "Longitude",
        "NERC Region",
        "Balancing Authority Code",
        "State",
        "City",
    ]
    gen_data_cols = ["Nameplate Capacity (MW)"]
    perf_data_cols = ["Net Generation (Megawatthours)"]
    storage_perf_data_cols = [
        "Net Generation (Megawatthours)"
    ]  # to use as equivalent to perf_data_cols if its storage
    summary_cols = ["Plant Code", "Prime Mover", "Num Generators", "Is Storage"]

    cols = summary_cols + plant_data_cols + gen_data_cols + perf_data_cols

    new_df = pd.DataFrame(columns=cols)
    for pid in gen_pid.intersection(plant_pid):
        tmp_dict = {}
        plant_data = cd_tools.get_plant_data_by_pid(plant, pid, plant_data_cols)
        # tmp_dict.update(dict(zip(plant_data_cols, plant_data)))

        if isinstance(gen.loc[pid, "Nameplate Capacity (MW)"], float):
            if pid in perf_pid:
                perf_data = cd_tools.get_generator_performance_data_by_pid_pm(
                    perf,
                    pid,
                    gen.loc[pid, "Prime Mover"],
                    perf_data_cols,
                    missing_val=missing_val,
                )
            else:
                # perf_data = [0.0]*len(perf_data_cols)
                perf_data = [missing_val] * len(perf_data_cols)
            # net_gen = perf.loc[pid, "Net Generation (Megawatthours)"] if pid in perf_pid else 0.0
            # if not isinstance(net_gen, float):
            #     net_gen = net_gen.sum()
            is_storage = pid in storage_pid
            if is_storage:
                perf_data = cd_tools.get_storage_performance_data_by_pid_pm(
                    perf,
                    pid,
                    gen.loc[pid, "Prime Mover"],
                    storage_perf_data_cols,
                    missing_val=missing_val,
                )

            gen_data = cd_tools.get_generator_data_by_pid_pm(
                gen, pid, gen.loc[pid, "Prime Mover"], gen_data_cols
            )
            tmp_dict = tmp_dict | dict(
                zip(summary_cols, [pid, gen.loc[pid, "Prime Mover"], 1, is_storage])
            )
            tmp_dict = tmp_dict | dict(zip(plant_data_cols, plant_data))
            tmp_dict = tmp_dict | dict(zip(gen_data_cols, gen_data))
            tmp_dict = tmp_dict | dict(zip(perf_data_cols, perf_data))

            # tmp_dict.update(dict(zip(summary_cols, [pid, gen.loc[pid, "Prime Mover"], 1])))

            # tmp_df_vals = [pid, gen.loc[pid, "Prime Mover"], 1, float(plant.loc[pid, "Latitude"]), float(plant.loc[pid, "Longitude"]), gen.loc[pid,"Nameplate Capacity (MW)"], net_gen]
            # tmp_df = pd.DataFrame(dict(zip(cols, tmp_df_vals)), index=[pid])
            tmp_df = pd.DataFrame(tmp_dict, index=[pid])
            new_df = pd.concat([new_df, tmp_df], axis=0)
        else:
            for pm in set(gen.loc[pid, "Prime Mover"].to_list()):
                gen_data = cd_tools.get_generator_data_by_pid_pm(
                    gen, pid, pm, gen_data_cols, missing_val=missing_val
                )

                if pid in perf_pid:
                    perf_data = cd_tools.get_generator_performance_data_by_pid_pm(
                        perf, pid, pm, perf_data_cols, missing_val=missing_val
                    )
                else:
                    # perf_data = [0.0]*len(perf_data_cols)
                    perf_data = [missing_val] * len(perf_data_cols)

                is_storage = False
                if pid in storage_pid:
                    if isinstance(storage.loc[pid, "Reported Prime Mover"], str):
                        is_storage = (
                            True
                            if storage.loc[pid, "Reported Prime Mover"] == pm
                            else False
                        )
                    else:
                        is_storage = (
                            True
                            if pm in storage.loc[pid, "Reported Prime Mover"].to_list()
                            else False
                        )

                if is_storage:
                    perf_data = cd_tools.get_storage_performance_data_by_pid_pm(
                        perf, pid, pm, storage_perf_data_cols, missing_val=missing_val
                    )

                n_pm = (
                    1
                    if isinstance(gen.loc[pid, "Prime Mover"], str)
                    else len(gen.loc[pid, "Prime Mover"])
                )
                tmp_dict = tmp_dict | dict(
                    zip(summary_cols, [pid, pm, n_pm, is_storage])
                )
                tmp_dict = tmp_dict | dict(zip(plant_data_cols, plant_data))
                tmp_dict = tmp_dict | dict(zip(gen_data_cols, gen_data))
                tmp_dict = tmp_dict | dict(zip(perf_data_cols, perf_data))
                tmp_df = pd.DataFrame(tmp_dict, index=[pid])
                new_df = pd.concat([new_df, tmp_df], axis=0)

    return new_df
