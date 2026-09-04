import urllib.request
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from app.services.aoi_service import calculate_aoi

STAC_SEARCH_URL = "https://stac.dataspace.copernicus.eu/v1/search"

def query_copernicus_stac(
    latitude: float,
    longitude: float,
    radius_km: float = 5.0,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 10,
    collection: str = "sentinel-1-grd"
) -> List[Dict[str, Any]]:
    """
    Queries the official Copernicus Data Space Ecosystem STAC API for Sentinel scenes
    covering the calculated AOI bounding box.
    """
    # 1. Generate the geographically-scaled AOI bounding box
    aoi_data = calculate_aoi(latitude, longitude, radius_km)
    bbox_coords = aoi_data["bounding_box"]
    
    # STAC bbox format is [west, south, east, north] (min_lon, min_lat, max_lon, max_lat)
    stac_bbox = [
        bbox_coords["west"],
        bbox_coords["south"],
        bbox_coords["east"],
        bbox_coords["north"]
    ]

    # 2. Configure dates
    # If no dates are provided, default to the last 30 days
    if not end_date:
        end_date = datetime.utcnow().strftime("%Y-%m-%d")
    if not start_date:
        # 30 days ago
        start_date = (datetime.utcnow() - timedelta(days=30)).strftime("%Y-%m-%d")

    # Format datetime as ISO interval "start/end"
    datetime_interval = f"{start_date}T00:00:00Z/{end_date}T23:59:59Z"

    # 3. Construct the STAC query
    stac_query = {
        "bbox": stac_bbox,
        "datetime": datetime_interval,
        "collections": [collection],
        "limit": min(limit, 100) # Safeguard max count
    }

    # 4. Execute the HTTP request using python standard library
    req = urllib.request.Request(
        STAC_SEARCH_URL,
        data=json.dumps(stac_query).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            features = res_data.get("features", [])
            
            parsed_scenes = []
            for feat in features:
                props = feat.get("properties", {})
                
                # Extract clean metadata properties mapping standard STAC extensions
                product_type = props.get("sar:product_type") or props.get("product_type") or "GRD"
                orbit_direction = props.get("sat:orbit_state") or props.get("orbit_direction") or "unknown"
                platform = props.get("platform") or "sentinel-1"
                
                scene_item = {
                    "id": feat.get("id"),
                    "collection": feat.get("collection") or collection,
                    "datetime": props.get("datetime"),
                    "platform": platform,
                    "product_type": product_type,
                    "orbit_direction": orbit_direction,
                    "geometry": feat.get("geometry"),
                    "bbox": feat.get("bbox")
                }
                parsed_scenes.append(scene_item)
                
            return parsed_scenes

    except urllib.error.URLError as e:
        # Propagate error message
        raise Exception(f"Failed to connect to Copernicus STAC API: {e}")
    except Exception as e:
        raise Exception(f"Error parsing Copernicus STAC response: {e}")

def get_scene_detail(scene_id: str, collection_id: str = "sentinel-1-grd") -> Dict[str, Any]:
    """
    Fetches the detail metadata for a specific Copernicus STAC item by ID.
    Parses assets, mapping files to a clean serialized structure.
    """
    item_url = f"https://stac.dataspace.copernicus.eu/v1/collections/{collection_id}/items/{scene_id}"
    
    req = urllib.request.Request(
        item_url,
        method="GET"
    )
    
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            props = res_data.get("properties", {})
            
            product_type = props.get("sar:product_type") or props.get("product_type") or "GRD"
            orbit_direction = props.get("sat:orbit_state") or props.get("orbit_direction") or "unknown"
            platform = props.get("platform") or "sentinel-1"
            
            raw_assets = res_data.get("assets", {})
            parsed_assets = []
            for key, val in raw_assets.items():
                asset_item = {
                    "key": key,
                    "title": val.get("title") or key,
                    "type": val.get("type"),
                    "roles": val.get("roles"),
                    "href": val.get("href"),
                    "size": val.get("file:size") or val.get("size")
                }
                parsed_assets.append(asset_item)
                
            return {
                "id": res_data.get("id"),
                "collection": res_data.get("collection") or collection_id,
                "datetime": props.get("datetime"),
                "platform": platform,
                "product_type": product_type,
                "orbit_direction": orbit_direction,
                "geometry": res_data.get("geometry"),
                "bbox": res_data.get("bbox"),
                "assets": parsed_assets
            }
            
    except urllib.error.HTTPError as e:
        if e.code == 404:
            raise ValueError(f"Satellite scene '{scene_id}' not found in collection '{collection_id}'.")
        raise Exception(f"Copernicus STAC API HTTP Error {e.code}: {e.reason}")
    except urllib.error.URLError as e:
        raise Exception(f"Failed to connect to Copernicus STAC API: {e}")
    except Exception as e:
        raise Exception(f"Error fetching scene details: {e}")

import os
import shutil
import time
import boto3
import rasterio
from rasterio.session import AWSSession
from rasterio.vrt import WarpedVRT
from rasterio.warp import transform_bounds
from app.core.config import settings
from app.services.spatial_query_service import haversine_distance

def get_aoi_cache_key(latitude: float, longitude: float, radius_km: float = 5.0) -> str:
    """
    Generates a deterministic normalized AOI key for filesystem cache paths.
    Rounds lat/lon to 4 decimal places (~11m resolution) to avoid floating-point jitter.
    """
    lat_str = f"{latitude:.4f}"
    lon_str = f"{longitude:.4f}"
    rad_str = f"{radius_km:.1f}"
    return f"aoi_{lat_str}_{lon_str}_{rad_str}km"

def resolve_scene_cache_dir(scene_id: str, aoi_key: Optional[str] = None, base_dir: Optional[str] = None) -> Optional[str]:
    """
    Resolves the directory path for a cached scene, supporting both AOI-aware subdirectories
    and legacy flat caches.
    """
    if base_dir is None:
        service_dir = os.path.dirname(os.path.abspath(__file__))
        app_dir = os.path.dirname(service_dir)
        backend_dir = os.path.dirname(app_dir)
        cache_base = os.path.join(backend_dir, "data", "satellite_cache", scene_id)
    else:
        cache_base = os.path.join(base_dir, "data", "satellite_cache", scene_id) if not base_dir.endswith(scene_id) else base_dir

    if not os.path.exists(cache_base):
        return None

    # 1. If exact aoi_key is specified
    if aoi_key:
        aoi_dir = os.path.join(cache_base, aoi_key)
        if os.path.exists(aoi_dir) and os.path.exists(os.path.join(aoi_dir, "metadata.json")):
            return aoi_dir
        return None

    # 2. Check if subdirectories exist (pick the newest by modification time)
    subdirs = [os.path.join(cache_base, d) for d in os.listdir(cache_base) if os.path.isdir(os.path.join(cache_base, d))]
    valid_subdirs = [d for d in subdirs if os.path.exists(os.path.join(d, "metadata.json"))]
    if valid_subdirs:
        valid_subdirs.sort(key=lambda p: os.path.getmtime(p), reverse=True)
        return valid_subdirs[0]

    # 3. Check if valid metadata exists directly in scene_id directory (legacy structure)
    if os.path.exists(os.path.join(cache_base, "metadata.json")):
        return cache_base

    return None

def process_scene_raster(
    scene_id: str,
    latitude: float,
    longitude: float,
    radius_km: float = 5.0,
    collection_id: str = "sentinel-1-grd"
) -> Dict[str, Any]:
    """
    Fetches raw VV and VH bands from Copernicus S3, crops them to the exact
    AOI bounds using a memory-safe windowed cloud read, and caches the GeoTIFFs locally
    under an AOI-aware directory: data/satellite_cache/<scene_id>/<aoi_cache_key>/
    """
    # 1. Validate CDSE S3 credentials
    access_key = settings.CDSE_S3_ACCESS_KEY
    secret_key = settings.CDSE_S3_SECRET_KEY
    
    if not access_key or not secret_key:
        raise ValueError(
            "Copernicus S3 Credentials are not configured in the environment. "
            "Please create a backend/.env file with CDSE_S3_ACCESS_KEY and CDSE_S3_SECRET_KEY."
        )

    # 2. Generate AOI bounding box and normalized cache key
    aoi_data = calculate_aoi(latitude, longitude, radius_km)
    bbox = aoi_data["bounding_box"]
    aoi_key = get_aoi_cache_key(latitude, longitude, radius_km)
    
    # Check AOI-specific cache directory
    scene_base_dir = os.path.join("data", "satellite_cache", scene_id)
    cache_dir = os.path.join(scene_base_dir, aoi_key)
    vv_path = os.path.join(cache_dir, "vv_clipped.tif")
    vh_path = os.path.join(cache_dir, "vh_clipped.tif")
    metadata_path = os.path.join(cache_dir, "metadata.json")

    # A. If already cached in AOI-specific subdirectory, return immediately
    if os.path.exists(vv_path) and os.path.exists(vh_path) and os.path.exists(metadata_path):
        try:
            with open(metadata_path, "r") as f:
                meta = json.load(f)
            return {
                "status": "cached",
                "scene_id": scene_id,
                "aoi_key": aoi_key,
                "vv_path": vv_path,
                "vh_path": vh_path,
                "aoi_bounds": bbox,
                "message": "Clipped rasters retrieved from local cache successfully."
            }
        except Exception:
            pass

    # B. Check if legacy flat cache matches the exact requested AOI
    legacy_vv = os.path.join(scene_base_dir, "vv_clipped.tif")
    legacy_vh = os.path.join(scene_base_dir, "vh_clipped.tif")
    legacy_meta = os.path.join(scene_base_dir, "metadata.json")
    if os.path.exists(legacy_vv) and os.path.exists(legacy_vh) and os.path.exists(legacy_meta):
        try:
            with open(legacy_meta, "r") as f:
                l_meta = json.load(f)
            l_coords = l_meta.get("aoi_coordinates", {})
            if l_coords:
                dist_km = haversine_distance(l_coords.get("latitude", 0), l_coords.get("longitude", 0), latitude, longitude)
                # If within 50m and radius matches, migrate/copy to the AOI-specific subdirectory
                if dist_km <= 0.05 and abs(l_coords.get("radius_km", 5.0) - radius_km) < 0.1:
                    os.makedirs(cache_dir, exist_ok=True)
                    shutil.copy2(legacy_vv, vv_path)
                    shutil.copy2(legacy_vh, vh_path)
                    shutil.copy2(legacy_meta, metadata_path)
                    return {
                        "status": "cached",
                        "scene_id": scene_id,
                        "aoi_key": aoi_key,
                        "vv_path": vv_path,
                        "vh_path": vh_path,
                        "aoi_bounds": bbox,
                        "message": "Clipped rasters migrated from legacy cache to AOI key successfully."
                    }
        except Exception:
            pass

    # Ensure AOI directory exists
    os.makedirs(cache_dir, exist_ok=True)

    # 3. Retrieve scene details to find S3 URLs for VV and VH
    detail = get_scene_detail(scene_id, collection_id)
    
    vv_asset = None
    vh_asset = None
    for asset in detail.get("assets", []):
        if asset.get("key") == "vv":
            vv_asset = asset
        elif asset.get("key") == "vh":
            vh_asset = asset

    if not vv_asset or not vh_asset:
        raise ValueError(f"Required VV/VH polarization assets not found for scene '{scene_id}'.")

    vv_s3_url = vv_asset.get("href")
    vh_s3_url = vh_asset.get("href")

    if not vv_s3_url or not vh_s3_url:
        raise ValueError(f"Asset access paths (href) are missing for scene '{scene_id}'.")

    # Helper to parse s3://eodata/Sentinel-1/...
    def parse_s3_url(url: str):
        if not url.startswith("s3://"):
            raise ValueError(f"Invalid S3 URL format: {url}")
        path = url[len("s3://"):]
        parts = path.split("/", 1)
        if len(parts) != 2:
            raise ValueError(f"Could not parse bucket and key from S3 URL: {url}")
        return parts[0], parts[1]

    vv_bucket, vv_key = parse_s3_url(vv_s3_url)
    vh_bucket, vh_key = parse_s3_url(vh_s3_url)

    # Configure session and environment for rasterio virtual S3 access
    session = boto3.Session(
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name="default"
    )

    rio_env = rasterio.Env(
        session=AWSSession(session, endpoint_url="eodata.dataspace.copernicus.eu"),
        AWS_VIRTUAL_HOSTING="FALSE"
    )

    original_sizes = {
        "vv": vv_asset.get("size"),
        "vh": vh_asset.get("size")
    }
    clipped_sizes = {}
    crs_info = ""

    start_time = time.time()

    # Process each asset
    with rio_env:
        for band_name, s3_key, out_path in [("vv", vv_key, vv_path), ("vh", vh_key, vh_path)]:
            s3_path = f"s3://{vv_bucket}/{s3_key}"
            
            try:
                with rasterio.open(s3_path) as src:
                    # Wrap in a WarpedVRT to reproject the GCPs to standard EPSG:4326 on the fly
                    with WarpedVRT(src, crs="EPSG:4326") as vrt:
                        crs_info = str(vrt.crs)
                        
                        # Direct geographic coordinates (no projection transform needed since VRT is EPSG:4326)
                        transformed_bounds = (
                            bbox["west"],
                            bbox["south"],
                            bbox["east"],
                            bbox["north"]
                        )
                        
                        # Get window coordinates in VRT space
                        window = vrt.window(*transformed_bounds)
                        
                        # Intersect to prevent out of bounds crashes
                        vrt_window = rasterio.windows.Window(0, 0, vrt.width, vrt.height)
                        window = window.intersection(vrt_window)
                        
                        if window.width <= 0 or window.height <= 0:
                            raise ValueError(
                                f"AOI bounding box does not overlap with scene coverage for polarization '{band_name}'."
                            )

                        # Windowed read from VRT
                        data = vrt.read(1, window=window)
                        
                        # Compute window transform
                        window_transform = vrt.window_transform(window)
                        
                        # Configure metadata profile for GeoTIFF in EPSG:4326
                        profile = vrt.profile.copy()
                        profile.update({
                            "driver": "GTiff",
                            "height": window.height,
                            "width": window.width,
                            "transform": window_transform,
                            "count": 1
                        })
                        
                        # Write cropped raster locally
                        with rasterio.open(out_path, "w", **profile) as dst:
                            dst.write(data, 1)

                        clipped_sizes[band_name] = os.path.getsize(out_path)

            except Exception as e:
                # Cleanup on failure
                if os.path.exists(out_path):
                    try:
                        os.remove(out_path)
                    except:
                        pass
                raise Exception(f"Failed to process {band_name.upper()} band: {str(e)}")

    # 4. Save metadata.json
    metadata = {
        "scene_id": scene_id,
        "acquisition_time": detail.get("datetime"),
        "platform": detail.get("platform"),
        "source_assets": {
            "vv": vv_s3_url,
            "vh": vh_s3_url
        },
        "aoi_coordinates": {
            "latitude": latitude,
            "longitude": longitude,
            "radius_km": radius_km
        },
        "clipping_bounds": bbox,
        "crs": crs_info,
        "original_sizes": original_sizes,
        "clipped_sizes": clipped_sizes,
        "processing_timestamp": datetime.utcnow().isoformat() + "Z",
        "processing_status": "success"
    }

    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2)

    return {
        "status": "success",
        "scene_id": scene_id,
        "aoi_key": aoi_key,
        "vv_path": vv_path,
        "vh_path": vh_path,
        "aoi_bounds": bbox,
        "message": f"Successfully clipped VV & VH rasters to the {radius_km}km AOI in {time.time() - start_time:.1f}s."
    }
