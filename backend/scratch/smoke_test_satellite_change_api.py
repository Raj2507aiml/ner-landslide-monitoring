"""
Satellite Change API Smoke Test - Phase 5 Checkpoint 14.0

Performs local HTTP requests using TestClient to verify the endpoint:
POST /api/v1/satellite/change-analysis
"""

import os
import sys

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.abspath(os.path.join(SCRIPTS_DIR, ".."))
sys.path.insert(0, BACKEND_DIR)

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def main():
    ref_scene = "S1D_IW_GRDH_1SDV_20260730T121311_20260730T121336_003903_0070EA_F56C_COG"
    comp_scene = "S1D_IW_GRDH_1SDV_20260811T121312_20260811T121337_004078_0076F9_676B_COG"
    
    print("=" * 60)
    print("SATELLITE CHANGE ANALYSIS API SMOKE TEST")
    print(f"Ref Scene:  {ref_scene}")
    print(f"Comp Scene: {comp_scene}")
    print("-" * 60)
    
    payload = {
        "reference_scene_id": ref_scene,
        "comparison_scene_id": comp_scene
    }
    
    response = client.post("/api/v1/satellite/change-analysis", json=payload)
    
    if response.status_code != 200:
        print(f"HTTP ERROR {response.status_code}: {response.json()}")
        sys.exit(1)
        
    data = response.json()
    
    print("HTTP SUCCESS (200 OK)")
    print()
    
    # Verify presence of main sections
    assert "metadata" in data
    assert "temporal_change_indicators" in data
    assert "radar_surface_change_signal" in data
    
    meta = data["metadata"]
    print("[Metadata]")
    print(f"  Ref Acquisition: {meta['reference_acquisition_time']}")
    print(f"  Comp Acquisition: {meta['comparison_acquisition_time']}")
    print(f"  Valid overlap percentage: {meta['valid_pixel_percentage']}%")
    print()
    
    signal = data["radar_surface_change_signal"]
    print("[Radar Surface Change Signal]")
    print(f"  RSCI Score:             {signal['radar_surface_change_index']} / 100")
    print(f"  Category:               {signal['category']}")
    print(f"  Spatial Extent Score:   {signal['spatial_extent_score']} / 100")
    print(f"  Anomaly Magnitude Score: {signal['anomaly_magnitude_score']} / 100")
    print(f"  Notice:                 {signal['scientific_notice']}")
    print()
    
    # Assertions on expected Gangtok values
    assert signal['category'] == "Stable", f"Expected category Stable, got {signal['category']}"
    assert abs(signal['radar_surface_change_index'] - 5.31) < 0.1, f"Expected RSCI ~5.31, got {signal['radar_surface_change_index']}"
    
    print("VERIFICATION SUCCESSFUL: API correctly returned RSCI ~5.31 and category Stable.")
    print("=" * 60)

if __name__ == "__main__":
    main()
