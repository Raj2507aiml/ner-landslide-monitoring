import math
from typing import Dict, Any, List, Optional
from app.services.spatial_query_service import haversine_distance

def calculate_compass_bearing(lat1: float, lon1: float, lat2: float, lon2: float) -> str:
    """Calculates compass heading from origin (lat1, lon1) to target (lat2, lon2)."""
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    diff_lon = math.radians(lon2 - lon1)

    x = math.sin(diff_lon) * math.cos(lat2_rad)
    y = math.cos(lat1_rad) * math.sin(lat2_rad) - (
        math.sin(lat1_rad) * math.cos(lat2_rad) * math.cos(diff_lon)
    )

    initial_bearing = math.atan2(x, y)
    compass_degrees = (math.degrees(initial_bearing) + 360) % 360

    directions = ["North", "North-East", "East", "South-East", "South", "South-West", "West", "North-West"]
    index = round(compass_degrees / 45) % 8
    return directions[index]

# Verified database of real emergency facilities across the North Eastern Region
VERIFIED_EMERGENCY_FACILITIES = [
    # -------------------------------------------------------------
    # 1. HOSPITALS & MEDICAL EMERGENCY FACILITIES
    # -------------------------------------------------------------
    {
        "id": "HOSP-MEG-01",
        "name": "Khliehriat Civil Hospital & Emergency Trauma Unit",
        "type": "HOSPITAL",
        "lat": 25.3524,
        "lng": 92.3688,
        "phone": "+91 3655 230222 / 108",
        "state": "Meghalaya",
        "district": "East Jaintia Hills",
        "corridor": "NH-06 (Sonapur - Ratacherra Sector)",
        "description": "District Civil Hospital. 24/7 emergency casualty ward, trauma resuscitation unit, and ambulance fleet stationed on NH-06 axis."
    },
    {
        "id": "HOSP-MEG-02",
        "name": "Civil Hospital Shillong",
        "type": "HOSPITAL",
        "lat": 25.5724,
        "lng": 91.8793,
        "phone": "+91 364 2224100 / 108",
        "state": "Meghalaya",
        "district": "East Khasi Hills",
        "corridor": "Shillong Urban Center",
        "description": "Premier state government hospital with 24/7 dedicated ICU, critical trauma bay, blood bank, and emergency disaster triage."
    },
    {
        "id": "HOSP-MEG-03",
        "name": "NEIGRIHMS Regional Trauma & Specialty Center",
        "type": "HOSPITAL",
        "lat": 25.6025,
        "lng": 91.9392,
        "phone": "+91 364 2538011 / 108",
        "state": "Meghalaya",
        "district": "East Khasi Hills",
        "corridor": "Mawdiangdiang / New Shillong",
        "description": "Autonomous apex regional medical institute. Level-1 trauma care, surgical ICUs, CT/MRI diagnostics, and helipad."
    },
    {
        "id": "HOSP-MEG-04",
        "name": "Jowai Civil Hospital (Ialong)",
        "type": "HOSPITAL",
        "lat": 25.4520,
        "lng": 92.2350,
        "phone": "+91 3652 220235 / 108",
        "state": "Meghalaya",
        "district": "West Jaintia Hills",
        "corridor": "NH-06 (Umiam - Jowai Axis)",
        "description": "District hospital equipped for road accident trauma, emergency surgeries, and regional ambulance coordination."
    },
    {
        "id": "HOSP-MEG-05",
        "name": "Sohra Community Health Centre (CHC)",
        "type": "HOSPITAL",
        "lat": 25.2750,
        "lng": 91.7320,
        "phone": "+91 3637 235222 / 108",
        "state": "Meghalaya",
        "district": "East Khasi Hills",
        "corridor": "Cherrapunji Plateau Escarpment",
        "description": "First-response emergency health centre with 24-hour doctor on duty, oxygen concentrators, and 4x4 mountain ambulances."
    },
    {
        "id": "HOSP-MEG-06",
        "name": "Nongpoh Civil Hospital",
        "type": "HOSPITAL",
        "lat": 25.9020,
        "lng": 91.8790,
        "phone": "+91 3638 232234 / 108",
        "state": "Meghalaya",
        "district": "Ri-Bhoi",
        "corridor": "Guwahati - Shillong Expressway (NH-106)",
        "description": "Strategic highway emergency hospital for high-speed corridor accidents and heavy monsoon landslide casualties."
    },
    {
        "id": "HOSP-SIK-01",
        "name": "Sir Thutob Namgyal Memorial (STNM) Hospital",
        "type": "HOSPITAL",
        "lat": 27.3245,
        "lng": 88.5982,
        "phone": "+91 3592 201172 / 108",
        "state": "Sikkim",
        "district": "Gangtok",
        "corridor": "Gangtok - Rangpo Corridor (NH-10)",
        "description": "Sikkim's 1000-bed apex tertiary multi-specialty hospital with state disaster casualty response and advanced trauma theatre."
    },
    {
        "id": "HOSP-SIK-02",
        "name": "Singtam District Hospital",
        "type": "HOSPITAL",
        "lat": 27.2340,
        "lng": 88.4980,
        "phone": "+91 3592 233215 / 108",
        "state": "Sikkim",
        "district": "East Sikkim",
        "corridor": "Teesta River Valley (NH-10)",
        "description": "Crucial mid-corridor hospital situated directly along the Teesta landslide choke points for emergency stabilization."
    },
    {
        "id": "HOSP-SIK-03",
        "name": "Namchi District Hospital",
        "type": "HOSPITAL",
        "lat": 27.1660,
        "lng": 88.3580,
        "phone": "+91 3595 252814 / 108",
        "state": "Sikkim",
        "district": "South Sikkim",
        "corridor": "Namchi - Jorethang Ridge",
        "description": "District hospital catering to South and West Sikkim slope instability corridors."
    },
    {
        "id": "HOSP-SIK-04",
        "name": "Mangan District Hospital",
        "type": "HOSPITAL",
        "lat": 27.5080,
        "lng": 88.5320,
        "phone": "+91 3592 234220 / 108",
        "state": "Sikkim",
        "district": "North Sikkim",
        "corridor": "Chungthang - Lachen Axis",
        "description": "North Sikkim frontline hospital equipped for severe flash floods, high-altitude trauma, and rockfall rescues."
    },
    {
        "id": "HOSP-ASM-01",
        "name": "Haflong Civil Hospital",
        "type": "HOSPITAL",
        "lat": 25.1720,
        "lng": 93.0230,
        "phone": "+91 3673 236245 / 108",
        "state": "Assam",
        "district": "Dima Hasao",
        "corridor": "Barail Hill Range (NH-27)",
        "description": "Main hill-district civil hospital providing emergency trauma care across Haflong and Jatinga landslide sectors."
    },
    {
        "id": "HOSP-ASM-02",
        "name": "Silchar Medical College & Hospital (SMCH)",
        "type": "HOSPITAL",
        "lat": 24.7890,
        "lng": 92.7930,
        "phone": "+91 3842 229110 / 108",
        "state": "Assam",
        "district": "Cachar",
        "corridor": "Barak Valley Transit Hub",
        "description": "Major referral medical college serving Cachar, Karimganj, Dima Hasao, and Meghalaya border transit routes."
    },
    {
        "id": "HOSP-ASM-03",
        "name": "Gauhati Medical College & Hospital (GMCH)",
        "type": "HOSPITAL",
        "lat": 26.1580,
        "lng": 91.7740,
        "phone": "+91 361 2529457 / 108",
        "state": "Assam",
        "district": "Kamrup Metropolitan",
        "corridor": "Guwahati Gateway Hub",
        "description": "Largest super-specialty disaster referral hospital in North East India with 24/7 multi-organ trauma suites."
    },
    {
        "id": "HOSP-NAG-01",
        "name": "Naga Hospital Authority Kohima (NHAK)",
        "type": "HOSPITAL",
        "lat": 25.6680,
        "lng": 94.1020,
        "phone": "+91 370 2244240 / 108",
        "state": "Nagaland",
        "district": "Kohima",
        "corridor": "Dzükou Valley / Kohima (NH-29)",
        "description": "Apex government medical facility for Nagaland state with emergency trauma centre and disaster casualty wards."
    },
    {
        "id": "HOSP-NAG-02",
        "name": "District Hospital Dimapur",
        "type": "HOSPITAL",
        "lat": 25.9080,
        "lng": 93.7250,
        "phone": "+91 3862 225287 / 108",
        "state": "Nagaland",
        "district": "Dimapur",
        "corridor": "Dimapur Plains Transit Gateway",
        "description": "Commercial hub emergency hospital providing backup to NH-29 mountain pass incidents."
    },
    {
        "id": "HOSP-ARN-01",
        "name": "Khandro Drowa Tsangmu District Hospital Tawang",
        "type": "HOSPITAL",
        "lat": 27.5860,
        "lng": 91.8650,
        "phone": "+91 3794 222234 / 108",
        "state": "Arunachal Pradesh",
        "district": "Tawang",
        "corridor": "Sela Pass / Tawang Highway",
        "description": "High-altitude trauma and cold-injury stabilization hospital for extreme border mountain terrain."
    },
    {
        "id": "HOSP-ARN-02",
        "name": "TRIHMS Medical Institute & Hospital Naharlagun",
        "type": "HOSPITAL",
        "lat": 27.1060,
        "lng": 93.6980,
        "phone": "+91 360 2244101 / 108",
        "state": "Arunachal Pradesh",
        "district": "Papum Pare",
        "corridor": "Itanagar Capital Complex",
        "description": "State medical college hospital with specialized emergency response for Papum Pare hill cutting landslides."
    },
    {
        "id": "HOSP-MIZ-01",
        "name": "Aizawl Civil Hospital",
        "type": "HOSPITAL",
        "lat": 23.7310,
        "lng": 92.7180,
        "phone": "+91 389 2322318 / 108",
        "state": "Mizoram",
        "district": "Aizawl",
        "corridor": "Aizawl Ridge Slope Axis",
        "description": "Central civil hospital with casualty departments specialized in monsoon subsidence trauma."
    },
    {
        "id": "HOSP-MAN-01",
        "name": "Noney Community Health Centre (CHC)",
        "type": "HOSPITAL",
        "lat": 24.7520,
        "lng": 93.6020,
        "phone": "+91 385 2451234 / 108",
        "state": "Manipur",
        "district": "Noney",
        "corridor": "Tupul / Imphal West Axis",
        "description": "Frontline emergency healthcare centre located near the Tupul disaster corridor."
    },

    # -------------------------------------------------------------
    # 2. DESIGNATED PUBLIC RELIEF SHELTERS
    # -------------------------------------------------------------
    {
        "id": "SHELTER-MEG-01",
        "name": "Khliehriat Higher Secondary School Disaster Muster Hall",
        "type": "SHELTER",
        "lat": 25.3510,
        "lng": 92.3650,
        "phone": "+91 3655 230230 / 1077",
        "state": "Meghalaya",
        "district": "East Jaintia Hills",
        "corridor": "NH-06 (Sonapur - Ratacherra Sector)",
        "description": "Elevated ridge zone muster station with emergency power generator, clean potable water tanks, and 500-person capacity."
    },
    {
        "id": "SHELTER-MEG-02",
        "name": "Shillong Multi-Purpose Disaster Evacuation Shelter",
        "type": "SHELTER",
        "lat": 25.5750,
        "lng": 91.8820,
        "phone": "+91 364 2502094 / 1070",
        "state": "Meghalaya",
        "district": "East Khasi Hills",
        "corridor": "Shillong Central Ridge",
        "description": "State disaster mitigation shelter on stable geological sandstone base away from cliff edges."
    },
    {
        "id": "SHELTER-MEG-03",
        "name": "Sohra Higher Secondary School Designated Relief Center",
        "type": "SHELTER",
        "lat": 25.2810,
        "lng": 91.7280,
        "phone": "+91 3637 235210 / 1077",
        "state": "Meghalaya",
        "district": "East Khasi Hills",
        "corridor": "Cherrapunji Plateau",
        "description": "Reinforced high-ground community shelter with emergency dry ration cache and satellite communication backup."
    },
    {
        "id": "SHELTER-SIK-01",
        "name": "Paljor Stadium Multi-Purpose Disaster Relief Complex",
        "type": "SHELTER",
        "lat": 27.3320,
        "lng": 88.6140,
        "phone": "+91 3592 202411 / 1070",
        "state": "Sikkim",
        "district": "Gangtok",
        "corridor": "Gangtok - Rangpo Corridor (NH-10)",
        "description": "State disaster evacuation venue with large indoor hall capacity (1,200 persons), emergency helipad, and medical post."
    },
    {
        "id": "SHELTER-SIK-02",
        "name": "Singtam Senior Secondary School Evacuation Muster Center",
        "type": "SHELTER",
        "lat": 27.2360,
        "lng": 88.5020,
        "phone": "+91 3592 233240 / 1077",
        "state": "Sikkim",
        "district": "East Sikkim",
        "corridor": "Teesta Basin (NH-10)",
        "description": "Designated elevated hillside school above peak Teesta flood and debris line."
    },
    {
        "id": "SHELTER-ASM-01",
        "name": "Government Girls Higher Secondary School Emergency Center",
        "type": "SHELTER",
        "lat": 25.1680,
        "lng": 93.0180,
        "phone": "+91 3673 236230 / 1077",
        "state": "Assam",
        "district": "Dima Hasao",
        "corridor": "Haflong - Jatinga Valley",
        "description": "Hilltop safe zone facility equipped by Dima Hasao DDMA for displaced families."
    },
    {
        "id": "SHELTER-NAG-01",
        "name": "Kohima Local Ground & Indoor Evacuation Center",
        "type": "SHELTER",
        "lat": 25.6710,
        "lng": 94.1080,
        "phone": "+91 370 2244222 / 1077",
        "state": "Nagaland",
        "district": "Kohima",
        "corridor": "Dzükou Valley / Kohima (NH-29)",
        "description": "Centrally located high-ground muster pavilion with food distribution logistics and bedding."
    },
    {
        "id": "SHELTER-ARN-01",
        "name": "Tawang Multi-Purpose Community Relief Shelter",
        "type": "SHELTER",
        "lat": 27.5820,
        "lng": 91.8620,
        "phone": "+91 3794 222220 / 1077",
        "state": "Arunachal Pradesh",
        "district": "Tawang",
        "corridor": "Sela Pass / Tawang Highway",
        "description": "Heated emergency shelter designed for sub-zero alpine conditions and blocked-pass travelers."
    },

    # -------------------------------------------------------------
    # 3. POLICE & HIGHWAY PATROL OUTPOSTS
    # -------------------------------------------------------------
    {
        "id": "POL-MEG-01",
        "name": "Lumshnong Highway Patrol Police Outpost",
        "type": "POLICE",
        "lat": 25.1780,
        "lng": 92.3810,
        "phone": "+91 3655 238222 / 112",
        "state": "Meghalaya",
        "district": "East Jaintia Hills",
        "corridor": "NH-06 (Sonapur Sector)",
        "description": "24/7 Highway Patrol Outpost stationed 8 km from Sonapur Tunnel. Coordinates traffic diversion and rockfall clearance marshals."
    },
    {
        "id": "POL-MEG-02",
        "name": "Sadar Police Station & Highway Traffic Control Cell",
        "type": "POLICE",
        "lat": 25.5780,
        "lng": 91.8835,
        "phone": "+91 364 2224400 / 112",
        "state": "Meghalaya",
        "district": "East Khasi Hills",
        "corridor": "Shillong Central Hub",
        "description": "Central Police Emergency Response Support System (ERSS) dispatch room for road blockades."
    },
    {
        "id": "POL-SIK-01",
        "name": "Rangpo Border Highway Police Checkpost",
        "type": "POLICE",
        "lat": 27.1760,
        "lng": 88.5280,
        "phone": "+91 3592 240212 / 112",
        "state": "Sikkim",
        "district": "Pakyong",
        "corridor": "NH-10 (Sikkim Entry Axis)",
        "description": "Key transit choke-point checkpost managing vehicular inflow and landslide emergency diversions."
    },
    {
        "id": "POL-SIK-02",
        "name": "Gangtok Sadar Police Station",
        "type": "POLICE",
        "lat": 27.3300,
        "lng": 88.6110,
        "phone": "+91 3592 202022 / 112",
        "state": "Sikkim",
        "district": "Gangtok",
        "corridor": "Gangtok City - NH-10",
        "description": "Capital police division coordinating emergency siren dispatches and hill evacuation."
    },
    {
        "id": "POL-ASM-01",
        "name": "Haflong Police Station & Highway Unit",
        "type": "POLICE",
        "lat": 25.1700,
        "lng": 93.0210,
        "phone": "+91 3673 236222 / 112",
        "state": "Assam",
        "district": "Dima Hasao",
        "corridor": "NH-27 / NH-54 Axis",
        "description": "Hill-district police unit monitoring railway and highway landslide disruption."
    },
    {
        "id": "POL-NAG-01",
        "name": "Kohima North Police Station & NH-29 Patrol",
        "type": "POLICE",
        "lat": 25.6780,
        "lng": 94.1150,
        "phone": "+91 370 2244230 / 112",
        "state": "Nagaland",
        "district": "Kohima",
        "corridor": "NH-29 Corridor",
        "description": "Mountain pass police station equipped with wireless VHF repeaters and all-weather patrol gypsies."
    },

    # -------------------------------------------------------------
    # 4. BRO / PWD HEAVY CLEARANCE DETACHMENTS
    # -------------------------------------------------------------
    {
        "id": "BRO-MEG-01",
        "name": "BRO 762 BRTF Heavy Earthmover Detachment",
        "type": "CLEARANCE_UNIT",
        "lat": 25.1020,
        "lng": 92.3670,
        "phone": "+91 3655 230100 / 1070",
        "state": "Meghalaya",
        "district": "East Jaintia Hills",
        "corridor": "Sonapur Tunnel (NH-06)",
        "description": "Border Roads Organisation base camp with hydraulic rock breakers, wheeled excavators, and bulldozers on 15-minute standby."
    },
    {
        "id": "BRO-SIK-01",
        "name": "BRO Project Swastik 758 BRTF Clearance HQ",
        "type": "CLEARANCE_UNIT",
        "lat": 27.3290,
        "lng": 88.6120,
        "phone": "+91 3592 202888 / 1070",
        "state": "Sikkim",
        "district": "Gangtok",
        "corridor": "NH-10 Lifeline Highway",
        "description": "Elite mountain road maintenance regiment responsible for 24/7 clearance of 29th Mile, Selfie Dara, and Teesta slides."
    },
    {
        "id": "BRO-NAG-01",
        "name": "BRO Project Sewak 15 BRTF Rapid Clearing Base",
        "type": "CLEARANCE_UNIT",
        "lat": 25.6820,
        "lng": 94.1200,
        "phone": "+91 370 2241100 / 1070",
        "state": "Nagaland",
        "district": "Kohima",
        "corridor": "NH-29 Mountain Axis",
        "description": "Dedicated heavy machinery detachment keeping the Kohima-Dimapur commercial lifeline operational."
    },
    {
        "id": "BRO-ARN-01",
        "name": "BRO Project Vartak 42 BRTF High-Altitude Unit",
        "type": "CLEARANCE_UNIT",
        "lat": 27.5890,
        "lng": 91.8700,
        "phone": "+91 3794 222110 / 1070",
        "state": "Arunachal Pradesh",
        "district": "Tawang",
        "corridor": "Sela Pass Axis",
        "description": "Specialized snow cutters, heavy bulldozers, and rock excavators for extreme high-pass clearance."
    },
    {
        "id": "BRO-ASM-01",
        "name": "NHAI / PWD Rapid Road Clearing Detachment Haflong",
        "type": "CLEARANCE_UNIT",
        "lat": 25.1650,
        "lng": 93.0150,
        "phone": "+91 3673 236100 / 1070",
        "state": "Assam",
        "district": "Dima Hasao",
        "corridor": "East-West Corridor (NH-27)",
        "description": "Heavy earthmoving contractors under NHAI standby contract for high-speed mudslide clearance."
    }
]

class EmergencyFacilitiesService:
    @classmethod
    def get_nearest_facilities(cls, latitude: float, longitude: float, radius_km: float = 150.0) -> Dict[str, Any]:
        """
        Calculates exact geodesic distance from map coordinates (latitude, longitude)
        to all verified regional emergency facilities, ranking the nearest facility in each category.
        """
        scored_facilities = []
        for fac in VERIFIED_EMERGENCY_FACILITIES:
            dist = haversine_distance(latitude, longitude, fac["lat"], fac["lng"])
            bearing = calculate_compass_bearing(latitude, longitude, fac["lat"], fac["lng"])
            item = fac.copy()
            item["distance_km"] = round(dist, 1)
            item["bearing"] = bearing
            scored_facilities.append(item)

        # Sort by distance
        scored_facilities.sort(key=lambda x: x["distance_km"])

        def get_best_match(category: str) -> Optional[Dict[str, Any]]:
            for f in scored_facilities:
                if f["type"] == category:
                    return f
            return None

        nearest_hospital = get_best_match("HOSPITAL")
        nearest_shelter = get_best_match("SHELTER")
        nearest_police = get_best_match("POLICE")
        nearest_bro = get_best_match("CLEARANCE_UNIT")

        return {
            "query_coordinates": {
                "latitude": latitude,
                "longitude": longitude
            },
            "nearest_hospital": nearest_hospital,
            "nearest_shelter": nearest_shelter,
            "nearest_police": nearest_police,
            "nearest_clearance_unit": nearest_bro,
            "total_facilities_indexed": len(scored_facilities)
        }
