import urllib.request
import urllib.error
import json

def test_endpoint(url, expected_status=200):
    print(f"\nQuerying: {url}")
    req = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(req) as response:
            status_code = response.status
            content_type = response.headers.get("Content-Type")
            raster_bounds = response.headers.get("X-Raster-Bounds")
            
            print(f"  Response Status: {status_code}")
            print(f"  Content-Type: {content_type}")
            print(f"  X-Raster-Bounds: {raster_bounds}")
            
            assert status_code == expected_status, f"Expected {expected_status}, got {status_code}"
            if expected_status == 200:
                assert content_type == "image/png", f"Expected image/png, got {content_type}"
                assert raster_bounds is not None, "Expected X-Raster-Bounds header, got None"
                
                # Verify bounds structure
                bounds = json.loads(raster_bounds)
                assert len(bounds) == 2, "Bounds must contain 2 points [[lat, lng], [lat, lng]]"
                assert len(bounds[0]) == 2 and len(bounds[1]) == 2, "Each point must have 2 coordinate floats"
                print("  [OK] Header and PNG verification succeeded.")
                
    except urllib.error.HTTPError as e:
        print(f"  HTTP Error: {e.code} - {e.reason}")
        if expected_status != 200:
            assert e.code == expected_status, f"Expected error {expected_status}, got {e.code}"
            print(f"  [OK] Succeeded with expected HTTP Error {e.code}.")
        else:
            raise e

def run_all_tests():
    # Valid cached scene from directory listing
    scene_id = "S1D_IW_GRDH_1SDV_20260827T234632_20260827T234657_004318_007F6B_A6D1_COG"
    
    print(f"=== Starting Raster Overlay Endpoint Verification (Target Scene: {scene_id}) ===")
    
    # 1. Terrain Slope Overlay
    test_endpoint(f"http://localhost:8000/api/v1/terrain/scenes/{scene_id}/overlay?layer=slope")
    
    # 2. Terrain DEM Overlay
    test_endpoint(f"http://localhost:8000/api/v1/terrain/scenes/{scene_id}/overlay?layer=dem")
    
    # 3. Terrain Aspect Overlay
    test_endpoint(f"http://localhost:8000/api/v1/terrain/scenes/{scene_id}/overlay?layer=aspect")
    
    # 4. Satellite VV Overlay
    test_endpoint(f"http://localhost:8000/api/v1/satellite/scenes/{scene_id}/overlay?layer=vv")
    
    # 5. Satellite VH Overlay
    test_endpoint(f"http://localhost:8000/api/v1/satellite/scenes/{scene_id}/overlay?layer=vh")
    
    # 6. Invalid Layer Name (Terrain)
    test_endpoint(f"http://localhost:8000/api/v1/terrain/scenes/{scene_id}/overlay?layer=invalid", expected_status=400)
    
    # 7. Invalid Layer Name (Satellite)
    test_endpoint(f"http://localhost:8000/api/v1/satellite/scenes/{scene_id}/overlay?layer=invalid", expected_status=400)
    
    # 8. Missing Scene ID
    missing_scene = "S1D_IW_GRDH_1SDV_00000000T000000_00000000T000000_000000_000000_0000_COG"
    test_endpoint(f"http://localhost:8000/api/v1/terrain/scenes/{missing_scene}/overlay?layer=slope", expected_status=404)
    
    print("\n=== All Raster Overlay Tests Completed Successfully! ===")

if __name__ == "__main__":
    run_all_tests()
