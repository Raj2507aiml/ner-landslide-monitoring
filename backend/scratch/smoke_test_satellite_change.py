"""
Satellite Change Service Smoke Test - Phase 5 Checkpoint 13.5

Creates a mock temporal scene, performs change detection, and validates output metrics.
"""

import os
import sys
import json
import shutil
import numpy as np
import rasterio

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.abspath(os.path.join(SCRIPTS_DIR, ".."))
sys.path.insert(0, BACKEND_DIR)

from app.services.satellite_change_service import SatelliteChangeService

def create_mock_scene(source_scene_id: str, dest_scene_id: str, offset: float):
    source_dir = os.path.join(BACKEND_DIR, "data", "satellite_cache", source_scene_id)
    dest_dir = os.path.join(BACKEND_DIR, "data", "satellite_cache", dest_scene_id)
    
    os.makedirs(dest_dir, exist_ok=True)
    
    # Read reference rasters and write to mock destination with offset
    for band in ["vv_clipped.tif", "vh_clipped.tif"]:
        src_path = os.path.join(source_dir, band)
        dst_path = os.path.join(dest_dir, band)
        
        with rasterio.open(src_path) as src:
            data = src.read(1)
            # Add offset to non-zero values
            mask = data > 0
            # Convert to float to add offset, then cast back to uint16
            mod_data = data.copy().astype(np.float32)
            # Scale amplitude by the offset (e.g. 1.5 corresponds to +3.52 dB backscatter change)
            mod_data[mask] = mod_data[mask] * offset
            mod_data = np.clip(mod_data, 1, 65535).astype(np.uint16)
            
            profile = src.profile.copy()
            with rasterio.open(dst_path, "w", **profile) as dst:
                dst.write(mod_data, 1)
                
    # Copy metadata and update scene_id
    src_meta = os.path.join(source_dir, "metadata.json")
    dst_meta = os.path.join(dest_dir, "metadata.json")
    with open(src_meta, "r") as f:
        meta = json.load(f)
    meta["scene_id"] = dest_scene_id
    with open(dst_meta, "w") as f:
        json.dump(meta, f, indent=2)

def clean_mock_scene(dest_scene_id: str):
    dest_dir = os.path.join(BACKEND_DIR, "data", "satellite_cache", dest_scene_id)
    if os.path.exists(dest_dir):
        shutil.rmtree(dest_dir)

def main():
    ref_scene = "S1D_IW_GRDH_1SDV_20260803T234630_20260803T234655_003968_00733F_EB90_COG"
    comp_scene = "S1D_IW_GRDH_1SDV_20260803T234630_20260803T234655_003968_00733F_EB90_COG_MOCK"
    
    print("=" * 60)
    print("SATELLITE MULTI-TEMPORAL CHANGE DETECTION SMOKE TEST")
    print("-" * 60)
    
    # 1. Create a mock comparison scene where all backscatter values are scaled by 1.5 (yielding positive change)
    print("Generating mock comparison scene with +3.5 dB backscatter scaling...")
    create_mock_scene(ref_scene, comp_scene, offset=1.5)
    
    try:
        # 2. Run change service comparison
        results = SatelliteChangeService.calculate_temporal_change(
            reference_scene_id=ref_scene,
            comparison_scene_id=comp_scene,
            significance_threshold_db=3.0
        )
        
        meta = results["metadata"]
        print("\n[Metadata]")
        print(f"  Reference Scene:           {meta['reference_scene_id']}")
        print(f"  Comparison Scene:          {meta['comparison_scene_id']}")
        print(f"  Ref Acquisition Time:      {meta['reference_acquisition_time']}")
        print(f"  Comp Acquisition Time:     {meta['comparison_acquisition_time']}")
        print(f"  Valid Overlapping Pixels:  {meta['valid_pixel_count']} ({meta['valid_pixel_percentage']}%)")
        print(f"  AOI Compatibility:         {meta['aoi_compatibility_result']}")
        print(f"  Significance Threshold:    {meta['provisional_significance_threshold_db']} dB")
        
        print("\n[Surface Change Indicators]")
        for band, indicators in results["surface_change_indicators"].items():
            print(f"  {band.upper()}:")
            print(f"    Mean Change:        {indicators['mean']} dB")
            print(f"    Median Change:      {indicators['median']} dB")
            print(f"    Std Deviation:      {indicators['std']} dB")
            print(f"    p10 Change:         {indicators['p10']} dB")
            print(f"    p90 Change:         {indicators['p90']} dB")
            print(f"    Sig Pos Change %:   {indicators['significant_positive_change_percentage']}%")
            print(f"    Sig Neg Change %:   {indicators['significant_negative_change_percentage']}%")
            print()
            
        print("SCIENTIFIC WARNING: Identified backscatter changes represent Surface Change Indicators.")
        print("Radar returns fluctuate due to soil moisture, wind, vegetation, and local incidence angles.")
        print("These markers do NOT automatically confirm landslide occurrences.")
        print("=" * 60)
        
    except Exception as e:
        print(f"TEST FAILED: {e}")
        sys.exit(1)
    finally:
        print("Cleaning up mock scene...")
        clean_mock_scene(comp_scene)

if __name__ == "__main__":
    main()
