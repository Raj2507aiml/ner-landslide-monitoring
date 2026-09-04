"""
Unified Environmental Risk Engine - Phase 3.4
Combines Terrain, Rainfall, and Soil Moisture intelligence into an explainable,
weighted environmental landslide risk score (0-100).
"""

import concurrent.futures
from typing import Dict, Any, List, Optional

from app.services.terrain_service import analyze_point_terrain
from app.services.weather_service import analyze_rainfall
from app.services.soil_service import analyze_soil_moisture

# ---------------------------------------------------------------------------
# Centralized Weight Configuration (Calibratable via ML / Historical Data)
# ---------------------------------------------------------------------------
TERRAIN_WEIGHT = 0.35
RAINFALL_WEIGHT = 0.35
SOIL_WEIGHT = 0.30

# ---------------------------------------------------------------------------
# Centralized Risk Level to Base Numerical Score Conversion
# ---------------------------------------------------------------------------
def risk_level_to_score(risk_level: str) -> float:
    """
    Converts categorical risk levels into standard base numerical scores (0-100):
    - LOW       -> 20.0
    - MODERATE  -> 45.0
    - HIGH      -> 70.0
    - VERY_HIGH -> 90.0
    """
    if not isinstance(risk_level, str):
        return 20.0
    
    clean_level = risk_level.strip().upper().replace(" ", "_")
    mapping = {
        "LOW": 20.0,
        "MODERATE": 45.0,
        "HIGH": 70.0,
        "VERY_HIGH": 90.0
    }
    return mapping.get(clean_level, 20.0)


# ---------------------------------------------------------------------------
# Environmental Risk Classification
# ---------------------------------------------------------------------------
def classify_environmental_risk(score: float) -> str:
    """
    Categorizes unified environmental risk score into operational levels:
    - 0 to 25   -> LOW
    - 25 to 50  -> MODERATE
    - 50 to 75  -> HIGH
    - 75 to 100 -> VERY_HIGH
    """
    if score < 25.0:
        return "LOW"
    elif score <= 50.0:
        return "MODERATE"
    elif score <= 75.0:
        return "HIGH"
    else:
        return "VERY_HIGH"


# ---------------------------------------------------------------------------
# Factor Scoring Functions
# ---------------------------------------------------------------------------
def compute_terrain_score(terrain_data: Dict[str, Any]) -> float:
    """
    Computes a fine-grained terrain contribution score (0-100) combining
    categorical risk level and physical slope angle.
    """
    base = risk_level_to_score(terrain_data.get("terrain_risk_level", "LOW"))
    slope = float(terrain_data.get("slope_degrees", 0.0) or 0.0)
    
    # Continuous slope contribution curve
    if slope < 10.0:
        continuous_score = (slope / 10.0) * 30.0
    elif slope < 20.0:
        continuous_score = 30.0 + ((slope - 10.0) / 10.0) * 25.0
    elif slope < 30.0:
        continuous_score = 55.0 + ((slope - 20.0) / 10.0) * 25.0
    else:
        continuous_score = min(100.0, 80.0 + ((slope - 30.0) / 20.0) * 20.0)
    
    # Blend categorical score (60%) and continuous slope curve (40%)
    score = 0.60 * base + 0.40 * continuous_score
    return round(max(0.0, min(100.0, score)), 1)


def compute_rainfall_score(rainfall_data: Dict[str, Any]) -> float:
    """
    Computes rainfall trigger score (0-100) combining categorical risk level
    and multi-timescale antecedent precipitation accumulations.
    """
    base = risk_level_to_score(rainfall_data.get("rainfall_risk_level", "LOW"))
    r24 = float(rainfall_data.get("rainfall_last_24h_mm", 0.0) or 0.0)
    r3d = float(rainfall_data.get("rainfall_last_3_days_mm", 0.0) or 0.0)
    r7d = float(rainfall_data.get("rainfall_last_7_days_mm", 0.0) or 0.0)
    
    # Antecedent hydrological loading index
    accum_factor = min(100.0, (r24 / 80.0) * 40.0 + (r3d / 150.0) * 30.0 + (r7d / 250.0) * 30.0)
    
    score = 0.60 * base + 0.40 * accum_factor
    return round(max(0.0, min(100.0, score)), 1)


def compute_soil_score(soil_data: Dict[str, Any]) -> float:
    """
    Computes soil moisture saturation score (0-100) combining saturation risk
    and volumetric moisture percentage.
    """
    base = risk_level_to_score(soil_data.get("soil_saturation_risk", "LOW"))
    pct = float(soil_data.get("soil_moisture_percent", 0.0) or 0.0)
    
    score = 0.50 * base + 0.50 * pct
    return round(max(0.0, min(100.0, score)), 1)


# ---------------------------------------------------------------------------
# Explainability & Primary Contributor Generation
# ---------------------------------------------------------------------------
def generate_risk_factors(
    terrain_data: Optional[Dict[str, Any]],
    rainfall_data: Optional[Dict[str, Any]],
    soil_data: Optional[Dict[str, Any]],
    primary_factor: str
) -> List[str]:
    """
    Generates dynamic, authority-facing natural language explanation bullet points.
    """
    factors = []
    
    # 1. Terrain insights
    if terrain_data:
        slope = float(terrain_data.get("slope_degrees", 0.0) or 0.0)
        if slope >= 30.0:
            factors.append(f"Steep mountainous terrain ({slope:.1f}°) significantly magnifies gravitational shear stress")
        elif slope >= 15.0:
            factors.append(f"Moderate hillside gradient ({slope:.1f}°) presents susceptibility under prolonged rainfall")
        else:
            factors.append(f"Low hillside inclination ({slope:.1f}°) provides baseline terrain stability")
            
    # 2. Rainfall insights
    if rainfall_data:
        r24 = float(rainfall_data.get("rainfall_last_24h_mm", 0.0) or 0.0)
        r3d = float(rainfall_data.get("rainfall_last_3_days_mm", 0.0) or 0.0)
        if r24 >= 50.0 or r3d >= 100.0:
            factors.append(f"Severe recent precipitation ({r24:.1f} mm in 24h, {r3d:.1f} mm in 3d) induces heavy hydrodynamic loading")
        elif r24 >= 15.0 or r3d >= 35.0:
            factors.append(f"Recent antecedent rainfall ({r24:.1f} mm in 24h, {r3d:.1f} mm in 3d) contributes to gradual subsoil saturation")
        else:
            factors.append(f"Minimal recent rainfall ({r24:.1f} mm in 24h) minimizes dynamic triggering stress")
            
    # 3. Soil insights
    if soil_data:
        pct = float(soil_data.get("soil_moisture_percent", 0.0) or 0.0)
        condition = soil_data.get("soil_condition", "MOIST")
        if pct >= 60.0:
            factors.append(f"High volumetric soil moisture ({pct:.1f}%, {condition}) indicates elevated pore-water pressure and reduced soil shear strength")
        elif pct >= 35.0:
            factors.append(f"Moderate soil moisture ({pct:.1f}%, {condition}) retains partial drainage capacity")
        else:
            factors.append(f"Dry soil moisture profile ({pct:.1f}%, {condition}) indicates high available absorption capacity")
            
    return factors


def determine_primary_factor(
    terrain_contrib: float,
    rainfall_contrib: float,
    soil_contrib: float
) -> str:
    """
    Determines the single most influential environmental risk factor based on highest weighted contribution.
    """
    contributions = {
        "STEEP_TERRAIN": terrain_contrib,
        "HEAVY_RAINFALL": rainfall_contrib,
        "SOIL_SATURATION": soil_contrib
    }
    return max(contributions, key=contributions.get)


# ---------------------------------------------------------------------------
# Main Environmental Risk Calculation
# ---------------------------------------------------------------------------
def calculate_environmental_risk(latitude: float, longitude: float) -> Dict[str, Any]:
    """
    Executes the Unified Environmental Risk Engine:
    1. Validates coordinate bounds.
    2. Concurrently queries Terrain, Rainfall, and Soil Moisture services.
    3. Handles partial service failures gracefully via proportional weight redistribution.
    4. Computes fine-grained factor scores (0-100) and weighted environmental risk score (0-100).
    5. Categorizes overall risk level and determines primary contributing factor.
    6. Produces explainable natural language risk factors and data confidence indicators.
    """
    # 1. Coordinate validation
    if not (-90.0 <= latitude <= 90.0):
        raise ValueError(f"Latitude {latitude} is outside valid range [-90.0, 90.0].")
    if not (-180.0 <= longitude <= 180.0):
        raise ValueError(f"Longitude {longitude} is outside valid range [-180.0, 180.0].")

    terrain_data: Optional[Dict[str, Any]] = None
    rainfall_data: Optional[Dict[str, Any]] = None
    soil_data: Optional[Dict[str, Any]] = None

    # 2. Concurrently execute independent factor analyses with thread pool
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        fut_terrain = executor.submit(analyze_point_terrain, latitude, longitude)
        fut_rainfall = executor.submit(analyze_rainfall, latitude, longitude)
        fut_soil = executor.submit(analyze_soil_moisture, latitude, longitude)

        try:
            terrain_data = fut_terrain.result()
        except Exception:
            terrain_data = None

        try:
            rainfall_data = fut_rainfall.result()
        except Exception:
            rainfall_data = None

        try:
            soil_data = fut_soil.result()
        except Exception:
            soil_data = None

    # 3. Assess availability and handle partial failures
    available_factors = []
    if terrain_data: available_factors.append("terrain")
    if rainfall_data: available_factors.append("rainfall")
    if soil_data: available_factors.append("soil")

    if not available_factors:
        raise RuntimeError("All environmental factor services (Terrain, Rainfall, Soil) failed to return data.")

    # Confidence assessment
    if len(available_factors) == 3:
        confidence = "HIGH"
    elif len(available_factors) == 2:
        confidence = "MEDIUM"
    else:
        confidence = "LOW"

    data_availability = {
        "terrain": "AVAILABLE" if terrain_data else "UNAVAILABLE",
        "rainfall": "AVAILABLE" if rainfall_data else "UNAVAILABLE",
        "soil": "AVAILABLE" if soil_data else "UNAVAILABLE"
    }

    # 4. Proportional weight redistribution across available factors
    raw_weights = {
        "terrain": TERRAIN_WEIGHT if terrain_data else 0.0,
        "rainfall": RAINFALL_WEIGHT if rainfall_data else 0.0,
        "soil": SOIL_WEIGHT if soil_data else 0.0
    }
    sum_active_weights = sum(raw_weights.values())
    effective_weights = {k: (v / sum_active_weights) for k, v in raw_weights.items()}

    # 5. Compute individual factor scores (0-100)
    terrain_score = compute_terrain_score(terrain_data) if terrain_data else 0.0
    rainfall_score = compute_rainfall_score(rainfall_data) if rainfall_data else 0.0
    soil_score = compute_soil_score(soil_data) if soil_data else 0.0

    # 6. Calculate factor contributions and overall environmental score
    terrain_contrib = round(terrain_score * effective_weights["terrain"], 2)
    rainfall_contrib = round(rainfall_score * effective_weights["rainfall"], 2)
    soil_contrib = round(soil_score * effective_weights["soil"], 2)

    environmental_score = round(terrain_contrib + rainfall_contrib + soil_contrib, 1)
    environmental_score = max(0.0, min(100.0, environmental_score))

    # 7. Risk level and primary contributor
    environmental_risk_level = classify_environmental_risk(environmental_score)
    primary_factor = determine_primary_factor(terrain_contrib, rainfall_contrib, soil_contrib)

    # 8. Explainability factors
    risk_factors = generate_risk_factors(terrain_data, rainfall_data, soil_data, primary_factor)

    # 9. Format response structure
    terrain_payload = {
        "score": terrain_score,
        "risk_level": terrain_data.get("terrain_risk_level", "UNKNOWN") if terrain_data else "UNAVAILABLE",
        "slope_degrees": terrain_data.get("slope_degrees", 0.0) if terrain_data else None,
        "elevation_meters": terrain_data.get("elevation_meters", 0.0) if terrain_data else None
    }

    rainfall_payload = {
        "score": rainfall_score,
        "risk_level": rainfall_data.get("rainfall_risk_level", "UNKNOWN") if rainfall_data else "UNAVAILABLE",
        "rainfall_24h_mm": rainfall_data.get("rainfall_last_24h_mm", 0.0) if rainfall_data else None,
        "rainfall_3d_mm": rainfall_data.get("rainfall_last_3_days_mm", 0.0) if rainfall_data else None,
        "rainfall_7d_mm": rainfall_data.get("rainfall_last_7_days_mm", 0.0) if rainfall_data else None
    }

    soil_payload = {
        "score": soil_score,
        "risk_level": soil_data.get("soil_saturation_risk", "UNKNOWN") if soil_data else "UNAVAILABLE",
        "soil_moisture_percent": soil_data.get("soil_moisture_percent", 0.0) if soil_data else None
    }

    return {
        "latitude": round(float(latitude), 6),
        "longitude": round(float(longitude), 6),
        "environmental_risk_score": environmental_score,
        "environmental_risk_level": environmental_risk_level,
        "terrain": terrain_payload,
        "rainfall": rainfall_payload,
        "soil": soil_payload,
        "factor_contributions": {
            "terrain": terrain_contrib,
            "rainfall": rainfall_contrib,
            "soil": soil_contrib
        },
        "primary_contributing_factor": primary_factor,
        "risk_factors": risk_factors,
        "confidence": confidence,
        "data_availability": data_availability
    }
