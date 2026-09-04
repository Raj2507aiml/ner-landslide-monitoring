from pydantic import BaseModel, Field
from typing import Optional

class LocationAnalysisRequest(BaseModel):
    latitude: float = Field(..., ge=-90.0, le=90.0, description="Latitude of target point")
    longitude: float = Field(..., ge=-180.0, le=180.0, description="Longitude of target point")
    radius_km: float = Field(5.0, ge=0.1, le=25.0, description="Radius for the Area of Interest in kilometers")

class BoundingBox(BaseModel):
    north: float
    south: float
    east: float
    west: float

class AOIDetails(BaseModel):
    radius_km: float
    bounding_box: BoundingBox

class LocationDetails(BaseModel):
    latitude: float
    longitude: float

class RegionDetails(BaseModel):
    name: str = "North Eastern Region"
    in_ner: bool

class LocationAnalysisResponse(BaseModel):
    status: str
    location: LocationDetails
    region: RegionDetails
    aoi: Optional[AOIDetails] = None
    message: Optional[str] = None
