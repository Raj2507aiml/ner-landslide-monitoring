"""
Radar Change Signal Smoke Test - Phase 5 Checkpoint 13.9

Verifies that RadarChangeSignalService correctly calculates the RSCI score (approx 5.31)
and correctly maps the result to the Stable category using real Gangtok scenes.
"""

import os
import sys

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.abspath(os.path.join(SCRIPTS_DIR, ".."))
sys.path.insert(0, BACKEND_DIR)

from app.services.satellite_change_service import SatelliteChangeService
from app.services.radar_change_signal_service import RadarChangeSignalService

def main():
    ref_scene = "S1D_IW_GRDH_1SDV_20260730T121311_20260730T121336_003903_0070EA_F56C_COG"
    comp_scene = "S1D_IW_GRDH_1SDV_20260811T121312_20260811T121337_004078_0076F9_676B_COG"
    
    print("=" * 60)
    print("RADAR SURFACE CHANGE INDEX (RSCI) SMOKE TEST")
    print(f"Ref Scene:  {ref_scene}")
    print(f"Comp Scene: {comp_scene}")
    print("-" * 60)
    
    try:
        # 1. Run multi-temporal comparison
        change_data = SatelliteChangeService.calculate_temporal_change(ref_scene, comp_scene)
        
        # 2. Run RSCI signal calculation
        rsci_data = RadarChangeSignalService.calculate_rsci(change_data)
        
        print(f"RSCI Score:             {rsci_data['radar_surface_change_index']} / 100")
        print(f"Category:               {rsci_data['category']}")
        print(f"Spatial Extent Score:   {rsci_data['spatial_extent_score']} / 100")
        print(f"Anomaly Magnitude Score: {rsci_data['anomaly_magnitude_score']} / 100")
        print(f"Avg Change Pixels %:    {rsci_data['average_significant_change_percentage']}%")
        print(f"VV Spread:              {rsci_data['vv_spread_db']} dB")
        print(f"VH Spread:              {rsci_data['vh_spread_db']} dB")
        print()
        
        cross = rsci_data["supporting_cross_pol_change"]
        print("Supporting Cross-Polarization Indicator:")
        print(f"  Mean:   {cross['mean']} dB")
        print(f"  Median: {cross['median']} dB")
        print(f"  Std:    {cross['std']} dB")
        print()
        
        print(f"Notice: {rsci_data['scientific_notice']}")
        print("-" * 60)
        
        # Verification checks
        assert rsci_data['category'] == "Stable", f"Expected category Stable, got {rsci_data['category']}"
        assert abs(rsci_data['radar_surface_change_index'] - 5.31) < 0.1, f"Expected RSCI ~5.31, got {rsci_data['radar_surface_change_index']}"
        
        print("VERIFICATION SUCCESSFUL: RSCI is ~5.31 and category is Stable.")
        print("=" * 60)
        
    except Exception as e:
        print(f"TEST FAILED: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
