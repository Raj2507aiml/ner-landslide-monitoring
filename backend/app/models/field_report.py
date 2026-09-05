"""
Field Report Model - Phase 7 Checkpoint 16.1 & 16.2

Defines the SQLAlchemy model for geo-tagged field observations submitted
by citizens and field officials across the North Eastern Region.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, Float, String, Text, DateTime
from sqlalchemy.orm import relationship
from app.database.session import Base

class FieldReport(Base):
    """
    SQLAlchemy Model for citizen and field-official hazard intelligence reports.
    Stores geo-referenced ground cracks, slope movements, blocked roads, and other observations.
    """
    __tablename__ = "field_reports"

    id = Column(Integer, primary_key=True, index=True)
    report_type = Column(String(50), index=True, nullable=False)
    description = Column(Text, nullable=False)
    latitude = Column(Float, index=True, nullable=False)
    longitude = Column(Float, index=True, nullable=False)
    reporter_type = Column(String(50), nullable=False, default="CITIZEN")
    severity = Column(String(50), nullable=False, default="MEDIUM")
    status = Column(String(50), index=True, nullable=False, default="PENDING")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Jio Tag Evidence & Aadhaar Citizen Verification Details
    full_name = Column(String(150), nullable=True)
    aadhaar_number = Column(String(50), nullable=True)  # Strictly stored in masked format: XXXX-XXXX-1234
    aadhaar_hash = Column(String(64), nullable=True)    # SHA-256 for secure tamper detection
    aadhaar_card_path = Column(String(500), nullable=True)
    aadhaar_qr_path = Column(String(500), nullable=True)
    jio_tag_image_path = Column(String(500), nullable=True)
    verification_status = Column(String(50), nullable=False, default="PENDING")  # PENDING | VERIFIED | REJECTED | RE_UPLOAD_REQUIRED
    verification_note = Column(Text, nullable=True)
    verified_by = Column(String(120), nullable=True)
    verified_at = Column(DateTime, nullable=True)

    # 1-to-many relationship with attached media evidence
    media = relationship("FieldReportMedia", back_populates="report", cascade="all, delete-orphan")
