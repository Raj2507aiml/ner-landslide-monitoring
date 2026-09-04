"""
Multi-Source Landslide Risk Fusion Engine - Phase 8
Dynamically orchestrates and fuses three independent intelligence pillars:
1. Environmental Risk Intelligence (Terrain, Rainfall, Soil Moisture)
2. Historical Landslide Context (GSI/NASA catalog, spatial density, proximity)
3. Satellite Change Intelligence (Sentinel-1 SAR multi-temporal backscatter & RSCI)

Implements dynamic weight normalization, multi-source convergence detection,
primary driver isolation, operational situation status, and explainable insights.
"""

import concurrent.futures
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from app.database.session import SessionLocal
from app.services.environmental_risk_service import calculate_environmental_risk
from app.services.historical_risk_service import analyze_historical_context
from app.services.satellite_intelligence_service import analyze_satellite_change_intelligence


# ---------------------------------------------------------------------------
# Centralized Fusion Weights (Initial Calibration Parameters)
# ---------------------------------------------------------------------------
ENVIRONMENTAL_WEIGHT = 0.45
HISTORICAL_WEIGHT = 0.30
SATELLITE_WEIGHT = 0.25

# ---------------------------------------------------------------------------
# Centralized Risk Thresholds
# ---------------------------------------------------------------------------
MULTISOURCE_RISK_LOW_THRESHOLD = 25.0
MULTISOURCE_RISK_MODERATE_THRESHOLD = 50.0
MULTISOURCE_RISK_HIGH_THRESHOLD = 75.0

BALANCED_DRIVER_DELTA_THRESHOLD = 4.0


# ---------------------------------------------------------------------------
# Multi-Source Risk Classification
# ---------------------------------------------------------------------------
def classify_multisource_risk(score: float) -> str:
    """
    Classifies multi-source landslide risk score into operational hazard categories:
    - 0.0 to 25.0  -> LOW
    - 25.0 to 50.0 -> MODERATE
    - 50.0 to 75.0 -> HIGH
    - 75.0 to 100.0 -> VERY_HIGH
    """
    if score <= MULTISOURCE_RISK_LOW_THRESHOLD:
        return "LOW"
    elif score <= MULTISOURCE_RISK_MODERATE_THRESHOLD:
        return "MODERATE"
    elif score <= MULTISOURCE_RISK_HIGH_THRESHOLD:
        return "HIGH"
    else:
        return "VERY_HIGH"


# ---------------------------------------------------------------------------
# Primary Risk Driver Determination
# ---------------------------------------------------------------------------
def determine_primary_risk_driver(
    env_contrib: float,
    hist_contrib: float,
    sat_contrib: float,
    delta_threshold: float = BALANCED_DRIVER_DELTA_THRESHOLD
) -> str:
    """
    Determines the dominant risk driver based on active weighted contribution.
    If the top contributions are within delta_threshold of each other, classifies as BALANCED.
    """
    contributions = [
        ("ENVIRONMENTAL_CONDITIONS", env_contrib),
        ("HISTORICAL_SUSCEPTIBILITY", hist_contrib),
        ("SATELLITE_SURFACE_CHANGE", sat_contrib)
    ]
    contributions.sort(key=lambda x: x[1], reverse=True)

    top_name, top_val = contributions[0]
    second_name, second_val = contributions[1]

    # If top value is 0, or top two are within threshold and both positive
    if top_val > 0 and (top_val - second_val) <= delta_threshold:
        return "BALANCED"

    if top_val == 0:
        return "BALANCED"

    return top_name


# ---------------------------------------------------------------------------
# Risk Convergence Detection
# ---------------------------------------------------------------------------
def detect_risk_convergence(
    env_score: Optional[float],
    hist_score: Optional[float],
    sat_score: Optional[float]
) -> str:
    """
    Detects convergence across the three intelligence sources based on elevated signals:
    - SEVERE: All three sources exhibit elevated/high risk (>= 50.0) or fused score >= 75.0
    - STRONG: Two sources exhibit high risk (>= 50.0)
    - PARTIAL: One source exhibits high risk (>= 50.0) or multiple sources exhibit moderate risk (>= 30.0)
    - NONE: Baseline low activity across all available indicators
    """
    scores = [s for s in (env_score, hist_score, sat_score) if s is not None]
    if not scores:
        return "NONE"

    high_count = sum(1 for s in scores if s >= 50.0)
    moderate_count = sum(1 for s in scores if s >= 30.0)

    if len(scores) == 3 and high_count == 3:
        return "SEVERE"
    elif high_count >= 2:
        return "STRONG"
    elif high_count == 1 or moderate_count >= 2:
        return "PARTIAL"
    else:
        return "NONE"


# ---------------------------------------------------------------------------
# Operational Situation Status
# ---------------------------------------------------------------------------
def determine_operational_status(
    fused_score: float,
    env_score: Optional[float],
    hist_score: Optional[float],
    sat_score: Optional[float],
    convergence: str
) -> str:
    """
    Determines operational situational assessment (STABLE, WATCH, ELEVATED, ESCALATING, CRITICAL)
    by analyzing the interaction between dynamic environmental triggers, historical ground susceptibility,
    and satellite-observed surface backscatter changes.
    """
    e_val = env_score or 0.0
    h_val = hist_score or 0.0
    s_val = sat_score or 0.0

    if fused_score >= 75.0 or convergence == "SEVERE" or (e_val >= 60.0 and h_val >= 60.0 and s_val >= 50.0):
        return "CRITICAL"
    elif fused_score >= 50.0 and (e_val >= 45.0 or s_val >= 45.0) and h_val >= 40.0:
        return "ESCALATING"
    elif fused_score >= 40.0 or e_val >= 45.0 or s_val >= 45.0 or convergence == "STRONG":
        return "ELEVATED"
    elif fused_score >= 25.0 or h_val >= 35.0 or e_val >= 25.0:
        return "WATCH"
    else:
        return "STABLE"


# ---------------------------------------------------------------------------
# Explainability Factor Generator
# ---------------------------------------------------------------------------
def generate_multisource_risk_factors(
    env_data: Optional[Dict[str, Any]],
    hist_data: Optional[Dict[str, Any]],
    sat_data: Optional[Dict[str, Any]],
    env_contrib: float,
    hist_contrib: float,
    sat_contrib: float,
    active_weights: Dict[str, float],
    primary_driver: str,
    operational_status: str,
    convergence: str
) -> List[str]:
    """Generates dynamic, evidence-backed natural language explainability statements."""
    factors: List[str] = []

    # 1. Environmental Contribution
    if env_data and env_data.get("environmental_risk_score") is not None:
        e_score = env_data["environmental_risk_score"]
        e_level = env_data.get("environmental_risk_level", "UNKNOWN")
        w_pct = active_weights["environmental"] * 100.0
        factors.append(
            f"Current environmental conditions contribute {env_contrib:.1f} points ({w_pct:.0f}% active weight, Score: {e_score:.1f}, Level: {e_level})"
        )
        if env_data.get("primary_contributing_factor"):
            prim_env = env_data["primary_contributing_factor"].replace("_", " ").title()
            factors.append(f"Primary environmental trigger identified as: {prim_env}")
    else:
        factors.append("Environmental risk telemetry was unavailable; fusion weights were redistributed dynamically")

    # 2. Historical Context Contribution
    if hist_data and hist_data.get("historical_susceptibility_score") is not None:
        h_score = hist_data["historical_susceptibility_score"]
        h_level = hist_data.get("historical_risk_level", "UNKNOWN")
        nearby_cnt = hist_data.get("nearby_incident_count", 0)
        w_pct = active_weights["historical"] * 100.0
        if nearby_cnt > 0:
            nearest_km = hist_data.get("nearest_incident", {}).get("distance_km")
            dist_str = f", nearest at {nearest_km:.1f} km" if nearest_km is not None else ""
            factors.append(
                f"Historical landslide context contributes {hist_contrib:.1f} points ({w_pct:.0f}% active weight, {nearby_cnt} recorded incidents{dist_str})"
            )
        else:
            factors.append(
                f"Historical landslide context contributes {hist_contrib:.1f} points ({w_pct:.0f}% active weight, 0 recorded historical incidents in search radius)"
            )
    else:
        factors.append("Historical catalog data was unavailable; fusion weights were redistributed dynamically")

    # 3. Satellite SAR Contribution
    if sat_data and sat_data.get("satellite_data_available"):
        s_score = sat_data.get("satellite_change_score", 0.0)
        s_level = sat_data.get("satellite_risk_level", "UNKNOWN")
        rsci = sat_data.get("radar_surface_change_index")
        w_pct = active_weights["satellite"] * 100.0
        rsci_str = f", RSCI: {rsci:.1f}" if rsci is not None else ""
        factors.append(
            f"Sentinel-1 satellite radar change intelligence contributes {sat_contrib:.1f} points ({w_pct:.0f}% active weight{rsci_str}, Level: {s_level})"
        )
        if sat_data.get("orbit_direction") and sat_data.get("temporal_baseline_days"):
            factors.append(
                f"Satellite observation based on {sat_data['orbit_direction']} orbit with {sat_data['temporal_baseline_days']:.0f}-day temporal baseline"
            )
    else:
        reason = sat_data.get("data_unavailability_reason") if sat_data else "Satellite pair unavailable"
        factors.append(f"Satellite change intelligence unavailable ({reason}); weights normalized across active sensors")

    # 4. Convergence and Situation Synthesis
    if convergence == "SEVERE":
        factors.append("Severe multi-source convergence: dynamic triggers, ground susceptibility, and SAR surface disturbance are all elevated simultaneously")
    elif convergence == "STRONG":
        factors.append("Strong multi-source convergence detected between two primary risk intelligence dimensions")
    elif convergence == "PARTIAL":
        factors.append("Partial risk convergence observed with localized trigger elevation")

    if operational_status == "CRITICAL":
        factors.append("Operational assessment flagged at CRITICAL: urgent safety verification and heightened monitoring advised")
    elif operational_status == "ESCALATING":
        factors.append("Operational assessment flagged at ESCALATING: active triggering on susceptible slope terrain")
    elif operational_status == "ELEVATED":
        factors.append("Operational assessment flagged at ELEVATED: moderate-to-high baseline susceptibility with active factors")
    elif operational_status == "WATCH":
        factors.append("Operational assessment flagged at WATCH: routine increased vigilance for changing meteorological conditions")
    else:
        factors.append("Operational assessment flagged at STABLE: current triggers and baseline indicators remain within normal bounds")

    return factors


# ---------------------------------------------------------------------------
# Main Multi-Source Risk Fusion Engine
# ---------------------------------------------------------------------------
def calculate_multisource_landslide_risk(
    latitude: float,
    longitude: float,
    radius_km: float = 10.0,
    satellite_radius_km: float = 5.0,
    db: Optional[Session] = None
) -> Dict[str, Any]:
    """
    Executes the Multi-Source Landslide Risk Fusion Engine (Phase 8):
    1. Validates coordinate bounds and search radii.
    2. Concurrently fetches Environmental Risk, Historical Context, and Satellite Change Intelligence.
    3. Handles partial failures gracefully through proportional dynamic weight redistribution.
    4. Computes fused multi-source score (0-100), risk level, and primary driver.
    5. Analyzes multi-source convergence and operational situation status.
    6. Generates dynamic explainable risk statements and data confidence assessment.
    """
    # 1. Geographic Coordinate and Radius Validation
    if not (-90.0 <= latitude <= 90.0):
        raise ValueError(f"Latitude {latitude} is outside valid range [-90.0, 90.0].")
    if not (-180.0 <= longitude <= 180.0):
        raise ValueError(f"Longitude {longitude} is outside valid range [-180.0, 180.0].")
    if not (1.0 <= radius_km <= 100.0):
        raise ValueError(f"Historical radius {radius_km} km is outside valid range [1.0, 100.0] km.")
    if not (0.1 <= satellite_radius_km <= 25.0):
        raise ValueError(f"Satellite AOI radius {satellite_radius_km} km is outside valid range [0.1, 25.0] km.")

    env_data: Optional[Dict[str, Any]] = None
    hist_data: Optional[Dict[str, Any]] = None
    sat_data: Optional[Dict[str, Any]] = None

    # 2. Concurrently execute independent analyses with ThreadPoolExecutor
    def _fetch_env():
        return calculate_environmental_risk(latitude=latitude, longitude=longitude)

    def _fetch_hist():
        if db is not None:
            return analyze_historical_context(db=db, latitude=latitude, longitude=longitude, radius_km=radius_km)
        else:
            with SessionLocal() as local_db:
                return analyze_historical_context(db=local_db, latitude=latitude, longitude=longitude, radius_km=radius_km)

    def _fetch_sat():
        return analyze_satellite_change_intelligence(latitude=latitude, longitude=longitude, radius_km=satellite_radius_km)

    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        fut_env = executor.submit(_fetch_env)
        fut_hist = executor.submit(_fetch_hist)
        fut_sat = executor.submit(_fetch_sat)

        try:
            env_data = fut_env.result()
        except Exception:
            env_data = None

        try:
            hist_data = fut_hist.result()
        except Exception:
            hist_data = None

        try:
            sat_data = fut_sat.result()
        except Exception:
            sat_data = None

    # 3. Determine Availability Flags
    env_avail = bool(env_data and env_data.get("environmental_risk_score") is not None)
    hist_avail = bool(hist_data and hist_data.get("historical_susceptibility_score") is not None)
    sat_avail = bool(sat_data and sat_data.get("satellite_data_available") and sat_data.get("satellite_change_score") is not None)

    # If all sources fail, raise controlled RuntimeError (mapped to HTTP 502)
    if not env_avail and not hist_avail and not sat_avail:
        raise RuntimeError("All multi-source risk intelligence layers (Environmental, Historical, Satellite) failed to return data.")

    # 4. Dynamic Weight Normalization
    base_weights = {
        "environmental": ENVIRONMENTAL_WEIGHT if env_avail else 0.0,
        "historical": HISTORICAL_WEIGHT if hist_avail else 0.0,
        "satellite": SATELLITE_WEIGHT if sat_avail else 0.0
    }
    weight_sum = base_weights["environmental"] + base_weights["historical"] + base_weights["satellite"]

    if weight_sum > 0:
        active_weights = {
            "environmental": round(base_weights["environmental"] / weight_sum, 4),
            "historical": round(base_weights["historical"] / weight_sum, 4),
            "satellite": round(base_weights["satellite"] / weight_sum, 4)
        }
    else:
        active_weights = {"environmental": 0.0, "historical": 0.0, "satellite": 0.0}

    # 5. Extract Individual Pillar Scores & Weighted Contributions
    env_score = float(env_data["environmental_risk_score"]) if env_avail else None
    hist_score = float(hist_data["historical_susceptibility_score"]) if hist_avail else None
    sat_score = float(sat_data["satellite_change_score"]) if sat_avail else None

    env_contrib = round((env_score or 0.0) * active_weights["environmental"], 2)
    hist_contrib = round((hist_score or 0.0) * active_weights["historical"], 2)
    sat_contrib = round((sat_score or 0.0) * active_weights["satellite"], 2)

    # 6. Calculate Final Fused Multi-Source Score (0-100)
    raw_fused_score = env_contrib + hist_contrib + sat_contrib
    multisource_score = round(max(0.0, min(100.0, raw_fused_score)), 1)
    multisource_level = classify_multisource_risk(multisource_score)

    # 7. Convergence, Primary Driver, and Operational Status
    primary_driver = determine_primary_risk_driver(env_contrib, hist_contrib, sat_contrib)
    convergence = detect_risk_convergence(env_score, hist_score, sat_score)
    operational_status = determine_operational_status(multisource_score, env_score, hist_score, sat_score, convergence)

    # 8. Confidence Evaluation
    available_count = sum([env_avail, hist_avail, sat_avail])
    if available_count == 3:
        confidence = "HIGH"
    elif available_count == 2:
        confidence = "MEDIUM"
    else:
        confidence = "LOW"

    # 9. Dynamic Explainability Factors
    risk_factors = generate_multisource_risk_factors(
        env_data=env_data,
        hist_data=hist_data,
        sat_data=sat_data,
        env_contrib=env_contrib,
        hist_contrib=hist_contrib,
        sat_contrib=sat_contrib,
        active_weights=active_weights,
        primary_driver=primary_driver,
        operational_status=operational_status,
        convergence=convergence
    )

    # 10. Structured Payloads
    environmental_payload = {
        "available": env_avail,
        "score": env_score,
        "risk_level": env_data.get("environmental_risk_level") if env_avail else None,
        "active_weight": active_weights["environmental"],
        "contribution": env_contrib
    }

    historical_payload = {
        "available": hist_avail,
        "score": hist_score,
        "risk_level": hist_data.get("historical_risk_level") if hist_avail else None,
        "active_weight": active_weights["historical"],
        "contribution": hist_contrib,
        "nearby_incident_count": hist_data.get("nearby_incident_count") if hist_avail else None
    }

    satellite_payload = {
        "available": sat_avail,
        "score": sat_score,
        "risk_level": sat_data.get("satellite_risk_level") if sat_avail else None,
        "active_weight": active_weights["satellite"],
        "contribution": sat_contrib,
        "confidence": sat_data.get("confidence") if sat_data else "LOW"
    }

    data_availability = {
        "environmental": "AVAILABLE" if env_avail else "UNAVAILABLE",
        "historical": "AVAILABLE" if hist_avail else "UNAVAILABLE",
        "satellite": "AVAILABLE" if sat_avail else "UNAVAILABLE"
    }

    return {
        "latitude": round(float(latitude), 6),
        "longitude": round(float(longitude), 6),
        "multisource_landslide_risk_score": multisource_score,
        "multisource_landslide_risk_level": multisource_level,
        "operational_status": operational_status,
        "risk_convergence": convergence,
        "environmental": environmental_payload,
        "historical": historical_payload,
        "satellite": satellite_payload,
        "primary_risk_driver": primary_driver,
        "risk_factors": risk_factors,
        "confidence": confidence,
        "data_availability": data_availability
    }
