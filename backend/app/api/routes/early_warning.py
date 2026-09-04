"""
Early Warning Routing Interface - Phase 6 Checkpoint 15.3 & Phase 7 Checkpoint 16.5

Mounts the POST /api/v1/early-warning/analyze endpoint.
Combines environmental hazard models, satellite radar change, and independent ground observation signals.
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.services.aoi_service import is_inside_ner
from app.services.composite_risk_service import CompositeRiskService
from app.services.automatic_satellite_pair_service import AutomaticSatellitePairService
from app.services.early_warning_service import EarlyWarningService

router = APIRouter()

class EarlyWarningAnalysisRequest(BaseModel):
    latitude: float = Field(..., ge=-90.0, le=90.0, description="Latitude of query coordinate (-90 to 90)")
    longitude: float = Field(..., ge=-180.0, le=180.0, description="Longitude of query coordinate (-180 to 180)")

class HazardContextDetails(BaseModel):
    composite_hazard_index: float = Field(..., description="Overall Composite Hazard Index (0-100)")
    hazard_category: str = Field(..., description="Environmental hazard category (Low, Moderate, High, Very High)")

class SatelliteContextDetails(BaseModel):
    status: str = Field(..., description="Satellite pair discovery and clipping status")
    rsci: Optional[float] = Field(..., description="Calculated Radar Surface Change Index or null if unavailable")
    category: Optional[str] = Field(..., description="Surface change category description or null if unavailable")

class GroundObservationContextDetails(BaseModel):
    status: str = Field(..., description="Ground observation categorical status")
    message: str = Field(..., description="Ground observation summary message")
    verified_signal_score: float = Field(..., description="Normalized verified ground hazard score (0-100)")

class EarlyWarningResponse(BaseModel):
    warning_level: str = Field(..., description="Operational warning level state (NORMAL, WATCH, ALERT, CRITICAL)")
    decision_mode: str = Field(..., description="Decision logic operational mode (FULL_EVIDENCE, METEOROLOGICAL_FALLBACK)")
    hazard_context: HazardContextDetails
    satellite_context: SatelliteContextDetails
    recommended_action: str = Field(..., description="Target recommended action guidelines")
    reasoning: str = Field(..., description="Detailed text explaining how the warning level was determined")
    observational_verification: str = Field(..., description="Satellite availability status description")
    scientific_notice: str = Field(..., description="Scientific disclaimer notice")
    ground_observation_context: Optional[GroundObservationContextDetails] = Field(None, description="Independent ground observation field intelligence layer")

@router.post("/analyze", response_model=EarlyWarningResponse)
def analyze_early_warning(payload: EarlyWarningAnalysisRequest, db: Session = Depends(get_db)):
    """
    Computes the composite hazard assessment and queries automatic satellite change data,
    running them through the Early Warning Decision Engine.
    """
    # 1. Coordinate boundary validation
    if not is_inside_ner(payload.latitude, payload.longitude):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Target coordinates must lie within India's North Eastern Region."
        )

    # 2. Step A: Compute the Composite Hazard assessment
    try:
        composite_hazard = CompositeRiskService.calculate_composite_risk(
            db=db,
            latitude=payload.latitude,
            longitude=payload.longitude
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Composite hazard assessment failed during early warning evaluation: {str(e)}"
        )

    # 3. Step B: Query Automatic Satellite Change Analysis
    radar_change_data = None
    try:
        radar_change_data = AutomaticSatellitePairService.analyze_location_change(
            latitude=payload.latitude,
            longitude=payload.longitude,
            radius_km=5.0
        )
    except Exception:
        # Fall back to meteorological mode if satellite alignment fails
        pass

    # 4. Step C: Run EarlyWarningService evaluation
    try:
        decision_result = EarlyWarningService.evaluate_warning_status(
            composite_hazard_data=composite_hazard,
            radar_change_data=radar_change_data
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Early warning decision evaluation failed: {str(e)}"
        )

    # 5. Step D: Return unified Early Warning response structure
    sat_status = "UNAVAILABLE"
    if radar_change_data:
        sat_status = radar_change_data.get("status", "UNAVAILABLE")

    return {
        "warning_level": decision_result["warning_level"],
        "decision_mode": decision_result["operational_mode"],
        "hazard_context": {
            "composite_hazard_index": decision_result["hazard_context"]["composite_hazard_index"],
            "hazard_category": decision_result["hazard_context"]["categorical_hazard_level"]
        },
        "satellite_context": {
            "status": sat_status,
            "rsci": decision_result["evidence_summary"]["rsci_score"],
            "category": decision_result["evidence_summary"]["rsci_category"] if decision_result["evidence_summary"]["satellite_available"] else None
        },
        "recommended_action": decision_result["recommended_action"],
        "reasoning": decision_result["reasoning"],
        "observational_verification": decision_result["satellite_availability"],
        "scientific_notice": decision_result["scientific_notice"],
        "ground_observation_context": decision_result.get("ground_observation_context")
    }
