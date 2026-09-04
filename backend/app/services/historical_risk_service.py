"""
Historical Landslide Context Engine - Phase 3.5
Analyzes geographic historical landslide context, incident density, proximity,
and recency to determine historical susceptibility scores (0-100).
"""

import math
from datetime import datetime, date
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from app.services.spatial_query_service import (
    haversine_distance,
    get_historical_landslide_context,
    validate_inputs
)

# ---------------------------------------------------------------------------
# Centralized Weight Constants (Heuristically Calibrated)
# ---------------------------------------------------------------------------
FREQUENCY_WEIGHT = 0.40
DISTANCE_WEIGHT = 0.30
DENSITY_WEIGHT = 0.20
RECENCY_WEIGHT = 0.10

# ---------------------------------------------------------------------------
# Distance & Density Helpers
# ---------------------------------------------------------------------------
def calculate_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculates great-circle distance between two geographic coordinates in kilometers."""
    return haversine_distance(lat1, lon1, lat2, lon2)


def calculate_incident_density(incident_count: int, radius_km: float) -> float:
    """Calculates incident density in incidents per square kilometer."""
    if radius_km <= 0.0 or incident_count <= 0:
        return 0.0
    area_sq_km = math.pi * (radius_km ** 2)
    return round(incident_count / area_sq_km, 4)


# ---------------------------------------------------------------------------
# Factor Scoring Functions (0 to 100)
# ---------------------------------------------------------------------------
def calculate_frequency_score(incident_count: int, radius_km: float = 10.0) -> float:
    """
    Computes frequency score (0-100) based on incident count within search radius.
    Logarithmic curve scaled so 20+ incidents in a 10km radius maps to ~90-100.
    """
    if incident_count <= 0:
        return 0.0
    
    # Scale with expected density relative to standard 10km radius
    radius_scale = max(0.2, min(5.0, (10.0 / radius_km) ** 0.5))
    effective_count = incident_count * radius_scale
    
    # Logarithmic saturation curve
    score = (math.log(effective_count + 1.0) / math.log(25.0)) * 100.0
    return round(min(100.0, max(0.0, score)), 1)


def calculate_distance_score(nearest_distance_km: Optional[float], radius_km: float = 10.0) -> float:
    """
    Computes proximity score (0-100). Closer incidents yield higher susceptibility scores.
    """
    if nearest_distance_km is None or nearest_distance_km > radius_km:
        return 0.0
    
    proximity_ratio = max(0.0, 1.0 - (nearest_distance_km / radius_km))
    # Sub-linear response to give significant weight to incidents within immediate vicinity (< 3km)
    score = 100.0 * (proximity_ratio ** 0.8)
    return round(min(100.0, max(0.0, score)), 1)


def calculate_density_score(density_per_sq_km: float) -> float:
    """
    Computes spatial density score (0-100).
    Density of 0.08+ incidents/sq.km in mountainous terrain maps towards 100.
    """
    if density_per_sq_km <= 0.0:
        return 0.0
    score = (density_per_sq_km / 0.08) * 100.0
    return round(min(100.0, max(0.0, score)), 1)


def calculate_recency_score(recent_incident_count: int, total_dated_incidents: int) -> float:
    """
    Computes recency score (0-100) based on dated incident occurrences.
    """
    if total_dated_incidents == 0:
        return 20.0  # Neutral baseline when dates are unspecified in records (e.g. GSI catalog)
    if recent_incident_count == 0:
        return 10.0
    score = 25.0 + (recent_incident_count * 20.0)
    return round(min(100.0, max(0.0, score)), 1)


# ---------------------------------------------------------------------------
# Risk Classification & Explainability
# ---------------------------------------------------------------------------
def classify_historical_risk(score: float) -> str:
    """
    Classifies historical susceptibility score into standard operational hazard levels:
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


def generate_historical_risk_factors(
    incident_count: int,
    radius_km: float,
    nearest_dist_km: Optional[float],
    density_per_sq_km: float,
    recent_count: int
) -> List[str]:
    """Generates explainable human-readable insight statements."""
    factors = []
    
    if incident_count == 0:
        factors.append(f"No historical landslide incidents were recorded within {radius_km:.0f} km")
        factors.append("Absence of recorded historical incidents does not eliminate intrinsic terrain susceptibility")
        return factors
    
    factors.append(f"{incident_count} historical landslide incident{'s were' if incident_count != 1 else ' was'} recorded within {radius_km:.0f} km")
    
    if nearest_dist_km is not None:
        if nearest_dist_km <= 1.0:
            factors.append(f"Immediate proximity to nearest recorded historical incident ({nearest_dist_km:.1f} km)")
        else:
            factors.append(f"The nearest recorded incident is approximately {nearest_dist_km:.1f} km away")
            
    if density_per_sq_km >= 0.05:
        factors.append("High concentration of historical incidents indicates significant local slope instability")
    elif density_per_sq_km >= 0.02:
        factors.append("The area shows moderate historical landslide density")
    else:
        factors.append("Low historical landslide density across the surrounding zone")
        
    if recent_count > 0:
        factors.append(f"{recent_count} incident{'s have' if recent_count != 1 else ' has'} documented recent activity")
        
    return factors


# ---------------------------------------------------------------------------
# Main Context Analysis Function
# ---------------------------------------------------------------------------
def analyze_historical_context(
    db: Session,
    latitude: float,
    longitude: float,
    radius_km: float = 10.0
) -> Dict[str, Any]:
    """
    Executes the Historical Landslide Context Engine:
    1. Validates coordinate bounds and search radius.
    2. Directly queries GSI and NASA historical databases via spatial query service.
    3. Calculates incident count, nearest distance, spatial density, and recency.
    4. Computes factor scores and weighted historical susceptibility score (0-100).
    5. Categorizes risk level, produces explainable risk factors, and evaluates data confidence.
    """
    # 1. Input validation
    validate_inputs(latitude, longitude, radius_km)
    
    # 2. Query spatial context from historical database
    context = get_historical_landslide_context(db, latitude, longitude, radius_km)
    
    total_obs = context["combined_summary"]["total_historical_observations"]
    nearest_dist = context["combined_summary"]["nearest_historical_observation_km"]
    
    # 3. Density calculation
    density = calculate_incident_density(total_obs, radius_km)
    
    # 4. Recent activity extraction (NASA records have parsed event dates)
    nasa_events = context.get("nasa_events", [])
    recent_count = 0
    dated_count = 0
    
    # We inspect dated events
    for event in nasa_events:
        evt_date_str = event.get("event_date")
        if evt_date_str:
            dated_count += 1
            try:
                evt_date = datetime.strptime(evt_date_str[:10], "%Y-%m-%d").date()
                # Consider events from 2010 onwards as recent relative to historical catalogs
                if evt_date.year >= 2010:
                    recent_count += 1
            except Exception:
                pass
                
    recent_data_available = dated_count > 0
    
    # 5. Calculate factor scores (0-100)
    freq_score = calculate_frequency_score(total_obs, radius_km)
    dist_score = calculate_distance_score(nearest_dist, radius_km)
    dens_score = calculate_density_score(density)
    rec_score = calculate_recency_score(recent_count, dated_count)
    
    # 6. Calculate weighted susceptibility score (0-100)
    if total_obs == 0:
        susceptibility_score = 0.0
        risk_level = "LOW"
    else:
        weighted_score = (
            (freq_score * FREQUENCY_WEIGHT) +
            (dist_score * DISTANCE_WEIGHT) +
            (dens_score * DENSITY_WEIGHT) +
            (rec_score * RECENCY_WEIGHT)
        )
        susceptibility_score = round(max(0.0, min(100.0, weighted_score)), 1)
        risk_level = classify_historical_risk(susceptibility_score)
        
    # 7. Generate explainability insights
    risk_factors = generate_historical_risk_factors(
        incident_count=total_obs,
        radius_km=radius_km,
        nearest_dist_km=nearest_dist,
        density_per_sq_km=density,
        recent_count=recent_count
    )
    
    # 8. Data confidence assessment
    if total_obs >= 5:
        confidence = "HIGH"
    elif total_obs >= 1:
        confidence = "MEDIUM"
    else:
        confidence = "MEDIUM"  # Clean spatial query completed with 0 results
        
    nearest_payload = {
        "distance_km": round(nearest_dist, 2) if nearest_dist is not None else None,
        "available": nearest_dist is not None
    }
    
    recent_payload = {
        "recent_incident_count": recent_count,
        "data_available": recent_data_available
    }
    
    return {
        "latitude": round(float(latitude), 6),
        "longitude": round(float(longitude), 6),
        "search_radius_km": round(float(radius_km), 1),
        "nearby_incident_count": total_obs,
        "nearest_incident": nearest_payload,
        "incident_density_per_sq_km": density,
        "recent_activity": recent_payload,
        "historical_susceptibility_score": susceptibility_score,
        "historical_risk_level": risk_level,
        "factor_scores": {
            "frequency": freq_score,
            "distance": dist_score,
            "density": dens_score,
            "recency": rec_score
        },
        "risk_factors": risk_factors,
        "historical_data_available": True,
        "confidence": confidence
    }
