"""
Field Report Service - Phase 7 Checkpoint 16.1 & 16.6

Provides business logic, controlled verification workflows, and priority-ordered
review queues for managing citizen and field official hazard intelligence reports.
"""

import os
import io
import uuid
import json
import hashlib
from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple
from PIL import Image
from fastapi import UploadFile, HTTPException, status
from sqlalchemy import case
from sqlalchemy.orm import Session

from app.core.config import BASE_DIR
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
    compute_exif_consistency,
    MEDIA_ROOT_DIR
)

# Secure Documents Storage Configuration
SECURE_DOCS_ROOT = os.path.join(BASE_DIR, "data", "secure_documents")
MAX_DOC_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB limit
ALLOWED_DOC_FORMATS = {
    "JPEG": ("image/jpeg", ".jpg"),
    "PNG": ("image/png", ".png"),
    "WEBP": ("image/webp", ".webp")
}

def _ensure_secure_docs_dir():
    os.makedirs(SECURE_DOCS_ROOT, exist_ok=True)
    gitignore_path = os.path.join(SECURE_DOCS_ROOT, ".gitignore")
    if not os.path.exists(gitignore_path):
        with open(gitignore_path, "w") as f:
            f.write("*\n!.gitignore\n")

# Valid operational status transitions
VALID_TRANSITIONS: Dict[str, List[str]] = {
    ReportStatus.PENDING.value: [ReportStatus.UNDER_REVIEW.value, ReportStatus.VERIFIED.value, ReportStatus.REJECTED.value],
    ReportStatus.UNDER_REVIEW.value: [ReportStatus.VERIFIED.value, ReportStatus.REJECTED.value, ReportStatus.PENDING.value],
    ReportStatus.VERIFIED.value: [ReportStatus.UNDER_REVIEW.value],
    ReportStatus.REJECTED.value: [ReportStatus.UNDER_REVIEW.value],
}

class FieldReportService:
    @staticmethod
    def create_report(db: Session, report_in: FieldReportCreate) -> FieldReport:
        """
        Persists a new field observation report into the database with initial PENDING status.
        Securely handles full_name and validates/masks 12-digit Aadhaar number if provided.
        """
        masked_aadhaar = None
        aadhaar_hash = None
        aadhaar_auto_status = "UNVERIFIED"
        aadhaar_verification_details = None

        if report_in.aadhaar_number:
            raw_aadhaar = "".join(c for c in report_in.aadhaar_number if c.isdigit())
            if len(raw_aadhaar) != 12:
                raise ValueError("Aadhaar Number must contain exactly 12 numeric digits.")
            masked_aadhaar = f"XXXX-XXXX-{raw_aadhaar[-4:]}"
            aadhaar_hash = hashlib.sha256(raw_aadhaar.encode("utf-8")).hexdigest()

            try:
                from app.services.aadhaar_verification_service import AadhaarVerificationService
                verhoeff_valid = AadhaarVerificationService.validate_verhoeff(raw_aadhaar)
                if verhoeff_valid:
                    aadhaar_auto_status = "UNVERIFIED"
                    aadhaar_verification_details = json.dumps({
                        "verhoeff_passed": True,
                        "auto_status": "UNVERIFIED",
                        "confidence_score": 0.40,
                        "audit_reasons": ["12-digit Aadhaar number passed Verhoeff checksum algorithm."]
                    })
                else:
                    aadhaar_auto_status = "INVALID_NOT_AADHAAR"
                    aadhaar_verification_details = json.dumps({
                        "verhoeff_passed": False,
                        "auto_status": "INVALID_NOT_AADHAAR",
                        "confidence_score": 0.0,
                        "audit_reasons": ["12-digit Aadhaar number failed Verhoeff checksum algorithm."]
                    })
            except Exception as e:
                aadhaar_auto_status = "UNVERIFIED"
                aadhaar_verification_details = json.dumps({
                    "verhoeff_passed": False,
                    "auto_status": "UNVERIFIED",
                    "error": str(e),
                    "confidence_score": 0.0,
                    "audit_reasons": [f"Automated verification deferred: {str(e)}"]
                })

        db_report = FieldReport(
            report_type=report_in.report_type.value,
            description=report_in.description,
            latitude=report_in.latitude,
            longitude=report_in.longitude,
            reporter_type=report_in.reporter_type.value,
            severity=report_in.severity.value,
            status=ReportStatus.PENDING.value,
            full_name=report_in.full_name.strip() if report_in.full_name else None,
            aadhaar_number=masked_aadhaar,
            aadhaar_hash=aadhaar_hash,
            verification_status="PENDING",
            aadhaar_auto_status=aadhaar_auto_status,
            aadhaar_verification_details=aadhaar_verification_details,
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

        aadhaar_details_dict = None
        if report.aadhaar_verification_details:
            try:
                aadhaar_details_dict = json.loads(report.aadhaar_verification_details)
            except Exception:
                aadhaar_details_dict = None

        prediction_details_dict = None
        if report.prediction_details:
            try:
                prediction_details_dict = json.loads(report.prediction_details)
            except Exception:
                prediction_details_dict = None

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
            full_name=report.full_name,
            aadhaar_number=report.aadhaar_number,
            verification_status=report.verification_status or "PENDING",
            verification_note=report.verification_note,
            verified_by=report.verified_by,
            verified_at=report.verified_at,
            has_aadhaar_card=bool(report.aadhaar_card_path and os.path.exists(report.aadhaar_card_path)),
            has_aadhaar_qr=bool(report.aadhaar_qr_path and os.path.exists(report.aadhaar_qr_path)),
            has_jio_tag_image=bool(report.jio_tag_image_path),
            jio_tag_image_url=report.jio_tag_image_path,
            aadhaar_auto_status=report.aadhaar_auto_status or "UNVERIFIED",
            aadhaar_verification_details=aadhaar_details_dict,
            jio_tag_latitude=report.jio_tag_latitude,
            jio_tag_longitude=report.jio_tag_longitude,
            jio_tag_altitude=report.jio_tag_altitude,
            jio_tag_captured_at=report.jio_tag_captured_at,
            visual_hazard_score=report.visual_hazard_score,
            predicted_risk_score=report.predicted_risk_score,
            prediction_details=prediction_details_dict,
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
                exif_consistency_summary=exif_summary,
                full_name=r.full_name,
                aadhaar_number=r.aadhaar_number,
                verification_status=r.verification_status or "PENDING",
                verification_note=r.verification_note,
                has_aadhaar_card=bool(r.aadhaar_card_path),
                has_aadhaar_qr=bool(r.aadhaar_qr_path),
                has_jio_tag_image=bool(r.jio_tag_image_path),
                aadhaar_auto_status=r.aadhaar_auto_status or "UNVERIFIED",
                predicted_risk_score=r.predicted_risk_score,
                visual_hazard_score=r.visual_hazard_score
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

    @classmethod
    async def save_verification_documents(
        cls,
        db: Session,
        report_id: int,
        jio_tag_file: Optional[UploadFile] = None,
        aadhaar_card_file: Optional[UploadFile] = None,
        aadhaar_qr_file: Optional[UploadFile] = None
    ) -> FieldReport:
        """
        Processes and stores Jio Tag evidence and private Aadhaar documents.
        Aadhaar documents are strictly stored in private data/secure_documents/
        and are never exposed as public static files.
        """
        report = db.query(FieldReport).filter(FieldReport.id == report_id).first()
        if not report:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Field report with ID {report_id} not found."
            )

        _ensure_secure_docs_dir()
        secure_report_dir = os.path.join(SECURE_DOCS_ROOT, f"report_{report_id}")
        os.makedirs(secure_report_dir, exist_ok=True)

        async def _validate_and_read(file: UploadFile, label: str) -> Tuple[bytes, str]:
            file_bytes = await file.read(MAX_DOC_SIZE_BYTES + 1)
            if len(file_bytes) > MAX_DOC_SIZE_BYTES:
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail=f"{label} file size exceeds 10 MB limit."
                )
            if len(file_bytes) == 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"{label} uploaded file is empty."
                )
            try:
                test_img = Image.open(io.BytesIO(file_bytes))
                test_img.verify()
            except Exception:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"{label} is an invalid or corrupted image."
                )
            try:
                img = Image.open(io.BytesIO(file_bytes))
                fmt = (img.format or "").upper()
                if fmt not in ALLOWED_DOC_FORMATS:
                    raise HTTPException(
                        status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                        detail=f"{label} format '{fmt}' is not supported. Use JPEG, PNG, or WebP."
                    )
                mime, ext = ALLOWED_DOC_FORMATS[fmt]
                return file_bytes, ext
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Failed to read {label}: {str(e)}")

        # 1. Process Jio Tag photo if provided
        jio_tag_saved_path = None
        if jio_tag_file and jio_tag_file.filename:
            media_resp = await FieldReportMediaService.process_and_save_media(
                db=db,
                report_id=report_id,
                file=jio_tag_file
            )
            report.jio_tag_image_path = media_resp.media_url
            jio_tag_saved_path = os.path.join(MEDIA_ROOT_DIR, f"report_{report_id}", media_resp.stored_filename)

        # 2. Process Aadhaar Card if provided
        if aadhaar_card_file and aadhaar_card_file.filename:
            card_bytes, card_ext = await _validate_and_read(aadhaar_card_file, "Aadhaar Card")
            card_filename = f"card_{uuid.uuid4().hex}{card_ext}"
            card_path = os.path.join(secure_report_dir, card_filename)
            with open(card_path, "wb") as f:
                f.write(card_bytes)
            report.aadhaar_card_path = card_path

        # 3. Process Aadhaar QR code if provided
        if aadhaar_qr_file and aadhaar_qr_file.filename:
            qr_bytes, qr_ext = await _validate_and_read(aadhaar_qr_file, "Aadhaar QR")
            qr_filename = f"qr_{uuid.uuid4().hex}{qr_ext}"
            qr_path = os.path.join(secure_report_dir, qr_filename)
            with open(qr_path, "wb") as f:
                f.write(qr_bytes)
            report.aadhaar_qr_path = qr_path

        # 4. Automated Aadhaar Verification & AI Inspection
        if report.aadhaar_card_path or report.aadhaar_qr_path or report.aadhaar_number:
            try:
                from app.services.aadhaar_verification_service import AadhaarVerificationService
                aadhaar_verif = AadhaarVerificationService.verify_aadhaar_evidence(
                    aadhaar_number=report.aadhaar_number,
                    full_name=report.full_name,
                    card_image_path=report.aadhaar_card_path,
                    qr_image_path=report.aadhaar_qr_path
                )
                report.aadhaar_auto_status = aadhaar_verif.get("auto_status", "UNVERIFIED")
                report.aadhaar_verification_details = json.dumps(aadhaar_verif)
            except Exception:
                pass

        # 5. Jio Tag Telemetry & Landslide Risk Prediction
        if not jio_tag_saved_path and report.jio_tag_image_path:
            url_suffix = report.jio_tag_image_path.replace("/static/media/field_reports/", "").strip("/\\")
            cand_path = os.path.join(MEDIA_ROOT_DIR, url_suffix)
            if os.path.exists(cand_path):
                jio_tag_saved_path = cand_path

        if jio_tag_saved_path and os.path.exists(jio_tag_saved_path):
            try:
                from app.services.jio_tag_prediction_service import JioTagPredictionService
                prediction = JioTagPredictionService.extract_and_predict(
                    db=db,
                    image_path=jio_tag_saved_path,
                    fallback_lat=report.latitude,
                    fallback_lon=report.longitude
                )
                report.jio_tag_latitude = prediction.get("target_coordinates", {}).get("latitude")
                report.jio_tag_longitude = prediction.get("target_coordinates", {}).get("longitude")
                report.jio_tag_altitude = prediction.get("target_coordinates", {}).get("altitude")
                captured_at_str = prediction.get("telemetry", {}).get("captured_at")
                if captured_at_str:
                    try:
                        report.jio_tag_captured_at = datetime.fromisoformat(captured_at_str)
                    except Exception:
                        pass
                report.visual_hazard_score = prediction.get("visual_features", {}).get("visual_hazard_score")
                report.predicted_risk_score = prediction.get("calibrated_risk_score")
                report.prediction_details = json.dumps(prediction)
            except Exception:
                pass

        report.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(report)
        return report

    @classmethod
    def run_ai_analysis(cls, db: Session, report_id: int) -> Optional[FieldReportDetailResponse]:
        """
        Executes automated Aadhaar verification inspection and Jio Tag predictive modeling
        for a given field report. If no dedicated Jio Tag was provided, analyzes the first attached media photo.
        """
        report = db.query(FieldReport).filter(FieldReport.id == report_id).first()
        if not report:
            return None

        # 1. Run Aadhaar Verification if identity fields exist
        if report.aadhaar_card_path or report.aadhaar_qr_path or report.aadhaar_number:
            try:
                from app.services.aadhaar_verification_service import AadhaarVerificationService
                aadhaar_verif = AadhaarVerificationService.verify_aadhaar_evidence(
                    aadhaar_number=report.aadhaar_number,
                    full_name=report.full_name,
                    card_image_path=report.aadhaar_card_path,
                    qr_image_path=report.aadhaar_qr_path
                )
                report.aadhaar_auto_status = aadhaar_verif.get("auto_status", "UNVERIFIED")
                report.aadhaar_verification_details = json.dumps(aadhaar_verif)
            except Exception:
                pass

        # 2. Locate hazard image for prediction
        eval_image_path = None
        if report.jio_tag_image_path:
            url_suffix = report.jio_tag_image_path.replace("/static/media/field_reports/", "").strip("/\\")
            cand_path = os.path.join(MEDIA_ROOT_DIR, url_suffix)
            if os.path.exists(cand_path):
                eval_image_path = cand_path

        if not eval_image_path and report.media:
            first_m = report.media[0]
            cand_path = os.path.join(MEDIA_ROOT_DIR, f"report_{report_id}", first_m.stored_filename)
            if os.path.exists(cand_path):
                eval_image_path = cand_path

        if eval_image_path and os.path.exists(eval_image_path):
            try:
                from app.services.jio_tag_prediction_service import JioTagPredictionService
                prediction = JioTagPredictionService.extract_and_predict(
                    db=db,
                    image_path=eval_image_path,
                    fallback_lat=report.latitude,
                    fallback_lon=report.longitude
                )
                report.jio_tag_latitude = prediction.get("target_coordinates", {}).get("latitude")
                report.jio_tag_longitude = prediction.get("target_coordinates", {}).get("longitude")
                report.jio_tag_altitude = prediction.get("target_coordinates", {}).get("altitude")
                captured_at_str = prediction.get("telemetry", {}).get("captured_at")
                if captured_at_str:
                    try:
                        report.jio_tag_captured_at = datetime.fromisoformat(captured_at_str)
                    except Exception:
                        pass
                report.visual_hazard_score = prediction.get("visual_features", {}).get("visual_hazard_score")
                report.predicted_risk_score = prediction.get("calibrated_risk_score")
                report.prediction_details = json.dumps(prediction)
            except Exception:
                pass

        report.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(report)
        return cls.get_report_detail(db=db, report_id=report_id)

    @classmethod
    def get_secure_document_path(cls, db: Session, report_id: int, doc_type: str) -> Optional[str]:
        """
        Retrieves the absolute filesystem path for private Aadhaar documents.
        Enforces that only 'card' and 'qr' types are permitted.
        """
        report = db.query(FieldReport).filter(FieldReport.id == report_id).first()
        if not report:
            return None

        clean_type = (doc_type or "").strip().lower()
        if clean_type == "card":
            path = report.aadhaar_card_path
        elif clean_type == "qr":
            path = report.aadhaar_qr_path
        else:
            return None

        if path and os.path.exists(path):
            return path
        return None

    @classmethod
    def update_admin_verification(
        cls,
        db: Session,
        report_id: int,
        verification_status: str,
        verification_note: Optional[str] = None,
        verified_by: Optional[str] = None
    ) -> Tuple[FieldReport, bool]:
        """
        Updates manual admin verification status for Aadhaar and Jio Tag evidence.
        Accepts VERIFIED, REJECTED, or RE_UPLOAD_REQUIRED.
        Synchronizes with report operational status and determines if regional alert is warranted.
        """
        report = db.query(FieldReport).filter(FieldReport.id == report_id).first()
        if not report:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Field report with ID {report_id} not found."
            )

        valid_statuses = {"VERIFIED", "REJECTED", "RE_UPLOAD_REQUIRED"}
        clean_status = (verification_status or "").strip().upper()
        if clean_status not in valid_statuses:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid verification status '{verification_status}'. Must be one of: {', '.join(valid_statuses)}."
            )

        was_already_verified = (
            report.status == ReportStatus.VERIFIED.value
            if isinstance(report.status, str)
            else getattr(report.status, "value", str(report.status)) == ReportStatus.VERIFIED.value
        )

        report.verification_status = clean_status
        if verification_note is not None:
            report.verification_note = verification_note.strip()
        if verified_by:
            report.verified_by = verified_by
        report.verified_at = datetime.utcnow()
        report.updated_at = datetime.utcnow()

        became_verified = False
        if clean_status == "VERIFIED":
            report.status = ReportStatus.VERIFIED.value
            if not was_already_verified:
                became_verified = True
        elif clean_status == "REJECTED":
            report.status = ReportStatus.REJECTED.value
        elif clean_status == "RE_UPLOAD_REQUIRED":
            if report.status == ReportStatus.PENDING.value:
                report.status = ReportStatus.UNDER_REVIEW.value

        db.commit()
        db.refresh(report)
        return report, became_verified
