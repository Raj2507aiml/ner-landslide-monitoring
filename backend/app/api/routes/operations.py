"""
Operations API Routes - Phase 8 Checkpoint 17.4

Exposes endpoints for integrated operational situation assessments synthesizing
environmental risk, early warning decisions, field intelligence, and road disruptions.
"""

import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status as http_status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.services.aoi_service import is_inside_ner
from app.services.operational_assessment_service import OperationalAssessmentService
from app.schemas.operational_assessment import OperationalSituationAssessmentResponse

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/situation-assessment", response_model=OperationalSituationAssessmentResponse)
def get_operational_situation_assessment(
    latitude: float = Query(..., ge=-90.0, le=90.0, description="Center latitude (-90 to 90)"),
    longitude: float = Query(..., ge=-180.0, le=180.0, description="Center longitude (-180 to 180)"),
    radius_km: float = Query(5.0, ge=0.5, le=25.0, description="Analysis radius in kilometers (0.5 to 25.0 km)"),
    db: Session = Depends(get_db)
):
    """
    Synthesizes environmental landslide risk, early warning decisions, ground-truth field observations,
    and road network disruption intelligence into an integrated operational situation assessment.
    """
    if not is_inside_ner(latitude, longitude):
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="Target coordinates must lie within India's North Eastern Region."
        )

    try:
        return OperationalAssessmentService.evaluate_situation_assessment(
            db=db,
            latitude=latitude,
            longitude=longitude,
            radius_km=radius_km
        )
    except ValueError as ve:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=str(ve)
        )
    except Exception as e:
        logger.error(f"[Operations Route] Situation assessment evaluation failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Integrated operational situation assessment failed: {str(e)}"
        )
