"""
Field Report Media Service - Phase 7 Checkpoint 16.2

Handles image validation, Pillow integrity checks, secure UUID-based disk storage,
EXIF GPS extraction, and database persistence for field intelligence evidence.
"""

import os
import io
import uuid
from datetime import datetime
from typing import List, Optional, Tuple, Dict, Any
from PIL import Image, ExifTags
from fastapi import UploadFile, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import BASE_DIR
from app.models.field_report import FieldReport
from app.models.field_report_media import FieldReportMedia
from app.schemas.field_report_media import FieldReportMediaResponse

# Media storage configuration
MEDIA_ROOT_DIR = os.path.join(BASE_DIR, "data", "field_reports")
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB limit
ALLOWED_FORMATS = {
    "JPEG": ("image/jpeg", ".jpg"),
    "PNG": ("image/png", ".png"),
    "WEBP": ("image/webp", ".webp")
}

def _convert_dms_to_degrees(dms_value: Any) -> Optional[float]:
    """
    Converts EXIF degrees/minutes/seconds rational tuples to decimal degrees.
    """
    try:
        if isinstance(dms_value, (tuple, list)) and len(dms_value) >= 3:
            deg = float(dms_value[0])
            mins = float(dms_value[1])
            sec = float(dms_value[2])
            return deg + (mins / 60.0) + (sec / 3600.0)
        return float(dms_value)
    except Exception:
        return None

def extract_exif_metadata(image: Image.Image) -> Tuple[Optional[float], Optional[float], Optional[datetime]]:
    """
    Extracts optional GPS latitude, longitude, and timestamp from image EXIF tags if present.
    Returns (exif_latitude, exif_longitude, exif_timestamp).
    Never fabricates coordinates; returns None if tags are missing or invalid.
    """
    lat, lon, capture_time = None, None, None
    try:
        exif = image.getexif()
        if not exif:
            return None, None, None

        # Capture timestamp (tag 36867 = DateTimeOriginal, 306 = DateTime, 36868 = DateTimeDigitized)
        date_str = exif.get(36867) or exif.get(306) or exif.get(36868)
        if date_str:
            try:
                capture_time = datetime.strptime(str(date_str).strip(), "%Y:%m:%d %H:%M:%S")
            except Exception:
                capture_time = None

        # GPS Info tag is 34853 (0x8825)
        gps_ifd = exif.get_ifd(34853) if hasattr(exif, "get_ifd") else None
        if not gps_ifd and hasattr(image, "_getexif"):
            raw_exif = image._getexif()
            if raw_exif and 34853 in raw_exif:
                gps_ifd = raw_exif[34853]

        if gps_ifd:
            # 1: GPSLatitudeRef ('N' or 'S'), 2: GPSLatitude
            # 3: GPSLongitudeRef ('E' or 'W'), 4: GPSLongitude
            lat_ref = gps_ifd.get(1)
            lat_val = gps_ifd.get(2)
            lon_ref = gps_ifd.get(3)
            lon_val = gps_ifd.get(4)

            if lat_val is not None:
                deg_lat = _convert_dms_to_degrees(lat_val)
                if deg_lat is not None:
                    if lat_ref and str(lat_ref).upper() == "S":
                        deg_lat = -deg_lat
                    lat = round(deg_lat, 6)

            if lon_val is not None:
                deg_lon = _convert_dms_to_degrees(lon_val)
                if deg_lon is not None:
                    if lon_ref and str(lon_ref).upper() == "W":
                        deg_lon = -deg_lon
                    lon = round(deg_lon, 6)

            # Fallback timestamp from GPS Date/Time
            if not capture_time:
                gps_date = gps_ifd.get(29)
                gps_time = gps_ifd.get(7)
                if gps_date and gps_time:
                    try:
                        h = int(gps_time[0])
                        m = int(gps_time[1])
                        s = int(gps_time[2])
                        capture_time = datetime.strptime(f"{gps_date} {h:02d}:{m:02d}:{s:02d}", "%Y:%m:%d %H:%M:%S")
                    except Exception:
                        pass
    except Exception:
        pass

    return lat, lon, capture_time

from app.services.field_report_spatial_service import haversine_distance

def compute_exif_consistency(
    report_lat: Optional[float],
    report_lon: Optional[float],
    exif_lat: Optional[float],
    exif_lon: Optional[float]
) -> Tuple[Optional[float], Optional[str]]:
    """
    Evaluates geodesic distance and consistency between reported location and EXIF GPS.
    Thresholds:
      <= 0.5 km: CONSISTENT
      > 0.5 km and <= 5.0 km: NEARBY_DIFFERENCE
      > 5.0 km: SIGNIFICANT_DIFFERENCE
    """
    if exif_lat is None or exif_lon is None:
        return None, "NO_EXIF_GPS"
    if report_lat is None or report_lon is None:
        return None, None
    
    dist_km = round(haversine_distance(report_lat, report_lon, exif_lat, exif_lon), 3)
    if dist_km <= 0.5:
        consistency = "CONSISTENT"
    elif dist_km <= 5.0:
        consistency = "NEARBY_DIFFERENCE"
    else:
        consistency = "SIGNIFICANT_DIFFERENCE"
    
    return dist_km, consistency

class FieldReportMediaService:
    @staticmethod
    def get_media_url(report_id: int, stored_filename: str) -> str:
        """
        Constructs a safe, relative API URL for the media asset.
        """
        return f"/media/field_reports/report_{report_id}/{stored_filename}"

    @classmethod
    def to_schema(
        cls,
        media: FieldReportMedia,
        report_lat: Optional[float] = None,
        report_lon: Optional[float] = None
    ) -> FieldReportMediaResponse:
        """
        Converts a SQLAlchemy FieldReportMedia entity to FieldReportMediaResponse.
        Enriches with EXIF coordinate consistency evaluation.
        """
        target_lat = report_lat
        target_lon = report_lon
        if target_lat is None and hasattr(media, "report") and media.report:
            target_lat = media.report.latitude
            target_lon = media.report.longitude

        dist_km, consistency = compute_exif_consistency(
            report_lat=target_lat,
            report_lon=target_lon,
            exif_lat=media.exif_latitude,
            exif_lon=media.exif_longitude
        )

        return FieldReportMediaResponse(
            id=media.id,
            report_id=media.report_id,
            media_type=media.media_type,
            original_filename=media.original_filename,
            stored_filename=media.stored_filename,
            file_size_bytes=media.file_size_bytes,
            mime_type=media.mime_type,
            width=media.width,
            height=media.height,
            exif_latitude=media.exif_latitude,
            exif_longitude=media.exif_longitude,
            exif_timestamp=media.exif_timestamp,
            created_at=media.created_at,
            media_url=cls.get_media_url(media.report_id, media.stored_filename),
            exif_distance_km=dist_km,
            exif_consistency=consistency
        )

    @classmethod
    async def process_and_save_media(
        cls,
        db: Session,
        report_id: int,
        file: UploadFile
    ) -> FieldReportMediaResponse:
        """
        Validates, processes, extracts EXIF metadata, and securely stores an uploaded image file.
        """
        # 1. Verify parent report exists
        report = db.query(FieldReport).filter(FieldReport.id == report_id).first()
        if not report:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Field report with ID {report_id} not found."
            )

        # 2. Read and enforce size limit
        file_bytes = await file.read(MAX_FILE_SIZE_BYTES + 1)
        if len(file_bytes) > MAX_FILE_SIZE_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File size exceeds the maximum limit of 10 MB."
            )
        if len(file_bytes) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Uploaded file is empty."
            )

        # 3. Pillow Image Integrity & Format Verification
        try:
            # Verify file integrity header and bitstream
            test_img = Image.open(io.BytesIO(file_bytes))
            test_img.verify()
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Corrupted, invalid, or non-image file format."
            )

        # Reopen image to access dimensions, format, and EXIF
        try:
            image = Image.open(io.BytesIO(file_bytes))
            img_format = (image.format or "").upper()
            if img_format not in ALLOWED_FORMATS:
                raise HTTPException(
                    status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                    detail=f"Unsupported image format '{img_format}'. Only JPEG, PNG, and WebP images are allowed."
                )

            mime_type, file_ext = ALLOWED_FORMATS[img_format]
            width, height = image.size
            exif_lat, exif_lon, exif_time = extract_exif_metadata(image)
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to process image metadata: {str(e)}"
            )

        # 4. Secure Filename & Directory Storage
        stored_filename = f"{uuid.uuid4().hex}{file_ext}"
        report_dir = os.path.join(MEDIA_ROOT_DIR, f"report_{report_id}")
        os.makedirs(report_dir, exist_ok=True)
        file_path = os.path.join(report_dir, stored_filename)

        try:
            with open(file_path, "wb") as out_file:
                out_file.write(file_bytes)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to save image evidence to storage."
            )

        # Sanitize original filename (strip directory components)
        clean_original_filename = os.path.basename(file.filename or "uploaded_image.jpg")

        # 5. Persist Media Record in Database
        db_media = FieldReportMedia(
            report_id=report_id,
            media_type="IMAGE",
            original_filename=clean_original_filename,
            stored_filename=stored_filename,
            file_path=file_path,
            file_size_bytes=len(file_bytes),
            mime_type=mime_type,
            width=width,
            height=height,
            exif_latitude=exif_lat,
            exif_longitude=exif_lon,
            exif_timestamp=exif_time,
            created_at=datetime.utcnow()
        )
        db.add(db_media)
        db.commit()
        db.refresh(db_media)

        return cls.to_schema(db_media)

    @classmethod
    def get_media_for_report(cls, db: Session, report_id: int) -> List[FieldReportMediaResponse]:
        """
        Retrieves all media evidence items for a given report ID.
        """
        report = db.query(FieldReport).filter(FieldReport.id == report_id).first()
        if not report:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Field report with ID {report_id} not found."
            )
        media_records = db.query(FieldReportMedia).filter(FieldReportMedia.report_id == report_id).order_by(FieldReportMedia.created_at.asc()).all()
        return [cls.to_schema(m) for m in media_records]

    @classmethod
    def delete_media_item(cls, db: Session, report_id: int, media_id: int) -> Dict[str, Any]:
        """
        Deletes a media item from the database and removes the physical file from disk.
        """
        # Verify report
        report = db.query(FieldReport).filter(FieldReport.id == report_id).first()
        if not report:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Field report with ID {report_id} not found."
            )

        # Verify media belongs to report
        media = db.query(FieldReportMedia).filter(
            FieldReportMedia.id == media_id,
            FieldReportMedia.report_id == report_id
        ).first()

        if not media:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Media record with ID {media_id} not found for report {report_id}."
            )

        file_path = media.file_path

        # Delete database record
        db.delete(media)
        db.commit()

        # Delete physical file from disk gracefully
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception:
                pass

        return {
            "status": "deleted",
            "media_id": media_id,
            "message": f"Media evidence {media_id} successfully deleted."
        }
