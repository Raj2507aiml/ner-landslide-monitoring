"""
Radar Change Signal Service - Phase 5 Checkpoint 13.9

Implements the Radar Surface Change Index (RSCI) calculation from Sentinel-1 delta statistics.
Provides a conservative classification of satellite-observed backscatter variations.
"""

from typing import Dict, Any

class RadarChangeSignalService:
    @staticmethod
    def calculate_rsci(change_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Accepts the output of SatelliteChangeService.calculate_temporal_change
        and computes the 0-100 RSCI score, spatial extent, magnitude anomaly, and category.
        """
        indicators = change_data.get("surface_change_indicators", {})
        
        vv_stats = indicators.get("delta_vv_db", {})
        vh_stats = indicators.get("delta_vh_db", {})
        cross_stats = indicators.get("delta_cross_pol_db", {})
        
        # 1. Spatial Change Extent
        vv_pos = vv_stats.get("significant_positive_change_percentage", 0.0)
        vv_neg = vv_stats.get("significant_negative_change_percentage", 0.0)
        vh_pos = vh_stats.get("significant_positive_change_percentage", 0.0)
        vh_neg = vh_stats.get("significant_negative_change_percentage", 0.0)
        
        p_avg = (vv_pos + vv_neg + vh_pos + vh_neg) / 4.0
        
        def clamp(val: float, min_val: float, max_val: float) -> float:
            return max(min_val, min(val, max_val))
            
        # 15.0% acts as a conservative prototype engineering baseline, not a physical constant
        s_ext = clamp(((p_avg - 15.0) / 35.0) * 100.0, 0.0, 100.0)
        
        # 2. Backscatter Anomaly Magnitude
        vv_p90 = vv_stats.get("p90", 0.0)
        vv_p10 = vv_stats.get("p10", 0.0)
        vh_p90 = vh_stats.get("p90", 0.0)
        vh_p10 = vh_stats.get("p10", 0.0)
        
        i_vv = vv_p90 - vv_p10
        i_vh = vh_p90 - vh_p10
        i_max = max(i_vv, i_vh)
        
        m_mag = clamp(((i_max - 8.0) / 12.0) * 100.0, 0.0, 100.0)
        
        # 3. Final RSCI Index
        rsci = 0.40 * s_ext + 0.60 * m_mag
        rsci = clamp(rsci, 0.0, 100.0)
        
        # Categories mapping
        if rsci <= 25.0:
            category = "Stable"
        elif rsci <= 50.0:
            category = "Minor Surface Change"
        elif rsci <= 75.0:
            category = "Moderate Surface Change"
        else:
            category = "Significant Surface Change"
            
        scientific_notice = (
            "Radar Surface Change Index represents relative satellite-observed surface change "
            "between two acquisitions. It is not a landslide probability and does not confirm "
            "that a landslide has occurred."
        )
        
        return {
            "radar_surface_change_index": round(rsci, 2),
            "category": category,
            "spatial_extent_score": round(s_ext, 2),
            "anomaly_magnitude_score": round(m_mag, 2),
            "average_significant_change_percentage": round(p_avg, 2),
            "vv_spread_db": round(i_vv, 4),
            "vh_spread_db": round(i_vh, 4),
            "supporting_cross_pol_change": {
                "mean": cross_stats.get("mean", 0.0),
                "median": cross_stats.get("median", 0.0),
                "std": cross_stats.get("std", 0.0)
            },
            "scientific_notice": scientific_notice
        }
