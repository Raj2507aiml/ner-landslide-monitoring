import os
import sys
import json

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.abspath(os.path.join(SCRIPTS_DIR, ".."))
sys.path.insert(0, BACKEND_DIR)

from app.services.automatic_satellite_pair_service import AutomaticSatellitePairService

def main():
    lat = 25.52706310546959
    lon = 91.35848472637227
    print(f"Testing Automatic Satellite Change for Lat={lat}, Lon={lon}")
    try:
        res = AutomaticSatellitePairService.analyze_location_change(lat, lon, 5.0)
        print("Result:", res)
    except Exception as e:
        print("Caught Exception:", type(e).__name__, str(e))

if __name__ == "__main__":
    main()
