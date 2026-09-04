"""
Field Intelligence Risk Service - Phase 7 Checkpoint 16.5

Integrates ground-truth field reports into the operational risk assessment pipeline.
Generates structured Ground Observation Signals (Verified signal, Unverified observations,
Spatial clustering, and Recency analysis) without corrupting environmental models.
"""

from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from collections import Counter
from sqlalchemy.orm import Session

from app.models.field_report import FieldReport
from app.services.aoi_service import is_inside_ner
from app.services.field_report_spatial_service import (
    FieldReportSpatialService,
    calculate_bounding_box,
    haversine_distance
)
from app.schemas.field_report import (
    ReportStatus,
    ReportType,
    ReportSeverity,
    FieldIntelligenceStatus,
    VerifiedGroundSignalDetails,
    UnverifiedObservationsDetails,
    ClusterAnalysisDetails,
    RecencyAnalysisDetails,
    FieldIntelligenceRiskSignalResponse
)

# =========================================================================
# Deterministic Scientific & Operational Weights
# =========================================================================

SEVERITY_WEIGHTS = {
    ReportSeverity.LOW.value: 1,
    ReportSeverity.MEDIUM.value: 2,
    ReportSeverity.HIGH.value: 3,
    ReportSeverity.CRITICAL.value: 4,
}

REPORT_TYPE_WEIGHTS = {
    ReportType.CRACK.value: 2,
    ReportType.SLOPE_MOVEMENT.value: 4,
    ReportType.BLOCKED_ROAD.value: 2,
    ReportType.LANDSLIDE.value: 5,
    ReportType.DEBRIS.value: 3,
    ReportType.OTHER.value: 1,
}

class FieldIntelligenceRiskService:
    @classmethod
    def analyze_ground_risk_signal(
        cls,
        db: Session,
        latitude: float,
        longitude: float,
        radius_km: float = 5.0
    ) -> FieldIntelligenceRiskSignalResponse:
        """
        Evaluates field intelligence observations within radius_km of coordinates.
        Produces separate Verified, Unverified, Cluster, and Recency signals.
        """
        # 1. Bounds and NER verification
        if not (-90.0 <= latitude <= 90.0) or not (-180.0 <= longitude <= 180.0):
            raise ValueError(f"Invalid coordinates: ({latitude}, {longitude})")
        if radius_km < 0.1 or radius_km > 100.0:
            raise ValueError(f"Radius must be between 0.1 and 100.0 km. Got: {radius_km}")
        if not is_inside_ner(latitude, longitude):
            raise ValueError("Target coordinates must lie within India's North Eastern Region.")

        # 2. Query spatial bounding box and filter by geodesic Haversine distance
        min_lat, max_lat, min_lon, max_lon = calculate_bounding_box(latitude, longitude, radius_km)
        candidates = db.query(FieldReport).filter(
            FieldReport.latitude.between(min_lat, max_lat),
            FieldReport.longitude.between(min_lon, max_lon)
        ).all()

        nearby_reports: List[FieldReport] = []
        for r in candidates:
            dist = haversine_distance(latitude, longitude, r.latitude, r.longitude)
            if dist <= radius_km:
                nearby_reports.append(r)

        # 3. Separate Verified from Unverified Observations
        verified_reports: List[FieldReport] = []
        unverified_reports: List[FieldReport] = []
        rejected_count = 0

        for r in nearby_reports:
            status_val = r.status.value if hasattr(r.status, 'value') else str(r.status)
            if status_val == ReportStatus.VERIFIED.value:
                verified_reports.append(r)
            elif status_val in [ReportStatus.PENDING.value, ReportStatus.UNDER_REVIEW.value]:
                unverified_reports.append(r)
            elif status_val == ReportStatus.REJECTED.value:
                rejected_count += 1

        # 4. Verified Ground Signal Scoring Formula
        # Formula:
        # Each verified report i has weight = SEVERITY_WEIGHT(sev_i) * TYPE_WEIGHT(type_i)
        # raw_verified_score = sum(weight_i)
        # normalized_verified_score = min(100.0, raw_verified_score * 5.0)
        # (e.g. 1 Critical Landslide = 4*5 = 20 -> 20*5 = 100.0; 1 High Crack = 3*2 = 6 -> 30.0)
        raw_verified_score = 0.0
        verified_high_count = 0
        verified_critical_count = 0

        for r in verified_reports:
            sev_str = r.severity.value if hasattr(r.severity, 'value') else str(r.severity)
            type_str = r.report_type.value if hasattr(r.report_type, 'value') else str(r.report_type)
            
            s_weight = SEVERITY_WEIGHTS.get(sev_str, 2)
            t_weight = REPORT_TYPE_WEIGHTS.get(type_str, 1)
            raw_verified_score += (s_weight * t_weight)

            if sev_str == ReportSeverity.HIGH.value:
                verified_high_count += 1
            elif sev_str == ReportSeverity.CRITICAL.value:
                verified_critical_count += 1

        verified_score = round(min(100.0, raw_verified_score * 5.0), 2)

        # 5. Unverified Observations Analysis
        pending_count = 0
        under_review_count = 0
        unverified_high_priority_count = 0

        for r in unverified_reports:
            status_str = r.status.value if hasattr(r.status, 'value') else str(r.status)
            sev_str = r.severity.value if hasattr(r.severity, 'value') else str(r.severity)

            if status_str == ReportStatus.PENDING.value:
                pending_count += 1
            elif status_str == ReportStatus.UNDER_REVIEW.value:
                under_review_count += 1

            if sev_str in [ReportSeverity.HIGH.value, ReportSeverity.CRITICAL.value]:
                unverified_high_priority_count += 1

        # 6. Spatial Cluster / Duplicate Detection
        duplicates_map = FieldReportSpatialService.detect_spatial_duplicates(nearby_reports)
        clustered_ids = set()
        clustered_types = set()

        for r in nearby_reports:
            if r.id in duplicates_map and len(duplicates_map[r.id]) > 0:
                clustered_ids.add(r.id)
                type_str = r.report_type.value if hasattr(r.report_type, 'value') else str(r.report_type)
                clustered_types.add(type_str)

        potential_cluster_detected = len(clustered_ids) > 0
        cluster_report_count = len(clustered_ids)
        cluster_types_list = sorted(list(clustered_types))

        # 7. Recency Analysis (Buckets: 0-24h, 1-3d, 3-7d, >7d)
        now_dt = datetime.now(timezone.utc).replace(tzinfo=None)
        very_recent_count = 0
        recent_count = 0
        aging_count = 0
        historical_count = 0

        for r in nearby_reports:
            if r.created_at:
                # Ensure naive UTC comparison
                r_dt = r.created_at.replace(tzinfo=None) if r.created_at.tzinfo else r.created_at
                age_seconds = max(0, (now_dt - r_dt).total_seconds())
                age_days = age_seconds / 86400.0

                if age_days <= 1.0:
                    very_recent_count += 1
                elif age_days <= 3.0:
                    recent_count += 1
                elif age_days <= 7.0:
                    aging_count += 1
                else:
                    historical_count += 1

        # 8. Dominant Observation Types
        type_counts = Counter(
            (r.report_type.value if hasattr(r.report_type, 'value') else str(r.report_type))
            for r in nearby_reports
        )
        dominant_types = [t for t, _ in type_counts.most_common(3)]

        # 9. Field Intelligence Categorical Status & Operational Message
        total_reports_count = len(nearby_reports)
        status = FieldIntelligenceStatus.NORMAL
        operational_msg = "No ground hazard observations recorded in the target Area of Interest."

        if verified_critical_count >= 1 or verified_score >= 60.0 or (len(verified_reports) >= 2 and (verified_high_count + verified_critical_count) >= 2):
            status = FieldIntelligenceStatus.CRITICAL_GROUND_ALERT
            operational_msg = (
                f"CRITICAL GROUND ALERT: Verified critical field observations detected within {radius_km} km "
                f"(Verified Signal Score: {verified_score}/100). Immediate on-site response prioritization required."
            )
        elif len(verified_reports) >= 1 and (verified_score >= 20.0 or verified_high_count >= 1):
            status = FieldIntelligenceStatus.VERIFIED_GROUND_HAZARD
            operational_msg = (
                f"VERIFIED GROUND HAZARD: Confirmed field hazard evidence in the AOI (Verified Signal Score: {verified_score}/100). "
                f"Increased operational monitoring advised."
            )
        elif potential_cluster_detected or len(unverified_reports) >= 2 or unverified_high_priority_count >= 1:
            status = FieldIntelligenceStatus.MULTIPLE_OBSERVATIONS
            if potential_cluster_detected:
                operational_msg = (
                    f"MULTIPLE OBSERVATIONS: Localized hazard cluster detected ({cluster_report_count} reports of type {cluster_types_list}). "
                    f"Awaiting ground verification."
                )
            else:
                operational_msg = (
                    f"MULTIPLE OBSERVATIONS: {len(unverified_reports)} unverified reports received in this AOI. "
                    f"Field team inspection recommended."
                )
        elif total_reports_count >= 1:
            status = FieldIntelligenceStatus.OBSERVATION_REPORTED
            operational_msg = (
                f"OBSERVATION REPORTED: Isolated unverified observation received in the AOI. Under operational triage."
            )

        return FieldIntelligenceRiskSignalResponse(
            location={"latitude": latitude, "longitude": longitude},
            search_radius_km=radius_km,
            field_intelligence_status=status,
            verified_ground_signal=VerifiedGroundSignalDetails(
                score=verified_score,
                verified_reports=len(verified_reports),
                high_severity_reports=verified_high_count,
                critical_reports=verified_critical_count
            ),
            unverified_observations=UnverifiedObservationsDetails(
                pending_reports=pending_count,
                under_review_reports=under_review_count,
                high_priority_reports=unverified_high_priority_count
            ),
            cluster_analysis=ClusterAnalysisDetails(
                potential_cluster_detected=potential_cluster_detected,
                cluster_report_count=cluster_report_count,
                cluster_types=cluster_types_list
            ),
            recency=RecencyAnalysisDetails(
                very_recent=very_recent_count,
                recent=recent_count,
                aging=aging_count,
                historical=historical_count
            ),
            dominant_observation_types=dominant_types,
            operational_message=operational_msg,
            disclaimer="Field intelligence is treated as observational evidence and does not replace environmental hazard models."
        )
