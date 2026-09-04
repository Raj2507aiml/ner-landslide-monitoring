import React, { useState, useEffect } from 'react';
import {
  X,
  Shield,
  Lock,
  ArrowRight,
  AlertCircle,
  PhoneCall,
  Eye,
  EyeOff,
  User,
  KeyRound,
  UserPlus,
  LogIn,
  MapPin,
  CheckCircle2
} from 'lucide-react';
import { loginUser, registerCitizen, USER_ROLES } from '../services/authService';

export default function LoginModal({
  isOpen,
  initialTab = 'USER_LOGIN', // 'USER_LOGIN' | 'USER_REGISTER' | 'ADMIN_LOGIN'
  onClose,
  onLoginSuccess
}) {
  const [activePortal, setActivePortal] = useState('USER'); // 'USER' | 'ADMIN'
  const [userMode, setUserMode] = useState('LOGIN'); // 'LOGIN' | 'REGISTER'

  // User form states
  const [userEmail, setUserEmail] = useState('');
  const [userPassword, setUserPassword] = useState('');
  const [regName, setRegName] = useState('');
  const [regEmail, setRegEmail] = useState('');
  const [regPassword, setRegPassword] = useState('');
  const [regPhone, setRegPhone] = useState('');
  const [regState, setRegState] = useState('Meghalaya');

  // Admin form states
  const [adminEmail, setAdminEmail] = useState('');
  const [adminPassword, setAdminPassword] = useState('');

  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState(null);
  const [successMsg, setSuccessMsg] = useState(null);
  const [loading, setLoading] = useState(false);

  // Sync initial tab when modal opens
  useEffect(() => {
    if (initialTab === 'ADMIN_LOGIN') {
      setActivePortal('ADMIN');
      setUserMode('LOGIN');
    } else if (initialTab === 'USER_REGISTER') {
      setActivePortal('USER');
      setUserMode('REGISTER');
    } else {
      setActivePortal('USER');
      setUserMode('LOGIN');
    }
    setError(null);
    setSuccessMsg(null);
  }, [initialTab, isOpen]);

  if (!isOpen) return null;

  // Handle Citizen Login
  const handleUserLogin = async (e) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      const res = await loginUser(userEmail, userPassword, USER_ROLES.CITIZEN);
      setLoading(false);
      if (res.ok) {
        if (onLoginSuccess) onLoginSuccess(res.user);
        if (onClose) onClose();
      } else {
        setError(res.error);
      }
    } catch (err) {
      setLoading(false);
      setError('Login error occurred.');
    }
  };

  // Handle Citizen Registration
  const handleUserRegister = async (e) => {
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
        setSuccessMsg('Account registered successfully! Logging in...');
        setTimeout(() => {
          if (onLoginSuccess) onLoginSuccess(res.user);
          if (onClose) onClose();
        }, 600);
      } else {
        setError(res.error);
      }
    } catch (err) {
      setLoading(false);
      setError('Registration error occurred.');
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
        if (onClose) onClose();
      } else {
        setError(res.error || 'Access Denied: Only authorized government officials can log in here.');
      }
    } catch (err) {
      setLoading(false);
      setError('Official login error occurred.');
    }
  };

  return (
    <div className="fixed inset-0 z-[2200] flex items-center justify-center p-3 sm:p-4 bg-black/80 backdrop-blur-xs animate-in fade-in duration-150">
      <div className="bg-[var(--panel-bg)] border border-[var(--border-subtle)] rounded-xl shadow-2xl w-full max-w-md overflow-hidden text-[var(--text-main)] flex flex-col">
        
        {/* Modal Header */}
        <div className="px-5 py-4 bg-[var(--card-bg)] border-b border-[var(--border-subtle)] flex items-start justify-between">
          <div className="flex items-center gap-3">
            <div className={`p-2 rounded-lg border shrink-0 ${
              activePortal === 'ADMIN'
                ? 'bg-rose-500/15 border-rose-500/30 text-rose-400'
                : 'bg-emerald-500/15 border-emerald-500/30 text-emerald-400'
            }`}>
              {activePortal === 'ADMIN' ? <Shield className="h-5 w-5" /> : <User className="h-5 w-5" />}
            </div>
            <div>
              <div className="text-[9.5px] font-bold uppercase tracking-widest text-[var(--text-dim)]">
                Government of India · NDMA / NEC
              </div>
              <h3 className="font-bold text-sm text-[var(--text-main)] uppercase tracking-wide">
                {activePortal === 'ADMIN' ? 'Disaster Authority Login' : 'Citizen Portal Access'}
              </h3>
              <p className="text-[11px] text-[var(--text-muted)]">
                {activePortal === 'ADMIN' ? 'Restricted to Verified Incident Commanders' : 'Sign in or register for public landslide safety alerts'}
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-[var(--text-muted)] hover:text-[var(--text-main)] hover:bg-[var(--subcard-bg)] transition cursor-pointer"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Portal Type Switcher Tabs */}
        <div className="px-5 pt-4 pb-0">
          <div className="grid grid-cols-2 gap-1.5 p-1 bg-[var(--subcard-bg)] rounded-lg border border-[var(--border-subtle)] text-xs">
            <button
              type="button"
              onClick={() => {
                setActivePortal('USER');
                setError(null);
              }}
              className={`py-2 px-3 rounded-md font-bold flex items-center justify-center gap-2 transition cursor-pointer ${
                activePortal === 'USER'
                  ? 'bg-emerald-600 text-white shadow-xs'
                  : 'text-[var(--text-muted)] hover:text-[var(--text-main)]'
              }`}
            >
              <User className="h-3.5 w-3.5" />
              <span>User / Citizen</span>
            </button>

            <button
              type="button"
              onClick={() => {
                setActivePortal('ADMIN');
                setError(null);
              }}
              className={`py-2 px-3 rounded-md font-bold flex items-center justify-center gap-2 transition cursor-pointer ${
                activePortal === 'ADMIN'
                  ? 'bg-rose-700 text-white shadow-xs'
                  : 'text-[var(--text-muted)] hover:text-[var(--text-main)]'
              }`}
            >
              <Shield className="h-3.5 w-3.5" />
              <span>Official Admin</span>
            </button>
          </div>
        </div>

        {/* Modal Body */}
        <div className="p-5 space-y-4 text-xs">
          
          {/* Status / Error Alerts */}
          {error && (
            <div className="p-2.5 rounded-lg bg-rose-500/15 border border-rose-500/30 text-rose-400 text-xs flex items-center gap-2">
              <AlertCircle className="h-4 w-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {successMsg && (
            <div className="p-2.5 rounded-lg bg-emerald-500/15 border border-emerald-500/30 text-emerald-400 text-xs flex items-center gap-2">
              <CheckCircle2 className="h-4 w-4 shrink-0" />
              <span>{successMsg}</span>
            </div>
          )}

          {/* ================= USER / CITIZEN PORTAL ================= */}
          {activePortal === 'USER' && (
            <div className="space-y-3.5">
              
              {/* User Login vs Register Mode Toggle */}
              <div className="flex items-center justify-between border-b border-[var(--border-subtle)] pb-2 text-xs">
                <span className="font-bold text-[var(--text-main)]">
                  {userMode === 'LOGIN' ? 'Citizen Sign In' : 'Register New Citizen Account'}
                </span>
                <div className="flex items-center gap-2 text-[11px]">
                  <button
                    type="button"
                    onClick={() => {
                      setUserMode('LOGIN');
                      setError(null);
                    }}
                    className={`font-semibold transition cursor-pointer ${
                      userMode === 'LOGIN' ? 'text-emerald-400 underline underline-offset-4' : 'text-[var(--text-dim)] hover:text-[var(--text-main)]'
                    }`}
                  >
                    Login
                  </button>
                  <span className="text-[var(--text-dim)]">•</span>
                  <button
                    type="button"
                    onClick={() => {
                      setUserMode('REGISTER');
                      setError(null);
                    }}
                    className={`font-semibold transition cursor-pointer ${
                      userMode === 'REGISTER' ? 'text-emerald-400 underline underline-offset-4' : 'text-[var(--text-dim)] hover:text-[var(--text-main)]'
                    }`}
                  >
                    Register
                  </button>
                </div>
              </div>

              {/* USER LOGIN FORM */}
              {userMode === 'LOGIN' && (
                <form onSubmit={handleUserLogin} className="space-y-3">
                  <div className="space-y-1">
                    <label className="text-[10px] font-bold text-[var(--text-dim)] uppercase tracking-wider block">
                      Email Address or Name
                    </label>
                    <div className="relative">
                      <User className="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-[var(--text-dim)]" />
                      <input
                        type="text"
                        value={userEmail}
                        onChange={(e) => setUserEmail(e.target.value)}
                        placeholder="e.g. citizen@ner.gov.in"
                        className="w-full bg-[var(--subcard-bg)] border border-[var(--border-subtle)] focus:border-emerald-500 rounded-lg pl-8 pr-3 py-2 text-xs text-[var(--text-main)] outline-none"
                        required
                        autoFocus
                      />
                    </div>
                  </div>

                  <div className="space-y-1">
                    <label className="text-[10px] font-bold text-[var(--text-dim)] uppercase tracking-wider block">
                      Password
                    </label>
                    <div className="relative">
                      <Lock className="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-[var(--text-dim)]" />
                      <input
                        type={showPassword ? 'text' : 'password'}
                        value={userPassword}
                        onChange={(e) => setUserPassword(e.target.value)}
                        placeholder="••••••••"
                        className="w-full bg-[var(--subcard-bg)] border border-[var(--border-subtle)] focus:border-emerald-500 rounded-lg pl-8 pr-8 py-2 text-xs text-[var(--text-main)] outline-none"
                        required
                      />
                      <button
                        type="button"
                        onClick={() => setShowPassword(!showPassword)}
                        className="absolute right-2.5 top-2.5 text-[var(--text-dim)] hover:text-[var(--text-main)] cursor-pointer"
                      >
                        {showPassword ? <EyeOff className="h-3.5 w-3.5" /> : <Eye className="h-3.5 w-3.5" />}
                      </button>
                    </div>
                  </div>

                  <button
                    type="submit"
                    disabled={loading}
                    className="w-full py-2.5 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg font-bold text-xs flex items-center justify-center gap-2 transition cursor-pointer shadow-md shadow-emerald-950/20"
                  >
                    <span>{loading ? 'Signing in...' : 'Sign In as Citizen'}</span>
                    <ArrowRight className="h-3.5 w-3.5" />
                  </button>

                  <div className="pt-2 text-center">
                    <p className="text-[11px] text-[var(--text-muted)]">
                      Don't have an account yet?{' '}
                      <button
                        type="button"
                        onClick={() => setUserMode('REGISTER')}
                        className="font-bold text-emerald-400 hover:underline cursor-pointer"
                      >
                        Register here
                      </button>
                    </p>
                    <p className="text-[10px] text-[var(--text-dim)] pt-1">
                      Demo citizen: <code className="text-emerald-400 font-mono">citizen@ner.gov.in</code> / <code className="text-emerald-400 font-mono">password123</code>
                    </p>
                  </div>
                </form>
              )}

              {/* USER REGISTRATION FORM */}
              {userMode === 'REGISTER' && (
                <form onSubmit={handleUserRegister} className="space-y-2.5">
                  <div className="space-y-1">
                    <label className="text-[10px] font-bold text-[var(--text-dim)] uppercase tracking-wider block">
                      Full Name *
                    </label>
                    <input
                      type="text"
                      value={regName}
                      onChange={(e) => setRegName(e.target.value)}
                      placeholder="e.g. Raj Gupta / Pema Tashi"
                      className="w-full bg-[var(--subcard-bg)] border border-[var(--border-subtle)] focus:border-emerald-500 rounded-lg px-3 py-1.5 text-xs text-[var(--text-main)] outline-none"
                      required
                    />
                  </div>

                  <div className="space-y-1">
                    <label className="text-[10px] font-bold text-[var(--text-dim)] uppercase tracking-wider block">
                      Email Address *
                    </label>
                    <input
                      type="email"
                      value={regEmail}
                      onChange={(e) => setRegEmail(e.target.value)}
                      placeholder="e.g. raj.gupta@example.com"
                      className="w-full bg-[var(--subcard-bg)] border border-[var(--border-subtle)] focus:border-emerald-500 rounded-lg px-3 py-1.5 text-xs text-[var(--text-main)] outline-none"
                      required
                    />
                  </div>

                  <div className="grid grid-cols-2 gap-2">
                    <div className="space-y-1">
                      <label className="text-[10px] font-bold text-[var(--text-dim)] uppercase tracking-wider block">
                        State / District
                      </label>
                      <select
                        value={regState}
                        onChange={(e) => setRegState(e.target.value)}
                        className="w-full bg-[var(--subcard-bg)] border border-[var(--border-subtle)] focus:border-emerald-500 rounded-lg px-2 py-1.5 text-xs text-[var(--text-main)] outline-none"
                      >
                        <option value="Meghalaya">Meghalaya</option>
                        <option value="Assam">Assam</option>
                        <option value="Nagaland">Nagaland</option>
                        <option value="Sikkim">Sikkim</option>
                        <option value="Mizoram">Mizoram</option>
                        <option value="Arunachal Pradesh">Arunachal Pradesh</option>
                        <option value="Manipur">Manipur</option>
                        <option value="Tripura">Tripura</option>
                      </select>
                    </div>

                    <div className="space-y-1">
                      <label className="text-[10px] font-bold text-[var(--text-dim)] uppercase tracking-wider block">
                        Mobile (Optional)
                      </label>
                      <input
                        type="tel"
                        value={regPhone}
                        onChange={(e) => setRegPhone(e.target.value)}
                        placeholder="+91 98765..."
                        className="w-full bg-[var(--subcard-bg)] border border-[var(--border-subtle)] focus:border-emerald-500 rounded-lg px-3 py-1.5 text-xs text-[var(--text-main)] outline-none"
                      />
                    </div>
                  </div>

                  <div className="space-y-1">
                    <label className="text-[10px] font-bold text-[var(--text-dim)] uppercase tracking-wider block">
                      Create Password *
                    </label>
                    <div className="relative">
                      <input
                        type={showPassword ? 'text' : 'password'}
                        value={regPassword}
                        onChange={(e) => setRegPassword(e.target.value)}
                        placeholder="At least 4 characters"
                        className="w-full bg-[var(--subcard-bg)] border border-[var(--border-subtle)] focus:border-emerald-500 rounded-lg pl-3 pr-8 py-1.5 text-xs text-[var(--text-main)] outline-none"
                        required
                        minLength={4}
                      />
                      <button
                        type="button"
                        onClick={() => setShowPassword(!showPassword)}
                        className="absolute right-2.5 top-2 text-[var(--text-dim)] hover:text-[var(--text-main)] cursor-pointer"
                      >
                        {showPassword ? <EyeOff className="h-3.5 w-3.5" /> : <Eye className="h-3.5 w-3.5" />}
                      </button>
                    </div>
                  </div>

                  <button
                    type="submit"
                    disabled={loading}
                    className="w-full py-2.5 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg font-bold text-xs flex items-center justify-center gap-2 transition cursor-pointer shadow-md shadow-emerald-950/20 mt-1"
                  >
                    <UserPlus className="h-3.5 w-3.5" />
                    <span>{loading ? 'Creating Account...' : 'Complete Registration & Sign In'}</span>
                  </button>

                  <p className="text-[11px] text-center text-[var(--text-muted)] pt-1">
                    Already registered?{' '}
                    <button
                      type="button"
                      onClick={() => setUserMode('LOGIN')}
                      className="font-bold text-emerald-400 hover:underline cursor-pointer"
                    >
                      Sign in here
                    </button>
                  </p>
                </form>
              )}

            </div>
          )}

          {/* ================= OFFICIAL ADMIN PORTAL ================= */}
          {activePortal === 'ADMIN' && (
            <div className="space-y-3.5">
              <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/25 text-rose-300 text-[11px] leading-relaxed space-y-1">
                <div className="flex items-center gap-1.5 font-bold text-rose-400">
                  <Lock className="h-3.5 w-3.5" />
                  <span>Restricted Authority Console</span>
                </div>
                <p className="text-[var(--text-muted)]">
                  Only authorized disaster management personnel (NDRF, SDRF, District Magistrates) possess valid administrative credentials. Local citizens should use the User / Citizen portal tab above.
                </p>
              </div>

              <form onSubmit={handleAdminLogin} className="space-y-3">
                <div className="space-y-1">
                  <label className="text-[10px] font-bold text-[var(--text-dim)] uppercase tracking-wider block">
                    Official Email ID or Officer Username
                  </label>
                  <div className="relative">
                    <User className="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-[var(--text-dim)]" />
                    <input
                      type="text"
                      value={adminEmail}
                      onChange={(e) => setAdminEmail(e.target.value)}
                      placeholder="commander@ner.gov.in"
                      className="w-full bg-[var(--subcard-bg)] border border-[var(--border-subtle)] focus:border-rose-500 rounded-lg pl-8 pr-3 py-2 text-xs text-[var(--text-main)] outline-none font-mono"
                      required
                      autoFocus
                    />
                  </div>
                </div>

                <div className="space-y-1">
                  <label className="text-[10px] font-bold text-[var(--text-dim)] uppercase tracking-wider block">
                    Official Password
                  </label>
                  <div className="relative">
                    <KeyRound className="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-[var(--text-dim)]" />
                    <input
                      type={showPassword ? 'text' : 'password'}
                      value={adminPassword}
                      onChange={(e) => setAdminPassword(e.target.value)}
                      placeholder="••••••••••••"
                      className="w-full bg-[var(--subcard-bg)] border border-[var(--border-subtle)] focus:border-rose-500 rounded-lg pl-8 pr-8 py-2 text-xs text-[var(--text-main)] outline-none font-mono"
                      required
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="absolute right-2.5 top-2.5 text-[var(--text-dim)] hover:text-[var(--text-main)] cursor-pointer"
                    >
                      {showPassword ? <EyeOff className="h-3.5 w-3.5" /> : <Eye className="h-3.5 w-3.5" />}
                    </button>
                  </div>
                </div>

                <button
                  type="submit"
                  disabled={loading}
                  className="w-full py-2.5 bg-rose-700 hover:bg-rose-600 text-white rounded-lg font-bold text-xs flex items-center justify-center gap-2 transition cursor-pointer shadow-md shadow-rose-950/20"
                >
                  <span>{loading ? 'Verifying Credentials...' : 'Authenticate & Enter Command Center'}</span>
                  <ArrowRight className="h-3.5 w-3.5" />
                </button>
              </form>

              <div className="pt-2 border-t border-[var(--border-subtle)] text-[10px] text-[var(--text-dim)] space-y-0.5">
                <span className="font-semibold text-[var(--text-muted)] block">Official Authority Testing ID:</span>
                <div className="flex flex-wrap items-center gap-2 font-mono text-[10px]">
                  <span>Email: <strong className="text-emerald-400">commander@ner.gov.in</strong></span>
                  <span>•</span>
                  <span>Password: <strong className="text-emerald-400">password123</strong></span>
                </div>
              </div>
            </div>
          )}

        </div>

        {/* Modal Footer */}
        <div className="px-5 py-3 bg-[var(--subcard-bg)] border-t border-[var(--border-subtle)] flex items-center justify-between text-[10px] text-[var(--text-dim)]">
          <span className="flex items-center gap-1">
            <PhoneCall className="h-3 w-3 text-emerald-500" />
            <span>Emergency Operations: 1070 / 112</span>
          </span>
          <span>NDMA Secure Portal</span>
        </div>

      </div>
    </div>
  );
}
