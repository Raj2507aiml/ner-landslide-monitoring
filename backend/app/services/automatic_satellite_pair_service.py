"""
Automatic Satellite Pair Service - Phase 5 Checkpoint 14.2

Automatically discovers, pairs, and processes compatible multi-temporal Sentinel-1 scenes
for a given latitude, longitude, and radius, running change detection and RSCI.
"""

import os
import time
import threading
from datetime import datetime
from typing import Dict, Any, List, Optional

from app.services.satellite_service import query_copernicus_stac, process_scene_raster
from app.services.satellite_change_service import SatelliteChangeService
from app.services.radar_change_signal_service import RadarChangeSignalService

_satellite_analysis_cache: Dict[str, Any] = {}
_satellite_analysis_lock = threading.Lock()

class AutomaticSatellitePairService:
    @classmethod
    def get_cached_analysis(cls, latitude: float, longitude: float, radius_km: float = 5.0) -> Optional[Dict[str, Any]]:
        """Returns non-expired cached analysis result for coordinates, or None."""
        cache_key = f"{round(latitude, 3)}_{round(longitude, 3)}_{round(radius_km, 1)}"
        with _satellite_analysis_lock:
            cached = _satellite_analysis_cache.get(cache_key)
            if cached and (time.time() - cached["timestamp"]) < 3600:
                return cached["data"]
        return None

    @classmethod
    def analyze_location_change(
        cls,
        latitude: float,
        longitude: float,
        radius_km: float = 5.0
    ) -> Dict[str, Any]:
        """
        Queries STAC for the past 60 days, selects the best ascending/descending
        scene pair, triggers raw S3 clipping, and calculates temporal backscatter change.
        Thread-safe and cached for 1 hour to prevent redundant heavy S3 downloads.
        """
        cache_key = f"{round(latitude, 3)}_{round(longitude, 3)}_{round(radius_km, 1)}"
        with _satellite_analysis_lock:
            cached = _satellite_analysis_cache.get(cache_key)
            if cached and (time.time() - cached["timestamp"]) < 3600:
                return cached["data"]

        result = cls._execute_analysis(latitude, longitude, radius_km)
        with _satellite_analysis_lock:
            _satellite_analysis_cache[cache_key] = {"timestamp": time.time(), "data": result}
        return result

    @classmethod
    def _execute_analysis(
        cls,
        latitude: float,
        longitude: float,
        radius_km: float = 5.0
    ) -> Dict[str, Any]:
        # 1. Query Copernicus STAC API for Sentinel-1 scenes in the past 60 days
        end_date = datetime.utcnow().strftime("%Y-%m-%d")
        start_date = (datetime.utcnow() - pd_days(60)).strftime("%Y-%m-%d")
        
        try:
            scenes = query_copernicus_stac(
                latitude=latitude,
                longitude=longitude,
                radius_km=radius_km,
                start_date=start_date,
                end_date=end_date,
                limit=100
            )
        except Exception as e:
            raise Exception(f"Failed to query satellite catalog: {str(e)}")

        # Helper to parse datetime strings
        def parse_date(date_str: str) -> datetime:
            cleaned = date_str.replace("Z", "")
            if "." in cleaned:
                cleaned = cleaned.split(".")[0]
            return datetime.strptime(cleaned, "%Y-%m-%dT%H:%M:%S")

        # Helper to check coordinate within bbox
        def is_coord_in_bbox(lat: float, lon: float, bbox: List[float]) -> bool:
            if len(bbox) != 4:
                return False
            # bbox: [min_lon, min_lat, max_lon, max_lat]
            return bbox[0] <= lon <= bbox[2] and bbox[1] <= lat <= bbox[3]

        # 2. Filter candidates for valid Sentinel-1 GRD scenes covering the coordinates
        valid_candidates = []
        for s in scenes:
            scene_id = s.get("id")
            dt_str = s.get("datetime")
            bbox = s.get("bbox")
            orbit = s.get("orbit_direction")
            
            if not scene_id or not dt_str or not bbox or not orbit:
                continue
                
            # Must overlap the exact target coordinate
            if not is_coord_in_bbox(latitude, longitude, bbox):
                continue
                
            try:
                acq_time = parse_date(dt_str)
                valid_candidates.append({
                    "id": scene_id,
                    "datetime": acq_time,
                    "orbit_direction": orbit,
                    "collection": s.get("collection", "sentinel-1-grd"),
                    "bbox": bbox,
                    "platform": s.get("platform", "sentinel-1")
                })
            except ValueError:
                continue

        if len(valid_candidates) < 2:
            return {
                "status": "INSUFFICIENT_DATA",
                "message": f"Insufficient Sentinel-1 scenes found over the location in the past 60 days (found {len(valid_candidates)})."
            }

        # 3. Group candidates by orbit direction (ascending vs descending)
        orbit_groups = {"ascending": [], "descending": []}
        for cand in valid_candidates:
            orbit = cand["orbit_direction"]
            if orbit in orbit_groups:
                orbit_groups[orbit].append(cand)

        paired_candidates = []

        # 4. Search for valid pairs in each group
        for orbit, group in orbit_groups.items():
            if len(group) < 2:
                continue
            
            # Sort group by acquisition time descending (latest first)
            group.sort(key=lambda x: x["datetime"], reverse=True)
            
            # Latest scene acts as comparison scene
            comp_scene = group[0]
            
            best_ref_scene = None
            best_score = float("inf")
            best_diff_days = 0.0
            
            # Search earlier scenes in the same group
            for ref_scene in group[1:]:
                time_diff = comp_scene["datetime"] - ref_scene["datetime"]
                diff_days = time_diff.total_seconds() / 86400.0
                
                # Requirements: 10 to 36 days separation, max age limit 45 days
                if 10.0 <= diff_days <= 36.0:
                    # Preference: closest to 12 days (orbital repeat)
                    score = abs(diff_days - 12.0)
                    if score < best_score:
                        best_score = score
                        best_ref_scene = ref_scene
                        best_diff_days = diff_days
            
            if best_ref_scene:
                paired_candidates.append({
                    "orbit_direction": orbit,
                    "comp_scene": comp_scene,
                    "ref_scene": best_ref_scene,
                    "diff_days": best_diff_days,
                    "score": best_score
                })

        # 5. Handle pairing results
        if not paired_candidates:
            return {
                "status": "GEOMETRY_MISMATCH",
                "message": (
                    "Multiple Sentinel-1 scenes exist, but no compatible reference and comparison scenes "
                    "share matching orbital track geometries within a 10-36 day separation window."
                )
            }

        # Choose the best pair (smallest score/closest repeat cycle)
        paired_candidates.sort(key=lambda x: x["score"])

        from app.core.config import settings
        if not settings.CDSE_S3_ACCESS_KEY or not settings.CDSE_S3_SECRET_KEY:
            return {
                "status": "CREDENTIALS_REQUIRED",
                "message": "Copernicus S3 credentials are not configured in this environment. Configure CDSE_S3_ACCESS_KEY and CDSE_S3_SECRET_KEY in backend environment variables to enable live Sentinel-1 SAR change calculations."
            }
        
        last_error = None
        for selected_pair in paired_candidates:
            ref_scene = selected_pair["ref_scene"]
            comp_scene = selected_pair["comp_scene"]
            
            # 6. Process BOTH scenes using the exact same coordinate parameters
            try:
                ref_res = process_scene_raster(
                    scene_id=ref_scene["id"],
                    latitude=latitude,
                    longitude=longitude,
                    radius_km=radius_km,
                    collection_id=ref_scene["collection"]
                )
                
                comp_res = process_scene_raster(
                    scene_id=comp_scene["id"],
                    latitude=latitude,
                    longitude=longitude,
                    radius_km=radius_km,
                    collection_id=comp_scene["collection"]
                )
                
                # 7. Run SatelliteChangeService and RadarChangeSignalService
                aoi_key = ref_res.get("aoi_key")
                change_data = SatelliteChangeService.calculate_temporal_change(
                    reference_scene_id=ref_scene["id"],
                    comparison_scene_id=comp_scene["id"],
                    aoi_key=aoi_key
                )
                
                rsci_data = RadarChangeSignalService.calculate_rsci(change_data)
                
                # 8. Return structured payload
                return {
                    "status": "PAIRED_SUCCESS",
                    "metadata": {
                        "orbit_direction": selected_pair["orbit_direction"],
                        "temporal_separation_days": round(selected_pair["diff_days"], 2),
                        "reference_scene": {
                            "scene_id": ref_scene["id"],
                            "acquisition_time": ref_scene["datetime"].isoformat() + "Z",
                            "platform": ref_scene["platform"]
                        },
                        "comparison_scene": {
                            "scene_id": comp_scene["id"],
                            "acquisition_time": comp_scene["datetime"].isoformat() + "Z",
                            "platform": comp_scene["platform"]
                        }
                    },
                    "temporal_change_indicators": change_data["surface_change_indicators"],
                    "radar_surface_change_signal": rsci_data
                }
            except Exception as e:
                last_error = e
                continue

        if last_error:
            raise Exception(f"Failed to execute multi-temporal change calculations: {str(last_error)}")

# Helper function
def pd_days(count: int):
    import datetime
    return datetime.timedelta(days=count)
