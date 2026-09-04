import os
import sys

# ── Inject backend directory into sys.path ──────────────────────────────────
SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.abspath(os.path.join(SCRIPTS_DIR, ".."))
sys.path.insert(0, BACKEND_DIR)

from app.database.session import SessionLocal
from app.services.susceptibility_service import calculate_susceptibility_score

def run_tests():
    print("=== Starting Upgraded Susceptibility Engine Verification ===")
    db = SessionLocal()
    
    try:
        # ── Test 1: Compatibility Mode ─────────────────────────────────────────
        print("\n[TEST 1] Compatibility Mode (rainfall only, no slope)...")
        # Historical = 31.83, Rainfall = 20.0 -> 15.0 / 30.0. Max possible = 40 + 30 = 70.
        # Normalization: 100 * 46.83 / 70.0 = 66.90%
        res = calculate_susceptibility_score(db, 25.23908, 90.63944, radius_km=10.0, rainfall=20.0)
        print(f"  Scoring Mode: {res['rainfall_component']['scoring_mode']}")
        print(f"  Earned points sum: {res['historical_component']['score'] + res['rainfall_component']['score']} / {res['available_max_points']}")
        print(f"  Susceptibility score: {res['susceptibility_score']}")
        print(f"  Hazard level: {res['hazard_level']}")
        
        assert res["rainfall_component"]["scoring_mode"] == "compatibility"
        assert res["rainfall_component"]["max_score"] == 30.0
        assert res["rainfall_component"]["score"] == 15.0
        assert res["available_max_points"] == 70.0
        assert res["susceptibility_score"] == 66.90
        print("  [OK] Test 1 Passed.")

        # ── Test 2: Full Multi-timescale Mode ──────────────────────────────────
        print("\n[TEST 2] Full Multi-timescale Mode (slope=35, rainfall=35, rain_3d=95, rain_7d=210)...")
        # Historical = 31.83
        # Terrain (slope 35 > 30) = 30.0
        # Rainfall:
        #   daily 35 -> 5.0
        #   3d 95 -> 10.0
        #   7d 210 -> 10.0
        #   Total Rainfall = 25.0 / 30.0
        # Normalization: 100 * (31.83 + 30 + 25) / 100 = 86.83%
        res = calculate_susceptibility_score(
            db, 25.23908, 90.63944, radius_km=10.0,
            slope=35.0, rainfall=35.0, rainfall_3d=95.0, rainfall_7d=210.0
        )
        print(f"  Scoring Mode: {res['rainfall_component']['scoring_mode']}")
        print(f"  Rainfall components: daily={res['rainfall_component']['daily_score']}, 3d={res['rainfall_component']['three_day_score']}, 7d={res['rainfall_component']['seven_day_score']}")
        print(f"  Total score: {res['susceptibility_score']} / 100")
        print(f"  Hazard level: {res['hazard_level']}")
        print(f"  Explanation: {res['explanation']}")
        
        assert res["rainfall_component"]["scoring_mode"] == "multi_timescale"
        assert res["rainfall_component"]["max_score"] == 30.0
        assert res["rainfall_component"]["score"] == 25.0
        assert res["available_max_points"] == 100.0
        assert res["susceptibility_score"] == 86.83
        assert res["hazard_level"] == "Very High"
        print("  [OK] Test 2 Passed.")

        # ── Test 3: Partial Multi-timescale (Missing 7-day) ───────────────────
        print("\n[TEST 3] Partial Multi-timescale Mode (Missing 7-day, rainfall=35, rain_3d=95)...")
        # Historical = 31.83
        # Rainfall:
        #   daily 35 -> 5.0
        #   3d 95 -> 10.0
        #   Total Rainfall = 15.0 / 20.0
        # Normalization: 100 * (31.83 + 15.0) / (40 + 20) = 46.83 / 60.0 = 78.05%
        res = calculate_susceptibility_score(
            db, 25.23908, 90.63944, radius_km=10.0,
            rainfall=35.0, rainfall_3d=95.0, rainfall_7d=None
        )
        print(f"  Scoring Mode: {res['rainfall_component']['scoring_mode']}")
        print(f"  Rainfall components: daily={res['rainfall_component']['daily_score']}, 3d={res['rainfall_component']['three_day_score']}, 7d={res['rainfall_component']['seven_day_score']}")
        print(f"  Total score: {res['susceptibility_score']} / 100")
        print(f"  Available Max Points: {res['available_max_points']}")
        
        assert res["rainfall_component"]["scoring_mode"] == "multi_timescale_partial"
        assert res["rainfall_component"]["max_score"] == 20.0
        assert res["rainfall_component"]["score"] == 15.0
        assert res["available_max_points"] == 60.0
        assert res["susceptibility_score"] == 78.05
        print("  [OK] Test 3 Passed.")

        # ── Test 4: Partial Multi-timescale (Only 7-day) ──────────────────────
        print("\n[TEST 4] Partial Multi-timescale Mode (Only 7-day=210)...")
        # Historical = 31.83
        # Rainfall:
        #   7d 210 -> 10.0
        #   Total Rainfall = 10.0 / 10.0
        # Normalization: 100 * (31.83 + 10) / (40 + 10) = 41.83 / 50 = 83.66%
        res = calculate_susceptibility_score(
            db, 25.23908, 90.63944, radius_km=10.0,
            rainfall=None, rainfall_3d=None, rainfall_7d=210.0
        )
        print(f"  Scoring Mode: {res['rainfall_component']['scoring_mode']}")
        print(f"  Rainfall components: daily={res['rainfall_component']['daily_score']}, 3d={res['rainfall_component']['three_day_score']}, 7d={res['rainfall_component']['seven_day_score']}")
        print(f"  Total score: {res['susceptibility_score']} / 100")
        print(f"  Available Max Points: {res['available_max_points']}")
        
        assert res["rainfall_component"]["scoring_mode"] == "multi_timescale_partial"
        assert res["rainfall_component"]["max_score"] == 10.0
        assert res["rainfall_component"]["score"] == 10.0
        assert res["available_max_points"] == 50.0
        assert res["susceptibility_score"] == 83.66
        print("  [OK] Test 4 Passed.")

        print("\n=== All Upgraded Susceptibility Tests Passed Successfully ===")
        
    finally:
        db.close()

if __name__ == "__main__":
    run_tests()
