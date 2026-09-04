import os
import sys
import json

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.abspath(os.path.join(SCRIPTS_DIR, ".."))
sys.path.insert(0, BACKEND_DIR)

from app.services.satellite_service import process_scene_raster, get_aoi_cache_key
from app.services.satellite_change_service import SatelliteChangeService
from app.services.radar_change_signal_service import RadarChangeSignalService
from app.services.automatic_satellite_pair_service import AutomaticSatellitePairService

def audit_location(name, lat, lon, rad=5.0):
    print("\n" + "=" * 70)
    print(f"AUDITING RSCI PIPELINE FOR: {name} (Lat: {lat}, Lon: {lon})")
    print("=" * 70)
    
    res = AutomaticSatellitePairService.analyze_location_change(lat, lon, rad)
    meta = res["metadata"]
    indicators = res["temporal_change_indicators"]
    signal = res["radar_surface_change_signal"]
    
    print(f"Status: {res['status']}")
    print(f"Orbit Direction: {meta['orbit_direction']}")
    print(f"Temporal Separation: {meta['temporal_separation_days']} days")
    print(f"Reference Scene:  {meta['reference_scene']['scene_id']}")
    print(f"Comparison Scene: {meta['comparison_scene']['scene_id']}")
    
    vv_stats = indicators["delta_vv_db"]
    vh_stats = indicators["delta_vh_db"]
    cross_stats = indicators["delta_cross_pol_db"]
    
    print("\n--- 1. DELTA VV (dB) STATISTICS ---")
    print(f"  Mean: {vv_stats['mean']} dB | Median: {vv_stats['median']} dB | Std: {vv_stats['std']} dB")
    print(f"  P10: {vv_stats['p10']} dB | P90: {vv_stats['p90']} dB | Spread (P90-P10): {vv_stats['p90'] - vv_stats['p10']:.4f} dB")
    print(f"  Significant Change (+3dB): {vv_stats['significant_positive_change_percentage']}% | (-3dB): {vv_stats['significant_negative_change_percentage']}%")

    print("\n--- 2. DELTA VH (dB) STATISTICS ---")
    print(f"  Mean: {vh_stats['mean']} dB | Median: {vh_stats['median']} dB | Std: {vh_stats['std']} dB")
    print(f"  P10: {vh_stats['p10']} dB | P90: {vh_stats['p90']} dB | Spread (P90-P10): {vh_stats['p90'] - vh_stats['p10']:.4f} dB")
    print(f"  Significant Change (+3dB): {vh_stats['significant_positive_change_percentage']}% | (-3dB): {vh_stats['significant_negative_change_percentage']}%")

    print("\n--- 3. CROSS-POLARIZATION DELTA (dB) ---")
    print(f"  Mean: {cross_stats['mean']} dB | Median: {cross_stats['median']} dB | Std: {cross_stats['std']} dB")

    print("\n--- 4. RADAR SURFACE CHANGE SIGNAL (RSCI) INTERMEDIATES ---")
    print(f"  Average Significant Change (p_avg): {signal['average_significant_change_percentage']}%")
    print(f"  Spatial Extent Score (s_ext): {signal['spatial_extent_score']} / 100")
    print(f"  VV Spread (i_vv): {signal['vv_spread_db']} dB | VH Spread (i_vh): {signal['vh_spread_db']} dB")
    print(f"  Anomaly Magnitude Score (m_mag): {signal['anomaly_magnitude_score']} / 100")
    print(f"  Formula: 0.40 * {signal['spatial_extent_score']} + 0.60 * {signal['anomaly_magnitude_score']}")
    print(f"  Final RSCI: {signal['radar_surface_change_index']} / 100")
    print(f"  Assigned Category: {signal['category']}")
    print(f"  Scientific Notice: {signal['scientific_notice']}")

def main():
    audit_location("Gangtok, Sikkim", 27.3314, 88.6138)
    audit_location("Meghalaya Location", 25.52706310546959, 91.35848472637227)

if __name__ == "__main__":
    main()
