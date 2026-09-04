"""
Road Connectivity Intelligence Service - Phase 8 Checkpoint 17.1

Integrates road infrastructure geometries with Field Intelligence hazard reports,
calculates point-to-segment geodesic proximity, and produces explainable,
evidence-based road connectivity classifications.
"""

import math
import logging
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session

from app.models.field_report import FieldReport
from app.schemas.infrastructure import (
    RoadConnectivityStatus,
    RoadFeatureResponse,
    RoadImpactEvidence,
    LineStringGeometry,
    ConnectivitySummaryDetails,
    NearbyRoadsResponse
)
from app.services.road_network_service import RoadNetworkService
from app.services.spatial_query_service import haversine_distance

logger = logging.getLogger(__name__)

# Road impact proximity threshold in meters (1.0 km corridor)
ROAD_IMPACT_CORRIDOR_METERS = 1000.0

def point_to_segment_distance_m(
    p_lat: float,
    p_lon: float,
    a_lon: float,
    a_lat: float,
    b_lon: float,
    b_lat: float
) -> float:
    """
    Computes shortest Euclidean distance in meters from point P to line segment AB
    using local equirectangular projection centered on the segment.
    """
    lat_mid_rad = math.radians((a_lat + b_lat + p_lat) / 3.0)
    cos_lat = math.cos(lat_mid_rad)

    # Origin at Point P (0, 0)
    ax = (a_lon - p_lon) * 111320.0 * cos_lat
    ay = (a_lat - p_lat) * 110540.0

    bx = (b_lon - p_lon) * 111320.0 * cos_lat
    by = (b_lat - p_lat) * 110540.0

    # Vector AB
    abx = bx - ax
    aby = by - ay

    ab_sq = abx * abx + aby * aby
    if ab_sq == 0.0:
        return math.sqrt(ax * ax + ay * ay)

    # Vector AP (which is -A since P is 0,0)
    apx = -ax
    apy = -ay

    # Parameter t of projection onto line segment
    t = (apx * abx + apy * aby) / ab_sq
    t = max(0.0, min(1.0, t))

    closest_x = ax + t * abx
    closest_y = ay + t * aby

    return math.sqrt(closest_x * closest_x + closest_y * closest_y)

def point_to_linestring_distance_m(
    p_lat: float,
    p_lon: float,
    coordinates: List[List[float]]
) -> float:
    """
    Computes the minimum geodesic distance in meters from a point to a GeoJSON LineString
    across all constituent line segments. Coordinates format: [[lon, lat], ...].
    """
    if not coordinates:
        return float('inf')

    if len(coordinates) == 1:
        lon0, lat0 = coordinates[0]
        return haversine_distance(p_lat, p_lon, lat0, lon0) * 1000.0

    min_dist = float('inf')
    for i in range(len(coordinates) - 1):
        a_lon, a_lat = coordinates[i]
        b_lon, b_lat = coordinates[i + 1]
        dist = point_to_segment_distance_m(p_lat, p_lon, a_lon, a_lat, b_lon, b_lat)
        if dist < min_dist:
            min_dist = dist

    return min_dist

class RoadConnectivityService:
    @classmethod
    def evaluate_road_status(
        cls,
        road: Dict[str, Any],
        nearby_reports: List[FieldReport]
    ) -> RoadFeatureResponse:
        """
        Analyzes field intelligence observations in proximity to a road segment
        and determines an explainable connectivity status.
        """
        coords = road.get("geometry", {}).get("coordinates", [])
        osm_id = road.get("osm_id", "unknown")
        name = road.get("name")
        ref = road.get("ref")
        highway_type = road.get("highway_type", "unclassified")

        # Associate non-rejected field reports within impact corridor
        associated_reports: List[Tuple[FieldReport, float]] = []
        for r in nearby_reports:
            # Strictly exclude rejected reports from road impact evaluation
            if str(r.status).upper() == "REJECTED":
                continue

            dist_m = point_to_linestring_distance_m(r.latitude, r.longitude, coords)
            if dist_m <= ROAD_IMPACT_CORRIDOR_METERS:
                associated_reports.append((r, dist_m))

        # Sort associated reports by proximity
        associated_reports.sort(key=lambda item: item[1])

        # Evidence counts
        verified_count = 0
        under_review_count = 0
        pending_count = 0
        blocked_count = 0
        supporting_ids = []
        nearest_hazard_dist = None

        for r, dist_m in associated_reports:
            supporting_ids.append(r.id)
            if nearest_hazard_dist is None or dist_m < nearest_hazard_dist:
                nearest_hazard_dist = round(dist_m, 1)

            st = str(r.status).upper()
            rtype = str(r.report_type).upper()

            if st == "VERIFIED":
                verified_count += 1
            elif st == "UNDER_REVIEW":
                under_review_count += 1
            elif st == "PENDING":
                pending_count += 1

            if rtype == "BLOCKED_ROAD":
                blocked_count += 1

        evidence = RoadImpactEvidence(
            verified_reports=verified_count,
            under_review_reports=under_review_count,
            pending_reports=pending_count,
            blocked_road_reports=blocked_count,
            supporting_report_ids=supporting_ids
        )

        # Classification Hierarchy:
        # 1. BLOCKED: Verified BLOCKED_ROAD report
        # 2. SEVERELY_IMPACTED: Verified HIGH/CRITICAL LANDSLIDE or multiple verified severe hazards
        # 3. AT_RISK: Verified hazard (CRACK, SLOPE_MOVEMENT, DEBRIS, LANDSLIDE) near road
        # 4. MONITOR: Unverified PENDING or UNDER_REVIEW observation near road
        # 5. NORMAL: No active observations within corridor

        verified_severe_landslide = any(
            str(r.status).upper() == "VERIFIED" and
            str(r.report_type).upper() == "LANDSLIDE" and
            str(r.severity).upper() in ["HIGH", "CRITICAL"]
            for r, _ in associated_reports
        )

        verified_blocked_road = any(
            str(r.status).upper() == "VERIFIED" and
            str(r.report_type).upper() == "BLOCKED_ROAD"
            for r, _ in associated_reports
        )

        status = RoadConnectivityStatus.NORMAL
        explanation = "Normal connectivity: No active field hazard observations recorded within 1.0 km of this road segment."

        if verified_blocked_road:
            status = RoadConnectivityStatus.BLOCKED
            top_rep, top_dist = next((r, d) for r, d in associated_reports if str(r.status).upper() == "VERIFIED" and str(r.report_type).upper() == "BLOCKED_ROAD")
            explanation = f"Confirmed blockage: Verified BLOCKED_ROAD report #{top_rep.id} recorded within {round(top_dist)}m of this road segment."

        elif verified_severe_landslide:
            status = RoadConnectivityStatus.SEVERELY_IMPACTED
            top_rep, top_dist = next((r, d) for r, d in associated_reports if str(r.status).upper() == "VERIFIED" and str(r.report_type).upper() == "LANDSLIDE" and str(r.severity).upper() in ["HIGH", "CRITICAL"])
            explanation = f"Severely impacted: Verified {top_rep.severity} landslide observation #{top_rep.id} directly affecting the road corridor within {round(top_dist)}m."

        elif verified_count >= 2 and any(str(r.severity).upper() in ["HIGH", "CRITICAL"] for r, _ in associated_reports if str(r.status).upper() == "VERIFIED"):
            status = RoadConnectivityStatus.SEVERELY_IMPACTED
            explanation = f"Severely impacted: Multiple verified high-severity ground hazards ({verified_count} verified) within the road corridor."

        elif verified_count > 0:
            status = RoadConnectivityStatus.AT_RISK
            top_rep, top_dist = next((r, d) for r, d in associated_reports if str(r.status).upper() == "VERIFIED")
            explanation = f"Road at risk: Verified {top_rep.report_type} hazard report #{top_rep.id} detected {round(top_dist)}m from road infrastructure."

        elif (under_review_count + pending_count) > 0:
            status = RoadConnectivityStatus.MONITOR
            top_rep, top_dist = associated_reports[0]
            explanation = f"Observational monitoring: Unverified field report #{top_rep.id} ({top_rep.status}) submitted {round(top_dist)}m from road. Awaiting field triage."

        return RoadFeatureResponse(
            osm_id=osm_id,
            name=name,
            ref=ref,
            highway_type=highway_type,
            geometry=LineStringGeometry(type="LineString", coordinates=coords),
            connectivity_status=status,
            impact_evidence=evidence,
            nearest_hazard_distance_m=nearest_hazard_dist,
            explanation=explanation
        )

    @classmethod
    def analyze_nearby_roads(
        cls,
        db: Session,
        latitude: float,
        longitude: float,
        radius_km: float = 5.0,
        mock_raw_roads: Optional[Dict[str, Any]] = None
    ) -> NearbyRoadsResponse:
        """
        Retrieves road infrastructure and evaluates connectivity impact against all active Field Reports in the AOI.
        """
        raw_roads = RoadNetworkService.fetch_roads(
            latitude=latitude,
            longitude=longitude,
            radius_km=radius_km,
            mock_raw_data=mock_raw_roads
        )

        # Retrieve all active field reports in the database
        all_reports = db.query(FieldReport).all()

        analyzed_roads: List[RoadFeatureResponse] = []
        normal_count = 0
        monitor_count = 0
        at_risk_count = 0
        blocked_count = 0
        severely_impacted_count = 0

        for road_dict in raw_roads:
            feature_resp = cls.evaluate_road_status(road_dict, all_reports)
            analyzed_roads.append(feature_resp)

            if feature_resp.connectivity_status == RoadConnectivityStatus.NORMAL:
                normal_count += 1
            elif feature_resp.connectivity_status == RoadConnectivityStatus.MONITOR:
                monitor_count += 1
            elif feature_resp.connectivity_status == RoadConnectivityStatus.AT_RISK:
                at_risk_count += 1
            elif feature_resp.connectivity_status == RoadConnectivityStatus.BLOCKED:
                blocked_count += 1
            elif feature_resp.connectivity_status == RoadConnectivityStatus.SEVERELY_IMPACTED:
                severely_impacted_count += 1

        summary = ConnectivitySummaryDetails(
            normal=normal_count,
            monitor=monitor_count,
            at_risk=at_risk_count,
            blocked=blocked_count,
            severely_impacted=severely_impacted_count
        )

        return NearbyRoadsResponse(
            location={"latitude": latitude, "longitude": longitude},
            search_radius_km=radius_km,
            total_roads=len(analyzed_roads),
            connectivity_summary=summary,
            roads=analyzed_roads
        )
