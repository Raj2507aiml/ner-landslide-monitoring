from sqlalchemy import Column, Integer, Float, String, Boolean, Date, Text
from app.database.session import Base

class GSILandslideIncident(Base):
    """
    SQLAlchemy Model for GSI Historical Landslide Incidents in Northeast India.
    Provides detailed geoscientific and spatial characteristics.
    """
    __tablename__ = "gsi_landslide_incidents"

    id = Column(Integer, primary_key=True, index=True)
    source = Column(String(50), nullable=False, default="GSI")
    source_id = Column(Integer, unique=True, index=True, nullable=False)
    source_ref = Column(String(100), index=True, nullable=True)
    latitude = Column(Float, index=True, nullable=True)
    longitude = Column(Float, index=True, nullable=True)
    state = Column(String(100), index=True, nullable=False)
    district = Column(String(100), nullable=True)
    slide_name = Column(String(255), nullable=True)
    landslide_type = Column(String(100), nullable=True)
    material = Column(String(100), nullable=True)
    trigger = Column(String(100), nullable=True)
    activity = Column(String(100), nullable=True)
    movement_rate = Column(String(100), nullable=True)
    geology = Column(Text, nullable=True)
    geoscientific_cause = Column(Text, nullable=True)
    persons_death = Column(String(100), nullable=True)
    people_affected = Column(String(100), nullable=True)
    infrastructure_affected = Column(Text, nullable=True)
    
    # Temporal fields (always NULL for GSI, kept for compatibility/extension)
    event_date = Column(Date, index=True, nullable=True)
    temporal_precision = Column(String(50), nullable=False, default="unknown")
    location_accuracy = Column(String(50), nullable=True)
    
    # Quality flags
    valid_coordinates = Column(Boolean, nullable=False, default=True)
    duplicate_source_ref = Column(Boolean, nullable=False, default=False)
    duplicate_coordinates = Column(Boolean, nullable=False, default=False)


class NASALandslideEvent(Base):
    """
    SQLAlchemy Model for NASA Global Landslide Catalog Events in Northeast India.
    Provides temporal, triggering, and impact information.
    """
    __tablename__ = "nasa_landslide_events"

    id = Column(Integer, primary_key=True, index=True)
    source = Column(String(50), nullable=False, default="NASA_GLC")
    source_id = Column(String(50), unique=True, index=True, nullable=False)
    source_ref = Column(String(100), index=True, nullable=True)
    latitude = Column(Float, index=True, nullable=True)
    longitude = Column(Float, index=True, nullable=True)
    state = Column(String(100), index=True, nullable=False)
    district = Column(String(100), nullable=True)
    location_description = Column(Text, nullable=True)
    landslide_type = Column(String(100), nullable=True)
    trigger = Column(String(100), nullable=True)
    
    # Temporal fields (Parsed date available)
    event_date = Column(Date, index=True, nullable=True)
    temporal_precision = Column(String(50), nullable=False, default="day")
    
    # Impact fields
    fatalities = Column(Integer, nullable=True)
    injuries = Column(Integer, nullable=True)
    
    # Spatial metadata
    location_accuracy = Column(String(50), nullable=True)
    original_record_reference = Column(Text, nullable=True)
    
    # Quality flags
    valid_coordinates = Column(Boolean, nullable=False, default=True)
    valid_date = Column(Boolean, nullable=False, default=True)
    duplicate_source_id = Column(Boolean, nullable=False, default=False)
    duplicate_coordinates = Column(Boolean, nullable=False, default=False)
