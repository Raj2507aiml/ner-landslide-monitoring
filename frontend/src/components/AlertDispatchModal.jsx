import React, { useState, useEffect } from 'react';
import {
  X,
  Send,
  MessageSquare,
  Smartphone,
  Copy,
  Check,
  ShieldAlert,
  Radio,
  Clock3,
  Users,
  AlertTriangle,
  FileText,
  CheckCircle2,
  ExternalLink
} from 'lucide-react';
import {
  RECIPIENT_AGENCIES,
  formatEmergencyAlertText,
  formatWhatsAppUrl,
  formatSmsUrl,
  formatNdmaBulletin,
  recordDispatch,
  getDispatchHistory
} from '../services/alertDispatchService';

export default function AlertDispatchModal({
  isOpen,
  onClose,
  alertData = {}
}) {
  const [targetAgency, setTargetAgency] = useState('ALL');
  const [customPhone, setCustomPhone] = useState('');
  const [activeTab, setActiveTab] = useState('whatsapp'); // 'whatsapp' | 'sms' | 'telegram' | 'ndma'
  const [copied, setCopied] = useState(false);
  const [dispatchSuccess, setDispatchSuccess] = useState(null);
  const [history, setHistory] = useState([]);

  useEffect(() => {
    if (isOpen) {
      setHistory(getDispatchHistory());
      setDispatchSuccess(null);
      setCopied(false);
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const fullData = {
    ...alertData,
    targetAgency
  };

  const alertText = activeTab === 'ndma' 
    ? formatNdmaBulletin(fullData)
    : formatEmergencyAlertText(fullData);

  const handleCopy = () => {
    navigator.clipboard.writeText(alertText);
    setCopied(true);
    setTimeout(() => setCopied(false), 2500);

    // Record copy as a manual dispatch
    const entry = recordDispatch({
      channel: activeTab.toUpperCase(),
      agency: targetAgency,
      location: alertData.locationName || `${alertData.lat?.toFixed(2)}, ${alertData.lng?.toFixed(2)}`,
      warningLevel: alertData.warningLevel || 'ALERT',
      status: 'COPIED_TO_CLIPBOARD'
    });
    if (entry) setHistory(prev => [entry, ...prev]);
    setDispatchSuccess(`Alert copied to clipboard and recorded in session dispatch logs.`);
  };

  const handleDispatchChannel = (channel) => {
    let url = '';
    if (channel === 'whatsapp') {
      url = formatWhatsAppUrl(alertText, customPhone);
    } else if (channel === 'sms') {
      url = formatSmsUrl(alertText, customPhone);
    }

    if (url) {
      window.open(url, '_blank', 'noopener,noreferrer');
    }

    const entry = recordDispatch({
      channel: channel.toUpperCase(),
      agency: targetAgency,
      recipient: customPhone || 'Broadcast Group',
      location: alertData.locationName || `${alertData.lat?.toFixed(2)}, ${alertData.lng?.toFixed(2)}`,
      warningLevel: alertData.warningLevel || 'ALERT',
      status: 'TRANSMITTED'
    });

    if (entry) setHistory(prev => [entry, ...prev]);
    setDispatchSuccess(`Alert transmitted via ${channel.toUpperCase()} and logged to audit trail.`);
  };

  const level = alertData.warningLevel || 'ALERT';
  const levelBadgeColor =
    level === 'CRITICAL' || level === 'EMERGENCY'
      ? 'bg-rose-500/20 text-rose-400 border-rose-500/40'
      : level === 'WARNING' || level === 'ALERT'
      ? 'bg-orange-500/20 text-orange-400 border-orange-500/40'
      : 'bg-amber-500/20 text-amber-400 border-amber-500/40';

  return (
    <div className="fixed inset-0 z-[2000] flex items-center justify-center p-3 bg-black/60 backdrop-blur-xs animate-in fade-in duration-150">
      <div className="bg-[var(--panel-bg)] border border-[var(--border-subtle)] rounded-xl shadow-2xl w-full max-w-2xl max-h-[90vh] flex flex-col overflow-hidden text-[var(--text-main)]">
        
        {/* Modal Header */}
        <div className="px-4 py-3 bg-[var(--card-bg)] border-b border-[var(--border-subtle)] flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="p-1.5 rounded-lg bg-rose-500/15 border border-rose-500/30 text-rose-500 animate-pulse">
              <Radio className="h-4 w-4" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="font-bold text-xs sm:text-sm text-[var(--text-main)] uppercase tracking-wider">
                  Emergency Alert Dispatcher
                </h3>
                <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded border ${levelBadgeColor}`}>
                  {level}
                </span>
              </div>
              <p className="text-[10px] text-[var(--text-muted)]">
                Multi-Channel Incident Broadcast to Response Authorities
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-[var(--text-muted)] hover:text-[var(--text-main)] hover:bg-[var(--subcard-bg)] transition"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-4 space-y-4 overflow-y-auto flex-1 text-xs">
          
          {/* Target Agency Selector */}
          <div className="space-y-1.5">
            <label className="text-[10px] font-bold text-[var(--text-dim)] uppercase tracking-wider flex items-center gap-1">
              <Users className="h-3 w-3 text-emerald-500" />
              <span>Target Authority / Agency</span>
            </label>
            <select
              value={targetAgency}
              onChange={(e) => setTargetAgency(e.target.value)}
              className="w-full bg-[var(--subcard-bg)] border border-[var(--border-subtle)] rounded-lg p-2 text-xs text-[var(--text-main)] outline-none focus:border-emerald-500 font-medium"
            >
              {RECIPIENT_AGENCIES.map(agency => (
                <option key={agency.id} value={agency.id}>
                  {agency.name}
                </option>
              ))}
            </select>
          </div>

          {/* Optional Phone Number */}
          <div className="space-y-1">
            <div className="flex justify-between items-center">
              <label className="text-[10px] font-bold text-[var(--text-dim)] uppercase tracking-wider">
                Direct Recipient / Group Mobile (Optional)
              </label>
              <span className="text-[9px] text-[var(--text-muted)]">Leave blank for default WhatsApp/SMS broadcast</span>
            </div>
            <input
              type="text"
              placeholder="+91 98765 43210 (or keep blank for general broadcast)"
              value={customPhone}
              onChange={(e) => setCustomPhone(e.target.value)}
              className="w-full bg-[var(--subcard-bg)] border border-[var(--border-subtle)] rounded-lg px-2.5 py-1.5 text-xs text-[var(--text-main)] placeholder-[var(--text-dim)] outline-none focus:border-emerald-500 font-mono"
            />
          </div>

          {/* Channel Selector Tabs */}
          <div className="space-y-2">
            <div className="flex border-b border-[var(--border-subtle)] gap-1 text-[11px] font-bold">
              <button
                onClick={() => setActiveTab('whatsapp')}
                className={`flex items-center gap-1.5 px-3 py-1.5 border-b-2 transition cursor-pointer ${
                  activeTab === 'whatsapp'
                    ? 'border-emerald-500 text-emerald-400 bg-emerald-500/10 rounded-t'
                    : 'border-transparent text-[var(--text-muted)] hover:text-[var(--text-main)]'
                }`}
              >
                <MessageSquare className="h-3.5 w-3.5 text-emerald-400" />
                <span>WhatsApp</span>
              </button>

              <button
                onClick={() => setActiveTab('sms')}
                className={`flex items-center gap-1.5 px-3 py-1.5 border-b-2 transition cursor-pointer ${
                  activeTab === 'sms'
                    ? 'border-sky-500 text-sky-400 bg-sky-500/10 rounded-t'
                    : 'border-transparent text-[var(--text-muted)] hover:text-[var(--text-main)]'
                }`}
              >
                <Smartphone className="h-3.5 w-3.5 text-sky-400" />
                <span>Cellular SMS</span>
              </button>

              <button
                onClick={() => setActiveTab('telegram')}
                className={`flex items-center gap-1.5 px-3 py-1.5 border-b-2 transition cursor-pointer ${
                  activeTab === 'telegram'
                    ? 'border-blue-500 text-blue-400 bg-blue-500/10 rounded-t'
                    : 'border-transparent text-[var(--text-muted)] hover:text-[var(--text-main)]'
                }`}
              >
                <Send className="h-3.5 w-3.5 text-blue-400" />
                <span>Telegram / Bot</span>
              </button>

              <button
                onClick={() => setActiveTab('ndma')}
                className={`flex items-center gap-1.5 px-3 py-1.5 border-b-2 transition cursor-pointer ${
                  activeTab === 'ndma'
                    ? 'border-amber-500 text-amber-400 bg-amber-500/10 rounded-t'
                    : 'border-transparent text-[var(--text-muted)] hover:text-[var(--text-main)]'
                }`}
              >
                <FileText className="h-3.5 w-3.5 text-amber-400" />
                <span>NDMA SITREP Format</span>
              </button>
            </div>

            {/* Alert Message Preview Box */}
            <div className="relative bg-[var(--subcard-bg)] border border-[var(--border-subtle)] rounded-lg p-3 font-mono text-[10px] text-[var(--text-main)] whitespace-pre-wrap leading-relaxed max-h-48 overflow-y-auto">
              {alertText}
            </div>
          </div>

          {/* Feedback message */}
          {dispatchSuccess && (
            <div className="p-2.5 rounded-lg bg-emerald-500/10 border border-emerald-500/25 text-emerald-400 text-[10px] flex items-center gap-2">
              <CheckCircle2 className="h-3.5 w-3.5 shrink-0" />
              <span>{dispatchSuccess}</span>
            </div>
          )}

          {/* Action Trigger Buttons */}
          <div className="flex flex-wrap items-center justify-between gap-2 pt-1 border-t border-[var(--border-subtle)]">
            <button
              onClick={handleCopy}
              className="px-3 py-1.5 bg-[var(--card-bg)] hover:bg-[var(--subcard-bg)] border border-[var(--border-subtle)] text-[var(--text-main)] rounded-lg font-bold flex items-center gap-1.5 transition cursor-pointer text-xs"
            >
              {copied ? <Check className="h-3.5 w-3.5 text-emerald-400" /> : <Copy className="h-3.5 w-3.5" />}
              <span>{copied ? 'Copied Bulletin!' : 'Copy Formatted Bulletin'}</span>
            </button>

            <div className="flex gap-2">
              {activeTab === 'whatsapp' && (
                <button
                  onClick={() => handleDispatchChannel('whatsapp')}
                  className="px-4 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg font-bold flex items-center gap-1.5 transition cursor-pointer text-xs shadow-md shadow-emerald-950/20"
                >
                  <MessageSquare className="h-3.5 w-3.5" />
                  <span>Launch WhatsApp Dispatch</span>
                  <ExternalLink className="h-3 w-3 opacity-70" />
                </button>
              )}

              {activeTab === 'sms' && (
                <button
                  onClick={() => handleDispatchChannel('sms')}
                  className="px-4 py-1.5 bg-sky-600 hover:bg-sky-500 text-white rounded-lg font-bold flex items-center gap-1.5 transition cursor-pointer text-xs shadow-md shadow-sky-950/20"
                >
                  <Smartphone className="h-3.5 w-3.5" />
                  <span>Launch SMS Dispatch</span>
                  <ExternalLink className="h-3 w-3 opacity-70" />
                </button>
              )}

              {(activeTab === 'telegram' || activeTab === 'ndma') && (
                <button
                  onClick={handleCopy}
                  className="px-4 py-1.5 bg-amber-600 hover:bg-amber-500 text-white rounded-lg font-bold flex items-center gap-1.5 transition cursor-pointer text-xs shadow-md shadow-amber-950/20"
                >
                  <Copy className="h-3.5 w-3.5" />
                  <span>Copy for Broadcast Channel</span>
                </button>
              )}
            </div>
          </div>

          {/* Session Dispatch Log */}
          {history.length > 0 && (
            <div className="border-t border-[var(--border-subtle)] pt-3 space-y-1.5">
              <div className="flex justify-between items-center text-[10px] text-[var(--text-dim)] font-bold uppercase tracking-wider">
                <span className="flex items-center gap-1">
                  <Clock3 className="h-3 w-3" />
                  <span>Session Transmission History</span>
                </span>
                <span className="font-mono">{history.length} Logged</span>
              </div>

              <div className="divide-y divide-[var(--border-subtle)]/40 max-h-24 overflow-y-auto rounded border border-[var(--border-subtle)] bg-[var(--subcard-bg)] text-[9px]">
                {history.map((h) => (
                  <div key={h.id} className="p-1.5 flex justify-between items-center">
                    <div className="flex items-center gap-1.5">
                      <span className="font-mono font-bold text-emerald-400">{h.channel}</span>
                      <span className="text-[var(--text-muted)] truncate max-w-[150px]">{h.agency}</span>
                    </div>
                    <div className="flex items-center gap-2 font-mono text-[var(--text-dim)]">
                      <span>{new Date(h.timestamp).toLocaleTimeString()}</span>
                      <span className="text-emerald-400 font-bold">✓ {h.status}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

        </div>
      </div>
    </div>
  );
}
