import os
import sys
import json
import time
from fastapi.testclient import TestClient

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.abspath(os.path.join(SCRIPTS_DIR, ".."))
sys.path.insert(0, BACKEND_DIR)

from app.main import app
from app.database.session import SessionLocal
from app.services.composite_risk_service import CompositeRiskService
from app.services.satellite_service import get_aoi_cache_key, resolve_scene_cache_dir

def run_cross_location_audit():
    client = TestClient(app)
    db = SessionLocal()
    
    locations = [
        {"name": "Gangtok", "state": "Sikkim", "lat": 27.3314, "lon": 88.6138, "terrain": "Steep Himalayan / Mountain"},
        {"name": "Tawang", "state": "Arunachal Pradesh", "lat": 27.5861, "lon": 91.8650, "terrain": "High Himalayan Mountain"},
        {"name": "Kohima", "state": "Nagaland", "lat": 25.6751, "lon": 94.1086, "terrain": "Hilly Terrain"},
        {"name": "Imphal", "state": "Manipur", "lat": 24.8170, "lon": 93.9368, "terrain": "Valley + Surrounding Hills"},
        {"name": "Aizawl", "state": "Mizoram", "lat": 23.7271, "lon": 92.7176, "terrain": "Steep Hilly Terrain"},
        {"name": "Cherrapunji", "state": "Meghalaya", "lat": 25.2702, "lon": 91.7326, "terrain": "Plateau / Heavy Rainfall"},
        {"name": "Guwahati", "state": "Assam", "lat": 26.1445, "lon": 91.7362, "terrain": "Lowland / Urban Hills"},
        {"name": "Remote Low-Density (Anini)", "state": "Arunachal Pradesh", "lat": 28.2700, "lon": 95.9000, "terrain": "Sparse Historical / Remote"}
    ]
    
    results = []
    
    print("=" * 80)
    print("PHASE 6 CHECKPOINT 15.7 - CROSS-LOCATION ROBUSTNESS & REGRESSION AUDIT")
    print("=" * 80)
    
    # 1. Execute full pipeline for each location
    print("\n--- 1. EXECUTING END-TO-END PIPELINE ACROSS 8 NER LOCATIONS ---")
    for loc in locations:
        t0 = time.time()
        # Direct service call for detailed component inspection
        comp_res = CompositeRiskService.calculate_composite_risk(db, loc["lat"], loc["lon"])
        
        # Full API endpoint call
        resp = client.post("/api/v1/early-warning/analyze", json={"latitude": loc["lat"], "longitude": loc["lon"]})
        elapsed = time.time() - t0
        
        http_ok = (resp.status_code == 200)
        api_data = resp.json() if http_ok else {}
        
        entry = {
            "name": loc["name"],
            "state": loc["state"],
            "lat": loc["lat"],
            "lon": loc["lon"],
            "terrain": loc["terrain"],
            "http_status": resp.status_code,
            "elevation": comp_res["terrain"]["elevation"],
            "slope": comp_res["terrain"]["slope"],
            "aspect": comp_res["terrain"]["aspect"],
            "s_ml": comp_res["components"]["static_susceptibility"]["probability"],
            "i_ml": comp_res["components"]["static_susceptibility"]["index"],
            "v_hist": comp_res["components"]["historical_context"]["multiplier"],
            "s_rain": comp_res["components"]["rainfall_trigger"]["rainfall_score"],
            "f_rain": comp_res["components"]["rainfall_trigger"]["multiplier"],
            "composite_hazard_index": comp_res["composite_risk_index"],
            "hazard_category": comp_res["risk_level"],
            "decision_mode": api_data.get("decision_mode", "ERROR"),
            "warning_level": api_data.get("warning_level", "ERROR"),
            "sat_status": api_data.get("satellite_context", {}).get("status", "UNAVAILABLE"),
            "rsci": api_data.get("satellite_context", {}).get("rsci"),
            "rsci_category": api_data.get("satellite_context", {}).get("category"),
            "elapsed_sec": round(elapsed, 2)
        }
        results.append(entry)
        
        print(f"\n[{loc['name']}, {loc['state']}] ({loc['terrain']})")
        print(f"  HTTP: {resp.status_code} | Mode: {entry['decision_mode']} | Warning: {entry['warning_level']}")
        print(f"  Elev: {entry['elevation']}m | Slope: {entry['slope']}° | ML Prob: {entry['s_ml']:.3f} ({entry['i_ml']:.1f})")
        print(f"  v_hist: {entry['v_hist']:.3f} | s_rain: {entry['s_rain']:.1f} (f_rain: {entry['f_rain']:.2f})")
        print(f"  Composite Hazard: {entry['composite_hazard_index']:.1f} ({entry['hazard_category']})")
        print(f"  Satellite: Status={entry['sat_status']} | RSCI={entry['rsci']} | Cat={entry['rsci_category']}")

    # 2. Check Impossible Outputs and Invariants
    print("\n--- 2. IMPOSSIBLE OUTPUT & NUMERICAL INVARIANT SCAN ---")
    violations = []
    for r in results:
        # Physical bounds
        if not (-90.0 <= r["lat"] <= 90.0): violations.append(f"{r['name']}: lat out of bounds")
        if not (-180.0 <= r["lon"] <= 180.0): violations.append(f"{r['name']}: lon out of bounds")
        if r["elevation"] < -200 or r["elevation"] > 9000: violations.append(f"{r['name']}: impossible elevation {r['elevation']}")
        if r["slope"] < 0 or r["slope"] > 90: violations.append(f"{r['name']}: impossible slope {r['slope']}")
        if r["aspect"] < -1 or r["aspect"] > 360: violations.append(f"{r['name']}: impossible aspect {r['aspect']}")
        
        # Component ranges
        if not (0.0 <= r["s_ml"] <= 1.0): violations.append(f"{r['name']}: s_ml out of bounds")
        if not (1.0 <= r["v_hist"] <= 1.5): violations.append(f"{r['name']}: v_hist out of bounds {r['v_hist']}")
        if not (0.0 <= r["s_rain"] <= 30.0): violations.append(f"{r['name']}: s_rain out of bounds {r['s_rain']}")
        if not (0.5 <= r["f_rain"] <= 2.0): violations.append(f"{r['name']}: f_rain out of bounds {r['f_rain']}")
        if not (0.0 <= r["composite_hazard_index"] <= 100.0): violations.append(f"{r['name']}: composite index out of bounds")
        
        # RSCI & Mode logic
        if r["decision_mode"] == "FULL_EVIDENCE":
            if r["rsci"] is None: violations.append(f"{r['name']}: FULL_EVIDENCE with null RSCI")
            if not (0.0 <= r["rsci"] <= 100.0): violations.append(f"{r['name']}: RSCI out of bounds {r['rsci']}")
        elif r["decision_mode"] == "METEOROLOGICAL_FALLBACK":
            if r["rsci"] is not None: violations.append(f"{r['name']}: FALLBACK with non-null RSCI")
            
        if r["warning_level"] not in ["NORMAL", "WATCH", "ALERT", "CRITICAL"]:
            violations.append(f"{r['name']}: invalid warning level {r['warning_level']}")

    if violations:
        print(f"FAILED: Found {len(violations)} invariant violations:")
        for v in violations: print(f"  - {v}")
    else:
        print("PASSED: Zero impossible outputs or numerical boundary violations detected across all 8 locations.")

    # 3. Repeatability Test across 3 terrain types
    print("\n--- 3. REPEATABILITY TEST (Mountain, Plateau, Lowland) ---")
    rep_locs = [
        {"name": "Gangtok (Mountain)", "lat": 27.3314, "lon": 88.6138},
        {"name": "Cherrapunji (Plateau)", "lat": 25.2702, "lon": 91.7326},
        {"name": "Guwahati (Lowland)", "lat": 26.1445, "lon": 91.7362}
    ]
    for loc in rep_locs:
        run1 = CompositeRiskService.calculate_composite_risk(db, loc["lat"], loc["lon"])
        run2 = CompositeRiskService.calculate_composite_risk(db, loc["lat"], loc["lon"])
        diff_hazard = abs(run1["composite_risk_index"] - run2["composite_risk_index"])
        diff_ml = abs(run1["components"]["static_susceptibility"]["probability"] - run2["components"]["static_susceptibility"]["probability"])
        diff_hist = abs(run1["components"]["historical_context"]["multiplier"] - run2["components"]["historical_context"]["multiplier"])
        print(f"  {loc['name']}: Run1 Hazard={run1['composite_risk_index']}, Run2 Hazard={run2['composite_risk_index']} (Diff: {diff_hazard:.6f})")
        assert diff_hazard == 0.0, f"{loc['name']} deterministic hazard non-repeatable"
        assert diff_ml == 0.0, f"{loc['name']} deterministic ML non-repeatable"
        assert diff_hist == 0.0, f"{loc['name']} deterministic history non-repeatable"
    print("PASSED: 100% Deterministic repeatability across mountain, plateau, and lowland test coordinates.")

    # 4. Cross-Location Cache Isolation Test (A -> B -> A)
    print("\n--- 4. CROSS-LOCATION CACHE ISOLATION TEST (A -> B -> A) ---")
    loc_a = {"name": "Gangtok", "lat": 27.3314, "lon": 88.6138}
    loc_b = {"name": "Meghalaya Coordinate", "lat": 25.52706310546959, "lon": 91.35848472637227}
    
    key_a = get_aoi_cache_key(loc_a["lat"], loc_a["lon"], 5.0)
    key_b = get_aoi_cache_key(loc_b["lat"], loc_b["lon"], 5.0)
    print(f"  Location A Key: {key_a}")
    print(f"  Location B Key: {key_b}")
    assert key_a != key_b, "AOI keys must be distinct"
    
    # Analyze A
    res_a1 = client.post("/api/v1/early-warning/analyze", json={"latitude": loc_a["lat"], "longitude": loc_a["lon"]}).json()
    # Analyze B
    res_b = client.post("/api/v1/early-warning/analyze", json={"latitude": loc_b["lat"], "longitude": loc_b["lon"]}).json()
    # Re-analyze A
    res_a2 = client.post("/api/v1/early-warning/analyze", json={"latitude": loc_a["lat"], "longitude": loc_a["lon"]}).json()
    
    print(f"  Location A Run 1: Status={res_a1['satellite_context']['status']}, RSCI={res_a1['satellite_context']['rsci']}")
    print(f"  Location B:       Status={res_b['satellite_context']['status']}, RSCI={res_b['satellite_context']['rsci']}")
    print(f"  Location A Run 2: Status={res_a2['satellite_context']['status']}, RSCI={res_a2['satellite_context']['rsci']}")
    
    assert res_a1["satellite_context"]["rsci"] == res_a2["satellite_context"]["rsci"], "Location A must remain consistent after Location B analysis"
    print("PASSED: AOI cache isolation verified. Cross-location cache contamination did not occur.")

    # 5. Save detailed audit results to json
    audit_dump_path = os.path.join(BACKEND_DIR, "scratch", "cross_location_audit_results.json")
    with open(audit_dump_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"\nSaved cross-location audit results to: {audit_dump_path}")

    db.close()
    print("\n" + "=" * 80)
    print("CROSS-LOCATION ROBUSTNESS & REGRESSION AUDIT COMPLETED SUCCESSFULLY!")
    print("=" * 80)

if __name__ == "__main__":
    run_cross_location_audit()
