from src.common.light_rail_coords import load_bundled_light_rail_stops, lookup_stop_coords
from src.export.light_rail import build_light_rail_gtfs_data


def test_bundled_light_rail_stops_have_coords():
    stops = load_bundled_light_rail_stops()
    assert len(stops) >= 60
    lat, lon = lookup_stop_coords("LR920", stops)
    assert lat is not None and lon is not None
    # Sam Shing is in Tuen Mun
    assert 22.3 < lat < 22.5
    assert 113.9 < lon < 114.1


def test_build_light_rail_gtfs_data_does_not_require_geodata():
    # Should succeed using MTR CSV + bundled coords (no map.gov.hk).
    data = build_light_rail_gtfs_data(None, silent=True)
    assert data.routes is not None
    assert not data.routes.empty
    assert data.trips is not None
    assert not data.trips.empty
    assert data.stops is not None
    assert not data.stops.empty
    # Most stops should have coordinates from bundled JSON.
    with_coords = data.stops["stop_lat"].notna().sum()
    assert with_coords >= 50
