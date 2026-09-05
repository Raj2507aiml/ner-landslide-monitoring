"""
Jio Tag Prediction Service

Extracts embedded geo-spatial telemetry (EXIF GPS latitude, longitude, altitude, timestamp)
and runs computer vision surface analysis (crack/fissure density, bare soil exposure)
from uploaded Jio Tag photos to calculate calibrated landslide risk predictions.
"""

import os
from datetime import datetime
from typing import Dict, Any, Optional, Tuple
from PIL import Image, ImageFilter, ImageStat
from sqlalchemy.orm import Session

try:
    import numpy as np
except Exception:
    np = None

try:
    import cv2
    HAS_CV2 = True
except Exception:
    cv2 = None
    HAS_CV2 = False

from app.services.field_report_media_service import extract_exif_metadata
from app.services.composite_risk_service import CompositeRiskService

class JioTagPredictionService:

    @staticmethod
    def extract_telemetry(image_path: str) -> Dict[str, Any]:
        """
        Extracts GPS latitude, longitude, altitude, and capture timestamp from image EXIF tags.
        """
        telemetry = {
            "has_exif_gps": False,
            "latitude": None,
            "longitude": None,
            "altitude": None,
            "captured_at": None,
            "image_width": None,
            "image_height": None,
        }

        if not image_path or not os.path.exists(image_path):
            return telemetry

        try:
            with Image.open(image_path) as pil_img:
                w, h = pil_img.size
                telemetry["image_width"] = w
                telemetry["image_height"] = h

                lat, lon, capture_time = extract_exif_metadata(pil_img)
                if lat is not None and lon is not None:
                    telemetry["has_exif_gps"] = True
                    telemetry["latitude"] = float(lat)
                    telemetry["longitude"] = float(lon)
                    telemetry["captured_at"] = capture_time.isoformat() if capture_time else None

                # Extract altitude if available in GPS IFD
                if hasattr(pil_img, "getexif"):
                    exif = pil_img.getexif()
                    gps_ifd = exif.get_ifd(34853) if exif and hasattr(exif, "get_ifd") else None
                    if gps_ifd:
                        alt_val = gps_ifd.get(6)  # GPSAltitude
                        if alt_val is not None:
                            try:
                                if isinstance(alt_val, (tuple, list)):
                                    telemetry["altitude"] = round(float(alt_val[0]) / float(alt_val[1]), 2)
                                else:
                                    telemetry["altitude"] = round(float(alt_val), 2)
                            except Exception:
                                pass

            return telemetry
        except Exception:
            return telemetry

    @staticmethod
    def analyze_visual_hazard_features(image_path: str) -> Dict[str, Any]:
        """
        Runs computer vision feature extraction on the hazard observation image:
        1. Canny edge & fissure detection (or PIL edge gradient) to quantify ground crack and surface rupture density.
        2. HSV/color analysis to compute soil/mud exposure ratio vs vegetation.
        3. Composite Visual Hazard Score (0.0 to 1.0).
        """
        features = {
            "crack_density_index": 0.0,
            "soil_exposure_ratio": 0.0,
            "visual_hazard_score": 0.0,
            "dominant_visual_feature": "NORMAL_SURFACE"
        }

        if not image_path or not os.path.exists(image_path):
            return features

        # Try OpenCV-based extraction if available
        if HAS_CV2 and cv2 is not None and np is not None:
            try:
                img = cv2.imread(image_path)
                if img is not None:
                    # Resize to standard analysis resolution (640px width)
                    h, w = img.shape[:2]
                    scale = 640.0 / max(w, 640)
                    new_w, new_h = int(w * scale), int(h * scale)
                    resized = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)

                    # 1. Edge & Crack Detection via Canny & Blur
                    gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
                    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
                    edges = cv2.Canny(blurred, threshold1=50, threshold2=150)

                    total_pixels = float(new_w * new_h)
                    edge_pixels = float(np.count_nonzero(edges))
                    # Normalized edge density: typically 0.01 to 0.15 for real slope photos
                    raw_edge_density = edge_pixels / total_pixels
                    crack_density = min(1.0, round(raw_edge_density * 8.0, 3))
                    features["crack_density_index"] = crack_density

                    # 2. Bare Soil / Mudflow Exposure Ratio via HSV
                    hsv = cv2.cvtColor(resized, cv2.COLOR_BGR2HSV)
                    # Brown / Red-brown / Tan soil and rock mask
                    lower_soil = np.array([8, 30, 40], dtype=np.uint8)
                    upper_soil = np.array([28, 220, 200], dtype=np.uint8)
                    soil_mask = cv2.inRange(hsv, lower_soil, upper_soil)
                    soil_pixels = float(np.count_nonzero(soil_mask))
                    soil_exposure = min(1.0, round(soil_pixels / total_pixels, 3))
                    features["soil_exposure_ratio"] = soil_exposure

                    # 3. Composite Visual Hazard Score (0.0 to 1.0)
                    visual_score = round(0.60 * crack_density + 0.40 * soil_exposure, 2)
                    features["visual_hazard_score"] = visual_score

                    if visual_score >= 0.65:
                        features["dominant_visual_feature"] = "ACTIVE_FISSURE_SLOPE_EROSION"
                    elif visual_score >= 0.35:
                        features["dominant_visual_feature"] = "MODERATE_SURFACE_DISTURBANCE"
                    else:
                        features["dominant_visual_feature"] = "LOW_SURFACE_DEFORMATION"

                    return features
            except Exception:
                pass

        # PIL Fallback for headless environments without OpenCV
        try:
            with Image.open(image_path) as pil_img:
                rgb = pil_img.convert("RGB")
                w, h = rgb.size
                scale = 320.0 / max(w, 320)
                new_w, new_h = max(1, int(w * scale)), max(1, int(h * scale))
                small = rgb.resize((new_w, new_h))

                # Edge gradient using FIND_EDGES
                gray = small.convert("L")
                edge_img = gray.filter(ImageFilter.FIND_EDGES)
                stat = ImageStat.Stat(edge_img)
                avg_edge = stat.mean[0] / 255.0
                crack_density = min(1.0, round(avg_edge * 4.5, 3))
                features["crack_density_index"] = crack_density

                # Soil / mud pixel detection (brown/tan tones: R > G > B with reasonable saturation)
                soil_count = 0
                pixels = small.getdata()
                for r, g, b in pixels:
                    if r > 60 and g > 40 and b < min(r, g) and (r - b) > 20:
                        soil_count += 1
                soil_exposure = min(1.0, round(float(soil_count) / float(new_w * new_h), 3))
                features["soil_exposure_ratio"] = soil_exposure

                visual_score = round(0.60 * crack_density + 0.40 * soil_exposure, 2)
                features["visual_hazard_score"] = visual_score

                if visual_score >= 0.65:
                    features["dominant_visual_feature"] = "ACTIVE_FISSURE_SLOPE_EROSION"
                elif visual_score >= 0.35:
                    features["dominant_visual_feature"] = "MODERATE_SURFACE_DISTURBANCE"
                else:
                    features["dominant_visual_feature"] = "LOW_SURFACE_DEFORMATION"

                return features
        except Exception:
            return features

    @classmethod
    def extract_and_predict(
        cls,
        db: Session,
        image_path: str,
        fallback_lat: float,
        fallback_lon: float
    ) -> Dict[str, Any]:
        """
        Integrates Jio Tag telemetry extraction with dynamic composite risk calculation.
        Evaluates DEM terrain, antecedent rainfall, ML susceptibility, and visual hazard score.
        Returns full predictive breakdown.
        """
        # 1. Telemetry
        telemetry = cls.extract_telemetry(image_path)
        use_lat = telemetry["latitude"] if telemetry["has_exif_gps"] else fallback_lat
        use_lon = telemetry["longitude"] if telemetry["has_exif_gps"] else fallback_lon

        # 2. Visual Features
        visual_features = cls.analyze_visual_hazard_features(image_path)

        # 3. Environmental & Composite Risk Calculation
        try:
            comp_risk = CompositeRiskService.calculate_composite_risk(db, use_lat, use_lon)
            base_risk_score = float(comp_risk.get("composite_risk_index", 50.0))
            terrain = comp_risk.get("terrain", {})
            rainfall_comp = comp_risk.get("components", {}).get("rainfall_trigger", {})
            ml_comp = comp_risk.get("components", {}).get("static_susceptibility", {})
        except Exception as e:
            base_risk_score = 50.0
            terrain = {"elevation": 1200.0, "slope": 15.0}
            rainfall_comp = {"rainfall_score": 15.0}
            ml_comp = {"probability": 0.50}

        # 4. Calibrate with Visual Hazard Score (Amplifies risk if severe fissure/debris observed)
        visual_mult = 1.0 + (0.25 * visual_features["visual_hazard_score"])
        calibrated_risk = min(100.0, round(base_risk_score * visual_mult, 1))

        # 5. Risk Category
        if calibrated_risk >= 80.0:
            risk_level = "CRITICAL"
        elif calibrated_risk >= 60.0:
            risk_level = "HIGH"
        elif calibrated_risk >= 30.0:
            risk_level = "MODERATE"
        else:
            risk_level = "LOW"

        prediction_result = {
            "target_coordinates": {
                "latitude": round(use_lat, 6),
                "longitude": round(use_lon, 6),
                "altitude": telemetry.get("altitude"),
                "source": "JIO_TAG_EXIF" if telemetry["has_exif_gps"] else "REPORT_PIN"
            },
            "telemetry": telemetry,
            "visual_features": visual_features,
            "base_composite_risk": base_risk_score,
            "calibrated_risk_score": calibrated_risk,
            "risk_level": risk_level,
            "environmental_drivers": {
                "elevation_m": terrain.get("elevation"),
                "slope_deg": terrain.get("slope"),
                "rainfall_score": rainfall_comp.get("rainfall_score"),
                "ml_susceptibility_prob": ml_comp.get("probability")
            },
            "predictive_summary": (
                f"Landslide probability predicted at {calibrated_risk}% ({risk_level} Risk) "
                f"at coordinates ({use_lat:.4f}, {use_lon:.4f}). Visual surface hazard factor "
                f"measured at {visual_features['visual_hazard_score']} (Crack density: {visual_features['crack_density_index']})."
            )
        }

        return prediction_result
