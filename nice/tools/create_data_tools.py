import calendar


def get_plant_data_by_pid(plant_data, pid, plant_data_cols):
    return plant_data.loc[pid][plant_data_cols].to_list()


def get_generator_data_by_pid_pm(gen_data, pid, pm, gen_data_cols, missing_val=0.0):
    if isinstance(gen_data.loc[pid, "Prime Mover"], str):
        return gen_data.loc[pid][gen_data_cols].to_list()

    gen_pm = gen_data.loc[pid][gen_data.loc[pid]["Prime Mover"] == pm]
    if len(gen_pm) == 0:
        return [missing_val] * len(gen_data_cols)

    return gen_pm[gen_data_cols].sum(axis=0).to_list()


def get_generator_performance_data_by_pid_pm(
    perf_data, pid, pm, perf_data_cols, missing_val=0.0
):
    if isinstance(perf_data.loc[pid, "Reported Prime Mover"], str):
        if perf_data.loc[pid, "Reported Prime Mover"] == pm:
            return perf_data.loc[pid][perf_data_cols].to_list()
        # return [0.0]*len(perf_data_cols)
        return [missing_val] * len(perf_data_cols)

    perf_pm = perf_data.loc[pid][perf_data.loc[pid]["Reported Prime Mover"] == pm]
    if len(perf_pm) == 0:
        # return [0.0]*len(perf_data_cols)
        return [missing_val] * len(perf_data_cols)

    return perf_pm[perf_data_cols].sum(axis=0).to_list()


def get_storage_performance_data_by_pid_pm(
    storage_data, pid, pm, storage_data_cols, missing_val=0.0
):
    if isinstance(storage_data.loc[pid, "Reported Prime Mover"], str):
        if storage_data.loc[pid, "Reported Prime Mover"] == pm:
            return storage_data.loc[pid][storage_data_cols].to_list()
        return [missing_val] * len(storage_data_cols)

    perf_pm = storage_data.loc[pid][storage_data.loc[pid]["Reported Prime Mover"] == pm]
    if len(perf_pm) == 0:
        return [missing_val] * len(storage_data_cols)
        # return [None]*len(storage_data_cols)

    return perf_pm[storage_data_cols].sum(axis=0).to_list()


def get_monthly_capacity_factor(
    gen_data,
    perf_data_m12,
    pid,
    pm,
    column_fmt="Net Generation {month}",
    missing_val=0.0,
):
    # TODO: finish this function
    get_generator_data_by_pid_pm(
        gen_data, pid, pm, ["Nameplate Capacity (MW)"], missing_val=missing_val
    )

    months_to_n_days = {
        calendar.month_name[i]: calendar.monthrange(2024, i)[1] for i in range(1, 13)
    }
    m12_cols = [column_fmt.format(month=m) for m in list(months_to_n_days.keys())]
    if isinstance(perf_data_m12.loc[pid, "Reported Prime Mover"], str):
        if perf_data_m12.loc[pid, "Reported Prime Mover"] == pm:
            return perf_data_m12.loc[pid][m12_cols].to_list()
        return [missing_val] * len(m12_cols)

    perf_pm = perf_data_m12.loc[pid][
        perf_data_m12.loc[pid]["Reported Prime Mover"] == pm
    ]
    if len(perf_pm) == 0:
        return [missing_val] * len(m12_cols)
        # return [None]*len(storage_data_cols)

    return perf_pm[m12_cols].sum(axis=0).to_list()


def get_monthly_data(
    perf_data_m12,
    pid,
    pm,
    column_fmt="Netgen {month}",
    missing_val=0.0,
):
    months_to_n_days = {
        calendar.month_name[i]: calendar.monthrange(2024, i)[1] for i in range(1, 13)
    }
    m12_cols = [column_fmt.format(month=m) for m in list(months_to_n_days.keys())]
    if isinstance(perf_data_m12.loc[pid, "Reported Prime Mover"], str):
        if perf_data_m12.loc[pid, "Reported Prime Mover"] == pm:
            return perf_data_m12.loc[pid].replace({".": 0})[m12_cols].to_dict()
        return dict(zip(m12_cols, [missing_val] * len(m12_cols)))

    perf_pm = perf_data_m12.loc[pid][
        perf_data_m12.loc[pid]["Reported Prime Mover"] == pm
    ]
    if len(perf_pm) == 0:
        return dict(zip(m12_cols, [missing_val] * len(m12_cols)))

    return perf_pm[m12_cols].replace({".": 0}).sum(axis=0).to_dict()
