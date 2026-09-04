"""
Infrastructure API Routes - Phase 8 Checkpoints 17.1 & 17.3

Exposes endpoints for road network infrastructure discovery, GeoJSON LineString representations,
evidence-based connectivity impact assessments, and operational road disruption summaries.
"""

import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status as http_status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.services.aoi_service import is_inside_ner
from app.services.road_connectivity_service import RoadConnectivityService
from app.services.road_disruption_service import RoadDisruptionService
from app.schemas.infrastructure import (
    NearbyRoadsResponse,
    RoadDisruptionSummaryResponse
)

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/roads/nearby", response_model=NearbyRoadsResponse)
def get_nearby_roads(
    latitude: float = Query(..., ge=-90.0, le=90.0, description="Center latitude (-90 to 90)"),
    longitude: float = Query(..., ge=-180.0, le=180.0, description="Center longitude (-180 to 180)"),
    radius_km: float = Query(5.0, ge=0.5, le=25.0, description="Search radius in kilometers (0.5 to 25.0 km)"),
    db: Session = Depends(get_db)
):
    """
    Retrieves nearby road infrastructure and determines operational connectivity status
    based on verified and active Field Intelligence ground observations.
    """
    if not is_inside_ner(latitude, longitude):
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="Target coordinates must lie within India's North Eastern Region."
        )

    return RoadConnectivityService.analyze_nearby_roads(
        db=db,
        latitude=latitude,
        longitude=longitude,
        radius_km=radius_km
    )

@router.get("/roads/disruption-summary", response_model=RoadDisruptionSummaryResponse)
def get_road_disruption_summary(
    latitude: float = Query(..., ge=-90.0, le=90.0, description="Center latitude (-90 to 90)"),
    longitude: float = Query(..., ge=-180.0, le=180.0, description="Center longitude (-180 to 180)"),
    radius_km: float = Query(5.0, ge=0.5, le=25.0, description="Search radius in kilometers (0.5 to 25.0 km)"),
    db: Session = Depends(get_db)
):
    """
    Synthesizes an area-level operational road disruption intelligence summary,
    including prioritized road impact rankings, hazard breakdowns, and actionable operational guidance.
    """
    if not is_inside_ner(latitude, longitude):
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="Target coordinates must lie within India's North Eastern Region."
        )

    return RoadDisruptionService.generate_disruption_summary(
        db=db,
        latitude=latitude,
        longitude=longitude,
        radius_km=radius_km
    )

@router.get("/emergency-facilities")
def get_emergency_facilities(
    latitude: float = Query(..., ge=-90.0, le=90.0, description="Center latitude (-90 to 90)"),
    longitude: float = Query(..., ge=-180.0, le=180.0, description="Center longitude (-180 to 180)"),
    radius_km: float = Query(150.0, ge=1.0, le=500.0, description="Search radius in kilometers")
):
    """
    Dynamically computes real geodesic (Haversine) distances from map coordinates (lat, lng)
    to verified hospitals, trauma centres, public shelters, police outposts, and BRO units.
    Ensures zero hardcoded distance information for citizen advisories.
    """
    from app.services.emergency_facilities_service import EmergencyFacilitiesService
    return EmergencyFacilitiesService.get_nearest_facilities(
        latitude=latitude,
        longitude=longitude,
        radius_km=radius_km
    )
