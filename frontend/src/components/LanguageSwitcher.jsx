import React, { useState, useRef, useEffect } from 'react';
import { Languages, Check, ChevronDown } from 'lucide-react';
import { useTranslation, SUPPORTED_LANGUAGES } from '../services/i18nService';

export default function LanguageSwitcher({ compact = false, className = '' }) {
  const { lang, setLang } = useTranslation();
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef(null);

  const currentLangObj = SUPPORTED_LANGUAGES.find(l => l.code === lang) || SUPPORTED_LANGUAGES[0];

  // Close dropdown on outside click
  useEffect(() => {
    function handleClickOutside(event) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleSelect = (code) => {
    setLang(code);
    setIsOpen(false);
  };

  return (
    <div className={`relative inline-block text-left ${className}`} ref={dropdownRef}>
      {/* Switcher Trigger Button */}
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className={`flex items-center gap-1.5 px-2.5 py-1 rounded-md border border-[var(--border-subtle)] bg-[var(--card-bg)] text-[var(--text-main)] hover:border-[var(--border-strong)] transition cursor-pointer text-xs font-semibold shadow-xs ${
          isOpen ? 'ring-2 ring-emerald-500/40 border-emerald-500' : ''
        }`}
        title={`Current Language: ${currentLangObj.native} (${currentLangObj.name}) - Click to switch regional language`}
        aria-haspopup="true"
        aria-expanded={isOpen}
      >
        <Languages className="h-3.5 w-3.5 text-emerald-500 shrink-0" />
        <span className="font-bold text-xs">{currentLangObj.native}</span>
        {!compact && (
          <span className="hidden xl:inline text-[11px] text-[var(--text-dim)]">
            ({currentLangObj.code.toUpperCase()})
          </span>
        )}
        <ChevronDown className={`h-3 w-3 text-[var(--text-dim)] transition-transform duration-200 ${isOpen ? 'rotate-180' : ''}`} />
      </button>

      {/* Language Selection Dropdown Menu */}
      {isOpen && (
        <div className="absolute right-0 mt-1.5 w-72 sm:w-80 rounded-xl bg-[var(--panel-bg)] border border-[var(--border-strong)] shadow-2xl z-[9999] overflow-hidden backdrop-blur-xl animate-in fade-in zoom-in-95 duration-150">
          <div className="p-2.5 bg-[var(--subcard-bg)] border-b border-[var(--border-subtle)]">
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-black uppercase tracking-wider text-[var(--text-dim)] flex items-center gap-1.5">
                <Languages className="h-3 w-3 text-emerald-400" />
                <span>NER Regional Language / স্থানীয় ভাষা</span>
              </span>
              <span className="text-[9px] px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-mono font-bold">
                6 Bridge Dialects
              </span>
            </div>
            <p className="text-[10px] text-[var(--text-muted)] mt-1 leading-tight">
              Select your native or bridge language across the 8 North Eastern states for instant advisories & voice alerts.
            </p>
          </div>

          <div className="py-1 max-h-80 overflow-y-auto divide-y divide-[var(--border-subtle)]/40">
            {SUPPORTED_LANGUAGES.map((item) => {
              const isSelected = item.code === lang;
              return (
                <button
                  key={item.code}
                  type="button"
                  onClick={() => handleSelect(item.code)}
                  className={`w-full text-left px-3.5 py-2.5 flex items-start justify-between gap-3 transition cursor-pointer hover:bg-[var(--card-bg)] group ${
                    isSelected ? 'bg-emerald-500/10 font-semibold' : ''
                  }`}
                >
                  <div className="min-w-0 space-y-0.5">
                    <div className="flex items-center gap-2">
                      <span className={`text-xs font-bold ${isSelected ? 'text-emerald-400' : 'text-[var(--text-main)] group-hover:text-emerald-400'}`}>
                        {item.native}
                      </span>
                      <span className="text-[10px] text-[var(--text-dim)] font-normal">
                        ({item.name})
                      </span>
                      <span className="text-[9px] px-1.5 py-0.2 rounded bg-[var(--subcard-bg)] text-[var(--text-dim)] border border-[var(--border-subtle)]">
                        {item.code.toUpperCase()}
                      </span>
                    </div>

                    <div className="text-[10px] text-emerald-500/90 font-medium truncate">
                      {item.status}
                    </div>

                    <div className="text-[9.5px] text-[var(--text-muted)] leading-tight">
                      {item.bridgeRole}
                    </div>
                  </div>

                  {isSelected ? (
                    <div className="p-1 rounded-full bg-emerald-500/20 text-emerald-400 shrink-0 mt-1">
                      <Check className="h-3 w-3" />
                    </div>
                  ) : (
                    <span className="text-[10px] text-[var(--text-dim)] group-hover:text-emerald-400 shrink-0 mt-1">
                      Select
                    </span>
                  )}
                </button>
              );
            })}
          </div>

          <div className="p-2 bg-[var(--subcard-bg)]/80 border-t border-[var(--border-subtle)] text-[9.5px] text-[var(--text-dim)] text-center">
            Zero network delay · Audio & visual advisories update immediately
          </div>
        </div>
      )}
    </div>
  );
}
