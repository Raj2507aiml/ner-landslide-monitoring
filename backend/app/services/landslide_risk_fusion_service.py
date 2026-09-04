"""
Unified Landslide Risk Fusion Engine - Phase 6
Combines live Environmental Risk and Historical Landslide Susceptibility
into a single, explainable, weighted Unified Landslide Risk Score (0-100).
"""

import concurrent.futures
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from app.database.session import SessionLocal
from app.services.environmental_risk_service import calculate_environmental_risk
from app.services.historical_risk_service import analyze_historical_context

# ---------------------------------------------------------------------------
# Centralized Fusion Weights (Calibratable Parameters)
# ---------------------------------------------------------------------------
ENVIRONMENTAL_WEIGHT = 0.60
HISTORICAL_WEIGHT = 0.40


# ---------------------------------------------------------------------------
# Unified Risk Classification
# ---------------------------------------------------------------------------
def classify_unified_risk(score: float) -> str:
    """
    Classifies unified landslide risk score into operational hazard categories:
    - 0 to 25   -> LOW
    - 25 to 50  -> MODERATE
    - 50 to 75  -> HIGH
    - 75 to 100 -> VERY_HIGH
    """
    if score <= 25.0:
        return "LOW"
    elif score <= 50.0:
        return "MODERATE"
    elif score <= 75.0:
        return "HIGH"
    else:
        return "VERY_HIGH"


# ---------------------------------------------------------------------------
# Primary Risk Driver Determination
# ---------------------------------------------------------------------------
def determine_primary_risk_driver(env_contrib: float, hist_contrib: float, delta_threshold: float = 4.0) -> str:
    """
    Determines the dominant source of landslide risk based on weighted contributions:
    - ENVIRONMENTAL_CONDITIONS: Dynamic environmental triggers dominate
    - HISTORICAL_SUSCEPTIBILITY: Baseline historical terrain susceptibility dominates
    - BALANCED: Both sources contribute comparably within delta_threshold
    """
    diff = env_contrib - hist_contrib
    if abs(diff) <= delta_threshold:
        return "BALANCED"
    elif diff > 0:
        return "ENVIRONMENTAL_CONDITIONS"
    else:
        return "HISTORICAL_SUSCEPTIBILITY"


# ---------------------------------------------------------------------------
# Situational Trend Analysis
# ---------------------------------------------------------------------------
def determine_situation_status(
    env_score: float,
    hist_score: float,
    env_available: bool,
    hist_available: bool
) -> str:
    """
    Generates situational operational threat status (STABLE, ELEVATED, ESCALATING, CRITICAL)
    based on the interaction between current triggering conditions and underlying susceptibility:
    - CRITICAL: Confluence of high environmental triggers and high historical susceptibility
    - ESCALATING: Dynamic environmental triggers actively rising on susceptible terrain
    - ELEVATED: Significant underlying historical susceptibility or moderate triggering
    - STABLE: Low dynamic triggers and low baseline susceptibility
    """
    if not env_available and not hist_available:
        return "UNKNOWN"
    
    if (env_score >= 50.0 and hist_score >= 50.0) or (env_score >= 75.0 or hist_score >= 85.0):
        return "CRITICAL"
    elif env_score >= 45.0 and hist_score >= 30.0:
        return "ESCALATING"
    elif env_score >= 30.0 or hist_score >= 40.0:
        return "ELEVATED"
    else:
        return "STABLE"


# ---------------------------------------------------------------------------
# Explainability Factor Generation
# ---------------------------------------------------------------------------
def generate_fusion_risk_factors(
    env_data: Optional[Dict[str, Any]],
    hist_data: Optional[Dict[str, Any]],
    env_contrib: float,
    hist_contrib: float,
    primary_driver: str,
    situation: str
) -> List[str]:
    """Generates dynamic, authority-facing natural language explanation bullet points."""
    factors = []
    
    if env_data and hist_data:
        factors.append(
            f"Current environmental conditions contribute {env_contrib:.1f} points to the unified score (Level: {env_data.get('environmental_risk_level', 'UNKNOWN')})"
        )
        
        nearby_cnt = hist_data.get("nearby_incident_count", 0)
        nearest_km = hist_data.get("nearest_incident", {}).get("distance_km")
        if nearby_cnt > 0 and nearest_km is not None:
            factors.append(
                f"Historical landslide susceptibility contributes {hist_contrib:.1f} points ({nearby_cnt} recorded incidents within search radius, nearest at {nearest_km:.1f} km)"
            )
        elif nearby_cnt > 0:
            factors.append(
                f"Historical landslide susceptibility contributes {hist_contrib:.1f} points ({nearby_cnt} recorded incidents within search radius)"
            )
        else:
            factors.append(
                f"Historical landslide susceptibility contributes {hist_contrib:.1f} points (0 recorded historical incidents in search radius)"
            )
            
        # Situation-driven synthesis
        if situation == "CRITICAL":
            factors.append("Severe confluence of heavy dynamic environmental triggering and high historical ground susceptibility")
        elif situation == "ESCALATING":
            factors.append("Active hydrological loading and terrain slope are actively escalating slope instability")
        elif situation == "ELEVATED":
            factors.append("Elevated risk profile driven primarily by underlying geoscientific terrain susceptibility")
        else:
            factors.append("Current environmental triggers and baseline historical susceptibility indicate stable ground conditions")
            
        if env_data.get("primary_contributing_factor"):
            prim_env = env_data["primary_contributing_factor"].replace("_", " ").title()
            factors.append(f"Primary environmental trigger identified as: {prim_env}")
            
    elif env_data:
        factors.append(
            f"Environmental conditions contribute {env_contrib:.1f} points (100% normalized weight due to historical data absence)"
        )
        factors.append("Assessment reflects solely dynamic environmental indicators")
    elif hist_data:
        factors.append(
            f"Historical susceptibility contributes {hist_contrib:.1f} points (100% normalized weight due to environmental data absence)"
        )
        factors.append("Assessment reflects solely baseline historical catalog evidence")
        
    return factors


# ---------------------------------------------------------------------------
# Main Unified Landslide Risk Fusion
# ---------------------------------------------------------------------------
def calculate_unified_landslide_risk(
    latitude: float,
    longitude: float,
    radius_km: float = 10.0,
    db: Optional[Session] = None
) -> Dict[str, Any]:
    """
    Executes the Unified Landslide Risk Fusion Engine:
    1. Validates coordinate bounds and search radius.
    2. Concurrently queries Environmental Risk Service and Historical Context Service.
    3. Handles partial service failures gracefully via proportional weight redistribution.
    4. Combines scores using centralized weights (Environmental: 60%, Historical: 40%).
    5. Determines unified risk level, primary risk driver, and situational threat status.
    6. Produces explainable natural-language statements and data confidence assessment.
    """
    # 1. Coordinate & radius validation
    if not (-90.0 <= latitude <= 90.0):
        raise ValueError(f"Latitude {latitude} is outside valid range [-90.0, 90.0].")
    if not (-180.0 <= longitude <= 180.0):
        raise ValueError(f"Longitude {longitude} is outside valid range [-180.0, 180.0].")
    if not (1.0 <= radius_km <= 100.0):
        raise ValueError(f"Search radius {radius_km} km is outside valid range [1.0, 100.0] km.")

    env_data: Optional[Dict[str, Any]] = None
    hist_data: Optional[Dict[str, Any]] = None

    # 2. Concurrently execute independent analyses with thread pool
    def _fetch_env():
        return calculate_environmental_risk(latitude=latitude, longitude=longitude)

    def _fetch_hist():
        if db is not None:
            return analyze_historical_context(db=db, latitude=latitude, longitude=longitude, radius_km=radius_km)
        else:
            with SessionLocal() as local_db:
                return analyze_historical_context(db=local_db, latitude=latitude, longitude=longitude, radius_km=radius_km)

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        fut_env = executor.submit(_fetch_env)
        fut_hist = executor.submit(_fetch_hist)

        try:
            env_data = fut_env.result()
        except Exception:
            env_data = None

        try:
            hist_data = fut_hist.result()
        except Exception:
            hist_data = None

    # 3. Partial Failure Handling & Dynamic Weight Redistribution
    if not env_data and not hist_data:
        raise RuntimeError("Both Environmental Risk and Historical Context services failed to return data.")

    env_available = env_data is not None
    hist_available = hist_data is not None

    if env_available and hist_available:
        eff_env_weight = ENVIRONMENTAL_WEIGHT
        eff_hist_weight = HISTORICAL_WEIGHT
        env_conf = env_data.get("confidence", "HIGH")
        hist_conf = hist_data.get("confidence", "HIGH")
        if env_conf == "HIGH" and hist_conf == "HIGH":
            confidence = "HIGH"
        elif "LOW" in (env_conf, hist_conf):
            confidence = "MEDIUM"
        else:
            confidence = "HIGH"
    elif env_available:
        eff_env_weight = 1.0
        eff_hist_weight = 0.0
        confidence = "MEDIUM"
    else:  # hist_available
        eff_env_weight = 0.0
        eff_hist_weight = 1.0
        confidence = "MEDIUM"

    env_score = float(env_data.get("environmental_risk_score", 0.0)) if env_data else 0.0
    hist_score = float(hist_data.get("historical_susceptibility_score", 0.0)) if hist_data else 0.0

    env_contrib = round(env_score * eff_env_weight, 2)
    hist_contrib = round(hist_score * eff_hist_weight, 2)

    unified_score = round(env_contrib + hist_contrib, 1)
    unified_score = max(0.0, min(100.0, unified_score))

    unified_level = classify_unified_risk(unified_score)
    primary_driver = determine_primary_risk_driver(env_contrib, hist_contrib)
    situation_status = determine_situation_status(env_score, hist_score, env_available, hist_available)

    risk_factors = generate_fusion_risk_factors(
        env_data=env_data,
        hist_data=hist_data,
        env_contrib=env_contrib,
        hist_contrib=hist_contrib,
        primary_driver=primary_driver,
        situation=situation_status
    )

    environmental_payload = {
        "available": env_available,
        "score": env_score if env_available else None,
        "risk_level": env_data.get("environmental_risk_level", "UNAVAILABLE") if env_data else "UNAVAILABLE",
        "contribution": env_contrib
    }

    historical_payload = {
        "available": hist_available,
        "score": hist_score if hist_available else None,
        "risk_level": hist_data.get("historical_risk_level", "UNAVAILABLE") if hist_data else "UNAVAILABLE",
        "contribution": hist_contrib,
        "nearby_incident_count": hist_data.get("nearby_incident_count", 0) if hist_data else None
    }

    data_availability = {
        "environmental": "AVAILABLE" if env_available else "UNAVAILABLE",
        "historical": "AVAILABLE" if hist_available else "UNAVAILABLE"
    }

    return {
        "latitude": round(float(latitude), 6),
        "longitude": round(float(longitude), 6),
        "search_radius_km": round(float(radius_km), 1),
        "unified_landslide_risk_score": unified_score,
        "unified_landslide_risk_level": unified_level,
        "environmental": environmental_payload,
        "historical": historical_payload,
        "primary_risk_driver": primary_driver,
        "situation_status": situation_status,
        "risk_factors": risk_factors,
        "confidence": confidence,
        "data_availability": data_availability
    }
