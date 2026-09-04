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

def audit_legacy_safety():
    print("\n" + "=" * 70)
    print("AUDIT 1: Legacy Cache Safety & Multi-AOI Resolution")
    print("=" * 70)
    scene_id = "S1D_IW_GRDH_1SDV_20260830T120410_20260830T120435_004355_0080AB_66FC_COG"
    key1 = "aoi_25.5033_91.3365_5.0km"
    key2 = "aoi_25.5271_91.3585_5.0km"
    
    dir1 = resolve_scene_cache_dir(scene_id, key1)
    dir2 = resolve_scene_cache_dir(scene_id, key2)
    dir_none = resolve_scene_cache_dir(scene_id, None)
    
    print("Key 1 Resolved Dir:", dir1)
    print("Key 2 Resolved Dir:", dir2)
    print("None Key Resolved Dir:", dir_none)
    
    assert dir1 and os.path.exists(dir1), "Key 1 must resolve to existing directory"
    assert dir2 and os.path.exists(dir2), "Key 2 must resolve to existing directory"
    assert dir1 != dir2, "Keys 1 and 2 must resolve to distinct directories"
    print(">>> AUDIT 1 PASSED.")

def audit_optional_key_common_intersection():
    print("\n" + "=" * 70)
    print("AUDIT 2: Implicit Common AOI Key Resolution in SatelliteChangeService")
    print("=" * 70)
    ref_id = "S1D_IW_GRDH_1SDV_20260818T120500_20260818T120525_004180_007A7E_C8D7_COG"
    comp_id = "S1D_IW_GRDH_1SDV_20260830T120500_20260830T120525_004355_0080AB_75B8_COG"
    
    # Call calculate_temporal_change WITHOUT aoi_key
    res = SatelliteChangeService.calculate_temporal_change(ref_id, comp_id, aoi_key=None)
    print("Automatic Common AOI Resolution Success!")
    print("Ref Scene:", res["metadata"]["reference_scene_id"][:35], "...")
    print("Comp Scene:", res["metadata"]["comparison_scene_id"][:35], "...")
    print("Valid Pixels:", res["metadata"]["valid_pixel_count"])
    assert res["metadata"]["valid_pixel_count"] > 0
    print(">>> AUDIT 2 PASSED.")

def audit_meghalaya_regression():
    print("\n" + "=" * 70)
    print("AUDIT 3: Meghalaya Dashboard Coordinate Regression")
    print("=" * 70)
    lat = 25.52706310546959
    lon = 91.35848472637227
    rad = 5.0
    
    res = AutomaticSatellitePairService.analyze_location_change(lat, lon, rad)
    print("Status:", res["status"])
    ref = res["metadata"]["reference_scene"]["scene_id"]
    comp = res["metadata"]["comparison_scene"]["scene_id"]
    print("Pair:", ref[:35], "... vs", comp[:35], "...")
    print("Temporal Separation:", res["metadata"]["temporal_separation_days"], "days")
    print("RSCI Score:", res["radar_surface_change_signal"]["radar_surface_change_index"])
    print("Category:", res["radar_surface_change_signal"]["category"])
    
    assert res["status"] == "PAIRED_SUCCESS"
    assert res["radar_surface_change_signal"]["radar_surface_change_index"] >= 0
    print(">>> AUDIT 3 PASSED.")

def audit_gangtok_regression():
    print("\n" + "=" * 70)
    print("AUDIT 4: Gangtok Coordinate Regression")
    print("=" * 70)
    lat = 27.3314
    lon = 88.6138
    rad = 5.0
    
    res = AutomaticSatellitePairService.analyze_location_change(lat, lon, rad)
    print("Status:", res["status"])
    ref = res["metadata"]["reference_scene"]["scene_id"]
    comp = res["metadata"]["comparison_scene"]["scene_id"]
    print("Pair:", ref[:35], "... vs", comp[:35], "...")
    print("Temporal Separation:", res["metadata"]["temporal_separation_days"], "days")
    print("RSCI Score:", res["radar_surface_change_signal"]["radar_surface_change_index"])
    print("Category:", res["radar_surface_change_signal"]["category"])
    
    assert res["status"] == "PAIRED_SUCCESS"
    assert res["radar_surface_change_signal"]["radar_surface_change_index"] >= 0
    print(">>> AUDIT 4 PASSED.")

if __name__ == "__main__":
    audit_legacy_safety()
    audit_optional_key_common_intersection()
    audit_meghalaya_regression()
    audit_gangtok_regression()
    print("\n" + "=" * 70)
    print("ALL CONSISTENCY AUDIT CHECKS PASSED!")
    print("=" * 70)
