"""
Field Reports API Routes - Phase 7 Checkpoints 16.1, 16.2, 16.3, 16.5 & 16.6

Exposes endpoints for submitting, listing, spatial filtering, intelligence summaries,
GeoJSON map layers, risk signals, review queue triage, status updates, and media evidence attachment.
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, status as http_status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.services.aoi_service import is_inside_ner
from app.services.field_report_service import FieldReportService
from app.services.field_report_media_service import FieldReportMediaService
from app.services.field_report_spatial_service import FieldReportSpatialService
from app.services.field_intelligence_risk_service import FieldIntelligenceRiskService
from app.schemas.field_report import (
    FieldReportCreate,
    FieldReportResponse,
    FieldReportDetailResponse,
    FieldReportStatusUpdate,
    NearbyFieldReportResponse,
    FieldIntelligenceSummaryRequest,
    FieldIntelligenceSummaryResponse,
    FieldIntelligenceRiskSignalResponse,
    ReviewQueueResponse,
    ReportStatus,
    ReportType,
    ReportSeverity
)
from app.schemas.field_report_media import (
    FieldReportMediaResponse,
    FieldReportMediaDeleteResponse
)

router = APIRouter()

# =========================================================================
# 1. Base Report CRUD Endpoints
# =========================================================================

@router.post("", response_model=FieldReportResponse, status_code=http_status.HTTP_201_CREATED)
def create_field_report(report_in: FieldReportCreate, db: Session = Depends(get_db)):
    """
    Submits a new geo-tagged field hazard report.
    Enforces NER boundary validation.
    """
    if not is_inside_ner(report_in.latitude, report_in.longitude):
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="Target coordinates must lie within India's North Eastern Region."
        )
    return FieldReportService.create_report(db=db, report_in=report_in)

@router.get("", response_model=List[FieldReportResponse])
def list_field_reports(
    report_status: Optional[ReportStatus] = Query(None, alias="status", description="Filter by report status"),
    report_type: Optional[ReportType] = Query(None, description="Filter by report type"),
    severity: Optional[ReportSeverity] = Query(None, description="Filter by severity level"),
    skip: int = Query(0, ge=0, description="Offset items for pagination"),
    limit: int = Query(100, ge=1, le=500, description="Limit items per page"),
    db: Session = Depends(get_db)
):
    """
    Retrieves a list of field reports with optional status, report_type, and severity filtering.
    """
    return FieldReportService.get_reports(
        db=db,
        skip=skip,
        limit=limit,
        status=report_status,
        report_type=report_type,
        severity=severity
    )

# =========================================================================
# 2. Spatial Intelligence & Review Queue Endpoints (BEFORE /{report_id})
# =========================================================================

@router.get("/review-queue", response_model=ReviewQueueResponse)
def get_operational_review_queue(
    report_status: Optional[ReportStatus] = Query(None, alias="status", description="Filter by operational status"),
    severity: Optional[ReportSeverity] = Query(None, description="Filter by severity level"),
    report_type: Optional[ReportType] = Query(None, description="Filter by report type"),
    skip: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(50, ge=1, le=200, description="Pagination limit"),
    db: Session = Depends(get_db)
):
    """
    Returns prioritized field reports for disaster authority review queue triage.
    Orders by severity (CRITICAL > HIGH > MEDIUM > LOW) and submission recency.
    """
    return FieldReportService.get_review_queue(
        db=db,
        status=report_status,
        severity=severity,
        report_type=report_type,
        skip=skip,
        limit=limit
    )

@router.get("/risk-signal", response_model=FieldIntelligenceRiskSignalResponse)
def get_field_intelligence_risk_signal(
    latitude: float = Query(..., ge=-90.0, le=90.0, description="Search center latitude (-90 to 90)"),
    longitude: float = Query(..., ge=-180.0, le=180.0, description="Search center longitude (-180 to 180)"),
    radius_km: float = Query(5.0, ge=0.1, le=100.0, description="Search radius in kilometers (0.1 - 100 km)"),
    db: Session = Depends(get_db)
):
    """
    Evaluates ground-truth field hazard observations around coordinates to produce
    a structured Field Intelligence Risk Signal.
    """
    if not is_inside_ner(latitude, longitude):
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="Target coordinates must lie within India's North Eastern Region."
        )
    return FieldIntelligenceRiskService.analyze_ground_risk_signal(
        db=db,
        latitude=latitude,
        longitude=longitude,
        radius_km=radius_km
    )

@router.post("/intelligence-summary", response_model=FieldIntelligenceSummaryResponse)
def get_field_intelligence_summary(
    payload: FieldIntelligenceSummaryRequest,
    db: Session = Depends(get_db)
):
    """
    Generates an aggregated observational intelligence summary for the AOI.
    Enforces NER boundary and radius constraints.
    """
    if not is_inside_ner(payload.latitude, payload.longitude):
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="Target coordinates must lie within India's North Eastern Region."
        )
    return FieldReportSpatialService.generate_intelligence_summary(
        db=db,
        latitude=payload.latitude,
        longitude=payload.longitude,
        radius_km=payload.radius_km
    )

@router.get("/nearby", response_model=List[NearbyFieldReportResponse])
def get_nearby_field_reports(
    latitude: float = Query(..., ge=-90.0, le=90.0, description="Search center latitude"),
    longitude: float = Query(..., ge=-180.0, le=180.0, description="Search center longitude"),
    radius_km: float = Query(5.0, ge=0.1, le=100.0, description="Search radius in kilometers (0.1 - 100 km)"),
    report_status: Optional[ReportStatus] = Query(None, alias="status", description="Filter by report status"),
    report_type: Optional[ReportType] = Query(None, description="Filter by report type"),
    severity: Optional[ReportSeverity] = Query(None, description="Filter by severity level"),
    db: Session = Depends(get_db)
):
    """
    Retrieves all field reports within a radius of the specified coordinates.
    Includes geodesic distance, media counts, duplicate detection, and evidence classifications.
    """
    if not is_inside_ner(latitude, longitude):
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="Target coordinates must lie within India's North Eastern Region."
        )
    return FieldReportSpatialService.get_nearby_reports(
        db=db,
        latitude=latitude,
        longitude=longitude,
        radius_km=radius_km,
        status=report_status,
        report_type=report_type,
        severity=severity
    )

@router.get("/geojson", response_model=Dict[str, Any])
def get_field_reports_geojson(
    latitude: Optional[float] = Query(None, ge=-90.0, le=90.0, description="Optional center latitude"),
    longitude: Optional[float] = Query(None, ge=-180.0, le=180.0, description="Optional center longitude"),
    radius_km: Optional[float] = Query(None, ge=0.1, le=100.0, description="Optional radius in km"),
    report_status: Optional[ReportStatus] = Query(None, alias="status", description="Filter by report status"),
    report_type: Optional[ReportType] = Query(None, description="Filter by report type"),
    severity: Optional[ReportSeverity] = Query(None, description="Filter by severity level"),
    db: Session = Depends(get_db)
):
    """
    Exports field reports as a GIS-ready GeoJSON FeatureCollection.
    GeoJSON coordinate order is strictly [longitude, latitude].
    """
    if latitude is not None and longitude is not None:
        if not is_inside_ner(latitude, longitude):
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail="Target coordinates must lie within India's North Eastern Region."
            )
        if radius_km is None:
            radius_km = 5.0
            
    return FieldReportSpatialService.get_geojson_features(
        db=db,
        latitude=latitude,
        longitude=longitude,
        radius_km=radius_km,
        status=report_status,
        report_type=report_type,
        severity=severity
    )

# =========================================================================
# 3. Dynamic /{report_id} Endpoints
# =========================================================================

@router.get("/{report_id}", response_model=FieldReportDetailResponse)
def get_field_report(report_id: int, db: Session = Depends(get_db)):
    """
    Retrieves detailed field report by ID with media evidence and spatial context.
    """
    detail = FieldReportService.get_report_detail(db=db, report_id=report_id)
    if not detail:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"Field report with ID {report_id} not found."
        )
    return detail

@router.patch("/{report_id}/status", response_model=FieldReportResponse)
def update_field_report_status(
    report_id: int,
    status_in: FieldReportStatusUpdate,
    db: Session = Depends(get_db)
):
    """
    Updates the operational verification status of a field report.
    Enforces controlled workflow transitions (e.g. PENDING -> UNDER_REVIEW -> VERIFIED/REJECTED).
    """
    try:
        updated_report = FieldReportService.update_status(
            db=db,
            report_id=report_id,
            new_status=status_in.status
        )
    except ValueError as e:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    if not updated_report:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"Field report with ID {report_id} not found."
        )
    return updated_report

# =========================================================================
# 4. Media Evidence Endpoints
# =========================================================================

@router.post("/{report_id}/media", response_model=FieldReportMediaResponse, status_code=http_status.HTTP_201_CREATED)
async def upload_field_report_media(
    report_id: int,
    file: UploadFile = File(..., description="Photographic evidence image (JPEG, PNG, WebP)"),
    db: Session = Depends(get_db)
):
    """
    Uploads photographic evidence for a field hazard report.
    Validates image integrity with Pillow, extracts EXIF GPS if present, and stores securely.
    """
    return await FieldReportMediaService.process_and_save_media(
        db=db,
        report_id=report_id,
        file=file
    )

@router.get("/{report_id}/media", response_model=List[FieldReportMediaResponse])
def get_field_report_media(
    report_id: int,
    db: Session = Depends(get_db)
):
    """
    Retrieves all photographic evidence items attached to a field report.
    """
    return FieldReportMediaService.get_media_for_report(db=db, report_id=report_id)

@router.delete("/{report_id}/media/{media_id}", response_model=FieldReportMediaDeleteResponse)
def delete_field_report_media(
    report_id: int,
    media_id: int,
    db: Session = Depends(get_db)
):
    """
    Deletes a photographic evidence item and removes its physical file from storage.
    """
    return FieldReportMediaService.delete_media_item(
        db=db,
        report_id=report_id,
        media_id=media_id
    )
