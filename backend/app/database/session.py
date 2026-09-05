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
    """Auto-migrates missing columns in SQLite tables to guarantee backward compatibility."""
    if not str(db_engine.url).startswith("sqlite"):
        return
    try:
        from sqlalchemy import text
        with db_engine.connect() as conn:
            result = conn.execute(text("PRAGMA table_info(field_reports)"))
            existing_cols = {row[1] for row in result.fetchall()}
            if not existing_cols:
                return

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
                ("verified_at", "DATETIME"),
                ("aadhaar_auto_status", "VARCHAR(50) DEFAULT 'UNVERIFIED'"),
                ("aadhaar_verification_details", "TEXT"),
                ("jio_tag_latitude", "FLOAT"),
                ("jio_tag_longitude", "FLOAT"),
                ("jio_tag_altitude", "FLOAT"),
                ("jio_tag_captured_at", "DATETIME"),
                ("visual_hazard_score", "FLOAT"),
                ("predicted_risk_score", "FLOAT"),
                ("prediction_details", "TEXT"),
            ]

            for col_name, col_type in columns_to_add:
                if col_name not in existing_cols:
                    conn.execute(text(f"ALTER TABLE field_reports ADD COLUMN {col_name} {col_type}"))
            conn.commit()
    except Exception as e:
        pass
