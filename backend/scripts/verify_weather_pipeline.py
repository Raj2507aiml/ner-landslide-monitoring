import os
import sys

# ── Inject backend directory into sys.path ──────────────────────────────────
SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.abspath(os.path.join(SCRIPTS_DIR, ".."))
sys.path.insert(0, BACKEND_DIR)

from app.services.weather_service import fetch_weather_telemetry

def run_weather_check():
    print("=== Starting Backend Weather Pipeline Check ===")
    
    # NER coordinates: Shillong region
    lat = 25.5788
    lon = 91.8831
    
    try:
        data = fetch_weather_telemetry(lat, lon)
        print("Telemetry Fetch: [OK]")
        print("Returned Fields:")
        print(f"  Latitude: {data['latitude']}")
        print(f"  Longitude: {data['longitude']}")
        print(f"  Temperature: {data['temperature']} {data['temperature_unit']}")
        print(f"  Humidity: {data['relative_humidity']} {data['relative_humidity_unit']}")
        print(f"  Current Precip: {data['current_precipitation']} {data['current_precipitation_unit']}")
        print(f"  Daily Precip (Today): {data['daily_precipitation']} {data['daily_precipitation_unit']}")
        
        print("\nAntecedent Metrics:")
        print(f"  3-Day Cumulative: {data['three_day_cumulative']} mm")
        print(f"  7-Day Cumulative: {data['seven_day_cumulative']} mm")
        print(f"  Saturation Classification: {data['saturation_classification']}")
        
        print("\nDaily Precipitation History (past 7 days + today):")
        for rec in data["daily_precipitation_history"]:
            print(f"  Date: {rec['date']} -> {rec['precipitation_mm']} mm")
            
        # Verify calculation correctness mathematically
        history_vals = [r["precipitation_mm"] for r in data["daily_precipitation_history"]]
        calculated_3d = round(sum(history_vals[-3:]), 2)
        calculated_7d = round(sum(history_vals[-7:]), 2)
        
        print("\nVerification Checks:")
        print(f"  Is 3-day sum math correct? {calculated_3d == data['three_day_cumulative']} (Expected: {calculated_3d}, Got: {data['three_day_cumulative']})")
        print(f"  Is 7-day sum math correct? {calculated_7d == data['seven_day_cumulative']} (Expected: {calculated_7d}, Got: {data['seven_day_cumulative']})")
        
        assert calculated_3d == data["three_day_cumulative"]
        assert calculated_7d == data["seven_day_cumulative"]
        
        print("\n=== Backend Weather Pipeline Verified Successfully ===")
        
    except Exception as e:
        print("Check failed:", e)

if __name__ == "__main__":
    run_weather_check()
