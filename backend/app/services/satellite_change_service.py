"""
Satellite Change Service - Phase 5 Checkpoint 13.5

Compares two cached Sentinel-1 scenes over the same AOI to identify surface change indicators.
Calculates temporal deltas for VV, VH, and cross-polarization difference,
enforcing strict geographic and dimensions validations.
"""

import os
import json
import numpy as np
import rasterio
from typing import Dict, Any, Optional

from app.services.spatial_query_service import haversine_distance
from app.services.satellite_service import resolve_scene_cache_dir

class SatelliteChangeService:
    @staticmethod
    def calculate_temporal_change(
        reference_scene_id: str,
        comparison_scene_id: str,
        significance_threshold_db: float = 3.0,
        aoi_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Loads reference and comparison VV & VH clipped GeoTIFFs, performs alignment checks,
        converts DN amplitude to decibels, and computes temporal change statistics.
        """
        # Resolve paths
        service_dir = os.path.dirname(os.path.abspath(__file__))
        app_dir = os.path.dirname(service_dir)
        backend_dir = os.path.dirname(app_dir)
        
        # If aoi_key is omitted, check for common AOI keys between both scenes
        if aoi_key is None:
            ref_base = os.path.join(backend_dir, "data", "satellite_cache", reference_scene_id)
            comp_base = os.path.join(backend_dir, "data", "satellite_cache", comparison_scene_id)
            if os.path.exists(ref_base) and os.path.exists(comp_base):
                ref_subdirs = {d for d in os.listdir(ref_base) if os.path.isdir(os.path.join(ref_base, d)) and os.path.exists(os.path.join(ref_base, d, "metadata.json"))}
                comp_subdirs = {d for d in os.listdir(comp_base) if os.path.isdir(os.path.join(comp_base, d)) and os.path.exists(os.path.join(comp_base, d, "metadata.json"))}
                common_aois = ref_subdirs.intersection(comp_subdirs)
                if common_aois:
                    common_sorted = sorted(list(common_aois), key=lambda k: max(os.path.getmtime(os.path.join(ref_base, k)), os.path.getmtime(os.path.join(comp_base, k))), reverse=True)
                    aoi_key = common_sorted[0]
        
        ref_cache_dir = resolve_scene_cache_dir(reference_scene_id, aoi_key, base_dir=backend_dir)
        comp_cache_dir = resolve_scene_cache_dir(comparison_scene_id, aoi_key, base_dir=backend_dir)
        
        # 1. Verification of file availability
        if not ref_cache_dir or not os.path.exists(ref_cache_dir):
            raise FileNotFoundError(
                f"Reference scene directory not found for: {reference_scene_id} (AOI: {aoi_key or 'default'}). "
                "Ensure both scenes have been successfully cached first."
            )
            
        if not comp_cache_dir or not os.path.exists(comp_cache_dir):
            raise FileNotFoundError(
                f"Comparison scene directory not found for: {comparison_scene_id} (AOI: {aoi_key or 'default'}). "
                "Ensure both scenes have been successfully cached first."
            )

        ref_vv_path = os.path.join(ref_cache_dir, "vv_clipped.tif")
        ref_vh_path = os.path.join(ref_cache_dir, "vh_clipped.tif")
        ref_meta_path = os.path.join(ref_cache_dir, "metadata.json")
        
        comp_vv_path = os.path.join(comp_cache_dir, "vv_clipped.tif")
        comp_vh_path = os.path.join(comp_cache_dir, "vh_clipped.tif")
        comp_meta_path = os.path.join(comp_cache_dir, "metadata.json")
        
        for file_path in [ref_vv_path, ref_vh_path, ref_meta_path, comp_vv_path, comp_vh_path, comp_meta_path]:
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"Required cached file missing: {file_path}")

        # 2. Load and parse metadata files
        with open(ref_meta_path, "r") as f:
            ref_meta = json.load(f)
        with open(comp_meta_path, "r") as f:
            comp_meta = json.load(f)
            
        # 3. Perform geographic compatibility validation checks
        ref_coords = ref_meta.get("aoi_coordinates", {})
        comp_coords = comp_meta.get("aoi_coordinates", {})
        
        if not ref_coords or not comp_coords:
            raise ValueError("Invalid scene metadata: missing 'aoi_coordinates'.")
            
        dist_km = haversine_distance(
            ref_coords["latitude"], ref_coords["longitude"],
            comp_coords["latitude"], comp_coords["longitude"]
        )
        
        # Max center discrepancy allowed is 100 meters (0.1 km)
        aoi_compatible = bool(dist_km <= 0.1)
        if not aoi_compatible:
            raise ValueError(
                f"Scenes are geographically incompatible. Center discrepancy: {dist_km * 1000.0:.1f} meters. "
                "Both scenes must cover the same geographical AOI center."
            )

        # 4. Read rasters and perform shape dimensions validation checks
        with rasterio.open(ref_vv_path) as ref_vv_src, \
             rasterio.open(ref_vh_path) as ref_vh_src, \
             rasterio.open(comp_vv_path) as comp_vv_src, \
             rasterio.open(comp_vh_path) as comp_vh_src:
            
            ref_vv = ref_vv_src.read(1)
            ref_vh = ref_vh_src.read(1)
            comp_vv = comp_vv_src.read(1)
            comp_vh = comp_vh_src.read(1)

        if ref_vv.shape != comp_vv.shape:
            raise ValueError(
                f"VV dimensions mismatch: Reference {ref_vv.shape} vs Comparison {comp_vv.shape}. "
                "Clipped rasters must share identical dimensions."
            )
        if ref_vh.shape != comp_vh.shape:
            raise ValueError(
                f"VH dimensions mismatch: Reference {ref_vh.shape} vs Comparison {comp_vh.shape}."
            )

        total_pixel_count = int(ref_vv.size)

        # 5. Extract temporal masks excluding invalid pixels (<= 0) across all 4 arrays
        valid_mask = (ref_vv > 0) & (ref_vh > 0) & (comp_vv > 0) & (comp_vh > 0)
        valid_pixel_count = int(np.sum(valid_mask))
        
        if valid_pixel_count == 0:
            raise ValueError("No common overlapping valid pixels found across reference and comparison scenes.")

        valid_pixel_percentage = round((valid_pixel_count / total_pixel_count) * 100.0, 2)

        # 6. Extract valid pixel arrays as floats
        ref_vv_valid = ref_vv[valid_mask].astype(np.float32)
        ref_vh_valid = ref_vh[valid_mask].astype(np.float32)
        comp_vv_valid = comp_vv[valid_mask].astype(np.float32)
        comp_vh_valid = comp_vh[valid_mask].astype(np.float32)

        # 7. Convert to relative decibel (dB) representation
        ref_vv_db = 20.0 * np.log10(ref_vv_valid)
        ref_vh_db = 20.0 * np.log10(ref_vh_valid)
        comp_vv_db = 20.0 * np.log10(comp_vv_valid)
        comp_vh_db = 20.0 * np.log10(comp_vh_valid)

        # 8. Calculate temporal change (Deltas)
        delta_vv = comp_vv_db - ref_vv_db
        delta_vh = comp_vh_db - ref_vh_db

        # Cross-polarization values: (VH_dB - VV_dB)
        cross_ref = ref_vh_db - ref_vv_db
        cross_comp = comp_vh_db - comp_vv_db
        delta_cross = cross_comp - cross_ref

        # 9. Compute statistical metrics
        def compute_delta_stats(arr: np.ndarray, threshold: float) -> Dict[str, float]:
            mean_val = float(np.mean(arr))
            median_val = float(np.median(arr))
            std_val = float(np.std(arr))
            p10_val = float(np.percentile(arr, 10))
            p90_val = float(np.percentile(arr, 90))
            
            # Significant changes calculations
            sig_pos_count = np.sum(arr >= threshold)
            sig_neg_count = np.sum(arr <= -threshold)
            
            percentage_pos = (sig_pos_count / len(arr)) * 100.0
            percentage_neg = (sig_neg_count / len(arr)) * 100.0
            
            return {
                "mean": round(mean_val, 4),
                "median": round(median_val, 4),
                "std": round(std_val, 4),
                "p10": round(p10_val, 4),
                "p90": round(p90_val, 4),
                "significant_positive_change_percentage": round(percentage_pos, 2),
                "significant_negative_change_percentage": round(percentage_neg, 2)
            }

        return {
            "metadata": {
                "reference_scene_id": reference_scene_id,
                "comparison_scene_id": comparison_scene_id,
                "reference_acquisition_time": ref_meta.get("acquisition_time"),
                "comparison_acquisition_time": comp_meta.get("acquisition_time"),
                "total_pixel_count": total_pixel_count,
                "valid_pixel_count": valid_pixel_count,
                "valid_pixel_percentage": valid_pixel_percentage,
                "aoi_compatibility_result": "Compatible",
                "provisional_significance_threshold_db": significance_threshold_db
            },
            "surface_change_indicators": {
                "delta_vv_db": compute_delta_stats(delta_vv, significance_threshold_db),
                "delta_vh_db": compute_delta_stats(delta_vh, significance_threshold_db),
                "delta_cross_pol_db": compute_delta_stats(delta_cross, significance_threshold_db)
            }
        }
