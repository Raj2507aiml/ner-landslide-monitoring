"""
Road Network Service - Phase 8 Checkpoint 17.1

Fetches road infrastructure from OpenStreetMap Overpass API, parses GeoJSON LineStrings,
and provides deterministic disk caching for low latency and high availability.
"""

import os
import json
import time
import logging
from typing import List, Dict, Any, Optional
import httpx

from app.services.spatial_query_service import calculate_bounding_box

logger = logging.getLogger(__name__)

CURRENT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(CURRENT_DIR, "data")
CACHE_DIR = os.path.join(DATA_DIR, "infrastructure_cache")
os.makedirs(CACHE_DIR, exist_ok=True)

CACHE_TTL_SECONDS = 86400  # 24 Hours

OVERPASS_ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter"
]

HIGHWAY_CLASSES = [
    "motorway",
    "trunk",
    "primary",
    "secondary",
    "tertiary",
    "unclassified",
    "residential"
]

class RoadNetworkService:
    @staticmethod
    def get_cache_path(latitude: float, longitude: float, radius_km: float) -> str:
        """
        Generates a deterministic cache file path for given coordinates and radius.
        """
        key = f"osm_roads_{round(latitude, 3)}_{round(longitude, 3)}_{round(radius_km, 1)}.json"
        return os.path.join(CACHE_DIR, key)

    @classmethod
    def load_from_cache(cls, cache_path: str, allow_stale: bool = False) -> Optional[List[Dict[str, Any]]]:
        """
        Loads road features from disk cache if present and fresh.
        """
        if not os.path.exists(cache_path):
            return None

        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            timestamp = data.get("timestamp", 0)
            if allow_stale or (time.time() - timestamp < CACHE_TTL_SECONDS):
                return data.get("roads", [])
        except Exception as e:
            logger.warning(f"Failed to read infrastructure cache from {cache_path}: {e}")

        return None

    @classmethod
    def save_to_cache(cls, cache_path: str, roads: List[Dict[str, Any]]) -> None:
        """
        Saves parsed road infrastructure to disk cache.
        """
        try:
            payload = {
                "timestamp": time.time(),
                "count": len(roads),
                "roads": roads
            }
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save infrastructure cache to {cache_path}: {e}")

    @classmethod
    def build_overpass_query(cls, min_lat: float, min_lon: float, max_lat: float, max_lon: float) -> str:
        """
        Builds an optimized Overpass QL query string for highway geometries within bbox.
        """
        highway_regex = "^(" + "|".join(HIGHWAY_CLASSES) + ")$"
        return f"""
        [out:json][timeout:25];
        (
          way["highway"~"{highway_regex}"]
            ({min_lat},{min_lon},{max_lat},{max_lon});
        );
        out geom;
        """

    @classmethod
    def parse_overpass_response(cls, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Parses Overpass JSON elements into standardized GeoJSON LineString road objects.
        Strictly formats coordinates as [longitude, latitude].
        """
        roads: List[Dict[str, Any]] = []
        elements = data.get("elements", [])

        for elem in elements:
            if elem.get("type") != "way":
                continue

            raw_geom = elem.get("geometry", [])
            if not raw_geom or len(raw_geom) < 2:
                continue

            # Ensure strict GeoJSON [longitude, latitude] coordinate ordering
            coordinates = [[round(pt["lon"], 6), round(pt["lat"], 6)] for pt in raw_geom if "lat" in pt and "lon" in pt]
            if len(coordinates) < 2:
                continue

            tags = elem.get("tags", {})
            osm_id = str(elem.get("id"))
            name = tags.get("name")
            ref = tags.get("ref")
            highway_type = tags.get("highway", "unclassified")

            roads.append({
                "osm_id": osm_id,
                "name": name,
                "ref": ref,
                "highway_type": highway_type,
                "geometry": {
                    "type": "LineString",
                    "coordinates": coordinates
                }
            })

        return roads

    @classmethod
    def fetch_roads(
        cls,
        latitude: float,
        longitude: float,
        radius_km: float = 5.0,
        use_cache: bool = True,
        mock_raw_data: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieves road features around specified location.
        Leverages disk cache, queries Overpass API with endpoint fallback, and handles network errors safely.
        """
        # If mock data passed (for deterministic unit tests), parse and return directly
        if mock_raw_data is not None:
            return cls.parse_overpass_response(mock_raw_data)

        cache_path = cls.get_cache_path(latitude, longitude, radius_km)

        if use_cache:
            cached_roads = cls.load_from_cache(cache_path)
            if cached_roads is not None:
                return cached_roads

        min_lat, max_lat, min_lon, max_lon = calculate_bounding_box(latitude, longitude, radius_km)
        query = cls.build_overpass_query(min_lat, min_lon, max_lat, max_lon)

        # Attempt fetching from Overpass mirrors
        roads = None
        for endpoint in OVERPASS_ENDPOINTS:
            try:
                with httpx.Client(timeout=20.0) as client:
                    resp = client.post(endpoint, data={"data": query})
                    if resp.status_code == 200:
                        data = resp.json()
                        roads = cls.parse_overpass_response(data)
                        break
                    else:
                        logger.warning(f"Overpass endpoint {endpoint} returned status {resp.status_code}")
            except Exception as e:
                logger.warning(f"Failed to query Overpass endpoint {endpoint}: {e}")

        # If network requests failed, attempt loading stale cache
        if roads is None:
            stale_cached = cls.load_from_cache(cache_path, allow_stale=True)
            if stale_cached is not None:
                logger.info(f"Using stale cached roads for ({latitude}, {longitude})")
                return stale_cached
            # Fallback gracefully to empty list
            logger.error(f"Could not retrieve road infrastructure for ({latitude}, {longitude})")
            return []

        # Cache valid response
        if use_cache:
            cls.save_to_cache(cache_path, roads)

        return roads
