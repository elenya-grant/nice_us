def calc_spi_factor(
    df,
    cf_colname,
    spi_colname,
    surplus_threshold_fraction,
    full_utilization_threshold=1.0,
):
    # Clip CF to 1.0
    for i in df[df[cf_colname] > 1.0].index.to_list():
        df.loc[i, cf_colname] = 1.0

    # Clip CF to 0.0
    for i in df[df[cf_colname] < 0.0].index.to_list():
        df.loc[i, cf_colname] = 0.0

    # surplus interconnection = 1 - capacity factor
    df[spi_colname] = 1.0 - df[cf_colname]

    # if CF is greater than the full_utilization_threshold, set the SPI to 0.0
    for i in df[df[cf_colname] >= full_utilization_threshold].index.to_list():
        df.loc[i, spi_colname] = 0.0

    # if CF is greater than the surplus_threshold_limit, set the SPI to 0.0
    for i in df[df[cf_colname] > surplus_threshold_fraction].index.to_list():
        df.loc[i, spi_colname] = 0.0

    return df
