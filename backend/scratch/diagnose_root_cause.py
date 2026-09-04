import os
import sys
import json
import rasterio

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.abspath(os.path.join(SCRIPTS_DIR, ".."))
sys.path.insert(0, BACKEND_DIR)

from app.services.spatial_query_service import haversine_distance
from app.services.satellite_service import get_scene_detail

def main():
    ref_id = "S1D_IW_GRDH_1SDV_20260818T120410_20260818T120435_004180_007A7E_D268_COG"
    comp_id = "S1D_IW_GRDH_1SDV_20260830T120410_20260830T120435_004355_0080AB_66FC_COG"
    
    print("=" * 70)
    print("DETAILED GEOMETRY INVESTIGATION FOR THE 3441M DISCREPANCY")
    print("=" * 70)
    
    cache_dir = os.path.join(BACKEND_DIR, "data", "satellite_cache")
    
    # 1. Inspect Reference Scene in cache
    ref_meta_file = os.path.join(cache_dir, ref_id, "metadata.json")
    with open(ref_meta_file) as f:
        ref_meta = json.load(f)
        
    comp_meta_file = os.path.join(cache_dir, comp_id, "metadata.json")
    with open(comp_meta_file) as f:
        comp_meta = json.load(f)
        
    print("[1. REFERENCE SCENE CACHED METADATA]")
    print(f"Scene ID:       {ref_id}")
    print(f"Acquisition:    {ref_meta.get('acquisition_time')}")
    print(f"Cached AOI Center: Lat={ref_meta['aoi_coordinates']['latitude']}, Lon={ref_meta['aoi_coordinates']['longitude']}")
    print(f"Cached AOI Bounds: {ref_meta['clipping_bounds']}")
    
    ref_vv_file = os.path.join(cache_dir, ref_id, "vv_clipped.tif")
    with rasterio.open(ref_vv_file) as src:
        print(f"Raster Bounds:  {src.bounds}")
        print(f"Raster CRS:     {src.crs}")
        print(f"Raster Shape:   {src.shape}")
        print(f"Raster Transform: {src.transform}")
        ref_raster_center_lat = (src.bounds.top + src.bounds.bottom) / 2.0
        ref_raster_center_lon = (src.bounds.left + src.bounds.right) / 2.0
        print(f"Raster Center:  Lat={ref_raster_center_lat:.6f}, Lon={ref_raster_center_lon:.6f}")
        
    print("\n[2. COMPARISON SCENE CACHED METADATA]")
    print(f"Scene ID:       {comp_id}")
    print(f"Acquisition:    {comp_meta.get('acquisition_time')}")
    print(f"Cached AOI Center: Lat={comp_meta['aoi_coordinates']['latitude']}, Lon={comp_meta['aoi_coordinates']['longitude']}")
    print(f"Cached AOI Bounds: {comp_meta['clipping_bounds']}")
    
    comp_vv_file = os.path.join(cache_dir, comp_id, "vv_clipped.tif")
    with rasterio.open(comp_vv_file) as src:
        print(f"Raster Bounds:  {src.bounds}")
        print(f"Raster CRS:     {src.crs}")
        print(f"Raster Shape:   {src.shape}")
        print(f"Raster Transform: {src.transform}")
        comp_raster_center_lat = (src.bounds.top + src.bounds.bottom) / 2.0
        comp_raster_center_lon = (src.bounds.left + src.bounds.right) / 2.0
        print(f"Raster Center:  Lat={comp_raster_center_lat:.6f}, Lon={comp_raster_center_lon:.6f}")
        
    print("\n[3. DISCREPANCY ANALYSIS]")
    d_meta = haversine_distance(
        ref_meta['aoi_coordinates']['latitude'], ref_meta['aoi_coordinates']['longitude'],
        comp_meta['aoi_coordinates']['latitude'], comp_meta['aoi_coordinates']['longitude']
    )
    d_raster = haversine_distance(
        ref_raster_center_lat, ref_raster_center_lon,
        comp_raster_center_lat, comp_raster_center_lon
    )
    print(f"Distance between Cached Metadata Centers: {d_meta * 1000.0:.2f} meters")
    print(f"Distance between Actual GeoTIFF Centers:  {d_raster * 1000.0:.2f} meters")
    
    # 4. Fetch Native STAC BBox for both scenes
    print("\n[4. NATIVE STAC SCENE FOOTPRINT]")
    try:
        ref_stac = get_scene_detail(ref_id, "sentinel-1-grd")
        comp_stac = get_scene_detail(comp_id, "sentinel-1-grd")
        print(f"Ref Native STAC BBox:  {ref_stac.get('bbox')}")
        print(f"Comp Native STAC BBox: {comp_stac.get('bbox')}")
        
        ref_stac_center = [(ref_stac['bbox'][1] + ref_stac['bbox'][3])/2, (ref_stac['bbox'][0] + ref_stac['bbox'][2])/2]
        comp_stac_center = [(comp_stac['bbox'][1] + comp_stac['bbox'][3])/2, (comp_stac['bbox'][0] + comp_stac['bbox'][2])/2]
        d_stac = haversine_distance(ref_stac_center[0], ref_stac_center[1], comp_stac_center[0], comp_stac_center[1])
        print(f"Distance between Native STAC Centers: {d_stac * 1000.0:.2f} meters ({d_stac:.2f} km)")
    except Exception as e:
        print(f"Could not fetch STAC detail: {e}")

if __name__ == "__main__":
    main()
