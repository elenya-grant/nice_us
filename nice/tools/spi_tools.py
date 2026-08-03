def calc_spi_factor(
    df,
    cf_colname,
    spi_colname,
    surplus_threshold_fraction,
    full_utilization_threshold=1.0,
):
    """Calculate the Surplus Interconnection Factor based off the capacity factor.
    The surplus interconnection factor is 0 when the capacity factor is greater
    than the ``full_utilization_threshold``. The SPI is calculated as
    ``surplus_threshold_fraction - capacity factor``

    Args:
        df (pd.DataFrame): dataframe of generator data
        cf_colname (str): name of column in ``df`` that contains the capacity factor
            (ranging in values of 0 to 1)
        spi_colname (str): name of column in ``df`` that the surplus interconnection
            factor should be named as
        surplus_threshold_fraction (float): Utilization to calculate the SPI from, ranging from 0 - 1.
        full_utilization_threshold (float, optional): Capacity factor that is considered
            "fully utilized" and the SPI is set to zero.. Defaults to 1.0.

    Returns:
        pd.DataFrame: dataframe with new column with the surplus interconnection factor.
    """
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
