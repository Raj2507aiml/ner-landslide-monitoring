import React, { useState, useEffect } from 'react';
import {
  Activity,
  AlertTriangle,
  ShieldCheck,
  MapPin,
  Clock3,
  RefreshCw,
  Compass
} from 'lucide-react';
import { getIncidents } from '../services/incidentService';

const SEVERITY_BADGES = {
  CRITICAL: 'bg-rose-500/10 dark:bg-rose-950/30 text-rose-700 dark:text-rose-400 border-rose-500/40 animate-pulse',
  HIGH: 'bg-amber-500/10 dark:bg-amber-950/30 text-amber-700 dark:text-amber-400 border-amber-500/30',
  MODERATE: 'bg-sky-500/10 dark:bg-sky-950/30 text-sky-700 dark:text-sky-400 border-sky-500/30',
  LOW: 'bg-emerald-500/10 dark:bg-emerald-950/30 text-emerald-700 dark:text-emerald-400 border-emerald-500/30'
};

const STATUS_BADGES = {
  OPEN: 'bg-rose-500/10 dark:bg-rose-950/30 text-rose-700 dark:text-rose-400 border-rose-500/25',
  ACKNOWLEDGED: 'bg-amber-500/10 dark:bg-amber-950/30 text-amber-700 dark:text-amber-400 border-amber-500/25',
  IN_PROGRESS: 'bg-sky-500/10 dark:bg-sky-950/30 text-sky-700 dark:text-sky-400 border-sky-500/25',
  RESOLVED: 'bg-emerald-500/10 dark:bg-emerald-950/30 text-emerald-700 dark:text-emerald-400 border-emerald-500/25'
};

const ACTIVE_INCIDENT_STATUSES = [
  'OPEN',
  'ACKNOWLEDGED',
  'IN_PROGRESS'
];

export default function RecentAlertsPanel({
  refreshKey = 0,
  onLocateIncident = () => {}
}) {
  const [incidents, setIncidents] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  const fetchRecentIncidents = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const res = await getIncidents({ limit: 50 });
      if (res && res.ok && res.data) {
        const rawList = res.data.incidents || [];
        const activeList = rawList
          .filter(inc => ACTIVE_INCIDENT_STATUSES.includes(inc.status))
          .slice(0, 5);
        setIncidents(activeList);
      } else {
        setIncidents([]);
        setError(res?.error || 'Unable to retrieve recent incidents.');
      }
    } catch (err) {
      setIncidents([]);
      setError('Unable to connect to incident service.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchRecentIncidents();
  }, [refreshKey]);

  const formatDate = (dateStr) => {
    if (!dateStr) return 'N/A';
    try {
      const d = new Date(dateStr);
      if (isNaN(d.getTime())) return String(dateStr);
      return d.toLocaleString('en-US', {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        hour12: false
      });
    } catch {
      return String(dateStr);
    }
  };

  const handleLocate = (e, inc) => {
    e.stopPropagation();
    if (onLocateIncident && typeof inc.latitude === 'number' && typeof inc.longitude === 'number') {
      onLocateIncident({ lat: inc.latitude, lng: inc.longitude });
    }
  };

  return (
    <div className="bg-[var(--panel-bg)] backdrop-blur-md border border-[var(--border-subtle)] rounded-xl p-3.5 shadow-xs h-[420px] flex flex-col justify-between">
      
      {/* Panel Sub-Header */}
      <div className="flex items-center justify-between border-b border-[var(--border-subtle)] pb-2">
        <div className="flex items-center gap-2">
          <span className="text-xs font-bold text-[var(--text-main)] uppercase tracking-wider">
            Recent Alerts
          </span>
          <span className="text-[10px] px-2 py-0.5 rounded-full bg-amber-500/10 text-amber-500 border border-amber-500/20 font-mono font-semibold">
            {incidents.length} Active
          </span>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={fetchRecentIncidents}
            disabled={isLoading}
            title="Refresh recent incidents"
            className="p-1 rounded-md text-[var(--text-dim)] hover:text-[var(--text-main)] hover:bg-[var(--card-bg)] transition disabled:opacity-50 cursor-pointer"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${isLoading ? 'animate-spin text-emerald-500' : ''}`} />
          </button>
        </div>
      </div>

      {/* Main Content Area */}
      <div className="flex-1 overflow-y-auto my-1.5 pr-1 space-y-2">
        
        {/* Loading State */}
        {isLoading && incidents.length === 0 && (
          <div className="h-full flex flex-col items-center justify-center text-center p-4 space-y-2">
            <RefreshCw className="h-5 w-5 text-emerald-500 animate-spin" />
            <div className="space-y-0.5">
              <p className="text-xs text-[var(--text-main)] font-semibold">Synchronizing incident registry</p>
              <p className="text-[10px] text-[var(--text-muted)]">Awaiting telemetry feed...</p>
            </div>
          </div>
        )}

        {/* Error State */}
        {!isLoading && error && (
          <div className="h-full flex flex-col items-center justify-center text-center p-3 space-y-2 bg-rose-500/5 border border-rose-500/15 rounded-lg">
            <AlertTriangle className="h-5 w-5 text-rose-500" />
            <div className="space-y-0.5">
              <p className="text-xs font-semibold text-rose-500">Incident Feed Offline</p>
              <p className="text-[10px] text-[var(--text-muted)] max-w-[200px]">{error}</p>
            </div>
            <button
              onClick={fetchRecentIncidents}
              className="px-2.5 py-1 bg-[var(--card-bg)] hover:bg-[var(--subcard-bg)] text-[var(--text-main)] text-xs rounded border border-[var(--border-subtle)] font-medium transition cursor-pointer"
            >
              Retry
            </button>
          </div>
        )}

        {/* Empty State */}
        {!isLoading && !error && incidents.length === 0 && (
          <div className="h-full flex flex-col items-center justify-center text-center px-4 space-y-2">
            <div className="p-2 bg-emerald-500/10 text-emerald-500 rounded-full border border-emerald-500/20">
              <ShieldCheck className="h-5 w-5" />
            </div>
            <div className="space-y-0.5">
              <h4 className="text-xs font-semibold text-[var(--text-main)]">No active incidents</h4>
              <p className="text-[10px] text-[var(--text-muted)] leading-relaxed max-w-[200px]">
                Monitoring systems operational. Incidents log automatically upon severe hazard triggers.
              </p>
            </div>
          </div>
        )}

        {/* Dynamic Incidents List (Max 5) */}
        {!error && incidents.length > 0 && (
          <div className="space-y-2">
            {incidents.slice(0, 5).map((inc) => {
              const sevBadge = SEVERITY_BADGES[inc.severity] || SEVERITY_BADGES.LOW;
              const statusBadge = STATUS_BADGES[inc.status] || STATUS_BADGES.OPEN;

              return (
                <div
                  key={`alert-inc-${inc.id}`}
                  onClick={(e) => handleLocate(e, inc)}
                  className="bg-[var(--card-bg)] hover:bg-[var(--subcard-bg)] border border-[var(--border-subtle)] hover:border-[var(--border-strong)] rounded-lg p-2.5 transition space-y-1 text-xs shadow-xs cursor-pointer group"
                >
                  {/* Top Line: Code, Severity, Status */}
                  <div className="flex items-center justify-between gap-1">
                    <div className="flex items-center gap-2 min-w-0">
                      <div className={`p-1 rounded-md shrink-0 ${
                        inc.severity === 'CRITICAL' ? 'bg-rose-500/15 text-rose-500 border border-rose-500/30' :
                        inc.severity === 'HIGH' ? 'bg-amber-500/15 text-amber-500 border border-amber-500/30' :
                        'bg-sky-500/15 text-sky-500 border border-sky-500/30'
                      }`}>
                        <AlertTriangle className="h-3 w-3" />
                      </div>
                      <div className="truncate">
                        <span className="font-bold text-[var(--text-main)] text-xs block truncate group-hover:text-emerald-500 transition">
                          {inc.title ? inc.title.split(' - ')[0] : inc.incident_code}
                        </span>
                        <span className="text-[9px] text-[var(--text-dim)] font-mono">
                          {inc.incident_code}
                        </span>
                      </div>
                    </div>
                    <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded border uppercase shrink-0 ${sevBadge}`}>
                      {inc.severity}
                    </span>
                  </div>

                  {/* Bottom Line: Coordinates, Time, Locate Action */}
                  <div className="flex items-center justify-between text-[10px] text-[var(--text-dim)] pt-1 border-t border-[var(--border-subtle)]">
                    <div className="flex items-center gap-2 font-mono">
                      <span className="flex items-center gap-0.5">
                        <MapPin className="h-2.5 w-2.5 text-emerald-500 shrink-0" />
                        {inc.latitude?.toFixed(4)}°, {inc.longitude?.toFixed(4)}°
                      </span>
                      <span className="flex items-center gap-0.5 text-[var(--text-dim)]">
                        <Clock3 className="h-2.5 w-2.5 shrink-0" />
                        {formatDate(inc.created_at)}
                      </span>
                    </div>

                    <button
                      onClick={(e) => handleLocate(e, inc)}
                      title="Pinpoint incident coordinate on map"
                      className="flex items-center gap-1 px-1.5 py-0.5 bg-emerald-600/15 hover:bg-emerald-600/30 text-emerald-500 rounded border border-emerald-500/25 text-[9px] font-semibold transition cursor-pointer"
                    >
                      <Compass className="h-2.5 w-2.5" />
                      <span>Locate</span>
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}

      </div>

      {/* Technical Footer */}
      <div className="border-t border-[var(--border-subtle)] pt-2 mt-auto flex justify-between items-center text-[9px] text-[var(--text-dim)]">
        <span>Incident Registry:</span>
        <span className="font-mono text-[var(--text-muted)]">Phase 8 Operational</span>
      </div>

    </div>
  );
}
