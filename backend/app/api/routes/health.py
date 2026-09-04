from fastapi import APIRouter

router = APIRouter()

@router.get("/health")
def check_health():
    return {
        "status": "healthy",
        "service": "NER Landslide Monitoring API"
    }
