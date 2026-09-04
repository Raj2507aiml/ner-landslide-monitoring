import os
import sys
from fastapi.testclient import TestClient

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.abspath(os.path.join(SCRIPTS_DIR, ".."))
sys.path.insert(0, BACKEND_DIR)

from app.main import app

def test_api():
    client = TestClient(app)
    
    # 1. Gangtok
    resp1 = client.post("/api/v1/satellite/automatic-change-analysis", json={"latitude": 27.3314, "longitude": 88.6138})
    print("Gangtok API Response Status Code:", resp1.status_code)
    data1 = resp1.json()
    print("Gangtok Status:", data1.get("status"))
    print("Gangtok RSCI:", data1.get("radar_surface_change_signal", {}).get("radar_surface_change_index"))
    assert resp1.status_code == 200
    assert data1["status"] == "PAIRED_SUCCESS"

    # 2. Meghalaya dashboard coordinate
    resp2 = client.post("/api/v1/satellite/automatic-change-analysis", json={"latitude": 25.52706310546959, "longitude": 91.35848472637227})
    print("\nMeghalaya API Response Status Code:", resp2.status_code)
    data2 = resp2.json()
    print("Meghalaya Status:", data2.get("status"))
    print("Meghalaya RSCI:", data2.get("radar_surface_change_signal", {}).get("radar_surface_change_index"))
    assert resp2.status_code == 200
    assert data2["status"] == "PAIRED_SUCCESS"
    print("\n>>> ALL API TESTS PASSED!")

if __name__ == "__main__":
    test_api()
