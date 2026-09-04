"""
Phase 7 Checkpoint 16.2 Test Suite - Media Evidence Upload & Geolocation
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

def create_synthetic_image(format="JPEG", size=(200, 150), color="red", with_exif=False) -> bytes:
    """Creates an in-memory valid image buffer with optional GPS EXIF metadata."""
    buf = io.BytesIO()
    img = Image.new("RGB", size, color=color)
    exif = None
    if with_exif and format == "JPEG":
        exif = img.getexif()
        gps_ifd = exif.get_ifd(34853)
        gps_ifd[1] = "N"
        gps_ifd[2] = (27.0, 19.0, 53.04) # 27.3314 N
        gps_ifd[3] = "E"
        gps_ifd[4] = (88.0, 36.0, 49.68) # 88.6138 E
        gps_ifd[29] = "2026:09:01"
        gps_ifd[7] = (14, 30, 0)
        img.save(buf, format=format, exif=exif)
    else:
        img.save(buf, format=format)
    buf.seek(0)
    return buf.read()

def run_media_tests():
    Base.metadata.create_all(bind=engine)
    client = TestClient(app)
    
    print("=" * 80)
    print("PHASE 7 CHECKPOINT 16.2 - FIELD INTELLIGENCE MEDIA EVIDENCE TESTS")
    print("=" * 80)

    # Clean up test database records
    db = SessionLocal()
    db.query(FieldReportMedia).delete()
    db.query(FieldReport).delete()
    db.commit()
    db.close()

    # Step 1: Create a base field report
    report_payload = {
        "report_type": "CRACK",
        "description": "Visible ground fissure along road embankment.",
        "latitude": 27.3314,
        "longitude": 88.6138,
        "reporter_type": "FIELD_OFFICIAL",
        "severity": "HIGH"
    }
    resp_report = client.post("/api/v1/field-reports", json=report_payload)
    assert resp_report.status_code == 201
    report_id = resp_report.json()["id"]
    print(f"Created Base Field Report ID: {report_id}")

    # TEST A: Upload Valid JPEG Image
    print("\n--- TEST A: UPLOAD VALID JPEG IMAGE ---")
    jpeg_bytes = create_synthetic_image(format="JPEG", size=(320, 240), color="blue")
    files = {"file": ("crack_evidence.jpg", io.BytesIO(jpeg_bytes), "image/jpeg")}
    resp_a = client.post(f"/api/v1/field-reports/{report_id}/media", files=files)
    print(f"Status Code: {resp_a.status_code}")
    assert resp_a.status_code == 201, f"Expected 201, got {resp_a.status_code}"
    media_a = resp_a.json()
    print("Uploaded JPEG Metadata:", json.dumps(media_a, indent=2))
    assert media_a["id"] is not None
    assert media_a["report_id"] == report_id
    assert media_a["mime_type"] == "image/jpeg"
    assert media_a["width"] == 320
    assert media_a["height"] == 240
    assert media_a["media_url"].startswith(f"/media/field_reports/report_{report_id}/")
    media_a_id = media_a["id"]
    
    # Verify static serving endpoint
    resp_static = client.get(media_a["media_url"])
    print(f"Static Serving Status: {resp_static.status_code}")
    assert resp_static.status_code == 200
    assert len(resp_static.content) == len(jpeg_bytes)
    print(">>> TEST A PASSED.")

    # TEST B: Upload Valid PNG Image
    print("\n--- TEST B: UPLOAD VALID PNG IMAGE ---")
    png_bytes = create_synthetic_image(format="PNG", size=(400, 300), color="green")
    files = {"file": ("slope_diagram.png", io.BytesIO(png_bytes), "image/png")}
    resp_b = client.post(f"/api/v1/field-reports/{report_id}/media", files=files)
    print(f"Status Code: {resp_b.status_code}")
    assert resp_b.status_code == 201
    media_b = resp_b.json()
    assert media_b["mime_type"] == "image/png"
    assert media_b["width"] == 400
    assert media_b["height"] == 300
    print(">>> TEST B PASSED.")

    # TEST C: Upload Invalid Text File Renamed .jpg
    print("\n--- TEST C: UPLOAD FAKE JPEG (TEXT FILE RENAMED .JPG) ---")
    fake_jpg = b"This is plain text pretending to be a JPG file header malware.exe"
    files = {"file": ("malware.jpg", io.BytesIO(fake_jpg), "image/jpeg")}
    resp_c = client.post(f"/api/v1/field-reports/{report_id}/media", files=files)
    print(f"Status Code: {resp_c.status_code}")
    assert resp_c.status_code == 400
    print("Rejected fake JPG response:", resp_c.json())
    print(">>> TEST C PASSED.")

    # TEST D: Upload Corrupted Image Bytes
    print("\n--- TEST D: UPLOAD CORRUPTED IMAGE BYTES ---")
    corrupt_bytes = b"\xFF\xD8\xFF\xE0" + b"\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00" + b"CORRUPTED_GARBAGE_PAYLOAD"
    files = {"file": ("corrupt.jpg", io.BytesIO(corrupt_bytes), "image/jpeg")}
    resp_d = client.post(f"/api/v1/field-reports/{report_id}/media", files=files)
    print(f"Status Code: {resp_d.status_code}")
    assert resp_d.status_code == 400
    print("Rejected corrupted image response:", resp_d.json())
    print(">>> TEST D PASSED.")

    # TEST E: Upload to Nonexistent Report ID
    print("\n--- TEST E: UPLOAD TO NONEXISTENT REPORT ID ---")
    files = {"file": ("valid.jpg", io.BytesIO(jpeg_bytes), "image/jpeg")}
    resp_e = client.post("/api/v1/field-reports/999999/media", files=files)
    print(f"Status Code: {resp_e.status_code}")
    assert resp_e.status_code == 404
    print(">>> TEST E PASSED.")

    # TEST F: Retrieve Report Media
    print("\n--- TEST F: RETRIEVE ALL MEDIA FOR REPORT ---")
    resp_f = client.get(f"/api/v1/field-reports/{report_id}/media")
    print(f"Status Code: {resp_f.status_code}")
    assert resp_f.status_code == 200
    media_list = resp_f.json()
    print(f"Attached media items count: {len(media_list)}")
    assert len(media_list) == 2

    # Also verify GET /api/v1/field-reports/{report_id} returns detailed report with media array
    resp_detail = client.get(f"/api/v1/field-reports/{report_id}")
    assert resp_detail.status_code == 200
    detail_data = resp_detail.json()
    print(f"Detail report media array length: {len(detail_data.get('media', []))}")
    assert len(detail_data.get("media", [])) == 2
    print(">>> TEST F PASSED.")

    # TEST G: Verify EXIF Absence vs Presence
    print("\n--- TEST G: VERIFY EXIF ABSENCE & EXIF GPS EXTRACTION ---")
    # Image A had no EXIF:
    assert media_a["exif_latitude"] is None
    assert media_a["exif_longitude"] is None
    assert media_a["exif_timestamp"] is None
    print("EXIF absence safely resolved to null without errors.")

    # Upload image with EXIF GPS:
    exif_jpeg_bytes = create_synthetic_image(format="JPEG", size=(300, 200), color="yellow", with_exif=True)
    files = {"file": ("geotagged_crack.jpg", io.BytesIO(exif_jpeg_bytes), "image/jpeg")}
    resp_exif = client.post(f"/api/v1/field-reports/{report_id}/media", files=files)
    assert resp_exif.status_code == 201
    media_exif = resp_exif.json()
    print("Extracted EXIF Latitude:", media_exif["exif_latitude"])
    print("Extracted EXIF Longitude:", media_exif["exif_longitude"])
    print("Extracted EXIF Timestamp:", media_exif["exif_timestamp"])
    assert media_exif["exif_latitude"] is not None
    assert abs(media_exif["exif_latitude"] - 27.3314) < 0.001
    assert abs(media_exif["exif_longitude"] - 88.6138) < 0.001
    print(">>> TEST G PASSED.")

    # TEST H: Delete Media Endpoint
    print("\n--- TEST H: DELETE MEDIA ENDPOINT ---")
    resp_h = client.delete(f"/api/v1/field-reports/{report_id}/media/{media_a_id}")
    print(f"Status Code: {resp_h.status_code}")
    assert resp_h.status_code == 200
    print("Delete response:", resp_h.json())

    # Verify media count is now 2 (b + exif)
    resp_after_del = client.get(f"/api/v1/field-reports/{report_id}/media")
    assert len(resp_after_del.json()) == 2
    print(">>> TEST H PASSED.")

    # TEST I: Verify Existing Field Report Endpoints Still Work
    print("\n--- TEST I: VERIFY FIELD REPORT BASELINE ENDPOINTS ---")
    resp_i_get = client.get(f"/api/v1/field-reports/{report_id}")
    assert resp_i_get.status_code == 200
    resp_i_patch = client.patch(f"/api/v1/field-reports/{report_id}/status", json={"status": "UNDER_REVIEW"})
    assert resp_i_patch.status_code == 200
    assert resp_i_patch.json()["status"] == "UNDER_REVIEW"
    print(">>> TEST I PASSED.")

    # TEST J: Existing Project Smoke Test
    print("\n--- TEST J: EXISTING PROJECT SMOKE TEST ---")
    resp_health = client.get("/api/health")
    assert resp_health.status_code == 200
    print(f"Health API: {resp_health.json()}")

    resp_ew = client.post("/api/v1/early-warning/analyze", json={"latitude": 27.3314, "longitude": 88.6138})
    assert resp_ew.status_code == 200
    print(f"Early Warning API: Status=200, Warning Level={resp_ew.json()['warning_level']}")

    resp_risk = client.post("/api/v1/risk/composite", json={"latitude": 27.3314, "longitude": 88.6138})
    assert resp_risk.status_code == 200
    print(f"Composite Risk API: Status=200, Risk Index={resp_risk.json()['composite_risk_index']}")
    print(">>> TEST J PASSED.")

    print("\n" + "=" * 80)
    print("ALL MEDIA EVIDENCE TESTS (TEST A - TEST J) PASSED SUCCESSFULLY!")
    print("=" * 80)

if __name__ == "__main__":
    run_media_tests()
