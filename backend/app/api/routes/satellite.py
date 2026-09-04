from fastapi import APIRouter, Query, HTTPException, status
from fastapi.responses import JSONResponse, StreamingResponse
from typing import Optional
from datetime import datetime
import io
import urllib.request
from app.services.aoi_service import is_inside_ner
from app.services.satellite_service import query_copernicus_stac, get_scene_detail, process_scene_raster, resolve_scene_cache_dir
from app.services.satellite_change_service import SatelliteChangeService
from app.services.radar_change_signal_service import RadarChangeSignalService
from app.services.automatic_satellite_pair_service import AutomaticSatellitePairService
from app.schemas.satellite import (
    SatelliteSearchResponse,
    SceneDetailResponse,
    SceneProcessRequest,
    SceneProcessResponse,
    SatelliteChangeAnalysisRequest,
    AutomaticSatelliteChangeRequest,
    SatelliteChangeIntelligenceResponse
)



router = APIRouter()

@router.get("/search", response_model=SatelliteSearchResponse)
def search_satellite_scenes(
    latitude: float = Query(..., ge=-90.0, le=90.0, description="Latitude of target point"),
    longitude: float = Query(..., ge=-180.0, le=180.0, description="Longitude of target point"),
    radius_km: float = Query(5.0, ge=0.1, le=25.0, description="Search radius in kilometers"),
    start_date: Optional[str] = Query(None, pattern=r"^\d{4}-\d{2}-\d{2}$", description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, pattern=r"^\d{4}-\d{2}-\d{2}$", description="End date (YYYY-MM-DD)"),
    limit: int = Query(10, ge=1, le=100, description="Maximum number of results to return"),
    collection: str = Query("sentinel-1-grd", description="Copernicus catalog collection ID")
):
    """
    Search for Sentinel satellite scenes overlapping the specified AOI coordinates.
    Requires coordinates to lie within India's North Eastern Region (NER).
    """
    # 1. Validate if coordinate is within the 8 NER states
    if not is_inside_ner(latitude, longitude):
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "status": "outside_region",
                "count": 0,
                "scenes": [],
                "message": "Please select a location within the North Eastern Region of India."
            }
        )

    # 2. Validate date logic if both are provided
    if start_date and end_date:
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")
            if start_dt > end_dt:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="start_date must be before or equal to end_date."
                )
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Dates must be in YYYY-MM-DD format."
            )

    # 3. Fetch from Copernicus STAC API
    try:
        scenes = query_copernicus_stac(
            latitude=latitude,
            longitude=longitude,
            radius_km=radius_km,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
            collection=collection
        )
        return SatelliteSearchResponse(
            status="success",
            count=len(scenes),
            scenes=scenes
        )
    except Exception as e:
        # Return 502 Bad Gateway if external Copernicus API is down/times out
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Satellite catalog search failed: {str(e)}"
        )

@router.get("/scenes/{scene_id}", response_model=SceneDetailResponse)
def get_scene_metadata(
    scene_id: str,
    collection: str = Query("sentinel-1-grd", description="Copernicus catalog collection ID")
):
    """
    Retrieves the complete STAC Item details and available asset metadata 
    for a specific real Sentinel scene ID.
    """
    try:
        detail = get_scene_detail(scene_id, collection)
        return detail
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to inspect satellite scene: {str(e)}"
        )

@router.get("/scenes/{scene_id}/preview")
def get_scene_preview(
    scene_id: str,
    collection: str = Query("sentinel-1-grd", description="Copernicus catalog collection ID")
):
    """
    Fetches the thumbnail asset for the specified Sentinel scene and streams it 
    back to the client as an image preview.
    """
    try:
        detail = get_scene_detail(scene_id, collection)
        
        thumbnail_asset = None
        for asset in detail.get("assets", []):
            if asset.get("key") == "thumbnail" or (asset.get("roles") and "thumbnail" in asset.get("roles")):
                thumbnail_asset = asset
                break
                
        if not thumbnail_asset or not thumbnail_asset.get("href"):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No preview thumbnail asset found for scene '{scene_id}'."
            )
            
        url = thumbnail_asset.get("href")
        req = urllib.request.Request(url, method="GET")
        
        with urllib.request.urlopen(req, timeout=15) as response:
            content_bytes = response.read()
            media_type = response.headers.get_content_type() or "image/png"
            if media_type == "application/octet-stream":
                media_type = "image/png"
            return StreamingResponse(io.BytesIO(content_bytes), media_type=media_type)
            
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to fetch scene preview from source catalogue: {str(e)}"
        )

@router.post("/scenes/{scene_id}/process", response_model=SceneProcessResponse)
def process_scene(
    scene_id: str,
    payload: SceneProcessRequest,
    collection: str = Query("sentinel-1-grd", description="Copernicus catalog collection ID")
):
    """
    Triggers backend processing for a Sentinel-1 scene: fetches the raw VV/VH
    bands from Copernicus S3, crops them to the exact 5km AOI, and caches them locally.
    """
    try:
        result = process_scene_raster(
            scene_id=scene_id,
            latitude=payload.latitude,
            longitude=payload.longitude,
            radius_km=payload.radius_km,
            collection_id=collection
        )
        return SceneProcessResponse(
            status=result["status"],
            scene_id=result["scene_id"],
            aoi_key=result.get("aoi_key"),
            vv_path=result["vv_path"],
            vh_path=result["vh_path"],
            aoi_bounds=result["aoi_bounds"],
            message=result["message"]
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Processing failed: {str(e)}"
        )

@router.get("/scene/{scene_id}/raster-preview/{layer}")
def get_raster_preview(
    scene_id: str,
    layer: str,
    aoi_key: Optional[str] = Query(None, description="AOI cache key subdirectory")
):
    """
    Renders cached GeoTIFF (VV or VH) into a colorized semi-transparent PNG overlay
    and returns image bytes with spatial bounds headers.
    """
    import re
    import json
    import os
    import io
    from fastapi.responses import StreamingResponse
    from app.services.terrain_service import render_raster_to_png
    
    # 1. Validate scene_id alphanumeric / underscores
    if not scene_id or not all(c.isalnum() or c == "_" for c in scene_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid scene ID format."
        )
        
    # 2. Validate layer parameter
    if layer not in {"vv", "vh"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid layer name. Must be 'vv' or 'vh'."
        )
        
    # 3. Locate cached file
    cache_dir = resolve_scene_cache_dir(scene_id, aoi_key)
    if not cache_dir or not os.path.exists(cache_dir):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Layer '{layer}' has not been processed yet for scene '{scene_id}'."
        )
        
    tif_path = os.path.join(cache_dir, f"{layer}_clipped.tif")
    if not os.path.exists(tif_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Layer '{layer}' has not been processed yet for scene '{scene_id}'."
        )
        
    try:
        png_bytes, bounds = render_raster_to_png(tif_path, layer)
        
        # Leaflet bounds expect: [[south, west], [north, east]]
        headers = {
            "X-Raster-Bounds": json.dumps(bounds),
            "Access-Control-Expose-Headers": "X-Raster-Bounds"
        }
        return StreamingResponse(io.BytesIO(png_bytes), media_type="image/png", headers=headers)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Rendering failed: {str(e)}"
        )

@router.post("/change-analysis")
def analyze_satellite_change(payload: SatelliteChangeAnalysisRequest):
    """
    Exposes multi-temporal Sentinel-1 change analysis.
    Compares reference and comparison scenes and computes the Radar Surface Change Index.
    """
    try:
        # 1. Run multi-temporal comparison
        change_data = SatelliteChangeService.calculate_temporal_change(
            reference_scene_id=payload.reference_scene_id,
            comparison_scene_id=payload.comparison_scene_id,
            aoi_key=payload.aoi_key
        )
        
        # 2. Run RSCI signal calculation
        rsci_data = RadarChangeSignalService.calculate_rsci(change_data)
        
        # Return structured result separating metadata, temporal_change_indicators, and radar_surface_change_signal
        return {
            "metadata": change_data["metadata"],
            "temporal_change_indicators": change_data["surface_change_indicators"],
            "radar_surface_change_signal": {
                "radar_surface_change_index": rsci_data["radar_surface_change_index"],
                "category": rsci_data["category"],
                "spatial_extent_score": rsci_data["spatial_extent_score"],
                "anomaly_magnitude_score": rsci_data["anomaly_magnitude_score"],
                "average_significant_change_percentage": rsci_data["average_significant_change_percentage"],
                "vv_spread_db": rsci_data["vv_spread_db"],
                "vh_spread_db": rsci_data["vh_spread_db"],
                "supporting_cross_pol_change": rsci_data["supporting_cross_pol_change"],
                "scientific_notice": rsci_data["scientific_notice"]
            }
        }
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred during change analysis: {str(e)}"
        )

@router.post("/automatic-change-analysis")
def analyze_automatic_satellite_change(payload: AutomaticSatelliteChangeRequest):
    """
    Automatically selects compatible reference/comparison scenes over target location coordinates
    and runs multi-temporal change and Radar Surface Change Index (RSCI) calculations.
    """
    # 1. Validate coordinate boundary within India's North Eastern Region
    if not is_inside_ner(payload.latitude, payload.longitude):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Target coordinates must lie within India's North Eastern Region."
        )
        
    try:
        # Call the auto pairing and change service using the default 5.0 km AOI radius
        result = AutomaticSatellitePairService.analyze_location_change(
            latitude=payload.latitude,
            longitude=payload.longitude,
            radius_km=5.0
        )
        return result
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Automatic satellite change analysis failed: {str(e)}"
        )


@router.get("/change-intelligence", response_model=SatelliteChangeIntelligenceResponse)
def get_satellite_change_intelligence(
    latitude: float = Query(..., ge=-90.0, le=90.0, description="Latitude coordinate between -90 and 90"),
    longitude: float = Query(..., ge=-180.0, le=180.0, description="Longitude coordinate between -180 and 180"),
    radius_km: float = Query(5.0, ge=0.1, le=25.0, description="AOI search radius in kilometers (0.1 to 25.0)")
):
    """
    Satellite Change Intelligence Engine (Phase 7).
    Standardizes multi-temporal Sentinel-1 SAR change detections, backscatter deltas,
    and Radar Surface Change Index (RSCI) calculations into an explainable domain intelligence response.
    """
    try:
        from app.services.satellite_intelligence_service import analyze_satellite_change_intelligence
        result = analyze_satellite_change_intelligence(
            latitude=latitude,
            longitude=longitude,
            radius_km=radius_km
        )
        return SatelliteChangeIntelligenceResponse(**result)
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(val_err)
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Satellite change intelligence analysis failed: {str(exc)}"
        )



