"""
Phase 7 Checkpoint 16.3 Test Suite - Field Intelligence Spatial Validation & Map Integration
"""

import os
import sys
import io
import json
from PIL import Image
from fastapi.testclient import TestClient

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.abspath(os.path.join(SCRIPTS_DIR, ".."))
sys.path.insert(0, BACKEND_DIR)

from app.main import app
from app.database.session import SessionLocal, Base, engine
from app.models.field_report import FieldReport
from app.models.field_report_media import FieldReportMedia

def create_synthetic_image(format="JPEG", size=(100, 100), color="blue", with_exif=False) -> bytes:
    buf = io.BytesIO()
    img = Image.new("RGB", size, color=color)
    if with_exif:
        exif = img.getexif()
        gps_ifd = exif.get_ifd(34853)
        gps_ifd[1] = "N"
        gps_ifd[2] = (27.0, 19.0, 53.04) # 27.3314 N
        gps_ifd[3] = "E"
        gps_ifd[4] = (88.0, 36.0, 49.68) # 88.6138 E
        img.save(buf, format=format, exif=exif)
    else:
        img.save(buf, format=format)
    buf.seek(0)
    return buf.read()

def run_spatial_tests():
    Base.metadata.create_all(bind=engine)
    client = TestClient(app)
    
    print("=" * 80)
    print("PHASE 7 CHECKPOINT 16.3 - SPATIAL VALIDATION & MAP INTEGRATION TESTS")
    print("=" * 80)

    # Clean up test database records
    db = SessionLocal()
    db.query(FieldReportMedia).delete()
    db.query(FieldReport).delete()
    db.commit()
    db.close()

    # TEST A: Create multiple reports at controlled coordinates
    print("\n--- TEST A: CREATE CONTROLLED SPATIAL TEST REPORTS ---")
    # Base location: Gangtok Center (27.3314, 88.6138)
    reports_to_create = [
        # Report 1: Gangtok Epicenter - CRACK (Verified)
        {
            "report_type": "CRACK",
            "description": "Primary slope crack on Ridge Road.",
            "latitude": 27.3314,
            "longitude": 88.6138,
            "reporter_type": "FIELD_OFFICIAL",
            "severity": "CRITICAL",
            "status": "VERIFIED"
        },
        # Report 2: Gangtok Nearby (~0.25 km) - Same Type CRACK (Duplicate Candidate)
        {
            "report_type": "CRACK",
            "description": "Fissure observed 250m down from Ridge Road.",
            "latitude": 27.3330,
            "longitude": 88.6145,
            "reporter_type": "CITIZEN",
            "severity": "HIGH",
            "status": "PENDING"
        },
        # Report 3: Gangtok Nearby (~0.25 km) - Different Type BLOCKED_ROAD (Non-duplicate)
        {
            "report_type": "BLOCKED_ROAD",
            "description": "Small rockfall debris blocking lane.",
            "latitude": 27.3325,
            "longitude": 88.6140,
            "reporter_type": "CITIZEN",
            "severity": "MEDIUM",
            "status": "UNDER_REVIEW"
        },
        # Report 4: Gangtok Suburb (~3.2 km) - LANDSLIDE
        {
            "report_type": "LANDSLIDE",
            "description": "Mudflow on hillslope towards Ranipool.",
            "latitude": 27.3050,
            "longitude": 88.6000,
            "reporter_type": "FIELD_OFFICIAL",
            "severity": "CRITICAL",
            "status": "VERIFIED"
        },
        # Report 5: Distant Location (~45 km away in West Sikkim) - DEBRIS
        {
            "report_type": "DEBRIS",
            "description": "Debris pile near Pelling roadway.",
            "latitude": 27.2885,
            "longitude": 88.2370,
            "reporter_type": "CITIZEN",
            "severity": "LOW",
            "status": "REJECTED"
        }
    ]

    created_ids = []
    for item in reports_to_create:
        status_val = item.pop("status")
        resp = client.post("/api/v1/field-reports", json=item)
        assert resp.status_code == 201, f"Failed to create report: {resp.text}"
        rep_id = resp.json()["id"]
        # Update status if not PENDING
        if status_val != "PENDING":
            client.patch(f"/api/v1/field-reports/{rep_id}/status", json={"status": status_val})
        created_ids.append(rep_id)
    print(f"Created {len(created_ids)} test reports with IDs: {created_ids}")

    # Attach media with EXIF to Report 1
    img_with_exif = create_synthetic_image(format="JPEG", with_exif=True)
    resp_media = client.post(
        f"/api/v1/field-reports/{created_ids[0]}/media",
        files={"file": ("evidence_exif.jpg", io.BytesIO(img_with_exif), "image/jpeg")}
    )
    assert resp_media.status_code == 201
    print(f"Attached geo-tagged media to Report {created_ids[0]}")
    print(">>> TEST A PASSED.")

    # TEST B: Nearby Spatial Query within 5 km
    print("\n--- TEST B: NEARBY SPATIAL QUERY WITHIN 5.0 KM ---")
    resp_nearby = client.get(
        "/api/v1/field-reports/nearby",
        params={"latitude": 27.3314, "longitude": 88.6138, "radius_km": 5.0}
    )
    assert resp_nearby.status_code == 200
    nearby_data = resp_nearby.json()
    print(f"Found {len(nearby_data)} reports within 5.0 km")
    nearby_ids = [r["id"] for r in nearby_data]
    print(f"Nearby IDs: {nearby_ids}")
    # Should include reports 1, 2, 3, 4 (all <= 5km), but exclude report 5 (~45km)
    assert created_ids[0] in nearby_ids
    assert created_ids[1] in nearby_ids
    assert created_ids[2] in nearby_ids
    assert created_ids[3] in nearby_ids
    assert created_ids[4] not in nearby_ids
    print(">>> TEST B PASSED.")

    # TEST C: Reports Outside Radius are Excluded
    print("\n--- TEST C: VERIFY OUT-OF-RADIUS EXCLUSION ---")
    # Search with tight radius 1.0 km (should only get 1, 2, 3)
    resp_tight = client.get(
        "/api/v1/field-reports/nearby",
        params={"latitude": 27.3314, "longitude": 88.6138, "radius_km": 1.0}
    )
    assert resp_tight.status_code == 200
    tight_ids = [r["id"] for r in resp_tight.json()]
    print(f"Reports within 1.0 km: {tight_ids}")
    assert created_ids[0] in tight_ids
    assert created_ids[1] in tight_ids
    assert created_ids[2] in tight_ids
    assert created_ids[3] not in tight_ids  # ~3.2km away
    assert created_ids[4] not in tight_ids  # ~45km away
    print(">>> TEST C PASSED.")

    # TEST D: Distance km Values are Finite, Positive, and Sorted
    print("\n--- TEST D: DISTANCE INTEGRITY & SORTING ---")
    distances = [r["distance_km"] for r in nearby_data]
    print(f"Calculated distances: {distances}")
    for d in distances:
        assert d >= 0.0, f"Negative distance found: {d}"
        assert not (d != d), "NaN distance found" # NaN check
    # Check sorted order
    assert distances == sorted(distances), "Nearby reports must be sorted by distance ascending"
    print(">>> TEST D PASSED.")

    # TEST E: Field Intelligence Summary
    print("\n--- TEST E: FIELD INTELLIGENCE SUMMARY ENDPOINT ---")
    resp_summary = client.post(
        "/api/v1/field-reports/intelligence-summary",
        json={"latitude": 27.3314, "longitude": 88.6138, "radius_km": 5.0}
    )
    assert resp_summary.status_code == 200
    summary = resp_summary.json()
    print("Intelligence Summary Output:", json.dumps(summary, indent=2))
    assert summary["total_reports"] == 4
    assert summary["verified_reports"] == 2 # 1 and 4
    assert summary["pending_reports"] == 1  # 2
    assert summary["under_review_reports"] == 1 # 3
    assert summary["rejected_reports"] == 0
    assert summary["report_types_breakdown"]["CRACK"] == 2
    assert summary["report_types_breakdown"]["BLOCKED_ROAD"] == 1
    assert summary["report_types_breakdown"]["LANDSLIDE"] == 1
    assert summary["severity_breakdown"]["CRITICAL"] == 2
    assert summary["evidence_statistics"]["reports_with_media"] == 1
    assert summary["evidence_statistics"]["reports_with_exif_gps"] == 1
    print(">>> TEST E PASSED.")

    # TEST F: Verified vs Unverified Observation Separation
    print("\n--- TEST F: VERIFIED VS UNVERIFIED OBSERVATION SEPARATION ---")
    assert summary["verified_observations"] == 2
    assert summary["unverified_observations"] == 2 # pending (1) + under_review (1)
    print(f"Verified Observations: {summary['verified_observations']} | Unverified: {summary['unverified_observations']}")
    print(">>> TEST F PASSED.")

    # TEST G: Duplicate Detection (Same Type Nearby)
    print("\n--- TEST G: DUPLICATE DETECTION FOR SAME-TYPE NEARBY REPORTS ---")
    rep1_data = next(r for r in nearby_data if r["id"] == created_ids[0])
    rep2_data = next(r for r in nearby_data if r["id"] == created_ids[1])
    print(f"Report 1 ({rep1_data['report_type']}) potential_duplicate: {rep1_data['potential_duplicate']}, related: {rep1_data['related_report_ids']}")
    print(f"Report 2 ({rep2_data['report_type']}) potential_duplicate: {rep2_data['potential_duplicate']}, related: {rep2_data['related_report_ids']}")
    assert rep1_data["potential_duplicate"] is True
    assert created_ids[1] in rep1_data["related_report_ids"]
    assert rep2_data["potential_duplicate"] is True
    assert created_ids[0] in rep2_data["related_report_ids"]
    print(">>> TEST G PASSED.")

    # TEST H: Different Report Types are NOT Flagged as Duplicates
    print("\n--- TEST H: DIFFERENT TYPES ARE NOT DUPLICATES ---")
    rep3_data = next(r for r in nearby_data if r["id"] == created_ids[2])
    print(f"Report 3 ({rep3_data['report_type']}) potential_duplicate: {rep3_data['potential_duplicate']}")
    assert rep3_data["potential_duplicate"] is False
    assert len(rep3_data["related_report_ids"]) == 0
    print(">>> TEST H PASSED.")

    # TEST I: GeoJSON Endpoint Validation
    print("\n--- TEST I: GEOJSON FEATURECOLLECTION & COORDINATE ORDER ---")
    resp_geojson = client.get(
        "/api/v1/field-reports/geojson",
        params={"latitude": 27.3314, "longitude": 88.6138, "radius_km": 5.0}
    )
    assert resp_geojson.status_code == 200
    gj = resp_geojson.json()
    assert gj["type"] == "FeatureCollection"
    assert len(gj["features"]) == 4
    for feat in gj["features"]:
        assert feat["type"] == "Feature"
        assert feat["geometry"]["type"] == "Point"
        coords = feat["geometry"]["coordinates"]
        assert len(coords) == 2
        # Verify [longitude, latitude] order
        lon, lat = coords[0], coords[1]
        assert 88.0 <= lon <= 97.4, f"Invalid longitude order: {lon}"
        assert 21.9 <= lat <= 29.5, f"Invalid latitude order: {lat}"
        props = feat["properties"]
        assert "id" in props
        assert "report_type" in props
        assert "severity" in props
        assert "status" in props
        assert "observation_status" in props
        assert "evidence_confidence" in props
    print("GeoJSON coordinate order verified: [longitude, latitude]")
    print(">>> TEST I PASSED.")

    # TEST J: Invalid Radius Validation
    print("\n--- TEST J: INVALID RADIUS BOUNDARY VALIDATION ---")
    resp_neg_rad = client.get("/api/v1/field-reports/nearby", params={"latitude": 27.3314, "longitude": 88.6138, "radius_km": -5.0})
    assert resp_neg_rad.status_code == 422
    resp_huge_rad = client.get("/api/v1/field-reports/nearby", params={"latitude": 27.3314, "longitude": 88.6138, "radius_km": 500.0})
    assert resp_huge_rad.status_code == 422
    print(">>> TEST J PASSED.")

    # TEST K: Outside NER Coordinates Rejected
    print("\n--- TEST K: OUTSIDE NER COORDINATES REJECTED ---")
    resp_out_nearby = client.get("/api/v1/field-reports/nearby", params={"latitude": 28.6139, "longitude": 77.2090, "radius_km": 5.0})
    assert resp_out_nearby.status_code == 400
    assert "North Eastern Region" in resp_out_nearby.json()["detail"]

    resp_out_summary = client.post("/api/v1/field-reports/intelligence-summary", json={"latitude": 28.6139, "longitude": 77.2090, "radius_km": 5.0})
    assert resp_out_summary.status_code == 400
    print(">>> TEST K PASSED.")

    # TEST L: Existing Field Report CRUD & Media Endpoints Still Work
    print("\n--- TEST L: EXISTING REPORT CRUD & MEDIA ENDPOINTS VERIFICATION ---")
    resp_get_single = client.get(f"/api/v1/field-reports/{created_ids[0]}")
    assert resp_get_single.status_code == 200
    assert len(resp_get_single.json().get("media", [])) == 1

    resp_media_list = client.get(f"/api/v1/field-reports/{created_ids[0]}/media")
    assert resp_media_list.status_code == 200
    assert len(resp_media_list.json()) == 1
    print(">>> TEST L PASSED.")

    # TEST M: Existing Project Smoke Tests
    print("\n--- TEST M: EXISTING PROJECT SMOKE TESTS ---")
    resp_health = client.get("/api/health")
    assert resp_health.status_code == 200
    print(f"Health: {resp_health.json()}")

    resp_ew = client.post("/api/v1/early-warning/analyze", json={"latitude": 27.3314, "longitude": 88.6138})
    assert resp_ew.status_code == 200
    print(f"Early Warning: Status={resp_ew.status_code}, Warning Level={resp_ew.json()['warning_level']}")

    resp_risk = client.post("/api/v1/risk/composite", json={"latitude": 27.3314, "longitude": 88.6138})
    assert resp_risk.status_code == 200
    print(f"Composite Risk: Status={resp_risk.status_code}, Index={resp_risk.json()['composite_risk_index']}")
    print(">>> TEST M PASSED.")

    print("\n" + "=" * 80)
    print("ALL SPATIAL INTELLIGENCE TESTS (TEST A - TEST M) PASSED SUCCESSFULLY!")
    print("=" * 80)

if __name__ == "__main__":
    run_spatial_tests()
