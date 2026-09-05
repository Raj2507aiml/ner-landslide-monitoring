import { apiFetch } from './apiConfig.js';

/**
 * Dispatches an automated emergency SMS via Twilio Cloud Gateway.
 */
export async function sendTwilioSmsAlert({
  warningLevel = 'ALERT',
  locationName = 'NER Monitored Sector',
  message = '',
  recipients = null
}) {
  try {
    const response = await apiFetch('/v1/notifications/send-sms', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        warning_level: warningLevel,
        location_name: locationName,
        message: message,
        recipients: recipients && recipients.length > 0 ? recipients : null
      })
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      return {
        ok: false,
        status: 'ERROR',
        detail: errorData.detail || 'Failed to dispatch Twilio SMS alert.'
      };
    }

    const data = await response.json();
    return {
      ok: true,
      ...data
    };
  } catch (error) {
    return {
      ok: false,
      status: 'NETWORK_ERROR',
      detail: error.message || 'Unable to connect to notifications gateway service.'
    };
  }
}

/**
 * Fetches recent Twilio dispatch audit history.
 */
export async function getTwilioSmsHistory() {
  try {
    const response = await apiFetch('/v1/notifications/history', {
      method: 'GET'
    });
    if (!response.ok) return { total_logged: 0, dispatches: [] };
    return await response.json();
  } catch {
    return { total_logged: 0, dispatches: [] };
  }
}
