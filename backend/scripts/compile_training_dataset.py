"""
Landslide ML Dataset Compiler - Phase 3 Checkpoint 10B & 10C

Parses and cleans GSI and NASA historical database records, samples pseudo-negatives,
extracts terrain features (elevation, slope, aspect, sin/cos) from Copernicus DEM GLO-30,
and performs post-generation scientific validations.
"""

import os
import sys
import csv
import math
import json
import random
import numpy as np
import rasterio

# Resolve backend directory and inject into path for imports
SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.abspath(os.path.join(SCRIPTS_DIR, ".."))
sys.path.insert(0, BACKEND_DIR)

from app.database.session import SessionLocal
from app.models.historical_landslide import GSILandslideIncident, NASALandslideEvent
from app.services.spatial_query_service import haversine_distance

# ── Re-implementing point in polygon checks to run in-memory without disk overhead ────────
def _point_in_ring(x: float, y: float, ring: list) -> bool:
    """Ray-casting algorithm to check if point (x=lng, y=lat) is in a linear ring."""
    inside = False
    n = len(ring)
    if n < 3:
        return False
    p1x, p1y = ring[0]
    for i in range(n + 1):
        p2x, p2y = ring[i % n]
        if y > min(p1y, p2y):
            if y <= max(p1y, p2y):
                if x <= max(p1x, p2x):
                    if p1y != p2y:
                        xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                    if p1x == p2x or x <= xinters:
                        inside = not inside
        p1x, p1y = p2x, p2y
    return inside

def _point_in_polygon(x: float, y: float, polygon: list) -> bool:
    """Check if point is inside a polygon with optional holes."""
    if not _point_in_ring(x, y, polygon[0]):
        return False
    for hole in polygon[1:]:
        if _point_in_ring(x, y, hole):
            return False
    return True

def load_ner_boundary():
    geojson_path = os.path.join(BACKEND_DIR, "app", "data", "ner_boundary.geojson")
    if not os.path.exists(geojson_path):
        print(f"Warning: Boundary GeoJSON not found at: {geojson_path}. Falling back to bounding box.")
        return None
    with open(geojson_path, "r", encoding="utf-8") as f:
        geojson = json.load(f)
        
    for feature in geojson.get("features", []):
        geometry = feature.get("geometry", {})
        geom_type = geometry.get("type")
        coords = geometry.get("coordinates", [])
        
        bboxes = []
        if geom_type == "Polygon":
            ext = coords[0]
            lons = [p[0] for p in ext]
            lats = [p[1] for p in ext]
            bboxes.append((min(lons), min(lats), max(lons), max(lats)))
        elif geom_type == "MultiPolygon":
            for poly in coords:
                ext = poly[0]
                lons = [p[0] for p in ext]
                lats = [p[1] for p in ext]
                bboxes.append((min(lons), min(lats), max(lons), max(lats)))
        geometry["bboxes"] = bboxes
    return geojson

def is_inside_ner_mem(latitude: float, longitude: float, geojson) -> bool:
    if not geojson:
        return 21.9 <= latitude <= 29.5 and 88.0 <= longitude <= 97.4

    for feature in geojson.get("features", []):
        geometry = feature.get("geometry", {})
        geom_type = geometry.get("type")
        coords = geometry.get("coordinates", [])
        bboxes = geometry.get("bboxes", [])

        if geom_type == "Polygon":
            min_lon, min_lat, max_lon, max_lat = bboxes[0]
            if not (min_lon <= longitude <= max_lon and min_lat <= latitude <= max_lat):
                continue
            if _point_in_polygon(longitude, latitude, coords):
                return True
        elif geom_type == "MultiPolygon":
            for i, poly in enumerate(coords):
                min_lon, min_lat, max_lon, max_lat = bboxes[i]
                if not (min_lon <= longitude <= max_lon and min_lat <= latitude <= max_lat):
                    continue
                if _point_in_polygon(longitude, latitude, poly):
                    return True
    return False

def compile_dataset(distance_threshold_km=0.5, neg_ratio=2, min_neg_dist_km=2.0, max_attempts=500000):
    print("=== Starting Phase 1: Landslide ML Dataset Compilation ===")
    
    db = SessionLocal()
    
    # 1. Load GSI records
    gsi_records = db.query(GSILandslideIncident).all()
    gsi_count = len(gsi_records)
    
    # 2. Load NASA records
    nasa_records = db.query(NASALandslideEvent).all()
    nasa_count = len(nasa_records)
    
    print(f"Loaded {gsi_count} GSI incidents and {nasa_count} NASA events from SQLite.")
    
    # 3. Clean invalid coordinates and collect initial pool
    raw_pool = []
    invalid_removed = 0
    
    for r in gsi_records:
        lat, lon = r.latitude, r.longitude
        if lat is None or lon is None or not (-90.0 <= lat <= 90.0) or not (-180.0 <= lon <= 180.0):
            invalid_removed += 1
            continue
        raw_pool.append({
            "source_id": str(r.source_id),
            "source": "GSI",
            "latitude": lat,
            "longitude": lon,
            "event_date": None
        })
        
    for r in nasa_records:
        lat, lon = r.latitude, r.longitude
        if lat is None or lon is None or not (-90.0 <= lat <= 90.0) or not (-180.0 <= lon <= 180.0):
            invalid_removed += 1
            continue
        date_str = r.event_date.isoformat() if r.event_date else None
        raw_pool.append({
            "source_id": str(r.source_id),
            "source": "NASA_GLC",
            "latitude": lat,
            "longitude": lon,
            "event_date": date_str
        })
        
    # 4. Sort raw pool to prioritize dated events for deduplication
    # (NASA events with date first, then NASA without date, then GSI)
    raw_pool.sort(key=lambda x: (
        0 if (x["source"] == "NASA_GLC" and x["event_date"] is not None) else
        1 if (x["source"] == "NASA_GLC") else 2
    ))
    
    # 5. Deduplicate positive coordinates
    cleaned_positives = []
    duplicates_removed = 0
    
    for item in raw_pool:
        is_duplicate = False
        for accepted in cleaned_positives:
            dist = haversine_distance(
                item["latitude"], item["longitude"],
                accepted["latitude"], accepted["longitude"]
            )
            if dist <= distance_threshold_km:
                is_duplicate = True
                break
        
        if is_duplicate:
            duplicates_removed += 1
        else:
            cleaned_positives.append(item)
            
    # 6. Generate spatial_block_id (approx 55km blocks)
    for item in cleaned_positives:
        lat_block = int(math.floor(item["latitude"] * 2.0))
        lon_block = int(math.floor(item["longitude"] * 2.0))
        item["spatial_block_id"] = f"block_{lat_block}_{lon_block}"
        
    # 7. Write positives to CSV
    ml_data_dir = os.path.join(BACKEND_DIR, "data", "ml")
    os.makedirs(ml_data_dir, exist_ok=True)
    csv_path_pos = os.path.join(ml_data_dir, "positives_cleaned.csv")
    
    with open(csv_path_pos, "w", newline="", encoding="utf-8") as csvfile:
        fieldnames = ["source_id", "source", "latitude", "longitude", "event_date", "spatial_block_id"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for row in cleaned_positives:
            writer.writerow(row)
            
    # 8. Stats
    final_pos_count = len(cleaned_positives)
    dated_count = sum(1 for x in cleaned_positives if x["event_date"] is not None)
    
    print("\n=== Dataset Compilation Summary: Positives ===")
    print(f"Total GSI records:       {gsi_count}")
    print(f"Total NASA records:      {nasa_count}")
    print(f"Invalid records removed: {invalid_removed}")
    print(f"Duplicates removed:      {duplicates_removed}")
    print(f"Final positive count:    {final_pos_count}")
    print(f"Dated event count:       {dated_count}")
    print(f"Cleaned CSV exported:    {csv_path_pos}")
    
    # 9. Phase 2: Pseudo-Negative Sampling
    print("\n=== Starting Phase 2: Pseudo-Negative Sampling ===")
    num_negatives_needed = final_pos_count * neg_ratio
    print(f"Generating {num_negatives_needed} negative samples (Ratio 1:{neg_ratio})...")
    
    # Load boundary GeoJSON file once in-memory with bounding envelopes
    ner_boundary = load_ner_boundary()
    
    # Build spatial grid index for positive coordinates for fast distance verification
    pos_grid = {}
    grid_size = 0.05  # degrees
    
    for p in cleaned_positives:
        lat, lon = p["latitude"], p["longitude"]
        cell_x = int(math.floor(lon / grid_size))
        cell_y = int(math.floor(lat / grid_size))
        cell_key = (cell_x, cell_y)
        if cell_key not in pos_grid:
            pos_grid[cell_key] = []
        pos_grid[cell_key].append(p)
        
    negatives = []
    seen_coordinates = set()
    
    # Bounding box of NER states
    lat_min, lat_max = 21.9, 29.5
    lon_min, lon_max = 88.0, 97.4
    
    attempts = 0
    random.seed(42)  # Seed for reproducibility
    
    while len(negatives) < num_negatives_needed and attempts < max_attempts:
        attempts += 1
        
        lat_cand = random.uniform(lat_min, lat_max)
        lon_cand = random.uniform(lon_min, lon_max)
        
        # Check boundary in-memory
        if not is_inside_ner_mem(lat_cand, lon_cand, ner_boundary):
            continue
            
        # Check duplicate candidates
        coord_key = (round(lat_cand, 6), round(lon_cand, 6))
        if coord_key in seen_coordinates:
            continue
            
        # Check distance constraint using the spatial grid index
        cell_x = int(math.floor(lon_cand / grid_size))
        cell_y = int(math.floor(lat_cand / grid_size))
        
        too_close = False
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                neighbor_key = (cell_x + dx, cell_y + dy)
                if neighbor_key in pos_grid:
                    for p in pos_grid[neighbor_key]:
                        dist = haversine_distance(lat_cand, lon_cand, p["latitude"], p["longitude"])
                        if dist < min_neg_dist_km:
                            too_close = True
                            break
                if too_close:
                    break
            if too_close:
                break
                
        if too_close:
            continue
            
        seen_coordinates.add(coord_key)
        
        # Generate spatial block ID (approx 55km blocks)
        lat_block = int(math.floor(lat_cand * 2.0))
        lon_block = int(math.floor(lon_cand * 2.0))
        spatial_block_id = f"block_{lat_block}_{lon_block}"
        
        negatives.append({
            "source_id": f"neg_{len(negatives)}",
            "source": "PSEUDO_NEGATIVE",
            "latitude": lat_cand,
            "longitude": lon_cand,
            "event_date": None,
            "spatial_block_id": spatial_block_id,
            "landslide_label": 0
        })
        
    if len(negatives) < num_negatives_needed:
        raise ValueError(
            f"Fewer negative samples generated ({len(negatives)}) than requested ({num_negatives_needed}) after {attempts} attempts. "
            "Exceeded max attempts without satisfying the 2 km buffer distance limit."
        )
        
    print(f"Generated all {len(negatives)} valid negative samples successfully after {attempts} attempts.")
    
    # 10. Write negatives to CSV
    csv_path_neg = os.path.join(ml_data_dir, "negatives_sampled.csv")
    with open(csv_path_neg, "w", newline="", encoding="utf-8") as csvfile:
        fieldnames = ["source_id", "source", "latitude", "longitude", "event_date", "spatial_block_id", "landslide_label"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for row in negatives:
            writer.writerow(row)
    print(f"Sampled Negatives CSV exported: {csv_path_neg}")
            
    # 11. Write combined positives + negatives CSV (static_training_base.csv)
    csv_path_base = os.path.join(ml_data_dir, "static_training_base.csv")
    with open(csv_path_base, "w", newline="", encoding="utf-8") as csvfile:
        fieldnames = ["sample_id", "latitude", "longitude", "spatial_block_id", "landslide_label"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        
        idx = 0
        for p in cleaned_positives:
            writer.writerow({
                "sample_id": f"sample_{idx}",
                "latitude": p["latitude"],
                "longitude": p["longitude"],
                "spatial_block_id": p["spatial_block_id"],
                "landslide_label": 1
            })
            idx += 1
            
        for n in negatives:
            writer.writerow({
                "sample_id": f"sample_{idx}",
                "latitude": n["latitude"],
                "longitude": n["longitude"],
                "spatial_block_id": n["spatial_block_id"],
                "landslide_label": 0
            })
            idx += 1
    print(f"Static Training Base CSV exported: {csv_path_base}")
    
    # Run coordinate verification checks
    verify_outputs(cleaned_positives, negatives)
    db.close()
    
    # 12. Phase 3: Terrain Feature Extraction
    extract_terrain_features(csv_path_base)

def verify_outputs(cleaned_positives, negatives):
    print("\n=== Commencing Post-Sampling Verification ===")
    num_pos = len(cleaned_positives)
    num_neg = len(negatives)
    print(f"Positive samples check: {num_pos}")
    print(f"Negative samples check: {num_neg}")
    assert num_neg == num_pos * 2, f"Incorrect negative ratio! Expected {num_pos * 2}, got {num_neg}"
    
    # Check duplicates in negatives
    neg_coords = [(n["latitude"], n["longitude"]) for n in negatives]
    unique_neg_coords = set(neg_coords)
    duplicate_negs = len(neg_coords) - len(unique_neg_coords)
    print(f"Duplicate negative coordinates: {duplicate_negs}")
    assert duplicate_negs == 0, "Duplicate negative coordinates found!"
    
    # Verify 2 km exclusion zone
    pos_grid = {}
    grid_size = 0.05
    for p in cleaned_positives:
        lat, lon = p["latitude"], p["longitude"]
        cell_x = int(math.floor(lon / grid_size))
        cell_y = int(math.floor(lat / grid_size))
        cell_key = (cell_x, cell_y)
        if cell_key not in pos_grid:
            pos_grid[cell_key] = []
        pos_grid[cell_key].append(p)
        
    violation_count = 0
    for n in negatives:
        lat_cand, lon_cand = n["latitude"], n["longitude"]
        cell_x = int(math.floor(lon_cand / grid_size))
        cell_y = int(math.floor(lat_cand / grid_size))
        
        too_close = False
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                neighbor_key = (cell_x + dx, cell_y + dy)
                if neighbor_key in pos_grid:
                    for p in pos_grid[neighbor_key]:
                        dist = haversine_distance(lat_cand, lon_cand, p["latitude"], p["longitude"])
                        if dist < 2.0:
                            violation_count += 1
                            too_close = True
                            break
                if too_close:
                    break
            if too_close:
                break
                            
    print(f"Distance violations (< 2.0 km): {violation_count}")
    assert violation_count == 0, f"Found {violation_count} distance violations!"
    print("=== Verification PASSED successfully! ===")

def extract_terrain_features(base_csv_path):
    print("\n=== Starting Phase 3: Terrain Feature Extraction ===")
    
    # 1. Load base samples
    samples = []
    with open(base_csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            row["latitude"] = float(row["latitude"])
            row["longitude"] = float(row["longitude"])
            row["landslide_label"] = int(row["landslide_label"])
            samples.append(row)
            
    total_samples = len(samples)
    print(f"Loaded {total_samples} samples from {base_csv_path}.")
    
    # 2. Group samples by Copernicus DEM tile (1x1 degree)
    tile_groups = {}
    for s in samples:
        lat = s["latitude"]
        lon = s["longitude"]
        tile_lat = int(math.floor(lat))
        tile_lon = int(math.floor(lon))
        tile_key = (tile_lat, tile_lon)
        if tile_key not in tile_groups:
            tile_groups[tile_key] = []
        tile_groups[tile_key].append(s)
        
    print(f"Grouped coordinates into {len(tile_groups)} active Copernicus tiles.")
    
    extracted_records = []
    nodata_count = 0
    dropped_count = 0
    
    # 3. Process each tile group
    for tile_key, group in tile_groups.items():
        tile_lat, tile_lon = tile_key
        ns = "N" if tile_lat >= 0 else "S"
        ew = "E" if tile_lon >= 0 else "W"
        tile_id = f"Copernicus_DSM_COG_10_{ns}{abs(tile_lat):02d}_00_{ew}{abs(tile_lon):03d}_00_DEM"
        
        url = f"https://copernicus-dem-30m.s3.amazonaws.com/{tile_id}/{tile_id}.tif"
        vsicurl_url = f"/vsicurl/{url}"
        
        print(f"Opening tile virtually via S3 vsicurl: {tile_id} ({len(group)} points)...")
        
        try:
            with rasterio.open(vsicurl_url) as src:
                nodata_val = src.nodata if src.nodata is not None else -32767.0
                
                # Compute pixel coordinates
                cols = [(s["longitude"] - tile_lon) * 3600.0 for s in group]
                rows = [(tile_lat + 1.0 - s["latitude"]) * 3600.0 for s in group]
                
                # Bounding box of all coordinates in this tile
                col_min = max(0, int(math.floor(min(cols))) - 2)
                col_max = min(3600, int(math.ceil(max(cols))) + 3)
                row_min = max(0, int(math.floor(min(rows))) - 2)
                row_max = min(3600, int(math.ceil(max(rows))) + 3)
                
                # Read entire bounding box in one single network read
                window = rasterio.windows.Window(col_min, row_min, col_max - col_min, row_max - row_min)
                data_block = src.read(1, window=window)
                
                # Extract and compute features locally in-memory
                for i, s in enumerate(group):
                    col_float = cols[i]
                    row_float = rows[i]
                    
                    local_col = int(col_float) - col_min
                    local_row = int(row_float) - row_min
                    
                    # Boundary check for local slice indexing
                    if (local_col - 1 < 0 or local_col + 2 > data_block.shape[1] or
                        local_row - 1 < 0 or local_row + 2 > data_block.shape[0]):
                        dropped_count += 1
                        continue
                        
                    # Extract 3x3 pixel window
                    elev_window = data_block[local_row - 1 : local_row + 2, local_col - 1 : local_col + 2]
                    
                    if elev_window.shape != (3, 3):
                        dropped_count += 1
                        continue
                        
                    # Elevation at coordinate center
                    elev = float(elev_window[1, 1])
                    
                    # NoData check
                    if elev == nodata_val or np.isnan(elev) or elev < -500.0:
                        nodata_count += 1
                        dropped_count += 1
                        continue
                        
                    # Verify window values are all valid
                    if np.any(elev_window == nodata_val) or np.any(np.isnan(elev_window)):
                        nodata_count += 1
                        dropped_count += 1
                        continue
                        
                    # Compute spatial derivatives
                    # dy = 30.87m, dx = 30.87 * cos(lat)m
                    dy = 30.87
                    dx = 30.87 * math.cos(math.radians(s["latitude"]))
                    
                    z11, z12, z13 = float(elev_window[0, 0]), float(elev_window[0, 1]), float(elev_window[0, 2])
                    z21, z22, z23 = float(elev_window[1, 0]), float(elev_window[1, 1]), float(elev_window[1, 2])
                    z31, z32, z33 = float(elev_window[2, 0]), float(elev_window[2, 1]), float(elev_window[2, 2])
                    
                    # Horn's Sobel filter formulas
                    dz_dx = ((z13 + 2.0*z23 + z33) - (z11 + 2.0*z21 + z31)) / (8.0 * dx)
                    dz_dy = ((z31 + 2.0*z32 + z33) - (z11 + 2.0*z12 + z13)) / (8.0 * dy)
                    
                    slope_rad = math.atan(math.sqrt(dz_dx**2 + dz_dy**2))
                    slope = math.degrees(slope_rad)
                    
                    aspect_rad = math.atan2(dz_dy, -dz_dx)
                    aspect = (270.0 + math.degrees(aspect_rad)) % 360.0
                    
                    # Flat aspect conversion
                    if slope < 0.1:
                        aspect = -1.0
                        aspect_sin = 0.0
                        aspect_cos = 0.0
                    else:
                        aspect_sin = math.sin(math.radians(aspect))
                        aspect_cos = math.cos(math.radians(aspect))
                        
                    extracted_records.append({
                        "sample_id": s["sample_id"],
                        "latitude": s["latitude"],
                        "longitude": s["longitude"],
                        "spatial_block_id": s["spatial_block_id"],
                        "elevation": round(elev, 2),
                        "slope": round(slope, 4),
                        "aspect": round(aspect, 2),
                        "aspect_sin": round(aspect_sin, 6),
                        "aspect_cos": round(aspect_cos, 6),
                        "landslide_label": s["landslide_label"]
                    })
        except Exception as e:
            print(f"Error reading tile {tile_id}: {e}")
            dropped_count += len(group)
            
    # 4. Write static_training_terrain.csv
    csv_path_terrain = os.path.join(BACKEND_DIR, "data", "ml", "static_training_terrain.csv")
    with open(csv_path_terrain, "w", newline="", encoding="utf-8") as csvfile:
        fieldnames = ["sample_id", "latitude", "longitude", "spatial_block_id", "elevation", "slope", "aspect", "aspect_sin", "aspect_cos", "landslide_label"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for r in extracted_records:
            writer.writerow(r)
            
    print(f"\nTerrain extraction complete. Exported: {csv_path_terrain}")
    
    # 5. Extraction Stats Validation Report
    elevations = [r["elevation"] for r in extracted_records]
    slopes = [r["slope"] for r in extracted_records]
    
    print("\n=== Terrain Extraction Validation Report ===")
    print(f"Total Input Samples:        {total_samples}")
    print(f"Successfully Extracted:    {len(extracted_records)}")
    print(f"Dropped Coordinates:        {dropped_count}")
    print(f"NoData Coordinates Detected: {nodata_count}")
    if elevations:
        print(f"Elevation Min / Max / Mean: {min(elevations):.1f}m / {max(elevations):.1f}m / {np.mean(elevations):.1f}m")
        print(f"Slope Min / Max / Mean:     {min(slopes):.2f}° / {max(slopes):.2f}° / {np.mean(slopes):.2f}°")
    print("============================================")
    
    # 6. Scientific Validation: Positive vs Negative Distributions
    pos_records = [r for r in extracted_records if r["landslide_label"] == 1]
    neg_records = [r for r in extracted_records if r["landslide_label"] == 0]
    
    print("\n=== Post-Extraction Scientific Validation ===")
    for label, subset, name in [(1, pos_records, "POSITIVES"), (0, neg_records, "NEGATIVES")]:
        elevs = [r["elevation"] for r in subset]
        slps = [r["slope"] for r in subset]
        
        # Slope classes
        flat_pct = sum(1 for s in slps if s < 5.0) / len(slps) * 100.0 if slps else 0.0
        mod_pct = sum(1 for s in slps if 5.0 <= s <= 10.0) / len(slps) * 100.0 if slps else 0.0
        steep_pct = sum(1 for s in slps if s > 10.0) / len(slps) * 100.0 if slps else 0.0
        
        print(f"--- {name} (Count: {len(subset)}) ---")
        if elevs:
            print(f"  Elevation Mean / Median: {np.mean(elevs):.1f}m / {np.median(elevs):.1f}m")
            print(f"  Slope Mean / Median:     {np.mean(slps):.2f}° / {np.median(slps):.2f}°")
            print(f"  Slope Distribution Class:")
            print(f"    - Slope < 5°:       {flat_pct:.2f}%")
            print(f"    - Slope 5° - 10°:   {mod_pct:.2f}%")
            print(f"    - Slope > 10°:      {steep_pct:.2f}%")
            
    print("\n=== Environmental Bias Analysis ===")
    pos_flat_pct = sum(1 for r in pos_records if r["slope"] < 5.0) / len(pos_records) * 100.0 if pos_records else 0.0
    neg_flat_pct = sum(1 for r in neg_records if r["slope"] < 5.0) / len(neg_records) * 100.0 if neg_records else 0.0
    print(f"  Positives flat terrain proportion (< 5°): {pos_flat_pct:.2f}%")
    print(f"  Negatives flat terrain proportion (< 5°): {neg_flat_pct:.2f}%")
    
    # Check if negatives are heavily biased towards flat terrain
    if neg_flat_pct - pos_flat_pct > 30.0:
        print("  WARNING: Negatives are heavily concentrated in flat plains compared to positives.")
        print("  Scientific Status: NEGATIVE SAMPLING NEEDS REFINEMENT (Terrain Bias Detected).")
    else:
        print("  Scientific Status: SAFE TO PROCEED TO ML TRAINING (No Significant Flat Terrain Bias).")
    print("============================================")

if __name__ == "__main__":
    compile_dataset()
