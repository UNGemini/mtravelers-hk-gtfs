"""Static Light Rail stop coordinates for offline / CI use.

Hong Kong geodata.gov.hk / map.gov.hk locationSearch endpoints frequently
return 403/503 to datacenter IPs. Prefer the bundled JSON (and optional
process cache) instead of live geocoding.
"""

from __future__ import annotations

import json
import pickle
from pathlib import Path
from typing import Dict, Optional

# src/common/ -> repo root
_REPO_ROOT = Path(__file__).resolve().parents[2]
BUNDLED_STOPS_PATH = _REPO_ROOT / "data" / "light_rail_stops.json"
CACHE_STOPS_PATH = _REPO_ROOT / ".cache" / "light_rail_stops.pkl"


def load_bundled_light_rail_stops() -> Dict[str, Dict]:
    """Load stop_id -> {stop_id, name_en, name_tc, lat, lon} from repo data."""
    if not BUNDLED_STOPS_PATH.is_file():
        return {}
    try:
        with BUNDLED_STOPS_PATH.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return data
    except (OSError, json.JSONDecodeError):
        return {}
    return {}


def load_cached_light_rail_stops() -> Dict[str, Dict]:
    """Load stops from the pipeline pickle cache if present."""
    if not CACHE_STOPS_PATH.is_file():
        return {}
    try:
        with CACHE_STOPS_PATH.open("rb") as f:
            data = pickle.load(f)
        if isinstance(data, dict):
            return data
    except Exception:
        return {}
    return {}


def load_light_rail_stop_coords() -> Dict[str, Dict]:
    """Merge bundled + cache coords (cache wins on conflict)."""
    merged = dict(load_bundled_light_rail_stops())
    cached = load_cached_light_rail_stops()
    for stop_id, rec in cached.items():
        if not isinstance(rec, dict):
            continue
        lat = rec.get("lat")
        lon = rec.get("lon")
        if lat is None or lon is None:
            continue
        base = dict(merged.get(stop_id, {}))
        base.update(
            {
                "stop_id": rec.get("stop_id", stop_id),
                "name_en": rec.get("name_en") or base.get("name_en"),
                "name_tc": rec.get("name_tc") or base.get("name_tc"),
                "lat": float(lat),
                "lon": float(lon),
            }
        )
        merged[stop_id] = base
    return merged


def lookup_stop_coords(
    stop_id: str,
    coords: Optional[Dict[str, Dict]] = None,
) -> tuple[Optional[float], Optional[float]]:
    coords = coords if coords is not None else load_light_rail_stop_coords()
    rec = coords.get(stop_id) or {}
    lat, lon = rec.get("lat"), rec.get("lon")
    if lat is None or lon is None:
        return None, None
    try:
        return float(lat), float(lon)
    except (TypeError, ValueError):
        return None, None
