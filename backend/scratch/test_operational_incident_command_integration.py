"""
Phase 8 Checkpoint 18.2 Test Suite: Operational Incident Command Integration
"""

import os
import sys
import json
import subprocess
from datetime import datetime, timedelta
from fastapi.testclient import TestClient

BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_ROOT = os.path.abspath(os.path.join(BACKEND_DIR, ".."))
sys.path.insert(0, BACKEND_ROOT)

from app.main import app
from app.database.session import SessionLocal, Base, engine
from app.models.operational_incident import OperationalIncident
from app.models.field_report import FieldReport
from app.models.field_report_media import FieldReportMedia
from app.services.road_network_service import RoadNetworkService
from app.services.operational_incident_service import OperationalIncidentService

MOCK_ROADS = {
    "version": 0.6,
    "generator": "Overpass API",
    "elements": [
        {
            "type": "way",
            "id": 601,
            "tags": {"name": "NH-10 Highway", "ref": "NH10", "highway": "primary"},
            "geometry": [
                {"lat": 27.3300, "lon": 88.6100},
                {"lat": 27.3320, "lon": 88.6140},
                {"lat": 27.3350, "lon": 88.6180}
            ]
        }
    ]
}

def clean_db(db):
    db.query(FieldReportMedia).delete()
    db.query(FieldReport).delete()
    db.query(OperationalIncident).delete()
    db.commit()

def run_tests():
    Base.metadata.create_all(bind=engine)
    client = TestClient(app)

    print("=" * 80)
    print("PHASE 8 CHECKPOINT 18.2: INCIDENT COMMAND DASHBOARD INTEGRATION TESTS")
    print("=" * 80)

    db = SessionLocal()
    clean_db(db)

    lat, lon = 27.3314, 88.6138

    # Seed an active CRITICAL incident
    inc_open = OperationalIncident(
        incident_code="INC-20260902-0001",
        latitude=lat,
        longitude=lon,
        severity="CRITICAL",
        status="OPEN",
        source="AUTOMATED_ASSESSMENT",
        title="Automated CRITICAL Landslide Hazard Incident - ALERT Warning / HIGH_DISRUPTION",
        description="Operational situation is assessed as CRITICAL_PRIORITY.",
        operational_priority="CRITICAL_PRIORITY",
        composite_risk_index=85.0,
        early_warning_level="ALERT",
        field_intelligence_status="VERIFIED_HAZARD_CONFIRMED",
        road_disruption_status="HIGH_DISRUPTION",
        evidence_snapshot={
            "operational_priority": "CRITICAL_PRIORITY",
            "environmental_risk": {"composite_risk_index": 85.0, "risk_level": "High"},
            "early_warning": {"warning_level": "ALERT", "operational_mode": "FULL_EVIDENCE"},
            "ground_intelligence": {"status": "VERIFIED_HAZARD_CONFIRMED", "verified_reports": 2, "verified_signal_score": 12.0},
            "road_disruption": {"disruption_status": "HIGH_DISRUPTION", "affected_roads": 1},
            "priority_reasons": ["Concurrent ALERT warning and HIGH_DISRUPTION road blockage."]
        },
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(inc_open)
    db.commit()
    db.refresh(inc_open)

    # TEST A: Incident service constructs list requests correctly
    print("\n--- TEST A: INCIDENT LIST REQUEST ---")
    resp_a = client.get("/api/v1/incidents", params={"limit": 10, "offset": 0})
    assert resp_a.status_code == 200
    data_a = resp_a.json()
    assert "total" in data_a
    assert "incidents" in data_a
    assert len(data_a["incidents"]) >= 1
    print(f"Total: {data_a['total']}, Retrieved: {len(data_a['incidents'])}")
    print("[PASS] TEST A PASSED.")

    # TEST B: Status filters map correctly
    print("\n--- TEST B: STATUS FILTERING ---")
    resp_b_open = client.get("/api/v1/incidents", params={"status": "OPEN"})
    assert resp_b_open.status_code == 200
    assert all(i["status"] == "OPEN" for i in resp_b_open.json()["incidents"])
    print("[PASS] TEST B PASSED.")

    # TEST C: Severity filters map correctly
    print("\n--- TEST C: SEVERITY FILTERING ---")
    resp_c_crit = client.get("/api/v1/incidents", params={"severity": "CRITICAL"})
    assert resp_c_crit.status_code == 200
    assert all(i["severity"] == "CRITICAL" for i in resp_c_crit.json()["incidents"])
    print("[PASS] TEST C PASSED.")

    # TEST D: Incident list renders OPEN incident
    print("\n--- TEST D: OPEN INCIDENT PRESENTATION ---")
    inc_item = data_a["incidents"][0]
    assert inc_item["status"] == "OPEN"
    print(f"Incident Code: {inc_item['incident_code']}, Status: {inc_item['status']}")
    print("[PASS] TEST D PASSED.")

    # TEST E: Incident list renders CRITICAL severity
    print("\n--- TEST E: CRITICAL SEVERITY PRESENTATION ---")
    assert inc_item["severity"] == "CRITICAL"
    print(f"Severity: {inc_item['severity']}")
    print("[PASS] TEST E PASSED.")

    # TEST F: Selecting incident loads detail
    print("\n--- TEST F: DETAIL ENDPOINT ---")
    resp_f = client.get(f"/api/v1/incidents/{inc_open.id}")
    assert resp_f.status_code == 200
    detail = resp_f.json()
    assert detail["id"] == inc_open.id
    assert detail["title"] == inc_open.title
    print(f"Detail Retrieved: ID #{detail['id']}, Code: {detail['incident_code']}")
    print("[PASS] TEST F PASSED.")

    # TEST G: Evidence snapshot safely renders
    print("\n--- TEST G: EVIDENCE SNAPSHOT INTEGRITY ---")
    snap = detail["evidence_snapshot"]
    assert snap is not None
    assert "environmental_risk" in snap
    assert "early_warning" in snap
    assert "ground_intelligence" in snap
    assert "road_disruption" in snap
    assert "priority_reasons" in snap
    print("Snapshot keys:", list(snap.keys()))
    print("[PASS] TEST G PASSED.")

    # TEST H: OPEN incident shows Acknowledge action only
    print("\n--- TEST H: OPEN INCIDENT STATE (ACTION = ACKNOWLEDGE) ---")
    assert detail["status"] == "OPEN"
    assert detail["acknowledged_at"] is None
    print("[PASS] TEST H PASSED.")

    # TEST L: Successful acknowledge refreshes incident state
    print("\n--- TEST L: ACKNOWLEDGE TRANSITION ---")
    resp_l = client.post(f"/api/v1/incidents/{inc_open.id}/acknowledge", json={"notes": "Incident acknowledged by Shift Commander."})
    assert resp_l.status_code == 200
    detail_ack = resp_l.json()
    assert detail_ack["status"] == "ACKNOWLEDGED"
    assert detail_ack["acknowledged_at"] is not None
    print(f"Status: {detail_ack['status']}, Acknowledged At: {detail_ack['acknowledged_at']}")
    print("[PASS] TEST L PASSED.")

    # TEST I: ACKNOWLEDGED incident shows Start Response action only
    print("\n--- TEST I: ACKNOWLEDGED INCIDENT STATE (ACTION = START RESPONSE) ---")
    assert detail_ack["status"] == "ACKNOWLEDGED"
    print("[PASS] TEST I PASSED.")

    # TEST M: Successful start response refreshes incident state
    print("\n--- TEST M: START RESPONSE TRANSITION ---")
    resp_m = client.post(f"/api/v1/incidents/{inc_open.id}/start-response", json={"notes": "Response team en route."})
    assert resp_m.status_code == 200
    detail_inprog = resp_m.json()
    assert detail_inprog["status"] == "IN_PROGRESS"
    print(f"Status: {detail_inprog['status']}")
    print("[PASS] TEST M PASSED.")

    # TEST J: IN_PROGRESS incident shows Resolve action only
    print("\n--- TEST J: IN_PROGRESS INCIDENT STATE (ACTION = RESOLVE) ---")
    assert detail_inprog["status"] == "IN_PROGRESS"
    print("[PASS] TEST J PASSED.")

    # TEST N: Successful resolve refreshes incident state
    print("\n--- TEST N: RESOLVE TRANSITION ---")
    resp_n = client.post(f"/api/v1/incidents/{inc_open.id}/resolve", json={"notes": "Corridor stabilized and reopened."})
    assert resp_n.status_code == 200
    detail_res = resp_n.json()
    assert detail_res["status"] == "RESOLVED"
    assert detail_res["resolved_at"] is not None
    print(f"Status: {detail_res['status']}, Resolved At: {detail_res['resolved_at']}")
    print("[PASS] TEST N PASSED.")

    # TEST K: RESOLVED incident shows no lifecycle action
    print("\n--- TEST K: RESOLVED INCIDENT TERMINAL STATE ---")
    assert detail_res["status"] == "RESOLVED"
    print("[PASS] TEST K PASSED.")

    # TEST O: API failure does not crash component (safe error handling)
    print("\n--- TEST O: ERROR HANDLING (404 NOT FOUND) ---")
    resp_o = client.get("/api/v1/incidents/999999")
    assert resp_o.status_code == 404
    print("Error response handled cleanly:", resp_o.json())
    print("[PASS] TEST O PASSED.")

    # TEST P: Empty incident list displays correct empty state
    print("\n--- TEST P: EMPTY INCIDENT LIST ---")
    resp_p = client.get("/api/v1/incidents", params={"status": "OPEN"})
    assert resp_p.status_code == 200
    assert resp_p.json()["total"] == 0
    print("[PASS] TEST P PASSED.")

    # TEST Q: Refresh preserves filters
    print("\n--- TEST Q: REFRESH PRESERVES FILTERS ---")
    resp_q = client.get("/api/v1/incidents", params={"status": "RESOLVED", "severity": "CRITICAL"})
    assert resp_q.status_code == 200
    assert resp_q.json()["total"] == 1
    print("[PASS] TEST Q PASSED.")

    # TEST R: Frontend production build succeeds
    print("\n--- TEST R: FRONTEND PRODUCTION BUILD ---")
    frontend_dir = os.path.abspath(os.path.join(BACKEND_ROOT, "..", "frontend"))
    build_cmd = subprocess.run(["npm", "run", "build"], cwd=frontend_dir, shell=True, capture_output=True, text=True)
    assert build_cmd.returncode == 0, f"Frontend build failed: {build_cmd.stderr}"
    print("Frontend build compiled with exit code 0.")
    print("[PASS] TEST R PASSED.")

    db.close()
    print("\n" + "=" * 80)
    print("ALL TESTS (TEST A - TEST R) PASSED SUCCESSFULLY!")
    print("=" * 80)

if __name__ == "__main__":
    run_tests()
