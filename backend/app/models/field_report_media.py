"""
Field Report Media Model - Phase 7 Checkpoint 16.2

Defines the SQLAlchemy model for media evidence (photographs) attached
to citizen and field official hazard reports.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, Float, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database.session import Base

class FieldReportMedia(Base):
    """
    SQLAlchemy Model for media evidence files linked to field hazard reports.
    Stores metadata including dimensions, mime type, and extracted EXIF geolocation.
    """
    __tablename__ = "field_report_media"

    id = Column(Integer, primary_key=True, index=True)
    report_id = Column(Integer, ForeignKey("field_reports.id", ondelete="CASCADE"), index=True, nullable=False)
    media_type = Column(String(50), nullable=False, default="IMAGE")
    original_filename = Column(String(255), nullable=False)
    stored_filename = Column(String(255), unique=True, index=True, nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size_bytes = Column(Integer, nullable=False)
    mime_type = Column(String(100), nullable=False)
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    exif_latitude = Column(Float, nullable=True)
    exif_longitude = Column(Float, nullable=True)
    exif_timestamp = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    report = relationship("FieldReport", back_populates="media")
