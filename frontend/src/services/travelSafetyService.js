/**
 * Travel Safety Service - SIH 2026 NER Landslide Monitoring
 * Handles real-time GPS tracking, approach-angle mathematics,
 * alert deduplication state machines, and early warning dispatch.
 */

import { apiFetch } from './apiConfig.js';
import { playTravelSafetyVoiceAlert } from './emergencyAudioService.js';

// Default Curated Fallback Corridors if API is offline
export const FALLBACK_TRAVEL_CORRIDORS = [
  {
    id: 'corridor-nh06-sonapur',
    name: 'Sonapur Tunnel Corridor (NH-06)',
    highway: 'NH-06',
    state: 'Meghalaya',
    latitude: 25.1012,
    longitude: 92.3654,
    risk_probability: 84.0,
    severity: 'CRITICAL',
    source: 'CompositeRiskEngine (Monitored Corridor)',
    advisory: 'Frequent active mudflows and debris fall at Sonapur tunnel portal. Exercise extreme caution during rain.'
  },
  {
    id: 'corridor-nh13-sela',
    name: 'Sela Pass / Tawang Highway (NH-13)',
    highway: 'NH-13',
    state: 'Arunachal Pradesh',
    latitude: 27.5034,
    longitude: 92.1037,
    risk_probability: 88.0,
    severity: 'CRITICAL',
    source: 'CompositeRiskEngine (Monitored Corridor)',
    advisory: 'Steep rocky slopes prone to rockfall and freeze-thaw slippage near high-altitude passes.'
  },
  {
    id: 'corridor-nh10-gangtok',
    name: 'Gangtok - Siliguri Corridor (NH-10)',
    highway: 'NH-10',
    state: 'Sikkim',
    latitude: 27.3389,
    longitude: 88.6065,
    risk_probability: 82.0,
    severity: 'CRITICAL',
    source: 'CompositeRiskEngine (Monitored Corridor)',
    advisory: 'Teesta River gorge section susceptible to severe washouts and hillside subsidence.'
  },
  {
    id: 'corridor-nh37-tupul',
    name: 'Tupul / Imphal West Corridor (NH-37)',
    highway: 'NH-37',
    state: 'Manipur',
    latitude: 24.7865,
    longitude: 93.6322,
    risk_probability: 86.0,
    severity: 'CRITICAL',
    source: 'CompositeRiskEngine (Monitored Corridor)',
    advisory: 'Major historical railway/highway slide zone. Saturated slope conditions require alternate route planning.'
  },
  {
    id: 'corridor-nh29-dzukou',
    name: 'Dzükou Valley / Kohima Ridge (NH-29)',
    highway: 'NH-29',
    state: 'Nagaland',
    latitude: 25.6751,
    longitude: 94.1086,
    risk_probability: 76.0,
    severity: 'HIGH',
    source: 'CompositeRiskEngine (Monitored Corridor)',
    advisory: 'High cut-slope vulnerability along Kohima-Dimapur highway segment.'
  },
  {
    id: 'corridor-nh54a-haflong',
    name: 'Dima Hasao (Haflong) Corridor (NH-54A)',
    highway: 'NH-54A',
    state: 'Assam',
    latitude: 25.1667,
    longitude: 93.0167,
    risk_probability: 74.0,
    severity: 'HIGH',
    source: 'CompositeRiskEngine (Monitored Corridor)',
    advisory: 'Barail range hill pass prone to recurrent monsoon mudslides and embankment erosion.'
  },
  {
    id: 'corridor-nh54-aizawl',
    name: 'Aizawl Slope Corridor (NH-54)',
    highway: 'NH-54',
    state: 'Mizoram',
    latitude: 23.7271,
    longitude: 92.7176,
    risk_probability: 72.0,
    severity: 'HIGH',
    source: 'CompositeRiskEngine (Monitored Corridor)',
    advisory: 'Steep shale formations subject to localized structural instability under continuous precipitation.'
  },
  {
    id: 'corridor-nh10-kalimpong',
    name: 'Kalimpong / 29th Mile Teesta (NH-10)',
    highway: 'NH-10',
    state: 'Sikkim / West Bengal Border',
    latitude: 27.0667,
    longitude: 88.4667,
    risk_probability: 79.0,
    severity: 'HIGH',
    source: 'CompositeRiskEngine (Monitored Corridor)',
    advisory: 'Persistent slope failure zone at 29th Mile. River undercutting active.'
  }
];

/**
 * Calculates geodesic distance between two points using the Haversine formula (km).
 */
export function calculateDistanceKm(lat1, lon1, lat2, lon2) {
  if (lat1 == null || lon1 == null || lat2 == null || lon2 == null) return Infinity;
  const R = 6371.0; // Earth mean radius in km
  const dLat = (lat2 - lat1) * (Math.PI / 180);
  const dLon = (lon2 - lon1) * (Math.PI / 180);
  const a =
    Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos(lat1 * (Math.PI / 180)) * Math.cos(lat2 * (Math.PI / 180)) *
    Math.sin(dLon / 2) * Math.sin(dLon / 2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  return R * c;
}

/**
 * Computes forward compass bearing (0-360 degrees) from point 1 to point 2.
 */
export function calculateBearing(lat1, lon1, lat2, lon2) {
  const phi1 = lat1 * (Math.PI / 180);
  const phi2 = lat2 * (Math.PI / 180);
  const deltaLambda = (lon2 - lon1) * (Math.PI / 180);

  const y = Math.sin(deltaLambda) * Math.cos(phi2);
  const x = Math.cos(phi1) * Math.sin(phi2) - Math.sin(phi1) * Math.cos(phi2) * Math.cos(deltaLambda);
  const theta = Math.atan2(y, x);
  return (theta * (180 / Math.PI) + 360) % 360;
}

/**
 * Determines whether a traveler is actively approaching a hazard.
 * Checks distance reduction delta and bearing convergence.
 */
export function isApproachingHazard({ prevLoc, currLoc, hazardLoc, maxAngleDeg = 65 }) {
  if (!currLoc || !hazardLoc) return false;

  const currentDist = calculateDistanceKm(currLoc.lat, currLoc.lng, hazardLoc.lat, hazardLoc.lng);

  // If previous location is recorded, compare distance delta
  if (prevLoc && (prevLoc.lat !== currLoc.lat || prevLoc.lng !== currLoc.lng)) {
    const prevDist = calculateDistanceKm(prevLoc.lat, prevLoc.lng, hazardLoc.lat, hazardLoc.lng);
    const distanceDelta = currentDist - prevDist;

    // Moving closer by more than 30 meters
    if (distanceDelta < -0.03) {
      return true;
    }

    // Also check compass travel vector vs hazard bearing
    const travelBearing = calculateBearing(prevLoc.lat, prevLoc.lng, currLoc.lat, currLoc.lng);
    const hazardBearing = calculateBearing(currLoc.lat, currLoc.lng, hazardLoc.lat, hazardLoc.lng);
    const angleDiff = Math.abs((travelBearing - hazardBearing + 180) % 360 - 180);

    if (angleDiff <= maxAngleDeg) {
      return true;
    }
  }

  // Safe fallback: If user is within the 10 km corridor and moving/stationary
  return currentDist <= 10.0;
}

/**
 * Fetches monitored landslide hazard corridors from backend API,
 * with graceful offline fallback to curated high-risk corridors.
 */
export async function fetchTravelRiskZones(minRisk = 0.0) {
  try {
    const res = await apiFetch(`/v1/travel/risk-zones?min_risk=${minRisk}`);
    if (res && res.zones && Array.isArray(res.zones)) {
      return res.zones;
    }
  } catch (err) {
    console.warn('[TravelSafety] Backend travel API unavailable, using cached corridors:', err);
  }
  return FALLBACK_TRAVEL_CORRIDORS.filter(z => z.risk_probability >= minRisk);
}

// Stateful Deduplication Map: zoneId -> { state: 'IDLE' | 'WARNED_10KM' | 'WARNED_5KM', lastAlertTime: number }
const zoneAlertStates = new Map();

/**
 * Resets all alert deduplication states (e.g., when turning Travel Mode OFF).
 */
export function resetTravelAlertStates() {
  zoneAlertStates.clear();
}

/**
 * Core Evaluation Engine: Analyzes traveler position against hazard zones.
 * Triggers voice & visual alert on state transitions (10 km -> 5 km),
 * suppresses duplicates, and resets when leaving (> 12 km).
 */
export function evaluateTravelSafety({
  prevLoc,
  currLoc,
  zones = [],
  voiceAlertsEnabled = true,
  onAlertTriggered = null
}) {
  if (!currLoc || !currLoc.lat || !currLoc.lng) {
    return { activeAlert: null, evaluatedZones: [] };
  }

  let highestPriorityAlert = null;
  const evaluatedZones = [];

  for (const zone of zones) {
    const distanceKm = calculateDistanceKm(currLoc.lat, currLoc.lng, zone.latitude, zone.longitude);
    const isHighRisk = (zone.risk_probability || 0) >= 70.0;
    const isApproaching = isApproachingHazard({ prevLoc, currLoc, hazardLoc: { lat: zone.latitude, lng: zone.longitude } });

    evaluatedZones.push({
      ...zone,
      distanceKm: Math.round(distanceKm * 10) / 10,
      isApproaching,
      isHighRisk
    });

    // Alert candidate: Risk >= 70%, distance <= 10 km, approaching
    if (isHighRisk && distanceKm <= 10.0 && isApproaching) {
      if (!highestPriorityAlert || distanceKm < highestPriorityAlert.distanceKm) {
        highestPriorityAlert = {
          zone,
          distanceKm: Math.round(distanceKm * 10) / 10,
          isUrgent: distanceKm <= 5.0,
          riskScore: zone.risk_probability
        };
      }
    }

    // State-based deduplication & hysteresis
    let stateObj = zoneAlertStates.get(zone.id) || { state: 'IDLE', lastAlertTime: 0 };

    if (isHighRisk && isApproaching) {
      if (distanceKm <= 5.0 && stateObj.state !== 'WARNED_5KM') {
        // Critical 5 km boundary crossed -> issue intensified warning
        stateObj = { state: 'WARNED_5KM', lastAlertTime: Date.now() };
        zoneAlertStates.set(zone.id, stateObj);

        if (voiceAlertsEnabled) {
          playTravelSafetyVoiceAlert({
            riskScore: zone.risk_probability,
            distanceKm,
            regionName: zone.name,
            isUrgent: true
          });
        }
        if (onAlertTriggered) {
          onAlertTriggered({ zone, distanceKm, isUrgent: true, voiceDispatched: Boolean(voiceAlertsEnabled) });
        }
      } else if (distanceKm <= 10.0 && stateObj.state === 'IDLE') {
        // 10 km perimeter entered -> issue initial warning ONCE
        stateObj = { state: 'WARNED_10KM', lastAlertTime: Date.now() };
        zoneAlertStates.set(zone.id, stateObj);

        if (voiceAlertsEnabled) {
          playTravelSafetyVoiceAlert({
            riskScore: zone.risk_probability,
            distanceKm,
            regionName: zone.name,
            isUrgent: false
          });
        }
        if (onAlertTriggered) {
          onAlertTriggered({ zone, distanceKm, isUrgent: false, voiceDispatched: Boolean(voiceAlertsEnabled) });
        }
      }
    } else if (distanceKm > 12.0) {
      // User moved away beyond 12 km -> Reset state so re-entry warns again
      if (stateObj.state !== 'IDLE') {
        zoneAlertStates.set(zone.id, { state: 'IDLE', lastAlertTime: 0 });
      }
    }
  }

  // Sort evaluated zones by proximity
  evaluatedZones.sort((a, b) => a.distanceKm - b.distanceKm);

  return {
    activeAlert: highestPriorityAlert,
    evaluatedZones
  };
}

/**
 * Browser Geolocation Watcher Manager.
 * Safely requests GPS permissions, tracks live coordinates, and handles errors gracefully.
 */
export function startGeolocationWatch({ onLocationUpdate, onError }) {
  if (typeof window === 'undefined' || !navigator.geolocation) {
    if (onError) onError({ code: 'UNSUPPORTED', message: 'Geolocation is not supported by this browser.' });
    return () => {};
  }

  const options = {
    enableHighAccuracy: true,
    timeout: 15000,
    maximumAge: 5000
  };

  const watchId = navigator.geolocation.watchPosition(
    (position) => {
      if (onLocationUpdate && position.coords) {
        onLocationUpdate({
          lat: position.coords.latitude,
          lng: position.coords.longitude,
          accuracy: position.coords.accuracy,
          heading: position.coords.heading,
          speed: position.coords.speed,
          timestamp: position.timestamp
        });
      }
    },
    (err) => {
      let friendlyMessage = 'Unable to determine GPS location.';
      if (err.code === 1) { // PERMISSION_DENIED
        friendlyMessage = 'Location permission denied. Please allow location access in your browser settings to enable travel monitoring.';
      } else if (err.code === 2) { // POSITION_UNAVAILABLE
        friendlyMessage = 'GPS signal unavailable. Please ensure location services are enabled on your device.';
      } else if (err.code === 3) { // TIMEOUT
        friendlyMessage = 'GPS location request timed out. Retrying...';
      }
      if (onError) onError({ code: err.code, message: friendlyMessage });
    },
    options
  );

  return () => {
    try {
      navigator.geolocation.clearWatch(watchId);
    } catch {}
  };
}
