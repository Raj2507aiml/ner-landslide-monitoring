"""
ML Inference Service Smoke Test - Phase 3 Checkpoint 11D

Validates lazy loading singleton patterns, probability bounds, risk level mappings,
flat aspect coordinate treatments, and execution timing benchmarks.
"""

import os
import sys
import time

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.abspath(os.path.join(SCRIPTS_DIR, ".."))
sys.path.insert(0, BACKEND_DIR)

from app.services.ml_susceptibility_service import MLSusceptibilityService

def run_smoke_test():
    print("=== Running ML Service Smoke Test ===")
    
    # 1. Benchmark lazy loading vs memory access
    start_time = time.time()
    res1 = MLSusceptibilityService.predict_susceptibility(
        latitude=27.35,
        longitude=88.62,
        elevation=1500.0,
        slope=25.0,
        aspect=180.0
    )
    first_duration = time.time() - start_time
    print(f"  First prediction (includes disk load): {first_duration*1000:.2f}ms")
    
    start_time = time.time()
    res2 = MLSusceptibilityService.predict_susceptibility(
        latitude=27.35,
        longitude=88.62,
        elevation=1500.0,
        slope=25.0,
        aspect=180.0
    )
    second_duration = time.time() - start_time
    print(f"  Second prediction (in-memory cache):   {second_duration*1000:.2f}ms")
    
    # Confirm singleton
    assert second_duration < first_duration, "WARNING: Singleton loading failed, model is reloading on prediction."
    print("  Status: SUCCESS (Singleton model loading confirmed).")
    
    # 2. Verify Output Schema & Ranges
    print("\nInference Output Fields:")
    for k, v in res1.items():
        print(f"  - {k}: {v}")
        
    assert 0.0 <= res1["probability"] <= 1.0, f"Out-of-bounds probability: {res1['probability']}"
    assert res1["risk_level"] in ("Low", "Moderate", "High", "Very High"), f"Invalid risk level: {res1['risk_level']}"
    assert res1["threshold_used"] == 0.50, f"Incorrect threshold referenced: {res1['threshold_used']}"
    print("  Status: SUCCESS (Output value validation passed).")
    
    # 3. Verify Flat Aspect Transformations
    # Flat slope (<0.1) should override aspect to flat conventions
    res_flat = MLSusceptibilityService.predict_susceptibility(
        latitude=27.35,
        longitude=88.62,
        elevation=100.0,
        slope=0.0,
        aspect=-1.0
    )
    assert res_flat["aspect"] == -1.0, f"Flat aspect override failed: {res_flat['aspect']}"
    print("  Status: SUCCESS (Flat aspect transformation validation passed).")
    
    print("\n=== Smoke Test Completed Successfully! ===")

if __name__ == "__main__":
    run_smoke_test()
