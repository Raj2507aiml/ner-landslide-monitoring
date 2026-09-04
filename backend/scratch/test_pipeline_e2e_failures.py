import os
import sys
from fastapi.testclient import TestClient

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.abspath(os.path.join(SCRIPTS_DIR, ".."))
sys.path.insert(0, BACKEND_DIR)

from app.main import app
from app.database.session import SessionLocal
from app.services.composite_risk_service import CompositeRiskService
from app.services.early_warning_service import EarlyWarningService

def run_tests():
    client = TestClient(app)
    db = SessionLocal()
    
    print("=" * 75)
    print("PHASE 6 CHECKPOINT 15.6 - END-TO-END & FAILURE-STATE AUDIT")
    print("=" * 75)

    # 1. Successful End-to-End Test (Gangtok)
    print("\n--- TEST 1: SUCCESSFUL END-TO-END LOCATION (Gangtok, Sikkim) ---")
    resp = client.post("/api/v1/early-warning/analyze", json={"latitude": 27.3314, "longitude": 88.6138})
    print(f"HTTP Status: {resp.status_code}")
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    data = resp.json()
    print("Warning Level:", data["warning_level"])
    print("Decision Mode:", data["decision_mode"])
    print("Composite Hazard Index:", data["hazard_context"]["composite_hazard_index"])
    print("Satellite Status:", data["satellite_context"]["status"])
    print("RSCI Score:", data["satellite_context"]["rsci"])
    print("Observational Verification:", data["observational_verification"])
    print("Recommended Action:", data["recommended_action"][:50], "...")
    assert data["decision_mode"] == "FULL_EVIDENCE"
    assert data["satellite_context"]["rsci"] is not None
    print(">>> TEST 1 PASSED.")

    # 2. Outside NER Boundary Test (New Delhi)
    print("\n--- TEST 2: OUTSIDE NER LOCATION REJECTION (New Delhi) ---")
    resp_out = client.post("/api/v1/early-warning/analyze", json={"latitude": 28.6139, "longitude": 77.2090})
    print(f"HTTP Status: {resp_out.status_code}")
    print("Detail:", resp_out.json().get("detail"))
    assert resp_out.status_code == 400
    assert "North Eastern Region" in resp_out.json().get("detail", "")
    print(">>> TEST 2 PASSED (Safely rejected at boundary before heavy compute).")

    # 3. Satellite Data Unavailable / Fallback Mode Test
    print("\n--- TEST 3: METEOROLOGICAL FALLBACK MODE (Satellite Unavailable) ---")
    # Call EarlyWarningService with None radar_change_data
    comp_hazard = CompositeRiskService.calculate_composite_risk(db, 27.3314, 88.6138)
    ew_fallback = EarlyWarningService.evaluate_warning_status(comp_hazard, radar_change_data=None)
    print("Operational Mode:", ew_fallback["operational_mode"])
    print("Warning Level:", ew_fallback["warning_level"])
    print("Satellite Available Flag:", ew_fallback["evidence_summary"]["satellite_available"])
    print("RSCI Score in Fallback:", ew_fallback["evidence_summary"]["rsci_score"])
    print("Observational Verification Notice:", ew_fallback["satellite_availability"])
    assert ew_fallback["operational_mode"] == "METEOROLOGICAL_FALLBACK"
    assert ew_fallback["evidence_summary"]["satellite_available"] is False
    assert ew_fallback["evidence_summary"]["rsci_score"] is None
    print(">>> TEST 3 PASSED (No fake RSCI fabricated, safely transitioned to fallback).")

    # 4. Incompatible Satellite Status (e.g. GEOMETRY_MISMATCH)
    print("\n--- TEST 4: INCOMPATIBLE SATELLITE STATUS PROPAGATION ---")
    geo_mismatch_payload = {
        "status": "GEOMETRY_MISMATCH",
        "message": "No compatible reference and comparison scenes share matching orbital track geometries."
    }
    ew_geo = EarlyWarningService.evaluate_warning_status(comp_hazard, radar_change_data=geo_mismatch_payload)
    print("Operational Mode on GEOMETRY_MISMATCH:", ew_geo["operational_mode"])
    print("RSCI on GEOMETRY_MISMATCH:", ew_geo["evidence_summary"]["rsci_score"])
    assert ew_geo["operational_mode"] == "METEOROLOGICAL_FALLBACK"
    assert ew_geo["evidence_summary"]["rsci_score"] is None
    print(">>> TEST 4 PASSED (GEOMETRY_MISMATCH treated as unavailable, no crash).")

    # 5. Empty Historical Data Handling
    print("\n--- TEST 5: ZERO HISTORICAL DATA LOCATION HANDLING ---")
    # Coordinates in remote Arunachal sector with zero historical incidents in 10km
    res_zero = CompositeRiskService.calculate_composite_risk(db, 28.5000, 96.5000)
    print("Historical Proximity Score:", res_zero["components"]["historical_context"]["proximity_score"])
    print("Historical Density Score:", res_zero["components"]["historical_context"]["density_score"])
    print("Historical Multiplier:", res_zero["components"]["historical_context"]["multiplier"])
    print("Composite Risk Index:", res_zero["composite_risk_index"])
    assert res_zero["components"]["historical_context"]["proximity_score"] == 0.0
    assert res_zero["components"]["historical_context"]["density_score"] == 0.0
    assert res_zero["components"]["historical_context"]["multiplier"] == 1.0
    assert res_zero["composite_risk_index"] >= 0.0
    print(">>> TEST 5 PASSED (Proper zero score and 1.0 multiplier when no incidents exist).")

    db.close()
    print("\n" + "=" * 75)
    print("ALL END-TO-END AND FAILURE-STATE AUDIT TESTS PASSED!")
    print("=" * 75)

if __name__ == "__main__":
    run_tests()
