from fastapi import APIRouter, Query, HTTPException, status
from pydantic import BaseModel, Field
from typing import Optional
from app.services.soil_service import analyze_soil_moisture

router = APIRouter()

class SoilAnalysisResponse(BaseModel):
    """Schema for Soil Moisture Intelligence response (Phase 3.3)."""
    latitude: float
    longitude: float
    soil_moisture: float
    soil_moisture_percent: float
    soil_condition: str
    soil_saturation_risk: str
    data_source: str = "OPEN_METEO"
    surface_soil_moisture: Optional[float] = None
    root_zone_soil_moisture: Optional[float] = None

@router.get("/analyze", response_model=SoilAnalysisResponse)
def get_soil_analysis(
    latitude: float = Query(..., ge=-90.0, le=90.0, description="Latitude coordinate between -90 and 90"),
    longitude: float = Query(..., ge=-180.0, le=180.0, description="Longitude coordinate between -180 and 180"),
    source: str = Query("satellite", description="Data source provider ('satellite' or future IoT sensor)")
):
    """
    Analyzes live soil moisture conditions across multiple ground depth layers for a target coordinate.
    
    Returns:
    - soil_moisture: Volumetric soil water content fraction (0.0 to 1.0)
    - soil_moisture_percent: Soil water percentage (0.0 to 100.0%)
    - soil_condition: Physical condition (DRY, SLIGHTLY_MOIST, MOIST, WET, SATURATED)
    - soil_saturation_risk: Landslide saturation hazard level (LOW, MODERATE, HIGH, VERY_HIGH)
    - data_source: Data source attribution (e.g. OPEN_METEO)
    - surface_soil_moisture: Top-layer (0-1cm) moisture fraction
    - root_zone_soil_moisture: Deep root-zone (3-27cm) moisture fraction
    """
    try:
        result = analyze_soil_moisture(latitude=latitude, longitude=longitude, source=source)
        return SoilAnalysisResponse(**result)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Soil moisture analysis failed: {str(e)}"
        )
