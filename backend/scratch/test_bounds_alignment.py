import os
import sys
import json

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.abspath(os.path.join(SCRIPTS_DIR, ".."))
sys.path.insert(0, BACKEND_DIR)

from app.services.terrain_service import render_raster_to_png

def test_bounds():
    print("=== Commencing Raster Bounds Alignment Audit ===")
    
    # Locate one cached scene folder
    cache_dir = os.path.join(BACKEND_DIR, "data", "satellite_cache")
    scenes = [d for d in os.listdir(cache_dir) if os.path.isdir(os.path.join(cache_dir, d))]
    
    if not scenes:
        print("Error: No cached scenes found.")
        return
        
    scene_id = scenes[0]
    scene_dir = os.path.join(cache_dir, scene_id)
    tif_path = os.path.join(scene_dir, "dem_clipped.tif")
    metadata_path = os.path.join(scene_dir, "metadata.json")
    
    print(f"Targeting cached scene: {scene_id}")
    
    if not os.path.exists(tif_path) or not os.path.exists(metadata_path):
        print("Error: Missing dem_clipped.tif or metadata.json in scene cache.")
        return
        
    with open(metadata_path, "r", encoding="utf-8") as f:
        meta = json.load(f)
        
    original_bbox = meta.get("clipping_bounds")
    print(f"Original clipping bounds in metadata.json:")
    print(f"  South: {original_bbox['south']} | North: {original_bbox['north']}")
    print(f"  West:  {original_bbox['west']} | East:  {original_bbox['east']}")
    
    # Execute rendering
    png_bytes, returned_bounds = render_raster_to_png(tif_path, "dem")
    
    print(f"\nReturned bounds after alignment fix:")
    print(f"  South: {returned_bounds[0][0]} | North: {returned_bounds[1][0]}")
    print(f"  West:  {returned_bounds[0][1]} | East:  {returned_bounds[1][1]}")
    
    # Assert exact match
    epsilon = 1e-9
    assert abs(returned_bounds[0][0] - original_bbox["south"]) < epsilon, "South coordinate mismatch!"
    assert abs(returned_bounds[0][1] - original_bbox["west"]) < epsilon, "West coordinate mismatch!"
    assert abs(returned_bounds[1][0] - original_bbox["north"]) < epsilon, "North coordinate mismatch!"
    assert abs(returned_bounds[1][1] - original_bbox["east"]) < epsilon, "East coordinate mismatch!"
    
    print("\nStatus: SUCCESS (Returned bounds are identical to the original clipping bounds!)")
    print("================================================")

if __name__ == "__main__":
    test_bounds()
