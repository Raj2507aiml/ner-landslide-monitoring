from fastapi import APIRouter, Query, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.services.aoi_service import calculate_aoi, is_inside_ner
from app.services.terrain_service import fetch_and_clip_dem, analyze_point_terrain

router = APIRouter()

class TerrainAnalysisResponse(BaseModel):
    latitude: float
    longitude: float
    elevation_meters: float
    slope_degrees: float
    terrain_risk_level: str

@router.get("/analyze", response_model=TerrainAnalysisResponse)
def analyze_terrain(
    latitude: float = Query(..., ge=-90.0, le=90.0, description="Latitude of target coordinate (-90 to 90)"),
    longitude: float = Query(..., ge=-180.0, le=180.0, description="Longitude of target coordinate (-180 to 180)"),
    sample_radius_meters: float = Query(30.0, ge=5.0, le=500.0, description="Sampling distance around point in meters")
):
    """
    Phase 3.1: Terrain and Slope Analysis Endpoint.
    
    Accepts latitude and longitude, fetches elevation data, computes local terrain slope
    using multi-point sampling, and determines the operational landslide risk level:
    - 0 to 10 degrees -> LOW
    - 10 to 25 degrees -> MODERATE
    - 25 to 40 degrees -> HIGH
    - Above 40 degrees -> VERY_HIGH
    """
    try:
        result = analyze_point_terrain(latitude=latitude, longitude=longitude, sample_radius_meters=sample_radius_meters)
        return TerrainAnalysisResponse(**result)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Terrain analysis failed: {str(e)}"
        )

class TerrainStatistics(BaseModel):
    min_elevation: float
    max_elevation: float
    mean_elevation: float
    min_slope: float
    max_slope: float
    mean_slope: float
    dominant_aspect: str

class TerrainProcessResponse(BaseModel):
    status: str
    scene_id: str
    dem_path: str
    slope_path: str
    aspect_path: str
    statistics: TerrainStatistics
    message: Optional[str] = None

@router.get("/process", response_model=TerrainProcessResponse)
def process_terrain(
    scene_id: str = Query(..., description="Target satellite scene ID"),
    latitude: float = Query(..., ge=-90.0, le=90.0, description="Latitude of coordinate selection"),
    longitude: float = Query(..., ge=-180.0, le=180.0, description="Longitude of coordinate selection"),
    radius_km: float = Query(5.0, ge=0.1, le=25.0, description="AOI radius size in kilometers")
):
    """
    Validates coordinate bounds, maps to the Area of Interest (AOI),
    queries the public Copernicus GLO-30 DEM, and computes slope/aspect metrics.
    """
    # 1. Validate if coordinates lie within the North Eastern Region of India
    if not is_inside_ner(latitude, longitude):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Coordinates lie outside India's North Eastern Region."
        )

    # 2. Reconstruct the bounding box bounds using the project's AOI service
    aoi_data = calculate_aoi(latitude, longitude, radius_km)
    bbox = aoi_data["bounding_box"]

    # 3. Call the terrain processing service
    try:
        result = fetch_and_clip_dem(scene_id=scene_id, bbox=bbox)
        return TerrainProcessResponse(**result)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Terrain data unavailable: {str(e)}"
        )

@router.get("/scenes/{scene_id}/overlay")
def get_terrain_overlay(
    scene_id: str,
    layer: str = Query(..., description="Target terrain layer: slope, dem, or aspect")
):
    """
    Renders the cached slope, dem, or aspect GeoTIFF as a transparent RGBA PNG
    reprojected to EPSG:4326 on the fly, for Leaflet overlay display.
    """
    import re
    import json
    import os
    import io
    from fastapi.responses import StreamingResponse
    from app.services.terrain_service import render_raster_to_png
    
    # 1. Validate scene_id against regex to prevent path traversal
    if not re.match(r"^[a-zA-Z0-9_-]{30,80}$", scene_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid scene ID format."
        )
        
    # 2. Validate layer parameter
    if layer not in {"slope", "dem", "aspect"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid layer name. Must be 'slope', 'dem', or 'aspect'."
        )
        
    # 3. Locate cached file
    from app.services.satellite_service import resolve_scene_cache_dir
    cache_dir = resolve_scene_cache_dir(scene_id)
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

@router.get("/scenes/{scene_id}/risk")
def get_terrain_risk(
    scene_id: str,
    resolution: int = Query(25, ge=10, le=50, description="Grid resolution size (10 to 50)"),
    rainfall: Optional[float] = Query(None, description="Optional 24h rainfall trigger value (mm)"),
    rainfall_3d: Optional[float] = Query(None, description="Optional 3-day antecedent rainfall trigger value (mm)"),
    rainfall_7d: Optional[float] = Query(None, description="Optional 7-day antecedent rainfall trigger value (mm)"),
    db: Session = Depends(get_db)
):
    """
    Generates a spatial risk surface over the scene AOI and returns a transparent RGBA PNG.
    Features: in-memory candidate prefetching, in-memory resampling and scoring.
    """
    import re
    import json
    import os
    import io
    from fastapi.responses import StreamingResponse
    from app.services.terrain_service import generate_risk_surface, render_risk_grid_to_png
    from app.services.satellite_service import resolve_scene_cache_dir
    
    # 1. Validate scene_id path parameter to prevent traversal
    if not re.match(r"^[a-zA-Z0-9_-]{30,80}$", scene_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid scene ID format."
        )
        
    # 2. Locate cached file to check if scene is processed
    cache_dir = resolve_scene_cache_dir(scene_id)
    if not cache_dir or not os.path.exists(cache_dir):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scene '{scene_id}' has not been processed yet."
        )
        
    slope_path = os.path.join(cache_dir, "slope_clipped.tif")
    dem_path = os.path.join(cache_dir, "dem_clipped.tif")
    if not os.path.exists(slope_path) or not os.path.exists(dem_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Terrain rasters (slope/dem) are missing for scene '{scene_id}'."
        )
        
    try:
        # 3. Generate risk grid and bounds
        risk_grid, bounds = generate_risk_surface(
            scene_id=scene_id,
            db_session=db,
            resolution=resolution,
            search_radius_km=10.0,
            rainfall=rainfall,
            rainfall_3d=rainfall_3d,
            rainfall_7d=rainfall_7d
        )
        
        # 4. Render to PNG bytes
        png_bytes = render_risk_grid_to_png(risk_grid)
        
        headers = {
            "X-Raster-Bounds": json.dumps(bounds),
            "Access-Control-Expose-Headers": "X-Raster-Bounds"
        }
        return StreamingResponse(io.BytesIO(png_bytes), media_type="image/png", headers=headers)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate spatial risk surface: {str(e)}"
        )
