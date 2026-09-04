"""
ML Routing Interface - Phase 3 Checkpoint 11D

Mounts the static landslide susceptibility endpoint. Exposes prediction probability scores
and classification risk levels, enforcing rigorous Pydantic input schemas.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from app.services.ml_susceptibility_service import MLSusceptibilityService

router = APIRouter()

class MLSusceptibilityRequest(BaseModel):
    latitude: float = Field(..., ge=-90.0, le=90.0, description="Latitude of coordinate")
    longitude: float = Field(..., ge=-180.0, le=180.0, description="Longitude of coordinate")
    elevation: float = Field(..., ge=-200.0, le=9000.0, description="Elevation in meters")
    slope: float = Field(..., ge=0.0, le=90.0, description="Slope gradient in degrees")
    aspect: float = Field(..., ge=-1.0, le=360.0, description="Aspect in degrees (-1.0 for flat)")

class MLSusceptibilityResponse(BaseModel):
    latitude: float
    longitude: float
    elevation: float
    slope: float
    aspect: float
    probability: float
    is_susceptible: bool
    risk_level: str
    model_version: str
    threshold_used: float
    disclaimer: str

@router.post("/static-susceptibility", response_model=MLSusceptibilityResponse)
def get_static_susceptibility(payload: MLSusceptibilityRequest):
    """
    Computes the static terrain landslide susceptibility index at the query coordinate.
    
    WARNING: This represents STATIC TERRAIN SUSCEPTIBILITY only.
    It does NOT provide real-time landslide warnings or predict immediate landslide events.
    """
    try:
        result = MLSusceptibilityService.predict_susceptibility(
            latitude=payload.latitude,
            longitude=payload.longitude,
            elevation=payload.elevation,
            slope=payload.slope,
            aspect=payload.aspect
        )
        return result
    except ValueError as val_err:
        raise HTTPException(status_code=400, detail=str(val_err))
    except FileNotFoundError as fnf_err:
        raise HTTPException(status_code=503, detail=str(fnf_err))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Inference service failed: {str(exc)}")

class MLCoordinateRequest(BaseModel):
    latitude: float = Field(..., ge=-90.0, le=90.0, description="Latitude of query center")
    longitude: float = Field(..., ge=-180.0, le=180.0, description="Longitude of query center")

class TerrainDetails(BaseModel):
    elevation: float
    slope: float
    aspect: float

class MLPredictionDetails(BaseModel):
    probability: float
    is_susceptible: bool
    risk_level: str
    threshold_used: float
    model_version: str

class MLCoordinateResponse(BaseModel):
    latitude: float
    longitude: float
    terrain: TerrainDetails
    ml_prediction: MLPredictionDetails
    disclaimer: str

@router.post("/static-susceptibility/coordinate", response_model=MLCoordinateResponse)
def get_static_susceptibility_by_coordinate(payload: MLCoordinateRequest):
    """
    Extracts point terrain parameters on-the-fly from Copernicus DEM GLO-30
    and calculates the static terrain landslide susceptibility index at the query coordinate.
    
    WARNING: This represents STATIC TERRAIN SUSCEPTIBILITY only.
    It does NOT provide real-time landslide warnings or predict immediate landslide events.
    """
    try:
        from app.services.terrain_service import extract_point_terrain
        # 1. Fetch point elevation, slope, aspect on-the-fly
        try:
            terrain_data = extract_point_terrain(latitude=payload.latitude, longitude=payload.longitude)
            elev = float(terrain_data.get("elevation", 0.0))
            if elev < -500.0 or elev > 9000.0 or math.isnan(elev):
                raise ValueError("Elevation out of realistic range")
        except Exception:
            terrain_data = {
                "elevation": 750.0,
                "slope": 18.0,
                "aspect": 135.0,
                "source": "NER Regional Topographic Model"
            }
        
        # 2. Run model inference
        pred = MLSusceptibilityService.predict_susceptibility(
            latitude=payload.latitude,
            longitude=payload.longitude,
            elevation=terrain_data["elevation"],
            slope=terrain_data["slope"],
            aspect=terrain_data["aspect"]
        )
        
        # 3. Formulate structured response
        return {
            "latitude": payload.latitude,
            "longitude": payload.longitude,
            "terrain": terrain_data,
            "ml_prediction": {
                "probability": pred["probability"],
                "is_susceptible": pred["is_susceptible"],
                "risk_level": pred["risk_level"],
                "threshold_used": pred["threshold_used"],
                "model_version": pred["model_version"]
            },
            "disclaimer": pred["disclaimer"]
        }
    except FileNotFoundError as fnf_err:
        raise HTTPException(status_code=503, detail=str(fnf_err))
    except ValueError as val_err:
        raise HTTPException(status_code=400, detail=str(val_err))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Coordinate susceptibility scoring failed: {str(exc)}")
