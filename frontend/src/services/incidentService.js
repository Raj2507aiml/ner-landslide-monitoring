import { apiFetch } from './apiConfig';

export async function getIncidents(filters = {}) {
  try {
    const params = new URLSearchParams();
    if (filters.status && filters.status !== 'ALL') {
      params.append('status', filters.status);
    }
    if (filters.severity && filters.severity !== 'ALL') {
      params.append('severity', filters.severity);
    }
    if (filters.limit) {
      params.append('limit', filters.limit);
    }
    if (filters.offset) {
      params.append('offset', filters.offset);
    }

    const queryStr = params.toString() ? `?${params.toString()}` : '';
    const response = await apiFetch(`/v1/incidents${queryStr}`, {
      method: 'GET',
      headers: {
        'Accept': 'application/json'
      }
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      return {
        ok: false,
        status: response.status,
        error: errorData.detail || errorData.message || 'Failed to retrieve incidents.',
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
      error: 'Unable to connect to incident management service.',
      data: null
    };
  }
}

export async function getIncidentById(incidentId) {
  try {
    const response = await apiFetch(`/v1/incidents/${incidentId}`, {
      method: 'GET',
      headers: {
        'Accept': 'application/json'
      }
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      return {
        ok: false,
        status: response.status,
        error: errorData.detail || errorData.message || `Failed to retrieve incident #${incidentId}.`,
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
      error: 'Unable to connect to incident service.',
      data: null
    };
  }
}

export async function evaluateIncident(latitude, longitude, radiusKm = 5.0) {
  try {
    const response = await apiFetch(`/v1/incidents/evaluate?latitude=${latitude}&longitude=${longitude}&radius_km=${radiusKm}`, {
      method: 'POST',
      headers: {
        'Accept': 'application/json'
      }
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      return {
        ok: false,
        status: response.status,
        error: errorData.detail || errorData.message || 'Incident evaluation failed.',
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
      error: 'Unable to connect to incident evaluation service.',
      data: null
    };
  }
}

export async function acknowledgeIncident(incidentId, notes = null) {
  try {
    const response = await apiFetch(`/v1/incidents/${incidentId}/acknowledge`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
      },
      body: JSON.stringify(notes ? { notes } : {})
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      return {
        ok: false,
        status: response.status,
        error: errorData.detail || errorData.message || `Failed to acknowledge incident #${incidentId}.`,
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
      error: 'Unable to connect to incident service.',
      data: null
    };
  }
}

export async function startIncidentResponse(incidentId, notes = null) {
  try {
    const response = await apiFetch(`/v1/incidents/${incidentId}/start-response`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
      },
      body: JSON.stringify(notes ? { notes } : {})
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      return {
        ok: false,
        status: response.status,
        error: errorData.detail || errorData.message || `Failed to start response for incident #${incidentId}.`,
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
      error: 'Unable to connect to incident service.',
      data: null
    };
  }
}

export async function resolveIncident(incidentId, notes = null) {
  try {
    const response = await apiFetch(`/v1/incidents/${incidentId}/resolve`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
      },
      body: JSON.stringify(notes ? { notes } : {})
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      return {
        ok: false,
        status: response.status,
        error: errorData.detail || errorData.message || `Failed to resolve incident #${incidentId}.`,
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
      error: 'Unable to connect to incident service.',
      data: null
    };
  }
}
