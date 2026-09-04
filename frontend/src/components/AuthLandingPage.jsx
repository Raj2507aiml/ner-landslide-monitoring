import React, { useState } from 'react';
import {
  Shield,
  ShieldAlert,
  User,
  UserPlus,
  LogIn,
  Lock,
  Eye,
  EyeOff,
  AlertCircle,
  CheckCircle2,
  PhoneCall,
  MapPin,
  ChevronRight,
  Info
} from 'lucide-react';
import { loginUser, registerCitizen, USER_ROLES } from '../services/authService';
import LanguageSwitcher from './LanguageSwitcher';
import { useTranslation } from '../services/i18nService';

export default function AuthLandingPage({ onLoginSuccess, initialPortal = 'USER' }) {
  const { t } = useTranslation();
  // Main Portal: 'USER' (Citizen Safety Portal) vs 'ADMIN' (Official Disaster Authority Portal)
  const [activePortal, setActivePortal] = useState(initialPortal); // 'USER' | 'ADMIN'
  const [userMode, setUserMode] = useState('LOGIN'); // 'LOGIN' | 'REGISTER'

  // User / Citizen Form State
  const [userEmail, setUserEmail] = useState('');
  const [userPassword, setUserPassword] = useState('');
  const [regName, setRegName] = useState('');
  const [regEmail, setRegEmail] = useState('');
  const [regPassword, setRegPassword] = useState('');
  const [regPhone, setRegPhone] = useState('');
  const [regState, setRegState] = useState('Meghalaya');

  // Official Admin Form State
  const [adminEmail, setAdminEmail] = useState('');
  const [adminPassword, setAdminPassword] = useState('');

  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState(null);
  const [successMsg, setSuccessMsg] = useState(null);
  const [loading, setLoading] = useState(false);

  // Switch between Citizen portal and Admin portal
  const switchPortal = (portal) => {
    setActivePortal(portal);
    setError(null);
    setSuccessMsg(null);
    setShowPassword(false);
  };

  // Quick Credential Fill Helpers for Testing
  const fillDemoAdmin = () => {
    switchPortal('ADMIN');
    setAdminEmail('commander@ner.gov.in');
    setAdminPassword('password123');
    setError(null);
  };

  const fillDemoCitizen = () => {
    switchPortal('USER');
    setUserMode('LOGIN');
    setUserEmail('citizen@ner.gov.in');
    setUserPassword('password123');
    setError(null);
  };

  // Handle Citizen Login
  const handleCitizenLogin = async (e) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      const res = await loginUser(userEmail, userPassword, USER_ROLES.CITIZEN);
      setLoading(false);
      if (res.ok) {
        if (onLoginSuccess) onLoginSuccess(res.user);
      } else {
        setError(res.error || 'Invalid credentials.');
      }
    } catch (err) {
      setLoading(false);
      setError('An error occurred during login. Please try again.');
    }
  };

  // Handle Citizen Registration
  const handleCitizenRegister = async (e) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      const res = await registerCitizen({
        name: regName,
        email: regEmail,
        password: regPassword,
        phone: regPhone,
        state: regState
      });
      setLoading(false);
      if (res.ok) {
        setSuccessMsg('Account registered successfully! Redirecting to Citizen Dashboard...');
        setTimeout(() => {
          if (onLoginSuccess) onLoginSuccess(res.user);
        }, 600);
      } else {
        setError(res.error || 'Registration failed.');
      }
    } catch (err) {
      setLoading(false);
      setError('Registration error. Please check your network and try again.');
    }
  };

  // Handle Official Admin Login
  const handleAdminLogin = async (e) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      const res = await loginUser(adminEmail, adminPassword, USER_ROLES.ADMIN);
      setLoading(false);
      if (res.ok && res.user.role === USER_ROLES.ADMIN) {
        if (onLoginSuccess) onLoginSuccess(res.user);
      } else {
        setError(res.error || 'Access Denied: Only verified NDMA/NER disaster commanders can sign in here.');
      }
    } catch (err) {
      setLoading(false);
      setError('Official authentication error. Please try again.');
    }
  };

  return (
    <div className="min-h-screen bg-[var(--canvas-bg)] text-[var(--text-main)] font-sans flex flex-col justify-between relative selection:bg-emerald-500/30 selection:text-emerald-200">
      
      {/* Background Ambience */}
      <div 
        className="fixed inset-0 pointer-events-none z-0 bg-cover bg-center bg-no-repeat transition-opacity duration-500"
        style={{ 
          backgroundImage: "url('/terrain_bg.jpg')",
          opacity: "0.15"
        }}
      />
      <div 
        className="fixed inset-0 pointer-events-none z-0" 
        style={{ background: "var(--bg-gradient-vignette)" }}
      />

      {/* Top Government Seal Header */}
      <header className="relative z-10 w-full border-b border-[var(--border-subtle)] bg-[var(--header-bg)]/80 backdrop-blur-md px-4 sm:px-8 py-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="h-10 w-10 rounded-full border border-emerald-500/40 bg-emerald-950/50 flex items-center justify-center shrink-0 shadow-sm">
            <ShieldAlert className="h-5 w-5 text-emerald-400" />
          </div>
          <div>
            <div className="text-[10px] font-bold uppercase tracking-widest text-[var(--text-dim)]">
              {t('gov_seal', 'Government of India · NDMA · North Eastern Council')}
            </div>
            <h1 className="text-sm sm:text-base font-bold text-[var(--text-main)] leading-tight">
              {t('system_title', 'NER Landslide Risk Monitoring & Early Warning System')}
            </h1>
          </div>
        </div>

        <div className="flex items-center gap-2 text-xs text-[var(--text-muted)]">
          {/* Regional Multilingual Language Switcher */}
          <LanguageSwitcher compact={false} />

          <a
            href="tel:1070"
            className="hidden md:flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-rose-600/15 border border-rose-500/30 text-rose-400 text-xs font-semibold hover:bg-rose-600/25 transition"
            title="Call 24/7 State Disaster Management Helpline"
          >
            <PhoneCall className="h-3 w-3 text-rose-400" />
            <span>{t('helpline_title', 'Helpline: 1070')} / 112</span>
          </a>
        </div>
      </header>

      {/* Center Auth Card Container */}
      <main className="relative z-10 flex-1 flex items-center justify-center p-4 sm:p-6 my-auto">
        <div className="w-full max-w-lg bg-[var(--panel-bg)] border border-[var(--border-subtle)] rounded-2xl shadow-2xl overflow-hidden flex flex-col backdrop-blur-xl">
          
          {/* Top Portal Switcher (Citizen vs Official Admin) */}
          <div className="grid grid-cols-2 p-2 bg-[var(--subcard-bg)] border-b border-[var(--border-subtle)] gap-2">
            <button
              type="button"
              onClick={() => switchPortal('USER')}
              className={`py-2.5 px-3 rounded-xl font-bold text-xs flex items-center justify-center gap-2 transition cursor-pointer ${
                activePortal === 'USER'
                  ? 'bg-emerald-600 text-white shadow-md'
                  : 'text-[var(--text-muted)] hover:text-[var(--text-main)] hover:bg-[var(--card-bg)]'
              }`}
            >
              <User className="h-4 w-4" />
              <span>{t('citizen_portal_tab', 'Citizen Safety Portal')}</span>
            </button>

            <button
              type="button"
              onClick={() => switchPortal('ADMIN')}
              className={`py-2.5 px-3 rounded-xl font-bold text-xs flex items-center justify-center gap-2 transition cursor-pointer ${
                activePortal === 'ADMIN'
                  ? 'bg-rose-700 text-white shadow-md'
                  : 'text-[var(--text-muted)] hover:text-[var(--text-main)] hover:bg-[var(--card-bg)]'
              }`}
            >
              <Shield className="h-4 w-4" />
              <span>{t('admin_portal_tab', 'Official Admin Login')}</span>
            </button>
          </div>

          {/* Portal Sub-Header */}
          <div className="px-6 pt-5 pb-3 border-b border-[var(--border-subtle)]/60 bg-[var(--card-bg)]">
            {activePortal === 'USER' ? (
              <div className="flex items-start justify-between gap-2">
                <div>
                  <h2 className="text-base font-bold text-[var(--text-main)] flex items-center gap-2">
                    <User className="h-4 w-4 text-emerald-400" />
                    <span>{t('citizen_portal_subtitle', 'Public Citizen Safety Network')}</span>
                  </h2>
                  <p className="text-xs text-[var(--text-muted)] mt-0.5">
                    {t('citizen_portal_desc', 'Access interactive regional landslide maps, rainfall telemetry, and submit community hazard reports.')}
                  </p>
                </div>
              </div>
            ) : (
              <div>
                <div className="flex items-center gap-1.5 text-rose-400 text-[10px] font-bold uppercase tracking-widest">
                  <Shield className="h-3 w-3" />
                  <span>{t('restricted_access_badge', 'Restricted Access · Authorized Personnel Only')}</span>
                </div>
                <h2 className="text-base font-bold text-[var(--text-main)] mt-0.5">
                  {t('admin_portal_subtitle', 'Disaster Authority & Incident Command')}
                </h2>
                <p className="text-xs text-[var(--text-muted)] mt-0.5">
                  {t('admin_portal_desc', 'Secure sign-in for Incident Commanders, District Magistrates, NDRF coordinators, and BRO officers.')}
                </p>
              </div>
            )}
          </div>

          {/* Citizen Mode Selector: Login vs Register */}
          {activePortal === 'USER' && (
            <div className="px-6 pt-4 pb-1">
              <div className="flex border-b border-[var(--border-subtle)] text-xs font-semibold">
                <button
                  type="button"
                  onClick={() => {
                    setUserMode('LOGIN');
                    setError(null);
                    setSuccessMsg(null);
                  }}
                  className={`pb-2.5 px-4 transition cursor-pointer border-b-2 -mb-px flex items-center gap-1.5 ${
                    userMode === 'LOGIN'
                      ? 'border-emerald-500 text-emerald-400 font-bold'
                      : 'border-transparent text-[var(--text-muted)] hover:text-[var(--text-main)]'
                  }`}
                >
                  <LogIn className="h-3.5 w-3.5" />
                  <span>{t('sign_in_tab', 'User Sign In')}</span>
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setUserMode('REGISTER');
                    setError(null);
                    setSuccessMsg(null);
                  }}
                  className={`pb-2.5 px-4 transition cursor-pointer border-b-2 -mb-px flex items-center gap-1.5 ${
                    userMode === 'REGISTER'
                      ? 'border-emerald-500 text-emerald-400 font-bold'
                      : 'border-transparent text-[var(--text-muted)] hover:text-[var(--text-main)]'
                  }`}
                >
                  <UserPlus className="h-3.5 w-3.5" />
                  <span>{t('register_tab', 'Register New Citizen')}</span>
                </button>
              </div>
            </div>
          )}

          {/* Form Content Body */}
          <div className="p-6 space-y-4">
            
            {/* Error Message Banner */}
            {error && (
              <div className="p-3 bg-rose-500/10 border border-rose-500/30 rounded-lg flex items-start gap-2 text-xs text-rose-300 animate-in fade-in duration-200">
                <AlertCircle className="h-4 w-4 shrink-0 mt-0.5 text-rose-400" />
                <span>{error}</span>
              </div>
            )}

            {/* Success Message Banner */}
            {successMsg && (
              <div className="p-3 bg-emerald-500/10 border border-emerald-500/30 rounded-lg flex items-start gap-2 text-xs text-emerald-300 animate-in fade-in duration-200">
                <CheckCircle2 className="h-4 w-4 shrink-0 mt-0.5 text-emerald-400" />
                <span>{successMsg}</span>
              </div>
            )}

            {/* 1. CITIZEN USER LOGIN FORM */}
            {activePortal === 'USER' && userMode === 'LOGIN' && (
              <form onSubmit={handleCitizenLogin} className="space-y-3.5">
                <div>
                  <label className="block text-xs font-semibold text-[var(--text-main)] mb-1">
                    {t('email_label', 'Registered Email Address')}
                  </label>
                  <input
                    type="text"
                    required
                    value={userEmail}
                    onChange={(e) => setUserEmail(e.target.value)}
                    placeholder="e.g. citizen@ner.gov.in"
                    className="w-full px-3 py-2 text-xs bg-[var(--card-bg)] border border-[var(--border-subtle)] rounded-lg text-[var(--text-main)] placeholder-[var(--text-dim)] focus:outline-none focus:border-emerald-500"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-[var(--text-main)] mb-1">
                    {t('password_label', 'Password')}
                  </label>
                  <div className="relative">
                    <input
                      type={showPassword ? 'text' : 'password'}
                      required
                      value={userPassword}
                      onChange={(e) => setUserPassword(e.target.value)}
                      placeholder="Enter your account password"
                      className="w-full px-3 py-2 pr-9 text-xs bg-[var(--card-bg)] border border-[var(--border-subtle)] rounded-lg text-[var(--text-main)] placeholder-[var(--text-dim)] focus:outline-none focus:border-emerald-500"
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="absolute right-2.5 top-1/2 -translate-y-1/2 text-[var(--text-muted)] hover:text-[var(--text-main)]"
                    >
                      {showPassword ? <EyeOff className="h-3.5 w-3.5" /> : <Eye className="h-3.5 w-3.5" />}
                    </button>
                  </div>
                </div>

                <button
                  type="submit"
                  disabled={loading}
                  className="w-full py-2.5 px-4 bg-emerald-600 hover:bg-emerald-500 text-white font-bold rounded-lg text-xs shadow-md transition disabled:opacity-50 cursor-pointer flex items-center justify-center gap-2"
                >
                  <LogIn className="h-4 w-4" />
                  <span>{loading ? 'Authenticating...' : t('sign_in_button', 'Enter Citizen Safety Portal')}</span>
                </button>

                <div className="text-center pt-1">
                  <p className="text-xs text-[var(--text-muted)]">
                    Don't have an account?{' '}
                    <button
                      type="button"
                      onClick={() => setUserMode('REGISTER')}
                      className="text-emerald-400 hover:underline font-semibold cursor-pointer"
                    >
                      Click here to Register
                    </button>
                  </p>
                </div>
              </form>
            )}

            {/* 2. CITIZEN USER REGISTRATION FORM */}
            {activePortal === 'USER' && userMode === 'REGISTER' && (
              <form onSubmit={handleCitizenRegister} className="space-y-3">
                <div>
                  <label className="block text-xs font-semibold text-[var(--text-main)] mb-1">
                    {t('full_name_label', 'Full Name')} *
                  </label>
                  <input
                    type="text"
                    required
                    value={regName}
                    onChange={(e) => setRegName(e.target.value)}
                    placeholder="e.g. Pema Tashi"
                    className="w-full px-3 py-2 text-xs bg-[var(--card-bg)] border border-[var(--border-subtle)] rounded-lg text-[var(--text-main)] placeholder-[var(--text-dim)] focus:outline-none focus:border-emerald-500"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-[var(--text-main)] mb-1">
                    {t('email_label', 'Registered Email Address')} *
                  </label>
                  <input
                    type="email"
                    required
                    value={regEmail}
                    onChange={(e) => setRegEmail(e.target.value)}
                    placeholder="e.g. yourname@domain.com"
                    className="w-full px-3 py-2 text-xs bg-[var(--card-bg)] border border-[var(--border-subtle)] rounded-lg text-[var(--text-main)] placeholder-[var(--text-dim)] focus:outline-none focus:border-emerald-500"
                  />
                </div>

                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <label className="block text-xs font-semibold text-[var(--text-main)] mb-1">
                      {t('password_label', 'Password')} *
                    </label>
                    <div className="relative">
                      <input
                        type={showPassword ? 'text' : 'password'}
                        required
                        value={regPassword}
                        onChange={(e) => setRegPassword(e.target.value)}
                        placeholder="Min 4 chars"
                        className="w-full px-3 py-2 pr-8 text-xs bg-[var(--card-bg)] border border-[var(--border-subtle)] rounded-lg text-[var(--text-main)] placeholder-[var(--text-dim)] focus:outline-none focus:border-emerald-500"
                      />
                      <button
                        type="button"
                        onClick={() => setShowPassword(!showPassword)}
                        className="absolute right-2 top-1/2 -translate-y-1/2 text-[var(--text-muted)] hover:text-[var(--text-main)]"
                      >
                        {showPassword ? <EyeOff className="h-3 w-3" /> : <Eye className="h-3 w-3" />}
                      </button>
                    </div>
                  </div>

                  <div>
                    <label className="block text-xs font-semibold text-[var(--text-main)] mb-1">
                      {t('phone_label', 'Mobile Number')}
                    </label>
                    <input
                      type="tel"
                      value={regPhone}
                      onChange={(e) => setRegPhone(e.target.value)}
                      placeholder="+91 98765..."
                      className="w-full px-3 py-2 text-xs bg-[var(--card-bg)] border border-[var(--border-subtle)] rounded-lg text-[var(--text-main)] placeholder-[var(--text-dim)] focus:outline-none focus:border-emerald-500"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-[var(--text-main)] mb-1">
                    {t('state_label', 'Resident State')}
                  </label>
                  <select
                    value={regState}
                    onChange={(e) => setRegState(e.target.value)}
                    className="w-full px-3 py-2 text-xs bg-[var(--card-bg)] border border-[var(--border-subtle)] rounded-lg text-[var(--text-main)] focus:outline-none focus:border-emerald-500 cursor-pointer"
                  >
                    <option value="Meghalaya">Meghalaya</option>
                    <option value="Sikkim">Sikkim</option>
                    <option value="Assam">Assam</option>
                    <option value="Arunachal Pradesh">Arunachal Pradesh</option>
                    <option value="Nagaland">Nagaland</option>
                    <option value="Manipur">Manipur</option>
                    <option value="Mizoram">Mizoram</option>
                    <option value="Tripura">Tripura</option>
                  </select>
                </div>

                <button
                  type="submit"
                  disabled={loading}
                  className="w-full py-2.5 px-4 bg-emerald-600 hover:bg-emerald-500 text-white font-bold rounded-lg text-xs shadow-md transition disabled:opacity-50 cursor-pointer flex items-center justify-center gap-2 mt-2"
                >
                  <UserPlus className="h-4 w-4" />
                  <span>{loading ? 'Creating Citizen Profile...' : t('register_button', 'Create Citizen Account & Enter')}</span>
                </button>
              </form>
            )}

            {/* 3. OFFICIAL DISASTER AUTHORITY ADMIN LOGIN FORM */}
            {activePortal === 'ADMIN' && (
              <form onSubmit={handleAdminLogin} className="space-y-3.5">
                <div className="p-3 bg-rose-500/10 border border-rose-500/20 rounded-lg text-xs text-rose-300 flex items-start gap-2">
                  <Shield className="h-4 w-4 shrink-0 mt-0.5 text-rose-400" />
                  <p className="leading-tight">
                    Authorized official credential gate for Incident Commanders, District Magistrates, NDRF coordinators, and BRO officers.
                  </p>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-[var(--text-main)] mb-1">
                    Official Commander Email or Officer ID
                  </label>
                  <input
                    type="text"
                    required
                    value={adminEmail}
                    onChange={(e) => setAdminEmail(e.target.value)}
                    placeholder="e.g. commander@ner.gov.in"
                    className="w-full px-3 py-2 text-xs bg-[var(--card-bg)] border border-[var(--border-subtle)] rounded-lg text-[var(--text-main)] placeholder-[var(--text-dim)] focus:outline-none focus:border-rose-500"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-[var(--text-main)] mb-1">
                    {t('password_label', 'Password')} / Key
                  </label>
                  <div className="relative">
                    <input
                      type={showPassword ? 'text' : 'password'}
                      required
                      value={adminPassword}
                      onChange={(e) => setAdminPassword(e.target.value)}
                      placeholder="Enter official credentials"
                      className="w-full px-3 py-2 pr-9 text-xs bg-[var(--card-bg)] border border-[var(--border-subtle)] rounded-lg text-[var(--text-main)] placeholder-[var(--text-dim)] focus:outline-none focus:border-rose-500"
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="absolute right-2.5 top-1/2 -translate-y-1/2 text-[var(--text-muted)] hover:text-[var(--text-main)]"
                    >
                      {showPassword ? <EyeOff className="h-3.5 w-3.5" /> : <Eye className="h-3.5 w-3.5" />}
                    </button>
                  </div>
                </div>

                <button
                  type="submit"
                  disabled={loading}
                  className="w-full py-2.5 px-4 bg-rose-700 hover:bg-rose-600 text-white font-bold rounded-lg text-xs shadow-md transition disabled:opacity-50 cursor-pointer flex items-center justify-center gap-2"
                >
                  <Shield className="h-4 w-4" />
                  <span>{loading ? 'Verifying Credentials...' : t('admin_login_button', 'Authenticate Commander Access')}</span>
                </button>
              </form>
            )}

            {/* Quick Demo Credentials Quick-Fill Chips for Evaluators */}
            <div className="pt-3 border-t border-[var(--border-subtle)]">
              <span className="text-[10px] font-bold uppercase tracking-wider text-[var(--text-dim)] block mb-1.5">
                {t('demo_credentials_title', '1-Click Verification Test Credentials:')}
              </span>
              <div className="flex flex-wrap gap-2">
                <button
                  type="button"
                  onClick={fillDemoCitizen}
                  className="px-2.5 py-1 rounded-md bg-emerald-500/10 hover:bg-emerald-500/20 border border-emerald-500/30 text-emerald-400 text-[11px] font-medium transition cursor-pointer flex items-center gap-1.5"
                >
                  <User className="h-3 w-3" />
                  <span>{t('citizen_demo_tag', 'Pema Tashi (Citizen)')}</span>
                </button>

                <button
                  type="button"
                  onClick={fillDemoAdmin}
                  className="px-2.5 py-1 rounded-md bg-rose-500/10 hover:bg-rose-500/20 border border-rose-500/30 text-rose-400 text-[11px] font-medium transition cursor-pointer flex items-center gap-1.5"
                >
                  <Shield className="h-3 w-3" />
                  <span>{t('admin_demo_tag', 'Col. Sanjeev Roy (Admin)')}</span>
                </button>
              </div>
            </div>

          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="relative z-10 w-full py-3 px-4 sm:px-8 border-t border-[var(--border-subtle)] bg-[var(--header-bg)]/80 backdrop-blur-md flex flex-col sm:flex-row items-center justify-between text-[11px] text-[var(--text-dim)] gap-2">
        <div>
          National Disaster Management Authority (NDMA) & North Eastern Council (NEC)
        </div>
        <div className="flex items-center gap-3">
          <span>Sentinel-1 SAR Real-Time InSAR</span>
          <span>•</span>
          <span>ISRO NRSC Telemetry</span>
          <span>•</span>
          <span>GSI Geotechnical Database</span>
        </div>
      </footer>

    </div>
  );
}
