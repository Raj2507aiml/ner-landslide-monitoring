from pydantic import BaseModel
from typing import Dict, Optional, List

class GSILandslideRecord(BaseModel):
    """Schema for individual GSI historical landslide record (optimized for mapping)."""
    source_id: int
    source_ref: Optional[str] = None
    latitude: float
    longitude: float
    distance_km: float
    state: str
    district: Optional[str] = None
    slide_name: Optional[str] = None
    landslide_type: Optional[str] = None
    material: Optional[str] = None
    trigger: Optional[str] = None
    activity: Optional[str] = None
    movement_rate: Optional[str] = None

class NASALandslideRecord(BaseModel):
    """Schema for individual NASA historical landslide event (optimized for mapping)."""
    source_id: str
    source_ref: Optional[str] = None
    latitude: float
    longitude: float
    distance_km: float
    state: str
    location_description: Optional[str] = None
    landslide_type: Optional[str] = None
    trigger: Optional[str] = None
    event_date: Optional[str] = None
    fatalities: Optional[int] = None
    injuries: Optional[int] = None
    location_accuracy: Optional[str] = None

class GSISummary(BaseModel):
    """Factual summary stats for nearby GSI landslide incidents."""
    total_nearby_incidents: int
    nearest_incident_distance_km: Optional[float] = None
    landslide_type_distribution: Dict[str, int]
    trigger_distribution: Dict[str, int]

class NASASummary(BaseModel):
    """Factual summary stats for nearby NASA landslide events."""
    total_nearby_events: int
    nearest_event_distance_km: Optional[float] = None
    trigger_distribution: Dict[str, int]
    total_recorded_fatalities: int
    total_recorded_injuries: int
    earliest_event_date: Optional[str] = None
    latest_event_date: Optional[str] = None

class CombinedSummary(BaseModel):
    """Combined factual summary stats for all nearby historical landslide records."""
    total_historical_observations: int
    nearest_historical_observation_km: Optional[float] = None

class HistoricalContextResponse(BaseModel):
    """Standardized response schema for nearby historical landslide context (supports map features)."""
    query_latitude: float
    query_longitude: float
    radius_km: float
    gsi_summary: GSISummary
    nasa_summary: NASASummary
    combined_summary: CombinedSummary
    gsi_incidents: List[GSILandslideRecord] = []  # Exposed lists of nearby GSI records
    nasa_events: List[NASALandslideRecord] = []    # Exposed lists of nearby NASA events

# ── Susceptibility Component Schemas ────────────────────────────────────────

class HistoricalComponent(BaseModel):
    """Heuristic scoring details for historical landslide database presence."""
    score: float
    max_score: float
    proximity_score: float
    density_score: float
    total_observations: int
    nearest_observation_km: Optional[float] = None

class TerrainComponent(BaseModel):
    """Heuristic scoring details for terrain slope predisposition."""
    available: bool
    score: Optional[float] = None
    max_score: float
    mean_slope_degrees: Optional[float] = None
    level: Optional[str] = None

class RainfallComponent(BaseModel):
    """Heuristic scoring details for antecedent precipitation trigger conditions."""
    available: bool
    score: Optional[float] = None
    max_score: float
    precipitation_mm_24h: Optional[float] = None
    level: Optional[str] = None
    daily_score: Optional[float] = None
    three_day_score: Optional[float] = None
    seven_day_score: Optional[float] = None
    three_day_cumulative_mm: Optional[float] = None
    seven_day_cumulative_mm: Optional[float] = None
    scoring_mode: str = "compatibility"

class SusceptibilityResponse(BaseModel):
    """Unified response for heuristic landslide hazard susceptibility score."""
    query_latitude: float
    query_longitude: float
    radius_km: float
    susceptibility_score: float
    hazard_level: str
    historical_component: HistoricalComponent
    terrain_component: TerrainComponent
    rainfall_component: RainfallComponent
    available_max_points: float
    explanation: str


# ---------------------------------------------------------------------------
# Historical Risk Context Engine Schemas (Phase 3.5)
# ---------------------------------------------------------------------------
class NearestIncidentDetails(BaseModel):
    distance_km: Optional[float] = None
    available: bool

class RecentActivityDetails(BaseModel):
    recent_incident_count: int
    data_available: bool

class HistoricalFactorScores(BaseModel):
    frequency: float
    distance: float
    density: float
    recency: float

class HistoricalRiskContextResponse(BaseModel):
    latitude: float
    longitude: float
    search_radius_km: float
    nearby_incident_count: int
    nearest_incident: NearestIncidentDetails
    incident_density_per_sq_km: float
    recent_activity: RecentActivityDetails
    historical_susceptibility_score: float
    historical_risk_level: str
    factor_scores: HistoricalFactorScores
    risk_factors: List[str]
    historical_data_available: bool = True
    confidence: str

