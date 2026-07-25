import pandas as pd

from src.processing.stop_times import generate_stop_times_for_agency_optimized


def test_gmb_stop_times_works_without_region_column_on_trips():
    """Fallback GMB trips historically omitted region; generation must still work."""
    trips = pd.DataFrame(
        [
            {
                "route_id": "GMB-HKI-69",
                "service_id": "GMB_DEFAULT_SERVICE",
                "trip_id": "GMB-HKI-69-1",
                "direction_id": 0,
                "route_seq": 1,
                "route_code": "69",
                "route_short_name": "HKI-69",
                "original_service_id": "GMB_DEFAULT_SERVICE",
            }
        ]
    )
    stoptimes = pd.DataFrame(
        [
            {
                "region": "HKI",
                "route_code": "69",
                "route_seq": 1,
                "stop_id": "GMB-1",
                "sequence": 1,
            },
            {
                "region": "HKI",
                "route_code": "69",
                "route_seq": 1,
                "stop_id": "GMB-2",
                "sequence": 2,
            },
        ]
    )

    result = generate_stop_times_for_agency_optimized(
        agency_id="GMB",
        agency_trips_df=trips,
        agency_stoptimes_df=stoptimes,
        gov_routes_df=pd.DataFrame(),
        gov_trips_df=pd.DataFrame(),
        gov_frequencies_df=pd.DataFrame(),
        journey_time_data={},
        unified_to_original_map={},
        silent=True,
    )

    assert not result.empty
    assert set(result["trip_id"]) == {"GMB-HKI-69-1"}
    assert list(result["stop_sequence"]) == [1, 2]
    assert list(result["stop_id"]) == ["GMB-1", "GMB-2"]


def test_gmb_stop_times_with_region_column():
    trips = pd.DataFrame(
        [
            {
                "route_id": "GMB-NT-1",
                "service_id": "GMB-NT-1-287",
                "trip_id": "GMB-NT-1-287-2",
                "direction_id": 1,
                "route_seq": 2,
                "route_code": "1",
                "region": "NT",
                "route_short_name": "NT-1",
                "original_service_id": "287",
            }
        ]
    )
    stoptimes = pd.DataFrame(
        [
            {
                "region": "NT",
                "route_code": "1",
                "route_seq": 2,
                "stop_id": "GMB-10",
                "sequence": 1,
            },
            {
                "region": "NT",
                "route_code": "1",
                "route_seq": 2,
                "stop_id": "GMB-11",
                "sequence": 2,
            },
        ]
    )

    result = generate_stop_times_for_agency_optimized(
        agency_id="GMB",
        agency_trips_df=trips,
        agency_stoptimes_df=stoptimes,
        gov_routes_df=pd.DataFrame(),
        gov_trips_df=pd.DataFrame(),
        gov_frequencies_df=pd.DataFrame(),
        journey_time_data={},
        unified_to_original_map={},
        silent=True,
    )

    assert len(result) == 2
    assert result.iloc[0]["trip_id"] == "GMB-NT-1-287-2"
