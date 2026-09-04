"""
Composite Risk Routing Interface - Phase 4 Checkpoint 12.3

Mounts the POST /api/v1/risk/composite endpoint, exposing unified landslide risk index
assessments by calling the CompositeRiskService.
"""

from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.services.composite_risk_service import CompositeRiskService

router = APIRouter()

class CompositeRiskRequest(BaseModel):
    latitude: float = Field(..., ge=-90.0, le=90.0, description="Latitude of query coordinate (-90 to 90)")
    longitude: float = Field(..., ge=-180.0, le=180.0, description="Longitude of query coordinate (-180 to 180)")

class StaticSusceptibilityDetails(BaseModel):
    probability: float = Field(..., description="Raw static terrain susceptibility probability from ML model")
    index: float = Field(..., description="Static susceptibility index (probability * 100)")

class HistoricalContextDetails(BaseModel):
    proximity_score: float = Field(..., description="Score based on distance to nearest historical landslide (0-25)")
    density_score: float = Field(..., description="Score based on density of local historical landslides (0-15)")
    historical_score: float = Field(..., description="Total combined historical context score (0-40)")
    multiplier: float = Field(..., description="Vulnerability multiplier scaling factor (1.0 to 1.5)")

class RainfallTriggerDetails(BaseModel):
    daily_score: float = Field(..., description="Score for 24h daily precipitation sum (0-10)")
    three_day_score: float = Field(..., description="Score for 3-day cumulative precipitation (0-10)")
    seven_day_score: float = Field(..., description="Score for 7-day cumulative precipitation (0-10)")
    rainfall_score: float = Field(..., description="Total combined trigger rainfall score (0-30)")
    multiplier: float = Field(..., description="Dynamic trigger multiplier scaling factor (0.5 to 2.0)")

class ComponentDetails(BaseModel):
    static_susceptibility: StaticSusceptibilityDetails
    historical_context: HistoricalContextDetails
    rainfall_trigger: RainfallTriggerDetails

class TerrainDetails(BaseModel):
    elevation: float = Field(..., description="Extracted point elevation in meters")
    slope: float = Field(..., description="Calculated point slope in degrees")
    aspect: float = Field(..., description="Calculated point aspect in degrees (-1.0 for flat)")

class FieldIntelligenceContextDetails(BaseModel):
    status: str = Field(..., description="Ground observation categorical status")
    verified_ground_signal_score: float = Field(..., description="Normalized verified ground signal score (0 to 100)")
    verified_reports_nearby: int = Field(..., description="Count of verified reports in proximity")
    unverified_reports_nearby: int = Field(..., description="Count of unverified observations in proximity")
    potential_cluster_detected: bool = Field(..., description="Flag indicating if localized spatial clustering is present")
    dominant_observation_types: List[str] = Field(default_factory=list, description="Dominant hazard types observed")
    operational_message: Optional[str] = Field(None, description="Operational summary message")

class CompositeRiskResponse(BaseModel):
    status: str = Field("success", description="Status code indicator")
    latitude: float
    longitude: float
    composite_risk_index: float = Field(..., description="Overall Composite Risk Index (0-100)")
    risk_level: str = Field(..., description="Risk category classification (Low, Moderate, High, Very High)")
    components: ComponentDetails
    terrain: TerrainDetails
    explanation: str = Field(..., description="Dynamic scientific explanation of risk factors")
    formula_version: str = Field(..., description="Version of the composite formula used")
    field_intelligence_context: Optional[FieldIntelligenceContextDetails] = Field(None, description="Contextual field intelligence observation layer")

@router.post("/composite", response_model=CompositeRiskResponse)
def get_composite_risk(payload: CompositeRiskRequest, db: Session = Depends(get_db)):
    """
    Computes the Composite Landslide Risk Index (0-100) at the query coordinate.
    Combines static terrain ML prediction, local historical incident records,
    and dynamic multi-timescale antecedent precipitation.
    """
    try:
        result = CompositeRiskService.calculate_composite_risk(
            db=db,
            latitude=payload.latitude,
            longitude=payload.longitude
        )
        return {
            "status": "success",
            **result
        }
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(val_err)
        )
    except RuntimeError as run_err:
        # Catch DEM extraction or ML model binary reading failures
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(run_err)
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred during composite risk calculation: {str(exc)}"
        )


# ---------------------------------------------------------------------------
# Unified Environmental Risk Engine Endpoint (Phase 3.4)
# ---------------------------------------------------------------------------
class EnvironmentalTerrainDetails(BaseModel):
    score: float = Field(..., description="Calculated terrain score (0-100)")
    risk_level: str = Field(..., description="Terrain risk classification")
    slope_degrees: Optional[float] = Field(None, description="Physical terrain slope in degrees")
    elevation_meters: Optional[float] = Field(None, description="Local elevation in meters")

class EnvironmentalRainfallDetails(BaseModel):
    score: float = Field(..., description="Calculated rainfall score (0-100)")
    risk_level: str = Field(..., description="Rainfall risk classification")
    rainfall_24h_mm: Optional[float] = Field(None, description="Trailing 24h precipitation in mm")
    rainfall_3d_mm: Optional[float] = Field(None, description="3-day antecedent precipitation in mm")
    rainfall_7d_mm: Optional[float] = Field(None, description="7-day antecedent precipitation in mm")

class EnvironmentalSoilDetails(BaseModel):
    score: float = Field(..., description="Calculated soil moisture score (0-100)")
    risk_level: str = Field(..., description="Soil saturation risk classification")
    soil_moisture_percent: Optional[float] = Field(None, description="Volumetric soil moisture percentage")

class EnvironmentalFactorContributions(BaseModel):
    terrain: float = Field(..., description="Effective terrain contribution to environmental score")
    rainfall: float = Field(..., description="Effective rainfall contribution to environmental score")
    soil: float = Field(..., description="Effective soil moisture contribution to environmental score")

class EnvironmentalDataAvailability(BaseModel):
    terrain: str = Field(..., description="Terrain data availability status (AVAILABLE/UNAVAILABLE)")
    rainfall: str = Field(..., description="Rainfall data availability status (AVAILABLE/UNAVAILABLE)")
    soil: str = Field(..., description="Soil data availability status (AVAILABLE/UNAVAILABLE)")

class EnvironmentalRiskResponse(BaseModel):
    latitude: float
    longitude: float
    environmental_risk_score: float = Field(..., description="Weighted unified environmental risk score (0-100)")
    environmental_risk_level: str = Field(..., description="Overall environmental hazard category (LOW, MODERATE, HIGH, VERY_HIGH)")
    terrain: EnvironmentalTerrainDetails
    rainfall: EnvironmentalRainfallDetails
    soil: EnvironmentalSoilDetails
    factor_contributions: EnvironmentalFactorContributions
    primary_contributing_factor: str = Field(..., description="Dominant environmental factor (STEEP_TERRAIN, HEAVY_RAINFALL, SOIL_SATURATION)")
    risk_factors: List[str] = Field(..., description="Contextual natural-language risk explanation statements")
    confidence: str = Field(..., description="Assessment data confidence indicator (HIGH, MEDIUM, LOW)")
    data_availability: EnvironmentalDataAvailability


@router.get("/environmental-analysis", response_model=EnvironmentalRiskResponse)
def get_environmental_analysis(
    latitude: float = Query(..., ge=-90.0, le=90.0, description="Latitude of query coordinate (-90 to 90)"),
    longitude: float = Query(..., ge=-180.0, le=180.0, description="Longitude of query coordinate (-180 to 180)")
):
    """
    Unified Environmental Risk Engine (Phase 3.4).
    Combines Terrain slope, antecedent Rainfall accumulation, and Soil Moisture saturation
    into an explainable, weighted environmental landslide risk score (0-100).
    """
    try:
        from app.services.environmental_risk_service import calculate_environmental_risk
        result = calculate_environmental_risk(latitude=latitude, longitude=longitude)
        return EnvironmentalRiskResponse(**result)
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(val_err)
        )
    except RuntimeError as run_err:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(run_err)
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Environmental risk analysis failed: {str(exc)}"
        )


# ---------------------------------------------------------------------------
# Unified Landslide Risk Fusion Engine Endpoint (Phase 6)
# ---------------------------------------------------------------------------
class UnifiedEnvironmentalDetails(BaseModel):
    available: bool = Field(..., description="Availability status of environmental risk data")
    score: Optional[float] = Field(None, description="Calculated environmental risk score (0-100)")
    risk_level: str = Field(..., description="Environmental risk category")
    contribution: float = Field(..., description="Weighted contribution to unified risk score")

class UnifiedHistoricalDetails(BaseModel):
    available: bool = Field(..., description="Availability status of historical risk data")
    score: Optional[float] = Field(None, description="Calculated historical susceptibility score (0-100)")
    risk_level: str = Field(..., description="Historical risk category")
    contribution: float = Field(..., description="Weighted contribution to unified risk score")
    nearby_incident_count: Optional[int] = Field(None, description="Number of historical incidents recorded within search radius")

class UnifiedDataAvailability(BaseModel):
    environmental: str = Field(..., description="Environmental data status (AVAILABLE/UNAVAILABLE)")
    historical: str = Field(..., description="Historical data status (AVAILABLE/UNAVAILABLE)")

class UnifiedLandslideRiskResponse(BaseModel):
    latitude: float
    longitude: float
    search_radius_km: float
    unified_landslide_risk_score: float = Field(..., description="Unified Landslide Risk Score (0-100)")
    unified_landslide_risk_level: str = Field(..., description="Overall unified risk category (LOW, MODERATE, HIGH, VERY_HIGH)")
    environmental: UnifiedEnvironmentalDetails
    historical: UnifiedHistoricalDetails
    primary_risk_driver: str = Field(..., description="Dominant risk source (ENVIRONMENTAL_CONDITIONS, HISTORICAL_SUSCEPTIBILITY, BALANCED)")
    situation_status: str = Field(..., description="Operational threat status (STABLE, ELEVATED, ESCALATING, CRITICAL)")
    risk_factors: List[str] = Field(..., description="Dynamic explainability statements")
    confidence: str = Field(..., description="Data confidence indicator (HIGH, MEDIUM, LOW)")
    data_availability: UnifiedDataAvailability


@router.get("/unified-analysis", response_model=UnifiedLandslideRiskResponse)
def get_unified_landslide_risk_analysis(
    latitude: float = Query(..., ge=-90.0, le=90.0, description="Latitude of query coordinate (-90 to 90)"),
    longitude: float = Query(..., ge=-180.0, le=180.0, description="Longitude of query coordinate (-180 to 180)"),
    radius_km: float = Query(10.0, ge=1.0, le=100.0, description="Historical search radius in kilometers (1.0 to 100.0)"),
    db: Session = Depends(get_db)
):
    """
    Unified Landslide Risk Fusion Engine (Phase 6).
    Combines live Environmental Risk (Terrain, Rainfall, Soil Moisture) and
    Historical Landslide Susceptibility into a single, explainable Unified Landslide Risk Score (0-100).
    """
    try:
        from app.services.landslide_risk_fusion_service import calculate_unified_landslide_risk
        result = calculate_unified_landslide_risk(
            latitude=latitude,
            longitude=longitude,
            radius_km=radius_km,
            db=db
        )
        return UnifiedLandslideRiskResponse(**result)
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(val_err)
        )
    except RuntimeError as run_err:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(run_err)
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unified risk calculation failed: {str(exc)}"
        )


# ---------------------------------------------------------------------------
# Multi-Source Landslide Risk Fusion Schemas & Endpoint (Phase 8)
# ---------------------------------------------------------------------------
class MultiSourceEnvironmentalDetails(BaseModel):
    available: bool = Field(..., description="Availability flag for environmental risk telemetry")
    score: Optional[float] = Field(None, description="Calculated environmental hazard score (0-100)")
    risk_level: Optional[str] = Field(None, description="Environmental risk category")
    active_weight: float = Field(..., description="Proportional active weight after dynamic normalization")
    contribution: float = Field(..., description="Weighted numerical contribution to final fused score")

class MultiSourceHistoricalDetails(BaseModel):
    available: bool = Field(..., description="Availability flag for historical landslide context")
    score: Optional[float] = Field(None, description="Calculated historical susceptibility score (0-100)")
    risk_level: Optional[str] = Field(None, description="Historical risk category")
    active_weight: float = Field(..., description="Proportional active weight after dynamic normalization")
    contribution: float = Field(..., description="Weighted numerical contribution to final fused score")
    nearby_incident_count: Optional[int] = Field(None, description="Total historical landslide observations in search radius")

class MultiSourceSatelliteDetails(BaseModel):
    available: bool = Field(..., description="Availability flag for Sentinel-1 SAR change intelligence")
    score: Optional[float] = Field(None, description="Standardized satellite surface change score (0-100)")
    risk_level: Optional[str] = Field(None, description="Satellite surface change category")
    active_weight: float = Field(..., description="Proportional active weight after dynamic normalization")
    contribution: float = Field(..., description="Weighted numerical contribution to final fused score")
    confidence: Optional[str] = Field(None, description="Satellite pair and processing confidence indicator")

class MultiSourceDataAvailability(BaseModel):
    environmental: str = Field(..., description="Environmental data availability status (AVAILABLE/UNAVAILABLE)")
    historical: str = Field(..., description="Historical data availability status (AVAILABLE/UNAVAILABLE)")
    satellite: str = Field(..., description="Satellite data availability status (AVAILABLE/UNAVAILABLE)")

class MultiSourceLandslideRiskResponse(BaseModel):
    latitude: float
    longitude: float
    multisource_landslide_risk_score: float = Field(..., description="Fused multi-source landslide risk assessment score (0-100)")
    multisource_landslide_risk_level: str = Field(..., description="Operational multi-source risk category (LOW, MODERATE, HIGH, VERY_HIGH)")
    operational_status: str = Field(..., description="Actionable situational status (STABLE, WATCH, ELEVATED, ESCALATING, CRITICAL)")
    risk_convergence: str = Field(..., description="Multi-source convergence classification (NONE, PARTIAL, STRONG, SEVERE)")
    environmental: MultiSourceEnvironmentalDetails
    historical: MultiSourceHistoricalDetails
    satellite: MultiSourceSatelliteDetails
    primary_risk_driver: str = Field(..., description="Dominant risk source (ENVIRONMENTAL_CONDITIONS, HISTORICAL_SUSCEPTIBILITY, SATELLITE_SURFACE_CHANGE, BALANCED)")
    risk_factors: List[str] = Field(..., description="Dynamic, explainable multi-source risk statements")
    confidence: str = Field(..., description="Overall multi-source assessment confidence (HIGH, MEDIUM, LOW)")
    data_availability: MultiSourceDataAvailability


@router.get("/multisource-analysis", response_model=MultiSourceLandslideRiskResponse)
def get_multisource_landslide_risk_analysis(
    latitude: float = Query(..., ge=-90.0, le=90.0, description="Latitude coordinate between -90 and 90"),
    longitude: float = Query(..., ge=-180.0, le=180.0, description="Longitude coordinate between -180 and 180"),
    radius_km: float = Query(10.0, ge=1.0, le=100.0, description="Historical search radius in kilometers (1.0 to 100.0)"),
    satellite_radius_km: float = Query(5.0, ge=0.1, le=25.0, description="Satellite AOI search radius in kilometers (0.1 to 25.0)"),
    db: Session = Depends(get_db)
):
    """
    Multi-Source Landslide Risk Fusion Engine (Phase 8).
    Dynamically fuses Environmental Risk Intelligence, Historical Landslide Susceptibility,
    and Sentinel-1 Satellite Change Intelligence into a comprehensive Multi-Source Landslide Risk Assessment.
    """
    try:
        from app.services.multisource_risk_fusion_service import calculate_multisource_landslide_risk
        result = calculate_multisource_landslide_risk(
            latitude=latitude,
            longitude=longitude,
            radius_km=radius_km,
            satellite_radius_km=satellite_radius_km,
            db=db
        )
        return MultiSourceLandslideRiskResponse(**result)
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(val_err)
        )
    except RuntimeError as run_err:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(run_err)
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Multi-source risk fusion analysis failed: {str(exc)}"
        )



