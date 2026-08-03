import calendar
from pathlib import Path

import pandas as pd

from nice import DATA_DIR
from nice.tools.create_data import create_surplus_interconnect_data
from nice.tools.create_monthly_data import summarize_monthly_eia_data
from nice.tools.spi_tools import calc_spi_factor


def generate_annual_and_monthly_spi_from_eia(
    output_data_dir=DATA_DIR / "nice_data_aggregated",
    surplus_threshold_fraction=0.8,
    full_utilization_threshold=1.0,
    data_year=2024,
    missing_val=None,
):
    # Create folder to save or load data to if needed
    if not output_data_dir.exists():
        Path(output_data_dir).mkdir(exist_ok=True, parents=True)

    # Output filepath for the summary data
    missing_val_desc = "None" if missing_val is None else missing_val
    spi_data_fpath = (
        output_data_dir / f"summary_data_missing_is_{missing_val_desc}_{data_year}.csv"
    )

    # Output filepath for the SPI monthly data
    spi_monthly_data_fpath = (
        output_data_dir / f"monthly_Netgen_surplus_interconnect_{data_year}.csv"
    )

    # Create monthly data if needed
    if not spi_monthly_data_fpath.is_file():
        print("Running monthly")
        m12_data = summarize_monthly_eia_data(data_year=data_year)
        m12_data.sort_index().to_csv(spi_monthly_data_fpath)
        print("Completed monthly")
    else:
        m12_data = pd.read_csv(spi_monthly_data_fpath, index_col="Unnamed: 0")

    # Create aggregated data if needed
    if not spi_data_fpath.is_file():
        print("Running summary")
        data = create_surplus_interconnect_data(
            missing_val=missing_val, data_year=data_year
        )
        data.sort_index().to_csv(spi_data_fpath)
        print("Completed summary")
    else:
        data = pd.read_csv(spi_data_fpath, index_col="Unnamed: 0")

    # Set the index of both dataframes to Plant Code and the Prime Mover type
    m12_data.index.name = "Plant Code"
    m12_data.reset_index(drop=False, inplace=True)
    m12_data.set_index(keys=["Plant Code", "Prime Mover"], inplace=True)
    data.set_index(keys=["Plant Code", "Prime Mover"], inplace=True)

    # Calculate the capacity factor of each generator type within a plant
    data["Capacity Factor"] = data["Net Generation (Megawatthours)"] / (
        data["Nameplate Capacity (MW)"] * 8760
    )

    # Saturate the capacity factor to a maximum value of 1.
    for i in data[data["Capacity Factor"] > 1.0].index.to_list():
        data.loc[i, "Capacity Factor"] = 1.0

    # Clip the capacity factor to a minimum value of 0
    for i in data[data["Capacity Factor"] < 0.0].index.to_list():
        data.loc[i, "Capacity Factor"] = 0.0

    # Calculate the surplus interconnection factor for the annual data
    calc_spi_factor(
        data,
        "Capacity Factor",
        "Surplus Interconnect Factor",
        surplus_threshold_fraction,
        full_utilization_threshold=full_utilization_threshold,
    )

    # Combine the datasets
    shared_indices = (set(m12_data.index.to_list())).intersection(
        set(data.index.to_list())
    )
    shared_indx = (
        pd.MultiIndex.from_tuples(
            list(shared_indices), names=["Plant Code", "Prime Mover"]
        )
    ).sort_values()
    df = pd.concat([data.loc[shared_indx], m12_data.loc[shared_indx]], axis=1)

    # Calculate the monthly surplus interconnection
    column_fmt = "Netgen {month}"
    months_to_n_days = {
        calendar.month_name[i]: calendar.monthrange(2024, i)[1] for i in range(1, 13)
    }
    # m12_cols = [column_fmt.format(month=m) for m in list(months_to_n_days.keys())]

    for month, n_days in months_to_n_days.items():
        hours_per_month = n_days * 24
        df[f"{month} Capacity Factor"] = df[column_fmt.format(month=month)] / (
            df["Nameplate Capacity (MW)"] * hours_per_month
        )

        calc_spi_factor(
            df,
            f"{month} Capacity Factor",
            f"{month} Surplus Interconnect Factor",
            surplus_threshold_fraction,
            full_utilization_threshold=full_utilization_threshold,
        )

        df[f"{month} Surplus Interconnect Capacity (MW)"] = (
            df["Nameplate Capacity (MW)"] * df[f"{month} Surplus Interconnect Factor"]
        )

        return df
