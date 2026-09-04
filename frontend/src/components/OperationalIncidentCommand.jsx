import React, { useState, useEffect } from 'react';
import {
  Siren,
  ShieldAlert,
  AlertTriangle,
  CheckCircle2,
  Clock3,
  Activity,
  MapPin,
  RefreshCw,
  PlayCircle,
  CheckCheck,
  Eye,
  ClipboardList,
  Layers,
  ChevronRight,
  Info,
  Calendar,
  AlertOctagon,
  Radio,
  TrafficCone,
  Compass
} from 'lucide-react';
import {
  getIncidents,
  getIncidentById,
  acknowledgeIncident,
  startIncidentResponse,
  resolveIncident
} from '../services/incidentService';
import AlertDispatchModal from './AlertDispatchModal';

const SEVERITY_CONFIG = {
  LOW: {
    label: 'LOW',
    badge: 'bg-emerald-500/10 dark:bg-emerald-950/30 border-emerald-500/30 text-emerald-700 dark:text-emerald-400',
    dot: 'bg-emerald-500 dark:bg-emerald-400'
  },
  MODERATE: {
    label: 'MODERATE',
    badge: 'bg-sky-500/10 dark:bg-sky-950/30 border-sky-500/30 text-sky-700 dark:text-sky-400',
    dot: 'bg-sky-500 dark:bg-sky-400'
  },
  HIGH: {
    label: 'HIGH',
    badge: 'bg-amber-500/10 dark:bg-amber-950/30 border-amber-500/30 text-amber-700 dark:text-amber-400',
    dot: 'bg-amber-500 dark:bg-amber-400'
  },
  CRITICAL: {
    label: 'CRITICAL',
    badge: 'bg-rose-500/10 dark:bg-rose-950/30 border-rose-500/40 text-rose-700 dark:text-rose-400 animate-pulse',
    dot: 'bg-rose-500 dark:bg-rose-400'
  }
};

const STATUS_CONFIG = {
  OPEN: {
    label: 'OPEN',
    badge: 'bg-rose-500/10 dark:bg-rose-950/30 text-rose-700 dark:text-rose-300 border-rose-500/30',
    icon: AlertTriangle
  },
  ACKNOWLEDGED: {
    label: 'ACKNOWLEDGED',
    badge: 'bg-amber-500/10 dark:bg-amber-950/30 text-amber-700 dark:text-amber-300 border-amber-500/30',
    icon: Eye
  },
  IN_PROGRESS: {
    label: 'IN PROGRESS',
    badge: 'bg-sky-500/10 dark:bg-sky-950/30 text-sky-700 dark:text-sky-300 border-sky-500/30',
    icon: Activity
  },
  RESOLVED: {
    label: 'RESOLVED',
    badge: 'bg-emerald-500/10 dark:bg-emerald-950/30 text-emerald-700 dark:text-emerald-300 border-emerald-500/30',
    icon: CheckCircle2
  }
};

export default function OperationalIncidentCommand({
  onLocateIncident,
  selectedLocation
}) {
  const [incidents, setIncidents] = useState([]);
  const [totalCount, setTotalCount] = useState(0);
  const [selectedIncident, setSelectedIncident] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  // Filters
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [severityFilter, setSeverityFilter] = useState('ALL');

  // Lifecycle Action State
  const [actionLoading, setActionLoading] = useState(false);
  const [actionError, setActionError] = useState(null);

  // Emergency Alert Dispatch Modal State
  const [isDispatchModalOpen, setIsDispatchModalOpen] = useState(false);
  const [dispatchIncidentData, setDispatchIncidentData] = useState(null);

  const handleOpenDispatch = (incident) => {
    if (!incident) return;
    setDispatchIncidentData({
      locationName: incident.title || `Incident #${incident.incident_id || incident.id}`,
      lat: incident.latitude,
      lng: incident.longitude,
      warningLevel: incident.severity === 'CRITICAL' ? 'EMERGENCY' : incident.severity,
      riskScore: incident.risk_score || incident.evidence_snapshot?.risk_score,
      rainfallMm: incident.evidence_snapshot?.rainfall?.precipitation_mm,
      roadStatus: incident.road_disruption_status,
      incidentTitle: incident.description || incident.title
    });
    setIsDispatchModalOpen(true);
  };

  const fetchIncidentsList = async (currentStatus = statusFilter, currentSeverity = severityFilter) => {
    setIsLoading(true);
    setError(null);
    try {
      const res = await getIncidents({
        status: currentStatus,
        severity: currentSeverity,
        limit: 100
      });

      if (res.ok && res.data) {
        const list = res.data.incidents || [];
        setIncidents(list);
        setTotalCount(res.data.total || list.length);

        // Keep or select incident
        if (selectedIncident) {
          const updated = list.find(item => item.id === selectedIncident.id);
          if (updated) {
            setSelectedIncident(updated);
          } else if (list.length > 0) {
            setSelectedIncident(list[0]);
          } else {
            setSelectedIncident(null);
          }
        } else if (list.length > 0) {
          setSelectedIncident(list[0]);
        } else {
          setSelectedIncident(null);
        }
      } else {
        setIncidents([]);
        setTotalCount(0);
        setError(res.error || 'Unable to load operational incidents.');
      }
    } catch (err) {
      setIncidents([]);
      setTotalCount(0);
      setError('Unable to load operational incidents.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchIncidentsList(statusFilter, severityFilter);
  }, [statusFilter, severityFilter]);

  // Handle Lifecycle Action
  const handleLifecycleAction = async (actionType) => {
    if (!selectedIncident) return;
    setActionLoading(true);
    setActionError(null);

    try {
      let res;
      if (actionType === 'acknowledge') {
        res = await acknowledgeIncident(selectedIncident.id);
      } else if (actionType === 'start-response') {
        res = await startIncidentResponse(selectedIncident.id);
      } else if (actionType === 'resolve') {
        res = await resolveIncident(selectedIncident.id);
      }

      if (res && res.ok && res.data) {
        setSelectedIncident(res.data);
        await fetchIncidentsList(statusFilter, severityFilter);
      } else {
        setActionError(res?.error || `Failed to perform ${actionType} action.`);
      }
    } catch (err) {
      setActionError(`Failed to perform ${actionType} action.`);
    } finally {
      setActionLoading(false);
    }
  };

  // Summary counts derived from current list
  const openCount = incidents.filter(i => i.status === 'OPEN').length;
  const ackCount = incidents.filter(i => i.status === 'ACKNOWLEDGED').length;
  const inProgCount = incidents.filter(i => i.status === 'IN_PROGRESS').length;
  const resolvedCount = incidents.filter(i => i.status === 'RESOLVED').length;

  const formatDate = (dateStr) => {
    if (!dateStr) return 'N/A';
    try {
      const d = new Date(dateStr);
      return d.toLocaleString('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: false
      });
    } catch {
      return dateStr;
    }
  };

  return (
    <div className="bg-[var(--panel-bg)] backdrop-blur-md border border-[var(--border-subtle)] rounded-xl p-4 sm:p-5 shadow-md space-y-4">
      
      {/* SECTION A — INCIDENT COMMAND HEADER & SUMMARY STATS */}
      <div className="space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-2.5 border-b border-[var(--border-subtle)] pb-3">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-500">
              <Siren className="h-5 w-5 animate-pulse" />
            </div>
            <div>
              <h3 className="text-sm sm:text-base font-bold text-[var(--text-main)] tracking-tight flex items-center gap-2">
                Operational Incident Command
              </h3>
              <p className="text-[11px] text-[var(--text-muted)]">
                Active incident monitoring and response lifecycle management.
              </p>
            </div>
          </div>

          <button
            onClick={() => fetchIncidentsList(statusFilter, severityFilter)}
            disabled={isLoading}
            className="flex items-center gap-1.5 px-2.5 py-1 bg-[var(--card-bg)] hover:bg-[var(--subcard-bg)] text-[var(--text-main)] rounded-lg border border-[var(--border-subtle)] text-xs font-medium transition cursor-pointer disabled:opacity-50"
          >
            <RefreshCw className={`h-3 w-3 ${isLoading ? 'animate-spin text-emerald-500' : ''}`} />
            <span>Refresh</span>
          </button>
        </div>

        {/* Summary Metric Badges */}
        <div className="grid grid-cols-2 sm:grid-cols-5 gap-2 text-xs">
          <div className="bg-[var(--card-bg)] p-2 rounded-lg border border-[var(--border-subtle)] flex items-center justify-between">
            <span className="text-[var(--text-dim)] text-[11px]">Total</span>
            <span className="font-mono font-bold text-[var(--text-main)] text-xs">{totalCount}</span>
          </div>
          <div className="bg-[var(--card-bg)] p-2 rounded-lg border border-[var(--border-subtle)] flex items-center justify-between">
            <span className="text-red-500 flex items-center gap-1 text-[11px]">
              <span className="h-1.5 w-1.5 rounded-full bg-red-500 animate-ping"></span>
              Open
            </span>
            <span className="font-mono font-bold text-red-500 text-xs">{openCount}</span>
          </div>
          <div className="bg-[var(--card-bg)] p-2 rounded-lg border border-[var(--border-subtle)] flex items-center justify-between">
            <span className="text-amber-500 text-[11px]">Acknowledged</span>
            <span className="font-mono font-bold text-amber-500 text-xs">{ackCount}</span>
          </div>
          <div className="bg-[var(--card-bg)] p-2 rounded-lg border border-[var(--border-subtle)] flex items-center justify-between">
            <span className="text-sky-500 text-[11px]">In Progress</span>
            <span className="font-mono font-bold text-sky-500 text-xs">{inProgCount}</span>
          </div>
          <div className="bg-[var(--card-bg)] p-2 rounded-lg border border-[var(--border-subtle)] flex items-center justify-between">
            <span className="text-emerald-500 text-[11px]">Resolved</span>
            <span className="font-mono font-bold text-emerald-500 text-xs">{resolvedCount}</span>
          </div>
        </div>
      </div>

      {/* SECTION B — FILTERS */}
      <div className="flex flex-wrap items-center justify-between gap-2.5 bg-[var(--card-bg)] p-2.5 rounded-lg border border-[var(--border-subtle)] text-xs">
        <div className="flex flex-wrap items-center gap-3">
          
          {/* Status Filter */}
          <div className="flex items-center gap-2">
            <span className="text-[var(--text-dim)] font-medium text-[11px]">Status:</span>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="bg-[var(--subcard-bg)] border border-[var(--border-subtle)] text-[var(--text-main)] rounded px-2 py-0.5 text-xs focus:outline-none focus:border-emerald-500 cursor-pointer font-medium"
            >
              <option value="ALL">All Statuses</option>
              <option value="OPEN">Open</option>
              <option value="ACKNOWLEDGED">Acknowledged</option>
              <option value="IN_PROGRESS">In Progress</option>
              <option value="RESOLVED">Resolved</option>
            </select>
          </div>

          {/* Severity Filter */}
          <div className="flex items-center gap-2">
            <span className="text-[var(--text-dim)] font-medium text-[11px]">Severity:</span>
            <select
              value={severityFilter}
              onChange={(e) => setSeverityFilter(e.target.value)}
              className="bg-[var(--subcard-bg)] border border-[var(--border-subtle)] text-[var(--text-main)] rounded px-2 py-0.5 text-xs focus:outline-none focus:border-emerald-500 cursor-pointer font-medium"
            >
              <option value="ALL">All Severities</option>
              <option value="CRITICAL">Critical</option>
              <option value="HIGH">High</option>
              <option value="MODERATE">Moderate</option>
              <option value="LOW">Low</option>
            </select>
          </div>

        </div>

        <div className="text-[var(--text-dim)] text-[10.5px]">
          Showing <strong className="text-[var(--text-main)]">{incidents.length}</strong> incident(s)
        </div>
      </div>

      {/* ERROR STATE */}
      {error && (
        <div className="p-3 bg-rose-500/10 border border-rose-500/25 text-rose-500 text-xs rounded-lg flex items-center justify-between">
          <div className="flex items-center gap-2">
            <AlertTriangle className="h-4 w-4 shrink-0" />
            <span>{error}</span>
          </div>
          <button
            onClick={() => fetchIncidentsList(statusFilter, severityFilter)}
            className="px-2 py-1 bg-[var(--card-bg)] hover:bg-[var(--subcard-bg)] text-[var(--text-main)] rounded border border-[var(--border-subtle)] text-xs transition cursor-pointer"
          >
            Retry
          </button>
        </div>
      )}

      {/* EMPTY STATE */}
      {!isLoading && !error && incidents.length === 0 && (
        <div className="bg-[var(--card-bg)] border border-[var(--border-subtle)] rounded-lg p-6 text-center space-y-2">
          <CheckCheck className="h-7 w-7 text-emerald-500 mx-auto" />
          <h4 className="text-xs font-bold text-[var(--text-main)]">No Incidents Found</h4>
          <p className="text-[11px] text-[var(--text-dim)] max-w-sm mx-auto">
            No operational incidents currently match the selected filters.
          </p>
        </div>
      )}

      {/* MAIN TWO-COLUMN LAYOUT: INCIDENT LIST + INCIDENT DETAIL PANEL */}
      {incidents.length > 0 && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-3.5">
          
          {/* SECTION C — INCIDENT LIST (5 of 12 columns) */}
          <div className="lg:col-span-5 space-y-2 max-h-[520px] overflow-y-auto pr-1">
            {incidents.map((inc) => {
              const isSelected = selectedIncident?.id === inc.id;
              const sev = SEVERITY_CONFIG[inc.severity] || SEVERITY_CONFIG.LOW;
              const stat = STATUS_CONFIG[inc.status] || STATUS_CONFIG.OPEN;
              const StatIcon = stat.icon;

              return (
                <div
                  key={`cmd-inc-${inc.id}`}
                  onClick={() => setSelectedIncident(inc)}
                  className={`p-3 rounded-lg border transition cursor-pointer text-xs space-y-1.5 shadow-xs ${
                    isSelected
                      ? 'bg-[var(--subcard-bg)] border-emerald-500 ring-1 ring-emerald-500/40'
                      : 'bg-[var(--card-bg)] border-[var(--border-subtle)] hover:border-[var(--border-strong)]'
                  }`}
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-mono font-bold text-[var(--text-main)]">
                      {inc.incident_code}
                    </span>
                    <div className="flex items-center gap-1">
                      <span className={`px-1.5 py-0.5 rounded text-[9px] font-bold border uppercase ${sev.badge}`}>
                        {sev.label}
                      </span>
                      <span className={`px-1.5 py-0.5 rounded text-[9px] font-semibold border flex items-center gap-1 uppercase ${stat.badge}`}>
                        <StatIcon className="h-2.5 w-2.5" />
                        {stat.label}
                      </span>
                    </div>
                  </div>

                  <h4 className="text-[var(--text-main)] font-semibold line-clamp-1 text-xs">
                    {inc.title}
                  </h4>

                  <div className="flex items-center justify-between text-[10px] text-[var(--text-dim)] pt-1 border-t border-[var(--border-subtle)]">
                    <span className="flex items-center gap-1">
                      <MapPin className="h-2.5 w-2.5 text-emerald-500" />
                      {inc.latitude?.toFixed(4)}°, {inc.longitude?.toFixed(4)}°
                    </span>
                    <span className="flex items-center gap-1 text-[var(--text-dim)]">
                      <Clock3 className="h-2.5 w-2.5" />
                      {formatDate(inc.created_at)}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>

          {/* SECTION D & E & F — INCIDENT DETAIL PANEL (7 of 12 columns) */}
          <div className="lg:col-span-7 bg-[var(--card-bg)] border border-[var(--border-subtle)] rounded-lg p-4 space-y-4">
            {selectedIncident ? (
              <>
                {/* Detail Header */}
                <div className="space-y-2 border-b border-[var(--border-subtle)] pb-3">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="flex items-center gap-1.5">
                      <span className="font-mono text-sm font-black text-[var(--text-main)]">
                        {selectedIncident.incident_code}
                      </span>
                      <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold border ${SEVERITY_CONFIG[selectedIncident.severity]?.badge || ''}`}>
                        {selectedIncident.severity}
                      </span>
                      <span className={`px-2 py-0.5 rounded-full text-[10px] font-semibold border flex items-center gap-1 ${STATUS_CONFIG[selectedIncident.status]?.badge || ''}`}>
                        {selectedIncident.status}
                      </span>
                    </div>

                    {/* Locate on Map Action */}
                    {onLocateIncident && selectedIncident.latitude && selectedIncident.longitude && (
                      <button
                        onClick={() => onLocateIncident(selectedIncident.latitude, selectedIncident.longitude)}
                        className="flex items-center gap-1 px-2 py-0.5 bg-emerald-600/15 hover:bg-emerald-600/30 text-emerald-500 rounded border border-emerald-500/30 text-[11px] font-medium transition cursor-pointer"
                      >
                        <Compass className="h-3 w-3" />
                        <span>Locate on Map</span>
                      </button>
                    )}
                  </div>

                  <h3 className="text-xs font-bold text-[var(--text-main)]">
                    {selectedIncident.title}
                  </h3>

                  {selectedIncident.description && (
                    <p className="text-xs text-[var(--text-muted)] leading-relaxed bg-[var(--subcard-bg)] p-2 rounded-lg border border-[var(--border-subtle)]">
                      {selectedIncident.description}
                    </p>
                  )}
                </div>

                {/* Metadata & Timeline Grid */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
                  <div className="space-y-1 bg-[var(--subcard-bg)] p-2.5 rounded-lg border border-[var(--border-subtle)]">
                    <span className="text-[var(--text-dim)] font-semibold block text-[10.5px]">Location Coordinates:</span>
                    <span className="font-mono text-[var(--text-main)]">
                      Lat: {selectedIncident.latitude?.toFixed(5)}°, Lng: {selectedIncident.longitude?.toFixed(5)}°
                    </span>
                    <span className="text-[var(--text-dim)] font-semibold block text-[10.5px] pt-1">Source:</span>
                    <span className="font-mono text-[var(--text-muted)] capitalize text-[10.5px]">
                      {selectedIncident.source ? selectedIncident.source.replace(/_/g, ' ').toLowerCase() : 'Automated'}
                    </span>
                  </div>

                  <div className="space-y-1 bg-[var(--subcard-bg)] p-2.5 rounded-lg border border-[var(--border-subtle)] text-[10.5px]">
                    <div className="flex justify-between">
                      <span className="text-[var(--text-dim)]">Created:</span>
                      <span className="text-[var(--text-main)] font-mono">{formatDate(selectedIncident.created_at)}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-[var(--text-dim)]">Acknowledged:</span>
                      <span className="text-[var(--text-main)] font-mono">
                        {selectedIncident.acknowledged_at ? formatDate(selectedIncident.acknowledged_at) : 'Pending'}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-[var(--text-dim)]">Resolved:</span>
                      <span className="text-[var(--text-main)] font-mono">
                        {selectedIncident.resolved_at ? formatDate(selectedIncident.resolved_at) : 'Active'}
                      </span>
                    </div>
                  </div>
                </div>

                {/* SECTION E — IMMUTABLE EVIDENCE SNAPSHOT */}
                <div className="space-y-2 pt-2 border-t border-[var(--border-subtle)]">
                  <div className="flex items-center justify-between">
                    <h4 className="text-xs font-bold text-[var(--text-main)] uppercase tracking-wider flex items-center gap-1.5">
                      <Layers className="h-3.5 w-3.5 text-emerald-500" />
                      Immutable Evidence Snapshot
                    </h4>
                    <span className="text-[10px] text-[var(--text-dim)] font-mono">
                      Priority: <strong className="text-emerald-500">{selectedIncident.operational_priority || 'N/A'}</strong>
                    </span>
                  </div>

                  <p className="text-[10px] text-[var(--text-dim)] italic">
                    This evidence reflects conditions captured when the incident was created and does not automatically change with subsequent analysis.
                  </p>

                  {selectedIncident.evidence_snapshot ? (
                    <div className="space-y-1.5">
                      <div className="grid grid-cols-2 gap-1.5 text-[11px]">
                        {/* Environmental Snapshot */}
                        <div className="bg-[var(--subcard-bg)] p-2 rounded-md border border-[var(--border-subtle)]">
                          <span className="text-[var(--text-dim)] block text-[9.5px]">Composite Hazard Index</span>
                          <span className="font-mono font-bold text-[var(--text-main)]">
                            {selectedIncident.evidence_snapshot.environmental_risk?.composite_risk_index !== undefined
                              ? selectedIncident.evidence_snapshot.environmental_risk.composite_risk_index.toFixed(1)
                              : selectedIncident.composite_risk_index?.toFixed(1) || 'N/A'}
                          </span>
                          <span className="text-[9.5px] text-amber-500 ml-1">
                            ({selectedIncident.evidence_snapshot.environmental_risk?.risk_level || 'N/A'})
                          </span>
                        </div>

                        {/* Early Warning Snapshot */}
                        <div className="bg-[var(--subcard-bg)] p-2 rounded-md border border-[var(--border-subtle)]">
                          <span className="text-[var(--text-dim)] block text-[9.5px]">Early Warning Snapshot</span>
                          <span className="font-mono font-bold text-rose-500">
                            {selectedIncident.evidence_snapshot.early_warning?.warning_level || selectedIncident.early_warning_level || 'N/A'}
                          </span>
                          <span className="text-[9.5px] text-[var(--text-dim)] ml-1">
                            ({selectedIncident.evidence_snapshot.early_warning?.operational_mode || 'Standard'})
                          </span>
                        </div>

                        {/* Ground Intelligence Snapshot */}
                        <div className="bg-[var(--subcard-bg)] p-2 rounded-md border border-[var(--border-subtle)]">
                          <span className="text-[var(--text-dim)] block text-[9.5px]">Ground Observations</span>
                          <span className="font-mono text-[var(--text-main)]">
                            {selectedIncident.evidence_snapshot.ground_intelligence?.status || selectedIncident.field_intelligence_status || 'NORMAL'}
                          </span>
                        </div>

                        {/* Road Disruption Snapshot */}
                        <div className="bg-[var(--subcard-bg)] p-2 rounded-md border border-[var(--border-subtle)]">
                          <span className="text-[var(--text-dim)] block text-[9.5px]">Road Disruption</span>
                          <span className="font-mono text-amber-500">
                            {selectedIncident.evidence_snapshot.road_disruption?.disruption_status || selectedIncident.road_disruption_status || 'NORMAL'}
                          </span>
                        </div>
                      </div>

                      {/* Snapshot Reasons */}
                      {selectedIncident.evidence_snapshot.priority_reasons && selectedIncident.evidence_snapshot.priority_reasons.length > 0 && (
                        <div className="bg-[var(--subcard-bg)] p-2 rounded-md border border-[var(--border-subtle)] space-y-1 text-[10.5px] text-[var(--text-muted)]">
                          <span className="text-[9.5px] font-bold text-[var(--text-dim)] uppercase tracking-wider block">
                            Trigger Rationale:
                          </span>
                          {selectedIncident.evidence_snapshot.priority_reasons.map((r, idx) => (
                            <div key={`snap-reason-${idx}`} className="flex items-start gap-1.5">
                              <span className="text-emerald-500 font-bold">•</span>
                              <span>{r}</span>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  ) : (
                    <div className="p-2 bg-[var(--subcard-bg)] rounded-md text-[var(--text-dim)] text-xs italic border border-[var(--border-subtle)]">
                      No serialized evidence snapshot attached to this incident record.
                    </div>
                  )}
                </div>

                {/* SECTION F — LIFECYCLE ACTION CONTROLS */}
                <div className="pt-2.5 border-t border-[var(--border-subtle)] space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-[var(--text-main)] uppercase tracking-wider">
                      Lifecycle Response Control
                    </span>
                    <span className="text-[10.5px] text-[var(--text-dim)]">
                      Current: <strong className="text-[var(--text-main)]">{selectedIncident.status}</strong>
                    </span>
                  </div>

                  {actionError && (
                    <div className="p-2 bg-rose-500/10 border border-rose-500/25 text-rose-500 text-xs rounded flex items-center gap-2">
                      <AlertTriangle className="h-3.5 w-3.5 shrink-0" />
                      <span>{actionError}</span>
                    </div>
                  )}

                  <div className="flex items-center gap-2.5">
                    {/* OPEN -> ACKNOWLEDGED */}
                    {selectedIncident.status === 'OPEN' && (
                      <button
                        onClick={() => handleLifecycleAction('acknowledge')}
                        disabled={actionLoading}
                        className="flex items-center gap-1.5 px-3 py-1.5 bg-amber-600 hover:bg-amber-500 text-white rounded-lg text-xs font-bold shadow-xs transition cursor-pointer disabled:opacity-50"
                      >
                        {actionLoading ? (
                          <RefreshCw className="h-3 w-3 animate-spin" />
                        ) : (
                          <Eye className="h-3 w-3" />
                        )}
                        <span>{actionLoading ? 'Acknowledging...' : 'Acknowledge Incident'}</span>
                      </button>
                    )}

                    {/* ACKNOWLEDGED -> IN_PROGRESS */}
                    {selectedIncident.status === 'ACKNOWLEDGED' && (
                      <button
                        onClick={() => handleLifecycleAction('start-response')}
                        disabled={actionLoading}
                        className="flex items-center gap-1.5 px-3 py-1.5 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-xs font-bold shadow-xs transition cursor-pointer disabled:opacity-50"
                      >
                        {actionLoading ? (
                          <RefreshCw className="h-3 w-3 animate-spin" />
                        ) : (
                          <PlayCircle className="h-3 w-3" />
                        )}
                        <span>{actionLoading ? 'Starting Response...' : 'Start Response'}</span>
                      </button>
                    )}

                    {/* IN_PROGRESS -> RESOLVED */}
                    {selectedIncident.status === 'IN_PROGRESS' && (
                      <button
                        onClick={() => handleLifecycleAction('resolve')}
                        disabled={actionLoading}
                        className="flex items-center gap-1.5 px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg text-xs font-bold shadow-xs transition cursor-pointer disabled:opacity-50"
                      >
                        {actionLoading ? (
                          <RefreshCw className="h-3 w-3 animate-spin" />
                        ) : (
                          <CheckCircle2 className="h-3 w-3" />
                        )}
                        <span>{actionLoading ? 'Resolving...' : 'Resolve Incident'}</span>
                      </button>
                    )}

                    {/* RESOLVED (Terminal state) */}
                    {selectedIncident.status === 'RESOLVED' && (
                      <div className="flex items-center gap-1.5 px-3 py-1 bg-emerald-500/10 dark:bg-emerald-950/30 border border-emerald-500/30 text-emerald-700 dark:text-emerald-400 rounded-lg text-xs font-bold">
                        <CheckCheck className="h-3.5 w-3.5" />
                        <span>Incident Resolved ({formatDate(selectedIncident.resolved_at)})</span>
                      </div>
                    )}
                    {/* Broadcast Emergency Alert Button */}
                    <button
                      onClick={() => handleOpenDispatch(selectedIncident)}
                      className="flex items-center gap-1.5 px-3 py-1.5 bg-rose-600 hover:bg-rose-500 text-white rounded-lg text-xs font-bold shadow-xs transition cursor-pointer"
                      title="Broadcast incident warning to emergency response forces"
                    >
                      <Radio className="h-3 w-3 animate-pulse" />
                      <span>Broadcast Alert</span>
                    </button>
                  </div>
                </div>
              </>
            ) : (
              <div className="h-56 flex flex-col items-center justify-center text-[var(--text-dim)] text-xs">
                <ClipboardList className="h-7 w-7 mb-2" />
                <span>Select an incident from the list to view operational details</span>
              </div>
            )}
          </div>

        </div>
      )}

      {/* Emergency Alert Dispatch Modal */}
      <AlertDispatchModal
        isOpen={isDispatchModalOpen}
        onClose={() => setIsDispatchModalOpen(false)}
        alertData={dispatchIncidentData || {}}
      />
    </div>
  );
}
