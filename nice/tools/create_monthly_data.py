import calendar

import pandas as pd

from nice.tools.create_data_tools import get_monthly_data
from nice.tools.eia_860_file_tools import load_eia_860
from nice.tools.eia_923_file_tools import load_eia_923


def do_monthly_stuff(data_year=2024):
    gen = load_eia_860("Generator", year=data_year)
    perf = load_eia_923("M_12", sheet="Page 1 Generation and Fuel Data", year=data_year)

    gen["Plant Code"] = gen["Plant Code"].astype(int)  # 13371
    perf["Plant Code"] = perf["Plant Id"].astype(int)

    perf_pid = set(perf["Plant Code"].to_list())
    gen_pid = set(gen["Plant Code"].to_list())

    perf.set_index(keys="Plant Code", inplace=True)
    gen.set_index(keys="Plant Code", inplace=True)

    # column_fmt="Net Generation {month}"
    column_fmt = "Netgen {month}"

    # perf.replace({'.':0}, value=None)

    months_to_n_days = {
        calendar.month_name[i]: calendar.monthrange(2024, i)[1] for i in range(1, 13)
    }
    m12_cols = [column_fmt.format(month=m) for m in list(months_to_n_days.keys())]

    # Plant ID of 1 has two PM, Plan ID of 2 has one
    # perf.loc[pid,"Reported_Prime Mover"]

    # hm = perf.loc[3][perf.loc[3]["Reported Prime Mover"] == "ST"]
    # hm[m12_cols].sum(axis=0)

    cols = ["Prime Mover"] + m12_cols
    monthly_df = pd.DataFrame(columns=cols)
    for pid in gen_pid.intersection(perf_pid):
        tmp_dict = {}

        if isinstance(gen.loc[pid, "Nameplate Capacity (MW)"], float):
            tmp_dict |= {"Prime Mover": gen.loc[pid, "Prime Mover"]}
            tmp_dict |= get_monthly_data(
                perf, pid, gen.loc[pid, "Prime Mover"], missing_val=None
            )
            tmp_df = pd.DataFrame(tmp_dict, index=[pid])
            monthly_df = pd.concat([monthly_df, tmp_df], axis=0)
        else:
            for pm in set(gen.loc[pid, "Prime Mover"].to_list()):
                tmp_dict = {}
                tmp_dict |= {"Prime Mover": pm}
                tmp_dict |= get_monthly_data(perf, pid, pm, missing_val=None)
                tmp_df = pd.DataFrame(tmp_dict, index=[pid])
                monthly_df = pd.concat([monthly_df, tmp_df], axis=0)

    return monthly_df
