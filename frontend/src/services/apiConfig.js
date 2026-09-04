/**
 * Central API Configuration & Resilient Fetch Utility
 * Supports localhost, 127.0.0.1, custom LAN IPs, and Vite dev proxies.
 */

export function getApiBaseUrl() {
  if (import.meta.env?.VITE_API_BASE_URL) {
    return import.meta.env.VITE_API_BASE_URL.replace(/\/+$/, '');
  }

  if (typeof window !== 'undefined') {
    const hostname = window.location.hostname || '';
    // On Render deployment: route directly to the live backend API service
    if (hostname.includes('onrender.com')) {
      return 'https://ner-landslide-api-raj2507.onrender.com/api';
    }

    // In production builds behind a reverse proxy, use relative '/api'
    const isStandardPort = window.location.port === '' || window.location.port === '80' || window.location.port === '443';
    if (import.meta.env.PROD || isStandardPort) {
      return '/api';
    }

    return `http://${hostname || '127.0.0.1'}:8000/api`;
  }
  return 'http://127.0.0.1:8000/api';
}

export function getMediaBaseUrl() {
  if (import.meta.env?.VITE_MEDIA_BASE_URL) {
    return import.meta.env.VITE_MEDIA_BASE_URL.replace(/\/+$/, '');
  }

  if (typeof window !== 'undefined') {
    const hostname = window.location.hostname || '';
    if (hostname.includes('onrender.com')) {
      return 'https://ner-landslide-api-raj2507.onrender.com';
    }

    const isStandardPort = window.location.port === '' || window.location.port === '80' || window.location.port === '443';
    if (import.meta.env.PROD || isStandardPort) {
      return '';
    }

    return `http://${hostname || '127.0.0.1'}:8000`;
  }
  return 'http://127.0.0.1:8000';
}

/**
 * Executes a resilient HTTP fetch with fallback between 127.0.0.1, localhost, and Vite dev proxy.
 * Prevents IPv6 ::1 connection refused issues on Windows.
 */
export async function apiFetch(endpoint, options = {}) {
  const cleanEndpoint = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
  
  const primaryBase = getApiBaseUrl();
  const primaryUrl = `${primaryBase}${cleanEndpoint}`;

  try {
    const res = await fetch(primaryUrl, options);
    return res;
  } catch (primaryErr) {
    // Retry once after a brief delay if on Render (handles cold starts & container swaps)
    if (typeof window !== 'undefined' && window.location.hostname.includes('onrender.com')) {
      try {
        await new Promise(r => setTimeout(r, 1200));
        const retryRes = await fetch(primaryUrl, options);
        return retryRes;
      } catch {
        throw primaryErr;
      }
    }

    // Only attempt local host fallbacks when actually developing on localhost
    if (typeof window !== 'undefined' && (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1')) {
      const fallbackHost = (window.location.hostname === '127.0.0.1') ? 'localhost' : '127.0.0.1';
      const fallbackUrl = `http://${fallbackHost}:8000/api${cleanEndpoint}`;

      try {
        const fallbackRes = await fetch(fallbackUrl, options);
        return fallbackRes;
      } catch (fallbackErr) {
        throw primaryErr;
      }
    }
    throw primaryErr;
  }
}
