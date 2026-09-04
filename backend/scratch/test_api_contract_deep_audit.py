import os
import sys
import json
import math
from fastapi.testclient import TestClient

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.abspath(os.path.join(SCRIPTS_DIR, ".."))
sys.path.insert(0, BACKEND_DIR)

from app.main import app

def is_json_primitive(val):
    if val is None: return True
    if isinstance(val, (bool, int, float, str)):
        if isinstance(val, float) and (math.isnan(val) or math.isinf(val)):
            return False
        return True
    if isinstance(val, list):
        return all(is_json_primitive(x) for x in val)
    if isinstance(val, dict):
        return all(isinstance(k, str) and is_json_primitive(v) for k, v in val.items())
    return False

def audit_api_contracts():
    client = TestClient(app)
    
    print("=" * 80)
    print("PHASE 6 CHECKPOINT 15.8 - API CONTRACT & DATA INTEGRITY DEEP AUDIT")
    print("=" * 80)

    # 1. Early Warning Endpoint Audit (Gangtok)
    print("\n--- 1. AUDITING POST /api/v1/early-warning/analyze (Gangtok - Full Evidence) ---")
    resp_ew = client.post("/api/v1/early-warning/analyze", json={"latitude": 27.3314, "longitude": 88.6138})
    print(f"Status Code: {resp_ew.status_code}")
    assert resp_ew.status_code == 200
    data_ew = resp_ew.json()
    assert is_json_primitive(data_ew), "Response must contain only valid JSON primitives"
    print("JSON Serialization: 100% Valid Primitives (No NaN, Inf, or non-serializable objects)")
    print("Response payload:", json.dumps(data_ew, indent=2))

    # 2. Composite Risk Endpoint Audit (Gangtok)
    print("\n--- 2. AUDITING POST /api/v1/risk/composite (Gangtok) ---")
    resp_risk = client.post("/api/v1/risk/composite", json={"latitude": 27.3314, "longitude": 88.6138, "radius_km": 10.0})
    print(f"Status Code: {resp_risk.status_code}")
    assert resp_risk.status_code == 200
    data_risk = resp_risk.json()
    assert is_json_primitive(data_risk), "Risk response must contain valid JSON primitives"
    print("JSON Serialization: 100% Valid Primitives")
    print("Composite Risk Index:", data_risk["composite_risk_index"], f"({data_risk['risk_level']})")
    print("Components Static Index:", data_risk["components"]["static_susceptibility"]["index"])
    print("Components Hist Multiplier:", data_risk["components"]["historical_context"]["multiplier"])
    print("Components Rain Multiplier:", data_risk["components"]["rainfall_trigger"]["multiplier"])

    # 3. Automatic Satellite Change Endpoint Audit (Gangtok)
    print("\n--- 3. AUDITING POST /api/v1/satellite/automatic-change-analysis (Gangtok) ---")
    resp_sat = client.post("/api/v1/satellite/automatic-change-analysis", json={"latitude": 27.3314, "longitude": 88.6138})
    print(f"Status Code: {resp_sat.status_code}")
    assert resp_sat.status_code == 200
    data_sat = resp_sat.json()
    assert is_json_primitive(data_sat), "Satellite change response must contain valid JSON primitives"
    print("JSON Serialization: 100% Valid Primitives")
    print("Satellite Status:", data_sat["status"])
    print("RSCI Score:", data_sat["radar_surface_change_signal"]["radar_surface_change_index"])
    print("Category:", data_sat["radar_surface_change_signal"]["category"])

    # 4. Error Responses Audit
    print("\n--- 4. AUDITING ERROR RESPONSES ---")
    # Outside NER
    resp_out = client.post("/api/v1/early-warning/analyze", json={"latitude": 28.6139, "longitude": 77.2090})
    print(f"Outside NER Status Code: {resp_out.status_code}")
    assert resp_out.status_code == 400
    assert "detail" in resp_out.json()
    print("Outside NER Error Body:", resp_out.json())

    # Invalid Coordinates (Pydantic validation)
    resp_inv = client.post("/api/v1/early-warning/analyze", json={"latitude": 150.0, "longitude": 88.6138})
    print(f"Invalid Lat Status Code: {resp_inv.status_code}")
    assert resp_inv.status_code == 422
    assert "detail" in resp_inv.json()
    print("Validation Error Body:", resp_inv.json()["detail"][0]["msg"])

    # 5. Guwahati Baseline Regression Check
    print("\n--- 5. GUWAHATI BASELINE REGRESSION CHECK ---")
    resp_ghy = client.post("/api/v1/early-warning/analyze", json={"latitude": 26.1445, "longitude": 91.7362})
    assert resp_ghy.status_code == 200
    data_ghy = resp_ghy.json()
    print("Guwahati Warning Level:", data_ghy["warning_level"])
    print("Guwahati Decision Mode:", data_ghy["decision_mode"])
    print("Guwahati Composite Hazard Index:", data_ghy["hazard_context"]["composite_hazard_index"])
    print("Guwahati Satellite Status:", data_ghy["satellite_context"]["status"])
    print("Guwahati RSCI:", data_ghy["satellite_context"]["rsci"])
    assert data_ghy["warning_level"] == "NORMAL"
    assert data_ghy["hazard_context"]["composite_hazard_index"] < 50.0
    print(">>> Guwahati Baseline Verified.")

    print("\n" + "=" * 80)
    print("API CONTRACT & DATA INTEGRITY DEEP AUDIT COMPLETED SUCCESSFULLY!")
    print("=" * 80)

if __name__ == "__main__":
    audit_api_contracts()
