"""
Import Historical Landslide Datasets — Phase 2.6C Checkpoint 3B

Reads standardized GSI GeoJSON and NASA CSV files and loads them into
gsi_landslide_incidents and nasa_landslide_events tables in SQLite.
Ensures idempotency using source_id lookup.
"""

import os
import sys
import json
import csv
from datetime import datetime, date

# ── Resolve backend directory and inject into path for imports ─────────────
SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.abspath(os.path.join(SCRIPTS_DIR, ".."))
sys.path.insert(0, BACKEND_DIR)

from app.database.session import SessionLocal
from app.models.historical_landslide import GSILandslideIncident, NASALandslideEvent

# ── File Paths ─────────────────────────────────────────────────────────────
GSI_STANDARDIZED_PATH = os.path.join(BACKEND_DIR, "data", "historical", "processed", "gsi_ner_standardized.geojson")
NASA_STANDARDIZED_PATH = os.path.join(BACKEND_DIR, "data", "historical", "processed", "nasa_glc_ner_standardized.csv")

BATCH_SIZE = 500

def _parse_bool(val) -> bool:
    """Parse string representation of boolean values safely."""
    if val is None:
        return False
    s = str(val).strip().upper()
    return s in ("TRUE", "1", "YES", "T", "Y")

def _parse_date(val) -> date | None:
    """Parse YYYY-MM-DD date string safely to a python date object."""
    if not val:
        return None
    s = str(val).strip()
    if not s or s.upper() == "NULL" or s.upper() == "NONE":
        return None
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except ValueError:
        return None

def _parse_int(val) -> int | None:
    """Parse string representation of integer safely."""
    if val is None:
        return None
    s = str(val).strip()
    if not s or s.upper() == "NULL" or s.upper() == "NONE":
        return None
    try:
        return int(float(s))
    except ValueError:
        return None

def _parse_float(val) -> float | None:
    """Parse string representation of float safely."""
    if val is None:
        return None
    s = str(val).strip()
    if not s or s.upper() == "NULL" or s.upper() == "NONE":
        return None
    try:
        return float(s)
    except ValueError:
        return None

def _clean_str(val) -> str | None:
    """Clean string values and return None if empty/whitespace-only."""
    if val is None:
        return None
    s = str(val).strip()
    return s if s else None

def import_gsi(db_session):
    print("---------------- GSI Import ----------------")
    if not os.path.exists(GSI_STANDARDIZED_PATH):
        print(f"Error: GSI standardized file not found at: {GSI_STANDARDIZED_PATH}")
        return
        
    print(f"Loading GSI standardized GeoJSON from: {GSI_STANDARDIZED_PATH}")
    with open(GSI_STANDARDIZED_PATH, "r", encoding="utf-8") as f:
        gsi_fc = json.load(f)
        
    features = gsi_fc.get("features", [])
    total_records = len(features)
    print(f"Total records in source file: {total_records}")
    
    # Pre-load existing GSI source_ids to prevent duplicates (idempotency)
    existing_ids = set(row[0] for row in db_session.query(GSILandslideIncident.source_id).all())
    print(f"Found {len(existing_ids)} existing GSI records in database.")
    
    inserted_count = 0
    skipped_count = 0
    failed_count = 0
    
    batch = []
    
    for feat in features:
        props = feat.get("properties", {})
        source_id = props.get("source_id")
        
        if source_id is None:
            print("Warning: Skipping GSI feature with missing source_id.")
            failed_count += 1
            continue
            
        source_id_int = int(source_id)
        
        # Idempotency check
        if source_id_int in existing_ids:
            skipped_count += 1
            continue
            
        # Map GeoJSON properties directly to GSILandslideIncident model
        incident = GSILandslideIncident(
            source=props.get("source", "GSI"),
            source_id=source_id_int,
            source_ref=_clean_str(props.get("source_ref")),
            latitude=_parse_float(props.get("latitude")),
            longitude=_parse_float(props.get("longitude")),
            state=_clean_str(props.get("state")),
            district=_clean_str(props.get("district")),
            slide_name=_clean_str(props.get("slide_name")),
            landslide_type=_clean_str(props.get("landslide_type")),
            material=_clean_str(props.get("material")),
            trigger=_clean_str(props.get("trigger")),
            activity=_clean_str(props.get("activity")),
            movement_rate=_clean_str(props.get("movement_rate")),
            geology=_clean_str(props.get("geology")),
            geoscientific_cause=_clean_str(props.get("geoscientific_cause")),
            persons_death=_clean_str(props.get("persons_death")),
            people_affected=_clean_str(props.get("people_affected")),
            infrastructure_affected=_clean_str(props.get("infrastructure_affected")),
            event_date=None,  # Always null in GSI
            temporal_precision=props.get("temporal_precision", "unknown"),
            location_accuracy=None,
            valid_coordinates=_parse_bool(props.get("valid_coordinates")),
            duplicate_source_ref=_parse_bool(props.get("duplicate_source_ref")),
            duplicate_coordinates=_parse_bool(props.get("duplicate_coordinates"))
        )
        
        batch.append(incident)
        
        if len(batch) >= BATCH_SIZE:
            try:
                db_session.add_all(batch)
                db_session.commit()
                inserted_count += len(batch)
                batch = []
                print(f"  Inserted {inserted_count} / {total_records} GSI records...")
            except Exception as e:
                db_session.rollback()
                print(f"Error during GSI batch insertion: {e}")
                failed_count += len(batch)
                batch = []
                
    # Insert remaining records in batch
    if batch:
        try:
            db_session.add_all(batch)
            db_session.commit()
            inserted_count += len(batch)
            print(f"  Inserted remaining {len(batch)} GSI records.")
        except Exception as e:
            db_session.rollback()
            print(f"Error during final GSI batch insertion: {e}")
            failed_count += len(batch)
            
    print(f"GSI Import Summary: Inserted={inserted_count}, Skipped={skipped_count}, Failed={failed_count}")
    return inserted_count, skipped_count, failed_count

def import_nasa(db_session):
    print("\n---------------- NASA Import ----------------")
    if not os.path.exists(NASA_STANDARDIZED_PATH):
        print(f"Error: NASA standardized file not found at: {NASA_STANDARDIZED_PATH}")
        return
        
    print(f"Loading NASA standardized CSV from: {NASA_STANDARDIZED_PATH}")
    with open(NASA_STANDARDIZED_PATH, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        
    total_records = len(rows)
    print(f"Total records in source file: {total_records}")
    
    # Pre-load existing NASA source_ids (event_id is a string)
    existing_ids = set(row[0] for row in db_session.query(NASALandslideEvent.source_id).all())
    print(f"Found {len(existing_ids)} existing NASA records in database.")
    
    inserted_count = 0
    skipped_count = 0
    failed_count = 0
    
    batch = []
    
    for r in rows:
        source_id = _clean_str(r.get("source_id"))
        
        if not source_id:
            print("Warning: Skipping NASA record with missing source_id.")
            failed_count += 1
            continue
            
        # Idempotency check
        if source_id in existing_ids:
            skipped_count += 1
            continue
            
        # Map CSV columns to NASALandslideEvent model
        event = NASALandslideEvent(
            source=r.get("source", "NASA_GLC"),
            source_id=source_id,
            source_ref=_clean_str(r.get("source_ref")),
            latitude=_parse_float(r.get("latitude")),
            longitude=_parse_float(r.get("longitude")),
            state=_clean_str(r.get("state")),
            district=_clean_str(r.get("district")),
            location_description=_clean_str(r.get("location_description")),
            landslide_type=_clean_str(r.get("landslide_type")),
            trigger=_clean_str(r.get("trigger")),
            event_date=_parse_date(r.get("event_date")),
            temporal_precision=r.get("temporal_precision", "day"),
            fatalities=_parse_int(r.get("fatalities")),
            injuries=_parse_int(r.get("injuries")),
            location_accuracy=_clean_str(r.get("location_accuracy")),
            original_record_reference=_clean_str(r.get("original_record_reference")),
            valid_coordinates=_parse_bool(r.get("valid_coordinates")),
            valid_date=_parse_bool(r.get("valid_date")),
            duplicate_source_id=_parse_bool(r.get("duplicate_source_id")),
            duplicate_coordinates=_parse_bool(r.get("duplicate_coordinates"))
        )
        
        batch.append(event)
        
        if len(batch) >= BATCH_SIZE:
            try:
                db_session.add_all(batch)
                db_session.commit()
                inserted_count += len(batch)
                batch = []
                print(f"  Inserted {inserted_count} / {total_records} NASA records...")
            except Exception as e:
                db_session.rollback()
                print(f"Error during NASA batch insertion: {e}")
                failed_count += len(batch)
                batch = []
                
    # Insert remaining records in batch
    if batch:
        try:
            db_session.add_all(batch)
            db_session.commit()
            inserted_count += len(batch)
            print(f"  Inserted remaining {len(batch)} NASA records.")
        except Exception as e:
            db_session.rollback()
            print(f"Error during final NASA batch insertion: {e}")
            failed_count += len(batch)
            
    print(f"NASA Import Summary: Inserted={inserted_count}, Skipped={skipped_count}, Failed={failed_count}")
    return inserted_count, skipped_count, failed_count

def main():
    print("=== Starting Historical Landslide Datasets Safe Database Import ===")
    db_session = SessionLocal()
    try:
        # Import GSI
        gsi_ins, gsi_sk, gsi_fa = import_gsi(db_session)
        
        # Import NASA
        nasa_ins, nasa_sk, nasa_fa = import_nasa(db_session)
        
        # Total counts in DB
        gsi_total = db_session.query(GSILandslideIncident).count()
        nasa_total = db_session.query(NASALandslideEvent).count()
        
        print("\n=== Import Completed Successfully ===")
        print(f"GSI final db count:  {gsi_total}")
        print(f"NASA final db count: {nasa_total}")
        
    except Exception as e:
        print(f"Fatal execution error: {e}")
    finally:
        db_session.close()

if __name__ == "__main__":
    main()
