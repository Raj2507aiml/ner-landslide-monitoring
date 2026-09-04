"""
Operational Situation Assessment Schemas - Phase 8 Checkpoint 17.4

Defines Pydantic models and enums for integrated situational decision support,
synthesizing environmental risk, early warning, ground observations, and road disruption intelligence.
"""

from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

class OperationalPriorityLevel(str, Enum):
    ROUTINE = "ROUTINE"
    ATTENTION_REQUIRED = "ATTENTION_REQUIRED"
    HIGH_PRIORITY = "HIGH_PRIORITY"
    CRITICAL_PRIORITY = "CRITICAL_PRIORITY"

class EnvironmentalContextDetails(BaseModel):
    composite_risk_index: float = Field(..., description="Overall Composite Landslide Risk Index (0-100)")
    risk_level: str = Field(..., description="Categorical environmental risk level (Low, Moderate, High, Very High)")

class EarlyWarningContextDetails(BaseModel):
    warning_level: str = Field(..., description="Early warning state (NORMAL, WATCH, ALERT, CRITICAL)")
    operational_mode: str = Field(..., description="Warning decision mode (FULL_EVIDENCE, METEOROLOGICAL_FALLBACK)")
    recommended_action: str = Field(..., description="Target recommended action guidelines from warning engine")

class GroundIntelligenceContextDetails(BaseModel):
    status: str = Field(..., description="Ground observation categorical status")
    verified_reports: int = Field(0, description="Count of verified reports near location")
    unverified_reports: int = Field(0, description="Count of unverified pending/under review reports")
    verified_signal_score: float = Field(0.0, description="Normalized verified ground hazard score (0-100)")
    potential_cluster_detected: bool = Field(False, description="Whether a spatial hazard cluster was detected")

class InfrastructureImpactContextDetails(BaseModel):
    disruption_status: str = Field(..., description="Area-level road disruption status")
    affected_roads: int = Field(0, description="Count of confirmed affected roads (AT_RISK + BLOCKED + SEVERELY_IMPACTED)")
    monitored_roads: int = Field(0, description="Count of unverified roads under observation (MONITOR)")
    priority_road_count: int = Field(0, description="Count of roads requiring prioritized operational intervention")

class OperationalSituationAssessmentResponse(BaseModel):
    location: Dict[str, float] = Field(..., description="Coordinates of analysis origin {latitude, longitude}")
    analysis_radius_km: float = Field(..., description="Search radius in kilometers")
    environmental_context: EnvironmentalContextDetails = Field(..., description="Environmental hazard risk context")
    early_warning: EarlyWarningContextDetails = Field(..., description="Operational early warning context")
    ground_intelligence: GroundIntelligenceContextDetails = Field(..., description="Ground-truth field observation context")
    infrastructure_impact: InfrastructureImpactContextDetails = Field(..., description="Road network connectivity and disruption context")
    operational_priority: OperationalPriorityLevel = Field(..., description="Overall synthesized operational priority level")
    priority_reasons: List[str] = Field(default_factory=list, description="Explainable deterministic reasons for priority assignment")
    recommended_actions: List[str] = Field(default_factory=list, description="Target operational action recommendations")
    assessment_summary: str = Field(..., description="Synthesized situation summary narrative")
    disclaimer: str = Field(
        "Integrated Operational Situation Assessment is an evidence-synthesis and decision-support tool. "
        "It synthesizes independent environmental, warning, field observation, and road disruption layers "
        "without mathematically altering hazard models, and does not replace official statutory disaster management directives or physical road closures.",
        description="Scientific and legal decision-support disclaimer"
    )
