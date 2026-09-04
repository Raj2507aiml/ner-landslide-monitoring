"""
Satellite Feature Service Smoke Test - Phase 5 Checkpoint 13.3

Runs feature extraction on a cached Sentinel-1 scene and outputs backscatter stats.
"""

import os
import sys

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.abspath(os.path.join(SCRIPTS_DIR, ".."))
sys.path.insert(0, BACKEND_DIR)

from app.services.satellite_feature_service import SatelliteFeatureService

def main():
    scene_id = "S1D_IW_GRDH_1SDV_20260803T234630_20260803T234655_003968_00733F_EB90_COG"
    print("=" * 60)
    print(f"SATELLITE FEATURE EXTRACTION SMOKE TEST")
    print(f"Scene ID: {scene_id}")
    print("-" * 60)
    
    try:
        features = SatelliteFeatureService.extract_features(scene_id)
        
        print(f"Total Pixels:             {features['total_pixel_count']}")
        print(f"Valid Pixels:             {features['valid_pixel_count']}")
        print(f"Valid Pixel Percentage:   {features['valid_pixel_percentage']}%")
        print()
        
        stats = features["statistics"]
        
        print("VV Backscatter Intensity (dB):")
        print(f"  Mean:   {stats['vv_db']['mean']} dB")
        print(f"  Median: {stats['vv_db']['median']} dB")
        print(f"  Std:    {stats['vv_db']['std']} dB")
        print(f"  p10:    {stats['vv_db']['p10']} dB")
        print(f"  p90:    {stats['vv_db']['p90']} dB")
        print()
        
        print("VH Backscatter Intensity (dB):")
        print(f"  Mean:   {stats['vh_db']['mean']} dB")
        print(f"  Median: {stats['vh_db']['median']} dB")
        print(f"  Std:    {stats['vh_db']['std']} dB")
        print(f"  p10:    {stats['vh_db']['p10']} dB")
        print(f"  p90:    {stats['vh_db']['p90']} dB")
        print()
        
        print("Cross-Polarization Difference (VH_dB - VV_dB):")
        print(f"  Mean:   {stats['cross_pol_diff_db']['mean']} dB")
        print(f"  Median: {stats['cross_pol_diff_db']['median']} dB")
        print(f"  Std:    {stats['cross_pol_diff_db']['std']} dB")
        print()
        print("SCIENTIFIC WARNING: A single Sentinel-1 radar scene is an instantaneous backscatter observation.")
        print("Landslide detection requires relative temporal change analysis between pre-event and post-event passes.")
        print("=" * 60)
    except Exception as e:
        print(f"TEST FAILED with exception: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
