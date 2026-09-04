/**
 * Central API Configuration & Resilient Fetch Utility
 * Supports localhost, 127.0.0.1, custom LAN IPs, and Vite dev proxies.
 */

export function getApiBaseUrl() {
  if (import.meta.env?.VITE_API_BASE_URL) {
    return import.meta.env.VITE_API_BASE_URL.replace(/\/+$/, '');
  }

  if (typeof window !== 'undefined') {
    // In production builds or when served via reverse proxy on standard HTTP/HTTPS ports (80, 443),
    // use relative '/api' to prevent exposing ports or internal backend IPs.
    const isStandardPort = window.location.port === '' || window.location.port === '80' || window.location.port === '443';
    if (import.meta.env.PROD || isStandardPort) {
      return '/api';
    }

    const hostname = window.location.hostname || '127.0.0.1';
    return `http://${hostname}:8000/api`;
  }
  return 'http://127.0.0.1:8000/api';
}

export function getMediaBaseUrl() {
  if (import.meta.env?.VITE_MEDIA_BASE_URL) {
    return import.meta.env.VITE_MEDIA_BASE_URL.replace(/\/+$/, '');
  }

  if (typeof window !== 'undefined') {
    const isStandardPort = window.location.port === '' || window.location.port === '80' || window.location.port === '443';
    if (import.meta.env.PROD || isStandardPort) {
      return '';
    }

    const hostname = window.location.hostname || '127.0.0.1';
    return `http://${hostname}:8000`;
  }
  return 'http://127.0.0.1:8000';
}

/**
 * Executes a resilient HTTP fetch with fallback between 127.0.0.1, localhost, and Vite dev proxy.
 * Prevents IPv6 ::1 connection refused issues on Windows.
 */
export async function apiFetch(endpoint, options = {}) {
  const cleanEndpoint = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
  
  // Strategy 1: Direct call using current window.location.hostname
  const primaryBase = getApiBaseUrl();
  const primaryUrl = `${primaryBase}${cleanEndpoint}`;

  try {
    const res = await fetch(primaryUrl, options);
    return res;
  } catch (primaryErr) {
    // Strategy 2: Try explicit IPv4 127.0.0.1 or localhost fallback
    const fallbackHost = (typeof window !== 'undefined' && window.location.hostname === '127.0.0.1')
      ? 'localhost'
      : '127.0.0.1';
    const fallbackUrl = `http://${fallbackHost}:8000/api${cleanEndpoint}`;

    try {
      const fallbackRes = await fetch(fallbackUrl, options);
      return fallbackRes;
    } catch (fallbackErr) {
      // Strategy 3: Try relative dev proxy (/api/...)
      try {
        const proxyUrl = `/api${cleanEndpoint}`;
        const proxyRes = await fetch(proxyUrl, options);
        return proxyRes;
      } catch (proxyErr) {
        // If all fallbacks failed, throw original error
        throw primaryErr;
      }
    }
  }
}
