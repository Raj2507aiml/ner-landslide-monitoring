"""
Phase 8 Checkpoint 17.4 Test Suite: Integrated Operational Situation Assessment
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
from app.services.road_network_service import RoadNetworkService
from app.services.operational_assessment_service import OperationalAssessmentService
from app.schemas.operational_assessment import OperationalPriorityLevel

MOCK_ROADS = {
    "version": 0.6,
    "generator": "Overpass API",
    "elements": [
        {
            "type": "way",
            "id": 401,
            "tags": {"name": "NH-10 Highway", "ref": "NH10", "highway": "primary"},
            "geometry": [
                {"lat": 27.3300, "lon": 88.6100},
                {"lat": 27.3320, "lon": 88.6140},
                {"lat": 27.3350, "lon": 88.6180}
            ]
        },
        {
            "type": "way",
            "id": 402,
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
    db.commit()

def run_tests():
    Base.metadata.create_all(bind=engine)
    client = TestClient(app)

    print("=" * 80)
    print("PHASE 8 CHECKPOINT 17.4: OPERATIONAL SITUATION ASSESSMENT TESTS")
    print("=" * 80)

    db = SessionLocal()
    clean_db(db)

    lat, lon = 27.3314, 88.6138

    # Cache mock roads for offline determinism
    cache_path = RoadNetworkService.get_cache_path(lat, lon, 5.0)
    parsed = RoadNetworkService.parse_overpass_response(MOCK_ROADS)
    RoadNetworkService.save_to_cache(cache_path, parsed)

    # TEST A: Normal environmental + normal road + no field concerns -> ROUTINE / ATTENTION_REQUIRED
    print("\n--- TEST A: NORMAL INDICATORS -> ROUTINE / ATTENTION_REQUIRED ---")
    resp_a = client.get("/api/v1/operations/situation-assessment", params={"latitude": lat, "longitude": lon, "radius_km": 5.0})
    assert resp_a.status_code == 200, f"Error: {resp_a.text}"
    data_a = resp_a.json()
    print("Response A Priority:", data_a["operational_priority"])
    print("Environmental Context:", data_a["environmental_context"])
    print("Early Warning Context:", data_a["early_warning"])
    print("Infrastructure Context:", data_a["infrastructure_impact"])
    assert data_a["operational_priority"] in ["ROUTINE", "ATTENTION_REQUIRED"]
    print("[PASS] TEST A PASSED.")

    # Direct test at Guwahati (low slope plain area) for pure ROUTINE baseline
    lat_ghy, lon_ghy = 26.1445, 91.7362
    cache_ghy = RoadNetworkService.get_cache_path(lat_ghy, lon_ghy, 5.0)
    RoadNetworkService.save_to_cache(cache_ghy, parsed)
    res_routine = OperationalAssessmentService.evaluate_situation_assessment(
        db=db,
        latitude=lat_ghy,
        longitude=lon_ghy,
        radius_km=5.0,
        mock_raw_roads=MOCK_ROADS,
        mock_radar_change_data={"status": "PAIRED_SUCCESS", "radar_surface_change_signal": {"radar_surface_change_index": 5.0, "category": "Stable"}}
    )
    print(f"Guwahati Plain Area Priority: {res_routine.operational_priority.value}, Warning: {res_routine.early_warning.warning_level}")
    assert res_routine.operational_priority == OperationalPriorityLevel.ROUTINE
    print("[PASS] TEST A (Pure ROUTINE) PASSED.")

    # TEST B: WATCH warning -> ATTENTION_REQUIRED
    print("\n--- TEST B: WATCH WARNING -> ATTENTION_REQUIRED ---")
    clean_db(db)
    res_watch = OperationalAssessmentService.evaluate_situation_assessment(
        db=db,
        latitude=lat,
        longitude=lon,
        radius_km=5.0,
        mock_raw_roads=MOCK_ROADS,
        mock_radar_change_data={"status": "PAIRED_SUCCESS", "radar_surface_change_signal": {"radar_surface_change_index": 15.0, "category": "Minor"}}
    )
    print("Watch Scenario Early Warning:", res_watch.early_warning.warning_level)
    print("Watch Scenario Priority:", res_watch.operational_priority.value)
    assert res_watch.early_warning.warning_level == "WATCH"
    assert res_watch.operational_priority == OperationalPriorityLevel.ATTENTION_REQUIRED
    print("[PASS] TEST B PASSED.")

    # TEST C: MONITORING_REQUIRED road disruption -> ATTENTION_REQUIRED
    print("\n--- TEST C: MONITORING_REQUIRED ROAD DISRUPTION -> ATTENTION_REQUIRED ---")
    clean_db(db)
    db.add(FieldReport(
        report_type="CRACK",
        description="Crack on road shoulder",
        latitude=27.3320,
        longitude=88.6140,
        severity="MEDIUM",
        status="PENDING",
        created_at=datetime.utcnow()
    ))
    db.commit()

    resp_c = client.get("/api/v1/operations/situation-assessment", params={"latitude": lat, "longitude": lon, "radius_km": 5.0})
    data_c = resp_c.json()
    print("Disruption Status:", data_c["infrastructure_impact"]["disruption_status"])
    print("Operational Priority:", data_c["operational_priority"])
    assert data_c["infrastructure_impact"]["disruption_status"] == "MONITORING_REQUIRED"
    assert data_c["operational_priority"] == "ATTENTION_REQUIRED"
    print("[PASS] TEST C PASSED.")

    # TEST D: ALERT warning -> HIGH_PRIORITY
    print("\n--- TEST D: ALERT WARNING -> HIGH_PRIORITY ---")
    clean_db(db)
    res_alert = OperationalAssessmentService.evaluate_situation_assessment(
        db=db,
        latitude=lat,
        longitude=lon,
        radius_km=5.0,
        mock_raw_roads=MOCK_ROADS,
        mock_radar_change_data={"status": "PAIRED_SUCCESS", "radar_surface_change_signal": {"radar_surface_change_index": 50.0, "category": "Moderate"}}
    )
    print("Alert Scenario Early Warning:", res_alert.early_warning.warning_level)
    print("Alert Scenario Priority:", res_alert.operational_priority.value)
    assert res_alert.early_warning.warning_level == "ALERT"
    assert res_alert.operational_priority == OperationalPriorityLevel.HIGH_PRIORITY
    print("[PASS] TEST D PASSED.")

    # TEST E: ELEVATED_DISRUPTION -> HIGH_PRIORITY
    print("\n--- TEST E: ELEVATED_DISRUPTION -> HIGH_PRIORITY ---")
    clean_db(db)
    db.add(FieldReport(
        report_type="SLOPE_MOVEMENT",
        description="Soil creep near corridor",
        latitude=27.3320,
        longitude=88.6140,
        severity="MEDIUM",
        status="VERIFIED",
        created_at=datetime.utcnow()
    ))
    db.commit()

    resp_e = client.get("/api/v1/operations/situation-assessment", params={"latitude": lat, "longitude": lon, "radius_km": 5.0})
    data_e = resp_e.json()
    print("Disruption Status:", data_e["infrastructure_impact"]["disruption_status"])
    print("Operational Priority:", data_e["operational_priority"])
    assert data_e["infrastructure_impact"]["disruption_status"] == "ELEVATED_DISRUPTION"
    assert data_e["operational_priority"] in ["HIGH_PRIORITY", "CRITICAL_PRIORITY"]
    print("[PASS] TEST E PASSED.")

    # TEST F: HIGH_DISRUPTION -> HIGH_PRIORITY
    print("\n--- TEST F: HIGH_DISRUPTION -> HIGH_PRIORITY ---")
    clean_db(db)
    db.add(FieldReport(
        report_type="BLOCKED_ROAD",
        description="Boulders blocking corridor",
        latitude=27.3320,
        longitude=88.6140,
        severity="HIGH",
        status="VERIFIED",
        created_at=datetime.utcnow()
    ))
    db.commit()

    resp_f = client.get("/api/v1/operations/situation-assessment", params={"latitude": lat, "longitude": lon, "radius_km": 5.0})
    data_f = resp_f.json()
    print("Disruption Status:", data_f["infrastructure_impact"]["disruption_status"])
    print("Operational Priority:", data_f["operational_priority"])
    assert data_f["infrastructure_impact"]["disruption_status"] == "HIGH_DISRUPTION"
    assert data_f["operational_priority"] in ["HIGH_PRIORITY", "CRITICAL_PRIORITY"]
    print("[PASS] TEST F PASSED.")

    # TEST G: CRITICAL warning -> CRITICAL_PRIORITY
    print("\n--- TEST G: CRITICAL WARNING -> CRITICAL_PRIORITY ---")
    clean_db(db)
    res_crit_warn = OperationalAssessmentService.evaluate_situation_assessment(
        db=db,
        latitude=lat,
        longitude=lon,
        radius_km=5.0,
        mock_raw_roads=MOCK_ROADS,
        mock_radar_change_data={"status": "PAIRED_SUCCESS", "radar_surface_change_signal": {"radar_surface_change_index": 85.0, "category": "Severe"}}
    )
    print("Critical Warn Scenario Early Warning:", res_crit_warn.early_warning.warning_level)
    print("Critical Warn Scenario Priority:", res_crit_warn.operational_priority.value)
    assert res_crit_warn.early_warning.warning_level == "CRITICAL"
    assert res_crit_warn.operational_priority == OperationalPriorityLevel.CRITICAL_PRIORITY
    print("[PASS] TEST G PASSED.")

    # TEST H: CRITICAL_DISRUPTION -> CRITICAL_PRIORITY
    print("\n--- TEST H: CRITICAL_DISRUPTION -> CRITICAL_PRIORITY ---")
    clean_db(db)
    db.add(FieldReport(
        report_type="LANDSLIDE",
        description="Catastrophic mudflow",
        latitude=27.3410,
        longitude=88.6210,
        severity="CRITICAL",
        status="VERIFIED",
        created_at=datetime.utcnow()
    ))
    db.commit()

    resp_h = client.get("/api/v1/operations/situation-assessment", params={"latitude": lat, "longitude": lon, "radius_km": 5.0})
    data_h = resp_h.json()
    print("Disruption Status:", data_h["infrastructure_impact"]["disruption_status"])
    print("Operational Priority:", data_h["operational_priority"])
    assert data_h["infrastructure_impact"]["disruption_status"] == "CRITICAL_DISRUPTION"
    assert data_h["operational_priority"] == "CRITICAL_PRIORITY"
    print("[PASS] TEST H PASSED.")

    # TEST I: ALERT + HIGH_DISRUPTION -> CRITICAL_PRIORITY
    print("\n--- TEST I: ALERT + HIGH_DISRUPTION COMBINATION ---")
    clean_db(db)
    db.add(FieldReport(
        report_type="BLOCKED_ROAD",
        description="Blocked corridor road",
        latitude=27.3320,
        longitude=88.6140,
        severity="HIGH",
        status="VERIFIED",
        created_at=datetime.utcnow()
    ))
    db.commit()

    res_combo = OperationalAssessmentService.evaluate_situation_assessment(
        db=db,
        latitude=lat,
        longitude=lon,
        radius_km=5.0,
        mock_raw_roads=MOCK_ROADS,
        mock_radar_change_data={"status": "PAIRED_SUCCESS", "radar_surface_change_signal": {"radar_surface_change_index": 50.0, "category": "Moderate"}}
    )
    print("Combo Warning Level:", res_combo.early_warning.warning_level)
    print("Combo Disruption Status:", res_combo.infrastructure_impact.disruption_status)
    print("Combo Priority:", res_combo.operational_priority.value)
    assert res_combo.early_warning.warning_level == "ALERT"
    assert res_combo.infrastructure_impact.disruption_status == "HIGH_DISRUPTION"
    assert res_combo.operational_priority == OperationalPriorityLevel.CRITICAL_PRIORITY
    print("[PASS] TEST I PASSED.")

    # TEST J: Priority precedence verification
    print("\n--- TEST J: PRIORITY PRECEDENCE VERIFICATION ---")
    # CRITICAL_PRIORITY > HIGH_PRIORITY > ATTENTION_REQUIRED > ROUTINE
    assert OperationalPriorityLevel.CRITICAL_PRIORITY.value == "CRITICAL_PRIORITY"
    assert OperationalPriorityLevel.HIGH_PRIORITY.value == "HIGH_PRIORITY"
    assert OperationalPriorityLevel.ATTENTION_REQUIRED.value == "ATTENTION_REQUIRED"
    assert OperationalPriorityLevel.ROUTINE.value == "ROUTINE"
    print("[PASS] TEST J PASSED.")

    # TEST K: Priority reasons are explainable
    print("\n--- TEST K: EXPLAINABLE PRIORITY REASONS ---")
    assert len(data_h["priority_reasons"]) > 0
    print("Priority Reasons:", data_h["priority_reasons"])
    assert any("CRITICAL_DISRUPTION" in r or "severe" in r.lower() for r in data_h["priority_reasons"])
    print("[PASS] TEST K PASSED.")

    # TEST L: Recommended actions are generated
    print("\n--- TEST L: RECOMMENDED ACTIONS ---")
    assert len(data_h["recommended_actions"]) > 0
    print("Recommended Actions:", data_h["recommended_actions"])
    assert any("disaster management" in a.lower() or "emergency" in a.lower() for a in data_h["recommended_actions"])
    print("[PASS] TEST L PASSED.")

    # TEST M: Invalid coordinates validation
    print("\n--- TEST M: INVALID COORDINATES VALIDATION ---")
    resp_m = client.get("/api/v1/operations/situation-assessment", params={"latitude": 100.0, "longitude": 88.6138, "radius_km": 5.0})
    assert resp_m.status_code == 422
    print("[PASS] TEST M PASSED.")

    # TEST N: NER boundary validation
    print("\n--- TEST N: NER BOUNDARY VALIDATION ---")
    resp_n = client.get("/api/v1/operations/situation-assessment", params={"latitude": 28.6139, "longitude": 77.2090, "radius_km": 5.0})
    assert resp_n.status_code == 400
    print("[PASS] TEST N PASSED.")

    # TEST O: Existing Composite Risk regression
    print("\n--- TEST O: COMPOSITE RISK REGRESSION ---")
    resp_o = client.post("/api/v1/risk/composite", json={"latitude": lat, "longitude": lon})
    assert resp_o.status_code == 200
    assert "composite_risk_index" in resp_o.json()
    print("[PASS] TEST O PASSED.")

    # TEST P: Existing Early Warning regression
    print("\n--- TEST P: EARLY WARNING REGRESSION ---")
    resp_p = client.post("/api/v1/early-warning/analyze", json={"latitude": lat, "longitude": lon})
    assert resp_p.status_code == 200
    assert "warning_level" in resp_p.json()
    print("[PASS] TEST P PASSED.")

    # TEST Q: Existing Field Intelligence regression
    print("\n--- TEST Q: FIELD INTELLIGENCE REGRESSION ---")
    resp_q = client.get("/api/v1/field-reports/review-queue")
    assert resp_q.status_code == 200
    print("[PASS] TEST Q PASSED.")

    # TEST R: Existing Road Disruption regression
    print("\n--- TEST R: ROAD DISRUPTION REGRESSION ---")
    resp_r = client.get("/api/v1/infrastructure/roads/disruption-summary", params={"latitude": lat, "longitude": lon, "radius_km": 5.0})
    assert resp_r.status_code == 200
    assert "disruption_status" in resp_r.json()
    print("[PASS] TEST R PASSED.")

    db.close()
    print("\n" + "=" * 80)
    print("ALL TESTS (TEST A - TEST R) PASSED SUCCESSFULLY!")
    print("=" * 80)

if __name__ == "__main__":
    run_tests()
