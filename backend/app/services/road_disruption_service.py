"""
Road Disruption Intelligence Service - Phase 8 Checkpoint 17.3

Consumes road connectivity data and Field Intelligence evidence to synthesize
area-level disruption severity, prioritized road impact rankings, and hazard breakdowns.
"""

import logging
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session

from app.models.field_report import FieldReport
from app.schemas.infrastructure import (
    RoadConnectivityStatus,
    DisruptionSeverityStatus,
    DisruptionPriorityLevel,
    PriorityRoadImpactItem,
    RoadCountsSummary,
    RoadDisruptionSummaryResponse,
    NearbyRoadsResponse
)
from app.services.road_connectivity_service import RoadConnectivityService

logger = logging.getLogger(__name__)

STANDARD_HAZARD_TYPES = [
    "CRACK",
    "SLOPE_MOVEMENT",
    "BLOCKED_ROAD",
    "LANDSLIDE",
    "DEBRIS",
    "OTHER"
]

class RoadDisruptionService:
    @classmethod
    def generate_disruption_summary(
        cls,
        db: Session,
        latitude: float,
        longitude: float,
        radius_km: float = 5.0,
        mock_raw_roads: Optional[Dict[str, Any]] = None
    ) -> RoadDisruptionSummaryResponse:
        """
        Synthesizes an area-level operational road disruption intelligence summary.
        """
        # Fetch analyzed roads and connectivity classifications
        nearby_response: NearbyRoadsResponse = RoadConnectivityService.analyze_nearby_roads(
            db=db,
            latitude=latitude,
            longitude=longitude,
            radius_km=radius_km,
            mock_raw_roads=mock_raw_roads
        )

        counts = nearby_response.connectivity_summary
        road_counts = RoadCountsSummary(
            total=nearby_response.total_roads,
            normal=counts.normal,
            monitor=counts.monitor,
            at_risk=counts.at_risk,
            blocked=counts.blocked,
            severely_impacted=counts.severely_impacted
        )

        affected_roads = counts.at_risk + counts.blocked + counts.severely_impacted
        monitored_roads = counts.monitor

        # Area-Level Disruption Severity Hierarchy
        # 1. CRITICAL_DISRUPTION: >= 1 SEVERELY_IMPACTED road
        # 2. HIGH_DISRUPTION: >= 1 BLOCKED road OR >= 2 affected roads
        # 3. ELEVATED_DISRUPTION: >= 1 AT_RISK road
        # 4. MONITORING_REQUIRED: >= 1 MONITOR road (0 confirmed affected)
        # 5. NORMAL: no disruption or monitor evidence

        if counts.severely_impacted >= 1:
            disruption_status = DisruptionSeverityStatus.CRITICAL_DISRUPTION
            operational_message = (
                "CRITICAL DISRUPTION: Severe verified road impacts detected within the Area of Interest. "
                "Immediate operational assessment and emergency response prioritization recommended."
            )
        elif counts.blocked >= 1 or affected_roads >= 2:
            disruption_status = DisruptionSeverityStatus.HIGH_DISRUPTION
            operational_message = (
                "HIGH DISRUPTION: Confirmed road blockage or multiple significant road corridor impacts. "
                "High operational prioritization required for road clearance and traffic management."
            )
        elif counts.at_risk >= 1:
            disruption_status = DisruptionSeverityStatus.ELEVATED_DISRUPTION
            operational_message = (
                "ELEVATED DISRUPTION: Verified ground hazards are affecting one or more road corridors. "
                "Precautionary monitoring and field inspection advised."
            )
        elif monitored_roads >= 1:
            disruption_status = DisruptionSeverityStatus.MONITORING_REQUIRED
            operational_message = (
                "MONITORING REQUIRED: Unverified citizen observations are located near road corridors and require field triage."
            )
        else:
            disruption_status = DisruptionSeverityStatus.NORMAL
            operational_message = (
                "NORMAL: No evidence-based road disruption detected within the analysis area."
            )

        # Operational Priority Engine for Disrupted Roads
        # Only SEVERELY_IMPACTED, BLOCKED, AT_RISK enter priority list
        confirmed_affected_roads = [
            r for r in nearby_response.roads 
            if r.connectivity_status in [
                RoadConnectivityStatus.SEVERELY_IMPACTED,
                RoadConnectivityStatus.BLOCKED,
                RoadConnectivityStatus.AT_RISK
            ]
        ]

        def priority_sort_key(road):
            # Priority Weight: SEVERELY_IMPACTED (3) > BLOCKED (2) > AT_RISK (1)
            tier_weight = 1
            if road.connectivity_status == RoadConnectivityStatus.SEVERELY_IMPACTED:
                tier_weight = 3
            elif road.connectivity_status == RoadConnectivityStatus.BLOCKED:
                tier_weight = 2

            verified = road.impact_evidence.verified_reports
            dist = road.nearest_hazard_distance_m if road.nearest_hazard_distance_m is not None else 999999.0
            blocked = road.impact_evidence.blocked_road_reports

            # Sort by: -tier_weight (highest tier first), -verified (most verified reports first), dist (closest hazard first), -blocked
            return (-tier_weight, -verified, dist, -blocked)

        confirmed_affected_roads.sort(key=priority_sort_key)

        priority_items: List[PriorityRoadImpactItem] = []
        for idx, r in enumerate(confirmed_affected_roads, start=1):
            if r.connectivity_status == RoadConnectivityStatus.SEVERELY_IMPACTED:
                p_level = DisruptionPriorityLevel.CRITICAL
            elif r.connectivity_status == RoadConnectivityStatus.BLOCKED:
                p_level = DisruptionPriorityLevel.HIGH
            else:
                p_level = DisruptionPriorityLevel.MEDIUM

            priority_items.append(PriorityRoadImpactItem(
                priority_rank=idx,
                osm_id=r.osm_id,
                road_name=r.name,
                road_ref=r.ref,
                highway_type=r.highway_type,
                connectivity_status=r.connectivity_status,
                disruption_priority=p_level,
                nearest_hazard_distance_m=r.nearest_hazard_distance_m,
                verified_reports=r.impact_evidence.verified_reports,
                blocked_road_reports=r.impact_evidence.blocked_road_reports,
                supporting_report_ids=r.impact_evidence.supporting_report_ids,
                explanation=r.explanation
            ))

        # Monitoring List for unverified roads
        monitored_road_features = [
            r for r in nearby_response.roads
            if r.connectivity_status == RoadConnectivityStatus.MONITOR
        ]
        monitored_road_features.sort(key=lambda r: r.nearest_hazard_distance_m if r.nearest_hazard_distance_m is not None else 999999.0)

        monitoring_items: List[PriorityRoadImpactItem] = []
        for idx, r in enumerate(monitored_road_features, start=1):
            monitoring_items.append(PriorityRoadImpactItem(
                priority_rank=idx,
                osm_id=r.osm_id,
                road_name=r.name,
                road_ref=r.ref,
                highway_type=r.highway_type,
                connectivity_status=r.connectivity_status,
                disruption_priority=DisruptionPriorityLevel.LOW,
                nearest_hazard_distance_m=r.nearest_hazard_distance_m,
                verified_reports=r.impact_evidence.verified_reports,
                blocked_road_reports=r.impact_evidence.blocked_road_reports,
                supporting_report_ids=r.impact_evidence.supporting_report_ids,
                explanation=r.explanation
            ))

        # Aggregate Hazard Impact Breakdown for reports associated with affected & monitored roads
        associated_report_ids = set()
        for p in priority_items:
            associated_report_ids.update(p.supporting_report_ids)
        for m in monitoring_items:
            associated_report_ids.update(m.supporting_report_ids)

        hazard_breakdown = {ht: 0 for ht in STANDARD_HAZARD_TYPES}
        if associated_report_ids:
            reports = db.query(FieldReport).filter(
                FieldReport.id.in_(list(associated_report_ids)),
                FieldReport.status != "REJECTED"
            ).all()

            for rep in reports:
                rtype = str(rep.report_type).upper()
                if rtype in hazard_breakdown:
                    hazard_breakdown[rtype] += 1
                else:
                    hazard_breakdown["OTHER"] += 1

        return RoadDisruptionSummaryResponse(
            location={"latitude": latitude, "longitude": longitude},
            search_radius_km=radius_km,
            road_counts=road_counts,
            affected_roads=affected_roads,
            monitored_roads=monitored_roads,
            disruption_status=disruption_status,
            priority_roads=priority_items,
            monitoring_roads=monitoring_items,
            hazard_impact_breakdown=hazard_breakdown,
            operational_message=operational_message
        )
