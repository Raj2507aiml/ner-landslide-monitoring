"""
E2E Frontend-Backend Integration Test for Field Intelligence Reporting - Phase 7 Checkpoint 16.4
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

def create_synthetic_image(format="JPEG", size=(100, 100), color="red") -> bytes:
    buf = io.BytesIO()
    img = Image.new("RGB", size, color=color)
    img.save(buf, format=format)
    buf.seek(0)
    return buf.read()

def run_integration_verification():
    Base.metadata.create_all(bind=engine)
    client = TestClient(app)
    
    print("=" * 80)
    print("PHASE 7 CHECKPOINT 16.4 - E2E FRONTEND INTEGRATION VERIFICATION")
    print("=" * 80)

    # 1. Clean test DB
    db = SessionLocal()
    db.query(FieldReportMedia).delete()
    db.query(FieldReport).delete()
    db.commit()
    db.close()

    # 2. Test Report Creation Flow (as performed by FieldReportModal)
    print("\n1. Testing Report Creation (POST /api/v1/field-reports)...")
    payload = {
        "report_type": "CRACK",
        "description": "Visible ground fissure along hillside retaining wall.",
        "latitude": 27.3314,
        "longitude": 88.6138,
        "reporter_type": "CITIZEN",
        "severity": "HIGH"
    }
    resp = client.post("/api/v1/field-reports", json=payload)
    assert resp.status_code == 201, f"Report creation failed: {resp.text}"
    report_data = resp.json()
    report_id = report_data["id"]
    print(f"[PASS] Report successfully created with ID: #{report_id}")
    assert report_data["status"] == "PENDING"
    assert report_data["report_type"] == "CRACK"
    assert report_data["severity"] == "HIGH"

    # 3. Test Multi-Media Upload Flow (as performed by FieldReportModal Step 5)
    print("\n2. Testing Multi-Image Evidence Upload (POST /api/v1/field-reports/{id}/media)...")
    img_jpeg = create_synthetic_image(format="JPEG", color="blue")
    img_png = create_synthetic_image(format="PNG", color="green")

    # Upload first image
    resp_img1 = client.post(
        f"/api/v1/field-reports/{report_id}/media",
        files={"file": ("crack_evidence_1.jpg", io.BytesIO(img_jpeg), "image/jpeg")}
    )
    assert resp_img1.status_code == 201, f"Image 1 upload failed: {resp_img1.text}"
    media1_data = resp_img1.json()
    print(f"[PASS] Uploaded evidence 1 (JPEG): ID #{media1_data['id']}, URL={media1_data['media_url']}")

    # Upload second image
    resp_img2 = client.post(
        f"/api/v1/field-reports/{report_id}/media",
        files={"file": ("crack_evidence_2.png", io.BytesIO(img_png), "image/png")}
    )
    assert resp_img2.status_code == 201, f"Image 2 upload failed: {resp_img2.text}"
    media2_data = resp_img2.json()
    print(f"[PASS] Uploaded evidence 2 (PNG): ID #{media2_data['id']}, URL={media2_data['media_url']}")

    # 4. Verify FieldIntelligenceCard Data Sources
    print("\n3. Testing Dashboard Field Intelligence Query (GET /nearby & POST /intelligence-summary)...")
    resp_nearby = client.get(
        "/api/v1/field-reports/nearby",
        params={"latitude": 27.3314, "longitude": 88.6138, "radius_km": 5.0}
    )
    assert resp_nearby.status_code == 200
    nearby_list = resp_nearby.json()
    assert len(nearby_list) == 1
    assert nearby_list[0]["id"] == report_id
    assert nearby_list[0]["media_count"] == 2
    assert nearby_list[0]["observation_status"] == "UNVERIFIED_OBSERVATION"
    print(f"[PASS] Nearby reports returned correctly: {len(nearby_list)} report(s) found with {nearby_list[0]['media_count']} media files.")

    resp_summary = client.post(
        "/api/v1/field-reports/intelligence-summary",
        json={"latitude": 27.3314, "longitude": 88.6138, "radius_km": 5.0}
    )
    assert resp_summary.status_code == 200
    summary_data = resp_summary.json()
    assert summary_data["total_reports"] == 1
    assert summary_data["unverified_observations"] == 1
    assert summary_data["evidence_statistics"]["reports_with_media"] == 1
    print(f"[PASS] Intelligence summary returned: Total={summary_data['total_reports']}, With Media={summary_data['evidence_statistics']['reports_with_media']}")

    # 5. Verify Error Rejection Handling
    print("\n4. Testing Error Rejection Validation...")
    # Outside NER
    resp_out = client.post("/api/v1/field-reports", json={**payload, "latitude": 28.6139, "longitude": 77.2090})
    assert resp_out.status_code == 400
    print("[PASS] Outside NER coordinates rejected with HTTP 400")

    # Invalid File Type
    fake_txt = b"not an image"
    resp_bad_file = client.post(
        f"/api/v1/field-reports/{report_id}/media",
        files={"file": ("notes.txt", io.BytesIO(fake_txt), "text/plain")}
    )
    assert resp_bad_file.status_code == 400
    print("[PASS] Non-image file upload rejected with HTTP 400")

    # 6. Verify System Smoke Tests
    print("\n5. Testing System Health & Core Pipeline Stability...")
    resp_health = client.get("/api/health")
    assert resp_health.status_code == 200
    resp_ew = client.post("/api/v1/early-warning/analyze", json={"latitude": 27.3314, "longitude": 88.6138})
    assert resp_ew.status_code == 200
    print("[PASS] Core early warning and backend routes verified healthy.")

    print("\n" + "=" * 80)
    print("ALL E2E FRONTEND INTEGRATION CHECKS PASSED SUCCESSFULLY!")
    print("=" * 80)

if __name__ == "__main__":
    run_integration_verification()
