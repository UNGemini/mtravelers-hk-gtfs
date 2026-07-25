# github.com/hkbus/hk-bus-crawling (Patched for mtravelers pipeline)

import asyncio
import logging
from pyproj import Transformer
import json
import string
import httpx
import csv
import re
import random

# HK1980 Grid to WGS84 transformer
epsgTransformer = Transformer.from_crs('epsg:2326', 'epsg:4326')

def check_and_add_result(results, query_name, stop_info, exit_char, barrier_free, final_res_list):
    for result in results:
        if result.get('nameZH') == query_name:
            lat, lng = epsgTransformer.transform(result['y'], result['x'])
            final_res_list.append({
                "station_code": stop_info["station_code"],
                "station_name_en": stop_info["name_en"],
                "station_name_zh": stop_info["name_tc"],
                "exit": exit_char,
                "lat": lat,
                "lon": lng,
                "barrier_free": barrier_free,
            })
            return True
    return False

async def fetch_geodata_with_retry(client, url, max_retries=5, silent=False):
    """Fetches geodata with exponential backoff to handle 503 / 429 rate limits."""
    for attempt in range(max_retries):
        try:
            res = await client.get(url)
            
            # Handle rate limiting status codes gracefully
            if res.status_code in (429, 503):
                delay = (2 ** attempt) + random.uniform(0.5, 1.5)
                if not silent:
                    print(f"CSDI API rate-limited ({res.status_code}). Retrying in {delay:.2f}s (Attempt {attempt + 1}/{max_retries})...")
                await asyncio.sleep(delay)
                continue
            
            res.raise_for_status()
            return res.json()
            
        except httpx.HTTPStatusError as e:
            if attempt == max_retries - 1 and not silent:
                print(f"HTTP error for {url}: {e}")
        except (httpx.RequestError, json.JSONDecodeError) as e:
            if attempt == max_retries - 1 and not silent:
                print(f"Request error for {url}: {e}")
        
        # Brief pause before retrying on non-503 errors
        await asyncio.sleep(1.0)
        
    return None

async def fetch_mtr_exits(silent=False):
    if not silent:
        print("Fetching MTR exit data from opendata.mtr.com.hk and geodata.gov.hk...")

    final_results = []
    mtr_stops = {}

    # Use a standard browser User-Agent header to avoid basic WAF blocks
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    async with httpx.AsyncClient(timeout=httpx.Timeout(30.0, pool=None), headers=headers) as client:
        # Fetch MTR stations
        try:
            stations_res = await client.get('https://opendata.mtr.com.hk/data/mtr_lines_and_stations.csv')
            stations_res.raise_for_status()
            stations_res.encoding = 'utf-8'
            reader = csv.reader(stations_res.text.strip().split("\n"))
            next(reader, None)
            for entry in reader:
                station_code = entry[2]
                mtr_stops[entry[3]] = {"station_code": station_code, "name_tc": entry[4], "name_en": entry[5]}
        except httpx.HTTPError as e:
            if not silent:
                print(f"Error fetching MTR station list: {e}")
            return []

        # Fetch barrier-free (lift) info
        try:
            facilities_res = await client.get("https://opendata.mtr.com.hk/data/barrier_free_facilities.csv")
            facilities_res.raise_for_status()
            facilities_res.encoding = 'utf-8'
            reader = csv.reader(facilities_res.text.strip().split("\n"))
            for entry in reader:
                if len(entry) > 3 and entry[2] == 'Y' and entry[3] != '' and entry[0] in mtr_stops:
                    for exit_code in re.findall(r"[A-Z][0-9]*", entry[3]):
                        mtr_stops[entry[0]][exit_code.strip()] = True
        except httpx.HTTPError as e:
            if not silent:
                print(f"Error fetching barrier-free facilities: {e}")

        # Crawl exit geolocations
        for key, stop in mtr_stops.items():
            geo_query = '港鐵' + stop['name_tc'] + '站進出口'
            search_url = "https://www.map.gov.hk/gs/api/v1.0.0/locationSearch?q=" + geo_query

            # Fetch through our retry-enabled helper
            geo_results = await fetch_geodata_with_retry(client, search_url, silent=silent)

            if geo_results:
                for char in string.ascii_uppercase:
                    q = '港鐵' + stop['name_tc'] + '站-' + str(char) + '進出口'
                    check_and_add_result(geo_results, q, stop, char, char in stop, final_results)

                    for i in range(1, 10):
                        exit_code = char + str(i)
                        q = '港鐵' + stop['name_tc'] + '站-' + exit_code + '進出口'
                        check_and_add_result(geo_results, q, stop, exit_code, exit_code in stop, final_results)

            # Added a 0.5s pause between stations to prevent triggering server WAF limits
            await asyncio.sleep(0.5)

    # Deduplicate results
    deduped_results = list({(v['station_name_zh'] + v['exit']): v for v in final_results}.values())

    if not silent:
        print(f"Successfully fetched and processed {len(deduped_results)} unique MTR station exits.")

    return deduped_results

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    logging.getLogger('httpx').setLevel(logging.WARNING)
    asyncio.run(fetch_mtr_exits())