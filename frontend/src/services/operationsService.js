import { apiFetch } from './apiConfig';

export async function getSituationAssessment(latitude, longitude, radiusKm = 5.0) {
  try {
    const response = await apiFetch(`/v1/operations/situation-assessment?latitude=${latitude}&longitude=${longitude}&radius_km=${radiusKm}`, {
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
        error: errorData.detail || errorData.message || 'Failed to retrieve operational situation assessment.',
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
      error: 'Unable to connect to operational assessment service.',
      data: null
    };
  }
}
