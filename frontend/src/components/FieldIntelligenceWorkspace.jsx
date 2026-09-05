import { useState, useEffect, useCallback } from 'react';
import { createPortal } from 'react-dom';
import { 
  X, 
  ShieldAlert, 
  CheckCircle2, 
  AlertTriangle, 
  Clock, 
  MapPin, 
  Image as ImageIcon, 
  FileText, 
  Filter, 
  RefreshCw, 
  ArrowRight, 
  ExternalLink, 
  Compass, 
  Eye, 
  XCircle, 
  CheckCheck,
  AlertOctagon,
  Layers
} from 'lucide-react';
import { 
  getReviewQueue, 
  getFieldReportById, 
  updateReportStatus 
} from '../services/fieldReportService';
import { getMediaBaseUrl } from '../services/apiConfig';

const SEVERITY_CONFIG = {
  CRITICAL: { label: 'Critical', badge: 'bg-rose-500/10 dark:bg-rose-950/30 border-rose-500/40 text-rose-700 dark:text-rose-400', dot: 'bg-rose-500' },
  HIGH: { label: 'High', badge: 'bg-orange-500/10 dark:bg-orange-950/30 border-orange-500/40 text-orange-700 dark:text-orange-400', dot: 'bg-orange-500' },
  MEDIUM: { label: 'Medium', badge: 'bg-amber-500/10 dark:bg-amber-950/30 border-amber-500/40 text-amber-700 dark:text-amber-400', dot: 'bg-amber-500' },
  LOW: { label: 'Low', badge: 'bg-emerald-500/10 dark:bg-emerald-950/30 border-emerald-500/40 text-emerald-700 dark:text-emerald-400', dot: 'bg-emerald-500' },
};

const STATUS_CONFIG = {
  PENDING: { label: 'Pending Triage', badge: 'bg-amber-500/10 dark:bg-amber-950/30 border-amber-500/30 text-amber-700 dark:text-amber-400' },
  UNDER_REVIEW: { label: 'Under Review', badge: 'bg-sky-500/10 dark:bg-sky-950/30 border-sky-500/30 text-sky-700 dark:text-sky-400' },
  VERIFIED: { label: 'Verified Ground Truth', badge: 'bg-emerald-500/10 dark:bg-emerald-950/30 border-emerald-500/30 text-emerald-700 dark:text-emerald-400' },
  REJECTED: { label: 'Rejected', badge: 'bg-slate-500/10 dark:bg-slate-800/40 border-slate-500/30 text-slate-700 dark:text-slate-400' },
};

const REPORT_TYPE_LABELS = {
  CRACK: 'Ground Crack / Fissure',
  SLOPE_MOVEMENT: 'Slope Movement / Creep',
  BLOCKED_ROAD: 'Blocked Road / Pass',
  LANDSLIDE: 'Active Landslide',
  DEBRIS: 'Debris Accumulation',
  OTHER: 'Other Hazard',
};

export default function FieldIntelligenceWorkspace({ isOpen, onClose, onReportUpdated }) {
  // Filters & pagination
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [severityFilter, setSeverityFilter] = useState('ALL');
  const [typeFilter, setTypeFilter] = useState('ALL');

  // Queue data
  const [queueItems, setQueueItems] = useState([]);
  const [kpis, setKpis] = useState({
    total: 0,
    pending: 0,
    underReview: 0,
    verified: 0,
    critical: 0
  });
  const [isLoadingQueue, setIsLoadingQueue] = useState(false);

  // Selected report inspection
  const [selectedReportId, setSelectedReportId] = useState(null);
  const [selectedReportDetail, setSelectedReportDetail] = useState(null);
  const [isLoadingDetail, setIsLoadingDetail] = useState(false);
  const [isUpdatingStatus, setIsUpdatingStatus] = useState(false);
  const [actionError, setActionError] = useState(null);
  const [actionSuccess, setActionSuccess] = useState(null);

  // Lightbox preview for photos
  const [activePhotoUrl, setActivePhotoUrl] = useState(null);

  // Body scroll locking and Escape key handler
  useEffect(() => {
    if (!isOpen) return;

    const originalOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';

    const handleKeyDown = (e) => {
      if (e.key === 'Escape') {
        if (activePhotoUrl) {
          setActivePhotoUrl(null);
        } else {
          onClose();
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => {
      document.body.style.overflow = originalOverflow;
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [isOpen, activePhotoUrl, onClose]);

  // Fetch Review Queue
  const fetchQueue = useCallback(async () => {
    setIsLoadingQueue(true);
    setActionError(null);

    const res = await getReviewQueue({
      status: statusFilter,
      severity: severityFilter,
      reportType: typeFilter,
      limit: 100
    });

    setIsLoadingQueue(false);
    if (res.ok && res.data) {
      setQueueItems(res.data.items || []);
      setKpis({
        total: res.data.total || 0,
        pending: res.data.pending_count || 0,
        underReview: res.data.under_review_count || 0,
        verified: res.data.verified_count || 0,
        critical: res.data.critical_count || 0
      });

      // Auto-select first report if none selected
      if (!selectedReportId && res.data.items && res.data.items.length > 0) {
        setSelectedReportId(res.data.items[0].id);
      }
    }
  }, [statusFilter, severityFilter, typeFilter, selectedReportId]);

  // Load queue on mount / filter change
  useEffect(() => {
    if (isOpen) {
      fetchQueue();
    }
  }, [isOpen, fetchQueue]);

  // Fetch Detailed Report Inspection
  useEffect(() => {
    if (!selectedReportId) {
      setSelectedReportDetail(null);
      return;
    }

    let isMounted = true;
    async function loadDetail() {
      setIsLoadingDetail(true);
      const res = await getFieldReportById(selectedReportId);
      if (isMounted) {
        setIsLoadingDetail(false);
        if (res.ok) {
          setSelectedReportDetail(res.data);
        } else {
          setSelectedReportDetail(null);
        }
      }
    }

    loadDetail();
    setActionError(null);
    setActionSuccess(null);
    return () => {
      isMounted = false;
    };
  }, [selectedReportId]);

  // Handle Status Update
  const handleTransitionStatus = async (newStatus) => {
    if (!selectedReportId) return;

    setIsUpdatingStatus(true);
    setActionError(null);
    setActionSuccess(null);

    let res = await updateReportStatus(selectedReportId, newStatus);

    // Resilient transition: If direct PENDING -> VERIFIED fails due to backend workflow,
    // automatically promote to UNDER_REVIEW first, then transition to VERIFIED
    if (!res.ok && newStatus === 'VERIFIED' && selectedReportDetail?.status === 'PENDING') {
      const reviewRes = await updateReportStatus(selectedReportId, 'UNDER_REVIEW');
      if (reviewRes.ok) {
        res = await updateReportStatus(selectedReportId, 'VERIFIED');
      }
    }

    setIsUpdatingStatus(false);

    if (res.ok) {
      if (res.data?.notification_dispatched) {
        setActionSuccess(`Observation verified! Automated SMS alert dispatched to registered users in ${res.data.detected_state || 'the region'} (${res.data.recipients_notified || 1} contact(s)).`);
      } else if (newStatus === 'VERIFIED') {
        setActionSuccess('Observation verified.');
      } else {
        setActionSuccess(`Report status successfully updated to ${newStatus}.`);
      }

      // Refresh detailed view & queue
      const updatedDetail = await getFieldReportById(selectedReportId);
      if (updatedDetail.ok) {
        setSelectedReportDetail(updatedDetail.data);
      }
      fetchQueue();
      if (onReportUpdated) {
        onReportUpdated(res.data);
      }
    } else {
      setActionError(res.error || 'Failed to update report status.');
    }
  };

  if (!isOpen) return null;

  const modalContent = (
    <div 
      className="fixed inset-0 z-[99999] flex items-center justify-center p-2 sm:p-4 md:p-6 bg-[var(--overlay-backdrop)] backdrop-blur-md overflow-hidden"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
      onWheel={(e) => e.stopPropagation()}
    >
      <div 
        className="relative w-full max-w-7xl h-[94vh] flex flex-col bg-[var(--modal-bg)] border border-[var(--border-subtle)] text-[var(--text-main)] rounded-2xl shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-150"
        onClick={(e) => e.stopPropagation()}
        onWheel={(e) => e.stopPropagation()}
      >
        
        {/* Workspace Top Header */}
        <div className="flex-none flex items-center justify-between px-6 py-3.5 border-b border-[var(--border-subtle)] bg-[var(--modal-header-bg)]">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-emerald-500/10 text-emerald-500 rounded-xl border border-emerald-500/20">
              <ShieldAlert className="h-5 w-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-base font-bold text-[var(--text-main)] tracking-tight">
                  Field Intelligence Operational Review Workspace
                </h2>
                <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-600/20 text-emerald-500 border border-emerald-500/30">
                  AUTHORITY OPS
                </span>
              </div>
              <p className="text-xs text-[var(--text-muted)]">
                Triage, inspect photo evidence, evaluate EXIF consistency, and verify ground observations
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={fetchQueue}
              disabled={isLoadingQueue}
              className="p-2 rounded-xl bg-[var(--card-bg)] hover:bg-[var(--subcard-bg)] text-[var(--text-main)] transition disabled:opacity-50 cursor-pointer flex items-center gap-1.5 text-xs font-semibold border border-[var(--border-subtle)]"
              title="Refresh Queue"
            >
              <RefreshCw className={`h-4 w-4 ${isLoadingQueue ? 'animate-spin text-emerald-500' : ''}`} />
              <span className="hidden sm:inline">Refresh</span>
            </button>
            <button
              onClick={onClose}
              className="p-2 rounded-xl text-[var(--text-dim)] hover:text-[var(--text-main)] hover:bg-[var(--card-bg)] transition cursor-pointer"
              title="Close Workspace (Esc)"
            >
              <X className="h-5 w-5" />
            </button>
          </div>
        </div>

        {/* Operational KPI Summary Banner */}
        <div className="flex-none grid grid-cols-2 sm:grid-cols-5 gap-2 px-6 py-2.5 bg-[var(--subcard-bg)] border-b border-[var(--border-subtle)] text-xs">
          <div className="p-2.5 rounded-xl bg-[var(--card-bg)] border border-[var(--border-subtle)] flex items-center justify-between">
            <div>
              <span className="text-[10.5px] font-semibold text-[var(--text-dim)] block uppercase tracking-wider">Total Filed</span>
              <span className="text-base font-bold text-[var(--text-main)]">{kpis.total}</span>
            </div>
            <Layers className="h-4 w-4 text-[var(--text-dim)]" />
          </div>

          <div className="p-2.5 rounded-xl bg-amber-500/10 border border-amber-500/20 flex items-center justify-between">
            <div>
              <span className="text-[10.5px] font-semibold text-amber-500 block uppercase tracking-wider">Under Review</span>
              <span className="text-base font-bold text-amber-500">{kpis.underReview}</span>
            </div>
            <Clock className="h-4 w-4 text-amber-500" />
          </div>

          <div className="p-2.5 rounded-xl bg-[var(--card-bg)] border border-[var(--border-subtle)] flex items-center justify-between">
            <div>
              <span className="text-[10.5px] font-semibold text-[var(--text-dim)] block uppercase tracking-wider">Pending</span>
              <span className="text-base font-bold text-[var(--text-main)]">{kpis.pending}</span>
            </div>
            <Eye className="h-4 w-4 text-[var(--text-dim)]" />
          </div>

          <div className="p-2.5 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-between">
            <div>
              <span className="text-[10.5px] font-semibold text-emerald-500 block uppercase tracking-wider">Verified</span>
              <span className="text-base font-bold text-emerald-500">{kpis.verified}</span>
            </div>
            <CheckCircle2 className="h-4 w-4 text-emerald-500" />
          </div>

          <div className="p-2.5 rounded-xl bg-rose-500/10 border border-rose-500/20 flex items-center justify-between">
            <div>
              <span className="text-[10.5px] font-semibold text-rose-500 block uppercase tracking-wider">Rejected</span>
              <span className="text-base font-bold text-rose-500">{kpis.rejected}</span>
            </div>
            <XCircle className="h-4 w-4 text-rose-500" />
          </div>
        </div>

        {/* Operational Filter & Action Bar */}
        <div className="flex-none px-6 py-2.5 border-b border-[var(--border-subtle)] bg-[var(--card-bg)] flex flex-wrap items-center justify-between gap-3 text-xs">
          
          {/* Status Tabs */}
          <div className="flex items-center gap-1 bg-[var(--subcard-bg)] p-1 rounded-xl border border-[var(--border-subtle)]">
            {['ALL', 'PENDING', 'UNDER_REVIEW', 'VERIFIED', 'REJECTED'].map((st) => (
              <button
                key={st}
                onClick={() => setStatusFilter(st)}
                className={`px-3 py-1 rounded-lg font-semibold transition cursor-pointer text-[11px] ${
                  statusFilter === st 
                    ? 'bg-emerald-600 text-white shadow-xs' 
                    : 'text-[var(--text-muted)] hover:text-[var(--text-main)]'
                }`}
              >
                {st === 'ALL' ? 'All Statuses' : STATUS_CONFIG[st]?.label || st}
              </button>
            ))}
          </div>

          {/* Secondary Filters */}
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-1.5">
              <span className="text-[var(--text-dim)] font-semibold text-[11px]">Severity:</span>
              <select
                value={severityFilter}
                onChange={(e) => setSeverityFilter(e.target.value)}
                className="bg-[var(--subcard-bg)] border border-[var(--border-subtle)] text-[var(--text-main)] rounded-lg px-2.5 py-1 text-[11px] focus:outline-none focus:border-emerald-500 cursor-pointer font-medium"
              >
                <option value="ALL">All Severities</option>
                <option value="CRITICAL">Critical</option>
                <option value="HIGH">High</option>
                <option value="MEDIUM">Medium</option>
                <option value="LOW">Low</option>
              </select>
            </div>

            <div className="flex items-center gap-1.5">
              <span className="text-[var(--text-dim)] font-semibold text-[11px]">Hazard:</span>
              <select
                value={typeFilter}
                onChange={(e) => setTypeFilter(e.target.value)}
                className="bg-[var(--subcard-bg)] border border-[var(--border-subtle)] text-[var(--text-main)] rounded-lg px-2.5 py-1 text-[11px] focus:outline-none focus:border-emerald-500 cursor-pointer font-medium"
              >
                <option value="ALL">All Types</option>
                <option value="CRACK">Ground Crack</option>
                <option value="SLOPE_MOVEMENT">Slope Movement</option>
                <option value="BLOCKED_ROAD">Blocked Road</option>
                <option value="LANDSLIDE">Active Landslide</option>
                <option value="DEBRIS">Debris</option>
                <option value="OTHER">Other</option>
              </select>
            </div>
          </div>
        </div>

        {/* Main Body: Two-Column Split View */}
        <div className="flex-1 flex flex-col md:flex-row overflow-hidden">
          
          {/* Left Column: Review Queue List */}
          <div className="w-full md:w-[380px] lg:w-[420px] border-r border-[var(--border-subtle)] flex flex-col bg-[var(--subcard-bg)]">
            <div className="px-4 py-2 border-b border-[var(--border-subtle)] bg-[var(--card-bg)] flex items-center justify-between text-xs">
              <span className="font-semibold text-[var(--text-dim)]">
                Queue ({queueItems.length} {queueItems.length === 1 ? 'report' : 'reports'})
              </span>
              <span className="text-[10px] text-emerald-500 font-mono font-bold">
                Sorted by Severity & Recency
              </span>
            </div>

            <div className="flex-1 overflow-y-auto p-3 space-y-2.5 overscroll-contain">
              {isLoadingQueue ? (
                <div className="flex flex-col items-center justify-center py-16 text-[var(--text-muted)] space-y-2">
                  <RefreshCw className="h-6 w-6 animate-spin text-emerald-500" />
                  <span className="text-xs">Loading operational review queue...</span>
                </div>
              ) : queueItems.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-16 text-[var(--text-muted)] text-center px-4">
                  <CheckCheck className="h-8 w-8 text-[var(--text-dim)] mb-2" />
                  <p className="text-xs font-semibold text-[var(--text-main)]">No matching reports in queue</p>
                  <p className="text-[11px] text-[var(--text-dim)] mt-1">Adjust your filters to inspect other operational records.</p>
                </div>
              ) : (
                queueItems.map((item) => {
                  const isSelected = item.id === selectedReportId;
                  const sev = SEVERITY_CONFIG[item.severity] || SEVERITY_CONFIG.MEDIUM;
                  const st = STATUS_CONFIG[item.status] || STATUS_CONFIG.PENDING;

                  return (
                    <div
                      key={item.id}
                      onClick={() => setSelectedReportId(item.id)}
                      className={`p-3.5 rounded-xl border text-left transition cursor-pointer relative ${
                        isSelected
                          ? 'bg-[var(--card-bg)] border-emerald-500 shadow-md ring-1 ring-emerald-500/50'
                          : 'bg-[var(--card-bg)] border-[var(--border-subtle)] hover:border-[var(--border-strong)] hover:bg-[var(--subcard-bg)]'
                      }`}
                    >
                      {/* Priority Ribbon / Header */}
                      <div className="flex items-center justify-between gap-2 mb-1.5">
                        <div className="flex items-center gap-1.5">
                          <span className={`px-2 py-0.5 rounded-md text-[10px] font-bold border ${sev.badge}`}>
                            {sev.label}
                          </span>
                          <span className={`px-2 py-0.5 rounded-md text-[10px] font-semibold border ${st.badge}`}>
                            {st.label}
                          </span>
                        </div>
                        <span className="text-[10px] font-mono text-[var(--text-dim)]">
                          #{item.id}
                        </span>
                      </div>

                      {/* Title & Reporter */}
                      <div className="mb-1">
                        <h4 className="text-xs font-bold text-[var(--text-main)] flex items-center justify-between">
                          <span>{REPORT_TYPE_LABELS[item.report_type] || item.report_type}</span>
                          <span className="text-[10px] font-normal text-[var(--text-muted)]">
                            {item.reporter_type === 'FIELD_OFFICIAL' ? '👮 Official' : '👤 Citizen'}
                          </span>
                        </h4>
                      </div>

                      {/* Description Snippet */}
                      <p className="text-[11px] text-[var(--text-muted)] line-clamp-2 leading-relaxed mb-2 font-normal">
                        {item.description}
                      </p>

                      {/* Footer Info / Tags */}
                      <div className="flex items-center justify-between pt-1 border-t border-[var(--border-subtle)] text-[10px] text-[var(--text-dim)]">
                        <div className="flex items-center gap-1">
                          <MapPin className="h-3 w-3 text-[var(--text-dim)]" />
                          <span className="font-mono">{item.latitude.toFixed(3)}, {item.longitude.toFixed(3)}</span>
                        </div>

                        <div className="flex items-center gap-2">
                          {item.media_count > 0 && (
                            <span className="inline-flex items-center gap-1 text-sky-500 font-medium">
                              <ImageIcon className="h-3 w-3" />
                              {item.media_count}
                            </span>
                          )}
                          {item.potential_duplicate && (
                            <span className="text-amber-500 font-semibold" title="Duplicate hazard cluster near">
                              ⚠️ Cluster
                            </span>
                          )}
                        </div>
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </div>

          {/* Right Column: Detailed Report Inspection & Triage */}
          <div className="flex-1 flex flex-col bg-[var(--modal-bg)] overflow-y-auto overscroll-contain">
            {isLoadingDetail ? (
              <div className="flex flex-col items-center justify-center h-full py-20 text-[var(--text-muted)] space-y-2">
                <RefreshCw className="h-8 w-8 animate-spin text-emerald-500" />
                <span className="text-xs">Loading report inspection details...</span>
              </div>
            ) : !selectedReportDetail ? (
              <div className="flex flex-col items-center justify-center h-full py-20 text-[var(--text-muted)] text-center px-6">
                <ShieldAlert className="h-12 w-12 text-[var(--text-dim)] mb-3" />
                <h3 className="text-base font-bold text-[var(--text-main)]">Select a Report for Operational Triage</h3>
                <p className="text-xs text-[var(--text-dim)] max-w-md mt-1">
                  Choose an observation item from the review queue on the left to inspect detailed photo evidence, verify coordinates, and execute operational transitions.
                </p>
              </div>
            ) : (
              <div className="p-6 space-y-6 max-w-4xl">
                
                {/* Action Error Banner */}
                {actionError && (
                  <div className="flex items-start gap-2.5 p-3.5 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-500 text-xs">
                    <AlertTriangle className="h-4 w-4 shrink-0 mt-0.5 text-rose-500" />
                    <p className="leading-relaxed font-medium">{actionError}</p>
                  </div>
                )}

                {/* Inspection Header */}
                <div className="flex flex-wrap items-center justify-between gap-3 pb-4 border-b border-[var(--border-subtle)]">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-mono font-bold text-emerald-500">
                        REPORT #{selectedReportDetail.id}
                      </span>
                      <span className={`px-2.5 py-0.5 rounded-md text-xs font-bold border ${STATUS_CONFIG[selectedReportDetail.status]?.badge}`}>
                        {STATUS_CONFIG[selectedReportDetail.status]?.label}
                      </span>
                      <span className={`px-2.5 py-0.5 rounded-md text-xs font-bold border ${SEVERITY_CONFIG[selectedReportDetail.severity]?.badge}`}>
                        {SEVERITY_CONFIG[selectedReportDetail.severity]?.label} Severity
                      </span>
                    </div>
                    <h3 className="text-lg font-bold text-[var(--text-main)] mt-1">
                      {REPORT_TYPE_LABELS[selectedReportDetail.report_type] || selectedReportDetail.report_type}
                    </h3>
                  </div>

                  <div className="text-right text-xs text-[var(--text-dim)]">
                    <span className="block font-medium text-[var(--text-muted)]">
                      Submitted by: {selectedReportDetail.reporter_type === 'FIELD_OFFICIAL' ? '👮 Official Field Unit' : '👤 Local Resident'}
                    </span>
                    <span className="text-[11px] text-[var(--text-dim)]">
                      {new Date(selectedReportDetail.created_at).toLocaleString()}
                    </span>
                  </div>
                </div>

                {/* Section 1: Observation Details */}
                <div className="space-y-2 bg-[var(--card-bg)] p-4 rounded-xl border border-[var(--border-subtle)]">
                  <label className="block text-xs font-semibold text-[var(--text-dim)] uppercase tracking-wider">
                    Observation Description
                  </label>
                  <p className="text-xs text-[var(--text-main)] leading-relaxed whitespace-pre-wrap">
                    {selectedReportDetail.description}
                  </p>
                </div>

                {/* Section 2: Spatial & Location Intelligence */}
                <div className="space-y-3 bg-[var(--card-bg)] p-4 rounded-xl border border-[var(--border-subtle)]">
                  <div className="flex items-center justify-between">
                    <label className="block text-xs font-semibold text-[var(--text-dim)] uppercase tracking-wider">
                      Location & Spatial Context
                    </label>
                    {selectedReportDetail.spatial_context?.potential_duplicate && (
                      <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-500/10 text-amber-500 border border-amber-500/30">
                        ⚠️ Spatial Duplicate Cluster Detected
                      </span>
                    )}
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
                    <div className="p-3 bg-[var(--subcard-bg)] rounded-lg border border-[var(--border-subtle)]">
                      <span className="text-[10.5px] text-[var(--text-dim)] block">Reported Coordinates</span>
                      <span className="font-mono text-[var(--text-main)] font-semibold">
                        {selectedReportDetail.latitude.toFixed(6)}, {selectedReportDetail.longitude.toFixed(6)}
                      </span>
                    </div>

                    <div className="p-3 bg-[var(--subcard-bg)] rounded-lg border border-[var(--border-subtle)]">
                      <span className="text-[10.5px] text-[var(--text-dim)] block">Nearby Reports (5km)</span>
                      <span className="font-semibold text-emerald-500">
                        {selectedReportDetail.spatial_context?.nearby_reports_count || 0} active observation(s)
                      </span>
                    </div>

                    <div className="p-3 bg-[var(--subcard-bg)] rounded-lg border border-[var(--border-subtle)]">
                      <span className="text-[10.5px] text-[var(--text-dim)] block">Evidence Confidence</span>
                      <span className="font-semibold text-emerald-500">
                        {selectedReportDetail.evidence_confidence || 'UNVERIFIED'}
                      </span>
                    </div>
                  </div>
                </div>

                {/* Section 3: Photo Evidence Gallery */}
                <div className="space-y-3 bg-[var(--card-bg)] p-4 rounded-xl border border-[var(--border-subtle)]">
                  <label className="block text-xs font-semibold text-[var(--text-dim)] uppercase tracking-wider flex items-center justify-between">
                    <span>Photographic Evidence ({selectedReportDetail.media?.length || 0})</span>
                    <span className="text-[10px] text-[var(--text-dim)] font-normal">Click any photo to enlarge</span>
                  </label>

                  {(!selectedReportDetail.media || selectedReportDetail.media.length === 0) ? (
                    <div className="p-6 text-center text-[var(--text-dim)] text-xs border border-dashed border-[var(--border-subtle)] rounded-xl">
                      <ImageIcon className="h-6 w-6 mx-auto mb-1 text-[var(--text-dim)]" />
                      <span>No photo evidence attached to this report.</span>
                    </div>
                  ) : (
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                      {selectedReportDetail.media.map((m) => {
                        const fullUrl = `${getMediaBaseUrl()}${m.media_url}`;
                        return (
                          <div
                            key={m.id}
                            onClick={() => setActivePhotoUrl(fullUrl)}
                            className="group relative bg-[var(--subcard-bg)] border border-[var(--border-subtle)] rounded-xl overflow-hidden cursor-pointer hover:border-emerald-500/50 transition flex flex-col"
                          >
                            <div className="h-44 bg-[var(--modal-bg)] flex items-center justify-center overflow-hidden relative">
                              <img
                                src={fullUrl}
                                alt={m.original_filename}
                                className="w-full h-full object-cover group-hover:scale-105 transition duration-300"
                              />
                              <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 transition flex items-center justify-center gap-1.5 text-white text-xs font-semibold">
                                <Eye className="h-4 w-4" /> Enlarge
                              </div>
                            </div>

                            <div className="p-3 text-[11px] space-y-1 bg-[var(--subcard-bg)]">
                              <p className="font-semibold text-[var(--text-main)] truncate" title={m.original_filename}>
                                {m.original_filename}
                              </p>
                              <div className="flex items-center justify-between text-[10px] text-[var(--text-dim)]">
                                <span>{(m.file_size_bytes / (1024 * 1024)).toFixed(2)} MB {m.width && `• ${m.width}x${m.height}`}</span>
                                <span>{new Date(m.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                              </div>

                              {m.exif_latitude && m.exif_longitude ? (
                                <div className="pt-1.5 border-t border-[var(--border-subtle)] flex items-center justify-between text-[10px]">
                                  <span className="text-[var(--text-dim)] font-mono">
                                    EXIF: {m.exif_latitude.toFixed(4)}, {m.exif_longitude.toFixed(4)}
                                  </span>
                                  <span className={`font-bold ${
                                    m.exif_consistency === 'CONSISTENT' ? 'text-emerald-500' :
                                    m.exif_consistency === 'NEARBY_DIFFERENCE' ? 'text-amber-500' :
                                    'text-rose-500'
                                  }`}>
                                    {m.exif_consistency} ({m.exif_distance_km}km)
                                  </span>
                                </div>
                              ) : (
                                <div className="pt-1.5 border-t border-[var(--border-subtle)] text-[10px] text-[var(--text-dim)]">
                                  No EXIF GPS tags found
                                </div>
                              )}
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>

                {/* Section 4: Evidence Consistency Assessment */}
                <div className="p-4 rounded-xl bg-[var(--card-bg)] border border-[var(--border-subtle)] space-y-2 text-xs">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-emerald-500 font-mono flex items-center gap-1.5">
                      <Compass className="h-4 w-4 text-emerald-500" />
                      Coordinate & Evidence Consistency Assessment
                    </span>
                    <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                      selectedReportDetail.spatial_context?.exif_consistency_summary === 'CONSISTENT' ? 'bg-emerald-500/10 text-emerald-500 border border-emerald-500/30' :
                      selectedReportDetail.spatial_context?.exif_consistency_summary === 'NEARBY_DIFFERENCE' ? 'bg-amber-500/10 text-amber-500 border border-amber-500/30' :
                      selectedReportDetail.spatial_context?.exif_consistency_summary === 'SIGNIFICANT_DIFFERENCE' ? 'bg-rose-500/10 text-rose-500 border border-rose-500/30' :
                      'bg-[var(--subcard-bg)] text-[var(--text-dim)] border border-[var(--border-subtle)]'
                    }`}>
                      {selectedReportDetail.spatial_context?.exif_consistency_summary || 'NO_EXIF_GPS'}
                    </span>
                  </div>

                  <p className="text-[var(--text-muted)] text-[11px] leading-relaxed">
                    ℹ️ <strong>Operational Guidance:</strong> EXIF metadata is supporting evidence and should not independently determine report validity. Observers may photograph landslides from vantage points or roads up to several hundred meters away.
                  </p>
                </div>

                {/* Action Feedback Alerts */}
                {actionError && (
                  <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-400 text-xs flex items-center gap-2">
                    <AlertTriangle className="h-4 w-4 shrink-0 text-rose-400" />
                    <span>{actionError}</span>
                  </div>
                )}

                {actionSuccess && (
                  <div className="p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-xs flex items-center gap-2">
                    <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-400" />
                    <span>{actionSuccess}</span>
                  </div>
                )}

                {/* Section 5: Review Action Workflow */}
                <div className="pt-4 border-t border-[var(--border-subtle)] flex flex-wrap items-center justify-between gap-3">
                  <div className="text-xs text-[var(--text-muted)]">
                    Current Status: <span className="font-bold text-[var(--text-main)]">{selectedReportDetail.status}</span>
                  </div>

                  <div className="flex items-center gap-2">
                    {selectedReportDetail.status === 'PENDING' && (
                      <>
                        <button
                          type="button"
                          onClick={() => handleTransitionStatus('REJECTED')}
                          disabled={isUpdatingStatus}
                          className="px-4 py-2 rounded-xl bg-[var(--card-bg)] hover:bg-rose-500/20 text-rose-500 border border-[var(--border-subtle)] text-xs font-semibold transition disabled:opacity-50 cursor-pointer"
                        >
                          ✕ Reject Report
                        </button>
                        <button
                          type="button"
                          onClick={() => handleTransitionStatus('UNDER_REVIEW')}
                          disabled={isUpdatingStatus}
                          className="px-4 py-2 rounded-xl bg-sky-600 hover:bg-sky-500 text-white text-xs font-bold shadow-md shadow-sky-600/30 transition disabled:opacity-50 cursor-pointer flex items-center gap-1.5"
                        >
                          <Eye className="h-4 w-4" /> Start Review
                        </button>
                        <button
                          type="button"
                          onClick={() => handleTransitionStatus('VERIFIED')}
                          disabled={isUpdatingStatus}
                          className="px-4 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold shadow-md shadow-emerald-600/30 transition disabled:opacity-50 cursor-pointer flex items-center gap-1.5"
                        >
                          <CheckCircle2 className="h-4 w-4" /> Quick Verify & SMS Alert
                        </button>
                      </>
                    )}

                    {selectedReportDetail.status === 'UNDER_REVIEW' && (
                      <>
                        <button
                          type="button"
                          onClick={() => handleTransitionStatus('REJECTED')}
                          disabled={isUpdatingStatus}
                          className="px-4 py-2 rounded-xl bg-rose-500/10 hover:bg-rose-500/20 text-rose-500 border border-rose-500/30 text-xs font-semibold transition disabled:opacity-50 cursor-pointer"
                        >
                          ✕ Reject Observation
                        </button>
                        <button
                          type="button"
                          onClick={() => handleTransitionStatus('VERIFIED')}
                          disabled={isUpdatingStatus}
                          className="px-5 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold shadow-md shadow-emerald-600/30 transition disabled:opacity-50 cursor-pointer flex items-center gap-1.5"
                        >
                          <CheckCircle2 className="h-4 w-4" /> Confirm & Verify Observation
                        </button>
                      </>
                    )}

                    {selectedReportDetail.status === 'VERIFIED' && (
                      <div className="flex items-center gap-3">
                        <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-500 text-xs font-bold">
                          <CheckCircle2 className="h-4 w-4" /> Verified Ground Observation
                        </div>
                        <button
                          type="button"
                          onClick={() => handleTransitionStatus('UNDER_REVIEW')}
                          disabled={isUpdatingStatus}
                          className="px-3 py-1.5 rounded-lg text-[var(--text-muted)] hover:text-[var(--text-main)] bg-[var(--card-bg)] border border-[var(--border-subtle)] text-[11px] font-semibold transition cursor-pointer"
                        >
                          Reopen Review
                        </button>
                      </div>
                    )}

                    {selectedReportDetail.status === 'REJECTED' && (
                      <div className="flex items-center gap-3">
                        <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-500 text-xs font-bold">
                          <XCircle className="h-4 w-4" /> Rejected Report
                        </div>
                        <button
                          type="button"
                          onClick={() => handleTransitionStatus('UNDER_REVIEW')}
                          disabled={isUpdatingStatus}
                          className="px-3 py-1.5 rounded-lg text-[var(--text-muted)] hover:text-[var(--text-main)] bg-[var(--card-bg)] border border-[var(--border-subtle)] text-[11px] font-semibold transition cursor-pointer"
                        >
                          Reopen Review
                        </button>
                      </div>
                    )}
                  </div>
                </div>

              </div>
            )}
          </div>

        </div>

      </div>

      {/* Full Size Image Lightbox Modal */}
      {activePhotoUrl && (
        <div 
          className="fixed inset-0 z-[100000] flex items-center justify-center p-4 bg-black/90 backdrop-blur-md"
          onClick={() => setActivePhotoUrl(null)}
        >
          <div className="relative max-w-4xl max-h-[90vh] flex flex-col items-center">
            <button
              onClick={() => setActivePhotoUrl(null)}
              className="absolute -top-10 right-0 text-white hover:text-slate-300 p-1 cursor-pointer"
            >
              <X className="h-6 w-6" />
            </button>
            <img
              src={activePhotoUrl}
              alt="Evidence preview"
              className="max-w-full max-h-[85vh] object-contain rounded-xl border border-[var(--border-subtle)] shadow-2xl"
            />
          </div>
        </div>
      )}
    </div>
  );

  return typeof document !== 'undefined' ? createPortal(modalContent, document.body) : null;
}
