import geopandas as gpd
import geopy
import numpy as np
import pandas as pd
from geopy.distance import geodesic
from shapely.geometry import Polygon

from nice import DATA_DIR


def load_reference_pv_supply_curve(crs="EPSG:4326", as_gpd=True):
    # column_lookup_filename = "pv_column_lookup.csv"
    # column_lu = pd.read_csv(column_lookup_fpath)

    grid_cell_length = 11.5  # km
    distance_to_side = grid_cell_length / 2
    distance_to_corner = np.sqrt((distance_to_side**2) + (distance_to_side**2))

    l_corner = geodesic(kilometers=distance_to_corner)
    l_side = geodesic(kilometers=distance_to_side)

    filename = "solar_reference_access_2035_moderate_supply_curve.csv"
    fpath = DATA_DIR / "RevSupplyCurves_UtilityPV_2024" / filename
    df = pd.read_csv(fpath)

    df.set_index(keys=["sc_point_gid"], inplace=True)

    if not as_gpd:
        return df

    df["area_developable_sq_km"]

    # 0=north, 90=east, 180=south, 270=west
    # top right -> bottom right -> bottom left -> top left
    # 45, 135, 225, 315
    corner_bearings = [45.0, 135.0, 225.0, 315.0]
    side_bearings = [0.0, 90.0, 180.0, 270.0]

    geometry_df = pd.Series(index=df.index, name="geometry")
    for gi in df.index.to_list():
        centroid = geopy.Point(df.loc[gi]["latitude"], df.loc[gi]["longitude"])

        bounding_pts = []
        for i, b_corner in enumerate(corner_bearings):
            # get side point
            side_pt = l_side.destination(centroid, bearing=side_bearings[i])
            corner_pt = l_corner.destination(centroid, bearing=b_corner)
            # have to do in reverse order
            bounding_pts.append((side_pt.longitude, side_pt.latitude))
            bounding_pts.append((corner_pt.longitude, corner_pt.latitude))
        # shp = Polygon(bounding_pts)
        geometry_df.loc[gi] = Polygon(bounding_pts)

    df = pd.concat([df, geometry_df], axis=1)
    gdf = gpd.GeoDataFrame(df, crs=crs)
    return gdf


def calc_distance(lat1, lon1, lat2, lon2):
    pa = geopy.Point(lat1, lon1)
    pb = geopy.Point(lat2, lon2)
    return geodesic(pa, pb).kilometers


def find_distance(row, other_lat, other_lon):
    pa = geopy.Point(row["latitude"], row["longitude"])

    if np.isnan(other_lat) or np.isnan(other_lon):
        return 1e9
    pb = geopy.Point(other_lat, other_lon)
    return geodesic(pa, pb).kilometers


def find_distance_df(row):
    pa = geopy.Point(row["rev_latitude"], row["rev_longitude"])
    pb = geopy.Point(row["plant_latitude"], row["plant_longitude"])
    return geodesic(pa, pb).kilometers


def find_nearest_rev_site(plant_geo, rev_data, missing_plant_ids):
    found_stuff = pd.DataFrame(
        index=missing_plant_ids, columns=["State", "Rev GID", "Distance to Rev GID"]
    )

    states_to_check = list(set(plant_geo.loc[missing_plant_ids]["State"].to_list()))
    for state in states_to_check:
        plant_geo_state = plant_geo[plant_geo["State"] == state]
        rev_data_state = rev_data[rev_data["state"] == state]

        missing_plant_ids_state = list(
            set(plant_geo_state.index.to_list()) & set(missing_plant_ids)
        )

        for ii in missing_plant_ids_state:
            distance_to_sites = rev_data_state.apply(
                find_distance,
                axis=1,
                args=(
                    plant_geo_state.loc[ii]["Latitude"],
                    plant_geo_state.loc[ii]["Longitude"],
                ),
            )
            found_stuff.loc[ii, "Rev GID"] = distance_to_sites.argmin()
            found_stuff.loc[ii, "Distance to Rev GID"] = distance_to_sites.min()
            found_stuff.loc[ii, "State"] = state

    return found_stuff
