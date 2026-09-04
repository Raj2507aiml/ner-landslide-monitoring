import { apiFetch } from './apiConfig';

/**
 * Service to handle location-related API communication.
 */
export async function analyzeLocation(latitude, longitude, radiusKm = 5.0) {
  try {
    const response = await apiFetch('/v1/locations/analyze', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        latitude,
        longitude,
        radius_km: radiusKm,
      }),
    });

    if (!response.ok) {
      try {
        const errorData = await response.json();
        return {
          ok: false,
          status: response.status,
          error: errorData.message || errorData.detail || 'Analysis request failed.',
          data: errorData
        };
      } catch {
        return {
          ok: false,
          status: response.status,
          error: `HTTP error ${response.status}: Failed to analyze coordinates.`
        };
      }
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
      error: 'Backend connection failed. Please ensure the API server is online.'
    };
  }
}

export async function searchSatelliteData(latitude, longitude, radiusKm = 5.0, startDate = '', endDate = '', limit = 10) {
  try {
    let url = `/v1/satellite/search?latitude=${latitude}&longitude=${longitude}&radius_km=${radiusKm}&limit=${limit}`;
    if (startDate) url += `&start_date=${startDate}`;
    if (endDate) url += `&end_date=${endDate}`;

    const response = await apiFetch(url, {
      method: 'GET',
    });

    if (!response.ok) {
      try {
        const errorData = await response.json();
        return {
          ok: false,
          status: response.status,
          error: errorData.message || errorData.detail || 'Satellite search request failed.',
          data: errorData
        };
      } catch {
        return {
          ok: false,
          status: response.status,
          error: `HTTP error ${response.status}: Failed to search satellite catalogue.`
        };
      }
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
      error: 'Backend connection failed. Please ensure the API server is online.'
    };
  }
}

export async function getSatelliteSceneDetail(sceneId, collectionId = 'sentinel-1-grd') {
  try {
    const response = await apiFetch(`/v1/satellite/scenes/${sceneId}?collection=${collectionId}`, {
      method: 'GET',
    });

    if (!response.ok) {
      try {
        const errorData = await response.json();
        return {
          ok: false,
          status: response.status,
          error: errorData.message || errorData.detail || 'Scene inspection failed.',
          data: errorData
        };
      } catch {
        return {
          ok: false,
          status: response.status,
          error: `HTTP error ${response.status}: Failed to inspect scene details.`
        };
      }
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
      error: 'Backend connection failed. Please ensure the API server is online.'
    };
  }
}

export async function processSatelliteScene(sceneId, latitude, longitude, radiusKm = 5.0) {
  try {
    const response = await apiFetch(`/v1/satellite/scenes/${sceneId}/process`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        latitude,
        longitude,
        radius_km: radiusKm,
      }),
    });

    if (!response.ok) {
      try {
        const errorData = await response.json();
        return {
          ok: false,
          status: response.status,
          error: errorData.message || errorData.detail || 'Scene processing request failed.',
          data: errorData
        };
      } catch {
        return {
          ok: false,
          status: response.status,
          error: `HTTP error ${response.status}: Failed to process scene.`
        };
      }
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
      error: 'Backend connection failed. Please ensure the API server is online.'
    };
  }
}

export async function getWeatherTelemetry(latitude, longitude) {
  try {
    const response = await apiFetch(`/v1/weather/telemetry?latitude=${latitude}&longitude=${longitude}`, {
      method: 'GET',
    });

    if (!response.ok) {
      try {
        const errorData = await response.json();
        return {
          ok: false,
          status: response.status,
          error: errorData.message || errorData.detail || 'Weather telemetry request failed.',
          data: errorData
        };
      } catch {
        return {
          ok: false,
          status: response.status,
          error: `HTTP error ${response.status}: Failed to retrieve weather telemetry.`
        };
      }
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
      error: 'Backend connection failed. Please ensure the API server is online.'
    };
  }
}

export async function processTerrainData(sceneId, latitude, longitude, radiusKm = 5.0) {
  try {
    const response = await apiFetch(
      `/v1/terrain/process?scene_id=${sceneId}&latitude=${latitude}&longitude=${longitude}&radius_km=${radiusKm}`,
      { method: 'GET' }
    );

    if (!response.ok) {
      try {
        const errorData = await response.json();
        return {
          ok: false,
          status: response.status,
          error: errorData.message || errorData.detail || 'Terrain analysis request failed.',
          data: errorData
        };
      } catch {
        return {
          ok: false,
          status: response.status,
          error: `HTTP error ${response.status}: Failed to retrieve terrain analysis data.`
        };
      }
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
      error: 'Backend connection failed. Please ensure the API server is online.'
    };
  }
}

export async function fetchNearbyHistoricalLandslides(latitude, longitude, radiusKm = 10.0) {
  // Validate coordinates and radius
  if (typeof latitude !== 'number' || isNaN(latitude) || latitude < -90 || latitude > 90) {
    throw new Error('Invalid latitude: must be a number between -90 and 90.');
  }
  if (typeof longitude !== 'number' || isNaN(longitude) || longitude < -180 || longitude > 180) {
    throw new Error('Invalid longitude: must be a number between -180 and 180.');
  }
  if (typeof radiusKm !== 'number' || isNaN(radiusKm) || radiusKm <= 0 || radiusKm > 100) {
    throw new Error('Invalid radius: must be a number between 0 and 100 km.');
  }

  try {
    const response = await apiFetch(
      `/historical/nearby?lat=${latitude}&lon=${longitude}&radius=${radiusKm}`,
      { method: 'GET' }
    );

    if (!response.ok) {
      try {
        const errorData = await response.json();
        return {
          ok: false,
          status: response.status,
          error: errorData.message || errorData.detail || 'Historical landslide query failed.',
          data: errorData
        };
      } catch {
        return {
          ok: false,
          status: response.status,
          error: `HTTP error ${response.status}: Failed to retrieve historical landslide context.`
        };
      }
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
      error: 'Backend connection failed. Please ensure the API server is online.'
    };
  }
}

export async function fetchSusceptibilityScore(
  latitude,
  longitude,
  radiusKm = 10.0,
  slope = null,
  rainfall = null,
  rainfall3d = null,
  rainfall7d = null
) {
  // Validate coordinates and radius
  if (typeof latitude !== 'number' || isNaN(latitude) || latitude < -90 || latitude > 90) {
    throw new Error('Invalid latitude: must be a number between -90 and 90.');
  }
  if (typeof longitude !== 'number' || isNaN(longitude) || longitude < -180 || longitude > 180) {
    throw new Error('Invalid longitude: must be a number between -180 and 180.');
  }
  if (typeof radiusKm !== 'number' || isNaN(radiusKm) || radiusKm <= 0 || radiusKm > 100) {
    throw new Error('Invalid radius: must be a number between 0 and 100 km.');
  }

  try {
    const params = new URLSearchParams({
      lat: latitude.toString(),
      lon: longitude.toString(),
      radius: radiusKm.toString(),
    });

    if (slope !== null && !isNaN(Number(slope))) {
      params.append('slope', slope.toString());
    }

    if (rainfall !== null && !isNaN(Number(rainfall))) {
      params.append('rainfall', rainfall.toString());
    }

    if (rainfall3d !== null && !isNaN(Number(rainfall3d))) {
      params.append('rainfall_3d', rainfall3d.toString());
    }

    if (rainfall7d !== null && !isNaN(Number(rainfall7d))) {
      params.append('rainfall_7d', rainfall7d.toString());
    }

    const response = await apiFetch(
      `/historical/susceptibility?${params.toString()}`,
      { method: 'GET' }
    );

    if (!response.ok) {
      try {
        const errorData = await response.json();
        return {
          ok: false,
          status: response.status,
          error: errorData.message || errorData.detail || 'Susceptibility calculation failed.',
          data: errorData
        };
      } catch {
        return {
          ok: false,
          status: response.status,
          error: `HTTP error ${response.status}: Failed to calculate susceptibility.`
        };
      }
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
      error: 'Backend connection failed. Please ensure the API server is online.'
    };
  }
}

export async function fetchStaticMLSusceptibility(latitude, longitude) {
  try {
    const response = await apiFetch('/v1/ml/static-susceptibility/coordinate', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        latitude,
        longitude
      }),
    });

    if (!response.ok) {
      try {
        const errorData = await response.json();
        return {
          ok: false,
          status: response.status,
          error: errorData.message || errorData.detail || 'ML susceptibility query failed.',
          data: errorData
        };
      } catch {
        return {
          ok: false,
          status: response.status,
          error: `HTTP error ${response.status}: Failed to calculate static ML susceptibility.`
        };
      }
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
      error: 'Backend connection failed. Please ensure the API server is online.'
    };
  }
}

export async function fetchCompositeLandslideRisk(latitude, longitude) {
  try {
    const response = await apiFetch('/v1/risk/composite', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        latitude,
        longitude
      }),
    });

    if (!response.ok) {
      try {
        const errorData = await response.json();
        return {
          ok: false,
          status: response.status,
          error: errorData.message || errorData.detail || 'Composite risk query failed.',
          data: errorData
        };
      } catch {
        return {
          ok: false,
          status: response.status,
          error: `HTTP error ${response.status}: Failed to calculate composite landslide risk.`
        };
      }
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
      error: 'Backend connection failed. Please ensure the API server is online.'
    };
  }
}

export async function fetchAutomaticSatelliteChange(latitude, longitude) {
  try {
    const response = await apiFetch('/v1/satellite/automatic-change-analysis', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        latitude,
        longitude
      }),
    });

    if (!response.ok) {
      try {
        const errorData = await response.json();
        return {
          ok: false,
          status: response.status,
          error: errorData.message || errorData.detail || 'Automatic satellite change query failed.',
          data: errorData
        };
      } catch {
        return {
          ok: false,
          status: response.status,
          error: `HTTP error ${response.status}: Failed to calculate automatic satellite change.`
        };
      }
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
      error: 'Backend connection failed. Please ensure the API server is online.'
    };
  }
}

export async function fetchEarlyWarningAnalysis(latitude, longitude) {
  try {
    const response = await apiFetch('/v1/early-warning/analyze', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        latitude,
        longitude
      }),
    });

    if (!response.ok) {
      try {
        const errorData = await response.json();
        return {
          ok: false,
          status: response.status,
          error: errorData.message || errorData.detail || 'Early warning analysis query failed.',
          data: errorData
        };
      } catch {
        return {
          ok: false,
          status: response.status,
          error: `HTTP error ${response.status}: Failed to calculate early warning status.`
        };
      }
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
      error: 'Backend connection failed. Please ensure the API server is online.'
    };
  }
}




