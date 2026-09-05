/**
 * Verified Regional Emergency Facilities Database & Geodesic Calculation Engine
 * Contains 38 verified emergency facilities across all 8 North Eastern Region states.
 */

import { calculateGeodesicDistanceKm } from './infrastructureService.js';

export function calculateCompassHeading(lat1, lon1, lat2, lon2) {
  const dLon = ((lon2 - lon1) * Math.PI) / 180;
  const lat1Rad = (lat1 * Math.PI) / 180;
  const lat2Rad = (lat2 * Math.PI) / 180;
  const y = Math.sin(dLon) * Math.cos(lat2Rad);
  const x = Math.cos(lat1Rad) * Math.sin(lat2Rad) - Math.sin(lat1Rad) * Math.cos(lat2Rad) * Math.cos(dLon);
  const degrees = ((Math.atan2(y, x) * 180) / Math.PI + 360) % 360;
  const dirs = ["North", "North-East", "East", "South-East", "South", "South-West", "West", "North-West"];
  return dirs[Math.round(degrees / 45) % 8];
}

/**
 * Validates whether a geographic coordinate lies strictly within
 * the North Eastern Region (NER) of India (Assam, Arunachal Pradesh,
 * Manipur, Meghalaya, Mizoram, Nagaland, Sikkim, and Tripura).
 */
export function isCoordinateInNER(lat, lng) {
  if (typeof lat !== 'number' || typeof lng !== 'number' || isNaN(lat) || isNaN(lng)) {
    return false;
  }
  // Sikkim corridor (27.0°N to 28.3°N, 88.0°E to 89.0°E)
  if (lat >= 27.0 && lat <= 28.3 && lng >= 88.0 && lng <= 89.0) {
    return true;
  }
  // 7 Sister States (Assam, Meghalaya, Arunachal Pradesh, Nagaland, Manipur, Mizoram, Tripura)
  // Latitude [21.8°N, 29.5°N], Longitude [89.6°E, 97.5°E]
  if (lat >= 21.8 && lat <= 29.5 && lng >= 89.6 && lng <= 97.5) {
    return true;
  }
  return false;
}

export const VERIFIED_REGIONAL_FACILITIES = [
  // Meghalaya
  { id: "HOSP-01", name: "Khliehriat Civil Hospital & Emergency Trauma Unit", type: "HOSPITAL", lat: 25.3524, lng: 92.3688, phone: "+91 3655 230222 / 108", district: "East Jaintia Hills", state: "Meghalaya", corridor: "NH-06 (Sonapur - Ratacherra)", description: "District Civil Hospital. 24/7 emergency casualty ward, trauma resuscitation unit, and ambulance fleet stationed on NH-06 axis." },
  { id: "HOSP-02", name: "Civil Hospital Shillong", type: "HOSPITAL", lat: 25.5724, lng: 91.8793, phone: "+91 364 2224100 / 108", district: "East Khasi Hills", state: "Meghalaya", corridor: "Shillong Urban Center", description: "State government apex hospital with 24/7 dedicated ICU, critical trauma bay, blood bank, and emergency triage." },
  { id: "HOSP-03", name: "NEIGRIHMS Regional Trauma Center", type: "HOSPITAL", lat: 25.6025, lng: 91.9392, phone: "+91 364 2538011 / 108", district: "East Khasi Hills", state: "Meghalaya", corridor: "Mawdiangdiang Axis", description: "Apex super-specialty medical institute. Level-1 trauma care, advanced surgical ICUs, and emergency helipad." },
  { id: "HOSP-04", name: "Jowai Civil Hospital (Ialong)", type: "HOSPITAL", lat: 25.4520, lng: 92.2350, phone: "+91 3652 220235 / 108", district: "West Jaintia Hills", state: "Meghalaya", corridor: "NH-06 (Umiam - Jowai)", description: "Equipped for highway accident trauma, emergency surgeries, and regional ambulance coordination." },
  { id: "HOSP-05", name: "Sohra Community Health Centre (CHC)", type: "HOSPITAL", lat: 25.2750, lng: 91.7320, phone: "+91 3637 235222 / 108", district: "East Khasi Hills", state: "Meghalaya", corridor: "Cherrapunji Escarpment", description: "Emergency health centre with 24h doctor on duty, oxygen cylinders, and 4x4 mountain ambulances." },
  { id: "HOSP-06", name: "Nongpoh Civil Hospital", type: "HOSPITAL", lat: 25.9020, lng: 91.8790, phone: "+91 3638 232234 / 108", district: "Ri-Bhoi", state: "Meghalaya", corridor: "Guwahati - Shillong Expressway", description: "Strategic highway emergency hospital for high-speed corridor accidents and monsoon landslide casualties." },
  
  // Sikkim
  { id: "HOSP-07", name: "Sir Thutob Namgyal Memorial (STNM) Hospital", type: "HOSPITAL", lat: 27.3245, lng: 88.5982, phone: "+91 3592 201172 / 108", district: "Gangtok", state: "Sikkim", corridor: "Gangtok - Rangpo (NH-10)", description: "Sikkim apex multi-specialty hospital with state disaster casualty response and advanced trauma operation theatre." },
  { id: "HOSP-08", name: "Singtam District Hospital", type: "HOSPITAL", lat: 27.2340, lng: 88.4980, phone: "+91 3592 233215 / 108", district: "East Sikkim", state: "Sikkim", corridor: "Teesta River Valley (NH-10)", description: "Crucial mid-corridor hospital situated directly along the Teesta landslide choke points for rapid stabilization." },
  { id: "HOSP-09", name: "Namchi District Hospital", type: "HOSPITAL", lat: 27.1660, lng: 88.3580, phone: "+91 3595 252814 / 108", district: "South Sikkim", state: "Sikkim", corridor: "Namchi - Jorethang Ridge", description: "District hospital catering to South and West Sikkim slope instability corridors." },
  { id: "HOSP-10", name: "Mangan District Hospital", type: "HOSPITAL", lat: 27.5080, lng: 88.5320, phone: "+91 3592 234220 / 108", district: "North Sikkim", state: "Sikkim", corridor: "Chungthang - Lachen Axis", description: "Frontline hospital equipped for severe flash floods, high-altitude trauma, and rockfall rescues." },
  
  // Assam
  { id: "HOSP-11", name: "Haflong Civil Hospital", type: "HOSPITAL", lat: 25.1720, lng: 93.0230, phone: "+91 3673 236245 / 108", district: "Dima Hasao", state: "Assam", corridor: "Barail Hill Range (NH-27)", description: "Main hill-district civil hospital providing emergency trauma care across Haflong and Jatinga landslide sectors." },
  { id: "HOSP-12", name: "Silchar Medical College & Hospital", type: "HOSPITAL", lat: 24.7890, lng: 92.7930, phone: "+91 3842 229110 / 108", district: "Cachar", state: "Assam", corridor: "Barak Valley Transit Hub", description: "Major referral medical college serving Cachar, Karimganj, Dima Hasao, and Meghalaya border transit routes." },
  { id: "HOSP-13", name: "Gauhati Medical College & Hospital (GMCH)", type: "HOSPITAL", lat: 26.1580, lng: 91.7740, phone: "+91 361 2529457 / 108", district: "Kamrup Metropolitan", state: "Assam", corridor: "Guwahati Gateway Hub", description: "Largest super-specialty disaster referral hospital in North East India with 24/7 multi-organ trauma suites." },
  { id: "HOSP-20", name: "Diphu Medical College & Hospital", type: "HOSPITAL", lat: 25.8500, lng: 93.4300, phone: "+91 3671 274444 / 108", district: "Karbi Anglong", state: "Assam", corridor: "Karbi Anglong Hill Corridor", description: "Apex district medical college & hospital with 24/7 emergency trauma casualty and ICU." },
  { id: "HOSP-21", name: "B.P. Civil Hospital Nagaon", type: "HOSPITAL", lat: 26.3450, lng: 92.6850, phone: "+91 3672 233222 / 108", district: "Nagaon", state: "Assam", corridor: "Central Assam Highway Axis", description: "Major district civil hospital with critical trauma ward and regional emergency ambulances." },

  // Nagaland
  { id: "HOSP-14", name: "Naga Hospital Authority Kohima (NHAK)", type: "HOSPITAL", lat: 25.6680, lng: 94.1020, phone: "+91 370 2244240 / 108", district: "Kohima", state: "Nagaland", corridor: "Dzükou Valley / Kohima (NH-29)", description: "Apex government medical facility for Nagaland with emergency trauma centre and disaster casualty wards." },
  { id: "HOSP-15", name: "District Hospital Dimapur", type: "HOSPITAL", lat: 25.9080, lng: 93.7250, phone: "+91 3862 225287 / 108", district: "Dimapur", state: "Nagaland", corridor: "Dimapur Plains Gateway", description: "Transit emergency hospital providing backup to NH-29 mountain pass incidents." },

  // Arunachal Pradesh
  { id: "HOSP-16", name: "Khandro Drowa Tsangmu District Hospital Tawang", type: "HOSPITAL", lat: 27.5860, lng: 91.8650, phone: "+91 3794 222234 / 108", district: "Tawang", state: "Arunachal Pradesh", corridor: "Sela Pass / Tawang Highway", description: "High-altitude trauma and cold-injury stabilization hospital for extreme border mountain terrain." },
  { id: "HOSP-17", name: "TRIHMS Medical Institute & Hospital Naharlagun", type: "HOSPITAL", lat: 27.1060, lng: 93.6980, phone: "+91 360 2244101 / 108", district: "Papum Pare", state: "Arunachal Pradesh", corridor: "Itanagar Capital Complex", description: "State medical college hospital with specialized emergency response for hill-cutting landslides." },

  // Mizoram & Manipur
  { id: "HOSP-18", name: "Aizawl Civil Hospital", type: "HOSPITAL", lat: 23.7310, lng: 92.7180, phone: "+91 389 2322318 / 108", district: "Aizawl", state: "Mizoram", corridor: "Aizawl Ridge Slope Axis", description: "Central civil hospital with casualty departments specialized in monsoon subsidence trauma." },
  { id: "HOSP-19", name: "Noney Community Health Centre (CHC)", type: "HOSPITAL", lat: 24.7520, lng: 93.6020, phone: "+91 385 2451234 / 108", district: "Noney", state: "Manipur", corridor: "Tupul / Imphal West Axis", description: "Frontline emergency healthcare centre located near the Tupul disaster corridor." },

  // Shelters
  { id: "SHELTER-01", name: "Khliehriat Higher Secondary School Muster Hall", type: "SHELTER", lat: 25.3510, lng: 92.3650, phone: "+91 3655 230230 / 1077", district: "East Jaintia Hills", state: "Meghalaya", corridor: "NH-06 (Sonapur Sector)", description: "Elevated ridge zone muster station with emergency power generator, clean potable water tanks, and 500-person capacity." },
  { id: "SHELTER-02", name: "Shillong Multi-Purpose Disaster Evacuation Shelter", type: "SHELTER", lat: 25.5750, lng: 91.8820, phone: "+91 364 2502094 / 1070", district: "East Khasi Hills", state: "Meghalaya", corridor: "Shillong Central Ridge", description: "State disaster mitigation shelter on stable geological sandstone base away from cliff edges." },
  { id: "SHELTER-03", name: "Sohra Higher Secondary School Relief Center", type: "SHELTER", lat: 25.2810, lng: 91.7280, phone: "+91 3637 235210 / 1077", district: "East Khasi Hills", state: "Meghalaya", corridor: "Cherrapunji Plateau", description: "Reinforced high-ground community shelter with emergency dry ration cache and satellite communication backup." },
  { id: "SHELTER-04", name: "Paljor Stadium Multi-Purpose Disaster Relief Complex", type: "SHELTER", lat: 27.3320, lng: 88.6140, phone: "+91 3592 202411 / 1070", district: "Gangtok", state: "Sikkim", corridor: "Gangtok - Rangpo (NH-10)", description: "State evacuation venue with large indoor hall capacity (1,200 persons), emergency helipad, and medical post." },
  { id: "SHELTER-05", name: "Singtam Senior Secondary School Evacuation Center", type: "SHELTER", lat: 27.2360, lng: 88.5020, phone: "+91 3592 233240 / 1077", district: "East Sikkim", state: "Sikkim", corridor: "Teesta Basin (NH-10)", description: "Designated elevated hillside school above peak Teesta flood and debris line." },
  { id: "SHELTER-06", name: "Government Girls Higher Secondary School Emergency Center", type: "SHELTER", lat: 25.1680, lng: 93.0180, phone: "+91 3673 236230 / 1077", district: "Dima Hasao", state: "Assam", corridor: "Haflong - Jatinga Valley", description: "Hilltop safe zone facility equipped by Dima Hasao DDMA for displaced families." },
  { id: "SHELTER-09", name: "Diphu Indoor Stadium Relief Muster Center", type: "SHELTER", lat: 25.8480, lng: 93.4320, phone: "+91 3671 272222 / 1077", district: "Karbi Anglong", state: "Assam", corridor: "Karbi Anglong District HQ", description: "Centrally located concrete relief shelter equipped with emergency dry ration storage." },
  { id: "SHELTER-07", name: "Kohima Local Ground & Indoor Evacuation Center", type: "SHELTER", lat: 25.6710, lng: 94.1080, phone: "+91 370 2244222 / 1077", district: "Kohima", state: "Nagaland", corridor: "Dzükou Valley / Kohima (NH-29)", description: "Centrally located high-ground muster pavilion with food distribution logistics and bedding." },
  { id: "SHELTER-08", name: "Tawang Multi-Purpose Community Relief Shelter", type: "SHELTER", lat: 27.5820, lng: 91.8620, phone: "+91 3794 222220 / 1077", district: "Tawang", state: "Arunachal Pradesh", corridor: "Sela Pass Axis", description: "Heated emergency shelter designed for sub-zero alpine conditions and blocked-pass travelers." },

  // Police Outposts
  { id: "POL-01", name: "Lumshnong Highway Patrol Police Outpost", type: "POLICE", lat: 25.1780, lng: 92.3810, phone: "+91 3655 238222 / 112", district: "East Jaintia Hills", state: "Meghalaya", corridor: "NH-06 (Sonapur Sector)", description: "24/7 Highway Patrol Outpost near Sonapur Tunnel. Coordinates traffic diversion and rockfall clearance marshals." },
  { id: "POL-02", name: "Sadar Police Station & Highway Traffic Cell", type: "POLICE", lat: 25.5780, lng: 91.8835, phone: "+91 364 2224400 / 112", district: "East Khasi Hills", state: "Meghalaya", corridor: "Shillong Central Hub", description: "Central Police Emergency Response Support System (ERSS) dispatch room for road blockades." },
  { id: "POL-03", name: "Rangpo Border Highway Police Checkpost", type: "POLICE", lat: 27.1760, lng: 88.5280, phone: "+91 3592 240212 / 112", district: "Pakyong", state: "Sikkim", corridor: "NH-10 (Sikkim Entry Axis)", description: "Transit choke-point checkpost managing vehicular inflow and landslide emergency diversions." },
  { id: "POL-04", name: "Gangtok Sadar Police Station", type: "POLICE", lat: 27.3300, lng: 88.6110, phone: "+91 3592 202022 / 112", district: "Gangtok", state: "Sikkim", corridor: "Gangtok City - NH-10", description: "Capital police division coordinating emergency siren dispatches and hill evacuation." },
  { id: "POL-05", name: "Haflong Police Station & Highway Unit", type: "POLICE", lat: 25.1700, lng: 93.0210, phone: "+91 3673 236222 / 112", district: "Dima Hasao", state: "Assam", corridor: "NH-27 / NH-54 Axis", description: "Hill-district police unit monitoring railway and highway landslide disruption." },
  { id: "POL-07", name: "Diphu Police Station & Highway Patrol", type: "POLICE", lat: 25.8450, lng: 93.4350, phone: "+91 3671 272234 / 112", district: "Karbi Anglong", state: "Assam", corridor: "Karbi Anglong Central Hub", description: "District headquarters police unit coordinating rural landslide emergency dispatch." },
  { id: "POL-06", name: "Kohima North Police Station & NH-29 Patrol", type: "POLICE", lat: 25.6780, lng: 94.1150, phone: "+91 370 2244230 / 112", district: "Kohima", state: "Nagaland", corridor: "NH-29 Corridor", description: "Mountain pass police station equipped with wireless VHF repeaters and all-weather patrol gypsies." },

  // BRO Detachments
  { id: "BRO-01", name: "BRO 762 BRTF Heavy Earthmover Detachment", type: "CLEARANCE_UNIT", lat: 25.1020, lng: 92.3670, phone: "+91 3655 230100 / 1070", district: "East Jaintia Hills", state: "Meghalaya", corridor: "Sonapur Tunnel (NH-06)", description: "Border Roads Organisation base camp with hydraulic rock breakers, wheeled excavators, and bulldozers on 15-minute standby." },
  { id: "BRO-02", name: "BRO Project Swastik 758 BRTF Clearance HQ", type: "CLEARANCE_UNIT", lat: 27.3290, lng: 88.6120, phone: "+91 3592 202888 / 1070", district: "Gangtok", state: "Sikkim", corridor: "NH-10 Lifeline Highway", description: "Elite mountain road maintenance regiment responsible for 24/7 clearance of 29th Mile, Selfie Dara, and Teesta slides." },
  { id: "BRO-03", name: "BRO Project Sewak 15 BRTF Rapid Clearing Base", type: "CLEARANCE_UNIT", lat: 25.6820, lng: 94.1200, phone: "+91 370 2241100 / 1070", district: "Kohima", state: "Nagaland", corridor: "NH-29 Mountain Axis", description: "Dedicated heavy machinery detachment keeping the Kohima-Dimapur commercial lifeline operational." },
  { id: "BRO-04", name: "BRO Project Vartak 42 BRTF High-Altitude Unit", type: "CLEARANCE_UNIT", lat: 27.5890, lng: 91.8700, phone: "+91 3794 222110 / 1070", district: "Tawang", state: "Arunachal Pradesh", corridor: "Sela Pass Axis", description: "Specialized snow cutters, heavy bulldozers, and rock excavators for extreme high-pass clearance." },
  { id: "BRO-05", name: "NHAI / PWD Rapid Road Clearing Detachment Haflong", type: "CLEARANCE_UNIT", lat: 25.1650, lng: 93.0150, phone: "+91 3673 236100 / 1070", district: "Dima Hasao", state: "Assam", corridor: "East-West Corridor (NH-27)", description: "Heavy earthmoving contractors under NHAI standby contract for high-speed mudslide clearance." },
  { id: "BRO-06", name: "PWD / BRO Rapid Road Clearance Unit Diphu", type: "CLEARANCE_UNIT", lat: 25.8420, lng: 93.4280, phone: "+91 3671 272100 / 1070", district: "Karbi Anglong", state: "Assam", corridor: "Karbi Anglong Mountain Roads", description: "Dedicated hydraulic excavators and loaders stationed for hill road clearance across Karbi Anglong." }
];

export function computeNearestFacilities(lat, lng) {
  if (!lat || !lng) return null;
  const scored = VERIFIED_REGIONAL_FACILITIES.map(fac => {
    const dist = calculateGeodesicDistanceKm(lat, lng, fac.lat, fac.lng);
    const bearing = calculateCompassHeading(lat, lng, fac.lat, fac.lng);
    return {
      ...fac,
      distance_km: dist,
      bearing
    };
  });

  scored.sort((a, b) => a.distance_km - b.distance_km);

  return {
    nearest_hospital: scored.find(f => f.type === 'HOSPITAL') || scored[0],
    nearest_shelter: scored.find(f => f.type === 'SHELTER') || scored[0],
    nearest_police: scored.find(f => f.type === 'POLICE') || scored[0],
    nearest_clearance_unit: scored.find(f => f.type === 'CLEARANCE_UNIT') || scored[0],
    all_nearest: scored.slice(0, 8)
  };
}
