"""
Run NER Landslide Standardization — Phase 2.6C Checkpoint 2

Runs both GSI and NASA GLC processors and saves the unified metadata summary
into backend/data/historical/processed/processing_summary.json
"""

import json
import os
import sys
from datetime import datetime, timezone

# -- Add backend/scripts to sys.path so we can import our modules -----------
SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPTS_DIR)

import process_gsi_inventory
import process_nasa_glc

PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPTS_DIR, "..", ".."))
OUT_DIR = os.path.join(PROJECT_ROOT, "backend", "data", "historical", "processed")
SUMMARY_PATH = os.path.join(OUT_DIR, "processing_summary.json")

def main():
    print("=== Starting Historical Landslide Dataset Standardization ===")
    
    # Run GSI process
    gsi_summary = process_gsi_inventory.process()
    
    print("\n------------------------------------------------------------\n")
    
    # Run NASA process
    nasa_summary = process_nasa_glc.process()
    
    # Standard schema mapping documented
    schema_mapping = {
        "GSI": {
            "source_id": "OBJECTID",
            "source_ref": "SLIDE_NO",
            "latitude": "LATITUDE / Geometry Point Y",
            "longitude": "LONGITUDE / Geometry Point X",
            "state": "STATE",
            "district": "DISTRICT",
            "slide_name": "SLIDE_NAME",
            "landslide_type": "MOVEMENT_TYPE",
            "material": "MATERIAL_TYPE",
            "trigger": "TRIGGERING",
            "activity": "ACTIVITY",
            "movement_rate": "MOVEMENT_RATE",
            "geology": "GEOLOGY",
            "geoscientific_cause": "GEOSCIENTIFIC_CAUSE",
            "persons_death": "PERSONS_DEATH",
            "people_affected": "PEOPLE_AFFECTED",
            "infrastructure_affected": "INFRASTRUCTURE_AFFECTED",
            "event_date": "None (always NULL)",
            "temporal_precision": "None (always 'unknown')",
            "location_accuracy": "None (always NULL)"
        },
        "NASA_GLC": {
            "source_id": "event_id",
            "source_ref": "OBJECTID or FID",
            "latitude": "latitude",
            "longitude": "longitude",
            "state": "admin_divi",
            "district": "None (always empty)",
            "location_description": "location_d",
            "landslide_type": "landslide_",
            "trigger": "landslide1",
            "event_date": "event_date (parsed to YYYY-MM-DD)",
            "temporal_precision": "None (always 'day' for valid date)",
            "fatalities": "fatality_c (cast to int)",
            "injuries": "injury_cou (cast to int)",
            "location_accuracy": "location_a",
            "original_record_reference": "source_nam"
        }
    }
    
    # Aggregated summary
    combined_summary = {
        "processing_timestamp": datetime.now(timezone.utc).isoformat(),
        "schema_mapping": schema_mapping,
        "datasets": {
            "GSI": gsi_summary,
            "NASA_GLC": nasa_summary
        }
    }
    
    # Write summary
    print(f"\nWriting processing summary to: {SUMMARY_PATH}")
    with open(SUMMARY_PATH, "w", encoding="utf-8") as f:
        json.dump(combined_summary, f, ensure_ascii=False, indent=2)
        
    print("\n=== Dataset Standardization Successfully Completed ===")

if __name__ == "__main__":
    main()
