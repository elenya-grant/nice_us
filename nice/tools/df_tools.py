import pandas as pd


def convert_to_type(df, new_col, old_col, data_type):
    df[new_col] = df[old_col].astype(data_type)
    return df


def add_extra_cols(df, col_to_duplicate, new_colname):
    df = pd.concat([df, df[col_to_duplicate].rename(new_colname)], axis=1)
    return df
