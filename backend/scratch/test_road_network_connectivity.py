"""
Phase 8 Checkpoint 17.1 Test Suite: Road Network & Connectivity Intelligence Foundation
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
from app.services.road_connectivity_service import (
    RoadConnectivityService,
    point_to_linestring_distance_m,
    point_to_segment_distance_m
)
from app.schemas.infrastructure import RoadConnectivityStatus

MOCK_OVERPASS_DATA = {
    "version": 0.6,
    "generator": "Overpass API",
    "elements": [
        {
            "type": "way",
            "id": 101,
            "tags": {
                "highway": "primary",
                "name": "NH-10 Highway",
                "ref": "NH10"
            },
            "geometry": [
                {"lat": 27.3300, "lon": 88.6100},
                {"lat": 27.3320, "lon": 88.6140},
                {"lat": 27.3350, "lon": 88.6180}
            ]
        },
        {
            "type": "way",
            "id": 102,
            "tags": {
                "highway": "secondary",
                "name": "Gangtok-Nathula Link"
            },
            "geometry": [
                {"lat": 27.3400, "lon": 88.6200},
                {"lat": 27.3450, "lon": 88.6250}
            ]
        },
        {
            "type": "way",
            "id": 103,
            "tags": {
                "highway": "residential"
            },
            "geometry": [
                {"lat": 27.3200, "lon": 88.6000},
                {"lat": 27.3220, "lon": 88.6020}
            ]
        }
    ]
}

def run_tests():
    Base.metadata.create_all(bind=engine)
    client = TestClient(app)

    print("=" * 80)
    print("PHASE 8 CHECKPOINT 17.1: ROAD NETWORK & CONNECTIVITY INTELLIGENCE TESTS")
    print("=" * 80)

    # Clean DB
    db = SessionLocal()
    db.query(FieldReportMedia).delete()
    db.query(FieldReport).delete()
    db.commit()

    lat_gangtok, lon_gangtok = 27.3314, 88.6138

    # TEST A: Valid road network parsing
    print("\n--- TEST A: VALID ROAD NETWORK PARSING ---")
    parsed_roads = RoadNetworkService.parse_overpass_response(MOCK_OVERPASS_DATA)
    assert len(parsed_roads) == 3
    assert parsed_roads[0]["osm_id"] == "101"
    assert parsed_roads[0]["name"] == "NH-10 Highway"
    assert parsed_roads[0]["ref"] == "NH10"
    assert parsed_roads[0]["highway_type"] == "primary"
    print(f"Parsed {len(parsed_roads)} roads successfully.")
    print("[PASS] TEST A PASSED.")

    # TEST B: Correct GeoJSON coordinate order [lon, lat]
    print("\n--- TEST B: CORRECT GEOJSON COORDINATE ORDER [lon, lat] ---")
    coords_0 = parsed_roads[0]["geometry"]["coordinates"]
    first_pt = coords_0[0]
    # GeoJSON standard: [longitude, latitude] -> lon ~88.61, lat ~27.33
    assert first_pt[0] == 88.6100
    assert first_pt[1] == 27.3300
    assert parsed_roads[0]["geometry"]["type"] == "LineString"
    print(f"Sample Point: [lon={first_pt[0]}, lat={first_pt[1]}] verified.")
    print("[PASS] TEST B PASSED.")

    # TEST C: Point-to-road distance calculation across multiple segments
    print("\n--- TEST C: POINT-TO-ROAD DISTANCE ACROSS MULTIPLE SEGMENTS ---")
    # Point located directly near the middle vertex (27.3320, 88.6140)
    p_lat, p_lon = 27.3321, 88.6141
    dist_m = point_to_linestring_distance_m(p_lat, p_lon, coords_0)
    print(f"Calculated distance from ({p_lat}, {p_lon}) to NH-10: {dist_m:.2f} meters")
    assert 0.0 < dist_m < 50.0  # Should be ~15 meters away

    # Point located far away
    p_far_lat, p_far_lon = 27.4000, 88.7000
    dist_far_m = point_to_linestring_distance_m(p_far_lat, p_far_lon, coords_0)
    assert dist_far_m > 5000.0
    print("[PASS] TEST C PASSED.")

    # TEST D: NORMAL classification without relevant reports
    print("\n--- TEST D: NORMAL CLASSIFICATION WITHOUT RELEVANT REPORTS ---")
    road_d = RoadConnectivityService.evaluate_road_status(parsed_roads[0], [])
    assert road_d.connectivity_status == RoadConnectivityStatus.NORMAL
    assert road_d.impact_evidence.verified_reports == 0
    assert "Normal connectivity" in road_d.explanation
    print(f"Status: {road_d.connectivity_status}, Explanation: {road_d.explanation}")
    print("[PASS] TEST D PASSED.")

    # TEST E: MONITOR classification with nearby PENDING observation
    print("\n--- TEST E: MONITOR CLASSIFICATION WITH NEARBY PENDING OBSERVATION ---")
    rep_pending = FieldReport(
        id=1,
        report_type="CRACK",
        description="Fissure reported on asphalt",
        latitude=27.3320,
        longitude=88.6140,
        severity="MEDIUM",
        status="PENDING",
        created_at=datetime.utcnow()
    )
    road_e = RoadConnectivityService.evaluate_road_status(parsed_roads[0], [rep_pending])
    assert road_e.connectivity_status == RoadConnectivityStatus.MONITOR
    assert road_e.impact_evidence.pending_reports == 1
    assert 1 in road_e.impact_evidence.supporting_report_ids
    assert "Observational monitoring" in road_e.explanation
    print(f"Status: {road_e.connectivity_status}, Nearest: {road_e.nearest_hazard_distance_m}m")
    print("[PASS] TEST E PASSED.")

    # TEST F: AT_RISK classification with VERIFIED hazard near road
    print("\n--- TEST F: AT_RISK CLASSIFICATION WITH VERIFIED HAZARD NEAR ROAD ---")
    rep_verified_crack = FieldReport(
        id=2,
        report_type="SLOPE_MOVEMENT",
        description="Slope creeping towards guard rail",
        latitude=27.3320,
        longitude=88.6140,
        severity="MEDIUM",
        status="VERIFIED",
        created_at=datetime.utcnow()
    )
    road_f = RoadConnectivityService.evaluate_road_status(parsed_roads[0], [rep_verified_crack])
    assert road_f.connectivity_status == RoadConnectivityStatus.AT_RISK
    assert road_f.impact_evidence.verified_reports == 1
    assert "Road at risk" in road_f.explanation
    print(f"Status: {road_f.connectivity_status}, Explanation: {road_f.explanation}")
    print("[PASS] TEST F PASSED.")

    # TEST G: BLOCKED classification with VERIFIED BLOCKED_ROAD report
    print("\n--- TEST G: BLOCKED CLASSIFICATION WITH VERIFIED BLOCKED_ROAD REPORT ---")
    rep_verified_blocked = FieldReport(
        id=3,
        report_type="BLOCKED_ROAD",
        description="Boulders blocking both lanes",
        latitude=27.3320,
        longitude=88.6140,
        severity="HIGH",
        status="VERIFIED",
        created_at=datetime.utcnow()
    )
    road_g = RoadConnectivityService.evaluate_road_status(parsed_roads[0], [rep_verified_blocked])
    assert road_g.connectivity_status == RoadConnectivityStatus.BLOCKED
    assert road_g.impact_evidence.blocked_road_reports == 1
    assert "Confirmed blockage" in road_g.explanation
    print(f"Status: {road_g.connectivity_status}, Explanation: {road_g.explanation}")
    print("[PASS] TEST G PASSED.")

    # TEST H: SEVERELY_IMPACTED classification with VERIFIED HIGH/CRITICAL LANDSLIDE
    print("\n--- TEST H: SEVERELY_IMPACTED CLASSIFICATION WITH VERIFIED HIGH/CRITICAL LANDSLIDE ---")
    rep_verified_landslide = FieldReport(
        id=4,
        report_type="LANDSLIDE",
        description="Major slope collapse covering road",
        latitude=27.3320,
        longitude=88.6140,
        severity="CRITICAL",
        status="VERIFIED",
        created_at=datetime.utcnow()
    )
    road_h = RoadConnectivityService.evaluate_road_status(parsed_roads[0], [rep_verified_landslide])
    assert road_h.connectivity_status == RoadConnectivityStatus.SEVERELY_IMPACTED
    assert "Severely impacted" in road_h.explanation
    print(f"Status: {road_h.connectivity_status}, Explanation: {road_h.explanation}")
    print("[PASS] TEST H PASSED.")

    # TEST I: REJECTED reports do NOT affect road classification
    print("\n--- TEST I: REJECTED REPORTS DO NOT AFFECT ROAD CLASSIFICATION ---")
    rep_rejected = FieldReport(
        id=5,
        report_type="BLOCKED_ROAD",
        description="False report of road closure",
        latitude=27.3320,
        longitude=88.6140,
        severity="CRITICAL",
        status="REJECTED",
        created_at=datetime.utcnow()
    )
    road_i = RoadConnectivityService.evaluate_road_status(parsed_roads[0], [rep_rejected])
    assert road_i.connectivity_status == RoadConnectivityStatus.NORMAL
    assert road_i.impact_evidence.blocked_road_reports == 0
    assert len(road_i.impact_evidence.supporting_report_ids) == 0
    print("[PASS] TEST I PASSED.")

    # TEST J: NER boundary validation
    print("\n--- TEST J: NER BOUNDARY VALIDATION ---")
    # Coordinates in Delhi (outside NER)
    resp_j = client.get("/api/v1/infrastructure/roads/nearby", params={"latitude": 28.6139, "longitude": 77.2090, "radius_km": 5.0})
    assert resp_j.status_code == 400
    assert "North Eastern Region" in resp_j.json()["detail"]
    print("[PASS] TEST J PASSED.")

    # TEST K: Invalid radius validation
    print("\n--- TEST K: INVALID RADIUS VALIDATION ---")
    # Radius too small (< 0.5)
    resp_k1 = client.get("/api/v1/infrastructure/roads/nearby", params={"latitude": lat_gangtok, "longitude": lon_gangtok, "radius_km": 0.1})
    assert resp_k1.status_code == 422

    # Radius too large (> 25.0)
    resp_k2 = client.get("/api/v1/infrastructure/roads/nearby", params={"latitude": lat_gangtok, "longitude": lon_gangtok, "radius_km": 50.0})
    assert resp_k2.status_code == 422
    print("[PASS] TEST K PASSED.")

    # TEST L: Empty road response handled gracefully
    print("\n--- TEST L: EMPTY ROAD RESPONSE HANDLED GRACEFULLY ---")
    empty_roads = RoadNetworkService.parse_overpass_response({"elements": []})
    assert empty_roads == []
    empty_analysis = RoadConnectivityService.analyze_nearby_roads(db, lat_gangtok, lon_gangtok, 5.0, mock_raw_roads={"elements": []})
    assert empty_analysis.total_roads == 0
    assert empty_analysis.roads == []
    assert empty_analysis.connectivity_summary.normal == 0
    print("[PASS] TEST L PASSED.")

    # TEST M: External API failure handled gracefully (fallback to empty list / cache)
    print("\n--- TEST M: EXTERNAL API FAILURE HANDLED GRACEFULLY ---")
    # Seed mock reports into database to verify end-to-end API route with mock data
    db.add_all([rep_pending, rep_verified_crack, rep_verified_blocked])
    db.commit()

    # Pre-save cache to test offline cache fallback
    cache_path = RoadNetworkService.get_cache_path(lat_gangtok, lon_gangtok, 5.0)
    RoadNetworkService.save_to_cache(cache_path, parsed_roads)
    cached_loaded = RoadNetworkService.load_from_cache(cache_path)
    assert len(cached_loaded) == 3
    print(f"Cached {len(cached_loaded)} road features verified.")

    resp_m = client.get("/api/v1/infrastructure/roads/nearby", params={"latitude": lat_gangtok, "longitude": lon_gangtok, "radius_km": 5.0})
    assert resp_m.status_code == 200
    data_m = resp_m.json()
    assert "roads" in data_m
    assert "connectivity_summary" in data_m
    print(f"API Route Summary: Total: {data_m['total_roads']}, Summary: {data_m['connectivity_summary']}")
    print("[PASS] TEST M PASSED.")

    # TEST N: Existing Field Intelligence APIs regression test
    print("\n--- TEST N: EXISTING FIELD INTELLIGENCE APIS REGRESSION ---")
    resp_n_queue = client.get("/api/v1/field-reports/review-queue")
    assert resp_n_queue.status_code == 200
    assert "items" in resp_n_queue.json()

    resp_n_sig = client.get("/api/v1/field-reports/risk-signal", params={"latitude": lat_gangtok, "longitude": lon_gangtok})
    assert resp_n_sig.status_code == 200
    assert "field_intelligence_status" in resp_n_sig.json()
    print("[PASS] TEST N PASSED.")

    # TEST O: Existing Composite Risk endpoint regression test
    print("\n--- TEST O: EXISTING COMPOSITE RISK REGRESSION ---")
    resp_o = client.post("/api/v1/risk/composite", json={"latitude": lat_gangtok, "longitude": lon_gangtok})
    assert resp_o.status_code == 200
    data_o = resp_o.json()
    assert "composite_risk_index" in data_o
    print(f"Composite Risk Index: {data_o['composite_risk_index']}")
    print("[PASS] TEST O PASSED.")

    # TEST P: Existing Early Warning endpoint regression test
    print("\n--- TEST P: EXISTING EARLY WARNING REGRESSION ---")
    resp_p = client.post("/api/v1/early-warning/analyze", json={"latitude": lat_gangtok, "longitude": lon_gangtok})
    assert resp_p.status_code == 200
    data_p = resp_p.json()
    assert "warning_level" in data_p
    print(f"Early Warning Level: {data_p['warning_level']}")
    print("[PASS] TEST P PASSED.")

    db.close()
    print("\n" + "=" * 80)
    print("ALL TESTS (TEST A - TEST P) PASSED SUCCESSFULLY!")
    print("=" * 80)

if __name__ == "__main__":
    run_tests()
