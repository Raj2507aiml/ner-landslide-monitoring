"""
Field Report Media Schemas - Phase 7 Checkpoint 16.2 & 16.6

Defines Pydantic models for media evidence responses, EXIF geolocation metadata,
and coordinate consistency evaluation.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

class FieldReportMediaResponse(BaseModel):
    """
    Pydantic schema for field report media metadata response.
    Returns safe relative/API media URLs without leaking internal filesystem paths.
    Enriched with EXIF distance and consistency classifications.
    """
    id: int
    report_id: int
    media_type: str = Field(..., description="Media type (e.g. IMAGE)")
    original_filename: str = Field(..., description="Original client-provided filename")
    stored_filename: str = Field(..., description="Secure UUID-based filename on disk")
    file_size_bytes: int = Field(..., description="File size in bytes")
    mime_type: str = Field(..., description="Detected MIME type (e.g. image/jpeg, image/png, image/webp)")
    width: Optional[int] = Field(None, description="Image pixel width")
    height: Optional[int] = Field(None, description="Image pixel height")
    exif_latitude: Optional[float] = Field(None, description="Extracted EXIF GPS latitude if present in image")
    exif_longitude: Optional[float] = Field(None, description="Extracted EXIF GPS longitude if present in image")
    exif_timestamp: Optional[datetime] = Field(None, description="Extracted EXIF capture timestamp if present")
    created_at: datetime
    media_url: str = Field(..., description="Safe relative API URL to access/download the image")
    exif_distance_km: Optional[float] = Field(None, description="Geodesic distance between reported coordinates and EXIF GPS (km)")
    exif_consistency: Optional[str] = Field(None, description="EXIF consistency rating: CONSISTENT, NEARBY_DIFFERENCE, SIGNIFICANT_DIFFERENCE, NO_EXIF_GPS")

    class Config:
        from_attributes = True

class FieldReportMediaDeleteResponse(BaseModel):
    status: str
    media_id: int
    message: str
