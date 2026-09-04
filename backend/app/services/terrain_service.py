import os
import json
import math
import time
from datetime import datetime
from typing import Dict, Any, List, Optional
import threading
from collections import OrderedDict
import numpy as np
import rasterio
from rasterio.warp import calculate_default_transform, reproject, Resampling
from rasterio.merge import merge

class DEMDatasetCache:
    def __init__(self, max_size=12):
        self.max_size = max_size
        self.cache = OrderedDict()
        self.lock = threading.Lock()

    def get(self, url):
        with self.lock:
            if url in self.cache:
                self.cache.move_to_end(url)
                return self.cache[url]
            return None

    def put(self, url, dataset):
        with self.lock:
            if url in self.cache:
                self.cache.move_to_end(url)
                self.cache[url] = dataset
            else:
                self.cache[url] = dataset
                if len(self.cache) > self.max_size:
                    oldest_url, oldest_dataset = self.cache.popitem(last=False)
                    try:
                        oldest_dataset.close()
                    except:
                        pass

    def remove(self, url):
        with self.lock:
            if url in self.cache:
                dataset = self.cache.pop(url)
                try:
                    dataset.close()
                except:
                    pass

# Instantiate the thread-safe connection handle cache
dem_cache = DEMDatasetCache(max_size=12)

def get_tile_names_for_bbox(bbox: Dict[str, float]) -> List[str]:
    """
    Identifies all 1x1 degree Copernicus DEM GLO-30 tile IDs intersecting the bbox.
    bbox format: {"west": float, "south": float, "east": float, "north": float}
    """
    min_lon = int(math.floor(bbox["west"]))
    max_lon = int(math.floor(bbox["east"]))
    min_lat = int(math.floor(bbox["south"]))
    max_lat = int(math.floor(bbox["north"]))
    
    tiles = []
    for lat in range(min_lat, max_lat + 1):
        for lon in range(min_lon, max_lon + 1):
            ns = "N" if lat >= 0 else "S"
            ew = "E" if lon >= 0 else "W"
            tile_id = f"Copernicus_DSM_COG_10_{ns}{abs(lat):02d}_00_{ew}{abs(lon):03d}_00_DEM"
            tiles.append(tile_id)
    return tiles

def fetch_and_clip_dem(scene_id: str, bbox: Dict[str, float], aoi_key: Optional[str] = None) -> Dict[str, Any]:
    """
    Checks cache, retrieves/clips Copernicus DEM tiles anonymously via /vsicurl/,
    reprojects to UTM metric coordinate system, and calculates slope/aspect metrics.
    """
    # 1. Define paths and check cache first
    from app.services.satellite_service import resolve_scene_cache_dir
    cache_dir = resolve_scene_cache_dir(scene_id, aoi_key) or (os.path.join("data", "satellite_cache", scene_id, aoi_key) if aoi_key else os.path.join("data", "satellite_cache", scene_id))
    dem_path = os.path.join(cache_dir, "dem_clipped.tif")
    slope_path = os.path.join(cache_dir, "slope_clipped.tif")
    aspect_path = os.path.join(cache_dir, "aspect_clipped.tif")
    metadata_path = os.path.join(cache_dir, "metadata.json")

    # Check existing valid cache
    if os.path.exists(dem_path) and os.path.exists(slope_path) and os.path.exists(aspect_path) and os.path.exists(metadata_path):
        try:
            with open(metadata_path, "r") as f:
                meta = json.load(f)
            t_data = meta.get("terrain_data", {})
            if t_data.get("terrain_processing_status") == "success":
                return {
                    "status": "cached",
                    "scene_id": scene_id,
                    "dem_path": dem_path,
                    "slope_path": slope_path,
                    "aspect_path": aspect_path,
                    "statistics": {
                        "min_elevation": t_data.get("elevation_min"),
                        "max_elevation": t_data.get("elevation_max"),
                        "mean_elevation": t_data.get("elevation_mean"),
                        "min_slope": t_data.get("slope_min"),
                        "max_slope": t_data.get("slope_max"),
                        "mean_slope": t_data.get("slope_mean"),
                        "dominant_aspect": t_data.get("dominant_aspect")
                    },
                    "message": "Terrain metrics retrieved from local cache successfully."
                }
        except Exception:
            pass

    # Ensure cache directory exists
    os.makedirs(cache_dir, exist_ok=True)

    # 2. Get bounds from bbox
    bounds = (bbox["west"], bbox["south"], bbox["east"], bbox["north"])
    center_lon = (bbox["west"] + bbox["east"]) / 2.0

    # 3. Discover intersecting tiles
    tiles = get_tile_names_for_bbox(bbox)
    
    start_time = time.time()
    opened_files = []
    nodata_val = -32767.0
    src_crs = "EPSG:4326"

    # Open files virtually with vsicurl
    try:
        for tile_id in tiles:
            url = f"https://copernicus-dem-30m.s3.amazonaws.com/{tile_id}/{tile_id}.tif"
            vsicurl_url = f"/vsicurl/{url}"
            src = rasterio.open(vsicurl_url)
            opened_files.append(src)

        if not opened_files:
            raise ValueError(f"No elevation tiles could be opened for bbox: {bbox}")

        nodata_val = opened_files[0].nodata if (opened_files[0].nodata is not None) else -32767.0
        
        # Merge intersecting tiles and clip to bounds
        merged_array, merged_transform = merge(opened_files, bounds=bounds, nodata=nodata_val)
        merged_width = merged_array.shape[2]
        merged_height = merged_array.shape[1]

    except Exception as e:
        raise Exception(f"Failed to virtually fetch and merge DEM tiles: {str(e)}")
    finally:
        for src in opened_files:
            try:
                src.close()
            except:
                pass

    # 4. Dynamic UTM zone selection and metric Reprojection
    zone_number = int(math.floor((center_lon + 180) / 6)) + 1
    utm_epsg = 32600 + zone_number  # Northern hemisphere UTM Zone EPSG code
    dst_crs = f"EPSG:{utm_epsg}"

    try:
        # Calculate metric UTM transform
        dst_transform, dst_width, dst_height = calculate_default_transform(
            src_crs=src_crs,
            dst_crs=dst_crs,
            width=merged_width,
            height=merged_height,
            left=bounds[0],
            bottom=bounds[1],
            right=bounds[2],
            top=bounds[3]
        )

        dst_array = np.zeros((1, dst_height, dst_width), dtype=np.float32)

        # Reproject to UTM zone in meters
        reproject(
            source=merged_array,
            destination=dst_array,
            src_transform=merged_transform,
            src_crs=src_crs,
            dst_transform=dst_transform,
            dst_crs=dst_crs,
            resampling=Resampling.bilinear,
            src_nodata=nodata_val,
            dst_nodata=nodata_val
        )
    except Exception as e:
        raise Exception(f"Failed to reproject DEM to local UTM metric space {dst_crs}: {str(e)}")

    # 5. Slope & Aspect Calculations
    dx = dst_transform.a
    dy = -dst_transform.e  # transform.e is negative, invert to represent metric cell height

    elevation = dst_array[0]
    valid_mask = (elevation != nodata_val) & (~np.isnan(elevation))

    # Compute derivatives in meters
    dy_grad, dx_grad = np.gradient(elevation, dy, dx)
    dz_dx = dx_grad
    dz_dy = -dy_grad  # invert row direction gradient to match standard Y axis

    # Slope in degrees
    slope_rad = np.arctan(np.sqrt(dz_dx**2 + dz_dy**2))
    slope_deg = np.degrees(slope_rad)

    # Aspect in degrees
    aspect_rad = np.arctan2(dz_dy, -dz_dx)
    aspect_deg = (270.0 + np.degrees(aspect_rad)) % 360.0

    # Handle flat aspect conventionally as -1
    aspect_deg[slope_deg < 0.1] = -1.0

    # Mask invalid pixels
    slope_deg[~valid_mask] = nodata_val
    aspect_deg[~valid_mask] = nodata_val

    # 6. Calculate pixel statistics
    valid_elevations = elevation[valid_mask]
    valid_slopes = slope_deg[valid_mask & (slope_deg != nodata_val)]
    valid_aspects = aspect_deg[valid_mask & (aspect_deg != nodata_val) & (aspect_deg != -1.0)]

    if len(valid_elevations) > 0:
        elev_min = float(valid_elevations.min())
        elev_max = float(valid_elevations.max())
        elev_mean = float(valid_elevations.mean())
    else:
        elev_min = elev_max = elev_mean = 0.0

    if len(valid_slopes) > 0:
        slope_min = float(valid_slopes.min())
        slope_max = float(valid_slopes.max())
        slope_mean = float(valid_slopes.mean())
    else:
        slope_min = slope_max = slope_mean = 0.0

    # Dominant aspect calculation
    if len(valid_aspects) > 0:
        bins = [0, 22.5, 67.5, 112.5, 157.5, 202.5, 247.5, 292.5, 337.5, 360]
        counts, _ = np.histogram(valid_aspects, bins=bins)
        counts[0] += counts[-1]  # Combine North bins
        counts = counts[:-1]
        directions = ["North", "North-East", "East", "South-East", "South", "South-West", "West", "North-West"]
        dominant_aspect = directions[np.argmax(counts)]
    else:
        dominant_aspect = "Flat/Undefined"

    # 7. Write outputs to cache
    profile = {
        "driver": "GTiff",
        "dtype": "float32",
        "nodata": nodata_val,
        "width": dst_width,
        "height": dst_height,
        "count": 1,
        "crs": dst_crs,
        "transform": dst_transform,
        "compress": "lzw"
    }

    try:
        with rasterio.open(dem_path, "w", **profile) as dst:
            dst.write(elevation, 1)
        with rasterio.open(slope_path, "w", **profile) as dst:
            dst.write(slope_deg, 1)
        with rasterio.open(aspect_path, "w", **profile) as dst:
            dst.write(aspect_deg, 1)
    except Exception as e:
        # Cleanup
        for p in (dem_path, slope_path, aspect_path):
            if os.path.exists(p):
                try:
                    os.remove(p)
                except:
                    pass
        raise Exception(f"Failed to save terrain rasters to cache: {str(e)}")

    # 8. Update existing metadata.json
    terrain_meta = {
        "dem_source": "Copernicus DEM GLO-30 AWS Open Data",
        "dem_tiles": tiles,
        "dem_crs": src_crs,
        "output_crs": dst_crs,
        "elevation_min": round(elev_min, 2),
        "elevation_max": round(elev_max, 2),
        "elevation_mean": round(elev_mean, 2),
        "slope_min": round(slope_min, 2),
        "slope_max": round(slope_max, 2),
        "slope_mean": round(slope_mean, 2),
        "dominant_aspect": dominant_aspect,
        "output_width": dst_width,
        "output_height": dst_height,
        "dem_file_size": os.path.getsize(dem_path),
        "slope_file_size": os.path.getsize(slope_path),
        "aspect_file_size": os.path.getsize(aspect_path),
        "terrain_processing_timestamp": datetime.utcnow().isoformat() + "Z",
        "terrain_processing_status": "success"
    }

    existing_meta = {}
    if os.path.exists(metadata_path):
        try:
            with open(metadata_path, "r") as f:
                existing_meta = json.load(f)
        except:
            pass

    existing_meta["terrain_data"] = terrain_meta

    with open(metadata_path, "w") as f:
        json.dump(existing_meta, f, indent=2)

    return {
        "status": "success",
        "scene_id": scene_id,
        "dem_path": dem_path,
        "slope_path": slope_path,
        "aspect_path": aspect_path,
        "statistics": {
            "min_elevation": round(elev_min, 2),
            "max_elevation": round(elev_max, 2),
            "mean_elevation": round(elev_mean, 2),
            "min_slope": round(slope_min, 2),
            "max_slope": round(slope_max, 2),
            "mean_slope": round(slope_mean, 2),
            "dominant_aspect": dominant_aspect
        },
        "message": f"Successfully clipped DEM & calculated slope/aspect in {time.time() - start_time:.1f}s."
    }

def render_raster_to_png(tif_path: str, layer_type: str) -> tuple:
    """
    Reads a single-band GeoTIFF, virtually reprojects it to EPSG:4326 on the fly,
    normalizes and colormaps the values into a transparent RGBA PNG, and
    returns the PNG bytes alongside the geographic bounding box [[south, west], [north, east]].
    """
    import os
    import json
    import numpy as np
    import rasterio
    from rasterio.vrt import WarpedVRT
    from rasterio.io import MemoryFile
    from rasterio.transform import from_bounds
    
    if not os.path.exists(tif_path):
        raise FileNotFoundError(f"Raster file not found: {tif_path}")
        
    cache_dir = os.path.dirname(tif_path)
    metadata_path = os.path.join(cache_dir, "metadata.json")
    clipping_bounds = None
    if os.path.exists(metadata_path):
        try:
            with open(metadata_path, "r") as f:
                meta = json.load(f)
            clipping_bounds = meta.get("clipping_bounds")
        except:
            pass
            
    with rasterio.open(tif_path) as src:
        if clipping_bounds:
            west = clipping_bounds["west"]
            south = clipping_bounds["south"]
            east = clipping_bounds["east"]
            north = clipping_bounds["north"]
            vrt_width = src.width
            vrt_height = src.height
            dst_transform = from_bounds(west, south, east, north, vrt_width, vrt_height)
            vrt_context = WarpedVRT(src, crs="EPSG:4326", transform=dst_transform, width=vrt_width, height=vrt_height)
            bounds = [
                [south, west],
                [north, east]
            ]
        else:
            vrt_context = WarpedVRT(src, crs="EPSG:4326")
            bounds = None
            
        with vrt_context as vrt:
            if not bounds:
                bounds = [
                    [vrt.bounds.bottom, vrt.bounds.left],
                    [vrt.bounds.top, vrt.bounds.right]
                ]
            data = vrt.read(1)
            nodata = vrt.nodata
            
            # Clean data (replace nan with nodata)
            if nodata is not None:
                data = np.nan_to_num(data, nan=nodata)
            else:
                data = np.nan_to_num(data, nan=0.0)
                nodata = 0.0
                
            height, width = data.shape
            
            # Create RGBA array (4, height, width)
            rgba = np.zeros((4, height, width), dtype=np.uint8)
            
            # Mask invalid/nodata pixels
            valid_mask = (data != nodata) & (~np.isnan(data))
            
            if layer_type == "slope":
                # Slope colormap: Yellow-Orange-Red
                # Clamp slope to [0, 50]
                normalized = np.clip(data, 0.0, 50.0) / 50.0
                
                r = np.zeros_like(data, dtype=np.uint8)
                g = np.zeros_like(data, dtype=np.uint8)
                b = np.zeros_like(data, dtype=np.uint8)
                a = np.zeros_like(data, dtype=np.uint8)
                
                # Piecewise interpolation for smooth colormap
                mask1 = valid_mask & (normalized < 0.33)
                f1 = normalized[mask1] / 0.33
                r[mask1] = (255 * (1 - f1) + 254 * f1).astype(np.uint8)
                g[mask1] = (255 * (1 - f1) + 141 * f1).astype(np.uint8)
                b[mask1] = (178 * (1 - f1) + 60 * f1).astype(np.uint8)
                a[mask1] = (120 + 40 * f1).astype(np.uint8)
                
                mask2 = valid_mask & (normalized >= 0.33) & (normalized < 0.66)
                f2 = (normalized[mask2] - 0.33) / 0.33
                r[mask2] = (254 * (1 - f2) + 240 * f2).astype(np.uint8)
                g[mask2] = (141 * (1 - f2) + 59 * f2).astype(np.uint8)
                b[mask2] = (60 * (1 - f2) + 32 * f2).astype(np.uint8)
                a[mask2] = (160 + 40 * f2).astype(np.uint8)
                
                mask3 = valid_mask & (normalized >= 0.66)
                f3 = (normalized[mask3] - 0.66) / 0.34
                r[mask3] = (240 * (1 - f3) + 189 * f3).astype(np.uint8)
                g[mask3] = (59 * (1 - f3) + 0 * f3).astype(np.uint8)
                b[mask3] = (32 * (1 - f3) + 38 * f3).astype(np.uint8)
                a[mask3] = (200 + 40 * f3).astype(np.uint8)
                
                rgba[0] = r
                rgba[1] = g
                rgba[2] = b
                rgba[3] = a
                
            elif layer_type == "dem":
                # DEM colormap: Terrain elevation
                # Normalize actual elevations in this scene
                valid_data = data[valid_mask]
                if len(valid_data) > 0:
                    min_val = valid_data.min()
                    max_val = valid_data.max()
                    rng = max_val - min_val if max_val > min_val else 1.0
                    normalized = (data - min_val) / rng
                else:
                    normalized = np.zeros_like(data)
                
                r = np.zeros_like(data, dtype=np.uint8)
                g = np.zeros_like(data, dtype=np.uint8)
                b = np.zeros_like(data, dtype=np.uint8)
                a = np.zeros_like(data, dtype=np.uint8)
                
                # Green to LightBrown: t in [0, 0.5]
                mask1 = valid_mask & (normalized < 0.5)
                f1 = normalized[mask1] / 0.5
                r[mask1] = (34 * (1 - f1) + 160 * f1).astype(np.uint8)
                g[mask1] = (139 * (1 - f1) + 120 * f1).astype(np.uint8)
                b[mask1] = (34 * (1 - f1) + 90 * f1).astype(np.uint8)
                a[mask1] = 160
                
                # LightBrown to DarkBrown: t in [0.5, 0.8]
                mask2 = valid_mask & (normalized >= 0.5) & (normalized < 0.8)
                f2 = (normalized[mask2] - 0.5) / 0.3
                r[mask2] = (160 * (1 - f2) + 110 * f2).astype(np.uint8)
                g[mask2] = (120 * (1 - f2) + 85 * f2).astype(np.uint8)
                b[mask2] = (90 * (1 - f2) + 60 * f2).astype(np.uint8)
                a[mask2] = 180
                
                # DarkBrown to White: t in [0.8, 1.0]
                mask3 = valid_mask & (normalized >= 0.8)
                f3 = (normalized[mask3] - 0.8) / 0.2
                r[mask3] = (110 * (1 - f3) + 245 * f3).astype(np.uint8)
                g[mask3] = (85 * (1 - f3) + 245 * f3).astype(np.uint8)
                b[mask3] = (60 * (1 - f3) + 245 * f3).astype(np.uint8)
                a[mask3] = (180 + 75 * f3).astype(np.uint8)
                
                rgba[0] = r
                rgba[1] = g
                rgba[2] = b
                rgba[3] = a
                
            elif layer_type == "aspect":
                # Aspect colormap: Circular color wheel representing directions
                # -1 = Flat, 0-360 = angle
                r = np.zeros_like(data, dtype=np.uint8)
                g = np.zeros_like(data, dtype=np.uint8)
                b = np.zeros_like(data, dtype=np.uint8)
                a = np.zeros_like(data, dtype=np.uint8)
                
                # Flat aspect (-1.0)
                flat_mask = valid_mask & (data == -1.0)
                r[flat_mask] = 128
                g[flat_mask] = 128
                b[flat_mask] = 128
                a[flat_mask] = 100
                
                # Angular colors (North Red, East Yellow, South Green, West Blue)
                ang_mask = valid_mask & (data != -1.0)
                angles = data[ang_mask]
                rads = np.radians(angles)
                
                r[ang_mask] = (127.5 * (1.0 + np.cos(rads))).astype(np.uint8)
                g[ang_mask] = (127.5 * (1.0 + np.sin(rads))).astype(np.uint8)
                b[ang_mask] = (127.5 * (1.0 - np.cos(rads))).astype(np.uint8)
                a[ang_mask] = 150
                
                rgba[0] = r
                rgba[1] = g
                rgba[2] = b
                rgba[3] = a
                
            elif layer_type in ("vv", "vh"):
                # Sentinel-1 Backscatter (decibels)
                # Max range clamp
                min_val = -25.0 if layer_type == "vv" else -30.0
                max_val = 0.0 if layer_type == "vv" else -5.0
                rng = max_val - min_val
                
                normalized = np.clip(data, min_val, max_val)
                normalized = (normalized - min_val) / rng
                
                # Grayscale mapping (Radar visualization)
                gray = (normalized * 255).astype(np.uint8)
                
                rgba[0] = gray
                rgba[1] = gray
                rgba[2] = gray
                rgba[3] = np.where(valid_mask, 180, 0).astype(np.uint8)
                
            # Geographic bounds are already computed above
            
            # Write RGBA matrix using rasterio PNG driver
            with MemoryFile() as memfile:
                with memfile.open(
                    driver="PNG",
                    width=width,
                    height=height,
                    count=4,
                    dtype="uint8"
                ) as dst:
                    dst.write(rgba)
                png_bytes = memfile.read()
                
            return png_bytes, bounds

def generate_risk_surface(
    scene_id: str,
    db_session,
    resolution: int = 25,
    search_radius_km: float = 10.0,
    rainfall: float = None,
    rainfall_3d: float = None,
    rainfall_7d: float = None,
    aoi_key: Optional[str] = None
) -> tuple:
    """
    Generates a spatial landslide susceptibility grid over the AOI from cached slope/elevation
    rasters and in-memory pre-fetched historical landslides.
    """
    import os
    import math
    import numpy as np
    import rasterio
    from rasterio.vrt import WarpedVRT
    from rasterio.enums import Resampling
    from app.models.historical_landslide import GSILandslideIncident, NASALandslideEvent
    from app.services.spatial_query_service import haversine_distance
    from app.services.satellite_service import resolve_scene_cache_dir
    
    cache_dir = resolve_scene_cache_dir(scene_id, aoi_key) or os.path.join("data", "satellite_cache", scene_id)
    slope_path = os.path.join(cache_dir, "slope_clipped.tif")
    dem_path = os.path.join(cache_dir, "dem_clipped.tif")
    aspect_path = os.path.join(cache_dir, "aspect_clipped.tif")
    vv_path = os.path.join(cache_dir, "vv_clipped.tif")
    vh_path = os.path.join(cache_dir, "vh_clipped.tif")
    
    if not os.path.exists(slope_path) or not os.path.exists(dem_path):
        raise FileNotFoundError(f"Terrain rasters not found in cache for scene {scene_id}")
        
    import json
    from rasterio.transform import from_bounds
    
    metadata_path = os.path.join(cache_dir, "metadata.json")
    clipping_bounds = None
    if os.path.exists(metadata_path):
        try:
            with open(metadata_path, "r") as f:
                meta = json.load(f)
            clipping_bounds = meta.get("clipping_bounds")
        except:
            pass

    # 1. Open rasters once and resample directly to target resolution
    with rasterio.open(slope_path) as src_slope, rasterio.open(dem_path) as src_dem:
        if clipping_bounds:
            west = clipping_bounds["west"]
            south = clipping_bounds["south"]
            east = clipping_bounds["east"]
            north = clipping_bounds["north"]
            vrt_width = src_slope.width
            vrt_height = src_slope.height
            dst_transform = from_bounds(west, south, east, north, vrt_width, vrt_height)
            vrt_slope_ctx = WarpedVRT(src_slope, crs="EPSG:4326", transform=dst_transform, width=vrt_width, height=vrt_height)
            vrt_dem_ctx = WarpedVRT(src_dem, crs="EPSG:4326", transform=dst_transform, width=vrt_width, height=vrt_height)
            bounds = [
                [south, west],
                [north, east]
            ]
        else:
            vrt_slope_ctx = WarpedVRT(src_slope, crs="EPSG:4326")
            vrt_dem_ctx = WarpedVRT(src_dem, crs="EPSG:4326")
            bounds = None

        with vrt_slope_ctx as vrt_slope, vrt_dem_ctx as vrt_dem:
            if not bounds:
                bounds = [
                    [vrt_slope.bounds.bottom, vrt_slope.bounds.left],
                    [vrt_slope.bounds.top, vrt_slope.bounds.right]
                ]
                west, south, east, north = vrt_slope.bounds.left, vrt_slope.bounds.bottom, vrt_slope.bounds.right, vrt_slope.bounds.top
            
            slope_grid = vrt_slope.read(1, out_shape=(resolution, resolution), resampling=Resampling.nearest)
            dem_grid = vrt_dem.read(1, out_shape=(resolution, resolution), resampling=Resampling.nearest)
            
            nodata_slope = src_slope.nodata if src_slope.nodata is not None else -32767.0
            nodata_dem = src_dem.nodata if src_dem.nodata is not None else -32767.0
            
    # 2. Optimized Historical Landslide pre-fetching
    # Calculate expanded query bounding box to catch any nearby landslides
    lat_degree_km = 111.1
    delta_lat = search_radius_km / lat_degree_km
    cos_lat = math.cos(math.radians((south + north) / 2.0))
    delta_lon = search_radius_km / (lat_degree_km * cos_lat) if cos_lat > 0.0001 else delta_lat
    
    south_q = south - delta_lat
    north_q = north + delta_lat
    west_q = west - delta_lon
    east_q = east + delta_lon
    
    # Run database query only once per table
    gsi_candidates = (
        db_session.query(GSILandslideIncident.latitude, GSILandslideIncident.longitude)
        .filter(GSILandslideIncident.latitude.between(south_q, north_q))
        .filter(GSILandslideIncident.longitude.between(west_q, east_q))
        .all()
    )
    nasa_candidates = (
        db_session.query(NASALandslideEvent.latitude, NASALandslideEvent.longitude)
        .filter(NASALandslideEvent.latitude.between(south_q, north_q))
        .filter(NASALandslideEvent.longitude.between(west_q, east_q))
        .all()
    )
    
    # Combine coordinate candidate pools in-memory
    landslide_points = []
    for lat, lon in gsi_candidates + nasa_candidates:
        if lat is not None and lon is not None:
            landslide_points.append((lat, lon))
            
    # 3. Cell calculation loop (vector/in-memory only)
    risk_grid = np.full((resolution, resolution), np.nan, dtype=np.float32)
    
    delta_y = (north - south) / resolution
    delta_x = (east - west) / resolution
    
    # Calculate rainfall score if rainfall is provided
    # Reuses susceptibility service math
    rainfall_score = 0.0
    rainfall_max = 0.0
    if rainfall is not None or rainfall_3d is not None or rainfall_7d is not None:
        # Multi-timescale rainfall calculation
        r_daily = rainfall if rainfall is not None else 0.0
        r_3d = rainfall_3d if rainfall_3d is not None else 0.0
        r_7d = rainfall_7d if rainfall_7d is not None else 0.0
        
        # Daily intensity score (Max 10)
        daily_score = 0.0
        if r_daily >= 50.0:
            daily_score = 10.0
        elif r_daily >= 10.0:
            daily_score = 5.0
            
        # 3-day cumulative score (Max 10)
        three_day_score = 0.0
        if r_3d >= 100.0:
            three_day_score = 10.0
        elif r_3d >= 30.0:
            three_day_score = 5.0
            
        # 7-day cumulative score (Max 10)
        seven_day_score = 0.0
        if r_7d >= 150.0:
            seven_day_score = 10.0
        elif r_7d >= 50.0:
            seven_day_score = 5.0
            
        # Combine
        total_precip_score = daily_score + three_day_score + seven_day_score
        
        # Max normalisation parameter for compatibility vs multi_timescale
        if rainfall is not None and rainfall_3d is None and rainfall_7d is None:
            # Compatibility mode: single 24h precipitation
            # 24h score is max 30
            compat_score = 0.0
            if r_daily >= 50.0:
                compat_score = 30.0
            elif r_daily >= 10.0:
                compat_score = 15.0
            rainfall_score = compat_score
            rainfall_max = 30.0
        else:
            # Multi-timescale mode
            # If all are present, max score is 30. If some are missing, normalize.
            avail_max = 0.0
            if rainfall is not None: avail_max += 10.0
            if rainfall_3d is not None: avail_max += 10.0
            if rainfall_7d is not None: avail_max += 10.0
            
            rainfall_score = total_precip_score
            rainfall_max = avail_max

    # Compute risk score for each cell
    for r in range(resolution):
        # Row 0 is at the top (North), so subtract
        cell_lat = north - (r + 0.5) * delta_y
        for c in range(resolution):
            cell_lon = west + (c + 0.5) * delta_x
            
            slope_val = slope_grid[r, c]
            dem_val = dem_grid[r, c]
            
            # Check nodata or nan
            if np.isnan(slope_val) or np.isnan(dem_val) or slope_val == nodata_slope or dem_val == nodata_dem:
                continue
                
            # In-memory proximity & density calculations
            dists = []
            for lat_l, lon_l in landslide_points:
                dists.append(haversine_distance(cell_lat, cell_lon, lat_l, lon_l))
                
            nearest_dist = min(dists) if dists else None
            total_obs = sum(1 for d in dists if d <= search_radius_km)
            
            # Proximity Score (Max 25)
            if total_obs == 0 or nearest_dist is None:
                proximity_score = 0.0
            else:
                proximity_score = 25.0 * (1.0 - min(nearest_dist / search_radius_km, 1.0))
            proximity_score = max(0.0, min(25.0, proximity_score))
            
            # Density Score (Max 15)
            if total_obs == 0:
                density_score = 0.0
            else:
                density_score = 15.0 * math.log(total_obs + 1) / math.log(21.0)
            density_score = max(0.0, min(15.0, density_score))
            
            historical_score = proximity_score + density_score
            
            # Terrain Score (Max 30)
            if slope_val < 15.0:
                terrain_score = 5.0
            elif slope_val <= 30.0:
                terrain_score = 18.0
            else:
                terrain_score = 30.0
                
            # Combine static scores (Historical + Terrain)
            combined_score = historical_score + terrain_score
            combined_max = 70.0
            
            # Add dynamic rainfall if supplied
            cell_score = combined_score + rainfall_score
            cell_max = combined_max + rainfall_max
            
            # Normalise to 0-100 scale
            normalized_score = 100.0 * (cell_score / cell_max)
            risk_grid[r, c] = max(0.0, min(100.0, normalized_score))
            
    return risk_grid, bounds

def extract_point_terrain(latitude: float, longitude: float) -> dict:
    """
    Extracts elevation, slope, and aspect for a single coordinate by virtually
    opening the corresponding Copernicus GLO-30 DEM tile, reading a 3x3 window,
    and calculating derivatives.
    """
    tile_lat = int(math.floor(latitude))
    tile_lon = int(math.floor(longitude))
    ns = "N" if tile_lat >= 0 else "S"
    ew = "E" if tile_lon >= 0 else "W"
    tile_id = f"Copernicus_DSM_COG_10_{ns}{abs(tile_lat):02d}_00_{ew}{abs(tile_lon):03d}_00_DEM"
    
    url = f"https://copernicus-dem-30m.s3.amazonaws.com/{tile_id}/{tile_id}.tif"
    vsicurl_url = f"/vsicurl/{url}"
    
    col_float = (longitude - tile_lon) * 3600.0
    row_float = (tile_lat + 1.0 - latitude) * 3600.0
    col = int(col_float)
    row = int(row_float)
    
    # Boundary padding check
    col = max(1, min(3598, col))
    row = max(1, min(3598, row))
    
    src = dem_cache.get(vsicurl_url)
    retries = 1
    elev_window = None
    nodata_val = -32767.0
    
    while retries >= 0:
        if src is None:
            try:
                src = rasterio.open(vsicurl_url)
                dem_cache.put(vsicurl_url, src)
            except Exception as e:
                raise FileNotFoundError(f"Failed to virtually open elevation tile {tile_id}: {str(e)}")
                
        try:
            nodata_val = src.nodata if src.nodata is not None else -32767.0
            window = rasterio.windows.Window(col - 1, row - 1, 3, 3)
            elev_window = src.read(1, window=window)
            break
        except Exception as e:
            dem_cache.remove(vsicurl_url)
            src = None
            retries -= 1
            if retries < 0:
                raise IOError(f"Failed to read from elevation tile {tile_id} after retry: {str(e)}")
        
    if elev_window.shape != (3, 3):
        raise ValueError(f"Extracted elevation window shape {elev_window.shape} is invalid.")
        
    elev = float(elev_window[1, 1])
    if elev == nodata_val or np.isnan(elev) or elev < -500.0:
        raise ValueError(f"Point coordinate contains NoData or invalid elevation values.")
        
    if np.any(elev_window == nodata_val) or np.any(np.isnan(elev_window)):
        raise ValueError(f"Neighboring pixels contain NoData or invalid values; cannot compute derivatives.")
        
    # Spacing calculations
    dy = 30.87
    dx = 30.87 * math.cos(math.radians(latitude))
    
    z11, z12, z13 = float(elev_window[0, 0]), float(elev_window[0, 1]), float(elev_window[0, 2])
    z21, z22, z23 = float(elev_window[1, 0]), float(elev_window[1, 1]), float(elev_window[1, 2])
    z31, z32, z33 = float(elev_window[2, 0]), float(elev_window[2, 1]), float(elev_window[2, 2])
    
    # Horn's method
    dz_dx = ((z13 + 2.0*z23 + z33) - (z11 + 2.0*z21 + z31)) / (8.0 * dx)
    dz_dy = ((z31 + 2.0*z32 + z33) - (z11 + 2.0*z12 + z13)) / (8.0 * dy)
    
    slope_rad = math.atan(math.sqrt(dz_dx**2 + dz_dy**2))
    slope = math.degrees(slope_rad)
    
    aspect_rad = math.atan2(dz_dy, -dz_dx)
    aspect = (270.0 + math.degrees(aspect_rad)) % 360.0
    
    if slope < 0.1:
        aspect = -1.0
        
    return {
        "elevation": round(elev, 2),
        "slope": round(slope, 4),
        "aspect": round(aspect, 2)
    }

def render_risk_grid_to_png(risk_grid: np.ndarray) -> bytes:
    """
    Renders a 2D risk susceptibility grid into a transparent RGBA PNG byte stream.
    Uses Green -> Yellow -> Orange -> Red -> DarkRed hazard gradient scale.
    """
    import numpy as np
    from rasterio.io import MemoryFile
    
    height, width = risk_grid.shape
    rgba = np.zeros((4, height, width), dtype=np.uint8)
    
    for r in range(height):
        for c in range(width):
            val = risk_grid[r, c]
            if np.isnan(val) or val < 0.0:
                rgba[0, r, c] = 0
                rgba[1, r, c] = 0
                rgba[2, r, c] = 0
                rgba[3, r, c] = 0
            else:
                # Normalise val between 0 and 100
                t = max(0.0, min(100.0, val)) / 100.0
                
                # Piecewise color mapping: Green -> Yellow -> Orange -> Red -> DarkRed
                if t < 0.25:
                    f = t / 0.25
                    rgba[0, r, c] = int(34 * (1 - f) + 251 * f)
                    rgba[1, r, c] = int(139 * (1 - f) + 192 * f)
                    rgba[2, r, c] = int(34 * (1 - f) + 45 * f)
                    rgba[3, r, c] = int(100 + 40 * f) # transparency starts at 100
                elif t < 0.50:
                    f = (t - 0.25) / 0.25
                    rgba[0, r, c] = int(251 * (1 - f) + 245 * f)
                    rgba[1, r, c] = int(192 * (1 - f) + 124 * f)
                    rgba[2, r, c] = int(45 * (1 - f) + 0 * f)
                    rgba[3, r, c] = int(140 + 40 * f)
                elif t < 0.75:
                    f = (t - 0.50) / 0.25
                    rgba[0, r, c] = int(245 * (1 - f) + 211 * f)
                    rgba[1, r, c] = int(124 * (1 - f) + 47 * f)
                    rgba[2, r, c] = int(0 * (1 - f) + 47 * f)
                    rgba[3, r, c] = int(180 + 40 * f)
                else:
                    f = (t - 0.75) / 0.25
                    rgba[0, r, c] = int(211 * (1 - f) + 136 * f)
                    rgba[1, r, c] = int(47 * (1 - f) + 0 * f)
                    rgba[2, r, c] = int(47 * (1 - f) + 21 * f)
                    rgba[3, r, c] = int(200 + 55 * f) # solid at high values
                    
    # Write using rasterio PNG driver
    with MemoryFile() as memfile:
        with memfile.open(
            driver="PNG",
            width=width,
            height=height,
            count=4,
            dtype="uint8"
        ) as dst:
            dst.write(rgba)
        png_bytes = memfile.read()
        
    return png_bytes


# ---------------------------------------------------------------------------
# Phase 3.1: Point-based Terrain & Slope Analysis
# ---------------------------------------------------------------------------

def classify_terrain_risk(slope_degrees: float) -> str:
    """
    Classifies terrain slope into operational landslide risk levels:
    - 0 to 10 degrees -> LOW
    - 10 to 25 degrees -> MODERATE
    - 25 to 40 degrees -> HIGH
    - Above 40 degrees -> VERY_HIGH
    """
    if slope_degrees < 10.0:
        return "LOW"
    elif slope_degrees <= 25.0:
        return "MODERATE"
    elif slope_degrees <= 40.0:
        return "HIGH"
    else:
        return "VERY_HIGH"


def fetch_elevation_batch_open_meteo(coordinates: List[tuple]) -> List[float]:
    """
    Queries the free Open-Meteo elevation API for a batch of (latitude, longitude) tuples.
    Returns a list of elevation values in meters.
    """
    import httpx

    if not coordinates:
        return []

    lats = ",".join(f"{c[0]:.6f}" for c in coordinates)
    lons = ",".join(f"{c[1]:.6f}" for c in coordinates)
    url = f"https://api.open-meteo.com/v1/elevation?latitude={lats}&longitude={lons}"

    try:
        with httpx.Client(timeout=8.0) as client:
            resp = client.get(url)
            if resp.status_code == 200:
                data = resp.json()
                elevations = data.get("elevation", [])
                if isinstance(elevations, list) and len(elevations) == len(coordinates):
                    return [float(e) for e in elevations]
    except Exception:
        # Fallback to secondary provider if request fails
        pass
    return []


def fetch_elevation_batch_open_elevation(coordinates: List[tuple]) -> List[float]:
    """
    Secondary fallback: Queries Open-Elevation API for a batch of coordinates.
    """
    import httpx

    if not coordinates:
        return []

    payload = {"locations": [{"latitude": c[0], "longitude": c[1]} for c in coordinates]}
    url = "https://api.open-elevation.com/api/v1/lookup"

    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.post(url, json=payload)
            if resp.status_code == 200:
                data = resp.json()
                results = data.get("results", [])
                if len(results) == len(coordinates):
                    return [float(r.get("elevation", 0.0)) for r in results]
    except Exception:
        pass
    return []


def analyze_point_terrain(latitude: float, longitude: float, sample_radius_meters: float = 30.0) -> Dict[str, Any]:
    """
    Performs Phase 3.1 Terrain and Slope Analysis:
    1. Validates coordinate bounds.
    2. Generates a 3x3 local sampling stencil (center + 8 compass neighbors) spaced by sample_radius_meters.
    3. Fetches elevation data using reliable free elevation APIs (Open-Meteo with fallback).
    4. Computes terrain gradient and slope in degrees using Horn's weighted finite-difference method.
    5. Determines terrain risk classification (LOW, MODERATE, HIGH, VERY_HIGH).
    
    Returns structured dict:
    - latitude: float
    - longitude: float
    - elevation_meters: float
    - slope_degrees: float
    - terrain_risk_level: str
    """
    # 1. Validate coordinate bounds
    if not (-90.0 <= latitude <= 90.0):
        raise ValueError(f"Latitude {latitude} is outside valid range [-90.0, 90.0].")
    if not (-180.0 <= longitude <= 180.0):
        raise ValueError(f"Longitude {longitude} is outside valid range [-180.0, 180.0].")

    # 2. Compute local sampling offsets (meters to degrees)
    d = max(10.0, min(100.0, sample_radius_meters))
    lat_rad = math.radians(latitude)
    cos_lat = math.cos(lat_rad)
    if cos_lat < 0.0001:
        cos_lat = 0.0001

    d_lat = d / 111139.0
    d_lon = d / (111139.0 * cos_lat)

    # 3x3 grid sampling coordinates:
    # [0] NW, [1] N, [2] NE
    # [3] W,  [4] C, [5] E
    # [6] SW, [7] S, [8] SE
    grid_coords = [
        (latitude + d_lat, longitude - d_lon),
        (latitude + d_lat, longitude),
        (latitude + d_lat, longitude + d_lon),
        (latitude, longitude - d_lon),
        (latitude, longitude),
        (latitude, longitude + d_lon),
        (latitude - d_lat, longitude - d_lon),
        (latitude - d_lat, longitude),
        (latitude - d_lat, longitude + d_lon),
    ]

    # 3. Fetch elevations via primary provider (Open-Meteo)
    elevations = fetch_elevation_batch_open_meteo(grid_coords)

    # Fallback to secondary provider if primary fails
    if not elevations or len(elevations) != 9:
        elevations = fetch_elevation_batch_open_elevation(grid_coords)

    # Fallback to local Copernicus GLO-30 virtual DEM raster extraction if online APIs are unavailable
    if not elevations or len(elevations) != 9:
        try:
            pt_res = extract_point_terrain(latitude, longitude)
            elev = float(pt_res.get("elevation", 0.0))
            slope = float(pt_res.get("slope", 0.0))
            risk_level = classify_terrain_risk(slope)
            return {
                "latitude": round(latitude, 6),
                "longitude": round(longitude, 6),
                "elevation_meters": round(elev, 2),
                "slope_degrees": round(slope, 2),
                "terrain_risk_level": risk_level
            }
        except Exception as dem_err:
            raise RuntimeError(f"Unable to retrieve elevation from online services or local DEM: {str(dem_err)}")

    # 4. Calculate finite differences using Horn's 3x3 weighted stencil
    z_nw, z_n, z_ne = elevations[0], elevations[1], elevations[2]
    z_w,  z_c, z_e  = elevations[3], elevations[4], elevations[5]
    z_sw, z_s, z_se = elevations[6], elevations[7], elevations[8]

    dx = d
    dy = d

    dz_dx = ((z_ne + 2.0 * z_e + z_se) - (z_nw + 2.0 * z_w + z_sw)) / (8.0 * dx)
    dz_dy = ((z_nw + 2.0 * z_n + z_ne) - (z_sw + 2.0 * z_s + z_se)) / (8.0 * dy)

    slope_rad = math.atan(math.sqrt(dz_dx**2 + dz_dy**2))
    slope_deg = round(math.degrees(slope_rad), 2)
    center_elevation = round(float(z_c), 2)

    # 5. Classify terrain risk level
    risk_level = classify_terrain_risk(slope_deg)

    return {
        "latitude": round(latitude, 6),
        "longitude": round(longitude, 6),
        "elevation_meters": center_elevation,
        "slope_degrees": slope_deg,
        "terrain_risk_level": risk_level
    }

