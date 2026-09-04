"""
Composite Risk API Smoke Test - Phase 4 Checkpoint 12.3

Performs local HTTP requests using TestClient to verify the endpoint:
POST /api/v1/risk/composite
"""

import os
import sys

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.abspath(os.path.join(SCRIPTS_DIR, ".."))
sys.path.insert(0, BACKEND_DIR)

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_coordinate(name: str, lat: float, lon: float):
    print("=" * 60)
    print(f"LOCATION: {name}")
    print(f"COORDINATES: Lat={lat}, Lon={lon}")
    print("-" * 60)
    
    payload = {
        "latitude": lat,
        "longitude": lon
    }
    
    response = client.post("/api/v1/risk/composite", json=payload)
    
    if response.status_code != 200:
        print(f"HTTP ERROR {response.status_code}: {response.json()}")
        return False
        
    data = response.json()
    
    # Assertions / Validations
    assert data["status"] == "success"
    assert "composite_risk_index" in data
    assert "risk_level" in data
    assert "components" in data
    assert "terrain" in data
    
    comp = data["components"]
    assert "static_susceptibility" in comp
    assert "historical_context" in comp
    assert "rainfall_trigger" in comp
    
    print(f"Composite Risk Index: {data['composite_risk_index']}")
    print(f"Risk Level:           {data['risk_level']}")
    print()
    print("ML Static Susceptibility:")
    print(f"  Probability: {comp['static_susceptibility']['probability']:.4f}")
    print(f"  Index:       {comp['static_susceptibility']['index']:.2f}")
    print()
    print("Historical Vulnerability:")
    print(f"  Proximity Score: {comp['historical_context']['proximity_score']:.2f}")
    print(f"  Density Score:   {comp['historical_context']['density_score']:.2f}")
    print(f"  History Score:   {comp['historical_context']['historical_score']:.2f}")
    print(f"  Multiplier:      {comp['historical_context']['multiplier']:.4f}")
    print()
    print("Rainfall Trigger:")
    print(f"  Daily Score:     {comp['rainfall_trigger']['daily_score']:.2f}")
    print(f"  3-Day Score:     {comp['rainfall_trigger']['three_day_score']:.2f}")
    print(f"  7-Day Score:     {comp['rainfall_trigger']['seven_day_score']:.2f}")
    print(f"  Rain Score:      {comp['rainfall_trigger']['rainfall_score']:.2f}")
    print(f"  Multiplier:      {comp['rainfall_trigger']['multiplier']:.4f}")
    print()
    print("Terrain:")
    print(f"  Elevation: {data['terrain']['elevation']:.2f} m")
    print(f"  Slope:     {data['terrain']['slope']:.2f}°")
    print(f"  Aspect:    {data['terrain']['aspect']:.2f}°")
    print()
    print("Explanation:")
    print(f"  {data['explanation']}")
    print("=" * 60)
    print()
    return True

def test_invalid_coordinates():
    print("=" * 60)
    print("TESTING INVALID COORDINATES (Lat=120.0)")
    print("-" * 60)
    
    payload = {
        "latitude": 120.0,
        "longitude": 91.7302
    }
    
    response = client.post("/api/v1/risk/composite", json=payload)
    print(f"Status Code (Expected 422 for Pydantic bounds): {response.status_code}")
    print(f"Response: {response.json()}")
    print("=" * 60)
    print()
    assert response.status_code == 422

if __name__ == "__main__":
    success = True
    success &= test_coordinate("Guwahati (Assam plains)", 26.1405, 91.7302)
    success &= test_coordinate("Shillong (Meghalaya)", 25.5788, 91.8827)
    success &= test_coordinate("Gangtok (Sikkim)", 27.3314, 88.6138)
    
    test_invalid_coordinates()
    
    if success:
        print("ALL API CHECKS PASSED SUCCESSFULLY.")
        sys.exit(0)
    else:
        print("SOME API CHECKS FAILED.")
        sys.exit(1)
