import json
import urllib.request
import urllib.error
from typing import Dict, Any, Optional

# ---------------------------------------------------------------------------
# Soil Moisture Intelligence Service (Phase 3.3)
# ---------------------------------------------------------------------------

def classify_soil_condition(soil_moisture_percent: float) -> str:
    """
    Centralized classification of physical soil moisture condition:
    - 0 to 20%   -> DRY
    - 20 to 40%  -> SLIGHTLY_MOIST
    - 40 to 60%  -> MOIST
    - 60 to 80%  -> WET
    - 80 to 100% -> SATURATED
    """
    if soil_moisture_percent <= 20.0:
        return "DRY"
    elif soil_moisture_percent <= 40.0:
        return "SLIGHTLY_MOIST"
    elif soil_moisture_percent <= 60.0:
        return "MOIST"
    elif soil_moisture_percent <= 80.0:
        return "WET"
    else:
        return "SATURATED"


def classify_soil_risk(soil_moisture_percent: float) -> str:
    """
    Centralized classification of landslide triggering hazard due to soil saturation.
    High pore-water pressure and saturated soil drastically reduce shear strength.

    Thresholds:
    - Below 30%  -> LOW
    - 30 to 50%  -> MODERATE
    - 50 to 70%  -> HIGH
    - Above 70%  -> VERY_HIGH
    """
    if soil_moisture_percent < 30.0:
        return "LOW"
    elif soil_moisture_percent <= 50.0:
        return "MODERATE"
    elif soil_moisture_percent <= 70.0:
        return "HIGH"
    else:
        return "VERY_HIGH"


def analyze_soil_moisture(
    latitude: float,
    longitude: float,
    source: str = "satellite"
) -> Dict[str, Any]:
    """
    Analyzes live soil moisture conditions across multiple ground depth layers
    (surface 0-1cm, 1-3cm, root-zone 3-9cm, and 9-27cm) for a target coordinate.

    Designed with a modular architecture for future IoT / ESP32 sensor ingestion:
    Open-Meteo Soil Data / Future ESP32 Sensor -> Unified Soil Intelligence Service.

    Returns structured dictionary:
    - latitude: float
    - longitude: float
    - soil_moisture: float (volumetric water fraction, 0.00 to 1.00)
    - soil_moisture_percent: float (0.0 to 100.0%)
    - soil_condition: str (DRY, SLIGHTLY_MOIST, MOIST, WET, SATURATED)
    - soil_saturation_risk: str (LOW, MODERATE, HIGH, VERY_HIGH)
    - data_source: str ("OPEN_METEO")
    - surface_soil_moisture: float (0-1cm volumetric fraction)
    - root_zone_soil_moisture: float (3-9cm / 9-27cm volumetric fraction)
    """
    # 1. Coordinate range validation
    if not (-90.0 <= latitude <= 90.0):
        raise ValueError(f"Latitude {latitude} is out of valid range [-90.0, 90.0].")
    if not (-180.0 <= longitude <= 180.0):
        raise ValueError(f"Longitude {longitude} is out of valid range [-180.0, 180.0].")

    url = (
        f"https://api.open-meteo.com/v1/forecast"
        f"?latitude={latitude}&longitude={longitude}"
        f"&current=soil_moisture_0_to_1cm,soil_moisture_1_to_3cm,soil_moisture_3_to_9cm,soil_moisture_9_to_27cm"
        f"&hourly=soil_moisture_0_to_1cm,soil_moisture_1_to_3cm,soil_moisture_3_to_9cm,soil_moisture_9_to_27cm"
        f"&timezone=auto"
        f"&forecast_days=1"
    )

    res_data = None

    # Primary query strategy: httpx client with 10.0s timeout
    try:
        import httpx
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(url, headers={"User-Agent": "NER-Landslide-Monitoring-EWS/1.0"})
            if resp.status_code == 200:
                res_data = resp.json()
            else:
                raise Exception(f"Open-Meteo HTTP {resp.status_code}: {resp.text}")
    except Exception as primary_err:
        # Fallback query strategy: urllib.request with 10.0s timeout
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "NER-Landslide-Monitoring-EWS/1.0"},
                method="GET"
            )
            with urllib.request.urlopen(req, timeout=10) as response:
                res_data = json.loads(response.read().decode("utf-8"))
        except Exception as fallback_err:
            raise Exception(
                f"Failed to retrieve soil moisture data from Open-Meteo: {str(primary_err)} (Fallback: {str(fallback_err)})"
            )

    if not res_data or not isinstance(res_data, dict):
        raise Exception("Invalid or empty response payload received from soil moisture data service.")

    current = res_data.get("current", {})
    hourly = res_data.get("hourly", {})

    # Extract layer values from current readings (fallback to most recent hourly if current layer is None)
    def _get_layer_val(layer_key: str) -> float:
        val = current.get(layer_key)
        if val is not None and val >= 0.0:
            return float(val)
        # Fallback to last available hourly entry
        hourly_vals = hourly.get(layer_key, [])
        for h_val in reversed(hourly_vals):
            if h_val is not None and h_val >= 0.0:
                return float(h_val)
        return 0.35  # Safe default if layer is absent

    sm_0_1 = _get_layer_val("soil_moisture_0_to_1cm")
    sm_1_3 = _get_layer_val("soil_moisture_1_to_3cm")
    sm_3_9 = _get_layer_val("soil_moisture_3_to_9cm")
    sm_9_27 = _get_layer_val("soil_moisture_9_to_27cm")

    # Surface layer representation (0 - 1 cm / 1 - 3 cm)
    surface_moisture = round(sm_0_1, 4)

    # Root zone layer representation (average of 3-9cm and 9-27cm)
    root_zone_moisture = round((sm_3_9 + sm_9_27) / 2.0, 4)

    # Weighted composite soil moisture:
    # 40% surface (0-1cm, 1-3cm), 60% deep root-zone (3-9cm, 9-27cm)
    weighted_moisture = (sm_0_1 * 0.25 + sm_1_3 * 0.15 + sm_3_9 * 0.30 + sm_9_27 * 0.30)
    soil_moisture_val = round(weighted_moisture, 4)
    soil_moisture_percent = round(soil_moisture_val * 100.0, 2)

    # Condition & Saturation Risk Classifications
    soil_condition = classify_soil_condition(soil_moisture_percent)
    soil_saturation_risk = classify_soil_risk(soil_moisture_percent)

    data_source = "OPEN_METEO" if source.lower() == "satellite" else f"OPEN_METEO_{source.upper()}"

    return {
        "latitude": round(float(latitude), 6),
        "longitude": round(float(longitude), 6),
        "soil_moisture": round(soil_moisture_val, 2),
        "soil_moisture_percent": soil_moisture_percent,
        "soil_condition": soil_condition,
        "soil_saturation_risk": soil_saturation_risk,
        "data_source": data_source,
        "surface_soil_moisture": round(surface_moisture, 2),
        "root_zone_soil_moisture": round(root_zone_moisture, 2)
    }
