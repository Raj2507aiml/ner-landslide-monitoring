import os
import sys
import csv
import json
import math
import numpy as np

# Add backend root to python path
SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.abspath(os.path.join(SCRIPTS_DIR, ".."))
sys.path.insert(0, BACKEND_DIR)

from app.services.spatial_query_service import haversine_distance

# ── Point in Polygon checks ────────────────────────────────────────────────
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

def load_sikkim_polygon():
    geojson_path = os.path.join(BACKEND_DIR, "app", "data", "ner_boundary.geojson")
    if not os.path.exists(geojson_path):
        return None
    with open(geojson_path, "r", encoding="utf-8") as f:
        geojson = json.load(f)
        
    for feature in geojson.get("features", []):
        props = feature.get("properties", {})
        if props.get("state_name") == "Sikkim":
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
            return feature
    return None

def is_in_sikkim(latitude: float, longitude: float, sikkim_feature) -> bool:
    if not sikkim_feature:
        return 27.0 <= latitude <= 28.2 and 88.0 <= longitude <= 89.0

    geometry = sikkim_feature.get("geometry", {})
    geom_type = geometry.get("type")
    coords = geometry.get("coordinates", [])
    bboxes = geometry.get("bboxes", [])

    if geom_type == "Polygon":
        min_lon, min_lat, max_lon, max_lat = bboxes[0]
        if not (min_lon <= longitude <= max_lon and min_lat <= latitude <= max_lat):
            return False
        return _point_in_polygon(longitude, latitude, coords)
    elif geom_type == "MultiPolygon":
        for i, poly in enumerate(coords):
            min_lon, min_lat, max_lon, max_lat = bboxes[i]
            if not (min_lon <= longitude <= max_lon and min_lat <= latitude <= max_lat):
                continue
            if _point_in_polygon(longitude, latitude, poly):
                return True
        return False
    return False

def run_generalization_audit():
    print("=== Commencing Focused Generalization Audit ===")
    
    terrain_path = os.path.join(BACKEND_DIR, "data", "ml", "static_training_terrain.csv")
    if not os.path.exists(terrain_path):
        print(f"Error: terrain CSV not found at: {terrain_path}")
        return
        
    sikkim_poly = load_sikkim_polygon()
    
    # 1. Load samples
    sikkim_samples = []
    train_samples = []
    
    with open(terrain_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            r["latitude"] = float(r["latitude"])
            r["longitude"] = float(r["longitude"])
            r["elevation"] = float(r["elevation"])
            r["slope"] = float(r["slope"])
            r["aspect_sin"] = float(r["aspect_sin"])
            r["aspect_cos"] = float(r["aspect_cos"])
            r["landslide_label"] = int(r["landslide_label"])
            
            # Check partition
            if is_in_sikkim(r["latitude"], r["longitude"], sikkim_poly):
                sikkim_samples.append(r)
            else:
                train_samples.append(r)
                
    print(f"Loaded {len(sikkim_samples)} Sikkim holdout samples.")
    print(f"Loaded {len(train_samples)} Training region samples.")
    
    # Verify authoritative polygon splitting
    sikkim_in_train = sum(1 for s in train_samples if is_in_sikkim(s["latitude"], s["longitude"], sikkim_poly))
    train_in_sikkim = sum(1 for s in sikkim_samples if not is_in_sikkim(s["latitude"], s["longitude"], sikkim_poly))
    print(f"  Sikkim samples incorrectly in training: {sikkim_in_train}")
    print(f"  Training samples incorrectly in Sikkim: {train_in_sikkim}")
    assert sikkim_in_train == 0 and train_in_sikkim == 0, "Polygon partition error!"
    
    # 2. Compare Feature Distributions
    features = ["elevation", "slope", "aspect_sin", "aspect_cos"]
    print("\nFeature Distribution Statistics (Mean ± Std | Median):")
    print("Feature    | Sikkim (Holdout)                 | Training Region")
    print("--------------------------------------------------------------------------------")
    for f in features:
        sik_vals = [s[f] for s in sikkim_samples]
        trn_vals = [s[f] for s in train_samples]
        
        sik_mean, sik_std, sik_med = np.mean(sik_vals), np.std(sik_vals), np.median(sik_vals)
        trn_mean, trn_std, trn_med = np.mean(trn_vals), np.std(trn_vals), np.median(trn_vals)
        
        print(f"{f:10s} | {sik_mean:7.2f} ± {sik_std:7.2f} (Med: {sik_med:7.2f}) | {trn_mean:7.2f} ± {trn_std:7.2f} (Med: {trn_med:7.2f})")
        
    # Class-wise distributions
    print("\nClass-wise Slope Distributions (Mean ± Std | Median):")
    for label, name in [(1, "POSITIVES"), (0, "NEGATIVES")]:
        sik_slps = [s["slope"] for s in sikkim_samples if s["landslide_label"] == label]
        trn_slps = [s["slope"] for s in train_samples if s["landslide_label"] == label]
        
        sik_mean, sik_std, sik_med = np.mean(sik_slps), np.std(sik_slps), np.median(sik_slps)
        trn_mean, trn_std, trn_med = np.mean(trn_slps), np.std(trn_slps), np.median(trn_slps)
        
        print(f"  - {name} | Sikkim: {sik_mean:.2f}° ± {sik_std:.2f}° (Med: {sik_med:.2f}°) | Train: {trn_mean:.2f}° ± {trn_std:.2f}° (Med: {trn_med:.2f}°)")
        
    print("\nClass-wise Elevation Distributions (Mean ± Std | Median):")
    for label, name in [(1, "POSITIVES"), (0, "NEGATIVES")]:
        sik_elevs = [s["elevation"] for s in sikkim_samples if s["landslide_label"] == label]
        trn_elevs = [s["elevation"] for s in train_samples if s["landslide_label"] == label]
        
        sik_mean, sik_std, sik_med = np.mean(sik_elevs), np.std(sik_elevs), np.median(sik_elevs)
        trn_mean, trn_std, trn_med = np.mean(trn_elevs), np.std(trn_elevs), np.median(trn_elevs)
        
        print(f"  - {name} | Sikkim: {sik_mean:.1f}m ± {sik_std:.1f}m (Med: {sik_med:.1f}m) | Train: {trn_mean:.1f}m ± {trn_std:.1f}m (Med: {trn_med:.1f}m)")
        
    # 3. Positive-Negative Separability (Sikkim vs Training Region)
    # Simple linear/geometric distance metric of separability: Normalized Distance between means
    # Separability = |mean(pos) - mean(neg)| / sqrt(std(pos)^2 + std(neg)^2)
    # Higher value indicates cleaner physical separation between classes.
    print("\nPositive-Negative Separability Diagnostics (Separability Index):")
    for name, subset in [("Sikkim Holdout", sikkim_samples), ("Training Region", train_samples)]:
        pos_slps = [s["slope"] for s in subset if s["landslide_label"] == 1]
        neg_slps = [s["slope"] for s in subset if s["landslide_label"] == 0]
        
        pos_elevs = [s["elevation"] for s in subset if s["landslide_label"] == 1]
        neg_elevs = [s["elevation"] for s in subset if s["landslide_label"] == 0]
        
        sep_slope = abs(np.mean(pos_slps) - np.mean(neg_slps)) / np.sqrt(np.std(pos_slps)**2 + np.std(neg_slps)**2)
        sep_elev = abs(np.mean(pos_elevs) - np.mean(neg_elevs)) / np.sqrt(np.std(pos_elevs)**2 + np.std(neg_elevs)**2)
        
        print(f"  - {name:15s} | Slope Separability: {sep_slope:.4f} | Elevation Separability: {sep_elev:.4f}")
        
    # 4. Spatial near-duplicates check (Cross-boundary distance)
    print("\nSpatial Cross-Boundary Leakage Check:")
    train_pos = [s for s in train_samples if s["landslide_label"] == 1]
    
    min_cross_dist = float("inf")
    pairs_500m = 0
    pairs_1km = 0
    pairs_2km = 0
    
    # Build spatial grid for training positives
    grid_size = 0.05
    pos_grid = {}
    for p in train_pos:
        lat, lon = p["latitude"], p["longitude"]
        cell_x = int(math.floor(lon / grid_size))
        cell_y = int(math.floor(lat / grid_size))
        cell_key = (cell_x, cell_y)
        if cell_key not in pos_grid:
            pos_grid[cell_key] = []
        pos_grid[cell_key].append(p)
        
    for s in sikkim_samples:
        # Check only positives to see if landslide event coordinates overlap across bounds
        if s["landslide_label"] != 1:
            continue
            
        lat_cand, lon_cand = s["latitude"], s["longitude"]
        cell_x = int(math.floor(lon_cand / grid_size))
        cell_y = int(math.floor(lat_cand / grid_size))
        
        for dx in (-2, -1, 0, 1, 2):
            for dy in (-2, -1, 0, 1, 2):
                neighbor_key = (cell_x + dx, cell_y + dy)
                if neighbor_key in pos_grid:
                    for p in pos_grid[neighbor_key]:
                        dist = haversine_distance(lat_cand, lon_cand, p["latitude"], p["longitude"])
                        if dist < min_cross_dist:
                            min_cross_dist = dist
                        if dist <= 0.500:
                            pairs_500m += 1
                        if dist <= 1.000:
                            pairs_1km += 1
                        if dist <= 2.000:
                            pairs_2km += 1
                            
    print(f"  Minimum distance from Sikkim positive to Training positive: {min_cross_dist:.4f} km")
    print(f"  Landslide pairs within 500m: {pairs_500m}")
    print(f"  Landslide pairs within 1.0km: {pairs_1km}")
    print(f"  Landslide pairs within 2.0km: {pairs_2km}")
    
    print("\n=== Validation Complete ===")

if __name__ == "__main__":
    run_generalization_audit()
