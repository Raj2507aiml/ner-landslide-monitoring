"""
Early Warning API Smoke Test - Phase 6 Checkpoint 15.3

Performs local HTTP requests using TestClient to verify the early warning endpoint.
"""

import os
import sys
from unittest.mock import patch

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.abspath(os.path.join(SCRIPTS_DIR, ".."))
sys.path.insert(0, BACKEND_DIR)

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def main():
    print("=" * 60)
    print("EARLY WARNING DECISION API SMOKE TEST")
    print("-" * 60)
    
    # ----------------------------------------------------
    # Test A: Gangtok location with successful satellite pairing
    # ----------------------------------------------------
    lat_gt = 27.3314
    lon_gt = 88.6138
    print(f"Test A: Gangtok coordinates (Lat={lat_gt}, Lon={lon_gt})")
    
    payload_gt = {
        "latitude": lat_gt,
        "longitude": lon_gt
    }
    
    response_gt = client.post("/api/v1/early-warning/analyze", json=payload_gt)
    
    if response_gt.status_code != 200:
        print(f"HTTP ERROR {response_gt.status_code}: {response_gt.json()}")
        sys.exit(1)
        
    data_gt = response_gt.json()
    print("HTTP SUCCESS (200 OK)")
    print(f"  Warning Level:      {data_gt['warning_level']}")
    print(f"  Decision Mode:      {data_gt['decision_mode']}")
    print(f"  Hazard Index:       {data_gt['hazard_context']['composite_hazard_index']}")
    print(f"  Hazard Category:    {data_gt['hazard_context']['hazard_category']}")
    print(f"  Satellite Status:   {data_gt['satellite_context']['status']}")
    print(f"  RSCI Score:         {data_gt['satellite_context']['rsci']}")
    print(f"  RSCI Category:      {data_gt['satellite_context']['category']}")
    print(f"  Recommended Action: {data_gt['recommended_action']}")
    print(f"  Notice Present:     {'scientific_notice' in data_gt}")
    print()
    
    # Assertions for Test A
    assert response_gt.status_code == 200
    assert data_gt["warning_level"] in ["NORMAL", "WATCH", "ALERT", "CRITICAL"]
    assert data_gt["decision_mode"] == "FULL_EVIDENCE"
    assert data_gt["satellite_context"]["status"] == "PAIRED_SUCCESS"
    assert data_gt["satellite_context"]["rsci"] is not None
    assert "scientific_notice" in data_gt
    print("Test A: Passed")
    print("-" * 60)
    
    # ----------------------------------------------------
    # Test B: Location where satellite evidence is unavailable
    # ----------------------------------------------------
    print(f"Test B: Mocking satellite unavailable fallback for Gangtok")
    
    mock_response = {
        "status": "GEOMETRY_MISMATCH",
        "message": "No compatible scene pair found for change analysis."
    }
    
    with patch("app.services.automatic_satellite_pair_service.AutomaticSatellitePairService.analyze_location_change", return_value=mock_response):
        response_fb = client.post("/api/v1/early-warning/analyze", json=payload_gt)
        
    if response_fb.status_code != 200:
        print(f"HTTP ERROR {response_fb.status_code}: {response_fb.json()}")
        sys.exit(1)
        
    data_fb = response_fb.json()
    print("HTTP SUCCESS (200 OK)")
    print(f"  Warning Level:      {data_fb['warning_level']}")
    print(f"  Decision Mode:      {data_fb['decision_mode']}")
    print(f"  Hazard Index:       {data_fb['hazard_context']['composite_hazard_index']}")
    print(f"  Satellite Status:   {data_fb['satellite_context']['status']}")
    print(f"  RSCI Score:         {data_fb['satellite_context']['rsci']}")
    print(f"  RSCI Category:      {data_fb['satellite_context']['category']}")
    print(f"  Recommended Action: {data_fb['recommended_action']}")
    print(f"  Notice Present:     {'scientific_notice' in data_fb}")
    print()
    
    # Assertions for Test B
    assert response_fb.status_code == 200
    assert data_fb["decision_mode"] == "METEOROLOGICAL_FALLBACK"
    assert data_fb["satellite_context"]["status"] == "GEOMETRY_MISMATCH"
    assert data_fb["satellite_context"]["rsci"] is None
    assert data_fb["satellite_context"]["category"] is None
    assert "scientific_notice" in data_fb
    print("Test B: Passed")
    
    print("=" * 60)
    print("VERIFICATION SUCCESSFUL: Early Warning API evaluates correctly.")
    print("=" * 60)

if __name__ == "__main__":
    main()
