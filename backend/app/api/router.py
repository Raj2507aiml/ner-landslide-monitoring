from fastapi import APIRouter
from app.api.routes import (
    health,
    locations,
    satellite,
    weather,
    terrain,
    soil,
    historical,
    ml,
    risk,
    early_warning,
    field_reports,
    infrastructure,
    operations,
    incidents,
    auth
)

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router, prefix="/v1/auth", tags=["auth"])
api_router.include_router(locations.router, prefix="/v1/locations", tags=["locations"])
api_router.include_router(satellite.router, prefix="/v1/satellite", tags=["satellite"])
api_router.include_router(weather.router, prefix="/v1/weather", tags=["weather"])
api_router.include_router(terrain.router, prefix="/v1/terrain", tags=["terrain"])
api_router.include_router(soil.router, prefix="/v1/soil", tags=["soil"])
api_router.include_router(historical.router, prefix="/historical", tags=["historical"])
api_router.include_router(historical.router, prefix="/v1/historical", tags=["historical"])
api_router.include_router(ml.router, prefix="/v1/ml", tags=["ml"])
api_router.include_router(risk.router, prefix="/v1/risk", tags=["risk"])
api_router.include_router(early_warning.router, prefix="/v1/early-warning", tags=["early-warning"])
api_router.include_router(field_reports.router, prefix="/v1/field-reports", tags=["field-reports"])
api_router.include_router(infrastructure.router, prefix="/v1/infrastructure", tags=["infrastructure"])
api_router.include_router(operations.router, prefix="/v1/operations", tags=["operations"])
api_router.include_router(incidents.router, prefix="/v1/incidents", tags=["incidents"])

