# orig: github.com/hkbus/hk-bus-crawling (Patched for MCT)

import asyncio
import csv
import json
from pyproj import Transformer
import logging
import httpx
import random

async def fetch_light_rail_stops(silent=False):
    # Fetch Light Rail stop data and their locations
    if not silent:
        print("Fetching Light Rail stops...")

    # The ultimate browser disguise to bypass WAF
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7",
        "Referer": "https://www.map.gov.hk/gm/",
        "Origin": "https://www.map.gov.hk",
        "Connection": "keep-alive",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin"
    }

    a_client = httpx.AsyncClient(timeout=httpx.Timeout(30.0, pool=None), headers=headers)
    epsg_transformer = Transformer.from_crs('epsg:2326', 'epsg:4326')
    stop_list = {}

    try:
        r = await a_client.get('https://opendata.mtr.com.hk/data/light_rail_routes_and_stops.csv')
        r.raise_for_status()
    except httpx.RequestError as e:
        logging.error(f"Error fetching Light Rail data: {e}")
        await a_client.aclose()
        return {}

    reader = csv.reader(r.text.splitlines())
    csv_headers = next(reader, None)
    routes = [route for route in reader if len(route) == 7]

    for _, _, _, stop_id, chn, eng, _ in routes:
        light_rail_id = "LR" + stop_id
        if light_rail_id not in stop_list:
            url = f'https://www.map.gov.hk/gs/api/v1.0.0/locationSearch?q={chn}輕鐵站'
            
            max_retries = 5
            for attempt in range(max_retries):
                try:
                    r_geo = await a_client.get(url)
                    
                    # Handle rate limiting status codes gracefully
                    if r_geo.status_code in (429, 503):
                        delay = (2 ** attempt) + random.uniform(0.5, 1.5)
                        if not silent:
                            print(f"CSDI API rate-limited ({r_geo.status_code}). Retrying {chn} in {delay:.2f}s (Attempt {attempt + 1}/{max_retries})...")
                        await asyncio.sleep(delay)
                        continue
                        
                    r_geo.raise_for_status()
                    data = r_geo.json()
                    
                    if data and len(data) > 0:
                        lat, lng = epsg_transformer.transform(data[0]['y'], data[0]['x'])
                        stop_list[light_rail_id] = {
                            "stop_id": light_rail_id,
                            "name_en": eng,
                            "name_tc": chn,
                            "lat": lat,
                            "lon": lng
                        }
                    else:
                        if not silent:
                            print(f"Warning: No location found for {chn} Light Rail Station.")
                            
                    break # Break out of the retry loop on success

                except httpx.HTTPStatusError as e:
                    if attempt == max_retries - 1 and not silent:
                        logging.error(f"HTTP error processing geo data for {chn}: {e}")
                    await asyncio.sleep(1.0)
                except (httpx.RequestError, json.JSONDecodeError, IndexError, KeyError) as e:
                    if attempt == max_retries - 1 and not silent:
                        logging.error(f"Error processing geo data for {chn}: {e}")
                    await asyncio.sleep(1.0)
            
            # Polite 2-second delay between processing distinct stops
            await asyncio.sleep(2.0)

    await a_client.aclose()
    return stop_list

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    logging.getLogger('httpx').setLevel(logging.WARNING)
    stops = asyncio.run(fetch_light_rail_stops())
    with open('light_rail_stops.json', 'w', encoding='utf-8') as f:
        json.dump(stops, f, ensure_ascii=False, indent=4)
    print(f"Successfully fetched {len(stops)} Light Rail stops.")