import os
import sys
import csv
import json
import math
import numpy as np
from collections import Counter

# Add backend root to python path
SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.abspath(os.path.join(SCRIPTS_DIR, ".."))
sys.path.insert(0, BACKEND_DIR)

from app.services.spatial_query_service import haversine_distance

# ── Re-implementing point in polygon checks to run in-memory without disk overhead ────────
def _point_in_ring(x: float, y: float, ring: list) -> bool:
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
    if not _point_in_ring(x, y, polygon[0]):
        return False
    for hole in polygon[1:]:
        if _point_in_ring(x, y, hole):
            return False
    return True

def load_ner_boundary():
    geojson_path = os.path.join(BACKEND_DIR, "app", "data", "ner_boundary.geojson")
    if not os.path.exists(geojson_path):
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

def perform_scientific_validation():
    print("=== Commencing Scientific Validation of Landslide ML Datasets ===")
    
    pos_path = os.path.join(BACKEND_DIR, "data", "ml", "positives_cleaned.csv")
    neg_path = os.path.join(BACKEND_DIR, "data", "ml", "negatives_sampled.csv")
    base_path = os.path.join(BACKEND_DIR, "data", "ml", "static_training_base.csv")
    
    # Check paths
    for p in (pos_path, neg_path, base_path):
        if not os.path.exists(p):
            print(f"Error: Required file not found at: {p}")
            return
            
    # 1. Load Positives
    positives = []
    with open(pos_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            r["latitude"] = float(r["latitude"])
            r["longitude"] = float(r["longitude"])
            positives.append(r)
            
    # 2. Load Negatives
    negatives = []
    with open(neg_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            r["latitude"] = float(r["latitude"])
            r["longitude"] = float(r["longitude"])
            r["landslide_label"] = int(r["landslide_label"])
            negatives.append(r)
            
    # 3. Load Combined Base
    combined = []
    with open(base_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            r["latitude"] = float(r["latitude"])
            r["longitude"] = float(r["longitude"])
            r["landslide_label"] = int(r["landslide_label"])
            combined.append(r)
            
    # --- Count Consistency ---
    num_pos = len(positives)
    num_neg = len(negatives)
    num_comb = len(combined)
    ratio = num_neg / num_pos if num_pos > 0 else 0
    
    print(f"\n1. Count & Ratio Consistency:")
    print(f"  Positives Count:        {num_pos}")
    print(f"  Negatives Count:        {num_neg}")
    print(f"  Class Ratio (Neg/Pos):  {ratio:.4f} (Target: 2.0)")
    print(f"  Combined Base Count:    {num_comb} (Expected: {num_pos + num_neg})")
    
    pos_coords_set = set((p["latitude"], p["longitude"]) for p in positives)
    neg_coords_set = set((n["latitude"], n["longitude"]) for n in negatives)
    
    comb_pos_coords = set((c["latitude"], c["longitude"]) for c in combined if c["landslide_label"] == 1)
    comb_neg_coords = set((c["latitude"], c["longitude"]) for c in combined if c["landslide_label"] == 0)
    
    pos_match = pos_coords_set == comb_pos_coords
    neg_match = neg_coords_set == comb_neg_coords
    print(f"  Combined Positives Match Source: {pos_match}")
    print(f"  Combined Negatives Match Source: {neg_match}")
    
    # --- Geographic & Block ID Distributions ---
    pos_blocks = [p["spatial_block_id"] for p in positives]
    neg_blocks = [n["spatial_block_id"] for n in negatives]
    
    pos_block_counts = Counter(pos_blocks)
    neg_block_counts = Counter(neg_blocks)
    
    all_blocks = set(pos_block_counts.keys()) | set(neg_block_counts.keys())
    
    print(f"\n2. Spatial Block ID Distributions:")
    print(f"  Unique blocks with positives: {len(pos_block_counts)}")
    print(f"  Unique blocks with negatives: {len(neg_block_counts)}")
    print(f"  Total unique spatial blocks:  {len(all_blocks)}")
    
    # Detect blocks with disproportionate negative distributions
    disproportionate_blocks = []
    for block in all_blocks:
        pos_cnt = pos_block_counts.get(block, 0)
        neg_cnt = neg_block_counts.get(block, 0)
        if pos_cnt <= 2 and neg_cnt >= 20:
            disproportionate_blocks.append((block, pos_cnt, neg_cnt))
            
    print(f"  Blocks with high negatives but low positives (Pos <= 2, Neg >= 20):")
    if disproportionate_blocks:
        for block, pos_cnt, neg_cnt in sorted(disproportionate_blocks, key=lambda x: -x[2])[:10]:
            print(f"    - {block}: Pos={pos_cnt}, Neg={neg_cnt}")
    else:
        print("    - None found.")
        
    # --- Negative Sample Quality ---
    ner_boundary = load_ner_boundary()
    
    invalid_neg_coords = 0
    outside_ner = 0
    duplicate_negs = 0
    
    seen_negs = set()
    for n in negatives:
        lat, lon = n["latitude"], n["longitude"]
        if not (-90.0 <= lat <= 90.0) or not (-180.0 <= lon <= 180.0):
            invalid_neg_coords += 1
        if not is_inside_ner_mem(lat, lon, ner_boundary):
            outside_ner += 1
            
        coord = (round(lat, 6), round(lon, 6))
        if coord in seen_negs:
            duplicate_negs += 1
        seen_negs.add(coord)
        
    print(f"\n3. Negative Sample Quality:")
    print(f"  Invalid coordinate values:    {invalid_neg_coords}")
    print(f"  Coordinates outside NER poly: {outside_ner}")
    print(f"  Duplicate coordinates:        {duplicate_negs}")
    
    # --- Buffer Validation (2 km minimum distance) ---
    print(f"\n4. Buffer Validation:")
    
    min_dist_overall = float("inf")
    violations = 0
    
    pos_grid = {}
    grid_size = 0.05
    for p in positives:
        lat, lon = p["latitude"], p["longitude"]
        cell_x = int(math.floor(lon / grid_size))
        cell_y = int(math.floor(lat / grid_size))
        cell_key = (cell_x, cell_y)
        if cell_key not in pos_grid:
            pos_grid[cell_key] = []
        pos_grid[cell_key].append(p)
        
    for n in negatives:
        lat_cand, lon_cand = n["latitude"], n["longitude"]
        cell_x = int(math.floor(lon_cand / grid_size))
        cell_y = int(math.floor(lat_cand / grid_size))
        
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                neighbor_key = (cell_x + dx, cell_y + dy)
                if neighbor_key in pos_grid:
                    for p in pos_grid[neighbor_key]:
                        dist = haversine_distance(lat_cand, lon_cand, p["latitude"], p["longitude"])
                        if dist < min_dist_overall:
                            min_dist_overall = dist
                        if dist < 2.0:
                            violations += 1
                            
    print(f"  Minimum positive-negative distance: {min_dist_overall:.6f} km")
    print(f"  Exclusion zone violations (< 2.0 km): {violations}")
    
    # --- Leakage / Metadata Validation ---
    print(f"\n5. Leakage / Metadata Validation:")
    base_fieldnames = []
    with open(base_path, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        base_fieldnames = next(reader)
        
    print(f"  Fields in static_training_base.csv: {base_fieldnames}")
    leaked_fields = {"source", "source_id", "event_date", "trigger", "landslide_type"} & set(base_fieldnames)
    print(f"  Leaked metadata fields: {leaked_fields if leaked_fields else 'None'}")
    
    block_format_ok = all(c["spatial_block_id"].startswith("block_") for c in combined)
    print(f"  Spatial Block IDs format valid: {block_format_ok}")
    
    labels = [c["landslide_label"] for c in combined]
    label_counts = Counter(labels)
    print(f"  Label distribution: {dict(label_counts)}")
    
    print("\n=== Validation Complete ===")

if __name__ == "__main__":
    perform_scientific_validation()
