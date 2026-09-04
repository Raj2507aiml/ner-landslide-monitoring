import React, { useState, useRef, useEffect } from 'react';
import {
  Shield,
  User,
  ChevronDown,
  LogOut,
  MapPin,
  CheckCircle2,
  PhoneCall
} from 'lucide-react';
import { USER_ROLES, logoutUser } from '../services/authService';

export default function UserRoleSelector({
  currentUser,
  onUserChange,
  onOpenLoginModal
}) {
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef(null);

  // Close dropdown on outside click
  useEffect(() => {
    const handleClickOutside = (e) => {
      if (containerRef.current && !containerRef.current.contains(e.target)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const isAdmin = currentUser?.role === USER_ROLES.ADMIN;
  const isCitizen = currentUser?.role === USER_ROLES.CITIZEN;

  const handleSignOut = () => {
    logoutUser();
    if (onUserChange) onUserChange(null);
    setIsOpen(false);
  };

  if (!currentUser) {
    return null; // Guest state handled by parent header buttons
  }

  return (
    <div className="relative inline-block text-left" ref={containerRef}>
      
      {/* Trigger Button */}
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className={`flex items-center gap-2 px-2.5 py-1 rounded-md border transition cursor-pointer text-xs font-semibold shadow-xs ${
          isAdmin
            ? 'bg-rose-500/10 border-rose-500/30 text-rose-300 hover:bg-rose-500/20'
            : 'bg-emerald-500/10 border-emerald-500/30 text-emerald-300 hover:bg-emerald-500/20'
        }`}
        title={`Signed in as ${currentUser.name} (${currentUser.role})`}
      >
        <span className="text-sm">{currentUser.avatar || (isAdmin ? '🛡️' : '👤')}</span>
        <div className="flex flex-col text-left leading-none hidden sm:flex">
          <span className={`text-[10px] font-bold tracking-wider uppercase truncate max-w-[120px] ${
            isAdmin ? 'text-rose-400' : 'text-emerald-400'
          }`}>
            {currentUser.name}
          </span>
          <span className="text-[9px] text-[var(--text-dim)] font-mono">
            {isAdmin ? 'OFFICIAL ADMIN' : 'PUBLIC CITIZEN'}
          </span>
        </div>
        <ChevronDown className="h-3 w-3 opacity-70 ml-0.5" />
      </button>

      {/* Dropdown Menu */}
      {isOpen && (
        <div className="absolute right-0 mt-2 w-72 bg-[var(--panel-bg)] border border-[var(--border-subtle)] rounded-xl shadow-2xl p-2.5 z-[2000] text-xs text-[var(--text-main)] animate-in fade-in zoom-in-95 duration-100 backdrop-blur-md">
          
          {/* User Profile Info Card */}
          <div className="p-2.5 bg-[var(--subcard-bg)] rounded-lg border border-[var(--border-subtle)] mb-2 space-y-1.5">
            <div className="flex items-center justify-between">
              <span className={`text-[9px] font-black uppercase px-2 py-0.5 rounded border ${
                isAdmin
                  ? 'bg-rose-500/20 text-rose-300 border-rose-500/40'
                  : 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40'
              }`}>
                {currentUser.badgeText || (isAdmin ? 'OFFICIAL ADMIN' : 'REGISTERED CITIZEN')}
              </span>
              {currentUser.state && (
                <span className="text-[9px] text-[var(--text-dim)] flex items-center gap-0.5">
                  <MapPin className="h-2.5 w-2.5" />
                  {currentUser.state}
                </span>
              )}
            </div>

            <p className="font-bold text-xs text-[var(--text-main)] truncate">
              {currentUser.name}
            </p>
            <p className="text-[10.5px] font-mono text-[var(--text-muted)] truncate">
              {currentUser.email}
            </p>
            {currentUser.designation && (
              <p className="text-[9.5px] text-[var(--text-dim)] truncate">
                {currentUser.designation}
              </p>
            )}
          </div>

          {/* User Sign Out Action - NO switch to admin option for regular citizens! */}
          <div className="space-y-1">
            <button
              onClick={handleSignOut}
              className="w-full text-left p-2 rounded-lg bg-rose-500/10 hover:bg-rose-500/20 border border-rose-500/25 text-rose-400 hover:text-rose-300 transition cursor-pointer flex items-center justify-between font-bold text-xs"
            >
              <div className="flex items-center gap-2">
                <LogOut className="h-3.5 w-3.5" />
                <span>Sign Out / Logout</span>
              </div>
              <span className="text-[9px] font-mono uppercase text-rose-400/70">Exit</span>
            </button>
          </div>

          {/* Footer Helpline */}
          <div className="mt-2 pt-2 border-t border-[var(--border-subtle)] flex items-center justify-between text-[9px] text-[var(--text-dim)]">
            <span className="flex items-center gap-1">
              <PhoneCall className="h-2.5 w-2.5 text-emerald-500" />
              <span>Helpline: 1070 / 112</span>
            </span>
            <span>NER Portal</span>
          </div>

        </div>
      )}

    </div>
  );
}
