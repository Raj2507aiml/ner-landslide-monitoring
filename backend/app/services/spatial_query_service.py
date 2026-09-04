"""
Historical Spatial Intelligence Query Engine — Phase 2.6C Checkpoint 3C

Provides reusable backend functions to calculate geographic bounding boxes,
Haversine distances, and search for historical GSI and NASA landslide incidents.
"""

import math
from datetime import date
from collections import Counter
from sqlalchemy.orm import Session
from app.models.historical_landslide import GSILandslideIncident, NASALandslideEvent

MAX_ALLOWED_RADIUS_KM = 100.0
EARTH_RADIUS_KM = 6371.0088
MAX_MAP_RECORDS_PER_SOURCE = 100


def calculate_bounding_box(latitude: float, longitude: float, radius_km: float) -> tuple[float, float, float, float]:
    """
    Calculates an approximate bounding box around a point based on a search radius.
    
    1 degree of Latitude = ~111.1 km
    1 degree of Longitude = ~111.1 * cos(latitude) km
    """
    lat_degree_km = 111.1
    delta_lat = radius_km / lat_degree_km
    
    lat_rad = math.radians(latitude)
    cos_lat = math.cos(lat_rad)
    
    # Ensure cos_lat is not zero to prevent division by zero at poles
    if cos_lat > 0.0001:
        delta_lng = radius_km / (lat_degree_km * cos_lat)
    else:
        delta_lng = radius_km / lat_degree_km
        
    min_lat = latitude - delta_lat
    max_lat = latitude + delta_lat
    min_lon = longitude - delta_lng
    max_lon = longitude + delta_lng
    
    return min_lat, max_lat, min_lon, max_lon

def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculates the exact great-circle distance between two points using the Haversine formula."""
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    
    a = math.sin(delta_phi / 2.0)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0)**2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    
    return EARTH_RADIUS_KM * c

def validate_inputs(latitude: float, longitude: float, radius_km: float):
    """Validates the coordinates and radius parameters against spatial constraints."""
    if not (-90.0 <= latitude <= 90.0):
        raise ValueError("Latitude must be between -90 and 90 degrees.")
    if not (-180.0 <= longitude <= 180.0):
        raise ValueError("Longitude must be between -180 and 180 degrees.")
    if radius_km <= 0.0:
        raise ValueError("Radius must be a positive number greater than 0.")
    if radius_km > MAX_ALLOWED_RADIUS_KM:
        raise ValueError(f"Radius exceeds the maximum allowed search limit of {MAX_ALLOWED_RADIUS_KM} km.")

def find_nearby_gsi_incidents(db: Session, latitude: float, longitude: float, radius_km: float) -> list[dict]:
    """
    Finds and returns GSI historical landslide incidents within a given radius.
    Applies B-tree bounding box filtering first for query optimization.
    """
    validate_inputs(latitude, longitude, radius_km)
    
    # ── Stage A: Bounding Box Pre-filter ──────────────────────────────────
    min_lat, max_lat, min_lon, max_lon = calculate_bounding_box(latitude, longitude, radius_km)
    
    candidates = (
        db.query(GSILandslideIncident)
        .filter(GSILandslideIncident.latitude.between(min_lat, max_lat))
        .filter(GSILandslideIncident.longitude.between(min_lon, max_lon))
        .all()
    )
    
    # ── Stage B: Exact Distance Filter ────────────────────────────────────
    results = []
    for c in candidates:
        if c.latitude is None or c.longitude is None:
            continue
        dist = haversine_distance(latitude, longitude, c.latitude, c.longitude)
        if dist <= radius_km:
            results.append({
                "source_id": c.source_id,
                "source_ref": c.source_ref,
                "latitude": c.latitude,
                "longitude": c.longitude,
                "distance_km": round(dist, 4),
                "state": c.state,
                "district": c.district,
                "slide_name": c.slide_name,
                "landslide_type": c.landslide_type,
                "material": c.material,
                "trigger": c.trigger,
                "activity": c.activity,
                "movement_rate": c.movement_rate,
                "geology": c.geology,
                "geoscientific_cause": c.geoscientific_cause
            })
            
    # Sort results by distance ascending
    results.sort(key=lambda x: x["distance_km"])
    return results

def find_nearby_nasa_events(db: Session, latitude: float, longitude: float, radius_km: float) -> list[dict]:
    """
    Finds and returns NASA historical landslide events within a given radius.
    Applies B-tree bounding box filtering first for query optimization.
    """
    validate_inputs(latitude, longitude, radius_km)
    
    # ── Stage A: Bounding Box Pre-filter ──────────────────────────────────
    min_lat, max_lat, min_lon, max_lon = calculate_bounding_box(latitude, longitude, radius_km)
    
    candidates = (
        db.query(NASALandslideEvent)
        .filter(NASALandslideEvent.latitude.between(min_lat, max_lat))
        .filter(NASALandslideEvent.longitude.between(min_lon, max_lon))
        .all()
    )
    
    # ── Stage B: Exact Distance Filter ────────────────────────────────────
    results = []
    for c in candidates:
        if c.latitude is None or c.longitude is None:
            continue
        dist = haversine_distance(latitude, longitude, c.latitude, c.longitude)
        if dist <= radius_km:
            results.append({
                "source_id": c.source_id,
                "source_ref": c.source_ref,
                "latitude": c.latitude,
                "longitude": c.longitude,
                "distance_km": round(dist, 4),
                "state": c.state,
                "location_description": c.location_description,
                "landslide_type": c.landslide_type,
                "trigger": c.trigger,
                "event_date": c.event_date.isoformat() if c.event_date else None,
                "fatalities": c.fatalities,
                "injuries": c.injuries,
                "location_accuracy": c.location_accuracy
            })
            
    # Sort results by distance ascending
    results.sort(key=lambda x: x["distance_km"])
    return results

def get_historical_landslide_context(db: Session, latitude: float, longitude: float, radius_km: float) -> dict:
    """
    Aggregates GSI and NASA landslide results into a structured factual historical context payload.
    Provides total observations, distributions, and nearest records.
    """
    gsi_results = find_nearby_gsi_incidents(db, latitude, longitude, radius_km)
    nasa_results = find_nearby_nasa_events(db, latitude, longitude, radius_km)
    
    # ── GSI Summary ───────────────────────────────────────────────────────
    total_gsi = len(gsi_results)
    nearest_gsi = gsi_results[0]["distance_km"] if total_gsi > 0 else None
    
    gsi_types = Counter(r["landslide_type"] for r in gsi_results if r["landslide_type"])
    gsi_triggers = Counter(r["trigger"] for r in gsi_results if r["trigger"])
    
    # ── NASA Summary ──────────────────────────────────────────────────────
    total_nasa = len(nasa_results)
    nearest_nasa = nasa_results[0]["distance_km"] if total_nasa > 0 else None
    
    nasa_triggers = Counter(r["trigger"] for r in nasa_results if r["trigger"])
    total_fatalities = sum(r["fatalities"] for r in nasa_results if r["fatalities"] is not None)
    total_injuries = sum(r["injuries"] for r in nasa_results if r["injuries"] is not None)
    
    nasa_dates = [r["event_date"] for r in nasa_results if r["event_date"]]
    earliest_date = min(nasa_dates) if nasa_dates else None
    latest_date = max(nasa_dates) if nasa_dates else None
    
    # ── Combined Summary ──────────────────────────────────────────────────
    total_obs = total_gsi + total_nasa
    distances = []
    if nearest_gsi is not None:
        distances.append(nearest_gsi)
    if nearest_nasa is not None:
        distances.append(nearest_nasa)
    nearest_obs = min(distances) if distances else None
    
    return {
        "query_latitude": latitude,
        "query_longitude": longitude,
        "radius_km": radius_km,
        "gsi_summary": {
            "total_nearby_incidents": total_gsi,
            "nearest_incident_distance_km": nearest_gsi,
            "landslide_type_distribution": dict(gsi_types),
            "trigger_distribution": dict(gsi_triggers)
        },
        "nasa_summary": {
            "total_nearby_events": total_nasa,
            "nearest_event_distance_km": nearest_nasa,
            "trigger_distribution": dict(nasa_triggers),
            "total_recorded_fatalities": total_fatalities,
            "total_recorded_injuries": total_injuries,
            "earliest_event_date": earliest_date,
            "latest_event_date": latest_date
        },
        "combined_summary": {
            "total_historical_observations": total_obs,
            "nearest_historical_observation_km": nearest_obs
        },
        "gsi_incidents": gsi_results[:MAX_MAP_RECORDS_PER_SOURCE],
        "nasa_events": nasa_results[:MAX_MAP_RECORDS_PER_SOURCE]
    }
