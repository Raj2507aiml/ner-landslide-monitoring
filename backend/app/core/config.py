import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List
from dotenv import load_dotenv

# Resolve absolute path to backend/.env relative to config.py location
# config.py is at backend/app/core/config.py, so 3 levels up is backend/
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ENV_PATH = os.path.join(BASE_DIR, ".env")

# Pre-load into environment variables for general os.getenv usage
load_dotenv(ENV_PATH)

class Settings(BaseSettings):
    API_V1_STR: str = "/api"
    PROJECT_NAME: str = "NER Landslide Monitoring System API"
    
    ENVIRONMENT: str = "development"

    # CORS Configuration
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "https://ner-landslide-frontend-fmrr.onrender.com",
    ]

    @property
    def all_cors_origins(self) -> List[str]:
        origins = list(self.CORS_ORIGINS)
        custom_origins = os.getenv("ALLOWED_ORIGINS", "")
        if custom_origins:
            origins.extend([o.strip() for o in custom_origins.split(",") if o.strip()])
        return origins
    
    # Database Settings - SQLite defaults, PostgreSQL ready
    DATABASE_URL: str = "sqlite:///./landslide_monitoring.db"

    # Copernicus Data Space S3 Credentials
    CDSE_S3_ACCESS_KEY: str = ""
    CDSE_S3_SECRET_KEY: str = ""

    # Twilio SMS Early Warning Notification Gateway
    TWILIO_ACCOUNT_SID: str = os.getenv("TWILIO_ACCOUNT_SID", "")
    TWILIO_AUTH_TOKEN: str = os.getenv("TWILIO_AUTH_TOKEN", "")
    TWILIO_PHONE_NUMBER: str = os.getenv("TWILIO_PHONE_NUMBER", "+17372212163")
    EMERGENCY_RECIPIENT_NUMBERS: str = os.getenv("EMERGENCY_RECIPIENT_NUMBERS", "+917786898038")
    SMS_ALERT_TEMPLATE: str = "[NDMA ALERT] {severity} {report_type} in {state_name} ({latitude:.3f}N, {longitude:.3f}E): {description}. Helpline: 1070/112"

    model_config = SettingsConfigDict(
        env_file=ENV_PATH,
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

settings = Settings()
