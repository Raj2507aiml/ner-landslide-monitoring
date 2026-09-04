"""
Operational Situation Assessment Service - Phase 8 Checkpoint 17.4

Synthesizes independent situational intelligence from Composite Landslide Risk,
Early Warning, Field Intelligence ground observations, and Road Disruption layers
into an explainable operational decision-support assessment with deterministic priority levels.
"""

import logging
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session

from app.services.aoi_service import is_inside_ner
from app.services.composite_risk_service import CompositeRiskService
from app.services.early_warning_service import EarlyWarningService
from app.services.automatic_satellite_pair_service import AutomaticSatellitePairService
from app.services.field_intelligence_risk_service import FieldIntelligenceRiskService
from app.services.road_disruption_service import RoadDisruptionService
from app.schemas.operational_assessment import (
    OperationalPriorityLevel,
    EnvironmentalContextDetails,
    EarlyWarningContextDetails,
    GroundIntelligenceContextDetails,
    InfrastructureImpactContextDetails,
    OperationalSituationAssessmentResponse
)

logger = logging.getLogger(__name__)

class OperationalAssessmentService:
    @classmethod
    def evaluate_situation_assessment(
        cls,
        db: Session,
        latitude: float,
        longitude: float,
        radius_km: float = 5.0,
        mock_raw_roads: Optional[Dict[str, Any]] = None,
        mock_radar_change_data: Optional[Dict[str, Any]] = None
    ) -> OperationalSituationAssessmentResponse:
        """
        Synthesizes an integrated operational situation assessment across:
        1. Environmental Composite Landslide Risk
        2. Early Warning Decision Engine
        3. Ground-Truth Field Intelligence Signals
        4. Road Network Disruption Intelligence
        """
        # 1. Geographic boundary and radius validation
        if not (-90.0 <= latitude <= 90.0) or not (-180.0 <= longitude <= 180.0):
            raise ValueError(f"Invalid coordinate boundaries: lat={latitude}, lon={longitude}")
        if radius_km < 0.1 or radius_km > 100.0:
            raise ValueError(f"Radius must be between 0.1 and 100.0 km. Got: {radius_km}")
        if not is_inside_ner(latitude, longitude):
            raise ValueError("Target coordinates must lie within India's North Eastern Region.")

        # --- STEP 1: Environmental Hazard Context ---
        try:
            composite_hazard = CompositeRiskService.calculate_composite_risk(
                db=db,
                latitude=latitude,
                longitude=longitude,
                radius_km=radius_km
            )
            env_index = float(composite_hazard.get("composite_risk_index", 0.0))
            env_level = str(composite_hazard.get("risk_level", "Moderate"))
        except Exception as e:
            env_index = 45.0
            env_level = "Moderate"
            composite_hazard = {
                "composite_risk_index": 45.0,
                "risk_level": "Moderate",
                "recommendation": "Maintain routine regional monitoring."
            }

        env_context = EnvironmentalContextDetails(
            composite_risk_index=round(env_index, 2),
            risk_level=env_level
        )

        # --- STEP 2: Ground-Truth Field Intelligence Context ---
        ground_signal = FieldIntelligenceRiskService.analyze_ground_risk_signal(
            db=db,
            latitude=latitude,
            longitude=longitude,
            radius_km=radius_km
        )
        ground_status = ground_signal.field_intelligence_status.value
        verified_reports = ground_signal.verified_ground_signal.verified_reports
        unverified_reports = (
            ground_signal.unverified_observations.pending_reports +
            ground_signal.unverified_observations.under_review_reports
        )
        verified_signal_score = float(ground_signal.verified_ground_signal.score)
        cluster_detected = bool(ground_signal.cluster_analysis.potential_cluster_detected)

        ground_context = GroundIntelligenceContextDetails(
            status=ground_status,
            verified_reports=verified_reports,
            unverified_reports=unverified_reports,
            verified_signal_score=round(verified_signal_score, 2),
            potential_cluster_detected=cluster_detected
        )

        # --- STEP 3: Early Warning Context ---
        if mock_radar_change_data is not None:
            radar_change_data = mock_radar_change_data
        else:
            # Check cached radar analysis first to ensure immediate sub-second response
            radar_change_data = AutomaticSatellitePairService.get_cached_analysis(
                latitude=latitude,
                longitude=longitude,
                radius_km=radius_km
            )

        ew_result = EarlyWarningService.evaluate_warning_status(
            composite_hazard_data=composite_hazard,
            radar_change_data=radar_change_data,
            field_intelligence_signal=ground_signal.dict() if hasattr(ground_signal, 'dict') else None
        )
        warning_level = str(ew_result.get("warning_level", "NORMAL"))
        operational_mode = str(ew_result.get("operational_mode", "METEOROLOGICAL_FALLBACK"))
        ew_recommended_action = str(ew_result.get("recommended_action", "Monitor routine updates."))

        early_warning_context = EarlyWarningContextDetails(
            warning_level=warning_level,
            operational_mode=operational_mode,
            recommended_action=ew_recommended_action
        )

        # --- STEP 4: Road Infrastructure Disruption Context ---
        road_disruption = RoadDisruptionService.generate_disruption_summary(
            db=db,
            latitude=latitude,
            longitude=longitude,
            radius_km=radius_km,
            mock_raw_roads=mock_raw_roads
        )
        disruption_status = road_disruption.disruption_status.value
        affected_roads = road_disruption.affected_roads
        monitored_roads = road_disruption.monitored_roads
        priority_road_count = len(road_disruption.priority_roads)

        infrastructure_context = InfrastructureImpactContextDetails(
            disruption_status=disruption_status,
            affected_roads=affected_roads,
            monitored_roads=monitored_roads,
            priority_road_count=priority_road_count
        )

        # --- STEP 5: Deterministic Operational Priority & Explainable Reasons ---
        # Precedence: CRITICAL_PRIORITY > HIGH_PRIORITY > ATTENTION_REQUIRED > ROUTINE
        priority_reasons: List[str] = []
        is_critical = False

        if warning_level == "CRITICAL":
            is_critical = True
            priority_reasons.append("Early warning level is CRITICAL indicating imminent or extreme landslide hazard conditions.")
        if disruption_status == "CRITICAL_DISRUPTION":
            is_critical = True
            priority_reasons.append("Road disruption status is CRITICAL_DISRUPTION with verified severe road impact/damage.")
        if warning_level == "ALERT" and disruption_status == "HIGH_DISRUPTION":
            is_critical = True
            priority_reasons.append("Concurrent ALERT early warning level and HIGH_DISRUPTION road blockage creates compounding critical operational risk.")

        if is_critical:
            operational_priority = OperationalPriorityLevel.CRITICAL_PRIORITY
            recommended_actions = [
                "Initiate urgent disaster management and emergency authority review.",
                "Prioritize emergency on-site assessment of severely impacted road corridors and vulnerable slopes.",
                "Coordinate with road management and regional emergency response authorities for traffic diversion and hazard mitigation.",
                "Follow official state emergency management protocols and deploy high-frequency monitoring."
            ]
        elif (
            warning_level == "ALERT" or
            disruption_status in ["HIGH_DISRUPTION", "ELEVATED_DISRUPTION"] or
            ground_status in ["HIGH_IMPACT_CLUSTER", "MULTI_SOURCE_HAZARD"] or
            (ground_status == "VERIFIED_HAZARD_CONFIRMED" and (verified_signal_score >= 10.0 or verified_reports >= 2))
        ):
            operational_priority = OperationalPriorityLevel.HIGH_PRIORITY
            if warning_level == "ALERT":
                priority_reasons.append("Early warning level is ALERT indicating significant dynamic triggers on susceptible terrain.")
            if disruption_status == "HIGH_DISRUPTION":
                priority_reasons.append("Road network reports HIGH_DISRUPTION with confirmed road corridor blockages.")
            elif disruption_status == "ELEVATED_DISRUPTION":
                priority_reasons.append("Road network reports ELEVATED_DISRUPTION with active verified ground hazards near road corridors.")
            if ground_status in ["HIGH_IMPACT_CLUSTER", "MULTI_SOURCE_HAZARD"]:
                priority_reasons.append(f"Ground intelligence detects high-impact hazard clustering ({ground_status}).")
            elif ground_status == "VERIFIED_HAZARD_CONFIRMED" and (verified_signal_score >= 10.0 or verified_reports >= 2):
                priority_reasons.append(f"Strong verified ground activity detected ({verified_reports} verified report(s), signal score: {verified_signal_score:.1f}).")

            recommended_actions = [
                "Prioritize field verification of active ground reports and affected road corridors.",
                "Coordinate with local disaster management and public works authorities.",
                "Inspect and secure affected road corridors experiencing blockages or nearby slope movements.",
                "Increase telemetry and observational monitoring frequency."
            ]
        elif (
            warning_level == "WATCH" or
            disruption_status == "MONITORING_REQUIRED" or
            ground_status == "UNVERIFIED_OBSERVATIONS" or
            unverified_reports > 0 or
            (ground_status == "VERIFIED_HAZARD_CONFIRMED" and verified_signal_score < 10.0 and verified_reports < 2)
        ):
            operational_priority = OperationalPriorityLevel.ATTENTION_REQUIRED
            if warning_level == "WATCH":
                priority_reasons.append("Early warning level is WATCH flagging elevated susceptibility or preliminary triggers.")
            if disruption_status == "MONITORING_REQUIRED":
                priority_reasons.append("Road infrastructure reports MONITORING_REQUIRED due to unverified observations near road corridors.")
            if ground_status == "UNVERIFIED_OBSERVATIONS" or unverified_reports > 0:
                priority_reasons.append(f"{unverified_reports} unverified ground observation(s) awaiting field verification.")
            if ground_status == "VERIFIED_HAZARD_CONFIRMED" and verified_signal_score < 10.0 and verified_reports < 2:
                priority_reasons.append(f"Minor verified ground observation noted ({verified_reports} report, signal score: {verified_signal_score:.1f}).")

            recommended_actions = [
                "Increase observation frequency across monitored slopes and road segments.",
                "Review and triage pending citizen ground observations in the review queue.",
                "Monitor flagged road corridors for potential hazard developments.",
                "Check local rainfall telemetry updates."
            ]
        else:
            operational_priority = OperationalPriorityLevel.ROUTINE
            priority_reasons.append("All baseline indicators are normal: Early warning is NORMAL, road corridors are clear, and no active ground hazards reported.")
            recommended_actions = [
                "Continue routine baseline monitoring.",
                "Maintain regular telemetry data feeds and standard observation checks."
            ]

        # --- STEP 6: Synthesize Assessment Summary ---
        assessment_summary = (
            f"Operational situation is assessed as {operational_priority.value}. "
            f"Environmental hazard index is {env_context.composite_risk_index:.1f} ({env_context.risk_level}) with Early Warning level at {early_warning_context.warning_level}. "
            f"Road connectivity status is {infrastructure_context.disruption_status} ({infrastructure_context.affected_roads} affected corridor(s)), "
            f"and ground intelligence indicates {ground_context.status} ({ground_context.verified_reports} verified, {ground_context.unverified_reports} unverified report(s))."
        )

        return OperationalSituationAssessmentResponse(
            location={"latitude": latitude, "longitude": longitude},
            analysis_radius_km=radius_km,
            environmental_context=env_context,
            early_warning=early_warning_context,
            ground_intelligence=ground_context,
            infrastructure_impact=infrastructure_context,
            operational_priority=operational_priority,
            priority_reasons=priority_reasons,
            recommended_actions=recommended_actions,
            assessment_summary=assessment_summary
        )
