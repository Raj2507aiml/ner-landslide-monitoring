"""
Phase 7 Checkpoint 16.6 Test Suite: Field Intelligence Operational Review & Verification Workflow
"""

import os
import sys
import json
from datetime import datetime, timedelta
from fastapi.testclient import TestClient

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.abspath(os.path.join(SCRIPTS_DIR, ".."))
sys.path.insert(0, BACKEND_DIR)

from app.main import app
from app.database.session import SessionLocal, Base, engine
from app.models.field_report import FieldReport
from app.models.field_report_media import FieldReportMedia
from app.services.field_report_media_service import compute_exif_consistency

def run_tests():
    Base.metadata.create_all(bind=engine)
    client = TestClient(app)

    print("=" * 80)
    print("PHASE 7 CHECKPOINT 16.6: OPERATIONAL REVIEW & VERIFICATION WORKFLOW TESTS")
    print("=" * 80)

    # Clean test DB
    db = SessionLocal()
    db.query(FieldReportMedia).delete()
    db.query(FieldReport).delete()
    db.commit()

    lat, lon = 27.3314, 88.6138
    now = datetime.utcnow()

    # Seed diverse reports for review queue testing
    r_low = FieldReport(report_type="OTHER", description="Minor soil spillage", latitude=lat, longitude=lon, severity="LOW", status="PENDING", created_at=now - timedelta(minutes=10))
    r_med = FieldReport(report_type="BLOCKED_ROAD", description="Drainage overflow", latitude=lat, longitude=lon, severity="MEDIUM", status="PENDING", created_at=now - timedelta(minutes=20))
    r_high = FieldReport(report_type="SLOPE_MOVEMENT", description="Retaining wall displacement", latitude=lat, longitude=lon, severity="HIGH", status="UNDER_REVIEW", created_at=now - timedelta(minutes=30))
    r_crit = FieldReport(report_type="LANDSLIDE", description="Active debris flow across highway", latitude=lat, longitude=lon, severity="CRITICAL", status="PENDING", created_at=now - timedelta(minutes=40))
    
    db.add_all([r_low, r_med, r_high, r_crit])
    db.commit()

    # TEST A: Review queue returns reports
    print("\n--- TEST A: REVIEW QUEUE RETURNS REPORTS ---")
    resp_a = client.get("/api/v1/field-reports/review-queue")
    assert resp_a.status_code == 200, f"Failed: {resp_a.text}"
    data_a = resp_a.json()
    print("Review Queue Summary:", f"Total: {data_a['total']}, Pending: {data_a['pending_count']}, Critical: {data_a['critical_count']}")
    assert data_a["total"] == 4
    assert len(data_a["items"]) == 4
    print("[PASS] TEST A PASSED.")

    # TEST B: Priority ordering: CRITICAL > HIGH > MEDIUM > LOW
    print("\n--- TEST B: PRIORITY ORDERING (CRITICAL -> HIGH -> MEDIUM -> LOW) ---")
    severities = [item["severity"] for item in data_a["items"]]
    print("Ordered Severities:", severities)
    assert severities == ["CRITICAL", "HIGH", "MEDIUM", "LOW"]
    print("[PASS] TEST B PASSED.")

    # TEST C: Status filtering
    print("\n--- TEST C: STATUS FILTERING ---")
    resp_c = client.get("/api/v1/field-reports/review-queue", params={"status": "UNDER_REVIEW"})
    assert resp_c.status_code == 200
    data_c = resp_c.json()
    assert data_c["total"] == 1
    assert data_c["items"][0]["severity"] == "HIGH"
    assert data_c["items"][0]["status"] == "UNDER_REVIEW"
    print("[PASS] TEST C PASSED.")

    # TEST D: Start Review transition: PENDING -> UNDER_REVIEW
    print("\n--- TEST D: START REVIEW TRANSITION (PENDING -> UNDER_REVIEW) ---")
    resp_d = client.patch(f"/api/v1/field-reports/{r_crit.id}/status", json={"status": "UNDER_REVIEW"})
    assert resp_d.status_code == 200
    assert resp_d.json()["status"] == "UNDER_REVIEW"
    print("[PASS] TEST D PASSED.")

    # TEST E: Verification transition: UNDER_REVIEW -> VERIFIED
    print("\n--- TEST E: VERIFICATION TRANSITION (UNDER_REVIEW -> VERIFIED) ---")
    resp_e = client.patch(f"/api/v1/field-reports/{r_crit.id}/status", json={"status": "VERIFIED"})
    assert resp_e.status_code == 200
    assert resp_e.json()["status"] == "VERIFIED"
    print("[PASS] TEST E PASSED.")

    # TEST F: Rejection transition: UNDER_REVIEW -> REJECTED
    print("\n--- TEST F: REJECTION TRANSITION (UNDER_REVIEW -> REJECTED) ---")
    resp_f = client.patch(f"/api/v1/field-reports/{r_high.id}/status", json={"status": "REJECTED"})
    assert resp_f.status_code == 200
    assert resp_f.json()["status"] == "REJECTED"
    print("[PASS] TEST F PASSED.")

    # TEST G: Invalid status transition rejected
    print("\n--- TEST G: INVALID STATUS TRANSITION REJECTION ---")
    # r_low is PENDING; attempting direct jump to VERIFIED should be rejected
    resp_g = client.patch(f"/api/v1/field-reports/{r_low.id}/status", json={"status": "VERIFIED"})
    assert resp_g.status_code == 400
    print("Invalid Transition Error Message:", resp_g.json()["detail"])
    assert "Invalid status transition" in resp_g.json()["detail"]
    print("[PASS] TEST G PASSED.")

    # TEST H, I, J, K: EXIF consistency evaluation tests
    print("\n--- TEST H: EXIF CONSISTENCY (<= 0.5km -> CONSISTENT) ---")
    dist_h, cons_h = compute_exif_consistency(lat, lon, lat + 0.001, lon + 0.001) # ~140m
    print(f"Dist: {dist_h} km, Rating: {cons_h}")
    assert cons_h == "CONSISTENT"
    assert dist_h <= 0.5
    print("[PASS] TEST H PASSED.")

    print("\n--- TEST I: EXIF NEARBY DIFFERENCE (0.5km - 5km -> NEARBY_DIFFERENCE) ---")
    dist_i, cons_i = compute_exif_consistency(lat, lon, lat + 0.02, lon + 0.02) # ~2.8km
    print(f"Dist: {dist_i} km, Rating: {cons_i}")
    assert cons_i == "NEARBY_DIFFERENCE"
    assert 0.5 < dist_i <= 5.0
    print("[PASS] TEST I PASSED.")

    print("\n--- TEST J: EXIF SIGNIFICANT DIFFERENCE (> 5km -> SIGNIFICANT_DIFFERENCE) ---")
    dist_j, cons_j = compute_exif_consistency(lat, lon, lat + 0.1, lon + 0.1) # ~14km
    print(f"Dist: {dist_j} km, Rating: {cons_j}")
    assert cons_j == "SIGNIFICANT_DIFFERENCE"
    assert dist_j > 5.0
    print("[PASS] TEST J PASSED.")

    print("\n--- TEST K: MISSING EXIF HANDLED SAFELY ---")
    dist_k, cons_k = compute_exif_consistency(lat, lon, None, None)
    print(f"Dist: {dist_k}, Rating: {cons_k}")
    assert dist_k is None
    assert cons_k == "NO_EXIF_GPS"
    print("[PASS] TEST K PASSED.")

    # TEST L: Map/GeoJSON integration data
    print("\n--- TEST L: MAP / GEOJSON INTEGRATION DATA ---")
    resp_l = client.get("/api/v1/field-reports/geojson", params={"latitude": lat, "longitude": lon, "radius_km": 5.0})
    assert resp_l.status_code == 200
    data_l = resp_l.json()
    assert data_l["type"] == "FeatureCollection"
    assert len(data_l["features"]) == 4
    first_feat = data_l["features"][0]
    print("Sample GeoJSON Feature Properties:", first_feat["properties"])
    assert "id" in first_feat["properties"]
    assert "severity" in first_feat["properties"]
    assert "status" in first_feat["properties"]
    print("[PASS] TEST L PASSED.")

    # TEST M: Existing Field Report CRUD regression
    print("\n--- TEST M: EXISTING FIELD REPORT CRUD REGRESSION ---")
    detail_resp = client.get(f"/api/v1/field-reports/{r_crit.id}")
    assert detail_resp.status_code == 200
    detail_data = detail_resp.json()
    print("Report Detail Spatial Context:", detail_data.get("spatial_context"))
    assert "spatial_context" in detail_data
    print("[PASS] TEST M PASSED.")

    # TEST N: Existing Composite Risk regression
    print("\n--- TEST N: EXISTING COMPOSITE RISK REGRESSION ---")
    resp_n = client.post("/api/v1/risk/composite", json={"latitude": lat, "longitude": lon})
    assert resp_n.status_code == 200
    data_n = resp_n.json()
    assert "composite_risk_index" in data_n
    assert "field_intelligence_context" in data_n
    print(f"Composite Hazard Index: {data_n['composite_risk_index']}")
    print("[PASS] TEST N PASSED.")

    # TEST O: Existing Early Warning regression
    print("\n--- TEST O: EXISTING EARLY WARNING REGRESSION ---")
    resp_o = client.post("/api/v1/early-warning/analyze", json={"latitude": lat, "longitude": lon})
    assert resp_o.status_code == 200
    data_o = resp_o.json()
    assert "warning_level" in data_o
    assert "ground_observation_context" in data_o
    print(f"Early Warning Level: {data_o['warning_level']}")
    print("[PASS] TEST O PASSED.")

    db.close()
    print("\n" + "=" * 80)
    print("ALL TESTS (TEST A - TEST O) PASSED SUCCESSFULLY!")
    print("=" * 80)

if __name__ == "__main__":
    run_tests()
