"""
Operational Incident Service - Phase 8 Checkpoint 18.1

Orchestrates automatic operational incident creation based on situational assessments,
manages duplicate prevention, code generation, and controlled lifecycle transitions.
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.operational_incident import OperationalIncident
from app.schemas.operational_incident import (
    IncidentSeverity,
    IncidentStatus,
    IncidentSource
)
from app.schemas.operational_assessment import OperationalPriorityLevel
from app.services.operational_assessment_service import OperationalAssessmentService
from app.services.spatial_query_service import haversine_distance

logger = logging.getLogger(__name__)

DUPLICATE_PROXIMITY_THRESHOLD_KM = 1.0
ACTIVE_STATUSES = [
    IncidentStatus.OPEN.value,
    IncidentStatus.ACKNOWLEDGED.value,
    IncidentStatus.IN_PROGRESS.value
]

class OperationalIncidentService:
    @classmethod
    def generate_incident_code(cls, db: Session, target_date: Optional[datetime] = None) -> str:
        """
        Generates a unique, deterministic, human-readable incident code in format INC-YYYYMMDD-XXXX.
        """
        now = target_date or datetime.utcnow()
        date_str = now.strftime("%Y%m%d")
        prefix = f"INC-{date_str}-"

        # Find existing codes with today's prefix
        existing_codes = db.query(OperationalIncident.incident_code).filter(
            OperationalIncident.incident_code.like(f"{prefix}%")
        ).all()

        max_seq = 0
        for (code,) in existing_codes:
            try:
                seq_part = int(code.split("-")[-1])
                if seq_part > max_seq:
                    max_seq = seq_part
            except (ValueError, IndexError):
                continue

        next_seq = max_seq + 1
        return f"{prefix}{next_seq:04d}"

    @classmethod
    def find_active_duplicate(
        cls,
        db: Session,
        latitude: float,
        longitude: float,
        severity: str,
        proximity_km: float = DUPLICATE_PROXIMITY_THRESHOLD_KM
    ) -> Optional[OperationalIncident]:
        """
        Finds any existing active incident within geographic proximity matching severity.
        """
        active_incidents = db.query(OperationalIncident).filter(
            OperationalIncident.status.in_(ACTIVE_STATUSES)
        ).all()

        for inc in active_incidents:
            dist = haversine_distance(latitude, longitude, inc.latitude, inc.longitude)
            if dist <= proximity_km and inc.severity == severity:
                return inc

        return None

    @classmethod
    def evaluate_and_create_incident(
        cls,
        db: Session,
        latitude: float,
        longitude: float,
        radius_km: float = 5.0,
        mock_raw_roads: Optional[Dict[str, Any]] = None,
        mock_radar_change_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Evaluates operational situation assessment and creates a structured operational incident if required.
        """
        # 1. Run situation assessment across all underlying evidence streams
        assessment = OperationalAssessmentService.evaluate_situation_assessment(
            db=db,
            latitude=latitude,
            longitude=longitude,
            radius_km=radius_km,
            mock_raw_roads=mock_raw_roads,
            mock_radar_change_data=mock_radar_change_data
        )

        priority = assessment.operational_priority

        # 2. Determine if incident creation is triggered
        if priority == OperationalPriorityLevel.CRITICAL_PRIORITY:
            severity_mapped = IncidentSeverity.CRITICAL.value
        elif priority == OperationalPriorityLevel.HIGH_PRIORITY:
            severity_mapped = IncidentSeverity.HIGH.value
        else:
            return {
                "action": "not_required",
                "incident": None,
                "reason": f"Operational priority '{priority.value}' does not trigger automatic incident creation. Only HIGH_PRIORITY and CRITICAL_PRIORITY trigger incidents.",
                "assessment_summary": assessment.assessment_summary
            }

        # 3. Duplicate Prevention Check
        duplicate = cls.find_active_duplicate(
            db=db,
            latitude=latitude,
            longitude=longitude,
            severity=severity_mapped,
            proximity_km=DUPLICATE_PROXIMITY_THRESHOLD_KM
        )

        if duplicate:
            return {
                "action": "duplicate_prevented",
                "incident": duplicate,
                "reason": f"Active {duplicate.severity} incident '{duplicate.incident_code}' ({duplicate.status}) already exists within {DUPLICATE_PROXIMITY_THRESHOLD_KM} km.",
                "assessment_summary": assessment.assessment_summary
            }

        # 4. Construct Immutable Evidence Snapshot
        evidence_snapshot = {
            "operational_priority": priority.value,
            "environmental_risk": {
                "composite_risk_index": assessment.environmental_context.composite_risk_index,
                "risk_level": assessment.environmental_context.risk_level
            },
            "early_warning": {
                "warning_level": assessment.early_warning.warning_level,
                "operational_mode": assessment.early_warning.operational_mode
            },
            "ground_intelligence": {
                "status": assessment.ground_intelligence.status,
                "verified_reports": assessment.ground_intelligence.verified_reports,
                "unverified_reports": assessment.ground_intelligence.unverified_reports,
                "verified_signal_score": assessment.ground_intelligence.verified_signal_score,
                "potential_cluster_detected": assessment.ground_intelligence.potential_cluster_detected
            },
            "road_disruption": {
                "disruption_status": assessment.infrastructure_impact.disruption_status,
                "affected_roads": assessment.infrastructure_impact.affected_roads,
                "monitored_roads": assessment.infrastructure_impact.monitored_roads,
                "priority_road_count": assessment.infrastructure_impact.priority_road_count
            },
            "priority_reasons": assessment.priority_reasons
        }

        # 5. Generate Incident Code and Save Record
        incident_code = cls.generate_incident_code(db)
        title = f"Automated {severity_mapped} Landslide Hazard Incident - {assessment.early_warning.warning_level} Warning / {assessment.infrastructure_impact.disruption_status}"

        new_incident = OperationalIncident(
            incident_code=incident_code,
            latitude=latitude,
            longitude=longitude,
            severity=severity_mapped,
            status=IncidentStatus.OPEN.value,
            source=IncidentSource.AUTOMATED_ASSESSMENT.value,
            title=title,
            description=assessment.assessment_summary,
            operational_priority=priority.value,
            composite_risk_index=assessment.environmental_context.composite_risk_index,
            early_warning_level=assessment.early_warning.warning_level,
            field_intelligence_status=assessment.ground_intelligence.status,
            road_disruption_status=assessment.infrastructure_impact.disruption_status,
            evidence_snapshot=evidence_snapshot,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )

        db.add(new_incident)
        db.commit()
        db.refresh(new_incident)

        return {
            "action": "created",
            "incident": new_incident,
            "reason": f"{priority.value} triggered automatic {severity_mapped} incident creation.",
            "assessment_summary": assessment.assessment_summary
        }

    @classmethod
    def get_incident_by_id(cls, db: Session, incident_id: int) -> Optional[OperationalIncident]:
        """
        Retrieves an incident by primary key.
        """
        return db.query(OperationalIncident).filter(OperationalIncident.id == incident_id).first()

    @classmethod
    def list_incidents(
        cls,
        db: Session,
        status: Optional[str] = None,
        severity: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> Tuple[List[OperationalIncident], int]:
        """
        Lists incidents with optional status and severity filters, ordered newest first.
        """
        query = db.query(OperationalIncident)

        if status:
            query = query.filter(OperationalIncident.status == status)
        if severity:
            query = query.filter(OperationalIncident.severity == severity)

        total = query.count()
        incidents = query.order_by(OperationalIncident.created_at.desc()).offset(offset).limit(limit).all()

        return incidents, total

    @classmethod
    def acknowledge_incident(
        cls,
        db: Session,
        incident_id: int,
        notes: Optional[str] = None
    ) -> OperationalIncident:
        """
        Transitions incident: OPEN -> ACKNOWLEDGED.
        """
        incident = cls.get_incident_by_id(db, incident_id)
        if not incident:
            raise LookupError(f"Operational incident #{incident_id} not found.")

        if incident.status != IncidentStatus.OPEN.value:
            raise ValueError(f"Cannot acknowledge incident in '{incident.status}' state. Transition only allowed from 'OPEN'.")

        incident.status = IncidentStatus.ACKNOWLEDGED.value
        incident.acknowledged_at = datetime.utcnow()
        incident.updated_at = datetime.utcnow()

        if notes:
            incident.description = f"{incident.description or ''}\n[Ack Note]: {notes}".strip()

        db.commit()
        db.refresh(incident)
        return incident

    @classmethod
    def start_incident_response(
        cls,
        db: Session,
        incident_id: int,
        notes: Optional[str] = None
    ) -> OperationalIncident:
        """
        Transitions incident: ACKNOWLEDGED -> IN_PROGRESS.
        """
        incident = cls.get_incident_by_id(db, incident_id)
        if not incident:
            raise LookupError(f"Operational incident #{incident_id} not found.")

        if incident.status != IncidentStatus.ACKNOWLEDGED.value:
            raise ValueError(f"Cannot start response for incident in '{incident.status}' state. Transition only allowed from 'ACKNOWLEDGED'.")

        incident.status = IncidentStatus.IN_PROGRESS.value
        incident.updated_at = datetime.utcnow()

        if notes:
            incident.description = f"{incident.description or ''}\n[Response Note]: {notes}".strip()

        db.commit()
        db.refresh(incident)
        return incident

    @classmethod
    def resolve_incident(
        cls,
        db: Session,
        incident_id: int,
        notes: Optional[str] = None
    ) -> OperationalIncident:
        """
        Transitions incident: IN_PROGRESS -> RESOLVED.
        """
        incident = cls.get_incident_by_id(db, incident_id)
        if not incident:
            raise LookupError(f"Operational incident #{incident_id} not found.")

        if incident.status != IncidentStatus.IN_PROGRESS.value:
            raise ValueError(f"Cannot resolve incident in '{incident.status}' state. Transition only allowed from 'IN_PROGRESS'.")

        incident.status = IncidentStatus.RESOLVED.value
        incident.resolved_at = datetime.utcnow()
        incident.updated_at = datetime.utcnow()

        if notes:
            incident.description = f"{incident.description or ''}\n[Resolve Note]: {notes}".strip()

        db.commit()
        db.refresh(incident)
        return incident
