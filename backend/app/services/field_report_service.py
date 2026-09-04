"""
Field Report Service - Phase 7 Checkpoint 16.1 & 16.6

Provides business logic, controlled verification workflows, and priority-ordered
review queues for managing citizen and field official hazard intelligence reports.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy import case
from sqlalchemy.orm import Session

from app.models.field_report import FieldReport
from app.models.field_report_media import FieldReportMedia
from app.schemas.field_report import (
    FieldReportCreate,
    ReportStatus,
    ReportType,
    ReportSeverity,
    ObservationStatus,
    EvidenceConfidence,
    ReviewQueueItemResponse,
    ReviewQueueResponse,
    SpatialContextDetails,
    FieldReportDetailResponse
)
from app.services.field_report_spatial_service import (
    FieldReportSpatialService,
    get_evidence_semantics,
    haversine_distance
)
from app.services.field_report_media_service import (
    FieldReportMediaService,
    compute_exif_consistency
)

# Valid operational status transitions
VALID_TRANSITIONS: Dict[str, List[str]] = {
    ReportStatus.PENDING.value: [ReportStatus.UNDER_REVIEW.value, ReportStatus.REJECTED.value],
    ReportStatus.UNDER_REVIEW.value: [ReportStatus.VERIFIED.value, ReportStatus.REJECTED.value, ReportStatus.PENDING.value],
    ReportStatus.VERIFIED.value: [ReportStatus.UNDER_REVIEW.value],
    ReportStatus.REJECTED.value: [ReportStatus.UNDER_REVIEW.value],
}

class FieldReportService:
    @staticmethod
    def create_report(db: Session, report_in: FieldReportCreate) -> FieldReport:
        """
        Persists a new field observation report into the database with initial PENDING status.
        """
        db_report = FieldReport(
            report_type=report_in.report_type.value,
            description=report_in.description,
            latitude=report_in.latitude,
            longitude=report_in.longitude,
            reporter_type=report_in.reporter_type.value,
            severity=report_in.severity.value,
            status=ReportStatus.PENDING.value,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db.add(db_report)
        db.commit()
        db.refresh(db_report)
        return db_report

    @staticmethod
    def get_reports(
        db: Session,
        skip: int = 0,
        limit: int = 100,
        status: Optional[ReportStatus] = None,
        report_type: Optional[ReportType] = None,
        severity: Optional[ReportSeverity] = None
    ) -> List[FieldReport]:
        """
        Retrieves a list of field reports with optional filtering.
        """
        query = db.query(FieldReport)
        if status:
            query = query.filter(FieldReport.status == status.value)
        if report_type:
            query = query.filter(FieldReport.report_type == report_type.value)
        if severity:
            query = query.filter(FieldReport.severity == severity.value)
        return query.order_by(FieldReport.created_at.desc()).offset(skip).limit(limit).all()

    @staticmethod
    def get_report_by_id(db: Session, report_id: int) -> Optional[FieldReport]:
        """
        Retrieves a single field report by its primary key ID.
        """
        return db.query(FieldReport).filter(FieldReport.id == report_id).first()

    @classmethod
    def get_report_detail(cls, db: Session, report_id: int) -> Optional[FieldReportDetailResponse]:
        """
        Retrieves detailed report information enriched with EXIF GPS consistency and spatial duplicate context.
        """
        report = db.query(FieldReport).filter(FieldReport.id == report_id).first()
        if not report:
            return None

        # Build media responses with EXIF evaluation against report coordinates
        media_responses = []
        exif_consistencies = []
        for m in report.media:
            m_resp = FieldReportMediaService.to_schema(
                media=m,
                report_lat=report.latitude,
                report_lon=report.longitude
            )
            media_responses.append(m_resp)
            if m_resp.exif_consistency and m_resp.exif_consistency != "NO_EXIF_GPS":
                exif_consistencies.append(m_resp.exif_consistency)

        # Spatial duplicate & nearby analysis
        all_reports = db.query(FieldReport).all()
        duplicates_map = FieldReportSpatialService.detect_spatial_duplicates(all_reports)

        nearby_count = 0
        for other in all_reports:
            if other.id != report.id:
                dist = haversine_distance(report.latitude, report.longitude, other.latitude, other.longitude)
                if dist <= 5.0:
                    nearby_count += 1

        is_duplicate = report.id in duplicates_map and len(duplicates_map[report.id]) > 0
        related_ids = duplicates_map.get(report.id, [])

        exif_summary = "NO_EXIF_GPS"
        if "SIGNIFICANT_DIFFERENCE" in exif_consistencies:
            exif_summary = "SIGNIFICANT_DIFFERENCE"
        elif "NEARBY_DIFFERENCE" in exif_consistencies:
            exif_summary = "NEARBY_DIFFERENCE"
        elif "CONSISTENT" in exif_consistencies:
            exif_summary = "CONSISTENT"

        obs_status, conf = get_evidence_semantics(report.status)

        return FieldReportDetailResponse(
            id=report.id,
            report_type=report.report_type,
            description=report.description,
            latitude=report.latitude,
            longitude=report.longitude,
            reporter_type=report.reporter_type,
            severity=report.severity,
            status=report.status,
            created_at=report.created_at,
            updated_at=report.updated_at,
            media=media_responses,
            spatial_context=SpatialContextDetails(
                nearby_reports_count=nearby_count,
                potential_duplicate=is_duplicate,
                related_report_ids=related_ids,
                exif_consistency_summary=exif_summary
            ),
            observation_status=obs_status,
            evidence_confidence=conf
        )

    @staticmethod
    def update_status(
        db: Session,
        report_id: int,
        new_status: ReportStatus,
        enforce_workflow: bool = True
    ) -> Optional[FieldReport]:
        """
        Updates the operational verification status of a field report adhering to controlled workflow transitions.
        Raises ValueError on invalid transitions.
        """
        db_report = db.query(FieldReport).filter(FieldReport.id == report_id).first()
        if not db_report:
            return None

        current_status = db_report.status.value if hasattr(db_report.status, 'value') else str(db_report.status)
        target_status = new_status.value

        if enforce_workflow and current_status != target_status:
            allowed = VALID_TRANSITIONS.get(current_status, [])
            if target_status not in allowed:
                raise ValueError(
                    f"Invalid status transition from {current_status} to {target_status}. "
                    f"Reports in {current_status} can only transition to: {', '.join(allowed)}."
                )

        db_report.status = target_status
        db_report.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(db_report)
        return db_report

    @classmethod
    def get_review_queue(
        cls,
        db: Session,
        status: Optional[ReportStatus] = None,
        severity: Optional[ReportSeverity] = None,
        report_type: Optional[ReportType] = None,
        skip: int = 0,
        limit: int = 50
    ) -> ReviewQueueResponse:
        """
        Retrieves operational review queue items prioritized by severity (CRITICAL -> HIGH -> MEDIUM -> LOW)
        and recency (newer first). Enriches with spatial duplicate and EXIF consistency metadata.
        """
        # Global operational counts
        total_in_db = db.query(FieldReport).count()
        pending_count = db.query(FieldReport).filter(FieldReport.status == ReportStatus.PENDING.value).count()
        under_review_count = db.query(FieldReport).filter(FieldReport.status == ReportStatus.UNDER_REVIEW.value).count()
        verified_count = db.query(FieldReport).filter(FieldReport.status == ReportStatus.VERIFIED.value).count()
        rejected_count = db.query(FieldReport).filter(FieldReport.status == ReportStatus.REJECTED.value).count()
        critical_count = db.query(FieldReport).filter(FieldReport.severity == ReportSeverity.CRITICAL.value).count()

        # Severity priority case ordering
        severity_order = case(
            (FieldReport.severity == ReportSeverity.CRITICAL.value, 4),
            (FieldReport.severity == ReportSeverity.HIGH.value, 3),
            (FieldReport.severity == ReportSeverity.MEDIUM.value, 2),
            (FieldReport.severity == ReportSeverity.LOW.value, 1),
            else_=0
        )

        query = db.query(FieldReport)
        if status:
            query = query.filter(FieldReport.status == status.value)
        if severity:
            query = query.filter(FieldReport.severity == severity.value)
        if report_type:
            query = query.filter(FieldReport.report_type == report_type.value)

        filtered_total = query.count()
        reports = query.order_by(severity_order.desc(), FieldReport.created_at.desc()).offset(skip).limit(limit).all()

        # Precompute spatial duplicates across system reports
        all_reports = db.query(FieldReport).all()
        duplicates_map = FieldReportSpatialService.detect_spatial_duplicates(all_reports)

        items: List[ReviewQueueItemResponse] = []
        for r in reports:
            # Check attached photos EXIF consistency
            exif_consistencies = []
            for m in r.media:
                _, cons = compute_exif_consistency(
                    report_lat=r.latitude,
                    report_lon=r.longitude,
                    exif_lat=m.exif_latitude,
                    exif_lon=m.exif_longitude
                )
                if cons and cons != "NO_EXIF_GPS":
                    exif_consistencies.append(cons)

            exif_summary = "NO_EXIF_GPS"
            if "SIGNIFICANT_DIFFERENCE" in exif_consistencies:
                exif_summary = "SIGNIFICANT_DIFFERENCE"
            elif "NEARBY_DIFFERENCE" in exif_consistencies:
                exif_summary = "NEARBY_DIFFERENCE"
            elif "CONSISTENT" in exif_consistencies:
                exif_summary = "CONSISTENT"

            obs_status, conf = get_evidence_semantics(r.status)
            is_duplicate = r.id in duplicates_map and len(duplicates_map[r.id]) > 0
            related_ids = duplicates_map.get(r.id, [])

            items.append(ReviewQueueItemResponse(
                id=r.id,
                report_type=r.report_type,
                description=r.description,
                severity=r.severity,
                reporter_type=r.reporter_type,
                status=r.status,
                latitude=r.latitude,
                longitude=r.longitude,
                created_at=r.created_at,
                updated_at=r.updated_at,
                media_count=len(r.media),
                potential_duplicate=is_duplicate,
                related_report_ids=related_ids,
                observation_status=obs_status,
                evidence_confidence=conf,
                exif_consistency_summary=exif_summary
            ))

        return ReviewQueueResponse(
            total=filtered_total,
            pending_count=pending_count,
            under_review_count=under_review_count,
            verified_count=verified_count,
            rejected_count=rejected_count,
            critical_count=critical_count,
            items=items
        )
