"""
Field Report Spatial Service - Phase 7 Checkpoint 16.3

Provides spatial query capabilities, deterministic duplicate/cluster detection,
field intelligence summaries, and GeoJSON map exports for field hazard reports.
"""

import math
from typing import List, Optional, Dict, Any, Tuple, Set
from collections import defaultdict
from sqlalchemy.orm import Session

from app.models.field_report import FieldReport
from app.models.field_report_media import FieldReportMedia
from app.services.aoi_service import is_inside_ner
from app.schemas.field_report import (
    ReportStatus,
    ReportType,
    ReportSeverity,
    ObservationStatus,
    EvidenceConfidence,
    NearbyFieldReportResponse,
    FieldIntelligenceSummaryResponse,
    EnvironmentalContextSummary
)

EARTH_RADIUS_KM = 6371.0088
DEFAULT_DUPLICATE_RADIUS_KM = 0.5  # 500 meters threshold for identical hazard type

def calculate_bounding_box(latitude: float, longitude: float, radius_km: float) -> Tuple[float, float, float, float]:
    """
    Calculates bounding box coordinates [min_lat, max_lat, min_lon, max_lon]
    around a center point for indexed B-tree database pre-filtering.
    """
    lat_degree_km = 111.1
    delta_lat = radius_km / lat_degree_km
    
    lat_rad = math.radians(latitude)
    cos_lat = math.cos(lat_rad)
    delta_lng = radius_km / (lat_degree_km * cos_lat) if cos_lat > 0.0001 else radius_km / lat_degree_km

    return latitude - delta_lat, latitude + delta_lat, longitude - delta_lng, longitude + delta_lng

def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculates great-circle geodesic distance between two points in kilometers.
    """
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    
    a = math.sin(delta_phi / 2.0)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0)**2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    
    return EARTH_RADIUS_KM * c

def get_evidence_semantics(status_str: str) -> Tuple[ObservationStatus, EvidenceConfidence]:
    """
    Determines observation category and evidence confidence rating based on verification status.
    """
    if status_str == ReportStatus.VERIFIED.value:
        return ObservationStatus.VERIFIED_OBSERVATION, EvidenceConfidence.CONFIRMED
    elif status_str == ReportStatus.UNDER_REVIEW.value:
        return ObservationStatus.UNVERIFIED_OBSERVATION, EvidenceConfidence.REVIEW_PENDING
    elif status_str == ReportStatus.REJECTED.value:
        return ObservationStatus.REJECTED, EvidenceConfidence.REJECTED
    else:  # PENDING
        return ObservationStatus.UNVERIFIED_OBSERVATION, EvidenceConfidence.UNVERIFIED

class FieldReportSpatialService:
    @staticmethod
    def detect_spatial_duplicates(
        reports: List[FieldReport],
        threshold_km: float = DEFAULT_DUPLICATE_RADIUS_KM
    ) -> Dict[int, List[int]]:
        """
        Deterministic spatial duplicate detector.
        Identifies pairs of reports sharing the same report_type within the threshold distance.
        Returns a mapping from report_id to a list of related duplicate report IDs.
        """
        duplicates_map: Dict[int, List[int]] = defaultdict(list)
        n = len(reports)
        for i in range(n):
            for j in range(i + 1, n):
                r1 = reports[i]
                r2 = reports[j]
                if r1.report_type == r2.report_type:
                    dist = haversine_distance(r1.latitude, r1.longitude, r2.latitude, r2.longitude)
                    if dist <= threshold_km:
                        duplicates_map[r1.id].append(r2.id)
                        duplicates_map[r2.id].append(r1.id)
        return duplicates_map

    @classmethod
    def get_nearby_reports(
        cls,
        db: Session,
        latitude: float,
        longitude: float,
        radius_km: float = 5.0,
        status: Optional[ReportStatus] = None,
        report_type: Optional[ReportType] = None,
        severity: Optional[ReportSeverity] = None
    ) -> List[NearbyFieldReportResponse]:
        """
        Finds all field reports within the specified radius_km of coordinates.
        Applies bounding box pre-filtering followed by exact Haversine distance calculation.
        """
        min_lat, max_lat, min_lon, max_lon = calculate_bounding_box(latitude, longitude, radius_km)

        query = db.query(FieldReport).filter(
            FieldReport.latitude.between(min_lat, max_lat),
            FieldReport.longitude.between(min_lon, max_lon)
        )

        if status:
            query = query.filter(FieldReport.status == status.value)
        if report_type:
            query = query.filter(FieldReport.report_type == report_type.value)
        if severity:
            query = query.filter(FieldReport.severity == severity.value)

        candidates = query.all()

        # Exact distance filtering
        matched_items: List[Tuple[FieldReport, float]] = []
        for r in candidates:
            dist = haversine_distance(latitude, longitude, r.latitude, r.longitude)
            if dist <= radius_km:
                matched_items.append((r, dist))

        # Sort by distance ascending
        matched_items.sort(key=lambda x: x[1])
        matched_reports = [item[0] for item in matched_items]

        # Detect spatial duplicates among matched reports
        duplicates_map = cls.detect_spatial_duplicates(matched_reports)

        results: List[NearbyFieldReportResponse] = []
        for r, dist in matched_items:
            obs_status, ev_conf = get_evidence_semantics(r.status)
            related_ids = duplicates_map.get(r.id, [])
            results.append(
                NearbyFieldReportResponse(
                    id=r.id,
                    report_type=r.report_type,
                    description=r.description,
                    latitude=r.latitude,
                    longitude=r.longitude,
                    reporter_type=r.reporter_type,
                    severity=r.severity,
                    status=r.status,
                    created_at=r.created_at,
                    distance_km=round(dist, 3),
                    media_count=len(r.media) if r.media else 0,
                    potential_duplicate=len(related_ids) > 0,
                    related_report_ids=related_ids,
                    observation_status=obs_status,
                    evidence_confidence=ev_conf
                )
            )

        return results

    @classmethod
    def generate_intelligence_summary(
        cls,
        db: Session,
        latitude: float,
        longitude: float,
        radius_km: float = 5.0
    ) -> FieldIntelligenceSummaryResponse:
        """
        Generates an aggregated observational intelligence summary for the AOI.
        """
        nearby_reports = cls.get_nearby_reports(
            db=db,
            latitude=latitude,
            longitude=longitude,
            radius_km=radius_km
        )

        total_reports = len(nearby_reports)
        pending_count = 0
        under_review_count = 0
        verified_count = 0
        rejected_count = 0

        type_counts = {t.value: 0 for t in ReportType}
        severity_counts = {s.value: 0 for s in ReportSeverity}

        reports_with_media = 0
        reports_without_media = 0
        reports_with_exif = 0

        cluster_ids: Set[int] = set()

        for r in nearby_reports:
            # Status counts
            if r.status == ReportStatus.PENDING:
                pending_count += 1
            elif r.status == ReportStatus.UNDER_REVIEW:
                under_review_count += 1
            elif r.status == ReportStatus.VERIFIED:
                verified_count += 1
            elif r.status == ReportStatus.REJECTED:
                rejected_count += 1

            # Type breakdown
            type_counts[r.report_type.value] = type_counts.get(r.report_type.value, 0) + 1

            # Severity breakdown
            severity_counts[r.severity.value] = severity_counts.get(r.severity.value, 0) + 1

            # Media statistics
            if r.media_count > 0:
                reports_with_media += 1
                # Check if any media item for this report has EXIF GPS
                db_media = db.query(FieldReportMedia).filter(FieldReportMedia.report_id == r.id).all()
                if any(m.exif_latitude is not None for m in db_media):
                    reports_with_exif += 1
            else:
                reports_without_media += 1

            # Duplicate cluster tracking
            if r.potential_duplicate:
                cluster_ids.add(r.id)

        # Environmental risk context (lightweight reference)
        env_context = None
        try:
            from app.services.composite_risk_service import CompositeRiskService
            comp_res = CompositeRiskService.calculate_composite_risk(db=db, latitude=latitude, longitude=longitude)
            env_context = EnvironmentalContextSummary(
                composite_hazard_index=comp_res.get("composite_risk_index"),
                hazard_category=comp_res.get("risk_level"),
                note="Environmental risk model is independent of citizen field reports."
            )
        except Exception:
            env_context = EnvironmentalContextSummary(
                composite_hazard_index=None,
                hazard_category=None,
                note="Environmental context calculation currently unavailable."
            )

        return FieldIntelligenceSummaryResponse(
            coordinates={"latitude": latitude, "longitude": longitude},
            radius_km=radius_km,
            total_reports=total_reports,
            pending_reports=pending_count,
            under_review_reports=under_review_count,
            verified_reports=verified_count,
            rejected_reports=rejected_count,
            verified_observations=verified_count,
            unverified_observations=pending_count + under_review_count,
            report_types_breakdown=type_counts,
            severity_breakdown=severity_counts,
            evidence_statistics={
                "reports_with_media": reports_with_media,
                "reports_without_media": reports_without_media,
                "reports_with_exif_gps": reports_with_exif
            },
            potential_clusters_count=len(cluster_ids),
            environmental_context=env_context
        )

    @classmethod
    def get_geojson_features(
        cls,
        db: Session,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        radius_km: Optional[float] = None,
        status: Optional[ReportStatus] = None,
        report_type: Optional[ReportType] = None,
        severity: Optional[ReportSeverity] = None
    ) -> Dict[str, Any]:
        """
        Produces a standard GIS GeoJSON FeatureCollection.
        Ensures coordinate order is strictly [longitude, latitude] (GeoJSON specification).
        """
        if latitude is not None and longitude is not None and radius_km is not None:
            # Query spatially
            nearby_items = cls.get_nearby_reports(
                db=db,
                latitude=latitude,
                longitude=longitude,
                radius_km=radius_km,
                status=status,
                report_type=report_type,
                severity=severity
            )
            features = []
            for r in nearby_items:
                features.append({
                    "type": "Feature",
                    "geometry": {
                        "type": "Point",
                        "coordinates": [r.longitude, r.latitude]  # [lon, lat] STRICTLY
                    },
                    "properties": {
                        "id": r.id,
                        "report_type": r.report_type.value,
                        "description": r.description,
                        "severity": r.severity.value,
                        "status": r.status.value,
                        "reporter_type": r.reporter_type.value,
                        "created_at": r.created_at.isoformat() if r.created_at else None,
                        "distance_km": r.distance_km,
                        "media_count": r.media_count,
                        "potential_duplicate": r.potential_duplicate,
                        "related_report_ids": r.related_report_ids,
                        "observation_status": r.observation_status.value,
                        "evidence_confidence": r.evidence_confidence.value
                    }
                })
        else:
            # Global listing with optional attribute filters
            query = db.query(FieldReport)
            if status:
                query = query.filter(FieldReport.status == status.value)
            if report_type:
                query = query.filter(FieldReport.report_type == report_type.value)
            if severity:
                query = query.filter(FieldReport.severity == severity.value)
            all_reports = query.order_by(FieldReport.created_at.desc()).all()
            duplicates_map = cls.detect_spatial_duplicates(all_reports)

            features = []
            for r in all_reports:
                obs_status, ev_conf = get_evidence_semantics(r.status)
                related_ids = duplicates_map.get(r.id, [])
                features.append({
                    "type": "Feature",
                    "geometry": {
                        "type": "Point",
                        "coordinates": [r.longitude, r.latitude]  # [lon, lat] STRICTLY
                    },
                    "properties": {
                        "id": r.id,
                        "report_type": r.report_type,
                        "description": r.description,
                        "severity": r.severity,
                        "status": r.status,
                        "reporter_type": r.reporter_type,
                        "created_at": r.created_at.isoformat() if r.created_at else None,
                        "distance_km": None,
                        "media_count": len(r.media) if r.media else 0,
                        "potential_duplicate": len(related_ids) > 0,
                        "related_report_ids": related_ids,
                        "observation_status": obs_status.value,
                        "evidence_confidence": ev_conf.value
                    }
                })

        return {
            "type": "FeatureCollection",
            "features": features
        }
