import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.core.config import settings, BASE_DIR
from app.api.router import api_router
from app.database.session import engine, Base
import app.models  # Register models for Base.metadata

# Create database tables
Base.metadata.create_all(bind=engine)

# Check if running in production mode
is_production = settings.ENVIRONMENT.lower() == "production"

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Backend API for NER Landslide Risk Monitoring and Early Warning System",
    version="1.0.0",
    docs_url=None if is_production else "/docs",
    redoc_url=None if is_production else "/redoc",
    openapi_url=None if is_production else "/openapi.json"
)

# Set up CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.all_cors_origins,
    allow_origin_regex=r"^https:\/\/.*\.onrender\.com$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Field Report Media directory for safe image access
MEDIA_DIR = os.path.join(BASE_DIR, "data", "field_reports")
os.makedirs(MEDIA_DIR, exist_ok=True)
app.mount("/media/field_reports", StaticFiles(directory=MEDIA_DIR), name="field_report_media")

# Include central router
app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/")
def read_root():
    response = {
        "message": "Welcome to the NER Landslide Risk Monitoring System API",
        "status": "online",
        "health": f"{settings.API_V1_STR}/health"
    }
    if not is_production:
        response["docs"] = "/docs"
    return response
