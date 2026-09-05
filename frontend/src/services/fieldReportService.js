import { apiFetch, getApiBaseUrl } from './apiConfig';
import { getAuthToken } from './authService';

export async function createFieldReport(reportData) {
  try {
    const response = await apiFetch('/v1/field-reports', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(reportData),
    });

    if (!response.ok) {
      try {
        const errorData = await response.json();
        return {
          ok: false,
          status: response.status,
          error: errorData.detail || errorData.message || 'Failed to create field report.',
          data: errorData
        };
      } catch {
        return {
          ok: false,
          status: response.status,
          error: `HTTP error ${response.status}: Failed to create field report.`
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
      error: 'Unable to connect to the monitoring server.'
    };
  }
}

export async function uploadFieldReportMedia(reportId, file) {
  try {
    const formData = new FormData();
    formData.append('file', file);

    const response = await apiFetch(`/v1/field-reports/${reportId}/media`, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      try {
        const errorData = await response.json();
        return {
          ok: false,
          status: response.status,
          error: errorData.detail || errorData.message || 'Failed to upload media evidence.',
          data: errorData
        };
      } catch {
        return {
          ok: false,
          status: response.status,
          error: `HTTP error ${response.status}: Failed to upload media.`
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
      error: 'Network error during media evidence upload.'
    };
  }
}

export async function getNearbyFieldReports(latitude, longitude, radiusKm = 5.0, status = null, reportType = null) {
  try {
    let url = `/v1/field-reports/nearby?latitude=${latitude}&longitude=${longitude}&radius_km=${radiusKm}`;
    if (status) url += `&status=${encodeURIComponent(status)}`;
    if (reportType) url += `&report_type=${encodeURIComponent(reportType)}`;

    const response = await apiFetch(url, {
      method: 'GET',
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      return {
        ok: false,
        status: response.status,
        error: errorData.detail || 'Failed to retrieve nearby reports.',
        data: []
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
      error: 'Unable to connect to monitoring server.',
      data: []
    };
  }
}

export async function getFieldIntelligenceSummary(latitude, longitude, radiusKm = 5.0) {
  try {
    const response = await apiFetch('/v1/field-reports/intelligence-summary', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        latitude,
        longitude,
        radius_km: radiusKm
      }),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      return {
        ok: false,
        status: response.status,
        error: errorData.detail || 'Failed to retrieve intelligence summary.',
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
      error: 'Unable to connect to monitoring server.',
      data: null
    };
  }
}

export async function getFieldReportById(reportId) {
  try {
    const response = await apiFetch(`/v1/field-reports/${reportId}`, {
      method: 'GET',
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      return {
        ok: false,
        status: response.status,
        error: errorData.detail || 'Report not found.',
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
      error: 'Unable to connect to monitoring server.',
      data: null
    };
  }
}

export async function getReviewQueue({ status = null, severity = null, reportType = null, skip = 0, limit = 50 } = {}) {
  try {
    const params = new URLSearchParams();
    if (status && status !== 'ALL') params.append('status', status);
    if (severity && severity !== 'ALL') params.append('severity', severity);
    if (reportType && reportType !== 'ALL') params.append('report_type', reportType);
    if (skip) params.append('skip', skip.toString());
    if (limit) params.append('limit', limit.toString());

    const response = await apiFetch(`/v1/field-reports/review-queue?${params.toString()}`, {
      method: 'GET',
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      return {
        ok: false,
        status: response.status,
        error: errorData.detail || 'Failed to retrieve operational review queue.',
        data: { total: 0, items: [] }
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
      error: 'Unable to connect to monitoring server.',
      data: { total: 0, items: [] }
    };
  }
}

export async function updateReportStatus(reportId, newStatus) {
  try {
    const response = await apiFetch(`/v1/field-reports/${reportId}/status`, {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ status: newStatus }),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      return {
        ok: false,
        status: response.status,
        error: errorData.detail || 'Failed to update report status.',
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
      error: 'Unable to connect to monitoring server.',
      data: null
    };
  }
}

/**
 * Uploads Jio Tag image and confidential Aadhaar verification documents.
 */
export async function uploadVerificationDocuments(reportId, { jioTagFile = null, aadhaarCardFile = null, aadhaarQrFile = null } = {}) {
  try {
    const formData = new FormData();
    if (jioTagFile) formData.append('jio_tag_image', jioTagFile);
    if (aadhaarCardFile) formData.append('aadhaar_card', aadhaarCardFile);
    if (aadhaarQrFile) formData.append('aadhaar_qr', aadhaarQrFile);

    const response = await apiFetch(`/v1/field-reports/${reportId}/verification-documents`, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      return {
        ok: false,
        status: response.status,
        error: errorData.detail || 'Failed to upload verification documents.',
        data: errorData
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
      error: 'Network error during verification documents upload.'
    };
  }
}

/**
 * Submits Disaster Authority Admin verification decision (VERIFIED | REJECTED | RE_UPLOAD_REQUIRED).
 */
export async function updateAdminVerification(reportId, verificationStatus, verificationNote = '') {
  try {
    const token = getAuthToken();
    const headers = {
      'Content-Type': 'application/json',
    };
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    const response = await apiFetch(`/v1/field-reports/${reportId}/admin-verification`, {
      method: 'PATCH',
      headers,
      body: JSON.stringify({
        verification_status: verificationStatus,
        verification_note: verificationNote,
      }),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      return {
        ok: false,
        status: response.status,
        error: errorData.detail || 'Failed to update verification decision.',
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
      error: 'Unable to connect to monitoring server.',
      data: null
    };
  }
}

/**
 * Constructs an authenticated URL for viewing confidential Aadhaar documents (Card or QR) in the admin workspace.
 */
export function getAadhaarDocumentUrl(reportId, docType) {
  const token = getAuthToken();
  const baseUrl = getApiBaseUrl();
  const tokenQuery = token ? `?token=${encodeURIComponent(token)}` : '';
  return `${baseUrl}/v1/field-reports/${reportId}/aadhaar-document/${docType}${tokenQuery}`;
}
