"""
Satellite Feature Service - Phase 5 Checkpoint 13.3

Reads local cached Sentinel-1 VV & VH clipped GeoTIFFs, filters out nodata (0) values,
converts amplitude digital numbers (DN) to relative backscatter in decibels (dB),
and extracts geomorphological radar descriptors.
"""

import os
import numpy as np
import rasterio
from typing import Dict, Any, Optional
from app.services.satellite_service import resolve_scene_cache_dir

class SatelliteFeatureService:
    @staticmethod
    def extract_features(scene_id: str, aoi_key: Optional[str] = None) -> Dict[str, Any]:
        """
        Reads cached VV and VH clipped GeoTIFFs, filters out invalid pixels (values <= 0),
        and extracts backscatter statistics (mean, median, std, p10, p90) and cross-polarization ratio.
        """
        # Paths resolution
        service_dir = os.path.dirname(os.path.abspath(__file__))
        app_dir = os.path.dirname(service_dir)
        backend_dir = os.path.dirname(app_dir)
        cache_dir = resolve_scene_cache_dir(scene_id, aoi_key, base_dir=backend_dir)
        
        if not cache_dir or not os.path.exists(cache_dir):
            raise FileNotFoundError(
                f"Clipped rasters missing for scene '{scene_id}' (AOI: {aoi_key or 'default'}). "
                "Verify that the satellite processing pipeline has successfully cached the scene."
            )
            
        vv_path = os.path.join(cache_dir, "vv_clipped.tif")
        vh_path = os.path.join(cache_dir, "vh_clipped.tif")
        
        if not os.path.exists(vv_path) or not os.path.exists(vh_path):
            raise FileNotFoundError(
                f"Clipped rasters missing for scene '{scene_id}' in directory: {cache_dir}. "
                "Verify that the satellite processing pipeline has successfully cached the scene."
            )
            
        # Read arrays
        with rasterio.open(vv_path) as src_vv, rasterio.open(vh_path) as src_vh:
            vv_arr = src_vv.read(1)
            vh_arr = src_vh.read(1)
            
        total_pixel_count = int(vv_arr.size)
        
        # Exclude nodata value 0; align masks for both polarizations
        valid_mask = (vv_arr > 0) & (vh_arr > 0)
        valid_pixel_count = int(np.sum(valid_mask))
        
        if valid_pixel_count == 0:
            raise ValueError(f"No valid pixels (value > 0) found in rasters for scene '{scene_id}'.")
            
        valid_pixel_percentage = round((valid_pixel_count / total_pixel_count) * 100.0, 2)
        
        # Extract valid values
        vv_valid = vv_arr[valid_mask].astype(np.float32)
        vh_valid = vh_arr[valid_mask].astype(np.float32)
        
        # Convert DN amplitude directly to decibels (dB)
        # Formula: dB = 20 * log10(DN)
        vv_db = 20.0 * np.log10(vv_valid)
        vh_db = 20.0 * np.log10(vh_valid)
        
        # Cross-polarization difference (VH_dB - VV_dB)
        cross_db = vh_db - vv_db
        
        # Helper to compile descriptive stats
        def compute_stats(arr: np.ndarray, include_percentiles: bool = True) -> Dict[str, float]:
            stats = {
                "mean": round(float(np.mean(arr)), 4),
                "median": round(float(np.median(arr)), 4),
                "std": round(float(np.std(arr)), 4)
            }
            if include_percentiles:
                stats.update({
                    "p10": round(float(np.percentile(arr, 10)), 4),
                    "p90": round(float(np.percentile(arr, 90)), 4)
                })
            return stats
            
        return {
            "scene_id": scene_id,
            "total_pixel_count": total_pixel_count,
            "valid_pixel_count": valid_pixel_count,
            "valid_pixel_percentage": valid_pixel_percentage,
            "statistics": {
                "vv_db": compute_stats(vv_db, include_percentiles=True),
                "vh_db": compute_stats(vh_db, include_percentiles=True),
                "cross_pol_diff_db": compute_stats(cross_db, include_percentiles=False)
            }
        }
