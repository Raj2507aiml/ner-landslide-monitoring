import os
import sys
import json
import time

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.abspath(os.path.join(SCRIPTS_DIR, ".."))
sys.path.insert(0, BACKEND_DIR)

from app.services.spatial_query_service import haversine_distance
from app.services.satellite_service import (
    process_scene_raster,
    get_aoi_cache_key,
    resolve_scene_cache_dir
)
from app.services.satellite_change_service import SatelliteChangeService
from app.services.automatic_satellite_pair_service import AutomaticSatellitePairService

def test_scenario_a():
    print("\n" + "=" * 70)
    print("SCENARIO A: Same Scene + Same AOI (Cache Hit Verification)")
    print("=" * 70)
    scene_id = "S1D_IW_GRDH_1SDV_20260818T120500_20260818T120525_004180_007A7E_C8D7_COG"
    lat, lon, rad = 27.3314, 88.6138, 5.0
    
    # First call (migrates/ensures cached)
    r1 = process_scene_raster(scene_id, lat, lon, rad)
    print("Call 1 Status:", r1.get("status"), "| AOI Key:", r1.get("aoi_key"))
    
    # Second call (must be exact cache hit)
    t0 = time.time()
    r2 = process_scene_raster(scene_id, lat, lon, rad)
    dt = time.time() - t0
    print(f"Call 2 Status: {r2.get('status')} | AOI Key: {r2.get('aoi_key')} | Time: {dt*1000:.2f}ms")
    assert r2["status"] == "cached", "Expected cached hit on second call"
    print(">>> SCENARIO A PASSED.")

def test_scenario_b():
    print("\n" + "=" * 70)
    print("SCENARIO B: Same Scene + Different AOIs (Multi-AOI Coexistence)")
    print("=" * 70)
    scene_id = "S1D_IW_GRDH_1SDV_20260830T120410_20260830T120435_004355_0080AB_66FC_COG"
    
    # Location 1: Meghalaya Point 1
    lat1, lon1, rad = 25.503288765043795, 91.33652307913866, 5.0
    r1 = process_scene_raster(scene_id, lat1, lon1, rad)
    key1 = get_aoi_cache_key(lat1, lon1, rad)
    print(f"Location 1 ({lat1:.4f}, {lon1:.4f}) -> Key: {key1} | Status: {r1['status']}")
    
    # Location 2: Meghalaya Point 2 (3.4km away)
    lat2, lon2 = 25.52706310546959, 91.35848472637227
    key2 = get_aoi_cache_key(lat2, lon2, rad)
    print(f"Location 2 ({lat2:.4f}, {lon2:.4f}) -> Processing for Key: {key2}...")
    r2 = process_scene_raster(scene_id, lat2, lon2, rad)
    print(f"Location 2 Status: {r2['status']} | Key: {r2['aoi_key']}")
    
    # Verify both AOI directories exist under the same scene_id
    dir1 = resolve_scene_cache_dir(scene_id, key1)
    dir2 = resolve_scene_cache_dir(scene_id, key2)
    print(f"Dir 1 Path: {dir1}")
    print(f"Dir 2 Path: {dir2}")
    
    assert dir1 and os.path.exists(dir1), f"Directory {dir1} should exist"
    assert dir2 and os.path.exists(dir2), f"Directory {dir2} should exist"
    assert dir1 != dir2, "Both directories should be distinct"
    
    # Verify metadata coordinates
    with open(os.path.join(dir1, "metadata.json")) as f:
        m1 = json.load(f)
    with open(os.path.join(dir2, "metadata.json")) as f:
        m2 = json.load(f)
        
    print(f"Dir 1 Metadata Lat/Lon: {m1['aoi_coordinates']['latitude']}, {m1['aoi_coordinates']['longitude']}")
    print(f"Dir 2 Metadata Lat/Lon: {m2['aoi_coordinates']['latitude']}, {m2['aoi_coordinates']['longitude']}")
    print(">>> SCENARIO B PASSED.")

def test_scenario_c():
    print("\n" + "=" * 70)
    print("SCENARIO C: Multi-temporal Same AOI Alignment")
    print("=" * 70)
    ref_id = "S1D_IW_GRDH_1SDV_20260818T120500_20260818T120525_004180_007A7E_C8D7_COG"
    comp_id = "S1D_IW_GRDH_1SDV_20260830T120500_20260830T120525_004355_0080AB_75B8_COG"
    lat, lon, rad = 27.3314, 88.6138, 5.0
    aoi_key = get_aoi_cache_key(lat, lon, rad)
    
    # Process both
    process_scene_raster(ref_id, lat, lon, rad)
    process_scene_raster(comp_id, lat, lon, rad)
    
    change = SatelliteChangeService.calculate_temporal_change(ref_id, comp_id, aoi_key=aoi_key)
    print("Change calculation successful!")
    print("Ref Acquisition:", change["metadata"]["reference_acquisition_time"])
    print("Comp Acquisition:", change["metadata"]["comparison_acquisition_time"])
    print("Valid pixel count:", change["metadata"]["valid_pixel_count"])
    assert change["metadata"]["valid_pixel_count"] > 0
    print(">>> SCENARIO C PASSED.")

def test_scenario_d():
    print("\n" + "=" * 70)
    print("SCENARIO D: Regression Test — Dashboard Failure Coordinates")
    print("=" * 70)
    lat = 25.52706310546959
    lon = 91.35848472637227
    rad = 5.0
    
    print(f"Testing AutomaticSatellitePairService for Lat={lat}, Lon={lon}, Radius={rad}")
    result = AutomaticSatellitePairService.analyze_location_change(lat, lon, rad)
    ref_s_id = result["metadata"]["reference_scene"]["scene_id"]
    comp_s_id = result["metadata"]["comparison_scene"]["scene_id"]
    print("Selected Pair:", ref_s_id[:35], "...", "vs", comp_s_id[:35], "...")
    print("Temporal Separation:", result["metadata"]["temporal_separation_days"], "days")
    print("RSCI Score:", result["radar_surface_change_signal"]["radar_surface_change_index"])
    print("Category:", result["radar_surface_change_signal"]["category"])
    
    assert result["status"] == "PAIRED_SUCCESS"
    assert result["radar_surface_change_signal"]["radar_surface_change_index"] >= 0
    print(">>> SCENARIO D PASSED.")

def test_scenario_e():
    print("\n" + "=" * 70)
    print("SCENARIO E: Regression Test — Gangtok Coordinates")
    print("=" * 70)
    lat = 27.3314
    lon = 88.6138
    rad = 5.0
    
    print(f"Testing AutomaticSatellitePairService for Gangtok (Lat={lat}, Lon={lon})")
    result = AutomaticSatellitePairService.analyze_location_change(lat, lon, rad)
    print("Result Status:", result["status"])
    ref_s_id = result["metadata"]["reference_scene"]["scene_id"]
    comp_s_id = result["metadata"]["comparison_scene"]["scene_id"]
    print("Selected Pair:", ref_s_id[:35], "...", "vs", comp_s_id[:35], "...")
    print("Temporal Separation:", result["metadata"]["temporal_separation_days"], "days")
    print("RSCI Score:", result["radar_surface_change_signal"]["radar_surface_change_index"])
    print("Category:", result["radar_surface_change_signal"]["category"])
    
    assert result["status"] == "PAIRED_SUCCESS"
    assert result["radar_surface_change_signal"]["radar_surface_change_index"] >= 0
    print(">>> SCENARIO E PASSED.")

if __name__ == "__main__":
    test_scenario_a()
    test_scenario_b()
    test_scenario_c()
    test_scenario_d()
    test_scenario_e()
    print("\n" + "=" * 70)
    print("ALL VERIFICATION SCENARIOS (A - E) PASSED SUCCESSFULLY!")
    print("=" * 70)
