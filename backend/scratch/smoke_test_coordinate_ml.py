"""
Coordinate-Based Susceptibility Inference Smoke Test - Phase 3 Checkpoint 11G

Tests on-the-fly point terrain fetches and ML susceptibility scores for three
physically distinct locations in Northeast India (Guwahati, Shillong, Gangtok).
"""

import os
import sys
import time

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.abspath(os.path.join(SCRIPTS_DIR, ".."))
sys.path.insert(0, BACKEND_DIR)

from app.services.terrain_service import extract_point_terrain
from app.services.ml_susceptibility_service import MLSusceptibilityService

def run_tests():
    print("=== Commencing Coordinate-Based ML Inference Smoke Test ===")
    
    locations = [
        {"name": "Flat Location (Guwahati, Assam)", "lat": 26.1405, "lon": 91.7302},
        {"name": "Hilly Location (Shillong, Meghalaya)", "lat": 25.5788, "lon": 91.8827},
        {"name": "Steep Himalayan Location (Gangtok, Sikkim)", "lat": 27.3314, "lon": 88.6138}
    ]
    
    for loc in locations:
        print(f"\nTesting: {loc['name']} | Lat: {loc['lat']} | Lon: {loc['lon']}")
        start_time = time.time()
        
        # 1. Extract point terrain on-the-fly
        terrain_data = extract_point_terrain(loc["lat"], loc["lon"])
        
        # 2. Predict ML susceptibility
        pred = MLSusceptibilityService.predict_susceptibility(
            latitude=loc["lat"],
            longitude=loc["lon"],
            elevation=terrain_data["elevation"],
            slope=terrain_data["slope"],
            aspect=terrain_data["aspect"]
        )
        
        duration = time.time() - start_time
        print(f"  Extracted Terrain: Elevation={terrain_data['elevation']}m | Slope={terrain_data['slope']}° | Aspect={terrain_data['aspect']}°")
        print(f"  ML Prediction:     Probability={pred['probability']:.4f} | Risk={pred['risk_level']} | Susceptible={pred['is_susceptible']}")
        print(f"  Execution Time:    {duration*1000:.2f}ms")
        
        # Basic Validation Assertions
        assert 0.0 <= pred["probability"] <= 1.0, f"Probability out of bounds: {pred['probability']}"
        assert pred["risk_level"] in ("Low", "Moderate", "High", "Very High"), f"Invalid risk level: {pred['risk_level']}"
        assert terrain_data["elevation"] >= -100.0, f"Suspicious elevation: {terrain_data['elevation']}m"
        assert 0.0 <= terrain_data["slope"] <= 90.0, f"Slope out of bounds: {terrain_data['slope']}°"
        
    print("\n=== All Coordinate-Based Tests PASSED successfully! ===")

if __name__ == "__main__":
    run_tests()
