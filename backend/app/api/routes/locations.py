from fastapi import APIRouter, HTTPException, status
from fastapi.responses import JSONResponse
from app.schemas.location import LocationAnalysisRequest, LocationAnalysisResponse, LocationDetails, RegionDetails, AOIDetails, BoundingBox
from app.services.aoi_service import is_inside_ner, calculate_aoi

router = APIRouter()

@router.post("/analyze", response_model=LocationAnalysisResponse)
def analyze_location(request: LocationAnalysisRequest):
    """
    Analyzes a user-selected coordinate (latitude/longitude) and, if within 
    the North Eastern Region (NER) of India, generates a 5-25 km bounding box (AOI)
    which will later be used to pull satellite imagery.
    
    If the coordinates are outside the NER region boundary, this API returns
    HTTP 400 Bad Request containing a structured JSON response object. 
    
    RATIONALE FOR HTTP 400:
    Using HTTP 400 (Bad Request) represents a semantic input error where the coordinates 
    are syntactically valid on Earth, but violate the business validation boundary (outside NER).
    Returning a structured JSON body with HTTP 400 allows the frontend client to distinguish 
    this from server errors (500) or parsing errors (422) and display a user-friendly modal.
    """
    latitude = request.latitude
    longitude = request.longitude
    radius_km = request.radius_km

    # 1. Verify if location lies within the boundaries of the 8 NER states
    in_ner = is_inside_ner(latitude, longitude)

    location_info = LocationDetails(latitude=latitude, longitude=longitude)
    region_info = RegionDetails(in_ner=in_ner)

    if in_ner:
        # 2. Calculate the geographical bounding box (AOI)
        aoi_data = calculate_aoi(latitude, longitude, radius_km)
        aoi_info = AOIDetails(
            radius_km=aoi_data["radius_km"],
            bounding_box=BoundingBox(**aoi_data["bounding_box"])
        )
        return LocationAnalysisResponse(
            status="success",
            location=location_info,
            region=region_info,
            aoi=aoi_info
        )
    else:
        # 3. Return HTTP 400 with a structured body for locations outside the NER
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "status": "outside_region",
                "location": {
                    "latitude": latitude,
                    "longitude": longitude
                },
                "region": {
                    "name": "North Eastern Region",
                    "in_ner": False
                },
                "message": "Please select a location within the North Eastern Region of India."
            }
        )
