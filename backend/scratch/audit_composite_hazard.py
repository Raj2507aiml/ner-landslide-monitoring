import os
import sys
import json

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.abspath(os.path.join(SCRIPTS_DIR, ".."))
sys.path.insert(0, BACKEND_DIR)

from app.database.session import SessionLocal
from app.services.composite_risk_service import CompositeRiskService
from app.services.early_warning_service import EarlyWarningService

def main():
    db = SessionLocal()
    try:
        print("=" * 75)
        print("PHASE 6 CHECKPOINT 15.5B - COMPOSITE HAZARD INDEX AUDIT")
        print("=" * 75)
        
        locations = [
            {"name": "Gangtok, Sikkim", "lat": 27.3314, "lon": 88.6138},
            {"name": "Guwahati, Assam (Valley / Low Slope)", "lat": 26.1445, "lon": 91.7362},
            {"name": "Cherrapunji, Meghalaya (Plateau Escarpment)", "lat": 25.2700, "lon": 91.7300},
            {"name": "Kohima, Nagaland (Hilly Terrain)", "lat": 25.6751, "lon": 94.1086}
        ]
        
        results = []
        
        # 1. Multi-Location Comparison
        print("\n--- 1. MULTI-LOCATION COMPARISON ---")
        for loc in locations:
            res = CompositeRiskService.calculate_composite_risk(db, loc["lat"], loc["lon"])
            results.append(res)
            c = res["components"]
            t = res["terrain"]
            print(f"\nLocation: {loc['name']} ({loc['lat']}, {loc['lon']})")
            print(f"  Elevation: {t['elevation']} m | Slope: {t['slope']}° | Aspect: {t['aspect']}°")
            print(f"  Static ML Probability (s_ml): {c['static_susceptibility']['probability']} -> Index (i_ml): {c['static_susceptibility']['index']:.1f}")
            print(f"  Historical Context Score (s_hist): {c['historical_context']['historical_score']:.1f} -> Multiplier (v_hist): {c['historical_context']['multiplier']:.4f}")
            print(f"  Rainfall Trigger Score (s_rain): {c['rainfall_trigger']['rainfall_score']:.1f} -> Multiplier (f_rain): {c['rainfall_trigger']['multiplier']:.4f}")
            raw_prod = c['static_susceptibility']['index'] * c['historical_context']['multiplier'] * c['rainfall_trigger']['multiplier']
            print(f"  Raw Product (i_ml * v_hist * f_rain): {raw_prod:.2f}")
            print(f"  Final Composite Hazard Index: {res['composite_risk_index']} ({res['risk_level']})")
            
        # 2. Repeatability Test
        print("\n--- 2. REPEATABILITY TEST ---")
        for loc in locations[:2]:
            res1 = CompositeRiskService.calculate_composite_risk(db, loc["lat"], loc["lon"])
            res2 = CompositeRiskService.calculate_composite_risk(db, loc["lat"], loc["lon"])
            diff = abs(res1["composite_risk_index"] - res2["composite_risk_index"])
            print(f"{loc['name']}: Run 1 = {res1['composite_risk_index']}, Run 2 = {res2['composite_risk_index']} -> Difference = {diff:.4f}")
            assert diff == 0.0, "Composite hazard score should be deterministic for identical inputs"
        print(">>> Repeatability verified: 100% deterministic.")

        # 3. Dynamic vs Static Influence Simulation
        print("\n--- 3. STATIC VS DYNAMIC SIGNAL SENSITIVITY TEST ---")
        test_loc = locations[0] # Gangtok
        print(f"Testing dynamic rainfall sensitivity at {test_loc['name']}:")
        
        # Test simulated rainfall scores s_rain in [0, 5, 10, 15, 20, 25, 30]
        # Formula: f_rain = 0.5 + 0.05 * s_rain
        i_ml = results[0]["components"]["static_susceptibility"]["index"]
        v_hist = results[0]["components"]["historical_context"]["multiplier"]
        
        print(f"  Fixed Static: i_ml = {i_ml:.2f}, v_hist = {v_hist:.4f}")
        for s_rain in [0.0, 5.0, 10.0, 15.0, 20.0, 25.0, 30.0]:
            f_rain = max(0.5, min(2.0, 0.5 + 0.05 * s_rain))
            raw_val = i_ml * v_hist * f_rain
            clamped = max(0.0, min(100.0, raw_val))
            print(f"  s_rain = {s_rain:4.1f} | f_rain = {f_rain:.2f} | Raw Product = {raw_val:6.2f} | Clamped Index = {clamped:5.1f}")
            
        # 4. Early Warning Integration Check
        print("\n--- 4. EARLY WARNING INTEGRATION TEST ---")
        for res in results:
            ew = EarlyWarningService.evaluate_warning_status(res)
            print(f"Hazard Index in EW: {ew['hazard_context']['composite_hazard_index']} | Warning Level: {ew['warning_level']} | Mode: {ew['operational_mode']}")
            assert ew["hazard_context"]["composite_hazard_index"] == res["composite_risk_index"]

    finally:
        db.close()

if __name__ == "__main__":
    main()
