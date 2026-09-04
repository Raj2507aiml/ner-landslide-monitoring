"""
Automatic Satellite Change API Smoke Test - Phase 5 Checkpoint 14.3

Performs local HTTP requests using TestClient to verify the endpoint:
POST /api/v1/satellite/automatic-change-analysis
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
    lat = 27.3314
    lon = 88.6138
    
    print("=" * 60)
    print("AUTOMATIC SATELLITE CHANGE API SMOKE TEST")
    print(f"Coordinates: Lat={lat}, Lon={lon}")
    print("-" * 60)
    
    payload = {
        "latitude": lat,
        "longitude": lon
    }
    
    response = client.post("/api/v1/satellite/automatic-change-analysis", json=payload)
    
    if response.status_code != 200:
        print(f"HTTP ERROR {response.status_code}: {response.json()}")
        sys.exit(1)
        
    data = response.json()
    print("HTTP SUCCESS (200 OK)")
    print(f"Status: {data['status']}")
    print()
    
    if data["status"] != "PAIRED_SUCCESS":
        print(f"Failure Message: {data.get('message')}")
        sys.exit(1)
        
    meta = data["metadata"]
    print("[Paired Scene Metadata]")
    print(f"  Orbit Direction:          {meta['orbit_direction']}")
    print(f"  Temporal Separation Days: {meta['temporal_separation_days']} days")
    print("  Reference Scene:")
    print(f"    ID:   {meta['reference_scene']['scene_id']}")
    print(f"    Time: {meta['reference_scene']['acquisition_time']}")
    print("  Comparison Scene:")
    print(f"    ID:   {meta['comparison_scene']['scene_id']}")
    print(f"    Time: {meta['comparison_scene']['acquisition_time']}")
    
    signal = data["radar_surface_change_signal"]
    print("\n[Radar Surface Change Signal]")
    print(f"  RSCI Score:             {signal['radar_surface_change_index']} / 100")
    print(f"  Category:               {signal['category']}")
    print(f"  Spatial Extent Score:   {signal['spatial_extent_score']} / 100")
    print(f"  Anomaly Magnitude Score: {signal['anomaly_magnitude_score']} / 100")
    print(f"  Notice:                 {signal['scientific_notice']}")
    print()
    
    # Assertions
    assert data["status"] == "PAIRED_SUCCESS"
    assert signal["category"] == "Stable"
    # RSCI can be ~1.82 (newest Aug 30/Aug 18 pair) or ~5.31 (Aug 11/July 30 pair) depending on catalog query timing
    rsci = signal["radar_surface_change_index"]
    assert abs(rsci - 5.31) < 0.15 or abs(rsci - 1.82) < 0.15, f"Unexpected RSCI score: {rsci}"
    
    print("VERIFICATION SUCCESSFUL: API correctly returned RSCI change data and category Stable.")
    print("=" * 60)

if __name__ == "__main__":
    main()
