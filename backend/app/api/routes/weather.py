from fastapi import APIRouter, Query, HTTPException, status
from pydantic import BaseModel, Field
from typing import Optional, List
from app.services.weather_service import fetch_weather_telemetry, analyze_rainfall

router = APIRouter()

class RainfallAnalysisResponse(BaseModel):
    """Schema for Rainfall Intelligence response (Phase 3.2)."""
    latitude: float
    longitude: float
    current_rainfall_mm: float
    rainfall_last_24h_mm: float
    rainfall_last_3_days_mm: float
    rainfall_last_7_days_mm: float
    rainfall_intensity: str
    rainfall_risk_level: str

@router.get("/rainfall-analysis", response_model=RainfallAnalysisResponse)
def get_rainfall_analysis(
    latitude: float = Query(..., ge=-90.0, le=90.0, description="Latitude coordinate between -90 and 90"),
    longitude: float = Query(..., ge=-180.0, le=180.0, description="Longitude coordinate between -180 and 180")
):
    """
    Analyzes live rainfall conditions and antecedent multi-day precipitation for a target location.
    
    Returns:
    - current_rainfall_mm: Instantaneous/current precipitation
    - rainfall_last_24h_mm: Trailing 24-hour precipitation sum
    - rainfall_last_3_days_mm: 3-day antecedent precipitation sum
    - rainfall_last_7_days_mm: 7-day antecedent precipitation sum
    - rainfall_intensity: Instantaneous intensity classification (NONE, LIGHT, MODERATE, HEAVY, EXTREME)
    - rainfall_risk_level: Cumulative landslide risk classification (LOW, MODERATE, HIGH, VERY_HIGH)
    """
    try:
        result = analyze_rainfall(latitude=latitude, longitude=longitude)
        return RainfallAnalysisResponse(**result)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Rainfall analysis failed: {str(e)}"
        )


class DailyPrecipitationRecord(BaseModel):
    """Schema for individual daily precipitation record."""
    date: str
    precipitation_mm: float

class WeatherTelemetryResponse(BaseModel):
    """Schema for weather telemetry response, including antecedent rainfall metrics."""
    status: str
    latitude: float
    longitude: float
    temperature: Optional[float] = None
    temperature_unit: str = "°C"
    relative_humidity: Optional[float] = None
    relative_humidity_unit: str = "%"
    current_precipitation: Optional[float] = None
    current_precipitation_unit: str = "mm"
    daily_precipitation: Optional[float] = None
    daily_precipitation_unit: str = "mm"
    three_day_cumulative: float = 0.0
    seven_day_cumulative: float = 0.0
    saturation_classification: str = "Dry"
    daily_precipitation_history: List[DailyPrecipitationRecord] = []
    timestamp: str
    timezone: Optional[str] = None
    elevation: Optional[float] = None

@router.get("/telemetry", response_model=WeatherTelemetryResponse)
def get_weather_telemetry(
    latitude: float = Query(..., ge=-90.0, le=90.0, description="Latitude coordinate"),
    longitude: float = Query(..., ge=-180.0, le=180.0, description="Longitude coordinate")
):
    """
    Retrieves live meteorological telemetry data (temperature, humidity, precipitation)
    from Open-Meteo for the specified location coordinates. Includes past 7 days of daily
    precipitation sums to compute antecedent saturation metrics.
    """
    try:
        data = fetch_weather_telemetry(latitude, longitude)
        return WeatherTelemetryResponse(**data)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Weather service failure: {str(e)}"
        )
