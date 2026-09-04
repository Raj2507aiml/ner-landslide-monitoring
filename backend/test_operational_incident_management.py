"""
Phase 8 Checkpoint 18.1 Test Suite: Operational Incident Management Foundation
"""

import os
import sys
import json
from datetime import datetime, timedelta
from fastapi.testclient import TestClient

BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BACKEND_DIR)

from app.main import app
from app.database.session import SessionLocal, Base, engine
from app.models.operational_incident import OperationalIncident
from app.models.field_report import FieldReport
from app.models.field_report_media import FieldReportMedia
from app.services.road_network_service import RoadNetworkService
from app.services.operational_incident_service import OperationalIncidentService
from app.schemas.operational_incident import (
    IncidentSeverity,
    IncidentStatus,
    IncidentSource
)

MOCK_ROADS = {
    "version": 0.6,
    "generator": "Overpass API",
    "elements": [
        {
            "type": "way",
            "id": 501,
            "tags": {"name": "NH-10 Highway", "ref": "NH10", "highway": "primary"},
            "geometry": [
                {"lat": 27.3300, "lon": 88.6100},
                {"lat": 27.3320, "lon": 88.6140},
                {"lat": 27.3350, "lon": 88.6180}
            ]
        },
        {
            "type": "way",
            "id": 502,
            "tags": {"name": "Melli-Gangtok Road", "highway": "secondary"},
            "geometry": [
                {"lat": 27.3400, "lon": 88.6200},
                {"lat": 27.3450, "lon": 88.6250}
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
    print("PHASE 8 CHECKPOINT 18.1: OPERATIONAL INCIDENT MANAGEMENT TESTS")
    print("=" * 80)

    db = SessionLocal()
    clean_db(db)

    lat_gangtok, lon_gangtok = 27.3314, 88.6138
    lat_guwahati, lon_guwahati = 26.1445, 91.7362

    # Cache mock roads for offline determinism
    cache_path_gt = RoadNetworkService.get_cache_path(lat_gangtok, lon_gangtok, 5.0)
    cache_path_gw = RoadNetworkService.get_cache_path(lat_guwahati, lon_guwahati, 5.0)
    parsed = RoadNetworkService.parse_overpass_response(MOCK_ROADS)
    RoadNetworkService.save_to_cache(cache_path_gt, parsed)
    RoadNetworkService.save_to_cache(cache_path_gw, parsed)

    # TEST A: ROUTINE -> no incident
    print("\n--- TEST A: ROUTINE -> NO INCIDENT CREATED ---")
    clean_db(db)
    res_a = OperationalIncidentService.evaluate_and_create_incident(
        db=db,
        latitude=lat_guwahati,
        longitude=lon_guwahati,
        radius_km=5.0,
        mock_raw_roads=MOCK_ROADS,
        mock_radar_change_data={"status": "PAIRED_SUCCESS", "radar_surface_change_signal": {"radar_surface_change_index": 5.0, "category": "Stable"}}
    )
    print("Action A:", res_a["action"])
    assert res_a["action"] == "not_required"
    assert res_a["incident"] is None
    assert "does not trigger" in res_a["reason"]
    print("[PASS] TEST A PASSED.")

    # TEST B: ATTENTION_REQUIRED -> no incident
    print("\n--- TEST B: ATTENTION_REQUIRED -> NO INCIDENT CREATED ---")
    clean_db(db)
    res_b = OperationalIncidentService.evaluate_and_create_incident(
        db=db,
        latitude=lat_gangtok,
        longitude=lon_gangtok,
        radius_km=5.0,
        mock_raw_roads=MOCK_ROADS,
        mock_radar_change_data={"status": "PAIRED_SUCCESS", "radar_surface_change_signal": {"radar_surface_change_index": 15.0, "category": "Minor"}}
    )
    print("Action B:", res_b["action"])
    assert res_b["action"] == "not_required"
    assert res_b["incident"] is None
    print("[PASS] TEST B PASSED.")

    # TEST C: HIGH_PRIORITY -> HIGH incident created
    print("\n--- TEST C: HIGH_PRIORITY -> HIGH INCIDENT CREATED ---")
    clean_db(db)
    res_c = OperationalIncidentService.evaluate_and_create_incident(
        db=db,
        latitude=lat_gangtok,
        longitude=lon_gangtok,
        radius_km=5.0,
        mock_raw_roads=MOCK_ROADS,
        mock_radar_change_data={"status": "PAIRED_SUCCESS", "radar_surface_change_signal": {"radar_surface_change_index": 50.0, "category": "Moderate"}}
    )
    print("Action C:", res_c["action"])
    assert res_c["action"] == "created"
    assert res_c["incident"] is not None
    inc_c = res_c["incident"]
    assert inc_c.severity == IncidentSeverity.HIGH.value
    assert inc_c.status == IncidentStatus.OPEN.value
    print(f"Created Incident: {inc_c.incident_code}, Severity: {inc_c.severity}, Status: {inc_c.status}")
    print("[PASS] TEST C PASSED.")

    # TEST D: CRITICAL_PRIORITY -> CRITICAL incident created
    print("\n--- TEST D: CRITICAL_PRIORITY -> CRITICAL INCIDENT CREATED ---")
    clean_db(db)
    db.add(FieldReport(
        report_type="LANDSLIDE",
        description="Severe avalanche on road corridor",
        latitude=27.3410,
        longitude=88.6210,
        severity="CRITICAL",
        status="VERIFIED",
        created_at=datetime.utcnow()
    ))
    db.commit()

    res_d = OperationalIncidentService.evaluate_and_create_incident(
        db=db,
        latitude=lat_gangtok,
        longitude=lon_gangtok,
        radius_km=5.0,
        mock_raw_roads=MOCK_ROADS
    )
    print("Action D:", res_d["action"])
    assert res_d["action"] == "created"
    inc_d = res_d["incident"]
    assert inc_d.severity == IncidentSeverity.CRITICAL.value
    assert inc_d.status == IncidentStatus.OPEN.value
    print(f"Created Incident: {inc_d.incident_code}, Severity: {inc_d.severity}, Status: {inc_d.status}")
    print("[PASS] TEST D PASSED.")

    # TEST E: Evidence snapshot contains operational priority
    print("\n--- TEST E: EVIDENCE SNAPSHOT CONTAINS OPERATIONAL PRIORITY ---")
    snap = inc_d.evidence_snapshot
    assert "operational_priority" in snap
    assert snap["operational_priority"] == "CRITICAL_PRIORITY"
    print("Snapshot Operational Priority:", snap["operational_priority"])
    print("[PASS] TEST E PASSED.")

    # TEST F: Evidence snapshot contains environmental risk
    print("\n--- TEST F: EVIDENCE SNAPSHOT CONTAINS ENVIRONMENTAL RISK ---")
    assert "environmental_risk" in snap
    assert "composite_risk_index" in snap["environmental_risk"]
    assert "risk_level" in snap["environmental_risk"]
    print("Snapshot Environmental Risk:", snap["environmental_risk"])
    print("[PASS] TEST F PASSED.")

    # TEST G: Evidence snapshot contains early warning
    print("\n--- TEST G: EVIDENCE SNAPSHOT CONTAINS EARLY WARNING ---")
    assert "early_warning" in snap
    assert "warning_level" in snap["early_warning"]
    assert "operational_mode" in snap["early_warning"]
    print("Snapshot Early Warning:", snap["early_warning"])
    print("[PASS] TEST G PASSED.")

    # TEST H: Duplicate active incident prevented within geographic threshold (1.0 km)
    print("\n--- TEST H: DUPLICATE PREVENTION WITHIN 1.0 KM ---")
    # Evaluating again at the exact same location with same severe conditions
    res_h = OperationalIncidentService.evaluate_and_create_incident(
        db=db,
        latitude=lat_gangtok,
        longitude=lon_gangtok,
        radius_km=5.0,
        mock_raw_roads=MOCK_ROADS
    )
    print("Action H:", res_h["action"])
    assert res_h["action"] == "duplicate_prevented"
    assert res_h["incident"].id == inc_d.id
    assert "already exists within 1.0 km" in res_h["reason"]
    print("[PASS] TEST H PASSED.")

    # TEST I: Different geographic location allows new incident (> 1.0 km)
    print("\n--- TEST I: DIFFERENT LOCATION CREATES NEW INCIDENT ---")
    lat_shillong, lon_shillong = 25.5788, 91.8933
    cache_path_sh = RoadNetworkService.get_cache_path(lat_shillong, lon_shillong, 5.0)
    RoadNetworkService.save_to_cache(cache_path_sh, parsed)

    res_i = OperationalIncidentService.evaluate_and_create_incident(
        db=db,
        latitude=lat_shillong,
        longitude=lon_shillong,
        radius_km=5.0,
        mock_raw_roads=MOCK_ROADS,
        mock_radar_change_data={"status": "PAIRED_SUCCESS", "radar_surface_change_signal": {"radar_surface_change_index": 50.0, "category": "Moderate"}}
    )
    print("Action I:", res_i["action"])
    assert res_i["action"] == "created"
    assert res_i["incident"].id != inc_d.id
    print(f"Created Incident at Shillong: {res_i['incident'].incident_code}")
    print("[PASS] TEST I PASSED.")

    # TEST J: Resolved incident does not block future incident
    print("\n--- TEST J: RESOLVED INCIDENT DOES NOT BLOCK FUTURE INCIDENT ---")
    # Acknowledge, start response, and resolve incident D
    OperationalIncidentService.acknowledge_incident(db, inc_d.id)
    OperationalIncidentService.start_incident_response(db, inc_d.id)
    OperationalIncidentService.resolve_incident(db, inc_d.id)
    assert inc_d.status == IncidentStatus.RESOLVED.value

    # Evaluate again at Gangtok
    res_j = OperationalIncidentService.evaluate_and_create_incident(
        db=db,
        latitude=lat_gangtok,
        longitude=lon_gangtok,
        radius_km=5.0,
        mock_raw_roads=MOCK_ROADS
    )
    print("Action J after resolution:", res_j["action"])
    assert res_j["action"] == "created"
    assert res_j["incident"].id != inc_d.id
    print("[PASS] TEST J PASSED.")

    # TEST K: Incident code generation format
    print("\n--- TEST K: INCIDENT CODE GENERATION FORMAT ---")
    today_str = datetime.utcnow().strftime("%Y%m%d")
    code_format = res_j["incident"].incident_code
    print("Generated Incident Code:", code_format)
    assert code_format.startswith(f"INC-{today_str}-")
    seq_part = code_format.split("-")[-1]
    assert len(seq_part) == 4
    assert seq_part.isdigit()
    print("[PASS] TEST K PASSED.")

    # TEST L: OPEN -> ACKNOWLEDGED succeeds
    print("\n--- TEST L: OPEN -> ACKNOWLEDGED TRANSITION ---")
    inc_target = res_j["incident"]
    assert inc_target.status == "OPEN"
    assert inc_target.acknowledged_at is None

    ack_resp = client.post(f"/api/v1/incidents/{inc_target.id}/acknowledge", json={"notes": "Dispatched emergency crew."})
    assert ack_resp.status_code == 200
    data_ack = ack_resp.json()
    assert data_ack["status"] == "ACKNOWLEDGED"
    assert data_ack["acknowledged_at"] is not None
    print("Acknowledged At:", data_ack["acknowledged_at"])
    print("[PASS] TEST L PASSED.")

    # TEST M: ACKNOWLEDGED -> IN_PROGRESS succeeds
    print("\n--- TEST M: ACKNOWLEDGED -> IN_PROGRESS TRANSITION ---")
    resp_start = client.post(f"/api/v1/incidents/{inc_target.id}/start-response", json={"notes": "Crew arrived on scene."})
    assert resp_start.status_code == 200
    data_start = resp_start.json()
    assert data_start["status"] == "IN_PROGRESS"
    print("[PASS] TEST M PASSED.")

    # TEST N: IN_PROGRESS -> RESOLVED succeeds
    print("\n--- TEST N: IN_PROGRESS -> RESOLVED TRANSITION ---")
    resp_res = client.post(f"/api/v1/incidents/{inc_target.id}/resolve", json={"notes": "Road cleared and stabilized."})
    assert resp_res.status_code == 200
    data_res = resp_res.json()
    assert data_res["status"] == "RESOLVED"
    assert data_res["resolved_at"] is not None
    print("Resolved At:", data_res["resolved_at"])
    print("[PASS] TEST N PASSED.")

    # TEST O: Invalid lifecycle transition rejected
    print("\n--- TEST O: INVALID LIFECYCLE TRANSITION REJECTED ---")
    # Trying to acknowledge an already RESOLVED incident
    resp_invalid = client.post(f"/api/v1/incidents/{inc_target.id}/acknowledge")
    assert resp_invalid.status_code == 400
    print("Error on invalid transition:", resp_invalid.json()["detail"])
    print("[PASS] TEST O PASSED.")

    # TEST P: Incident listing works
    print("\n--- TEST P: INCIDENT LISTING ---")
    resp_list = client.get("/api/v1/incidents")
    assert resp_list.status_code == 200
    data_list = resp_list.json()
    assert "total" in data_list
    assert "incidents" in data_list
    assert data_list["total"] >= 2
    print(f"Total Listed Incidents: {data_list['total']}")
    print("[PASS] TEST P PASSED.")

    # TEST Q: Incident filtering by severity works
    print("\n--- TEST Q: INCIDENT FILTERING BY SEVERITY ---")
    resp_crit = client.get("/api/v1/incidents", params={"severity": "CRITICAL"})
    assert resp_crit.status_code == 200
    assert all(inc["severity"] == "CRITICAL" for inc in resp_crit.json()["incidents"])
    print("[PASS] TEST Q PASSED.")

    # TEST R: Incident filtering by status works
    print("\n--- TEST R: INCIDENT FILTERING BY STATUS ---")
    resp_stat = client.get("/api/v1/incidents", params={"status": "RESOLVED"})
    assert resp_stat.status_code == 200
    assert all(inc["status"] == "RESOLVED" for inc in resp_stat.json()["incidents"])
    print("[PASS] TEST R PASSED.")

    # TEST S: Incident detail endpoint works
    print("\n--- TEST S: INCIDENT DETAIL ENDPOINT ---")
    resp_detail = client.get(f"/api/v1/incidents/{inc_target.id}")
    assert resp_detail.status_code == 200
    assert resp_detail.json()["id"] == inc_target.id
    print("[PASS] TEST S PASSED.")

    # TEST T: NER boundary validation works
    print("\n--- TEST T: NER BOUNDARY VALIDATION ---")
    resp_t = client.post("/api/v1/incidents/evaluate", params={"latitude": 28.6139, "longitude": 77.2090, "radius_km": 5.0})
    assert resp_t.status_code == 400
    print("[PASS] TEST T PASSED.")

    # TEST U: Existing Operational Situation Assessment regression remains functional
    print("\n--- TEST U: OPERATIONAL SITUATION ASSESSMENT REGRESSION ---")
    resp_u = client.get("/api/v1/operations/situation-assessment", params={"latitude": lat_gangtok, "longitude": lon_gangtok, "radius_km": 5.0})
    assert resp_u.status_code == 200
    assert "operational_priority" in resp_u.json()
    print("[PASS] TEST U PASSED.")

    # TEST V: Existing Road Disruption regression remains functional
    print("\n--- TEST V: ROAD DISRUPTION REGRESSION ---")
    resp_v = client.get("/api/v1/infrastructure/roads/disruption-summary", params={"latitude": lat_gangtok, "longitude": lon_gangtok, "radius_km": 5.0})
    assert resp_v.status_code == 200
    assert "disruption_status" in resp_v.json()
    print("[PASS] TEST V PASSED.")

    # TEST W: Existing Early Warning regression remains functional
    print("\n--- TEST W: EARLY WARNING REGRESSION ---")
    resp_w = client.post("/api/v1/early-warning/analyze", json={"latitude": lat_gangtok, "longitude": lon_gangtok})
    assert resp_w.status_code == 200
    assert "warning_level" in resp_w.json()
    print("[PASS] TEST W PASSED.")

    # TEST X: Existing Composite Risk regression remains functional
    print("\n--- TEST X: COMPOSITE RISK REGRESSION ---")
    resp_x = client.post("/api/v1/risk/composite", json={"latitude": lat_gangtok, "longitude": lon_gangtok})
    assert resp_x.status_code == 200
    assert "composite_risk_index" in resp_x.json()
    print("[PASS] TEST X PASSED.")

    db.close()
    print("\n" + "=" * 80)
    print("ALL TESTS (TEST A - TEST X) PASSED SUCCESSFULLY!")
    print("=" * 80)

if __name__ == "__main__":
    run_tests()
