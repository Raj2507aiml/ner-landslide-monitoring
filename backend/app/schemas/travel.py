"""
Travel Route Early Warning Schemas - SIH 2026 NER Landslide Monitoring

Defines structured data contracts for travel safety monitoring,
high-risk corridor identification, and route hazard queries.
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class TravelRiskZone(BaseModel):
    id: str = Field(..., description="Unique identifier for the hazard zone or corridor")
    name: str = Field(..., description="Corridor or landmark name (e.g., Sonapur Tunnel NH-06)")
    highway: Optional[str] = Field(None, description="Highway code if applicable (e.g., NH-06, NH-29)")
    state: Optional[str] = Field(None, description="NER State where the corridor is located")
    latitude: float = Field(..., ge=-90.0, le=90.0, description="Latitude of the hazard zone")
    longitude: float = Field(..., ge=-180.0, le=180.0, description="Longitude of the hazard zone")
    risk_probability: float = Field(..., ge=0.0, le=100.0, description="Estimated landslide risk percentage (0-100)")
    severity: str = Field(..., description="Hazard classification: LOW, MODERATE, HIGH, VERY_HIGH, CRITICAL")
    source: str = Field(..., description="Source of prediction (e.g., OperationalIncident, CompositeRiskEngine)")
    advisory: Optional[str] = Field(None, description="Contextual travel safety advisory")
    timestamp: Optional[str] = Field(None, description="Last evaluation ISO timestamp")


class TravelRiskZonesResponse(BaseModel):
    status: str = Field("success", description="Status code indicator")
    total: int = Field(..., description="Total number of monitored hazard zones returned")
    high_risk_threshold: float = Field(70.0, description="Threshold above which warnings are triggered (default: 70%)")
    warning_distance_km: float = Field(10.0, description="Early warning perimeter in kilometers (default: 10 km)")
    zones: List[TravelRiskZone] = Field(default_factory=list, description="List of hazard zones")


class TravelRouteRiskQuery(BaseModel):
    origin_lat: float = Field(..., ge=-90.0, le=90.0)
    origin_lng: float = Field(..., ge=-180.0, le=180.0)
    destination_lat: float = Field(..., ge=-90.0, le=90.0)
    destination_lng: float = Field(..., ge=-180.0, le=180.0)
    buffer_km: float = Field(15.0, ge=1.0, le=50.0, description="Search corridor width along route")
