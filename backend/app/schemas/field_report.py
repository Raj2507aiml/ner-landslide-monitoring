"""
Field Report Schemas - Phase 7 Checkpoints 16.1, 16.2, 16.3, 16.5 & 16.6

Defines Pydantic models and Enums for field hazard reporting validation,
media metadata, spatial queries, intelligence summaries, risk signal integration,
and operational authority review workflows.
"""

from enum import Enum
from datetime import datetime
from typing import Optional, List, Dict, Any, Union
import json
from pydantic import BaseModel, Field, field_validator

from app.schemas.field_report_media import FieldReportMediaResponse

class ReportType(str, Enum):
    CRACK = "CRACK"
    SLOPE_MOVEMENT = "SLOPE_MOVEMENT"
    BLOCKED_ROAD = "BLOCKED_ROAD"
    LANDSLIDE = "LANDSLIDE"
    DEBRIS = "DEBRIS"
    OTHER = "OTHER"

class ReporterType(str, Enum):
    CITIZEN = "CITIZEN"
    FIELD_OFFICIAL = "FIELD_OFFICIAL"

class ReportSeverity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class ReportStatus(str, Enum):
    PENDING = "PENDING"
    UNDER_REVIEW = "UNDER_REVIEW"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"

class ObservationStatus(str, Enum):
    VERIFIED_OBSERVATION = "VERIFIED_OBSERVATION"
    UNVERIFIED_OBSERVATION = "UNVERIFIED_OBSERVATION"
    REJECTED = "REJECTED"

class EvidenceConfidence(str, Enum):
    CONFIRMED = "CONFIRMED"
    REVIEW_PENDING = "REVIEW_PENDING"
    UNVERIFIED = "UNVERIFIED"
    REJECTED = "REJECTED"

class FieldIntelligenceStatus(str, Enum):
    NORMAL = "NORMAL"
    OBSERVATION_REPORTED = "OBSERVATION_REPORTED"
    MULTIPLE_OBSERVATIONS = "MULTIPLE_OBSERVATIONS"
    VERIFIED_GROUND_HAZARD = "VERIFIED_GROUND_HAZARD"
    CRITICAL_GROUND_ALERT = "CRITICAL_GROUND_ALERT"

class ExifConsistencyClassification(str, Enum):
    CONSISTENT = "CONSISTENT"
    NEARBY_DIFFERENCE = "NEARBY_DIFFERENCE"
    SIGNIFICANT_DIFFERENCE = "SIGNIFICANT_DIFFERENCE"
    NO_EXIF_GPS = "NO_EXIF_GPS"

class FieldReportCreate(BaseModel):
    report_type: ReportType = Field(..., description="Type of observed field hazard")
    description: str = Field(..., min_length=3, max_length=2000, description="Detailed observation description")
    latitude: float = Field(..., ge=-90.0, le=90.0, description="Latitude of observation (-90 to 90)")
    longitude: float = Field(..., ge=-180.0, le=180.0, description="Longitude of observation (-180 to 180)")
    reporter_type: ReporterType = Field(default=ReporterType.CITIZEN, description="Role of the submitter")
    severity: ReportSeverity = Field(default=ReportSeverity.MEDIUM, description="Estimated hazard severity level")
    full_name: Optional[str] = Field(None, max_length=150, description="Full name of observer")
    aadhaar_number: Optional[str] = Field(None, description="12-digit Aadhaar number for ground verification")

class FieldReportStatusUpdate(BaseModel):
    status: ReportStatus = Field(..., description="Updated operational verification status")
    verification_note: Optional[str] = Field(None, description="Optional verification note/reason")

class AadhaarVerificationUpdate(BaseModel):
    verification_status: str = Field(..., description="VERIFIED | REJECTED | RE_UPLOAD_REQUIRED")
    verification_note: Optional[str] = Field(None, max_length=2000, description="Admin verification note or feedback")

class FieldReportResponse(BaseModel):
    id: int
    report_type: ReportType
    description: str
    latitude: float
    longitude: float
    reporter_type: ReporterType
    severity: ReportSeverity
    status: ReportStatus
    created_at: datetime
    updated_at: datetime
    detected_state: Optional[str] = None
    notification_dispatched: Optional[bool] = None
    recipients_notified: Optional[int] = None
    # Jio Tag & Aadhaar Verification Info (Secure & Masked)
    full_name: Optional[str] = None
    aadhaar_number: Optional[str] = None  # Strictly masked e.g. XXXX-XXXX-1234
    verification_status: Optional[str] = "PENDING"
    verification_note: Optional[str] = None
    verified_by: Optional[str] = None
    verified_at: Optional[datetime] = None
    has_aadhaar_card: Optional[bool] = False
    has_aadhaar_qr: Optional[bool] = False
    has_jio_tag_image: Optional[bool] = False
    jio_tag_image_url: Optional[str] = None
    # Automated Aadhaar Verification & AI Inspection
    aadhaar_auto_status: Optional[str] = "UNVERIFIED"
    aadhaar_verification_details: Optional[Union[Dict[str, Any], str]] = None
    # Jio Tag Spatial Telemetry & Predictive Risk Features
    jio_tag_latitude: Optional[float] = None
    jio_tag_longitude: Optional[float] = None
    jio_tag_altitude: Optional[float] = None
    jio_tag_captured_at: Optional[datetime] = None
    visual_hazard_score: Optional[float] = None
    predicted_risk_score: Optional[float] = None
    prediction_details: Optional[Union[Dict[str, Any], str]] = None

    @field_validator("aadhaar_verification_details", "prediction_details", mode="before")
    @classmethod
    def parse_json_details(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except Exception:
                return v
        return v

    class Config:
        from_attributes = True

class SpatialContextDetails(BaseModel):
    nearby_reports_count: int = Field(0, description="Count of other reports within 5km radius")
    potential_duplicate: bool = Field(False, description="Flag indicating if duplicate report of identical type is within 500m")
    related_report_ids: List[int] = Field(default_factory=list, description="IDs of potentially related spatial duplicate reports")
    exif_consistency_summary: Optional[str] = Field(None, description="Aggregate EXIF coordinate consistency across attached media")

class FieldReportDetailResponse(FieldReportResponse):
    """
    Detailed field report response including attached media evidence records and spatial context.
    """
    media: List[FieldReportMediaResponse] = []
    spatial_context: Optional[SpatialContextDetails] = None
    observation_status: Optional[ObservationStatus] = None
    evidence_confidence: Optional[EvidenceConfidence] = None

    class Config:
        from_attributes = True

class NearbyFieldReportResponse(BaseModel):
    """
    Field report response enriched with spatial distance and duplicate awareness.
    """
    id: int
    report_type: ReportType
    description: str
    latitude: float
    longitude: float
    reporter_type: ReporterType
    severity: ReportSeverity
    status: ReportStatus
    created_at: datetime
    distance_km: float = Field(..., description="Geodesic Haversine distance from search origin in km")
    media_count: int = Field(0, description="Number of attached photographic evidence files")
    potential_duplicate: bool = Field(False, description="Flag indicating if a nearby report of identical type exists within 0.5km")
    related_report_ids: List[int] = Field(default_factory=list, description="IDs of potentially related spatial duplicate reports")
    observation_status: ObservationStatus = Field(..., description="Semantic verification status category")
    evidence_confidence: EvidenceConfidence = Field(..., description="Evidence confidence rating")

class FieldIntelligenceSummaryRequest(BaseModel):
    latitude: float = Field(..., ge=-90.0, le=90.0, description="Query center latitude (-90 to 90)")
    longitude: float = Field(..., ge=-180.0, le=180.0, description="Query center longitude (-180 to 180)")
    radius_km: float = Field(5.0, ge=0.1, le=100.0, description="Search radius in kilometers (0.1 to 100 km)")

class EnvironmentalContextSummary(BaseModel):
    composite_hazard_index: Optional[float] = None
    hazard_category: Optional[str] = None
    note: str = "Environmental risk model is independent of citizen field reports."

class FieldIntelligenceSummaryResponse(BaseModel):
    coordinates: Dict[str, float]
    radius_km: float
    total_reports: int
    pending_reports: int
    under_review_reports: int
    verified_reports: int
    rejected_reports: int
    verified_observations: int
    unverified_observations: int
    report_types_breakdown: Dict[str, int]
    severity_breakdown: Dict[str, int]
    evidence_statistics: Dict[str, int]
    potential_clusters_count: int
    environmental_context: Optional[EnvironmentalContextSummary] = None

# =========================================================================
# Phase 7 Checkpoint 16.5: Field Intelligence Risk Signal Schemas
# =========================================================================

class VerifiedGroundSignalDetails(BaseModel):
    score: float = Field(..., description="Normalized verified ground hazard signal score (0 to 100)")
    verified_reports: int = Field(..., description="Count of verified reports in the AOI")
    high_severity_reports: int = Field(..., description="Count of verified reports with HIGH severity")
    critical_reports: int = Field(..., description="Count of verified reports with CRITICAL severity")

class UnverifiedObservationsDetails(BaseModel):
    pending_reports: int = Field(..., description="Count of unverified reports awaiting review")
    under_review_reports: int = Field(..., description="Count of reports actively under operational review")
    high_priority_reports: int = Field(..., description="Count of unverified reports with HIGH or CRITICAL severity")

class ClusterAnalysisDetails(BaseModel):
    potential_cluster_detected: bool = Field(..., description="Flag indicating if multiple reports of identical type cluster within 500m")
    cluster_report_count: int = Field(..., description="Total count of reports involved in localized spatial clusters")
    cluster_types: List[str] = Field(default_factory=list, description="Hazard types involved in detected clusters")

class RecencyAnalysisDetails(BaseModel):
    very_recent: int = Field(..., description="Reports submitted in past 0-24 hours")
    recent: int = Field(..., description="Reports submitted in past 1-3 days")
    aging: int = Field(..., description="Reports submitted in past 3-7 days")
    historical: int = Field(..., description="Reports submitted > 7 days ago")

class FieldIntelligenceRiskSignalResponse(BaseModel):
    location: Dict[str, float]
    search_radius_km: float
    field_intelligence_status: FieldIntelligenceStatus
    verified_ground_signal: VerifiedGroundSignalDetails
    unverified_observations: UnverifiedObservationsDetails
    cluster_analysis: ClusterAnalysisDetails
    recency: RecencyAnalysisDetails
    dominant_observation_types: List[str]
    operational_message: str
    disclaimer: str = "Field intelligence is treated as observational evidence and does not replace environmental hazard models."

# =========================================================================
# Phase 7 Checkpoint 16.6: Operational Review Queue Schemas
# =========================================================================

class ReviewQueueItemResponse(BaseModel):
    id: int
    report_type: ReportType
    description: str
    severity: ReportSeverity
    reporter_type: ReporterType
    status: ReportStatus
    latitude: float
    longitude: float
    created_at: datetime
    updated_at: datetime
    media_count: int = Field(0, description="Attached media evidence count")
    potential_duplicate: bool = Field(False, description="Flag indicating duplicate hazard within 500m")
    related_report_ids: List[int] = Field(default_factory=list, description="Related duplicate report IDs")
    observation_status: ObservationStatus = Field(..., description="Observation category")
    evidence_confidence: EvidenceConfidence = Field(..., description="Confidence classification")
    exif_consistency_summary: Optional[str] = Field(None, description="EXIF GPS consistency summary across attached photos")
    full_name: Optional[str] = None
    aadhaar_number: Optional[str] = None
    verification_status: Optional[str] = "PENDING"
    verification_note: Optional[str] = None
    has_aadhaar_card: Optional[bool] = False
    has_aadhaar_qr: Optional[bool] = False
    has_jio_tag_image: Optional[bool] = False
    aadhaar_auto_status: Optional[str] = "UNVERIFIED"
    predicted_risk_score: Optional[float] = None
    visual_hazard_score: Optional[float] = None

    class Config:
        from_attributes = True

class ReviewQueueResponse(BaseModel):
    total: int = Field(..., description="Total count of reports matching filter criteria")
    pending_count: int = Field(..., description="Total pending triage reports in system")
    under_review_count: int = Field(..., description="Total reports actively under operational review")
    verified_count: int = Field(..., description="Total verified ground observations in system")
    rejected_count: int = Field(..., description="Total rejected reports in system")
    critical_count: int = Field(..., description="Total critical severity reports in system")
    items: List[ReviewQueueItemResponse] = Field(..., description="Sorted review queue items prioritizing critical severity")
