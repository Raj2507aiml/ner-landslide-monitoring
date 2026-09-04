"""
Operational Incident Schemas - Phase 8 Checkpoint 18.1

Defines Pydantic models and enums for operational incident evaluation,
lifecycle transitions, evidence snapshots, and response payloads.
"""

from enum import Enum
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

class IncidentSeverity(str, Enum):
    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class IncidentStatus(str, Enum):
    OPEN = "OPEN"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED = "RESOLVED"

class IncidentSource(str, Enum):
    AUTOMATED_ASSESSMENT = "AUTOMATED_ASSESSMENT"
    MANUAL = "MANUAL"

class IncidentEvidenceSnapshot(BaseModel):
    operational_priority: str = Field(..., description="Operational priority level at incident creation")
    environmental_risk: Dict[str, Any] = Field(..., description="Composite landslide risk index and level")
    early_warning: Dict[str, Any] = Field(..., description="Warning level and decision mode")
    ground_intelligence: Dict[str, Any] = Field(..., description="Field observation status and scores")
    road_disruption: Dict[str, Any] = Field(..., description="Road disruption status and affected counts")
    priority_reasons: List[str] = Field(default_factory=list, description="Reasons triggering the operational priority")

class IncidentResponse(BaseModel):
    id: int = Field(..., description="Unique database ID")
    incident_code: str = Field(..., description="Human-readable incident code (INC-YYYYMMDD-XXXX)")
    latitude: float = Field(..., description="Latitude coordinate")
    longitude: float = Field(..., description="Longitude coordinate")
    severity: IncidentSeverity = Field(..., description="Incident severity level")
    status: IncidentStatus = Field(..., description="Current operational incident status")
    source: IncidentSource = Field(..., description="Origin source of the incident")
    title: str = Field(..., description="Descriptive summary title")
    description: Optional[str] = Field(None, description="Detailed narrative description")
    operational_priority: str = Field(..., description="Triggering operational priority level")
    composite_risk_index: Optional[float] = Field(None, description="Composite risk index score (0-100)")
    early_warning_level: Optional[str] = Field(None, description="Early warning level at creation")
    field_intelligence_status: Optional[str] = Field(None, description="Field intelligence status at creation")
    road_disruption_status: Optional[str] = Field(None, description="Road disruption status at creation")
    evidence_snapshot: Optional[Dict[str, Any]] = Field(None, description="Preserved evidence snapshot at creation time")
    created_at: datetime = Field(..., description="Creation timestamp in UTC")
    updated_at: datetime = Field(..., description="Last update timestamp in UTC")
    acknowledged_at: Optional[datetime] = Field(None, description="Timestamp when incident was acknowledged")
    resolved_at: Optional[datetime] = Field(None, description="Timestamp when incident was resolved")

    class Config:
        from_attributes = True

class IncidentEvaluationResponse(BaseModel):
    action: str = Field(..., description="Outcome action: 'created', 'duplicate_prevented', or 'not_required'")
    incident: Optional[IncidentResponse] = Field(None, description="Created or existing active incident details")
    reason: str = Field(..., description="Explainable reason for the evaluation action")
    assessment_summary: Optional[str] = Field(None, description="Underlying operational situation assessment summary")

class IncidentStatusUpdateRequest(BaseModel):
    notes: Optional[str] = Field(None, description="Optional operational notes for the status change")

class IncidentListResponse(BaseModel):
    total: int = Field(..., description="Total incidents matching query filters")
    incidents: List[IncidentResponse] = Field(default_factory=list, description="List of operational incident records")
