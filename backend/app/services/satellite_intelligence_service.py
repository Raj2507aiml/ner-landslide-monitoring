"""
Satellite Change Intelligence Service - Phase 7
Standardizes multi-temporal Sentinel-1 SAR change detections, backscatter deltas,
and Radar Surface Change Index (RSCI) calculations into an explainable domain intelligence object.
"""

from typing import Dict, Any, List, Optional

from app.services.aoi_service import is_inside_ner
from app.services.automatic_satellite_pair_service import AutomaticSatellitePairService


# ---------------------------------------------------------------------------
# Centralized Satellite Risk Thresholds (Calibration Parameters)
# ---------------------------------------------------------------------------
SATELLITE_RISK_LOW_THRESHOLD = 25.0
SATELLITE_RISK_MODERATE_THRESHOLD = 50.0
SATELLITE_RISK_HIGH_THRESHOLD = 75.0


# ---------------------------------------------------------------------------
# Satellite Risk Classification
# ---------------------------------------------------------------------------
def classify_satellite_risk(score: Optional[float]) -> Optional[str]:
    """
    Classifies satellite change score into initial operational hazard levels:
    - 0 to 25   -> LOW
    - 25 to 50  -> MODERATE
    - 50 to 75  -> HIGH
    - 75 to 100 -> VERY_HIGH
    """
    if score is None:
        return None
    if score <= SATELLITE_RISK_LOW_THRESHOLD:
        return "LOW"
    elif score <= SATELLITE_RISK_MODERATE_THRESHOLD:
        return "MODERATE"
    elif score <= SATELLITE_RISK_HIGH_THRESHOLD:
        return "HIGH"
    else:
        return "VERY_HIGH"


# ---------------------------------------------------------------------------
# Explainability Factor Generator
# ---------------------------------------------------------------------------
def generate_satellite_risk_factors(
    available: bool,
    rsci: Optional[float],
    risk_level: Optional[str],
    avg_change_pct: Optional[float],
    anomaly_mag_db: Optional[float],
    orbit_dir: Optional[str],
    baseline_days: Optional[float],
    delta_vv: Optional[Dict[str, Any]],
    delta_vh: Optional[Dict[str, Any]],
    reason: Optional[str] = None
) -> List[str]:
    """
    Generates dynamic, scientifically cautious, explainable risk factors.
    Avoids definitive claims like 'a landslide occurred' and focuses on
    radar-observed backscatter variations, spatial change percentages,
    and orbital geometry characteristics.
    """
    if not available:
        if reason:
            return [
                f"Satellite SAR change intelligence unavailable: {reason}",
                "Absence of satellite observations requires operational reliance on environmental triggers and ground telemetry."
            ]
        return [
            "Compatible Sentinel-1 temporal pair was unavailable for the requested location and analysis window.",
            "Operational assessment should rely on real-time environmental sensors and historical susceptibility."
        ]

    factors: List[str] = []

    # 1. Primary RSCI statement
    if rsci is not None and risk_level is not None:
        factors.append(
            f"Sentinel-1 SAR surface change analysis computed an index score of {rsci:.1f} ({risk_level} surface disturbance signal)"
        )

    # 2. Spatial Extent
    if avg_change_pct is not None:
        factors.append(
            f"Radar analysis detected significant surface backscatter changes across {avg_change_pct:.1f}% of the monitored area"
        )

    # 3. Anomaly Magnitude (dB spread)
    if anomaly_mag_db is not None:
        factors.append(
            f"Observed temporal SAR backscatter anomaly magnitude reached {anomaly_mag_db:.1f} dB"
        )

    # 4. Polarization Breakdown
    if delta_vv:
        vv_mean = delta_vv.get("mean", 0.0)
        factors.append(
            f"VV co-polarization change (mean: {vv_mean:+.2f} dB) indicates surface roughness and soil dielectric state variations"
        )

    if delta_vh:
        vh_mean = delta_vh.get("mean", 0.0)
        factors.append(
            f"VH cross-polarization variation (mean: {vh_mean:+.2f} dB) reflects changes in volumetric structure and vegetation canopy"
        )

    # 5. Orbital & Baseline Context
    if orbit_dir and baseline_days is not None:
        factors.append(
            f"Comparison utilized matching {orbit_dir}-orbit acquisitions separated by a {baseline_days:.0f}-day temporal baseline"
        )

    # 6. Scientific caveat statement
    factors.append(
        "Radar backscatter anomalies represent relative surface change signals and require correlation with environmental and geological factors."
    )

    return factors


# ---------------------------------------------------------------------------
# Main Satellite Change Intelligence Analysis
# ---------------------------------------------------------------------------
def analyze_satellite_change_intelligence(
    latitude: float,
    longitude: float,
    radius_km: float = 5.0
) -> Dict[str, Any]:
    """
    Standardized domain-level Satellite Change Intelligence Engine (Phase 7).
    Wraps the underlying AutomaticSatellitePairService and RadarChangeSignalService.
    Extracts real Sentinel-1 multi-temporal SAR backscatter variations and translates
    them into standardized domain metrics, explainable factors, and confidence flags.
    """
    # 1. Geographic and coordinate validation
    if not (-90.0 <= latitude <= 90.0):
        raise ValueError(f"Latitude {latitude} is outside valid range [-90.0, 90.0].")
    if not (-180.0 <= longitude <= 180.0):
        raise ValueError(f"Longitude {longitude} is outside valid range [-180.0, 180.0].")
    if not (0.1 <= radius_km <= 25.0):
        raise ValueError(f"Search radius {radius_km} km is outside valid range [0.1, 25.0] km.")

    # 2. Check if inside Northeast India (NER) boundary
    if not is_inside_ner(latitude, longitude):
        return {
            "latitude": round(float(latitude), 6),
            "longitude": round(float(longitude), 6),
            "satellite_data_available": False,
            "satellite_change_score": None,
            "satellite_risk_level": None,
            "radar_surface_change_index": None,
            "spatial_change_extent_percent": None,
            "radar_anomaly_magnitude_db": None,
            "average_significant_change_percent": None,
            "delta_vv_statistics": None,
            "delta_vh_statistics": None,
            "delta_cross_pol_statistics": None,
            "orbit_direction": None,
            "temporal_baseline_days": None,
            "reference_scene": None,
            "comparison_scene": None,
            "satellite_risk_factors": [
                "Target coordinates are located outside India's North Eastern Region (NER) monitoring boundary.",
                "Satellite change intelligence is configured specifically for the 8 Northeastern states."
            ],
            "confidence": "LOW",
            "data_source": "SENTINEL_1_COPERNICUS",
            "data_unavailability_reason": "Target coordinates lie outside the North Eastern Region monitoring domain."
        }

    # 3. Call existing AutomaticSatellitePairService
    try:
        raw_result = AutomaticSatellitePairService.analyze_location_change(
            latitude=latitude,
            longitude=longitude,
            radius_km=radius_km
        )
    except Exception as exc:
        return {
            "latitude": round(float(latitude), 6),
            "longitude": round(float(longitude), 6),
            "satellite_data_available": False,
            "satellite_change_score": None,
            "satellite_risk_level": None,
            "radar_surface_change_index": None,
            "spatial_change_extent_percent": None,
            "radar_anomaly_magnitude_db": None,
            "average_significant_change_percent": None,
            "delta_vv_statistics": None,
            "delta_vh_statistics": None,
            "delta_cross_pol_statistics": None,
            "orbit_direction": None,
            "temporal_baseline_days": None,
            "reference_scene": None,
            "comparison_scene": None,
            "satellite_risk_factors": generate_satellite_risk_factors(
                available=False,
                rsci=None,
                risk_level=None,
                avg_change_pct=None,
                anomaly_mag_db=None,
                orbit_dir=None,
                baseline_days=None,
                delta_vv=None,
                delta_vh=None,
                reason=f"Copernicus catalog or raster access error: {str(exc)}"
            ),
            "confidence": "LOW",
            "data_source": "SENTINEL_1_COPERNICUS",
            "data_unavailability_reason": f"Satellite pipeline execution failed: {str(exc)}"
        }

    # 4. Check if pairing succeeded
    status = raw_result.get("status")
    if status != "PAIRED_SUCCESS":
        msg = raw_result.get("message", "No compatible Sentinel-1 scene pair available.")
        return {
            "latitude": round(float(latitude), 6),
            "longitude": round(float(longitude), 6),
            "satellite_data_available": False,
            "satellite_change_score": None,
            "satellite_risk_level": None,
            "radar_surface_change_index": None,
            "spatial_change_extent_percent": None,
            "radar_anomaly_magnitude_db": None,
            "average_significant_change_percent": None,
            "delta_vv_statistics": None,
            "delta_vh_statistics": None,
            "delta_cross_pol_statistics": None,
            "orbit_direction": None,
            "temporal_baseline_days": None,
            "reference_scene": None,
            "comparison_scene": None,
            "satellite_risk_factors": generate_satellite_risk_factors(
                available=False,
                rsci=None,
                risk_level=None,
                avg_change_pct=None,
                anomaly_mag_db=None,
                orbit_dir=None,
                baseline_days=None,
                delta_vv=None,
                delta_vh=None,
                reason=msg
            ),
            "confidence": "LOW",
            "data_source": "SENTINEL_1_COPERNICUS",
            "data_unavailability_reason": msg
        }

    # 5. Extract REAL metrics from PAIRED_SUCCESS output
    metadata = raw_result.get("metadata", {})
    temp_indicators = raw_result.get("temporal_change_indicators", {})
    rsci_signal = raw_result.get("radar_surface_change_signal", {})

    rsci = float(rsci_signal.get("radar_surface_change_index", 0.0))
    satellite_change_score = round(rsci, 1)
    satellite_risk_level = classify_satellite_risk(satellite_change_score)

    spatial_change_extent = float(rsci_signal.get("spatial_extent_score", 0.0))
    avg_sig_change_pct = float(rsci_signal.get("average_significant_change_percentage", 0.0))

    vv_spread = float(rsci_signal.get("vv_spread_db", 0.0))
    vh_spread = float(rsci_signal.get("vh_spread_db", 0.0))
    anomaly_magnitude_db = round(max(vv_spread, vh_spread), 2)

    delta_vv_stats = temp_indicators.get("delta_vv_db")
    delta_vh_stats = temp_indicators.get("delta_vh_db")
    delta_cross_stats = temp_indicators.get("delta_cross_pol_db")

    orbit_dir = metadata.get("orbit_direction")
    baseline_days = float(metadata.get("temporal_separation_days", 0.0))

    ref_scene = metadata.get("reference_scene")
    comp_scene = metadata.get("comparison_scene")

    # 6. Determine Confidence
    if 10.0 <= baseline_days <= 24.0 and delta_vv_stats and delta_vh_stats:
        confidence = "HIGH"
    elif delta_vv_stats and delta_vh_stats:
        confidence = "MEDIUM"
    else:
        confidence = "LOW"

    # 7. Generate Explainability
    risk_factors = generate_satellite_risk_factors(
        available=True,
        rsci=satellite_change_score,
        risk_level=satellite_risk_level,
        avg_change_pct=avg_sig_change_pct,
        anomaly_mag_db=anomaly_magnitude_db,
        orbit_dir=orbit_dir,
        baseline_days=baseline_days,
        delta_vv=delta_vv_stats,
        delta_vh=delta_vh_stats
    )

    return {
        "latitude": round(float(latitude), 6),
        "longitude": round(float(longitude), 6),
        "satellite_data_available": True,
        "satellite_change_score": satellite_change_score,
        "satellite_risk_level": satellite_risk_level,
        "radar_surface_change_index": round(rsci, 2),
        "spatial_change_extent_percent": round(spatial_change_extent, 2),
        "radar_anomaly_magnitude_db": anomaly_magnitude_db,
        "average_significant_change_percent": round(avg_sig_change_pct, 2),
        "delta_vv_statistics": delta_vv_stats,
        "delta_vh_statistics": delta_vh_stats,
        "delta_cross_pol_statistics": delta_cross_stats,
        "orbit_direction": orbit_dir,
        "temporal_baseline_days": round(baseline_days, 1),
        "reference_scene": ref_scene,
        "comparison_scene": comp_scene,
        "satellite_risk_factors": risk_factors,
        "confidence": confidence,
        "data_source": "SENTINEL_1_COPERNICUS",
        "data_unavailability_reason": None
    }
