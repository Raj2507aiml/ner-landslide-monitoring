"""
Travel Route Landslide Early Warning API Routes - SIH 2026

Exposes endpoints for querying high-risk travel corridors,
evaluating live highway hazards, and route-based proximity warnings.
"""

import logging
import math
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.operational_incident import OperationalIncident
from app.schemas.travel import (
    TravelRiskZone,
    TravelRiskZonesResponse,
    TravelRouteRiskQuery
)
from app.services.spatial_query_service import haversine_distance

logger = logging.getLogger(__name__)
router = APIRouter()

# Curated High-Risk Highway Corridors across the 8 NER States
CURATED_TRAVEL_CORRIDORS = [
    {
        "id": "corridor-nh06-sonapur",
        "name": "Sonapur Tunnel Corridor",
        "highway": "NH-06",
        "state": "Meghalaya",
        "latitude": 25.1012,
        "longitude": 92.3654,
        "base_risk": 84.0,
        "severity": "CRITICAL",
        "advisory": "Frequent active mudflows and debris fall at Sonapur tunnel portal. Exercise extreme caution during rain."
    },
    {
        "id": "corridor-nh13-sela",
        "name": "Sela Pass / Tawang Highway",
        "highway": "NH-13",
        "state": "Arunachal Pradesh",
        "latitude": 27.5034,
        "longitude": 92.1037,
        "base_risk": 88.0,
        "severity": "CRITICAL",
        "advisory": "Steep rocky slopes prone to rockfall and freeze-thaw slippage near high-altitude passes."
    },
    {
        "id": "corridor-nh10-gangtok",
        "name": "Gangtok - Siliguri Corridor",
        "highway": "NH-10",
        "state": "Sikkim",
        "latitude": 27.3389,
        "longitude": 88.6065,
        "base_risk": 82.0,
        "severity": "CRITICAL",
        "advisory": "Teesta River gorge section susceptible to severe washouts and hillside subsidence."
    },
    {
        "id": "corridor-nh37-tupul",
        "name": "Tupul / Imphal West Corridor",
        "highway": "NH-37",
        "state": "Manipur",
        "latitude": 24.7865,
        "longitude": 93.6322,
        "base_risk": 86.0,
        "severity": "CRITICAL",
        "advisory": "Major historical railway/highway slide zone. Saturated slope conditions require alternate route planning."
    },
    {
        "id": "corridor-nh29-dzukou",
        "name": "Dzükou Valley / Kohima Ridge",
        "highway": "NH-29",
        "state": "Nagaland",
        "latitude": 25.6751,
        "longitude": 94.1086,
        "base_risk": 76.0,
        "severity": "HIGH",
        "advisory": "High cut-slope vulnerability along Kohima-Dimapur highway segment."
    },
    {
        "id": "corridor-nh54a-haflong",
        "name": "Dima Hasao (Haflong) Corridor",
        "highway": "NH-54A",
        "state": "Assam",
        "latitude": 25.1667,
        "longitude": 93.0167,
        "base_risk": 74.0,
        "severity": "HIGH",
        "advisory": "Barail range hill pass prone to recurrent monsoon mudslides and embankment erosion."
    },
    {
        "id": "corridor-nh54-aizawl",
        "name": "Aizawl Slope Corridor",
        "highway": "NH-54",
        "state": "Mizoram",
        "latitude": 23.7271,
        "longitude": 92.7176,
        "base_risk": 72.0,
        "severity": "HIGH",
        "advisory": "Steep shale formations subject to localized structural instability under continuous precipitation."
    },
    {
        "id": "corridor-nh10-kalimpong",
        "name": "Kalimpong / 29th Mile Teesta",
        "highway": "NH-10",
        "state": "Sikkim / West Bengal Border",
        "latitude": 27.0667,
        "longitude": 88.4667,
        "base_risk": 79.0,
        "severity": "HIGH",
        "advisory": "Persistent slope failure zone at 29th Mile. River undercutting active."
    },
    {
        "id": "corridor-nh206-cherra",
        "name": "Cherrapunji (Sohra Rim) Pass",
        "highway": "NH-206",
        "state": "Meghalaya",
        "latitude": 25.2986,
        "longitude": 91.7086,
        "base_risk": 68.0,
        "severity": "MODERATE",
        "advisory": "Extreme seasonal rainfall leading to swift runoff and shoulder erosion."
    },
    {
        "id": "corridor-lumding-badarpur",
        "name": "Lumding - Badarpur Hill Pass",
        "highway": "NH-27 / NH-06 Link",
        "state": "Assam",
        "latitude": 25.0400,
        "longitude": 92.9800,
        "base_risk": 75.0,
        "severity": "HIGH",
        "advisory": "Active geological fault zone with history of major rail and road blockades."
    }
]


def perpendicular_distance_km(p_lat: float, p_lng: float, l1_lat: float, l1_lng: float, l2_lat: float, l2_lng: float) -> float:
    """
    Computes approximate cross-track distance (km) of point P to great-circle path L1-L2.
    """
    d13 = haversine_distance(l1_lat, l1_lng, p_lat, p_lng)
    d12 = haversine_distance(l1_lat, l1_lng, l2_lat, l2_lng)
    if d12 <= 0.001:
        return d13

    # Bearing from L1 to L2 and L1 to P
    y12 = math.sin(math.radians(l2_lng - l1_lng)) * math.cos(math.radians(l2_lat))
    x12 = math.cos(math.radians(l1_lat)) * math.sin(math.radians(l2_lat)) - math.sin(math.radians(l1_lat)) * math.cos(math.radians(l2_lat)) * math.cos(math.radians(l2_lng - l1_lng))
    b12 = math.atan2(y12, x12)

    y13 = math.sin(math.radians(p_lng - l1_lng)) * math.cos(math.radians(p_lat))
    x13 = math.cos(math.radians(l1_lat)) * math.sin(math.radians(p_lat)) - math.sin(math.radians(l1_lat)) * math.cos(math.radians(p_lat)) * math.cos(math.radians(p_lng - l1_lng))
    b13 = math.atan2(y13, x13)

    cross_track = math.asin(math.sin(d13 / 6371.0) * math.sin(b13 - b12)) * 6371.0
    return abs(cross_track)


@router.get("/risk-zones", response_model=TravelRiskZonesResponse)
def get_travel_risk_zones(
    min_risk: float = Query(0.0, ge=0.0, le=100.0, description="Minimum risk score filter (default: 0.0)"),
    db: Session = Depends(get_db)
):
    """
    Returns monitored high-risk landslide hazard zones and travel corridors across NER.
    Combines live operational incidents from the database with curated highway corridors.
    """
    now_iso = datetime.utcnow().isoformat() + "Z"
    zones: List[TravelRiskZone] = []

    # 1. Fetch active operational incidents from the database
    try:
        active_incidents = db.query(OperationalIncident).filter(
            OperationalIncident.status.in_(["OPEN", "ACKNOWLEDGED", "IN_PROGRESS"])
        ).all()

        for inc in active_incidents:
            # Map severity or composite risk to probability
            risk_score = inc.composite_risk_index
            if risk_score is None or risk_score <= 0:
                severity_map = {
                    "CRITICAL": 92.0,
                    "HIGH": 78.0,
                    "MODERATE": 55.0,
                    "LOW": 30.0
                }
                risk_score = severity_map.get(inc.severity.upper(), 70.0)

            zones.append(
                TravelRiskZone(
                    id=f"incident-{inc.id}",
                    name=inc.title or f"Active Incident #{inc.incident_code}",
                    highway=None,
                    state=None,
                    latitude=inc.latitude,
                    longitude=inc.longitude,
                    risk_probability=round(float(risk_score), 1),
                    severity=inc.severity.upper() if inc.severity else "HIGH",
                    source=f"OperationalIncident ({inc.incident_code})",
                    advisory=inc.description or "Active landslide hazard recorded by response authorities.",
                    timestamp=inc.created_at.isoformat() + "Z" if inc.created_at else now_iso
                )
            )
    except Exception as e:
        logger.warning(f"[Travel Route] Unable to read DB incidents: {e}")

    # 2. Add curated highway corridors across NER
    for c in CURATED_TRAVEL_CORRIDORS:
        zones.append(
            TravelRiskZone(
                id=c["id"],
                name=f"{c['name']} ({c['highway']})",
                highway=c["highway"],
                state=c["state"],
                latitude=c["latitude"],
                longitude=c["longitude"],
                risk_probability=c["base_risk"],
                severity=c["severity"],
                source="CompositeRiskEngine (Monitored Corridor)",
                advisory=c["advisory"],
                timestamp=now_iso
            )
        )

    # 3. Apply min_risk filter if requested
    if min_risk > 0.0:
        zones = [z for z in zones if z.risk_probability >= min_risk]

    return TravelRiskZonesResponse(
        status="success",
        total=len(zones),
        high_risk_threshold=70.0,
        warning_distance_km=10.0,
        zones=zones
    )


@router.post("/route-eval")
def evaluate_route_hazards(
    query: TravelRouteRiskQuery,
    db: Session = Depends(get_db)
):
    """
    Evaluates hazard corridors intersecting or within buffer_km of a planned travel route.
    """
    all_zones_resp = get_travel_risk_zones(min_risk=0.0, db=db)
    zones_along_route = []

    for zone in all_zones_resp.zones:
        # Distance from origin
        dist_from_origin = haversine_distance(query.origin_lat, query.origin_lng, zone.latitude, zone.longitude)
        # Perpendicular distance to route line
        cross_track = perpendicular_distance_km(
            zone.latitude, zone.longitude,
            query.origin_lat, query.origin_lng,
            query.destination_lat, query.destination_lng
        )

        if cross_track <= query.buffer_km:
            zones_along_route.append({
                **zone.dict(),
                "distance_from_origin_km": round(dist_from_origin, 1),
                "corridor_offset_km": round(cross_track, 1)
            })

    # Sort in order of encounter along route
    zones_along_route.sort(key=lambda x: x["distance_from_origin_km"])

    return {
        "status": "success",
        "total_hazards": len(zones_along_route),
        "buffer_km": query.buffer_km,
        "hazards": zones_along_route
    }
