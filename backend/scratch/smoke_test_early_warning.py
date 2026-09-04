"""
Early Warning Service Smoke Test - Phase 6 Checkpoint 15.2

Runs early warning evaluations across different combinations of
hazard levels, rain intensities, and satellite availability states.
"""

import os
import sys

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.abspath(os.path.join(SCRIPTS_DIR, ".."))
sys.path.insert(0, BACKEND_DIR)

from app.services.early_warning_service import EarlyWarningService

def main():
    print("=" * 60)
    print("EARLY WARNING DECISION ENGINE SMOKE TEST")
    print("-" * 60)
    
    # ----------------------------------------------------
    # Scenario 1: Low Hazard + Stable Satellite -> NORMAL
    # ----------------------------------------------------
    hazard_1 = {
        "composite_risk_index": 20.0,
        "risk_level": "Low",
        "components": {
            "rainfall_trigger": {"rainfall_score": 2.0}
        }
    }
    radar_1 = {
        "status": "PAIRED_SUCCESS",
        "radar_surface_change_signal": {
            "radar_surface_change_index": 5.0,
            "category": "Stable"
        }
    }
    
    res_1 = EarlyWarningService.evaluate_warning_status(hazard_1, radar_1)
    print("Scenario 1: Low Hazard + Stable Satellite")
    print(f"  Warning Level:    {res_1['warning_level']}")
    print(f"  Action:           {res_1['recommended_action']}")
    print(f"  Reasoning:        {res_1['reasoning']}")
    print()
    assert res_1["warning_level"] == "NORMAL"
    
    # ----------------------------------------------------
    # Scenario 2: High Hazard + Stable Satellite -> WATCH
    # ----------------------------------------------------
    hazard_2 = {
        "composite_risk_index": 82.0,
        "risk_level": "Very High",
        "components": {
            "rainfall_trigger": {"rainfall_score": 12.0}
        }
    }
    radar_2 = {
        "status": "PAIRED_SUCCESS",
        "radar_surface_change_signal": {
            "radar_surface_change_index": 15.0,
            "category": "Stable"
        }
    }
    
    res_2 = EarlyWarningService.evaluate_warning_status(hazard_2, radar_2)
    print("Scenario 2: High Hazard + Stable Satellite")
    print(f"  Warning Level:    {res_2['warning_level']}")
    print(f"  Action:           {res_2['recommended_action']}")
    print(f"  Reasoning:        {res_2['reasoning']}")
    print()
    assert res_2["warning_level"] == "WATCH"
    
    # ----------------------------------------------------
    # Scenario 3: Elevated Hazard + Significant Satellite Change -> ALERT
    # ----------------------------------------------------
    hazard_3 = {
        "composite_risk_index": 62.0,
        "risk_level": "High",
        "components": {
            "rainfall_trigger": {"rainfall_score": 14.0}
        }
    }
    radar_3 = {
        "status": "PAIRED_SUCCESS",
        "radar_surface_change_signal": {
            "radar_surface_change_index": 82.0,
            "category": "Significant Surface Change"
        }
    }
    
    res_3 = EarlyWarningService.evaluate_warning_status(hazard_3, radar_3)
    print("Scenario 3: Elevated Hazard + Significant Satellite Change")
    print(f"  Warning Level:    {res_3['warning_level']}")
    print(f"  Action:           {res_3['recommended_action']}")
    print(f"  Reasoning:        {res_3['reasoning']}")
    print()
    assert res_3["warning_level"] == "ALERT"
    
    # ----------------------------------------------------
    # Scenario 4a: High Hazard + High Rainfall Trigger + Sat Unavailable -> CRITICAL
    # ----------------------------------------------------
    hazard_4a = {
        "composite_risk_index": 82.0,
        "risk_level": "Very High",
        "components": {
            "rainfall_trigger": {"rainfall_score": 25.0}
        }
    }
    
    res_4a = EarlyWarningService.evaluate_warning_status(hazard_4a, None)
    print("Scenario 4a: High Hazard + High Rain (Satellite Unavailable)")
    print(f"  Warning Level:    {res_4a['warning_level']}")
    print(f"  Action:           {res_4a['recommended_action']}")
    print(f"  Reasoning:        {res_4a['reasoning']}")
    print()
    assert res_4a["warning_level"] == "CRITICAL"
    
    # ----------------------------------------------------
    # Scenario 4b: High Hazard + Low Rainfall Trigger + Sat Unavailable -> WATCH
    # ----------------------------------------------------
    hazard_4b = {
        "composite_risk_index": 82.0,
        "risk_level": "Very High",
        "components": {
            "rainfall_trigger": {"rainfall_score": 5.0}
        }
    }
    
    res_4b = EarlyWarningService.evaluate_warning_status(hazard_4b, None)
    print("Scenario 4b: High Hazard + Low Rain (Satellite Unavailable)")
    print(f"  Warning Level:    {res_4b['warning_level']}")
    print(f"  Action:           {res_4b['recommended_action']}")
    print(f"  Reasoning:        {res_4b['reasoning']}")
    print()
    assert res_4b["warning_level"] == "WATCH"

    # ----------------------------------------------------
    # Scenario 4c: High Hazard + Meaningful Rainfall Trigger + Sat Unavailable -> ALERT
    # ----------------------------------------------------
    hazard_4c = {
        "composite_risk_index": 82.0,
        "risk_level": "Very High",
        "components": {
            "rainfall_trigger": {"rainfall_score": 17.0}
        }
    }
    
    res_4c = EarlyWarningService.evaluate_warning_status(hazard_4c, None)
    print("Scenario 4c: High Hazard + Meaningful Rain (Satellite Unavailable)")
    print(f"  Warning Level:    {res_4c['warning_level']}")
    print(f"  Action:           {res_4c['recommended_action']}")
    print(f"  Reasoning:        {res_4c['reasoning']}")
    print()
    assert res_4c["warning_level"] == "ALERT"

    print("=" * 60)
    print("VERIFICATION SUCCESSFUL: Early Warning Engine evaluates all scenarios correctly.")
    print("=" * 60)

if __name__ == "__main__":
    main()
