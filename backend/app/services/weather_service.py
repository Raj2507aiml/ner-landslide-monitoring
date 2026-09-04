import urllib.request
import urllib.error
import json
from datetime import datetime
from typing import Dict, Any

def fetch_weather_telemetry(lat: float, lon: float) -> Dict[str, Any]:
    """
    Fetches real-time temperature, humidity, precipitation, and daily precipitation history
    from the Open-Meteo API for the given coordinates, including past 7 days for antecedent calculations.
    """
    # Validate coordinate ranges
    if not (-90.0 <= lat <= 90.0) or not (-180.0 <= lon <= 180.0):
        raise ValueError("Invalid coordinate boundaries. Latitude must be in [-90, 90] and Longitude in [-180, 180].")

    url = (
        f"https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}"
        f"&current=temperature_2m,relative_humidity_2m,precipitation"
        f"&daily=precipitation_sum"
        f"&timezone=auto"
        f"&past_days=7"
        f"&forecast_days=1"
    )

    req = urllib.request.Request(
        url,
        headers={"User-Agent": "NER-Landslide-Monitoring-EWS/1.0"},
        method="GET"
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            
            current = res_data.get("current", {})
            daily = res_data.get("daily", {})
            
            # Extract values
            temperature = current.get("temperature_2m")
            relative_humidity = current.get("relative_humidity_2m")
            current_precipitation = current.get("precipitation")
            
            # Extract daily history
            daily_time = daily.get("time", [])
            daily_precip = daily.get("precipitation_sum", [])
            
            # Map daily precipitation history safely
            daily_history = []
            cleaned_precip = []
            for i in range(len(daily_time)):
                p_val = daily_precip[i] if i < len(daily_precip) else 0.0
                if p_val is None or p_val < 0.0:
                    p_val = 0.0
                daily_history.append({
                    "date": daily_time[i],
                    "precipitation_mm": float(p_val)
                })
                cleaned_precip.append(float(p_val))

            # Today's daily precipitation is the last element (today's current accumulated sum)
            daily_precipitation = cleaned_precip[-1] if cleaned_precip else 0.0
            
            # 3-day cumulative: Sum today + previous 2 days (up to 3 most recent)
            three_day_precip = cleaned_precip[-3:] if len(cleaned_precip) >= 3 else cleaned_precip
            three_day_cumulative = round(sum(three_day_precip), 2)
            
            # 7-day cumulative: Sum today + previous 6 days (up to 7 most recent)
            seven_day_precip = cleaned_precip[-7:] if len(cleaned_precip) >= 7 else cleaned_precip
            seven_day_cumulative = round(sum(seven_day_precip), 2)
            
            # Heuristic saturation classification based on 7-day cumulative
            if seven_day_cumulative < 10.0:
                saturation_classification = "Dry"
            elif seven_day_cumulative < 50.0:
                saturation_classification = "Light"
            elif seven_day_cumulative < 120.0:
                saturation_classification = "Moderate"
            elif seven_day_cumulative <= 250.0:
                saturation_classification = "Heavy"
            else:
                saturation_classification = "Extreme"

            # Units mapping
            current_units = res_data.get("current_units", {})
            daily_units = res_data.get("daily_units", {})

            return {
                "status": "success",
                "latitude": lat,
                "longitude": lon,
                "temperature": temperature,
                "temperature_unit": current_units.get("temperature_2m", "°C"),
                "relative_humidity": relative_humidity,
                "relative_humidity_unit": current_units.get("relative_humidity_2m", "%"),
                "current_precipitation": current_precipitation,
                "current_precipitation_unit": current_units.get("precipitation", "mm"),
                "daily_precipitation": daily_precipitation,
                "daily_precipitation_unit": daily_units.get("precipitation_sum", "mm"),
                "three_day_cumulative": three_day_cumulative,
                "seven_day_cumulative": seven_day_cumulative,
                "saturation_classification": saturation_classification,
                "daily_precipitation_history": daily_history,
                "timestamp": current.get("time") or datetime.utcnow().isoformat() + "Z",
                "timezone": res_data.get("timezone"),
                "elevation": res_data.get("elevation")
            }

    except urllib.error.HTTPError as e:
        raise Exception(f"Open-Meteo API returned error {e.code}: {e.reason}")
    except urllib.error.URLError as e:
        raise Exception(f"Failed to connect to weather telemetry service: {e.reason}")
    except Exception as e:
        raise Exception(f"Error parsing weather telemetry response: {str(e)}")


# ---------------------------------------------------------------------------
# Rainfall Intelligence Analysis (Phase 3.2)
# ---------------------------------------------------------------------------

def classify_rainfall_intensity(current_rainfall_mm: float) -> str:
    """
    Classifies instantaneous/current rainfall intensity based on standard meteorological thresholds:
    - 0.0 mm -> NONE
    - 0.1 to 2.5 mm -> LIGHT
    - 2.5 to 7.5 mm -> MODERATE
    - 7.5 to 20.0 mm -> HEAVY
    - Above 20.0 mm -> EXTREME
    """
    if current_rainfall_mm <= 0.0:
        return "NONE"
    elif current_rainfall_mm <= 2.5:
        return "LIGHT"
    elif current_rainfall_mm <= 7.5:
        return "MODERATE"
    elif current_rainfall_mm <= 20.0:
        return "HEAVY"
    else:
        return "EXTREME"


def classify_rainfall_risk(
    rainfall_24h_mm: float,
    rainfall_3d_mm: float,
    rainfall_7d_mm: float,
    current_rainfall_mm: float = 0.0
) -> str:
    """
    Classifies landslide triggering hazard risk primarily based on short-term intensity
    and antecedent multi-day accumulated precipitation.
    
    Centralized thresholds calibrated for Northeast India (NER) terrain:
    - VERY_HIGH: 24h >= 100mm OR 3d >= 200mm OR 7d >= 300mm OR (24h >= 75mm AND 3d >= 150mm) OR current >= 35mm
    - HIGH:      24h >= 50mm  OR 3d >= 100mm OR 7d >= 150mm OR (24h >= 35mm AND 3d >= 75mm)  OR current >= 20mm
    - MODERATE:  24h >= 20mm  OR 3d >= 45mm  OR 7d >= 75mm  OR current >= 7.5mm
    - LOW:       Below moderate trigger thresholds
    """
    if (
        rainfall_24h_mm >= 100.0
        or rainfall_3d_mm >= 200.0
        or rainfall_7d_mm >= 300.0
        or (rainfall_24h_mm >= 75.0 and rainfall_3d_mm >= 150.0)
        or current_rainfall_mm >= 35.0
    ):
        return "VERY_HIGH"
    elif (
        rainfall_24h_mm >= 50.0
        or rainfall_3d_mm >= 100.0
        or rainfall_7d_mm >= 150.0
        or (rainfall_24h_mm >= 35.0 and rainfall_3d_mm >= 75.0)
        or current_rainfall_mm >= 20.0
    ):
        return "HIGH"
    elif (
        rainfall_24h_mm >= 20.0
        or rainfall_3d_mm >= 45.0
        or rainfall_7d_mm >= 75.0
        or current_rainfall_mm >= 7.5
    ):
        return "MODERATE"
    else:
        return "LOW"


def analyze_rainfall(latitude: float, longitude: float) -> Dict[str, Any]:
    """
    Analyzes live rainfall conditions and antecedent multi-day accumulation for a target location.
    
    Queries Open-Meteo API for:
    - Current precipitation
    - Trailing 24-hour hourly precipitation
    - Past 7-day daily precipitation sums
    
    Calculates:
    - current_rainfall_mm
    - rainfall_last_24h_mm
    - rainfall_last_3_days_mm
    - rainfall_last_7_days_mm
    - rainfall_intensity (NONE, LIGHT, MODERATE, HEAVY, EXTREME)
    - rainfall_risk_level (LOW, MODERATE, HIGH, VERY_HIGH)
    """
    # 1. Validate coordinate boundaries
    if not (-90.0 <= latitude <= 90.0):
        raise ValueError(f"Latitude {latitude} is out of valid range [-90.0, 90.0].")
    if not (-180.0 <= longitude <= 180.0):
        raise ValueError(f"Longitude {longitude} is out of valid range [-180.0, 180.0].")

    url = (
        f"https://api.open-meteo.com/v1/forecast"
        f"?latitude={latitude}&longitude={longitude}"
        f"&current=precipitation,rain"
        f"&hourly=precipitation"
        f"&daily=precipitation_sum"
        f"&timezone=auto"
        f"&past_days=7"
        f"&forecast_days=1"
    )

    res_data = None

    # Primary strategy: httpx client with timeout
    try:
        import httpx
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(url, headers={"User-Agent": "NER-Landslide-Monitoring-EWS/1.0"})
            if resp.status_code == 200:
                res_data = resp.json()
            else:
                raise Exception(f"Open-Meteo HTTP {resp.status_code}: {resp.text}")
    except Exception as primary_err:
        # Fallback strategy: urllib.request
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "NER-Landslide-Monitoring-EWS/1.0"},
                method="GET"
            )
            with urllib.request.urlopen(req, timeout=10) as response:
                res_data = json.loads(response.read().decode("utf-8"))
        except Exception as fallback_err:
            raise Exception(f"Failed to fetch rainfall data from Open-Meteo: {str(primary_err)} (Fallback: {str(fallback_err)})")

    if not res_data or not isinstance(res_data, dict):
        raise Exception("Invalid or empty response payload received from Open-Meteo API.")

    current = res_data.get("current", {})
    hourly = res_data.get("hourly", {})
    daily = res_data.get("daily", {})

    # 1. Current precipitation (mm)
    raw_current = current.get("precipitation")
    if raw_current is None or raw_current < 0.0:
        raw_current = current.get("rain", 0.0)
    current_rainfall = round(float(raw_current or 0.0), 2)

    # 2. Trailing 24 hours precipitation (mm)
    hourly_times = hourly.get("time", [])
    hourly_precip = hourly.get("precipitation", [])
    cur_time = current.get("time")

    if cur_time and cur_time in hourly_times:
        idx = hourly_times.index(cur_time)
        start_idx = max(0, idx - 23)
        window = hourly_precip[start_idx : idx + 1]
        rainfall_24h = round(sum(float(p or 0.0) for p in window), 2)
    elif hourly_precip:
        # Trailing 24 recorded hours in series
        window = hourly_precip[-24:] if len(hourly_precip) >= 24 else hourly_precip
        rainfall_24h = round(sum(float(p or 0.0) for p in window), 2)
    else:
        # Fallback to today's daily precipitation if hourly is absent
        daily_sums = daily.get("precipitation_sum", [])
        rainfall_24h = round(float(daily_sums[-1] if daily_sums else 0.0), 2)

    # 3. Antecedent 3-Day and 7-Day cumulative precipitation (mm)
    raw_daily = daily.get("precipitation_sum", [])
    cleaned_daily = [float(p if p is not None and p >= 0.0 else 0.0) for p in raw_daily]

    # 3-day sum (today + prior 2 days)
    three_day_slice = cleaned_daily[-3:] if len(cleaned_daily) >= 3 else cleaned_daily
    rainfall_3d = round(sum(three_day_slice), 2)

    # 7-day sum (today + prior 6 days)
    seven_day_slice = cleaned_daily[-7:] if len(cleaned_daily) >= 7 else cleaned_daily
    rainfall_7d = round(sum(seven_day_slice), 2)

    # 4. Intensity & Risk Classifications
    intensity = classify_rainfall_intensity(current_rainfall)
    risk_level = classify_rainfall_risk(
        rainfall_24h_mm=rainfall_24h,
        rainfall_3d_mm=rainfall_3d,
        rainfall_7d_mm=rainfall_7d,
        current_rainfall_mm=current_rainfall
    )

    return {
        "latitude": round(float(latitude), 6),
        "longitude": round(float(longitude), 6),
        "current_rainfall_mm": current_rainfall,
        "rainfall_last_24h_mm": rainfall_24h,
        "rainfall_last_3_days_mm": rainfall_3d,
        "rainfall_last_7_days_mm": rainfall_7d,
        "rainfall_intensity": intensity,
        "rainfall_risk_level": risk_level
    }

