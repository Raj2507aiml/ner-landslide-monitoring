from pydantic import BaseModel, Field
from typing import List, Optional, Any, Dict

class SatelliteSearchResponseItem(BaseModel):
    id: str
    collection: str
    datetime: str
    platform: str
    product_type: Optional[str] = None
    orbit_direction: Optional[str] = None
    geometry: Optional[Dict[str, Any]] = None
    bbox: Optional[List[float]] = None

class SatelliteSearchResponse(BaseModel):
    status: str
    count: int
    scenes: List[SatelliteSearchResponseItem]
    message: Optional[str] = None

class SceneAssetItem(BaseModel):
    key: str
    title: Optional[str] = None
    type: Optional[str] = None
    roles: Optional[List[str]] = None
    href: Optional[str] = None
    size: Optional[int] = None

class SceneDetailResponse(BaseModel):
    id: str
    collection: str
    datetime: str
    platform: str
    product_type: Optional[str] = None
    orbit_direction: Optional[str] = None
    geometry: Optional[Dict[str, Any]] = None
    bbox: Optional[List[float]] = None
    assets: List[SceneAssetItem]

class SceneProcessRequest(BaseModel):
    latitude: float = Field(..., ge=-90.0, le=90.0, description="Latitude of coordinate selection")
    longitude: float = Field(..., ge=-180.0, le=180.0, description="Longitude of coordinate selection")
    radius_km: float = Field(5.0, ge=0.1, le=25.0, description="AOI radius size in kilometers")

class SceneProcessResponse(BaseModel):
    status: str
    scene_id: str
    aoi_key: Optional[str] = None
    vv_path: Optional[str] = None
    vh_path: Optional[str] = None
    aoi_bounds: Dict[str, float]
    message: Optional[str] = None

class SatelliteChangeAnalysisRequest(BaseModel):
    reference_scene_id: str = Field(..., description="ID of the reference satellite scene")
    comparison_scene_id: str = Field(..., description="ID of the comparison satellite scene")
    aoi_key: Optional[str] = Field(None, description="Optional AOI cache key")

class AutomaticSatelliteChangeRequest(BaseModel):
    latitude: float = Field(..., ge=-90.0, le=90.0, description="Latitude of target coordinate")
    longitude: float = Field(..., ge=-180.0, le=180.0, description="Longitude of target coordinate")


# ---------------------------------------------------------------------------
# Satellite Change Intelligence Schemas (Phase 7)
# ---------------------------------------------------------------------------
class SceneMetadataSnippet(BaseModel):
    scene_id: str
    acquisition_time: str
    platform: Optional[str] = None


class DeltaBandStatistics(BaseModel):
    mean: float
    median: float
    std: float
    p10: Optional[float] = None
    p90: Optional[float] = None
    significant_positive_change_percentage: Optional[float] = None
    significant_negative_change_percentage: Optional[float] = None


class SatelliteChangeIntelligenceResponse(BaseModel):
    latitude: float = Field(..., description="Query point latitude")
    longitude: float = Field(..., description="Query point longitude")
    satellite_data_available: bool = Field(..., description="Indicates if multi-temporal SAR pair analysis succeeded")
    satellite_change_score: Optional[float] = Field(None, description="Standardized satellite surface change score (0-100)")
    satellite_risk_level: Optional[str] = Field(None, description="Operational satellite hazard category (LOW, MODERATE, HIGH, VERY_HIGH)")
    radar_surface_change_index: Optional[float] = Field(None, description="Radar Surface Change Index (RSCI)")
    spatial_change_extent_percent: Optional[float] = Field(None, description="Spatial extent score of surface disturbance (%)")
    radar_anomaly_magnitude_db: Optional[float] = Field(None, description="Maximum observed SAR backscatter anomaly spread in dB")
    average_significant_change_percent: Optional[float] = Field(None, description="Average percentage of pixels with significant backscatter shift")
    delta_vv_statistics: Optional[DeltaBandStatistics] = Field(None, description="VV co-polarization temporal delta statistics")
    delta_vh_statistics: Optional[DeltaBandStatistics] = Field(None, description="VH cross-polarization temporal delta statistics")
    delta_cross_pol_statistics: Optional[DeltaBandStatistics] = Field(None, description="Cross-polarization ratio temporal delta statistics")
    orbit_direction: Optional[str] = Field(None, description="Satellite orbital pass trajectory (ascending or descending)")
    temporal_baseline_days: Optional[float] = Field(None, description="Temporal separation between reference and comparison acquisitions in days")
    reference_scene: Optional[SceneMetadataSnippet] = Field(None, description="Reference baseline satellite acquisition metadata")
    comparison_scene: Optional[SceneMetadataSnippet] = Field(None, description="Comparison monitoring satellite acquisition metadata")
    satellite_risk_factors: List[str] = Field(..., description="Dynamic, explainable satellite radar change insight statements")
    confidence: str = Field(..., description="Assessment data confidence indicator (HIGH, MEDIUM, LOW)")
    data_source: str = Field("SENTINEL_1_COPERNICUS", description="Underlying remote sensing platform")
    data_unavailability_reason: Optional[str] = Field(None, description="Contextual explanation if satellite pair analysis was unavailable")




