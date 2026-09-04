"""
Phase 7 Checkpoint 16.5 Test Suite: Field Intelligence Risk Signal Integration
"""

import os
import sys
import json
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.abspath(os.path.join(SCRIPTS_DIR, ".."))
sys.path.insert(0, BACKEND_DIR)

from app.main import app
from app.database.session import SessionLocal, Base, engine
from app.models.field_report import FieldReport
from app.models.field_report_media import FieldReportMedia

def run_tests():
    Base.metadata.create_all(bind=engine)
    client = TestClient(app)

    print("=" * 80)
    print("PHASE 7 CHECKPOINT 16.5: FIELD INTELLIGENCE RISK SIGNAL TESTS")
    print("=" * 80)

    # Clean test DB
    db = SessionLocal()
    db.query(FieldReportMedia).delete()
    db.query(FieldReport).delete()
    db.commit()

    # Base coords: Gangtok (27.3314, 88.6138)
    lat, lon = 27.3314, 88.6138

    # TEST A: No reports nearby -> NORMAL, score 0
    print("\n--- TEST A: NO REPORTS NEARBY ---")
    resp_a = client.get("/api/v1/field-reports/risk-signal", params={"latitude": lat, "longitude": lon, "radius_km": 5.0})
    assert resp_a.status_code == 200, f"Failed: {resp_a.text}"
    data_a = resp_a.json()
    print("Data A:", json.dumps(data_a, indent=2))
    assert data_a["field_intelligence_status"] == "NORMAL"
    assert data_a["verified_ground_signal"]["score"] == 0.0
    assert data_a["verified_ground_signal"]["verified_reports"] == 0
    print("[PASS] TEST A PASSED.")

    # TEST B: Single pending report -> OBSERVATION_REPORTED, verified score 0
    print("\n--- TEST B: SINGLE PENDING REPORT ---")
    rep_b = FieldReport(
        report_type="CRACK",
        description="Hairline crack on private driveway.",
        latitude=lat,
        longitude=lon,
        reporter_type="CITIZEN",
        severity="LOW",
        status="PENDING",
        created_at=datetime.utcnow()
    )
    db.add(rep_b)
    db.commit()

    resp_b = client.get("/api/v1/field-reports/risk-signal", params={"latitude": lat, "longitude": lon, "radius_km": 5.0})
    assert resp_b.status_code == 200
    data_b = resp_b.json()
    print("Data B:", json.dumps(data_b, indent=2))
    assert data_b["field_intelligence_status"] == "OBSERVATION_REPORTED"
    assert data_b["verified_ground_signal"]["score"] == 0.0
    assert data_b["unverified_observations"]["pending_reports"] == 1
    print("[PASS] TEST B PASSED.")

    # TEST C: Multiple nearby pending reports -> MULTIPLE_OBSERVATIONS or cluster
    print("\n--- TEST C: MULTIPLE NEARBY PENDING REPORTS ---")
    rep_c1 = FieldReport(
        report_type="CRACK",
        description="Second crack nearby within 200m.",
        latitude=lat + 0.001,
        longitude=lon + 0.001,
        reporter_type="CITIZEN",
        severity="MEDIUM",
        status="PENDING",
        created_at=datetime.utcnow()
    )
    rep_c2 = FieldReport(
        report_type="BLOCKED_ROAD",
        description="Road debris on bypass.",
        latitude=lat - 0.002,
        longitude=lon - 0.002,
        reporter_type="CITIZEN",
        severity="MEDIUM",
        status="UNDER_REVIEW",
        created_at=datetime.utcnow()
    )
    db.add_all([rep_c1, rep_c2])
    db.commit()

    resp_c = client.get("/api/v1/field-reports/risk-signal", params={"latitude": lat, "longitude": lon, "radius_km": 5.0})
    assert resp_c.status_code == 200
    data_c = resp_c.json()
    print("Data C:", json.dumps(data_c, indent=2))
    assert data_c["field_intelligence_status"] == "MULTIPLE_OBSERVATIONS"
    assert data_c["verified_ground_signal"]["score"] == 0.0
    assert data_c["unverified_observations"]["pending_reports"] == 2
    assert data_c["unverified_observations"]["under_review_reports"] == 1
    assert data_c["cluster_analysis"]["potential_cluster_detected"] is True # rep_b and rep_c1 share CRACK <= 500m
    print("[PASS] TEST C PASSED.")

    # Clear DB before Test D
    db.query(FieldReport).delete()
    db.commit()

    # TEST D: Verified HIGH severity CRACK -> verified score > 0, VERIFIED_GROUND_HAZARD
    print("\n--- TEST D: VERIFIED HIGH SEVERITY CRACK ---")
    rep_d = FieldReport(
        report_type="CRACK",
        description="Significant ground fissure verified on hillside roadway.",
        latitude=lat,
        longitude=lon,
        reporter_type="FIELD_OFFICIAL",
        severity="HIGH",
        status="VERIFIED",
        created_at=datetime.utcnow()
    )
    db.add(rep_d)
    db.commit()

    resp_d = client.get("/api/v1/field-reports/risk-signal", params={"latitude": lat, "longitude": lon, "radius_km": 5.0})
    assert resp_d.status_code == 200
    data_d = resp_d.json()
    print("Data D:", json.dumps(data_d, indent=2))
    # CRACK (2) * HIGH (3) = 6 * 5 = 30.0
    assert data_d["field_intelligence_status"] == "VERIFIED_GROUND_HAZARD"
    assert data_d["verified_ground_signal"]["score"] == 30.0
    assert data_d["verified_ground_signal"]["verified_reports"] == 1
    assert data_d["verified_ground_signal"]["high_severity_reports"] == 1
    print("[PASS] TEST D PASSED.")

    # Clear DB before Test E
    db.query(FieldReport).delete()
    db.commit()

    # TEST E: Verified CRITICAL LANDSLIDE -> score 100, CRITICAL_GROUND_ALERT
    print("\n--- TEST E: VERIFIED CRITICAL LANDSLIDE ---")
    rep_e = FieldReport(
        report_type="LANDSLIDE",
        description="Active slope collapse and mass mud movement.",
        latitude=lat,
        longitude=lon,
        reporter_type="FIELD_OFFICIAL",
        severity="CRITICAL",
        status="VERIFIED",
        created_at=datetime.utcnow()
    )
    db.add(rep_e)
    db.commit()

    resp_e = client.get("/api/v1/field-reports/risk-signal", params={"latitude": lat, "longitude": lon, "radius_km": 5.0})
    assert resp_e.status_code == 200
    data_e = resp_e.json()
    print("Data E:", json.dumps(data_e, indent=2))
    # LANDSLIDE (5) * CRITICAL (4) = 20 * 5 = 100.0
    assert data_e["field_intelligence_status"] == "CRITICAL_GROUND_ALERT"
    assert data_e["verified_ground_signal"]["score"] == 100.0
    assert data_e["verified_ground_signal"]["critical_reports"] == 1
    print("[PASS] TEST E PASSED.")

    # TEST F: Multiple verified nearby high severity reports -> cluster awareness
    print("\n--- TEST F: MULTIPLE VERIFIED NEARBY REPORTS & CLUSTERING ---")
    rep_f = FieldReport(
        report_type="LANDSLIDE",
        description="Second slide section 200m away.",
        latitude=lat + 0.001,
        longitude=lon + 0.001,
        reporter_type="FIELD_OFFICIAL",
        severity="HIGH",
        status="VERIFIED",
        created_at=datetime.utcnow()
    )
    db.add(rep_f)
    db.commit()

    resp_f = client.get("/api/v1/field-reports/risk-signal", params={"latitude": lat, "longitude": lon, "radius_km": 5.0})
    assert resp_f.status_code == 200
    data_f = resp_f.json()
    print("Data F:", json.dumps(data_f, indent=2))
    assert data_f["field_intelligence_status"] == "CRITICAL_GROUND_ALERT"
    assert data_f["cluster_analysis"]["potential_cluster_detected"] is True
    assert data_f["cluster_analysis"]["cluster_report_count"] == 2
    assert "LANDSLIDE" in data_f["cluster_analysis"]["cluster_types"]
    print("[PASS] TEST F PASSED.")

    # Clear DB before Test G
    db.query(FieldReport).delete()
    db.commit()

    # TEST G: Recency buckets
    print("\n--- TEST G: RECENCY BUCKET VALIDATION ---")
    now = datetime.utcnow()
    reports_g = [
        FieldReport(report_type="CRACK", description="6h ago", latitude=lat, longitude=lon, severity="LOW", status="PENDING", created_at=now - timedelta(hours=6)),
        FieldReport(report_type="DEBRIS", description="2d ago", latitude=lat, longitude=lon, severity="LOW", status="PENDING", created_at=now - timedelta(days=2)),
        FieldReport(report_type="BLOCKED_ROAD", description="5d ago", latitude=lat, longitude=lon, severity="LOW", status="PENDING", created_at=now - timedelta(days=5)),
        FieldReport(report_type="OTHER", description="15d ago", latitude=lat, longitude=lon, severity="LOW", status="PENDING", created_at=now - timedelta(days=15)),
    ]
    db.add_all(reports_g)
    db.commit()

    resp_g = client.get("/api/v1/field-reports/risk-signal", params={"latitude": lat, "longitude": lon, "radius_km": 5.0})
    assert resp_g.status_code == 200
    data_g = resp_g.json()
    print("Recency Data:", json.dumps(data_g["recency"], indent=2))
    assert data_g["recency"]["very_recent"] == 1
    assert data_g["recency"]["recent"] == 1
    assert data_g["recency"]["aging"] == 1
    assert data_g["recency"]["historical"] == 1
    print("[PASS] TEST G PASSED.")

    # TEST H: Outside NER location -> HTTP 400
    print("\n--- TEST H: OUTSIDE NER COORDINATES ---")
    resp_h = client.get("/api/v1/field-reports/risk-signal", params={"latitude": 28.6139, "longitude": 77.2090, "radius_km": 5.0})
    assert resp_h.status_code == 400
    assert "North Eastern Region" in resp_h.json()["detail"]
    print("[PASS] TEST H PASSED.")

    # TEST I: Invalid radius -> HTTP 422
    print("\n--- TEST I: INVALID RADIUS VALIDATION ---")
    resp_i1 = client.get("/api/v1/field-reports/risk-signal", params={"latitude": lat, "longitude": lon, "radius_km": -5.0})
    assert resp_i1.status_code == 422
    resp_i2 = client.get("/api/v1/field-reports/risk-signal", params={"latitude": lat, "longitude": lon, "radius_km": 500.0})
    assert resp_i2.status_code == 422
    print("[PASS] TEST I PASSED.")

    # TEST J: Existing Composite Risk endpoint -> HTTP 200, score unchanged, contextual field included
    print("\n--- TEST J: COMPOSITE RISK CONTEXTUAL INTEGRATION ---")
    resp_j = client.post("/api/v1/risk/composite", json={"latitude": lat, "longitude": lon})
    if resp_j.status_code != 200:
        print(f"[TEST J FAILED] Status: {resp_j.status_code}, Body: {resp_j.text}")
    assert resp_j.status_code == 200, f"Test J failed: {resp_j.text}"
    data_j = resp_j.json()
    print("Composite Risk Response Keys:", list(data_j.keys()))
    assert "composite_risk_index" in data_j
    assert "field_intelligence_context" in data_j
    assert data_j["field_intelligence_context"] is not None
    print(f"Composite Risk Index: {data_j['composite_risk_index']}, Field Intel Status: {data_j['field_intelligence_context']['status']}")
    print("[PASS] TEST J PASSED.")

    # TEST K: Existing Early Warning endpoint -> HTTP 200, ground observation context included
    print("\n--- TEST K: EARLY WARNING CONTEXTUAL INTEGRATION ---")
    resp_k = client.post("/api/v1/early-warning/analyze", json={"latitude": lat, "longitude": lon})
    if resp_k.status_code != 200:
        print(f"[TEST K FAILED] Status: {resp_k.status_code}, Body: {resp_k.text}")
    assert resp_k.status_code == 200, f"Test K failed: {resp_k.text}"
    data_k = resp_k.json()
    print("Early Warning Response Keys:", list(data_k.keys()))
    assert "warning_level" in data_k
    assert "ground_observation_context" in data_k
    assert data_k["ground_observation_context"] is not None
    print(f"Early Warning Level: {data_k['warning_level']}, Ground Status: {data_k['ground_observation_context']['status']}")
    print("[PASS] TEST K PASSED.")

    # TEST L: Existing Field Report CRUD endpoints
    print("\n--- TEST L: EXISTING FIELD REPORT CRUD ENDPOINTS ---")
    resp_list = client.get("/api/v1/field-reports")
    assert resp_list.status_code == 200

    resp_single = client.get(f"/api/v1/field-reports/{reports_g[0].id}")
    assert resp_single.status_code == 200

    resp_patch = client.patch(f"/api/v1/field-reports/{reports_g[0].id}/status", json={"status": "UNDER_REVIEW"})
    assert resp_patch.status_code == 200
    assert resp_patch.json()["status"] == "UNDER_REVIEW"
    print("[PASS] TEST L PASSED.")

    db.close()
    print("\n" + "=" * 80)
    print("ALL TESTS (TEST A - TEST L) PASSED SUCCESSFULLY!")
    print("=" * 80)

if __name__ == "__main__":
    run_tests()
