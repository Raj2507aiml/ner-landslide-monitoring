import os
import json
import math
from typing import Dict, Any, Optional

# Load GeoJSON boundary data relative to project path
CURRENT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GEOJSON_PATH = os.path.join(CURRENT_DIR, "data", "ner_boundary.geojson")

def _point_in_ring(x: float, y: float, ring: list) -> bool:
    """Ray-casting algorithm to check if point (x=lng, y=lat) is in a linear ring."""
    inside = False
    n = len(ring)
    if n < 3:
        return False
    p1x, p1y = ring[0]
    for i in range(n + 1):
        p2x, p2y = ring[i % n]
        if y > min(p1y, p2y):
            if y <= max(p1y, p2y):
                if x <= max(p1x, p2x):
                    if p1y != p2y:
                        xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                    if p1x == p2x or x <= xinters:
                        inside = not inside
        p1x, p1y = p2x, p2y
    return inside

def _point_in_polygon(x: float, y: float, polygon: list) -> bool:
    """Check if point is inside a polygon with optional holes."""
    # First ring is exterior, must be inside it
    if not _point_in_ring(x, y, polygon[0]):
        return False
    # Subsequent rings are holes, must NOT be inside them
    for hole in polygon[1:]:
        if _point_in_ring(x, y, hole):
            return False
    return True

# In-memory cached GeoJSON boundary data
_NER_GEOJSON: Optional[Dict[str, Any]] = None

def _get_ner_geojson() -> Optional[Dict[str, Any]]:
    global _NER_GEOJSON
    if _NER_GEOJSON is None:
        if os.path.exists(GEOJSON_PATH):
            try:
                with open(GEOJSON_PATH, "r", encoding="utf-8") as f:
                    _NER_GEOJSON = json.load(f)
            except Exception:
                _NER_GEOJSON = None
    return _NER_GEOJSON

def get_ner_state_name(latitude: float, longitude: float) -> Optional[str]:
    """
    Identifies which of the 8 North Eastern Region states contains the given coordinates.
    Returns the state name (e.g. 'Assam', 'Nagaland', 'Meghalaya', etc.) or None if outside NER.
    """
    geojson = _get_ner_geojson()
    if not geojson:
        # Fallback NER bounding box check
        if 21.9 <= latitude <= 29.5 and 88.0 <= longitude <= 97.4:
            return "North Eastern Region"
        return None

    for feature in geojson.get("features", []):
        geometry = feature.get("geometry", {})
        geom_type = geometry.get("type")
        coords = geometry.get("coordinates", [])
        state_name = feature.get("properties", {}).get("state_name")

        if geom_type == "Polygon":
            if _point_in_polygon(longitude, latitude, coords):
                return state_name
        elif geom_type == "MultiPolygon":
            for poly in coords:
                if _point_in_polygon(longitude, latitude, poly):
                    return state_name
    return None

def is_inside_ner(latitude: float, longitude: float) -> bool:
    """
    Checks if a given coordinate lies within the boundary of 
    the 8 states in the North Eastern Region of India.
    """
    return get_ner_state_name(latitude, longitude) is not None

def calculate_aoi(latitude: float, longitude: float, radius_km: float = 5.0) -> Dict[str, Any]:
    """
    Calculates a geographically reasonable bounding box (north, south, east, west)
    around a point based on a radius in kilometers.
    
    1 degree of Latitude = ~111.1 km
    1 degree of Longitude = ~111.1 * cos(latitude) km
    """
    # 1 degree of latitude in km
    lat_degree_km = 111.1
    
    # Delta latitude in degrees
    delta_lat = radius_km / lat_degree_km
    
    # Delta longitude in degrees (accounting for latitude scaling)
    lat_rad = math.radians(latitude)
    cos_lat = math.cos(lat_rad)
    
    # Ensure cos_lat is not zero to prevent division by zero (extreme poles)
    if cos_lat > 0.0001:
        delta_lng = radius_km / (lat_degree_km * cos_lat)
    else:
        delta_lng = radius_km / lat_degree_km

    # Define bounding box
    north = latitude + delta_lat
    south = latitude - delta_lat
    east = longitude + delta_lng
    west = longitude - delta_lng

    # Clamp coordinates to valid spherical boundaries
    north = max(-90.0, min(90.0, north))
    south = max(-90.0, min(90.0, south))
    
    # Adjust longitude wrap-around if it crosses the date line
    if east > 180.0:
        east -= 360.0
    if west < -180.0:
        west += 360.0

    return {
        "radius_km": radius_km,
        "bounding_box": {
            "north": round(north, 6),
            "south": round(south, 6),
            "east": round(east, 6),
            "west": round(west, 6)
        }
    }
