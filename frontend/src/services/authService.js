/**
 * Authentication & Session Service
 * Provides distinct User (Citizen) and Admin (Official Authority) authentication,
 * backend API connectivity with JWT tokens, role verification, and local fallback.
 */

import { apiFetch } from './apiConfig';

const AUTH_STORAGE_KEY = 'ner_auth_session_user';
const AUTH_TOKEN_KEY = 'ner_auth_jwt_token';
const REGISTERED_USERS_KEY = 'ner_registered_citizen_accounts';

export const USER_ROLES = {
  ADMIN: 'ADMIN',
  CITIZEN: 'CITIZEN'
};

// Standard government profiles
export const DEMO_USERS = {
  ADMIN: {
    id: 'USR-CMD-01',
    username: 'admin',
    name: 'Col. Sanjeev Roy (Retd.)',
    email: 'commander@ner.gov.in',
    role: USER_ROLES.ADMIN,
    designation: 'Joint Director & Incident Commander',
    agency: 'National Disaster Management Authority (NER EWDSS)',
    avatar: '🛡️',
    badgeText: 'COMMANDER (ADMIN)'
  },
  CITIZEN: {
    id: 'USR-CIT-01',
    username: 'citizen',
    name: 'Pema Tashi',
    email: 'citizen@ner.gov.in',
    role: USER_ROLES.CITIZEN,
    designation: 'Community Member / Local Observer',
    agency: 'Public Safety & Citizen Reporting Network',
    avatar: '👤',
    badgeText: 'CITIZEN'
  }
};

/**
 * Returns JWT token from localStorage.
 */
export function getAuthToken() {
  try {
    return localStorage.getItem(AUTH_TOKEN_KEY);
  } catch {
    return null;
  }
}

/**
 * Persists or clears JWT token in localStorage.
 */
export function setAuthToken(token) {
  try {
    if (token) {
      localStorage.setItem(AUTH_TOKEN_KEY, token);
    } else {
      localStorage.removeItem(AUTH_TOKEN_KEY);
    }
  } catch (e) {
    console.warn('Error saving auth token:', e);
  }
}

/**
 * Returns list of locally cached registered citizens from localStorage.
 */
export function getRegisteredUsers() {
  try {
    const raw = localStorage.getItem(REGISTERED_USERS_KEY);
    if (raw) {
      const parsed = JSON.parse(raw);
      if (Array.isArray(parsed)) return parsed;
    }
  } catch (e) {
    console.warn('Error reading registered users from storage:', e);
  }
  return [
    {
      id: 'USR-CIT-01',
      name: 'Pema Tashi',
      email: 'citizen@ner.gov.in',
      password: 'password123',
      phone: '+91 98765 43210',
      state: 'Meghalaya',
      role: USER_ROLES.CITIZEN
    }
  ];
}

/**
 * Registers a new citizen user via backend API with local fallback.
 */
export async function registerCitizen({ name, email, password, phone, state }) {
  const cleanEmail = (email || '').trim().toLowerCase();
  const cleanPass = (password || '').trim();
  const cleanName = (name || '').trim();

  if (!cleanName) {
    return { ok: false, error: 'Full name is required.' };
  }
  if (!cleanEmail || !cleanEmail.includes('@')) {
    return { ok: false, error: 'A valid email address is required.' };
  }
  if (!cleanPass || cleanPass.length < 4) {
    return { ok: false, error: 'Password must be at least 4 characters.' };
  }

  // 1. Attempt Backend API Registration
  try {
    const res = await apiFetch('/v1/auth/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name: cleanName,
        email: cleanEmail,
        password: cleanPass,
        phone: phone || null,
        state: state || 'North Eastern Region'
      })
    });

    if (res.ok) {
      const data = await res.json();
      if (data && data.access_token) {
        setAuthToken(data.access_token);
        const userObj = {
          id: data.user?.id || `CIT-${Date.now()}`,
          name: data.user?.name || cleanName,
          email: data.user?.email || cleanEmail,
          role: USER_ROLES.CITIZEN,
          phone: data.user?.phone || phone || '',
          state: data.user?.state || state || 'North Eastern Region',
          designation: 'Registered Citizen / Field Observer',
          agency: 'Community Landslide Watch Network',
          avatar: '👤',
          badgeText: 'REGISTERED CITIZEN'
        };
        setCurrentUser(userObj);
        return { ok: true, user: userObj };
      }
    } else {
      const errJson = await res.json().catch(() => ({}));
      return { ok: false, error: errJson.detail || 'Registration failed on server.' };
    }
  } catch (backendErr) {
    console.warn('Backend registration unavailable, falling back to local session:', backendErr);
  }

  // 2. Offline / Local Fallback Registration
  const existingUsers = getRegisteredUsers();
  const duplicate = existingUsers.find(u => u.email.toLowerCase() === cleanEmail);
  if (duplicate) {
    return { ok: false, error: 'An account with this email is already registered. Please sign in.' };
  }

  const newUser = {
    id: `CIT-${Date.now()}`,
    name: cleanName,
    email: cleanEmail,
    password: cleanPass,
    phone: (phone || '').trim(),
    state: state || 'North Eastern Region',
    role: USER_ROLES.CITIZEN,
    designation: 'Registered Citizen / Field Observer',
    agency: 'Community Landslide Watch Network',
    avatar: '👤',
    badgeText: 'REGISTERED CITIZEN'
  };

  try {
    const updatedList = [...existingUsers, newUser];
    localStorage.setItem(REGISTERED_USERS_KEY, JSON.stringify(updatedList));
  } catch (e) {
    console.warn('Error saving citizen to storage:', e);
  }

  setCurrentUser(newUser);
  return { ok: true, user: newUser };
}

/**
 * Authenticates user or admin credentials via backend API with local fallback.
 */
export async function loginUser(emailOrUsername, password, roleHint = null) {
  const cleanInput = (emailOrUsername || '').trim().toLowerCase();
  const cleanPass = (password || '').trim();

  if (!cleanInput || !cleanPass) {
    return { ok: false, error: 'Please enter both your email/ID and password.' };
  }

  const portalHint = (roleHint === USER_ROLES.ADMIN || cleanInput.includes('admin') || cleanInput.includes('commander'))
    ? 'admin'
    : 'user';

  // 1. Attempt Backend API Login
  try {
    const res = await apiFetch('/v1/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        email: cleanInput,
        password: cleanPass,
        portal_hint: portalHint
      })
    });

    if (res.ok) {
      const data = await res.json();
      if (data && data.access_token) {
        setAuthToken(data.access_token);
        const isServerAdmin = data.user?.role === 'admin';
        const userObj = {
          id: data.user?.id,
          name: data.user?.name,
          email: data.user?.email,
          role: isServerAdmin ? USER_ROLES.ADMIN : USER_ROLES.CITIZEN,
          phone: data.user?.phone || '',
          state: data.user?.state || '',
          designation: isServerAdmin ? 'Joint Director & Incident Commander' : 'Registered Citizen / Field Observer',
          agency: isServerAdmin ? 'National Disaster Management Authority (NER EWDSS)' : 'Community Landslide Watch Network',
          avatar: isServerAdmin ? '🛡️' : '👤',
          badgeText: isServerAdmin ? 'COMMANDER (ADMIN)' : 'REGISTERED CITIZEN'
        };
        setCurrentUser(userObj);
        return { ok: true, user: userObj };
      }
    } else {
      const errJson = await res.json().catch(() => ({}));
      return { ok: false, error: errJson.detail || 'Invalid email or password.' };
    }
  } catch (apiErr) {
    console.warn('Backend login unavailable, checking offline credentials:', apiErr);
  }

  // 2. Local Fallback Verification
  const isAdminUser = 
    cleanInput === 'commander@ner.gov.in' || 
    cleanInput === 'admin@ner.gov.in' || 
    cleanInput === 'admin' || 
    cleanInput === 'commander';

  const isValidAdminPass = 
    cleanPass === 'password123' || 
    cleanPass === 'admin123';

  if (isAdminUser && isValidAdminPass) {
    const adminUser = {
      ...DEMO_USERS.ADMIN,
      email: cleanInput.includes('@') ? cleanInput : 'commander@ner.gov.in',
      username: cleanInput
    };
    setCurrentUser(adminUser);
    return { ok: true, user: adminUser };
  }

  // Check Registered Citizen Credentials locally
  const registered = getRegisteredUsers();
  const matchedCitizen = registered.find(
    u => (u.email.toLowerCase() === cleanInput || u.name.toLowerCase() === cleanInput) && 
         u.password === cleanPass
  );

  if (matchedCitizen) {
    const citizenUser = {
      ...matchedCitizen,
      role: USER_ROLES.CITIZEN,
      avatar: '👤',
      badgeText: 'REGISTERED CITIZEN'
    };
    setCurrentUser(citizenUser);
    return { ok: true, user: citizenUser };
  }

  // Fallback demo citizen
  if ((cleanInput === 'citizen@ner.gov.in' || cleanInput === 'citizen' || cleanInput === 'user') && cleanPass === 'password123') {
    const citizenUser = DEMO_USERS.CITIZEN;
    setCurrentUser(citizenUser);
    return { ok: true, user: citizenUser };
  }

  if (portalHint === 'admin' || isAdminUser) {
    return { 
      ok: false, 
      error: 'Access Denied: Invalid official administrator credentials. Incident Commander authorization required.' 
    };
  }

  return { 
    ok: false, 
    error: 'Invalid email or password. If you do not have an account, please click "Register" to create one.' 
  };
}

/**
 * Verifies with backend if current token possesses administrator privileges.
 */
export async function verifyAdminAccess() {
  const token = getAuthToken();
  if (!token) return { ok: false, error: 'No token found' };

  try {
    const res = await apiFetch('/v1/auth/admin-verify', {
      method: 'GET',
      headers: { 'Authorization': `Bearer ${token}` }
    });
    if (res.ok) {
      const data = await res.json();
      return { ok: true, data };
    }
    const err = await res.json().catch(() => ({}));
    return { ok: false, status: res.status, error: err.detail || 'Access Denied' };
  } catch (e) {
    console.warn('Backend admin-verify error:', e);
    // If backend is down, verify against current localStorage user
    const current = getCurrentUser();
    if (current && current.role === USER_ROLES.ADMIN) {
      return { ok: true, data: { status: 'offline_verified', role: 'admin' } };
    }
    return { ok: false, error: 'Offline check failed' };
  }
}

/**
 * Retrieves authenticated user session from localStorage.
 */
export function getCurrentUser() {
  try {
    const raw = localStorage.getItem(AUTH_STORAGE_KEY);
    if (raw) {
      const parsed = JSON.parse(raw);
      if (parsed && parsed.role) return parsed;
    }
  } catch (e) {
    console.warn('Error reading auth session from storage:', e);
  }
  return null;
}

/**
 * Saves authenticated user session to localStorage.
 */
export function setCurrentUser(user) {
  try {
    if (user) {
      localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(user));
    } else {
      localStorage.removeItem(AUTH_STORAGE_KEY);
    }
  } catch (e) {
    console.warn('Error persisting auth session:', e);
  }
}

/**
 * Logs out user, clears token and session.
 */
export function logoutUser() {
  try {
    localStorage.removeItem(AUTH_STORAGE_KEY);
    localStorage.removeItem(AUTH_TOKEN_KEY);
  } catch (e) {
    console.warn('Failed to clear auth storage:', e);
  }
  return null;
}

/**
 * Safe role switcher helper
 */
export function switchUserRole(targetRole) {
  if (targetRole === USER_ROLES.CITIZEN) {
    setCurrentUser(DEMO_USERS.CITIZEN);
    return DEMO_USERS.CITIZEN;
  }
  return getCurrentUser();
}
