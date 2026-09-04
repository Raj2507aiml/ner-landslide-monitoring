"""
Verify Spatial Queries — Phase 2.6C Checkpoint 3C

Performs rigorous automated tests against the spatial query service:
1. Dense location test (Meghalaya coordinate: 25.23908, 90.63944)
2. Small radius vs. large radius validation
3. Graceful empty result handling
4. Error checking on invalid inputs
5. Haversine distance math sanity checks
"""

import os
import sys

# ── Inject backend directory into sys.path ──────────────────────────────────
SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.abspath(os.path.join(SCRIPTS_DIR, ".."))
sys.path.insert(0, BACKEND_DIR)

from app.database.session import SessionLocal
from app.services.spatial_query_service import (
    find_nearby_gsi_incidents,
    find_nearby_nasa_events,
    get_historical_landslide_context,
    haversine_distance
)

# Test Coordinate: Meghalaya landslide dense coordinate
TEST_LAT = 25.23908
TEST_LON = 90.63944

def run_tests():
    print("=== Starting Spatial Query Engine Verification Tests ===")
    db = SessionLocal()
    
    try:
        # ──────────────────────────────────────────────────────────────────
        # TEST 1 — Known landslide-dense location
        # ──────────────────────────────────────────────────────────────────
        print("\n[TEST 1] Querying known landslide-dense location (Meghalaya)...")
        gsi_incidents = find_nearby_gsi_incidents(db, TEST_LAT, TEST_LON, radius_km=5.0)
        nasa_events = find_nearby_nasa_events(db, TEST_LAT, TEST_LON, radius_km=10.0)
        
        print(f"  Found {len(gsi_incidents)} GSI incidents within 5.0 km.")
        print(f"  Found {len(nasa_events)} NASA events within 10.0 km.")
        
        # Verify sorting and distances
        if gsi_incidents:
            prev_dist = -1.0
            for idx, inc in enumerate(gsi_incidents):
                dist = inc["distance_km"]
                # 1. Non-negative
                assert dist >= 0, f"Distance {dist} cannot be negative"
                # 2. Within radius
                assert dist <= 5.0, f"Distance {dist} exceeds search radius 5.0"
                # 3. Sorted
                assert dist >= prev_dist, f"Incidents not sorted correctly at index {idx}: {dist} < {prev_dist}"
                prev_dist = dist
            print("  [OK] GSI distance range, sorting, and boundaries verified.")
        else:
            print("  ❌ GSI dense location returned 0 incidents. Verification failed.")
            sys.exit(1)
            
        if nasa_events:
            prev_dist = -1.0
            for idx, ev in enumerate(nasa_events):
                dist = ev["distance_km"]
                assert dist >= 0
                assert dist <= 10.0
                assert dist >= prev_dist
                prev_dist = dist
            print("  [OK] NASA distance range, sorting, and boundaries verified.")
            
        # ──────────────────────────────────────────────────────────────────
        # TEST 2 & 3 — Small radius vs. Larger radius
        # ──────────────────────────────────────────────────────────────────
        print("\n[TEST 2 & 3] Bounding radius comparison tests...")
        gsi_small = find_nearby_gsi_incidents(db, TEST_LAT, TEST_LON, radius_km=1.0)
        gsi_large = find_nearby_gsi_incidents(db, TEST_LAT, TEST_LON, radius_km=30.0)
        
        print(f"  GSI incidents: 1.0 km radius = {len(gsi_small)} | 30.0 km radius = {len(gsi_large)}")
        assert len(gsi_large) >= len(gsi_small), "Error: Larger search radius returned fewer results!"
        print("  [OK] Radius scaling verification passed.")
        
        # ──────────────────────────────────────────────────────────────────
        # TEST 4 — Empty result location
        # ──────────────────────────────────────────────────────────────────
        print("\n[TEST 4] Graceful empty result handling (Indian Ocean: 0.0, 80.0)...")
        empty_context = get_historical_landslide_context(db, latitude=0.0, longitude=80.0, radius_km=10.0)
        
        # Verify structure and values
        assert empty_context["gsi_summary"]["total_nearby_incidents"] == 0
        assert empty_context["gsi_summary"]["nearest_incident_distance_km"] is None
        assert empty_context["nasa_summary"]["total_nearby_events"] == 0
        assert empty_context["nasa_summary"]["nearest_event_distance_km"] is None
        assert empty_context["combined_summary"]["total_historical_observations"] == 0
        assert empty_context["combined_summary"]["nearest_historical_observation_km"] is None
        print("  [OK] Graceful empty result structures verified.")
        
        # ──────────────────────────────────────────────────────────────────
        # TEST 5 — Invalid inputs
        # ──────────────────────────────────────────────────────────────────
        print("\n[TEST 5] Input validation error checking...")
        
        # Invalid Lat
        try:
            find_nearby_gsi_incidents(db, 95.0, TEST_LON, 5.0)
            assert False, "Should raise ValueError for Lat > 90"
        except ValueError as e:
            print(f"  [OK] Lat > 90 caught: {e}")
            
        # Invalid Lon
        try:
            find_nearby_gsi_incidents(db, TEST_LAT, -190.0, 5.0)
            assert False, "Should raise ValueError for Lon < -180"
        except ValueError as e:
            print(f"  [OK] Lon < -180 caught: {e}")
            
        # Zero Radius
        try:
            find_nearby_gsi_incidents(db, TEST_LAT, TEST_LON, 0.0)
            assert False, "Should raise ValueError for radius = 0"
        except ValueError as e:
            print(f"  [OK] Radius = 0 caught: {e}")
            
        # Negative Radius
        try:
            find_nearby_gsi_incidents(db, TEST_LAT, TEST_LON, -5.0)
            assert False, "Should raise ValueError for radius < 0"
        except ValueError as e:
            print(f"  [OK] Radius < 0 caught: {e}")
            
        # Radius > Maximum
        try:
            find_nearby_gsi_incidents(db, TEST_LAT, TEST_LON, 120.0)
            assert False, "Should raise ValueError for radius > 100 km"
        except ValueError as e:
            print(f"  [OK] Radius > 100 km caught: {e}")
            
        # ──────────────────────────────────────────────────────────────────
        # TEST 6 — Haversine sanity check
        # ──────────────────────────────────────────────────────────────────
        print("\n[TEST 6] Haversine distance formula mathematical sanity check...")
        
        # Distance to same point should be 0
        dist_same = haversine_distance(TEST_LAT, TEST_LON, TEST_LAT, TEST_LON)
        print(f"  Distance to self: {dist_same} km")
        assert abs(dist_same) < 0.0001
        
        # Distance between known points (Guwahati to Shillong)
        # Guwahati: Lat 26.1856, Lon 91.7498
        # Shillong: Lat 25.5788, Lon 91.8933
        # Direct distance: ~68.3 km
        dist_cities = haversine_distance(26.1856, 91.7498, 25.5788, 91.8933)
        print(f"  Distance Guwahati to Shillong: {dist_cities:.2f} km")
        assert 67.5 <= dist_cities <= 69.5, f"Haversine calculation mismatch: {dist_cities}"
        print("  [OK] Haversine math verification passed.")
        
        # ──────────────────────────────────────────────────────────────────
        # PRINT COMBINED CONTEXT FOR DENSE COORDINATE (Verification printout)
        # ──────────────────────────────────────────────────────────────────
        print("\n[CONTEXT AUDIT] Printing combined context structure for Meghalaya coordinate:")
        context = get_historical_landslide_context(db, TEST_LAT, TEST_LON, radius_km=10.0)
        import json
        print(json.dumps(context, indent=2))
        
        print("\n=== All Tests Passed Successfully ===")
        
    finally:
        db.close()

if __name__ == "__main__":
    run_tests()
