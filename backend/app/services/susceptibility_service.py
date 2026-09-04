import math
from typing import Optional
from sqlalchemy.orm import Session
from app.services.spatial_query_service import get_historical_landslide_context

def calculate_susceptibility_score(
    db: Session,
    latitude: float,
    longitude: float,
    radius_km: float = 10.0,
    slope: Optional[float] = None,
    rainfall: Optional[float] = None,
    rainfall_3d: Optional[float] = None,
    rainfall_7d: Optional[float] = None
) -> dict:
    """
    Computes a heuristic landslide hazard susceptibility score (0-100) combining:
    1. Historical landslide evidence (proximity and local density)
    2. Terrain slope predisposition (slope in degrees)
    3. Antecedent precipitation trigger conditions (24h intensity, 3-day and 7-day cumulative sums)
    
    Supports partial input normalization when terrain or weather data is unavailable.
    """
    # ── 1. HISTORICAL COMPONENT (MAX 40) ───────────────────────────────────
    context = get_historical_landslide_context(db, latitude, longitude, radius_km)
    
    total_obs = context["combined_summary"]["total_historical_observations"]
    nearest_dist = context["combined_summary"]["nearest_historical_observation_km"]
    
    # Proximity Score (Max 25)
    if total_obs == 0 or nearest_dist is None:
        proximity_score = 0.0
    else:
        proximity_score = 25.0 * (1.0 - min(nearest_dist / radius_km, 1.0))
    # Clamp proximity score between 0.0 and 25.0
    proximity_score = max(0.0, min(25.0, proximity_score))
    
    # Density Score (Max 15)
    if total_obs == 0:
        density_score = 0.0
    else:
        # density = 15 * ln(n + 1) / ln(21)
        density_score = 15.0 * math.log(total_obs + 1) / math.log(21.0)
    # Clamp density score to a maximum of 15.0
    density_score = max(0.0, min(15.0, density_score))
    
    historical_score = proximity_score + density_score
    historical_max = 40.0
    
    # ── 2. TERRAIN COMPONENT (MAX 30) ──────────────────────────────────────
    terrain_available = slope is not None
    terrain_max = 30.0
    
    if not terrain_available:
        terrain_score = None
        terrain_level = None
    else:
        if slope < 15.0:
            terrain_score = 5.0
            terrain_level = "Low"
        elif 15.0 <= slope <= 30.0:
            terrain_score = 18.0
            terrain_level = "Moderate"
        else:  # slope > 30.0
            terrain_score = 30.0
            terrain_level = "High"
            
    # ── 3. RAINFALL COMPONENT (MAX 30) ─────────────────────────────────────
    rainfall_available = (rainfall is not None) or (rainfall_3d is not None) or (rainfall_7d is not None)
    
    daily_score = None
    three_day_score = None
    seven_day_score = None
    
    daily_max = 0.0
    three_day_max = 0.0
    seven_day_max = 0.0
    
    if not rainfall_available:
        rainfall_score = None
        rainfall_max = 30.0
        rainfall_level = None
        scoring_mode = "compatibility"
    else:
        # Compatibility Mode active if both 3-day and 7-day parameters are missing
        if rainfall_3d is None and rainfall_7d is None:
            scoring_mode = "compatibility"
            rainfall_max = 30.0
            if rainfall < 10.0:
                rainfall_score = 0.0
                rainfall_level = "Low"
            elif 10.0 <= rainfall <= 50.0:
                rainfall_score = 15.0
                rainfall_level = "Moderate"
            else:  # rainfall > 50.0
                rainfall_score = 30.0
                rainfall_level = "High"
        else:
            # Multi-timescale Mode (Full or Partial)
            is_partial = (rainfall is None) or (rainfall_3d is None) or (rainfall_7d is None)
            scoring_mode = "multi_timescale_partial" if is_partial else "multi_timescale"
            
            # 1. Daily intensity scoring (Max 10)
            if rainfall is not None:
                daily_max = 10.0
                if rainfall < 10.0:
                    daily_score = 0.0
                elif 10.0 <= rainfall <= 50.0:
                    daily_score = 5.0
                else:  # rainfall > 50.0
                    daily_score = 10.0
                    
            # 2. 3-day saturation scoring (Max 10)
            if rainfall_3d is not None:
                three_day_max = 10.0
                if rainfall_3d < 25.0:
                    three_day_score = 0.0
                elif 25.0 <= rainfall_3d <= 80.0:
                    three_day_score = 5.0
                else:  # rainfall_3d > 80.0
                    three_day_score = 10.0
                    
            # 3. 7-day saturation scoring (Max 10)
            if rainfall_7d is not None:
                seven_day_max = 10.0
                if rainfall_7d < 60.0:
                    seven_day_score = 0.0
                elif 60.0 <= rainfall_7d <= 180.0:
                    seven_day_score = 5.0
                else:  # rainfall_7d > 180.0
                    seven_day_score = 10.0
                    
            # Aggregate available components
            earned_rainfall_pts = 0.0
            if daily_score is not None:
                earned_rainfall_pts += daily_score
            if three_day_score is not None:
                earned_rainfall_pts += three_day_score
            if seven_day_score is not None:
                earned_rainfall_pts += seven_day_score
                
            rainfall_score = earned_rainfall_pts
            rainfall_max = daily_max + three_day_max + seven_day_max
            
            # Classify level based on percentage of available rainfall max points
            if rainfall_max > 0.0:
                ratio = rainfall_score / rainfall_max
                if ratio < 0.33:
                    rainfall_level = "Low"
                elif ratio < 0.67:
                    rainfall_level = "Moderate"
                else:
                    rainfall_level = "High"
            else:
                rainfall_level = None

    # ── 4. PARTIAL INPUT NORMALIZATION ─────────────────────────────────────
    earned_points = historical_score
    available_max = historical_max
    
    if terrain_available:
        earned_points += terrain_score
        available_max += terrain_max
        
    if rainfall_available:
        earned_points += rainfall_score
        available_max += rainfall_max
        
    # Calculate final score normalized to 100 points
    final_score = round(100.0 * earned_points / available_max, 2)
    
    # ── 5. HAZARD LEVEL CLASSIFICATION ─────────────────────────────────────
    if final_score <= 25.0:
        hazard_level = "Low"
    elif final_score <= 50.0:
        hazard_level = "Moderate"
    elif final_score <= 75.0:
        hazard_level = "High"
    else:  # 75.0 < final_score <= 100.0
        hazard_level = "Very High"
        
    # ── 6. COMPILING FACTOR EXPLANATION ────────────────────────────────────
    contributors = []
    
    # Check historical evidence contribution
    if total_obs > 0:
        if nearest_dist <= 2.0:
            contributors.append("immediate proximity to historical landslides")
        else:
            contributors.append("known historical landslide occurrences in the local area")
            
    # Check terrain slope contribution
    if terrain_available:
        if slope >= 30.0:
            contributors.append("highly steep terrain slopes (> 30°)")
        elif slope >= 15.0:
            contributors.append("moderately steep terrain slopes (15°-30°)")
            
    # Check rainfall contribution
    if rainfall_available:
        if scoring_mode == "compatibility":
            if rainfall >= 50.0:
                contributors.append("heavy recent precipitation (> 50mm)")
            elif rainfall >= 10.0:
                contributors.append("moderate recent rainfall (10-50mm)")
        else:
            if rainfall is not None:
                if rainfall >= 50.0:
                    contributors.append("extreme daily rainfall intensity (> 50mm)")
                elif rainfall >= 10.0:
                    contributors.append("moderate daily rainfall intensity (10-50mm)")
            if rainfall_3d is not None:
                if rainfall_3d >= 80.0:
                    contributors.append("heavy short-term rainfall accumulation (> 80mm)")
                elif rainfall_3d >= 25.0:
                    contributors.append("moderate short-term rainfall accumulation (25-80mm)")
            if rainfall_7d is not None:
                if rainfall_7d >= 180.0:
                    contributors.append("extreme weekly antecedent rainfall saturation (> 180mm)")
                elif rainfall_7d >= 60.0:
                    contributors.append("significant weekly antecedent rainfall saturation (60-180mm)")
            
    if contributors:
        explanation = (
            f"Heuristic calculations indicate a {hazard_level} hazard level primarily driven by "
            f"{', '.join(contributors[:-1])} and {contributors[-1]}." if len(contributors) > 1 else
            f"Heuristic calculations indicate a {hazard_level} hazard level primarily driven by "
            f"{contributors[0]}."
        )
    else:
        explanation = (
            f"Heuristic calculations indicate a {hazard_level} hazard level. There is no active "
            "precipitation, steep slope, or historical landslide record detected inside this radius."
        )
        
    return {
        "query_latitude": latitude,
        "query_longitude": longitude,
        "radius_km": radius_km,
        "susceptibility_score": final_score,
        "hazard_level": hazard_level,
        "historical_component": {
            "score": round(historical_score, 2),
            "max_score": historical_max,
            "proximity_score": round(proximity_score, 2),
            "density_score": round(density_score, 2),
            "total_observations": total_obs,
            "nearest_observation_km": nearest_dist
        },
        "terrain_component": {
            "available": terrain_available,
            "score": round(terrain_score, 2) if terrain_score is not None else None,
            "max_score": terrain_max,
            "mean_slope_degrees": slope,
            "level": terrain_level
        },
        "rainfall_component": {
            "available": rainfall_available,
            "score": round(rainfall_score, 2) if rainfall_score is not None else None,
            "max_score": rainfall_max,
            "precipitation_mm_24h": rainfall,
            "level": rainfall_level,
            "daily_score": round(daily_score, 2) if daily_score is not None else None,
            "three_day_score": round(three_day_score, 2) if three_day_score is not None else None,
            "seven_day_score": round(seven_day_score, 2) if seven_day_score is not None else None,
            "three_day_cumulative_mm": rainfall_3d,
            "seven_day_cumulative_mm": rainfall_7d,
            "scoring_mode": scoring_mode
        },
        "available_max_points": available_max,
        "explanation": explanation
    }
