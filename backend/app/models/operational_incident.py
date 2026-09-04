"""
Operational Incident Model - Phase 8 Checkpoint 18.1

Defines the SQLAlchemy model for tracking operational disaster-management incidents
triggered automatically by severe situation assessments or created manually.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, Float, String, Text, DateTime, JSON
from app.database.session import Base

class OperationalIncident(Base):
    """
    SQLAlchemy Model for operational landslide hazard incidents.
    Stores structured lifecycle data, evidence snapshots, and response milestones.
    """
    __tablename__ = "operational_incidents"

    id = Column(Integer, primary_key=True, index=True)
    incident_code = Column(String(50), unique=True, index=True, nullable=False)
    latitude = Column(Float, index=True, nullable=False)
    longitude = Column(Float, index=True, nullable=False)
    severity = Column(String(50), index=True, nullable=False)  # LOW, MODERATE, HIGH, CRITICAL
    status = Column(String(50), index=True, nullable=False, default="OPEN")  # OPEN, ACKNOWLEDGED, IN_PROGRESS, RESOLVED
    source = Column(String(50), nullable=False, default="AUTOMATED_ASSESSMENT")  # AUTOMATED_ASSESSMENT, MANUAL
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    operational_priority = Column(String(50), nullable=False)  # ROUTINE, ATTENTION_REQUIRED, HIGH_PRIORITY, CRITICAL_PRIORITY

    composite_risk_index = Column(Float, nullable=True)
    early_warning_level = Column(String(50), nullable=True)
    field_intelligence_status = Column(String(50), nullable=True)
    road_disruption_status = Column(String(50), nullable=True)

    evidence_snapshot = Column(JSON, nullable=True)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    acknowledged_at = Column(DateTime, nullable=True)
    resolved_at = Column(DateTime, nullable=True)
