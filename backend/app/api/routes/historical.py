from typing import Optional
from fastapi import APIRouter, Query, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.schemas.historical import (
    HistoricalContextResponse,
    SusceptibilityResponse,
    HistoricalRiskContextResponse
)
from app.services.spatial_query_service import get_historical_landslide_context
from app.services.susceptibility_service import calculate_susceptibility_score
from app.services.historical_risk_service import analyze_historical_context

router = APIRouter()

@router.get("/nearby", response_model=HistoricalContextResponse)
def get_nearby_landslides(
    lat: float = Query(..., ge=-90.0, le=90.0, description="Latitude coordinate of query center (-90.0 to 90.0)"),
    lon: float = Query(..., ge=-180.0, le=180.0, description="Longitude coordinate of query center (-180.0 to 180.0)"),
    radius: float = Query(10.0, gt=0.0, le=100.0, description="Search radius in kilometers (0.0 to 100.0)"),
    db: Session = Depends(get_db)
):
    """
    Exposes historical spatial landslide intelligence around a geographic location.
    Queries both GSI and NASA databases, calculates exact distances, and generates
    factual summary counts, distributions, and earliest/latest dates.
    """
    try:
        context = get_historical_landslide_context(db, lat, lon, radius)
        return context
    except ValueError as e:
        # Client validation error from the service layer
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        # Server-side execution exception
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred during database spatial lookup: {str(e)}"
        )

@router.get("/susceptibility", response_model=SusceptibilityResponse)
def get_susceptibility(
    lat: float = Query(..., ge=-90.0, le=90.0, description="Latitude coordinate of query center (-90.0 to 90.0)"),
    lon: float = Query(..., ge=-180.0, le=180.0, description="Longitude coordinate of query center (-180.0 to 180.0)"),
    radius: float = Query(10.0, gt=0.0, le=100.0, description="Search radius in kilometers (0.0 to 100.0)"),
    slope: Optional[float] = Query(None, ge=0.0, le=90.0, description="Mean slope in degrees (0.0 to 90.0)"),
    rainfall: Optional[float] = Query(None, ge=0.0, description="24h accumulated precipitation in millimeters (>= 0.0)"),
    rainfall_3d: Optional[float] = Query(None, ge=0.0, description="3-day cumulative precipitation in millimeters (>= 0.0)"),
    rainfall_7d: Optional[float] = Query(None, ge=0.0, description="7-day cumulative precipitation in millimeters (>= 0.0)"),
    db: Session = Depends(get_db)
):
    """
    Exposes heuristic hazard susceptibility scoring around a target coordinate.
    Combines historical evidence, slope predisposition, and rainfall triggers.
    Supports partial normalization when slope or rainfall is omitted.
    """
    try:
        result = calculate_susceptibility_score(
            db=db,
            latitude=lat,
            longitude=lon,
            radius_km=radius,
            slope=slope,
            rainfall=rainfall,
            rainfall_3d=rainfall_3d,
            rainfall_7d=rainfall_7d
        )
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred during susceptibility calculation: {str(e)}"
        )

@router.get("/risk-context", response_model=HistoricalRiskContextResponse)
def get_historical_risk_context(
    latitude: float = Query(..., ge=-90.0, le=90.0, description="Latitude coordinate between -90 and 90"),
    longitude: float = Query(..., ge=-180.0, le=180.0, description="Longitude coordinate between -180 and 180"),
    radius_km: float = Query(10.0, ge=1.0, le=100.0, description="Search radius in kilometers (1.0 to 100.0)"),
    db: Session = Depends(get_db)
):
    """
    Historical Landslide Context Engine (Phase 3.5).
    Analyzes geographic historical landslide context, incident density, proximity,
    and recency to determine historical susceptibility scores (0-100).
    """
    try:
        result = analyze_historical_context(
            db=db,
            latitude=latitude,
            longitude=longitude,
            radius_km=radius_km
        )
        return HistoricalRiskContextResponse(**result)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred during historical risk context calculation: {str(e)}"
        )

