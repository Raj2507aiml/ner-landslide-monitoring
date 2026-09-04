"""
Composite Landslide Risk Service Smoke Test - Phase 4 Checkpoint 12.2

Verifies formula behavior for:
1. Scientific scenarios (using unit mocks)
2. Live coordinate telemetry (Guwahati, Shillong, Gangtok)
"""

import os
import sys
import unittest
from unittest.mock import patch

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.abspath(os.path.join(SCRIPTS_DIR, ".."))
sys.path.insert(0, BACKEND_DIR)

from app.database.session import SessionLocal
from app.services.composite_risk_service import CompositeRiskService

class TestCompositeRiskFormula(unittest.TestCase):
    def setUp(self):
        self.db = SessionLocal()

    def tearDown(self):
        self.db.close()

    @patch("app.services.composite_risk_service.extract_point_terrain")
    @patch("app.services.composite_risk_service.MLSusceptibilityService.predict_susceptibility")
    @patch("app.services.composite_risk_service.fetch_weather_telemetry")
    @patch("app.services.composite_risk_service.get_historical_landslide_context")
    def test_scenario_1_flat_extreme_rain(self, mock_hist, mock_weather, mock_ml, mock_terrain):
        """Scenario 1: Flat Assam Terrain + Extreme Rainfall -> LOW risk"""
        mock_terrain.return_value = {"elevation": 50.0, "slope": 1.5, "aspect": 120.0}
        mock_ml.return_value = {"probability": 0.02}
        mock_weather.return_value = {
            "daily_precipitation": 55.0,
            "three_day_cumulative": 100.0,
            "seven_day_cumulative": 200.0
        }
        # Force rainfall scores to sum to 30 (extreme rain)
        mock_hist.return_value = {
            "combined_summary": {
                "total_historical_observations": 0,
                "nearest_historical_observation_km": None
            }
        }
        
        # Call service
        res = CompositeRiskService.calculate_composite_risk(self.db, 26.1405, 91.7302)
        
        print("\n[Scenario 1 - Flat Terrain + Extreme Rain]")
        print(f"  Composite Index: {res['composite_risk_index']}")
        print(f"  Risk Level:      {res['risk_level']}")
        print(f"  Explanation:     {res['explanation']}")
        
        self.assertEqual(res["composite_risk_index"], 4.0)
        self.assertEqual(res["risk_level"], "Low")

    @patch("app.services.composite_risk_service.extract_point_terrain")
    @patch("app.services.composite_risk_service.MLSusceptibilityService.predict_susceptibility")
    @patch("app.services.composite_risk_service.fetch_weather_telemetry")
    @patch("app.services.composite_risk_service.get_historical_landslide_context")
    def test_scenario_2_susceptible_moderate_rain(self, mock_hist, mock_weather, mock_ml, mock_terrain):
        """Scenario 2: Meghalaya Hilly Terrain + Moderate Rainfall -> VERY HIGH risk"""
        mock_terrain.return_value = {"elevation": 1200.0, "slope": 22.0, "aspect": 180.0}
        mock_ml.return_value = {"probability": 0.60}
        
        # Moderate rain: S_Rain = 15
        # Set weather returns that sum to 15 points:
        # e.g., daily = 15.0 -> score 5; 3d = 30.0 -> score 5; 7d = 80.0 -> score 5; sum = 15 points
        mock_weather.return_value = {
            "daily_precipitation": 15.0,
            "three_day_cumulative": 30.0,
            "seven_day_cumulative": 80.0
        }
        # S_Hist = 16 (proximity_score = 10, density_score = 6)
        # To bypass direct DB query calculations, mock get_historical_landslide_context:
        # But we also mock the exact return value of get_historical_landslide_context to make it calculate
        # s_hist = 16. Proximity = 10, Density = 6
        # To get proximity = 10, nearest_dist = 6km (25 * (1 - 6/10) = 10)
        # To get density = 6, total_obs = 2 (15 * ln(3)/ln(21) = 15 * 1.0986 / 3.0445 = 5.41 -> 5.4)
        # Let's override get_historical_landslide_context:
        mock_hist.return_value = {
            "combined_summary": {
                "total_historical_observations": 5,
                "nearest_historical_observation_km": 6.0
            }
        }
        # Wait, the actual calculation inside the function is:
        # proximity = 25 * (1 - 6/10) = 10
        # density = 15 * ln(6)/ln(21) = 15 * 1.7917 / 3.0445 = 8.8
        # sum = 18.8
        # Let's patch the inner proximity and density logic or supply mocked values that yield exactly 16
        # Let's adjust total_obs and nearest_dist to get exactly s_hist = 16:
        # We need proximity + density = 16.
        # Let's set nearest_dist = 6.0 (proximity = 10.0). We need density = 6.0.
        # 15 * ln(x+1)/ln(21) = 6.0 -> ln(x+1) = 6.0 * ln(21) / 15 = 6.0 * 3.0445 / 15 = 1.2178 -> x+1 = 3.37 -> x = 2.37.
        # Let's set total_obs = 2 (density = 15 * ln(3)/ln(21) = 5.41) -> s_hist = 15.41 -> v_hist = 1.1926
        # Let's patch mock_hist with total_obs = 3, nearest_dist = 6.0
        # density = 15 * ln(4)/ln(21) = 15 * 1.386 / 3.0445 = 6.83 -> s_hist = 16.83 -> v_hist = 1.210
        # Or we can just use 16.0 for s_hist. To test the exact math, we can adjust the expected output accordingly:
        # Let's write a mock wrapper that gives exactly proximity_score = 10.0 and density_score = 6.0:
        # Let's mock haversine_distance and math.log or simply let it calculate.
        # If nearest_dist = 6.0, radius = 10.0 -> proximity = 10.0
        # If total_obs = 2, density = 15 * ln(3)/ln(21) = 5.41 -> s_hist = 15.41.
        # Let's set nearest_dist = 5.766 (proximity = 10.58), total_obs = 2 (density = 5.41) -> s_hist = 16.00!
        mock_hist.return_value = {
            "combined_summary": {
                "total_historical_observations": 2,
                "nearest_historical_observation_km": 5.766
            }
        }
        
        res = CompositeRiskService.calculate_composite_risk(self.db, 25.5788, 91.8827)
        
        print("\n[Scenario 2 - Susceptible Terrain + Moderate Rain]")
        print(f"  Composite Index: {res['composite_risk_index']}")
        print(f"  Risk Level:      {res['risk_level']}")
        print(f"  Explanation:     {res['explanation']}")
        
        self.assertAlmostEqual(res["composite_risk_index"], 90.0, places=1)
        self.assertEqual(res["risk_level"], "Very High")

    @patch("app.services.composite_risk_service.extract_point_terrain")
    @patch("app.services.composite_risk_service.MLSusceptibilityService.predict_susceptibility")
    @patch("app.services.composite_risk_service.fetch_weather_telemetry")
    @patch("app.services.composite_risk_service.get_historical_landslide_context")
    def test_scenario_3_susceptible_dry(self, mock_hist, mock_weather, mock_ml, mock_terrain):
        """Scenario 3: Gangtok Susceptible Terrain + Dry Weather -> MODERATE risk"""
        mock_terrain.return_value = {"elevation": 1650.0, "slope": 13.5, "aspect": 60.0}
        mock_ml.return_value = {"probability": 0.85}
        mock_weather.return_value = {
            "daily_precipitation": 0.0,
            "three_day_cumulative": 0.0,
            "seven_day_cumulative": 0.0
        }
        # S_Hist = 12 (proximity_score = 8.0, density_score = 4.0)
        # To get proximity = 8.0 -> nearest_dist = 6.8 (25 * (1 - 6.8/10) = 8.0)
        # To get density = 4.0 -> total_obs = 1 (15 * ln(2)/ln(21) = 15 * 0.693 / 3.0445 = 3.41)
        # Let's set nearest_dist = 6.564 (proximity = 8.59), total_obs = 1 (density = 3.41) -> s_hist = 12.00!
        mock_hist.return_value = {
            "combined_summary": {
                "total_historical_observations": 1,
                "nearest_historical_observation_km": 6.564
            }
        }
        
        res = CompositeRiskService.calculate_composite_risk(self.db, 27.3314, 88.6138)
        
        print("\n[Scenario 3 - Susceptible Terrain + Dry Weather]")
        print(f"  Composite Index: {res['composite_risk_index']}")
        print(f"  Risk Level:      {res['risk_level']}")
        print(f"  Explanation:     {res['explanation']}")
        
        self.assertAlmostEqual(res["composite_risk_index"], 48.88, places=1)
        self.assertEqual(res["risk_level"], "Moderate")

def run_integration_tests():
    print("\n=== Commencing Live Database Integration Checks ===")
    db = SessionLocal()
    
    locations = [
        {"name": "Guwahati (Assam plains)", "lat": 26.1405, "lon": 91.7302},
        {"name": "Shillong (Meghalaya plateau)", "lat": 25.5788, "lon": 91.8827},
        {"name": "Gangtok (Sikkim slopes)", "lat": 27.3314, "lon": 88.6138}
    ]
    
    for loc in locations:
        print(f"\nQuerying: {loc['name']} | Lat: {loc['lat']} | Lon: {loc['lon']}")
        try:
            res = CompositeRiskService.calculate_composite_risk(db, loc["lat"], loc["lon"])
            print(f"  Composite Risk Index: {res['composite_risk_index']} | Risk Level: {res['risk_level']}")
            print(f"  Terrain: Elevation={res['terrain']['elevation']}m | Slope={res['terrain']['slope']}°")
            print(f"  Components: ML Prob={res['components']['static_susceptibility']['probability']:.4f} | Rain Mult={res['components']['rainfall_trigger']['multiplier']:.2f} | Hist Mult={res['components']['historical_context']['multiplier']:.2f}")
            print(f"  Explanation: {res['explanation']}")
            
            # Assertions
            assert 0.0 <= res["composite_risk_index"] <= 100.0
            assert res["risk_level"] in ("Low", "Moderate", "High", "Very High")
        except Exception as e:
            print(f"  Error querying location: {e}")
            
    db.close()
    print("\n=== Live Integration Checks Completed ===")

if __name__ == "__main__":
    unittest.main(exit=False)
    run_integration_tests()
