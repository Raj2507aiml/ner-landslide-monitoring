import React, { useState, useMemo } from 'react';
import {
  X,
  MessageSquare,
  PhoneCall,
  Copy,
  Check,
  Shield,
  HeartPulse,
  AlertTriangle,
  Radio,
  MapPin,
  ExternalLink,
  Users,
  Search
} from 'lucide-react';
import {
  MOUNTAIN_SURVIVAL_GUIDELINES,
  EMERGENCY_SMS_TARGETS,
  buildEmergencySmsPayload,
  generateSmsUri,
  getOfflineFacilitiesByState
} from '../services/offlineEmergencyData';
import { useTranslation } from '../services/i18nService';

export default function EmergencySmsModal({
  isOpen,
  onClose,
  selectedLocation = null,
  sectorName = 'North Eastern Mountain Corridor',
  state = 'North East India',
  isOnline = true
}) {
  const { t } = useTranslation();
  const [activeTab, setActiveTab] = useState('sms'); // 'sms' | 'shelters' | 'firstaid'
  const [selectedTarget, setSelectedTarget] = useState('112');
  const [incidentType, setIncidentType] = useState('LANDSLIDE_BLOCKAGE');
  const [personsCount, setPersonsCount] = useState(2);
  const [injuriesCount, setInjuriesCount] = useState(0);
  const [customNote, setCustomNote] = useState('');
  const [isCopied, setIsCopied] = useState(false);

  // Offline Shelters Filter States
  const [shelterStateFilter, setShelterStateFilter] = useState('ALL');
  const [shelterTypeFilter, setShelterTypeFilter] = useState('ALL');
  const [shelterSearch, setShelterSearch] = useState('');

  // Generate live pre-formatted SMS message text
  const smsBodyText = useMemo(() => {
    return buildEmergencySmsPayload({
      lat: selectedLocation?.lat,
      lng: selectedLocation?.lng,
      sectorName,
      state,
      incidentType,
      personsAffected: personsCount,
      injuries: injuriesCount,
      additionalNote: customNote
    });
  }, [selectedLocation, sectorName, state, incidentType, personsCount, injuriesCount, customNote]);

  const smsUri = useMemo(() => {
    return generateSmsUri(selectedTarget, smsBodyText);
  }, [selectedTarget, smsBodyText]);

  // Copy SMS text to clipboard
  const handleCopyText = () => {
    if (navigator.clipboard) {
      navigator.clipboard.writeText(smsBodyText).then(() => {
        setIsCopied(true);
        setTimeout(() => setIsCopied(false), 2500);
      }).catch(() => {
        fallbackCopyText();
      });
    } else {
      fallbackCopyText();
    }
  };

  const fallbackCopyText = () => {
    try {
      const textarea = document.createElement('textarea');
      textarea.value = smsBodyText;
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand('copy');
      document.body.removeChild(textarea);
      setIsCopied(true);
      setTimeout(() => setIsCopied(false), 2500);
    } catch {
      alert('SMS text prepared! Please select and copy the text box.');
    }
  };

  // Filter offline shelters
  const filteredShelters = useMemo(() => {
    let list = getOfflineFacilitiesByState(shelterStateFilter, shelterTypeFilter);
    if (shelterSearch.trim()) {
      const q = shelterSearch.toLowerCase();
      list = list.filter(f => 
        f.name.toLowerCase().includes(q) || 
        f.district.toLowerCase().includes(q) || 
        f.corridor.toLowerCase().includes(q)
      );
    }
    return list;
  }, [shelterStateFilter, shelterTypeFilter, shelterSearch]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-[9999] flex items-center justify-center p-3 sm:p-4 bg-black/75 backdrop-blur-sm animate-in fade-in duration-150">
      <div className="relative w-full max-w-2xl max-h-[92vh] bg-[var(--card-bg)] border border-[var(--border-subtle)] rounded-2xl shadow-2xl flex flex-col overflow-hidden text-xs">
        
        {/* Header */}
        <div className="p-4 border-b border-[var(--border-subtle)] bg-gradient-to-r from-emerald-950/40 via-[var(--panel-bg)] to-rose-950/30 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-lg bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
              <Radio className="h-5 w-5 animate-pulse" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="font-bold text-sm sm:text-base text-[var(--text-main)]">
                  {t('offline_pwa_title', 'Offline Emergency Hub & 2G SMS Dispatch')}
                </h3>
                {!isOnline && (
                  <span className="text-[9px] font-black uppercase px-2 py-0.5 rounded bg-amber-500/20 text-amber-400 border border-amber-500/30">
                    📴 Offline Mode
                  </span>
                )}
              </div>
              <p className="text-[11px] text-[var(--text-muted)]">
                {t('offline_pwa_subtitle', 'Zero-data emergency protocol for North Eastern mountain corridors with spotty cellular coverage.')}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-[var(--text-dim)] hover:text-[var(--text-main)] hover:bg-[var(--subcard-bg)] transition cursor-pointer"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Tab Navigation */}
        <div className="flex border-b border-[var(--border-subtle)] bg-[var(--subcard-bg)] text-xs font-semibold">
          <button
            onClick={() => setActiveTab('sms')}
            className={`flex-1 py-2.5 px-3 flex items-center justify-center gap-1.5 border-b-2 transition cursor-pointer ${
              activeTab === 'sms'
                ? 'border-emerald-500 text-emerald-400 bg-[var(--card-bg)]'
                : 'border-transparent text-[var(--text-muted)] hover:text-[var(--text-main)]'
            }`}
          >
            <MessageSquare className="h-4 w-4" />
            <span>1-Click 2G SMS</span>
          </button>

          <button
            onClick={() => setActiveTab('shelters')}
            className={`flex-1 py-2.5 px-3 flex items-center justify-center gap-1.5 border-b-2 transition cursor-pointer ${
              activeTab === 'shelters'
                ? 'border-emerald-500 text-emerald-400 bg-[var(--card-bg)]'
                : 'border-transparent text-[var(--text-muted)] hover:text-[var(--text-main)]'
            }`}
          >
            <Shield className="h-4 w-4" />
            <span>Emergency Shelters (38)</span>
          </button>

          <button
            onClick={() => setActiveTab('firstaid')}
            className={`flex-1 py-2.5 px-3 flex items-center justify-center gap-1.5 border-b-2 transition cursor-pointer ${
              activeTab === 'firstaid'
                ? 'border-emerald-500 text-emerald-400 bg-[var(--card-bg)]'
                : 'border-transparent text-[var(--text-muted)] hover:text-[var(--text-main)]'
            }`}
          >
            <HeartPulse className="h-4 w-4" />
            <span>Mountain First-Aid</span>
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-4 sm:p-5 overflow-y-auto space-y-4 flex-1">
          
          {/* TAB 1: 1-Click 2G SMS GENERATOR */}
          {activeTab === 'sms' && (
            <div className="space-y-4">
              
              {/* How it works info banner */}
              <div className="p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-start gap-2.5 text-[11px] text-[var(--text-main)]">
                <Radio className="h-4 w-4 text-emerald-400 shrink-0 mt-0.5" />
                <div className="space-y-0.5">
                  <p className="font-semibold text-emerald-400">Works without Mobile Data / 4G / 5G Internet</p>
                  <p className="text-[10px] text-[var(--text-muted)] leading-relaxed">
                    Mountain corridors frequently lose mobile data. This generator creates standard 2G GSM cellular SMS messages pre-filled with your precise GPS coordinates, corridor name, and situation details.
                  </p>
                </div>
              </div>

              {/* Target Helpline Selection */}
              <div className="space-y-1.5">
                <label className="text-[10px] font-bold uppercase tracking-wider text-[var(--text-dim)]">
                  Select Dispatch Recipient (National / State / District)
                </label>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
                  {EMERGENCY_SMS_TARGETS.map(target => (
                    <button
                      key={target.number}
                      type="button"
                      onClick={() => setSelectedTarget(target.number)}
                      className={`p-2.5 rounded-xl border text-left transition cursor-pointer flex flex-col justify-between ${
                        selectedTarget === target.number
                          ? 'bg-emerald-500/15 border-emerald-500 text-emerald-400 font-bold'
                          : 'bg-[var(--subcard-bg)] border-[var(--border-subtle)] text-[var(--text-muted)] hover:border-[var(--border-strong)]'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <span className="text-sm font-black text-[var(--text-main)]">{target.number}</span>
                        <span className="text-[9px] px-1.5 py-0.2 rounded bg-[var(--card-bg)] border border-[var(--border-subtle)]">
                          {target.badge}
                        </span>
                      </div>
                      <span className="text-[10px] text-[var(--text-dim)] mt-1 truncate">{target.name}</span>
                    </button>
                  ))}
                </div>
              </div>

              {/* Situation & Details Form */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div className="space-y-1.5">
                  <label className="text-[10px] font-bold uppercase tracking-wider text-[var(--text-dim)]">
                    Hazard / Situation Type
                  </label>
                  <select
                    value={incidentType}
                    onChange={(e) => setIncidentType(e.target.value)}
                    className="w-full bg-[var(--subcard-bg)] border border-[var(--border-subtle)] rounded-lg p-2 text-xs text-[var(--text-main)] focus:outline-none focus:border-emerald-500"
                  >
                    <option value="LANDSLIDE_BLOCKAGE">Active Landslide / Road Blocked</option>
                    <option value="VEHICLE_STRANDED">Vehicles Stranded on Mountain Pass</option>
                    <option value="MEDICAL_EMERGENCY">Casualties / Urgent Medical Need</option>
                    <option value="FLASH_FLOOD">River Surge / Flash Flood Cutoff</option>
                  </select>
                </div>

                <div className="grid grid-cols-2 gap-2">
                  <div className="space-y-1.5">
                    <label className="text-[10px] font-bold uppercase tracking-wider text-[var(--text-dim)]">
                      Persons Affected
                    </label>
                    <input
                      type="number"
                      min="1"
                      max="100"
                      value={personsCount}
                      onChange={(e) => setPersonsCount(Math.max(1, parseInt(e.target.value) || 1))}
                      className="w-full bg-[var(--subcard-bg)] border border-[var(--border-subtle)] rounded-lg p-2 text-xs text-[var(--text-main)] focus:outline-none focus:border-emerald-500"
                    />
                  </div>
                  <div className="space-y-1.5">
                    <label className="text-[10px] font-bold uppercase tracking-wider text-[var(--text-dim)]">
                      Injuries Reported
                    </label>
                    <input
                      type="number"
                      min="0"
                      max="50"
                      value={injuriesCount}
                      onChange={(e) => setInjuriesCount(Math.max(0, parseInt(e.target.value) || 0))}
                      className="w-full bg-[var(--subcard-bg)] border border-[var(--border-subtle)] rounded-lg p-2 text-xs text-[var(--text-main)] focus:outline-none focus:border-emerald-500"
                    />
                  </div>
                </div>
              </div>

              {/* Location Reference */}
              <div className="p-2.5 rounded-lg bg-[var(--subcard-bg)] border border-[var(--border-subtle)] flex items-center justify-between text-[11px]">
                <div className="flex items-center gap-2">
                  <MapPin className="h-4 w-4 text-emerald-500 shrink-0" />
                  <span className="font-semibold text-[var(--text-main)]">{sectorName}</span>
                </div>
                <span className="font-mono text-[10px] text-emerald-400 font-bold">
                  {selectedLocation?.lat ? `${selectedLocation.lat.toFixed(4)}°N, ${selectedLocation.lng.toFixed(4)}°E` : 'Auto-detected via GPS'}
                </span>
              </div>

              {/* Pre-formatted SMS Preview Box */}
              <div className="space-y-1.5">
                <div className="flex items-center justify-between">
                  <label className="text-[10px] font-bold uppercase tracking-wider text-[var(--text-dim)]">
                    Pre-formatted GSM SMS Message (Ready for 2G Network)
                  </label>
                  <span className="text-[10px] text-[var(--text-dim)] font-mono">
                    {smsBodyText.length} chars
                  </span>
                </div>
                <pre className="p-3 rounded-xl bg-slate-950 text-emerald-300 font-mono text-[11px] leading-relaxed whitespace-pre-wrap border border-emerald-500/30 select-all shadow-inner">
                  {smsBodyText}
                </pre>
              </div>

              {/* Action Buttons */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 pt-2">
                <a
                  href={smsUri}
                  className="sm:col-span-2 px-4 py-2.5 bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs rounded-xl flex items-center justify-center gap-2 shadow-lg shadow-emerald-950/40 transition cursor-pointer text-center"
                >
                  <MessageSquare className="h-4 w-4" />
                  <span>📱 Send via 2G SMS ({selectedTarget})</span>
                </a>

                <button
                  onClick={handleCopyText}
                  className="px-3 py-2.5 bg-[var(--subcard-bg)] hover:bg-[var(--card-bg)] border border-[var(--border-subtle)] text-[var(--text-main)] font-semibold text-xs rounded-xl flex items-center justify-center gap-1.5 transition cursor-pointer shadow-xs"
                >
                  {isCopied ? <Check className="h-4 w-4 text-emerald-400" /> : <Copy className="h-4 w-4" />}
                  <span>{isCopied ? 'Copied to Clipboard!' : '📋 Copy SMS Text'}</span>
                </button>
              </div>

              {/* Direct Emergency Calls Fallback */}
              <div className="pt-2 border-t border-[var(--border-subtle)] flex flex-wrap items-center justify-between gap-2 text-[10px] text-[var(--text-muted)]">
                <span>Standard Voice Calls (Zero Data):</span>
                <div className="flex items-center gap-2">
                  <a href="tel:112" className="px-2.5 py-1 rounded bg-rose-600/20 text-rose-300 hover:text-white border border-rose-500/40 font-bold transition flex items-center gap-1">
                    <PhoneCall className="h-3 w-3 text-rose-400" />
                    <span>Call 112 (ERSS)</span>
                  </a>
                  <a href="tel:1070" className="px-2.5 py-1 rounded bg-rose-600/20 text-rose-300 hover:text-white border border-rose-500/40 font-bold transition flex items-center gap-1">
                    <PhoneCall className="h-3 w-3 text-rose-400" />
                    <span>Call 1070 (State EOC)</span>
                  </a>
                </div>
              </div>

            </div>
          )}

          {/* TAB 2: OFFLINE EMERGENCY SHELTERS */}
          {activeTab === 'shelters' && (
            <div className="space-y-3">
              <div className="flex flex-col sm:flex-row gap-2">
                <div className="relative flex-1">
                  <Search className="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-[var(--text-dim)]" />
                  <input
                    type="text"
                    value={shelterSearch}
                    onChange={(e) => setShelterSearch(e.target.value)}
                    placeholder="Search shelter, district, corridor..."
                    className="w-full pl-8 pr-3 py-1.5 bg-[var(--subcard-bg)] border border-[var(--border-subtle)] rounded-lg text-xs text-[var(--text-main)] focus:outline-none focus:border-emerald-500"
                  />
                </div>
                <select
                  value={shelterStateFilter}
                  onChange={(e) => setShelterStateFilter(e.target.value)}
                  className="bg-[var(--subcard-bg)] border border-[var(--border-subtle)] rounded-lg px-2 py-1.5 text-xs text-[var(--text-main)] focus:outline-none focus:border-emerald-500"
                >
                  <option value="ALL">All 8 States</option>
                  <option value="Assam">Assam</option>
                  <option value="Arunachal Pradesh">Arunachal Pradesh</option>
                  <option value="Meghalaya">Meghalaya</option>
                  <option value="Manipur">Manipur</option>
                  <option value="Mizoram">Mizoram</option>
                  <option value="Nagaland">Nagaland</option>
                  <option value="Sikkim">Sikkim</option>
                  <option value="Tripura">Tripura</option>
                </select>
                <select
                  value={shelterTypeFilter}
                  onChange={(e) => setShelterTypeFilter(e.target.value)}
                  className="bg-[var(--subcard-bg)] border border-[var(--border-subtle)] rounded-lg px-2 py-1.5 text-xs text-[var(--text-main)] focus:outline-none focus:border-emerald-500"
                >
                  <option value="ALL">All Facility Types</option>
                  <option value="SHELTER">🛡️ Emergency Shelters</option>
                  <option value="HOSPITAL">🏥 Hospitals & Clinics</option>
                  <option value="POLICE">🚔 Police Patrol</option>
                  <option value="CLEARANCE_UNIT">🚜 BRO Bases</option>
                </select>
              </div>

              <div className="space-y-2 max-h-[50vh] overflow-y-auto pr-1">
                {filteredShelters.length === 0 ? (
                  <p className="text-center py-6 text-[var(--text-dim)] italic">No facilities match your search filter.</p>
                ) : (
                  filteredShelters.map((fac) => (
                    <div
                      key={fac.id}
                      className="p-3 rounded-xl bg-[var(--subcard-bg)] border border-[var(--border-subtle)] space-y-1.5"
                    >
                      <div className="flex items-start justify-between gap-2">
                        <div>
                          <div className="flex items-center gap-1.5">
                            <span className="font-bold text-xs text-[var(--text-main)]">{fac.name}</span>
                          </div>
                          <span className="text-[10px] text-[var(--text-dim)]">{fac.district}, {fac.state} • {fac.corridor}</span>
                        </div>
                        <span className={`px-2 py-0.5 rounded text-[9px] font-bold uppercase shrink-0 border ${
                          fac.type === 'HOSPITAL' ? 'bg-rose-500/15 text-rose-400 border-rose-500/30' :
                          fac.type === 'SHELTER' ? 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30' :
                          fac.type === 'POLICE' ? 'bg-sky-500/15 text-sky-400 border-sky-500/30' :
                          'bg-amber-500/15 text-amber-400 border-amber-500/30'
                        }`}>
                          {fac.type.replace('_', ' ')}
                        </span>
                      </div>
                      <p className="text-[10px] text-[var(--text-muted)] leading-relaxed">{fac.description}</p>
                      <div className="flex items-center justify-between pt-1 border-t border-[var(--border-subtle)] text-[10px]">
                        <span className="font-mono text-[var(--text-dim)]">{fac.lat.toFixed(4)}°N, {fac.lng.toFixed(4)}°E</span>
                        <a
                          href={`tel:${fac.phone.split('/')[0].trim()}`}
                          className="font-bold text-emerald-400 hover:underline flex items-center gap-1"
                        >
                          <PhoneCall className="h-3 w-3" />
                          <span>{fac.phone}</span>
                        </a>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          )}

          {/* TAB 3: MOUNTAIN FIRST-AID & SURVIVAL */}
          {activeTab === 'firstaid' && (
            <div className="space-y-3">
              <div className="p-3 rounded-xl bg-amber-500/10 border border-amber-500/20 text-[11px] text-[var(--text-main)] flex items-start gap-2">
                <AlertTriangle className="h-4 w-4 text-amber-400 shrink-0 mt-0.5" />
                <p className="leading-relaxed">
                  These verified protocols are cached directly on your device. Follow these steps when medical personnel cannot reach your mountain sector due to road blockage.
                </p>
              </div>

              <div className="space-y-3">
                {MOUNTAIN_SURVIVAL_GUIDELINES.map((guide, idx) => (
                  <div
                    key={guide.id}
                    className="p-3.5 rounded-xl bg-[var(--subcard-bg)] border border-[var(--border-subtle)] space-y-2"
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className="h-5 w-5 rounded-full bg-emerald-500/20 text-emerald-400 flex items-center justify-center font-bold text-[10px]">
                          {idx + 1}
                        </span>
                        <h4 className="font-bold text-xs text-[var(--text-main)]">{guide.title}</h4>
                      </div>
                      <span className="text-[9px] font-semibold px-2 py-0.5 rounded bg-[var(--card-bg)] text-[var(--text-dim)] border border-[var(--border-subtle)]">
                        {guide.badge}
                      </span>
                    </div>
                    <p className="text-[10px] text-[var(--text-dim)] italic">{guide.summary}</p>
                    <ul className="space-y-1.5 pt-1 text-[11px] text-[var(--text-muted)]">
                      {guide.steps.map((step, sIdx) => (
                        <li key={sIdx} className="flex items-start gap-2 leading-relaxed">
                          <span className="text-emerald-500 font-bold shrink-0">•</span>
                          <span>{step}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                ))}
              </div>
            </div>
          )}

        </div>

        {/* Footer */}
        <div className="p-3 bg-[var(--subcard-bg)] border-t border-[var(--border-subtle)] flex items-center justify-between text-[11px] text-[var(--text-dim)]">
          <span className="flex items-center gap-1.5 font-medium">
            <Radio className="h-3.5 w-3.5 text-emerald-400" />
            <span>PWA Offline Cache Active (ner-safety-cache-v1)</span>
          </span>
          <button
            onClick={onClose}
            className="px-3 py-1 bg-[var(--card-bg)] hover:bg-[var(--panel-bg)] text-[var(--text-main)] border border-[var(--border-subtle)] rounded-lg font-semibold transition cursor-pointer"
          >
            Close
          </button>
        </div>

      </div>
    </div>
  );
}
