import os
import sys
import json
from fastapi.testclient import TestClient

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.abspath(os.path.join(SCRIPTS_DIR, ".."))
sys.path.insert(0, BACKEND_DIR)

from app.main import app
from app.database.session import SessionLocal, Base, engine
from app.models.field_report import FieldReport

def run_tests():
    # Ensure all tables are created
    Base.metadata.create_all(bind=engine)
    client = TestClient(app)
    
    print("=" * 80)
    print("PHASE 7 CHECKPOINT 16.1 - FIELD INTELLIGENCE REPORTING TESTS")
    print("=" * 80)

    # Clean up test table records before test
    db = SessionLocal()
    db.query(FieldReport).delete()
    db.commit()
    db.close()

    # Test A: Create Valid Field Report
    print("\n--- TEST A: CREATE VALID FIELD REPORT ---")
    valid_payload = {
        "report_type": "CRACK",
        "description": "Large crack observed near roadside slope after rainfall.",
        "latitude": 27.3314,
        "longitude": 88.6138,
        "reporter_type": "CITIZEN",
        "severity": "HIGH"
    }
    resp_create = client.post("/api/v1/field-reports", json=valid_payload)
    print(f"Status Code: {resp_create.status_code}")
    assert resp_create.status_code == 201, f"Expected 201, got {resp_create.status_code}"
    report_data = resp_create.json()
    print("Created Report Payload:", json.dumps(report_data, indent=2))
    assert report_data["id"] is not None
    assert report_data["report_type"] == "CRACK"
    assert report_data["status"] == "PENDING"
    assert report_data["reporter_type"] == "CITIZEN"
    assert report_data["severity"] == "HIGH"
    report_id = report_data["id"]
    print(">>> TEST A PASSED.")

    # Create a second report for filtering tests
    official_payload = {
        "report_type": "SLOPE_MOVEMENT",
        "description": "Active slope movement detected near highway km 42.",
        "latitude": 25.5270,
        "longitude": 91.3584,
        "reporter_type": "FIELD_OFFICIAL",
        "severity": "CRITICAL"
    }
    resp_create2 = client.post("/api/v1/field-reports", json=official_payload)
    assert resp_create2.status_code == 201
    report_id2 = resp_create2.json()["id"]

    # Test B: Retrieve Reports (All and Filtered)
    print("\n--- TEST B: RETRIEVE REPORTS (LISTING & FILTERING) ---")
    # All reports
    resp_list = client.get("/api/v1/field-reports")
    assert resp_list.status_code == 200
    reports = resp_list.json()
    print(f"Total reports retrieved: {len(reports)}")
    assert len(reports) == 2

    # Filter by report_type = CRACK
    resp_filter_type = client.get("/api/v1/field-reports?report_type=CRACK")
    assert resp_filter_type.status_code == 200
    filtered_type = resp_filter_type.json()
    print(f"Filtered (report_type=CRACK) count: {len(filtered_type)}")
    assert len(filtered_type) == 1
    assert filtered_type[0]["report_type"] == "CRACK"

    # Filter by status = PENDING
    resp_filter_status = client.get("/api/v1/field-reports?status=PENDING")
    assert resp_filter_status.status_code == 200
    filtered_status = resp_filter_status.json()
    print(f"Filtered (status=PENDING) count: {len(filtered_status)}")
    assert len(filtered_status) == 2
    print(">>> TEST B PASSED.")

    # Test C: Retrieve Report by ID
    print("\n--- TEST C: RETRIEVE REPORT BY ID ---")
    resp_get = client.get(f"/api/v1/field-reports/{report_id}")
    print(f"Status Code: {resp_get.status_code}")
    assert resp_get.status_code == 200
    assert resp_get.json()["id"] == report_id
    assert resp_get.json()["description"] == valid_payload["description"]

    # Non-existent report ID
    resp_get_404 = client.get("/api/v1/field-reports/999999")
    print(f"Non-existent ID Status Code: {resp_get_404.status_code}")
    assert resp_get_404.status_code == 404
    print(">>> TEST C PASSED.")

    # Test D: Update Report Status
    print("\n--- TEST D: UPDATE REPORT STATUS ---")
    update_payload = {"status": "UNDER_REVIEW"}
    resp_patch1 = client.patch(f"/api/v1/field-reports/{report_id}/status", json=update_payload)
    print(f"Update to UNDER_REVIEW Status Code: {resp_patch1.status_code}")
    assert resp_patch1.status_code == 200
    assert resp_patch1.json()["status"] == "UNDER_REVIEW"

    update_payload2 = {"status": "VERIFIED"}
    resp_patch2 = client.patch(f"/api/v1/field-reports/{report_id}/status", json=update_payload2)
    assert resp_patch2.status_code == 200
    assert resp_patch2.json()["status"] == "VERIFIED"

    # Update non-existent report
    resp_patch_404 = client.patch("/api/v1/field-reports/999999/status", json=update_payload2)
    assert resp_patch_404.status_code == 404
    print(">>> TEST D PASSED.")

    # Test E: Invalid Coordinates
    print("\n--- TEST E: INVALID COORDINATES VALIDATION ---")
    # Coordinates out of global bounds (>90 lat)
    out_of_bounds_payload = {
        "report_type": "CRACK",
        "description": "Invalid lat coordinate test.",
        "latitude": 120.0,
        "longitude": 88.6138,
        "reporter_type": "CITIZEN",
        "severity": "LOW"
    }
    resp_inv_coord = client.post("/api/v1/field-reports", json=out_of_bounds_payload)
    print(f"Out of Bounds Lat Status Code: {resp_inv_coord.status_code}")
    assert resp_inv_coord.status_code == 422, "Pydantic should reject latitude > 90"

    # Coordinates outside NER (New Delhi)
    outside_ner_payload = {
        "report_type": "CRACK",
        "description": "Report submitted from Delhi.",
        "latitude": 28.6139,
        "longitude": 77.2090,
        "reporter_type": "CITIZEN",
        "severity": "LOW"
    }
    resp_out_ner = client.post("/api/v1/field-reports", json=outside_ner_payload)
    print(f"Outside NER Status Code: {resp_out_ner.status_code}")
    assert resp_out_ner.status_code == 400
    assert "North Eastern Region" in resp_out_ner.json()["detail"]
    print(">>> TEST E PASSED.")

    # Test F: Invalid Enum / Category Values
    print("\n--- TEST F: INVALID ENUM / CATEGORY VALUES ---")
    invalid_enum_payload = {
        "report_type": "EXPLOSION", # Invalid type
        "description": "Invalid report type test.",
        "latitude": 27.3314,
        "longitude": 88.6138,
        "reporter_type": "ROBOT", # Invalid reporter type
        "severity": "APOCALYPSE" # Invalid severity
    }
    resp_inv_enum = client.post("/api/v1/field-reports", json=invalid_enum_payload)
    print(f"Invalid Enum Status Code: {resp_inv_enum.status_code}")
    assert resp_inv_enum.status_code == 422
    print(">>> TEST F PASSED.")

    # Test G: Confirm Existing APIs Still Work
    print("\n--- TEST G: BACKWARD COMPATIBILITY & EXISTING API SMOKE TEST ---")
    # Health endpoint
    resp_health = client.get("/api/health")
    assert resp_health.status_code == 200
    print(f"Health API: {resp_health.json()}")

    # Early warning endpoint
    resp_ew = client.post("/api/v1/early-warning/analyze", json={"latitude": 27.3314, "longitude": 88.6138})
    assert resp_ew.status_code == 200
    print(f"Early Warning API: Status=200, Warning Level={resp_ew.json()['warning_level']}")

    # Composite risk endpoint
    resp_risk = client.post("/api/v1/risk/composite", json={"latitude": 27.3314, "longitude": 88.6138})
    assert resp_risk.status_code == 200
    print(f"Composite Risk API: Status=200, Risk Index={resp_risk.json()['composite_risk_index']}")
    print(">>> TEST G PASSED.")

    print("\n" + "=" * 80)
    print("ALL FIELD INTELLIGENCE REPORTING TESTS (A - G) PASSED SUCCESSFULLY!")
    print("=" * 80)

if __name__ == "__main__":
    run_tests()
