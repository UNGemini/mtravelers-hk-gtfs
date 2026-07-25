import pandas as pd
from sqlalchemy import create_engine

from src.export.export_gtfs import build_empty_mtr_export_frames
from src.processing.load_raw_data import process_and_load_gov_gtfs_data


def test_process_and_load_gov_gtfs_data_creates_empty_tables_when_inputs_are_empty():
    engine = create_engine("sqlite:///:memory:")

    process_and_load_gov_gtfs_data(
        raw_frequencies=[],
        raw_trips=[],
        raw_routes=[],
        raw_calendar=[],
        raw_calendar_dates=[],
        raw_stops=[],
        raw_stop_times=[],
        raw_fare_attributes=[],
        raw_fare_rules=[],
        engine=engine,
        silent=True,
    )

    expected_tables = {
        "gov_gtfs_frequencies": ["trip_id", "start_time", "end_time", "headway_secs"],
        "gov_gtfs_trips": ["route_id", "service_id", "trip_id"],
        "gov_gtfs_routes": ["route_id", "route_short_name", "route_long_name", "agency_id", "route_type"],
        "gov_gtfs_stops": ["stop_id", "stop_name", "stop_lat", "stop_lon"],
        "gov_gtfs_stop_times": ["trip_id", "arrival_time", "departure_time", "stop_id", "stop_sequence"],
    }

    for table_name, expected_columns in expected_tables.items():
        df = pd.read_sql_query(f"SELECT * FROM {table_name}", engine)
        assert list(df.columns) == expected_columns
        assert df.empty


def test_build_empty_mtr_export_frames_returns_empty_structured_frames():
    routes_df, trips_df, stoptimes_df = build_empty_mtr_export_frames()

    assert routes_df.empty
    assert trips_df.empty
    assert stoptimes_df.empty
    assert list(routes_df.columns) == [
        "route_id",
        "agency_id",
        "route_short_name",
        "route_long_name",
        "route_type",
        "route_color",
        "route_text_color",
    ]
    assert list(trips_df.columns) == [
        "route_id",
        "agency_id",
        "service_id",
        "trip_id",
        "direction_id",
        "original_service_id",
        "route_short_name",
    ]
    assert list(stoptimes_df.columns) == [
        "trip_id",
        "arrival_time",
        "departure_time",
        "stop_id",
        "stop_sequence",
    ]
