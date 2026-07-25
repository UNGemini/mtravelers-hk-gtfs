# orig: github.com/hkbus/hk-bus-crawling (Patched for mtravelers)

import asyncio
import csv
import logging

import httpx

from src.common.light_rail_coords import load_light_rail_stop_coords

LIGHT_RAIL_ROUTES_URL = "https://opendata.mtr.com.hk/data/light_rail_routes_and_stops.csv"


async def fetch_light_rail_stops(silent=False):
    """Fetch Light Rail stop ids/names and attach coordinates from bundled data.

    Live geodata.gov.hk / map.gov.hk lookup is intentionally skipped: those
    endpoints return 403 for most CI / cloud IPs and only slow the pipeline.
    Coordinates come from data/light_rail_stops.json (and optional .cache).
    """
    if not silent:
        print("Fetching Light Rail stops...")

    coords = load_light_rail_stop_coords()
    stop_list = {}

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(30.0, pool=None)) as client:
            r = await client.get(LIGHT_RAIL_ROUTES_URL)
            r.raise_for_status()
            text = r.text
    except (httpx.RequestError, httpx.HTTPStatusError) as e:
        logging.error(f"Error fetching Light Rail data: {e}")
        # Fall back to bundled/cache only so export can still emit stops.
        for stop_id, rec in coords.items():
            stop_list[stop_id] = {
                "stop_id": stop_id,
                "name_en": rec.get("name_en"),
                "name_tc": rec.get("name_tc"),
                "lat": rec.get("lat"),
                "lon": rec.get("lon"),
            }
        if not silent:
            print(f"Using {len(stop_list)} bundled Light Rail stops (MTR CSV unavailable).")
        return stop_list

    reader = csv.reader(text.splitlines())
    next(reader, None)
    routes = [route for route in reader if len(route) == 7]

    missing = []
    for _, _, _, stop_id, chn, eng, _ in routes:
        light_rail_id = "LR" + stop_id
        if light_rail_id in stop_list:
            continue
        rec = coords.get(light_rail_id, {})
        lat, lon = rec.get("lat"), rec.get("lon")
        if lat is None or lon is None:
            missing.append(light_rail_id)
        stop_list[light_rail_id] = {
            "stop_id": light_rail_id,
            "name_en": eng,
            "name_tc": chn,
            "lat": lat,
            "lon": lon,
        }

    with_coords = sum(1 for s in stop_list.values() if s.get("lat") is not None and s.get("lon") is not None)
    if not silent:
        print(
            f"Loaded {len(stop_list)} Light Rail stops "
            f"({with_coords} with coordinates from bundled/cache data)."
        )
        if missing:
            print(
                f"Warning: {len(missing)} Light Rail stop(s) missing coordinates "
                f"(no live geodata lookup). Example: {missing[:5]}"
            )

    return stop_list


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    stops = asyncio.run(fetch_light_rail_stops())
    print(f"Successfully fetched {len(stops)} Light Rail stops.")
