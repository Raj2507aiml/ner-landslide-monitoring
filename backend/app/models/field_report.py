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

    # 1-to-many relationship with attached media evidence
    media = relationship("FieldReportMedia", back_populates="report", cascade="all, delete-orphan")
