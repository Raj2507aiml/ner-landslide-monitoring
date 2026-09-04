import { apiFetch } from './apiConfig';

export async function getNearbyRoads(latitude, longitude, radiusKm = 5.0) {
  try {
    const response = await apiFetch(`/v1/infrastructure/roads/nearby?latitude=${latitude}&longitude=${longitude}&radius_km=${radiusKm}`, {
      method: 'GET',
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      return {
        ok: false,
        status: response.status,
        error: errorData.detail || 'Failed to retrieve road network infrastructure.',
        data: null
      };
    }

    const data = await response.json();
    return {
      ok: true,
      status: response.status,
      data
    };
  } catch (error) {
    return {
      ok: false,
      status: 0,
      error: 'Unable to connect to infrastructure monitoring service.',
      data: null
    };
  }
}

export async function getRoadDisruptionSummary(latitude, longitude, radiusKm = 5.0) {
  try {
    const response = await apiFetch(`/v1/infrastructure/roads/disruption-summary?latitude=${latitude}&longitude=${longitude}&radius_km=${radiusKm}`, {
      method: 'GET',
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      return {
        ok: false,
        status: response.status,
        error: errorData.detail || 'Failed to retrieve road disruption summary.',
        data: null
      };
    }

    const data = await response.json();
    return {
      ok: true,
      status: response.status,
      data
    };
  } catch (error) {
    return {
      ok: false,
      status: 0,
      error: 'Unable to connect to infrastructure monitoring service.',
      data: null
    };
  }
}

/**
 * Calculates great-circle distance between two coordinates in kilometers using Haversine formula.
 */
export function calculateGeodesicDistanceKm(lat1, lon1, lat2, lon2) {
  const R = 6371.0; // Earth radius in km
  const dLat = ((lat2 - lat1) * Math.PI) / 180;
  const dLon = ((lon2 - lon1) * Math.PI) / 180;
  const a =
    Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos((lat1 * Math.PI) / 180) *
      Math.cos((lat2 * Math.PI) / 180) *
      Math.sin(dLon / 2) *
      Math.sin(dLon / 2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  return Math.round(R * c * 10) / 10;
}

/**
 * Fetches dynamically computed nearest hospitals, relief shelters, police, and BRO units
 * based strictly on map coordinates (latitude, longitude).
 */
export async function getEmergencyFacilities(latitude, longitude, radiusKm = 150.0) {
  try {
    const response = await apiFetch(`/v1/infrastructure/emergency-facilities?latitude=${latitude}&longitude=${longitude}&radius_km=${radiusKm}`, {
      method: 'GET',
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      return {
        ok: false,
        status: response.status,
        error: errorData.detail || 'Failed to retrieve emergency facilities.',
        data: null
      };
    }

    const data = await response.json();
    return {
      ok: true,
      status: response.status,
      data
    };
  } catch (error) {
    return {
      ok: false,
      status: 0,
      error: 'Unable to reach emergency facilities service.',
      data: null
    };
  }
}

