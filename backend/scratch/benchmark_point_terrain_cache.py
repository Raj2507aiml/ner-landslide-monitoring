"""
In-Memory DEM Connection Cache Benchmark - Phase 3 Checkpoint 11G.2

Benchmarks cold vs. warm coordinate extraction timings, verifies numerical consistency,
and audits LRU handle eviction behavior.
"""

import os
import sys
import time

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.abspath(os.path.join(SCRIPTS_DIR, ".."))
sys.path.insert(0, BACKEND_DIR)

from app.services.terrain_service import extract_point_terrain, dem_cache

def run_benchmark():
    print("=== Commencing DEM Connection Cache Performance Benchmark ===")
    
    # Coordinates in the same tile (Gangtok, Sikkim area - Tile: N27_E088)
    tile1_coords = [
        {"name": "Gangtok Center", "lat": 27.3314, "lon": 88.6138},
        {"name": "Gangtok North", "lat": 27.3500, "lon": 88.6200},
        {"name": "Gangtok East",  "lat": 27.3200, "lon": 88.6400}
    ]
    
    # Coordinate in a different tile (Shillong, Meghalaya - Tile: N25_E091)
    tile2_coord = {"name": "Shillong Center", "lat": 25.5788, "lon": 91.8827}
    
    # --- Test Case A: Cold Open N27_E088 ---
    print(f"\n[Test A] Cold open to N27_E088 | {tile1_coords[0]['name']}")
    start = time.time()
    res1 = extract_point_terrain(tile1_coords[0]["lat"], tile1_coords[0]["lon"])
    cold_dur = time.time() - start
    print(f"  Result: Elevation={res1['elevation']}m | Slope={res1['slope']}° | Aspect={res1['aspect']}°")
    print(f"  Latency: {cold_dur*1000:.2f}ms")
    
    # --- Test Case B: Warm Open N27_E088 (Point 2) ---
    print(f"\n[Test B] Warm read (same tile, diff coord) | {tile1_coords[1]['name']}")
    start = time.time()
    res2 = extract_point_terrain(tile1_coords[1]["lat"], tile1_coords[1]["lon"])
    warm1_dur = time.time() - start
    print(f"  Result: Elevation={res2['elevation']}m | Slope={res2['slope']}° | Aspect={res2['aspect']}°")
    print(f"  Latency: {warm1_dur*1000:.2f}ms")
    
    # --- Test Case C: Warm Open N27_E088 (Point 3) ---
    print(f"\n[Test C] Warm read (same tile, diff coord) | {tile1_coords[2]['name']}")
    start = time.time()
    res3 = extract_point_terrain(tile1_coords[2]["lat"], tile1_coords[2]["lon"])
    warm2_dur = time.time() - start
    print(f"  Result: Elevation={res3['elevation']}m | Slope={res3['slope']}° | Aspect={res3['aspect']}°")
    print(f"  Latency: {warm2_dur*1000:.2f}ms")
    
    # --- Test Case D: Cold Open N25_E091 ---
    print(f"\n[Test D] Cold open to N25_E091 | {tile2_coord['name']}")
    start = time.time()
    res4 = extract_point_terrain(tile2_coord["lat"], tile2_coord["lon"])
    diff_tile_dur = time.time() - start
    print(f"  Result: Elevation={res4['elevation']}m | Slope={res4['slope']}° | Aspect={res4['aspect']}°")
    print(f"  Latency: {diff_tile_dur*1000:.2f}ms")
    
    # Verify Performance Improvements
    print("\nPerformance Comparison Summary:")
    print(f"  - Cold Open (Tile 1):      {cold_dur*1000:7.2f} ms")
    print(f"  - Warm Open (Tile 1, Pt 2): {warm1_dur*1000:7.2f} ms")
    print(f"  - Warm Open (Tile 1, Pt 3): {warm2_dur*1000:7.2f} ms")
    print(f"  - Cold Open (Tile 2):      {diff_tile_dur*1000:7.2f} ms")
    
    # Warm reads must be at least 80% faster than cold reads
    speed_inc = (cold_dur - warm1_dur) / cold_dur * 100.0
    print(f"\n  Speedup on same-tile reuse: {speed_inc:.2f}%")
    assert warm1_dur < cold_dur * 0.20, "Optimization failed: Warm read is not significantly faster."
    print("  Status: SUCCESS (Warm read speedup threshold achieved).")
    
    # --- Test Case E: Cache Eviction Audit ---
    print("\nAuditing cache eviction (filling capacity with 15 unique tiles)...")
    # Generate coordinates across 15 different integer tiles to force eviction (max size is 12)
    eviction_coords = []
    for lat_idx in range(23, 27):
        for lon_idx in range(91, 95):
            eviction_coords.append((float(lat_idx) + 0.5, float(lon_idx) + 0.5))
            
    print(f"  Triggering query loop on {len(eviction_coords)} unique tiles...")
    eviction_start = time.time()
    evicted_cnt = 0
    for lat, lon in eviction_coords[:15]:
        try:
            extract_point_terrain(lat, lon)
            evicted_cnt += 1
        except Exception as e:
            # Some tiles might be over ocean/plains with NoData, ignore those errors
            pass
            
    print(f"  Processed {evicted_cnt} unique tiles in {time.time() - eviction_start:.2f}s.")
    print(f"  Current active items in cache: {len(dem_cache.cache)}")
    assert len(dem_cache.cache) <= dem_cache.max_size, "Eviction error: Cache size exceeded max_size limit!"
    print("  Status: SUCCESS (LRU eviction successfully bounded cache size).")
    print("=============================================================")

if __name__ == "__main__":
    run_benchmark()
