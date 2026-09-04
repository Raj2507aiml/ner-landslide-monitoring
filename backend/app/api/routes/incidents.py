"""
Operational Incidents API Routes - Phase 8 Checkpoint 18.1

Exposes endpoints for automatic incident evaluation, listing, detail view,
and controlled state transitions (OPEN -> ACKNOWLEDGED -> IN_PROGRESS -> RESOLVED).
"""

import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Path, status as http_status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.services.aoi_service import is_inside_ner
from app.services.operational_incident_service import OperationalIncidentService
from app.schemas.operational_incident import (
    IncidentSeverity,
    IncidentStatus,
    IncidentResponse,
    IncidentEvaluationResponse,
    IncidentStatusUpdateRequest,
    IncidentListResponse
)

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/evaluate", response_model=IncidentEvaluationResponse)
def evaluate_operational_incident(
    latitude: float = Query(..., ge=-90.0, le=90.0, description="Latitude of query coordinate (-90 to 90)"),
    longitude: float = Query(..., ge=-180.0, le=180.0, description="Longitude of query coordinate (-180 to 180)"),
    radius_km: float = Query(5.0, ge=0.5, le=25.0, description="Analysis radius in kilometers (0.5 to 25.0 km)"),
    db: Session = Depends(get_db)
):
    """
    Evaluates current operational situation and determines whether an incident should be created automatically,
    prevented due to duplicate active incidents, or skipped if conditions do not warrant an incident.
    """
    if not is_inside_ner(latitude, longitude):
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="Target coordinates must lie within India's North Eastern Region."
        )

    try:
        res = OperationalIncidentService.evaluate_and_create_incident(
            db=db,
            latitude=latitude,
            longitude=longitude,
            radius_km=radius_km
        )
        return res
    except ValueError as ve:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=str(ve)
        )
    except Exception as e:
        logger.error(f"[Incidents Route] Incident evaluation failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Operational incident evaluation failed: {str(e)}"
        )

@router.get("", response_model=IncidentListResponse)
def list_operational_incidents(
    status: Optional[IncidentStatus] = Query(None, description="Filter by incident status"),
    severity: Optional[IncidentSeverity] = Query(None, description="Filter by incident severity"),
    limit: int = Query(50, ge=1, le=200, description="Max records to return"),
    offset: int = Query(0, ge=0, description="Record offset for pagination"),
    db: Session = Depends(get_db)
):
    """
    Lists operational incidents with optional status and severity filters, ordered newest first.
    """
    incidents, total = OperationalIncidentService.list_incidents(
        db=db,
        status=status.value if status else None,
        severity=severity.value if severity else None,
        limit=limit,
        offset=offset
    )
    return IncidentListResponse(total=total, incidents=incidents)

@router.get("/{incident_id}", response_model=IncidentResponse)
def get_operational_incident_detail(
    incident_id: int = Path(..., ge=1, description="Unique ID of the incident"),
    db: Session = Depends(get_db)
):
    """
    Retrieves detailed information for a specific operational incident.
    """
    incident = OperationalIncidentService.get_incident_by_id(db, incident_id)
    if not incident:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"Operational incident #{incident_id} not found."
        )
    return incident

@router.post("/{incident_id}/acknowledge", response_model=IncidentResponse)
def acknowledge_operational_incident(
    incident_id: int = Path(..., ge=1, description="Unique ID of the incident"),
    payload: Optional[IncidentStatusUpdateRequest] = None,
    db: Session = Depends(get_db)
):
    """
    Transitions incident status from OPEN to ACKNOWLEDGED.
    """
    notes = payload.notes if payload else None
    try:
        return OperationalIncidentService.acknowledge_incident(db, incident_id, notes=notes)
    except LookupError as le:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail=str(le))
    except ValueError as ve:
        raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail=str(ve))

@router.post("/{incident_id}/start-response", response_model=IncidentResponse)
def start_operational_incident_response(
    incident_id: int = Path(..., ge=1, description="Unique ID of the incident"),
    payload: Optional[IncidentStatusUpdateRequest] = None,
    db: Session = Depends(get_db)
):
    """
    Transitions incident status from ACKNOWLEDGED to IN_PROGRESS.
    """
    notes = payload.notes if payload else None
    try:
        return OperationalIncidentService.start_incident_response(db, incident_id, notes=notes)
    except LookupError as le:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail=str(le))
    except ValueError as ve:
        raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail=str(ve))

@router.post("/{incident_id}/resolve", response_model=IncidentResponse)
def resolve_operational_incident(
    incident_id: int = Path(..., ge=1, description="Unique ID of the incident"),
    payload: Optional[IncidentStatusUpdateRequest] = None,
    db: Session = Depends(get_db)
):
    """
    Transitions incident status from IN_PROGRESS to RESOLVED.
    """
    notes = payload.notes if payload else None
    try:
        return OperationalIncidentService.resolve_incident(db, incident_id, notes=notes)
    except LookupError as le:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail=str(le))
    except ValueError as ve:
        raise HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail=str(ve))
