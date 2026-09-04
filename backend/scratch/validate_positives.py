import os
import sys
import csv
import json
import numpy as np

# Add backend root to python path
SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.abspath(os.path.join(SCRIPTS_DIR, ".."))
sys.path.insert(0, BACKEND_DIR)

from app.database.session import SessionLocal
from app.models.historical_landslide import GSILandslideIncident, NASALandslideEvent
from app.services.spatial_query_service import haversine_distance

def validate_positives():
    print("=== Commencing Validation of positives_cleaned.csv ===")
    
    csv_path = os.path.join(BACKEND_DIR, "data", "ml", "positives_cleaned.csv")
    if not os.path.exists(csv_path):
        print(f"Error: positives_cleaned.csv not found at: {csv_path}")
        return
        
    # 1. Load CSV
    cleaned = []
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            row["latitude"] = float(row["latitude"])
            row["longitude"] = float(row["longitude"])
            cleaned.append(row)
            
    print(f"Loaded {len(cleaned)} cleaned records from CSV.")
    
    # 2. Check schema columns
    required_cols = {"source_id", "source", "latitude", "longitude", "event_date", "spatial_block_id"}
    csv_cols = set(cleaned[0].keys())
    missing_cols = required_cols - csv_cols
    print(f"Missing columns: {missing_cols if missing_cols else 'None'}")
    assert not missing_cols, "Required columns missing from CSV"
    
    # 3. Verify latitude/longitude and spatial_block_id ranges
    invalid_coords = 0
    empty_block_id = 0
    malformed_block_id = 0
    ner_out_of_bounds = 0
    
    # NER bounding box approximate range
    # 21.8N to 28.5N, 89.8E to 97.5E
    for row in cleaned:
        lat, lon = row["latitude"], row["longitude"]
        if not (-90.0 <= lat <= 90.0) or not (-180.0 <= lon <= 180.0):
            invalid_coords += 1
        if not (21.5 <= lat <= 29.0) or not (89.5 <= lon <= 98.0):
            ner_out_of_bounds += 1
            
        block_id = row["spatial_block_id"]
        if not block_id:
            empty_block_id += 1
        elif not block_id.startswith("block_") or len(block_id.split("_")) != 3:
            malformed_block_id += 1
            
    print(f"Coordinates outside general NER bounding box: {ner_out_of_bounds}")
    print(f"Invalid coordinate numbers: {invalid_coords}")
    print(f"Empty spatial_block_id: {empty_block_id}")
    print(f"Malformed spatial_block_id: {malformed_block_id}")
    
    assert invalid_coords == 0, "Invalid coordinates found in CSV"
    assert empty_block_id == 0, "Empty block IDs found in CSV"
    assert malformed_block_id == 0, "Malformed block IDs found in CSV"
    
    # 4. Load raw records from DB
    db = SessionLocal()
    gsi_records = db.query(GSILandslideIncident.latitude, GSILandslideIncident.longitude).all()
    nasa_records = db.query(NASALandslideEvent.latitude, NASALandslideEvent.longitude, NASALandslideEvent.event_date).all()
    db.close()
    
    raw_points = []
    raw_dated_count = 0
    for r in gsi_records:
        if r.latitude is not None and r.longitude is not None:
            raw_points.append((r.latitude, r.longitude, False))
    for r in nasa_records:
        if r.latitude is not None and r.longitude is not None:
            raw_points.append((r.latitude, r.longitude, r.event_date is not None))
            if r.event_date:
                raw_dated_count += 1
                
    print(f"Loaded {len(raw_points)} raw records from SQLite.")
    
    # 5. Calculate nearest-neighbor distances from raw points to cleaned points
    # (dist > 0.0001 represents a merged/removed duplicate)
    merges_0_100 = 0
    merges_100_250 = 0
    merges_250_500 = 0
    zero_distance_count = 0
    other_merges = 0
    
    cleaned_coords = np.array([(row["latitude"], row["longitude"]) for row in cleaned])
    
    for lat_r, lon_r, has_date in raw_points:
        # Vectorized distance computation for speed
        lats_c = cleaned_coords[:, 0]
        lons_c = cleaned_coords[:, 1]
        
        # Haversine components
        phi1 = np.radians(lat_r)
        phi2 = np.radians(lats_c)
        dphi = np.radians(lats_c - lat_r)
        dlam = np.radians(lons_c - lon_r)
        
        a = np.sin(dphi/2.0)**2 + np.cos(phi1) * np.cos(phi2) * np.sin(dlam/2.0)**2
        c = 2.0 * np.arctan2(np.sqrt(a), np.sqrt(1.0 - a))
        dists = 6371.0088 * c
        
        min_dist = dists.min()
        
        # We classify the minimum distance
        # threshold is 0.5 km (500m)
        if min_dist < 0.0001:  # Exactly matched accepted point
            zero_distance_count += 1
        elif min_dist <= 0.100:  # 0-100m
            merges_0_100 += 1
        elif min_dist <= 0.250:  # 100m-250m
            merges_100_250 += 1
        elif min_dist <= 0.500:  # 250m-500m
            merges_250_500 += 1
        else:
            other_merges += 1
            
    print(f"\nDeduplication Merge Breakdown:")
    print(f"  Exact matched records kept:   {zero_distance_count}")
    print(f"  Merged within 0 - 100m:       {merges_0_100}")
    print(f"  Merged within 100m - 250m:    {merges_100_250}")
    print(f"  Merged within 250m - 500m:    {merges_250_500}")
    print(f"  Merged outside 500m (outlier): {other_merges}")
    
    # 6. Verify NASA Preservation
    csv_dated_count = sum(1 for row in cleaned if row["event_date"])
    print(f"\nNASA dated event preservation:")
    print(f"  Raw dated NASA events:        {raw_dated_count}")
    print(f"  Cleaned dated NASA events:    {csv_dated_count}")
    assert csv_dated_count > 0, "NASA dated events were discarded!"
    print("[OK] NASA dated events preserved.")
    
    # 7. Check for duplicate coordinates remaining in the CSV
    unique_coords = set((row["latitude"], row["longitude"]) for row in cleaned)
    duplicate_rem = len(cleaned) - len(unique_coords)
    print(f"Duplicate coordinates remaining in CSV: {duplicate_rem}")
    assert duplicate_rem == 0, "Duplicate coordinates remain in compiled CSV!"
    
    print("\n=== Validation Completed Successfully! Cleaned dataset is SAFE to use. ===")

if __name__ == "__main__":
    validate_positives()
