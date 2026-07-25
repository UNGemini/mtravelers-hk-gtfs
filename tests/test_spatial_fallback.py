import pandas as pd
from sqlalchemy import create_engine
from shapely.geometry import Point
import geopandas as gpd

from src.processing.load_raw_data import _write_spatial_table_as_sql


def test_write_spatial_table_as_sql_preserves_lat_lon_columns():
    engine = create_engine("sqlite:///:memory:")
    gdf = gpd.GeoDataFrame(
        {"stop_id": [1], "name": ["A"]},
        geometry=[Point(1.23, 4.56)],
        crs="EPSG:4326",
    )

    _write_spatial_table_as_sql(gdf, "test_stops", engine)

    df = pd.read_sql_query("SELECT * FROM test_stops", engine)
    assert "lat" in df.columns
    assert "lon" in df.columns
    assert df.loc[0, "lat"] == 4.56
    assert df.loc[0, "lon"] == 1.23
