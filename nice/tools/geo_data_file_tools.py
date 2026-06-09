import geopandas as gpd
import pandas as pd

from nice import DATA_DIR


def convert_df_to_gdf(
    data, lat_col="Latitude", lon_col="Longitude", crs_val=4269, data_col=None
):
    # print("CONVERTING TO GDF")
    data[lat_col] = pd.to_numeric(data[lat_col], errors="coerce")
    data[lon_col] = pd.to_numeric(data[lon_col], errors="coerce")
    if data_col is not None:
        data[data_col] = pd.to_numeric(data[data_col], errors="coerce")
    df_geo = gpd.GeoDataFrame(
        data, geometry=gpd.points_from_xy(data[lon_col], data[lat_col], crs=crs_val)
    )
    return df_geo


def load_us_state_boundaries(year="2023"):
    state_filepath = DATA_DIR / f"tl_{year}_us_state" / f"tl_{year}_us_state.shp"
    if not state_filepath.is_file():
        state_filepath = f"https://www2.census.gov/geo/tiger/TIGER{year}/STATE/tl_{year}_us_state.zip"
    map_df = gpd.read_file(state_filepath)  # ,crs=4269)
    non_continental = ["HI", "VI", "MP", "GU", "AK", "AS", "PR"]
    for n in non_continental:
        map_df = map_df[map_df.STUSPS != n]
    return map_df


def load_rto_regions():
    iso_fpath = DATA_DIR / "rto_WKT.csv"
    iso_df = gpd.read_file(iso_fpath)
    non_continental = [
        "rto33",
        "rto34",
        "rto35",
        "rto36",
        "rto37",
        "rto38",
        "rto39",
        "rto40",
        "rto41",
    ]
    for n in non_continental:
        iso_df = iso_df[iso_df.rto != n]
    iso_df = iso_df.drop(columns=["WKT"])
    return iso_df


def convert_rto_to_iso():
    pass
