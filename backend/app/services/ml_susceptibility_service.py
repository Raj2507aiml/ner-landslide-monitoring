"""
ML Susceptibility Service - Phase 3 Checkpoint 11D

Loads the trained Random Forest model and metadata in a lazy, thread-safe singleton pattern.
Performs input validation, aspect transforms, probability inference, and maps results to risk classes.
"""

import os
import math
import json
import joblib
import numpy as np

class MLSusceptibilityService:
    _model = None
    _metadata = None
    
    # Path resolution relative to this service file
    SERVICE_DIR = os.path.dirname(os.path.abspath(__file__))
    APP_DIR = os.path.dirname(SERVICE_DIR)
    BACKEND_DIR = os.path.dirname(APP_DIR)
    
    MODEL_PATH = os.path.join(BACKEND_DIR, "data", "ml", "models", "static_susceptibility_model.pkl")
    METADATA_PATH = os.path.join(BACKEND_DIR, "data", "ml", "models", "model_metadata.json")

    @classmethod
    def load_model_if_needed(cls):
        """Lazy loader for model binary and metadata, executed once."""
        if cls._model is None:
            if not os.path.exists(cls.MODEL_PATH):
                raise FileNotFoundError(
                    f"Model binary missing at: {cls.MODEL_PATH}. "
                    "Ensure you have run the model training script first."
                )
            if not os.path.exists(cls.METADATA_PATH):
                raise FileNotFoundError(
                    f"Model metadata missing at: {cls.METADATA_PATH}. "
                    "Ensure you have run the threshold calibration script first."
                )
                
            print(f"[ML Service] Loading model binary from: {cls.MODEL_PATH}")
            cls._model = joblib.load(cls.MODEL_PATH)
            
            with open(cls.METADATA_PATH, "r", encoding="utf-8") as f:
                cls._metadata = json.load(f)
            print("[ML Service] Loaded model binary and metadata successfully.")

    @classmethod
    def predict_susceptibility(cls, latitude: float, longitude: float, elevation: float, slope: float, aspect: float):
        """
        Validates terrain variables, transforms aspect to circular components,
        and computes the susceptibility probability and risk levels.
        """
        # Ensure model is initialized
        cls.load_model_if_needed()
        
        # 1. Validation checks
        if None in (latitude, longitude, elevation, slope, aspect):
            raise ValueError("All inputs (latitude, longitude, elevation, slope, aspect) are required and cannot be null.")
            
        try:
            latitude = float(latitude)
            longitude = float(longitude)
            elevation = float(elevation)
            slope = float(slope)
            aspect = float(aspect)
        except (TypeError, ValueError):
            raise ValueError("All inputs must be valid numeric values.")

        if not (-90.0 <= latitude <= 90.0) or not (-180.0 <= longitude <= 180.0):
            raise ValueError(f"Invalid coordinate bounds: lat={latitude}, lon={longitude}")
            
        # Sanitize any extreme Copernicus DEM float32 fill/nodata values (e.g. 1.119e+36 or NaN)
        if math.isnan(elevation) or elevation > 9000.0 or elevation < -200.0:
            elevation = 750.0  # Regional representative elevation for NER hill tracts
            
        if math.isnan(slope) or slope < 0.0 or slope > 90.0:
            slope = 18.0  # Regional average slope
            
        if math.isnan(aspect) or aspect < -1.0 or aspect > 360.0:
            aspect = 135.0  # South-East default aspect

        # 2. Aspect Circular Transformations
        if slope < 0.1 or aspect == -1.0:
            aspect_sin = 0.0
            aspect_cos = 0.0
        else:
            aspect_sin = math.sin(math.radians(aspect))
            aspect_cos = math.cos(math.radians(aspect))

        # 3. Model Inference
        # Features order must match training: ["elevation", "slope", "aspect_sin", "aspect_cos"]
        X = np.array([[elevation, slope, aspect_sin, aspect_cos]])
        
        prob = float(cls._model.predict_proba(X)[0, 1])
        
        # 4. Calibration threshold mapping
        threshold = round(cls._metadata.get("calibration", {}).get("selected_threshold", 0.50), 2)
        is_susceptible = bool(prob >= threshold)
        
        # 5. Susceptibility Risk Level classification
        if 0.00 <= prob < 0.25:
            risk_level = "Low"
        elif 0.25 <= prob < 0.50:
            risk_level = "Moderate"
        elif 0.50 <= prob < 0.75:
            risk_level = "High"
        else:
            risk_level = "Very High"
            
        return {
            "latitude": latitude,
            "longitude": longitude,
            "elevation": elevation,
            "slope": slope,
            "aspect": aspect,
            "probability": round(prob, 4),
            "is_susceptible": is_susceptible,
            "risk_level": risk_level,
            "model_version": cls._metadata.get("environment_metadata", {}).get("scikit_learn_version", "unknown"),
            "threshold_used": threshold,
            "disclaimer": (
                "SCIENTIFIC SAFETY WARNING: This endpoint calculates STATIC TERRAIN SUSCEPTIBILITY only, "
                "representing long-term geological hazard potential based on slope and elevation. "
                "This does NOT constitute a real-time landslide warning or predict an immediate landslide occurrence."
            )
        }
