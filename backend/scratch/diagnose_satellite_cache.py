import os
import sys
import json

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.abspath(os.path.join(SCRIPTS_DIR, ".."))
sys.path.insert(0, BACKEND_DIR)

from app.services.spatial_query_service import haversine_distance

def main():
    cache_dir = os.path.join("data", "satellite_cache")
    if not os.path.exists(cache_dir):
        print("No cache directory found.")
        return
    
    scenes = [d for d in os.listdir(cache_dir) if os.path.isdir(os.path.join(cache_dir, d))]
    print(f"Total scenes in cache: {len(scenes)}\n")
    
    scene_metas = {}
    for s in scenes:
        meta_file = os.path.join(cache_dir, s, "metadata.json")
        if os.path.exists(meta_file):
            with open(meta_file, "r") as f:
                meta = json.load(f)
            scene_metas[s] = meta
            coords = meta.get("aoi_coordinates", {})
            bounds = meta.get("clipping_bounds", {})
            print("=" * 60)
            print(f"Scene ID: {s}")
            print(f"Acquisition: {meta.get('acquisition_time')}")
            print(f"AOI Coordinates in metadata: Lat={coords.get('latitude')}, Lon={coords.get('longitude')}, Radius={coords.get('radius_km')}")
            print(f"Clipping Bounds: {bounds}")
            print(f"CRS: {meta.get('crs')}")
            print(f"Processing Timestamp: {meta.get('processing_timestamp')}")
            
    # Check pairwise discrepancies between all cached scenes
    print("\n" + "=" * 60)
    print("PAIRWISE DISTANCE BETWEEN CACHED AOI CENTERS:")
    scene_ids = list(scene_metas.keys())
    for i in range(len(scene_ids)):
        for j in range(i + 1, len(scene_ids)):
            s1 = scene_ids[i]
            s2 = scene_ids[j]
            c1 = scene_metas[s1].get("aoi_coordinates", {})
            c2 = scene_metas[s2].get("aoi_coordinates", {})
            if c1 and c2:
                dist = haversine_distance(c1["latitude"], c1["longitude"], c2["latitude"], c2["longitude"])
                print(f"{s1[:30]}... VS {s2[:30]}... -> Distance: {dist * 1000.0:.2f} meters ({dist:.4f} km)")

if __name__ == "__main__":
    main()
