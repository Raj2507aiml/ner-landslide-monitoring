"""
Infrastructure & Road Connectivity Schemas - Phase 8 Checkpoints 17.1 & 17.3

Defines Pydantic models for road infrastructure features, GeoJSON LineStrings,
field report impact evidence, operational connectivity status, and aggregated disruption intelligence.
"""

from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

class RoadConnectivityStatus(str, Enum):
    NORMAL = "NORMAL"
    MONITOR = "MONITOR"
    AT_RISK = "AT_RISK"
    BLOCKED = "BLOCKED"
    SEVERELY_IMPACTED = "SEVERELY_IMPACTED"

class DisruptionSeverityStatus(str, Enum):
    NORMAL = "NORMAL"
    MONITORING_REQUIRED = "MONITORING_REQUIRED"
    ELEVATED_DISRUPTION = "ELEVATED_DISRUPTION"
    HIGH_DISRUPTION = "HIGH_DISRUPTION"
    CRITICAL_DISRUPTION = "CRITICAL_DISRUPTION"

class DisruptionPriorityLevel(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"

class LineStringGeometry(BaseModel):
    type: str = Field("LineString", description="GeoJSON geometry type")
    coordinates: List[List[float]] = Field(..., description="Array of [longitude, latitude] coordinates")

class RoadImpactEvidence(BaseModel):
    verified_reports: int = Field(0, description="Count of verified reports within road impact corridor")
    under_review_reports: int = Field(0, description="Count of reports under review within road impact corridor")
    pending_reports: int = Field(0, description="Count of unverified pending reports within road impact corridor")
    blocked_road_reports: int = Field(0, description="Count of explicit blocked road reports near road")
    supporting_report_ids: List[int] = Field(default_factory=list, description="IDs of field reports associated with this road")

class RoadFeatureResponse(BaseModel):
    osm_id: str = Field(..., description="OpenStreetMap Way ID")
    name: Optional[str] = Field(None, description="Road name if available")
    ref: Optional[str] = Field(None, description="Road reference/route number (e.g. NH-10)")
    highway_type: str = Field(..., description="OSM highway classification (primary, secondary, trunk, etc.)")
    geometry: LineStringGeometry = Field(..., description="GeoJSON LineString geometry with [lon, lat] coordinates")
    connectivity_status: RoadConnectivityStatus = Field(..., description="Operational road connectivity status")
    impact_evidence: RoadImpactEvidence = Field(..., description="Observational field evidence details")
    nearest_hazard_distance_m: Optional[float] = Field(None, description="Distance to nearest active field hazard observation in meters")
    explanation: str = Field(..., description="Explainable decision-support reason for connectivity status")

class ConnectivitySummaryDetails(BaseModel):
    normal: int = Field(0, description="Count of normal roads")
    monitor: int = Field(0, description="Count of roads under observational monitoring")
    at_risk: int = Field(0, description="Count of roads at risk from nearby verified hazards")
    blocked: int = Field(0, description="Count of roads confirmed blocked")
    severely_impacted: int = Field(0, description="Count of roads severely impacted by severe landslides")

class NearbyRoadsResponse(BaseModel):
    location: Dict[str, float] = Field(..., description="Search origin coordinates {latitude, longitude}")
    search_radius_km: float = Field(..., description="Search radius in kilometers")
    total_roads: int = Field(..., description="Total road features retrieved in AOI")
    connectivity_summary: ConnectivitySummaryDetails = Field(..., description="Aggregated connectivity status counts")
    roads: List[RoadFeatureResponse] = Field(default_factory=list, description="Road infrastructure features with connectivity analysis")

# =========================================================================
# Phase 8 Checkpoint 17.3: Road Disruption Intelligence Schemas
# =========================================================================

class PriorityRoadImpactItem(BaseModel):
    priority_rank: int = Field(..., description="Priority rank (1 being highest operational concern)")
    osm_id: str = Field(..., description="OSM Way ID")
    road_name: Optional[str] = Field(None, description="Road name if known")
    road_ref: Optional[str] = Field(None, description="Road route reference (e.g. NH-10)")
    highway_type: str = Field(..., description="Highway classification (primary, secondary, etc.)")
    connectivity_status: RoadConnectivityStatus = Field(..., description="Road connectivity status")
    disruption_priority: DisruptionPriorityLevel = Field(..., description="Operational disruption priority level")
    nearest_hazard_distance_m: Optional[float] = Field(None, description="Distance to nearest associated hazard in meters")
    verified_reports: int = Field(0, description="Count of verified reports near road")
    blocked_road_reports: int = Field(0, description="Count of explicit blocked road reports near road")
    supporting_report_ids: List[int] = Field(default_factory=list, description="IDs of supporting field hazard reports")
    explanation: str = Field(..., description="Explainable reason for priority assignment")

class RoadCountsSummary(BaseModel):
    total: int = Field(0, description="Total mapped roads in AOI")
    normal: int = Field(0, description="Count of normal roads")
    monitor: int = Field(0, description="Count of roads under observational monitoring")
    at_risk: int = Field(0, description="Count of roads at risk")
    blocked: int = Field(0, description="Count of confirmed blocked roads")
    severely_impacted: int = Field(0, description="Count of severely impacted roads")

class RoadDisruptionSummaryResponse(BaseModel):
    location: Dict[str, float] = Field(..., description="Coordinates of query origin {latitude, longitude}")
    search_radius_km: float = Field(..., description="Search radius in kilometers")
    road_counts: RoadCountsSummary = Field(..., description="Categorical counts across all mapped roads")
    affected_roads: int = Field(..., description="Count of confirmed affected roads (AT_RISK + BLOCKED + SEVERELY_IMPACTED)")
    monitored_roads: int = Field(..., description="Count of unverified roads under observation (MONITOR)")
    disruption_status: DisruptionSeverityStatus = Field(..., description="Area-level operational disruption severity")
    priority_roads: List[PriorityRoadImpactItem] = Field(default_factory=list, description="Ranked list of affected roads requiring operational intervention")
    monitoring_roads: List[PriorityRoadImpactItem] = Field(default_factory=list, description="List of roads under observation awaiting field verification")
    hazard_impact_breakdown: Dict[str, int] = Field(default_factory=dict, description="Counts of hazard types associated with affected and monitored roads")
    operational_message: str = Field(..., description="Explainable operational decision summary")
    disclaimer: str = Field(
        "Road disruption intelligence is evidence-based decision support and does not replace official road closure confirmation.",
        description="Scientific and legal disclaimer"
    )
