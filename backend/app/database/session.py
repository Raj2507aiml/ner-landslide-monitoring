from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

# For SQLite, check_same_thread needs to be False. For other DBs (Postgres, etc.), this is not needed.
connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Dependency to get database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def migrate_db(db_engine):
    """Auto-migrates missing columns in tables to guarantee backward compatibility across SQLite, Postgres, etc."""
    try:
        from sqlalchemy import inspect, text
        inspector = inspect(db_engine)
        tables = inspector.get_table_names()
        if "field_reports" not in tables:
            return

        columns = inspector.get_columns("field_reports")
        existing_cols = {col["name"] for col in columns}

        is_sqlite = str(db_engine.url).startswith("sqlite")
        dt_type = "DATETIME" if is_sqlite else "TIMESTAMP"

        columns_to_add = [
            ("full_name", "VARCHAR(150)"),
            ("aadhaar_number", "VARCHAR(50)"),
            ("aadhaar_hash", "VARCHAR(64)"),
            ("aadhaar_card_path", "VARCHAR(500)"),
            ("aadhaar_qr_path", "VARCHAR(500)"),
            ("jio_tag_image_path", "VARCHAR(500)"),
            ("verification_status", "VARCHAR(50) DEFAULT 'PENDING'"),
            ("verification_note", "TEXT"),
            ("verified_by", "VARCHAR(120)"),
            ("verified_at", dt_type),
            ("aadhaar_auto_status", "VARCHAR(50) DEFAULT 'UNVERIFIED'"),
            ("aadhaar_verification_details", "TEXT"),
            ("jio_tag_latitude", "FLOAT"),
            ("jio_tag_longitude", "FLOAT"),
            ("jio_tag_altitude", "FLOAT"),
            ("jio_tag_captured_at", dt_type),
            ("visual_hazard_score", "FLOAT"),
            ("predicted_risk_score", "FLOAT"),
            ("prediction_details", "TEXT"),
        ]

        with db_engine.connect() as conn:
            for col_name, col_type in columns_to_add:
                if col_name not in existing_cols:
                    try:
                        conn.execute(text(f"ALTER TABLE field_reports ADD COLUMN {col_name} {col_type}"))
                        conn.commit()
                    except Exception:
                        pass
    except Exception:
        pass
