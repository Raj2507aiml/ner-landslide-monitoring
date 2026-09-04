import { useState } from 'react';
import { 
  ShieldAlert, 
  MapPin, 
  Image as ImageIcon, 
  Clock, 
  CheckCircle2, 
  AlertCircle, 
  Eye, 
  PlusCircle, 
  ExternalLink,
  Layers,
  Copy
} from 'lucide-react';
import { calculateGeodesicDistanceKm } from '../services/infrastructureService';

const REPORT_TYPE_LABELS = {
  CRACK: 'Ground Crack',
  SLOPE_MOVEMENT: 'Slope Movement',
  BLOCKED_ROAD: 'Blocked Road',
  LANDSLIDE: 'Active Landslide',
  DEBRIS: 'Debris Flow',
  OTHER: 'Field Hazard',
};

const SEVERITY_STYLES = {
  CRITICAL: 'bg-rose-500/10 dark:bg-rose-950/30 text-rose-700 dark:text-rose-400 border-rose-500/30',
  HIGH: 'bg-orange-500/10 dark:bg-orange-950/30 text-orange-700 dark:text-orange-400 border-orange-500/30',
  MEDIUM: 'bg-amber-500/10 dark:bg-amber-950/30 text-amber-700 dark:text-amber-400 border-amber-500/30',
  LOW: 'bg-emerald-500/10 dark:bg-emerald-950/30 text-emerald-700 dark:text-emerald-400 border-emerald-500/30',
};

const STATUS_STYLES = {
  VERIFIED: 'bg-emerald-500/10 dark:bg-emerald-950/30 text-emerald-700 dark:text-emerald-400 border-emerald-500/30',
  UNDER_REVIEW: 'bg-amber-500/10 dark:bg-amber-950/30 text-amber-700 dark:text-amber-400 border-amber-500/30',
  PENDING: 'bg-slate-500/10 dark:bg-slate-800/40 text-slate-700 dark:text-slate-300 border-slate-500/30',
  REJECTED: 'bg-rose-500/10 dark:bg-rose-950/30 text-rose-700 dark:text-rose-400 border-rose-500/30',
};

export default function FieldIntelligenceCard({
  reports = [],
  summary = null,
  isLoading = false,
  error = null,
  onOpenReportModal,
  selectedLocation
}) {
  const [selectedImage, setSelectedImage] = useState(null);

  return (
    <div className="bg-[var(--panel-bg)] backdrop-blur-md border border-[var(--border-subtle)] rounded-xl p-4 sm:p-5 space-y-4 shadow-md">
      
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2.5 border-b border-[var(--border-subtle)] pb-3">
        <div className="flex items-center gap-2.5">
          <div className="p-1.5 bg-emerald-500/10 text-emerald-500 rounded-lg border border-emerald-500/20">
            <ShieldAlert className="h-4.5 w-4.5" />
          </div>
          <div>
            <h3 className="text-sm sm:text-base font-bold text-[var(--text-main)] tracking-tight flex items-center gap-2">
              Field Intelligence & Ground Observations
              {reports.length > 0 && (
                <span className="text-[10px] px-2 py-0.5 rounded-full bg-emerald-500/15 text-emerald-500 font-mono border border-emerald-500/30 font-semibold">
                  {reports.length} nearby
                </span>
              )}
            </h3>
            <p className="text-[11px] text-[var(--text-muted)]">
              Crowdsourced & official observational evidence within 5 km AOI
            </p>
          </div>
        </div>

        <button
          onClick={onOpenReportModal}
          className="flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold shadow-xs transition cursor-pointer self-start sm:self-auto"
        >
          <PlusCircle className="h-3.5 w-3.5" />
          <span>Report Observation</span>
        </button>
      </div>

      {/* Summary Statistics Bar (if summary available) */}
      {summary && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-center">
          <div className="bg-[var(--card-bg)] border border-[var(--border-subtle)] p-2 rounded-lg">
            <span className="text-[9px] uppercase font-bold text-[var(--text-dim)] tracking-wider block">Total AOI Reports</span>
            <span className="text-base font-bold text-[var(--text-main)]">{summary.total_reports}</span>
          </div>
          <div className="bg-[var(--card-bg)] border border-[var(--border-subtle)] p-2 rounded-lg">
            <span className="text-[9px] uppercase font-bold text-emerald-500 tracking-wider block">Verified Evidence</span>
            <span className="text-base font-bold text-emerald-500">{summary.verified_observations}</span>
          </div>
          <div className="bg-[var(--card-bg)] border border-[var(--border-subtle)] p-2 rounded-lg">
            <span className="text-[9px] uppercase font-bold text-amber-500 tracking-wider block">Under Review</span>
            <span className="text-base font-bold text-amber-500">{summary.unverified_observations}</span>
          </div>
          <div className="bg-[var(--card-bg)] border border-[var(--border-subtle)] p-2 rounded-lg">
            <span className="text-[9px] uppercase font-bold text-sky-500 tracking-wider block">With Photos</span>
            <span className="text-base font-bold text-sky-500">{summary.evidence_statistics?.reports_with_media || 0}</span>
          </div>
        </div>
      )}

      {/* Loading State */}
      {isLoading && (
        <div className="py-6 text-center space-y-2">
          <div className="h-5 w-5 border-2 border-emerald-500 border-t-transparent rounded-full animate-spin mx-auto" />
          <p className="text-xs text-[var(--text-muted)]">Loading ground intelligence reports...</p>
        </div>
      )}

      {/* Error State */}
      {error && !isLoading && (
        <div className="p-3 bg-rose-500/10 border border-rose-500/25 rounded-lg text-rose-500 text-xs flex items-center gap-2">
          <AlertCircle className="h-4 w-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Empty State */}
      {!isLoading && !error && reports.length === 0 && (
        <div className="py-6 px-4 text-center border border-dashed border-[var(--border-subtle)] rounded-lg bg-[var(--card-bg)] space-y-1.5">
          <Layers className="h-7 w-7 text-[var(--text-dim)] mx-auto" />
          <h4 className="text-xs font-bold text-[var(--text-main)]">No Field Observations in this AOI</h4>
          <p className="text-[10px] text-[var(--text-dim)] max-w-sm mx-auto">
            No citizen or field official reports have been recorded within 5 km of these coordinates.
          </p>
          <button
            onClick={onOpenReportModal}
            className="inline-flex items-center gap-1.5 px-3 py-1 rounded-lg bg-[var(--subcard-bg)] hover:bg-[var(--card-bg)] text-emerald-500 text-xs font-semibold border border-[var(--border-subtle)] transition mt-1 cursor-pointer"
          >
            <PlusCircle className="h-3.5 w-3.5" />
            <span>Submit First Observation Here</span>
          </button>
        </div>
      )}

      {/* Reports List */}
      {!isLoading && reports.length > 0 && (
        <div className="space-y-2.5 max-h-[380px] overflow-y-auto pr-1">
          {reports.map((report) => {
            const typeLabel = REPORT_TYPE_LABELS[report.report_type] || report.report_type;
            const severityStyle = SEVERITY_STYLES[report.severity] || 'bg-slate-800 text-slate-300';
            const statusStyle = STATUS_STYLES[report.status] || 'bg-slate-800 text-slate-300';

            const computedDist = report.distance_km !== undefined 
              ? report.distance_km 
              : (selectedLocation?.lat && report.latitude)
                ? calculateGeodesicDistanceKm(selectedLocation.lat, selectedLocation.lng, report.latitude, report.longitude)
                : null;
            const distanceLabel = computedDist !== null 
              ? (computedDist < 1 ? `${Math.round(computedDist * 1000)} m away` : `${computedDist} km away`)
              : 'Active AOI';

            return (
              <div 
                key={report.id}
                className="bg-[var(--card-bg)] border border-[var(--border-subtle)] hover:border-[var(--border-strong)] p-3 rounded-lg space-y-2 transition shadow-xs"
              >
                {/* Header row */}
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-bold text-[var(--text-main)]">
                      {typeLabel}
                    </span>
                    <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded border uppercase tracking-wider ${severityStyle}`}>
                      {report.severity}
                    </span>
                    <span className={`text-[9px] font-semibold px-1.5 py-0.5 rounded border ${statusStyle}`}>
                      {report.status.replace('_', ' ')}
                    </span>
                  </div>

                  <div className="flex items-center gap-2 text-[10px] text-[var(--text-dim)] font-mono">
                    <span className="flex items-center gap-1">
                      <MapPin className="h-2.5 w-2.5 text-emerald-500" />
                      {distanceLabel}
                    </span>
                    <span>•</span>
                    <span className="text-[var(--text-dim)]">
                      {new Date(report.created_at).toLocaleDateString()}
                    </span>
                  </div>
                </div>

                {/* Description */}
                <p className="text-xs text-[var(--text-muted)] leading-relaxed font-normal">
                  {report.description}
                </p>

                {/* Footer details & duplicate warning */}
                <div className="flex flex-wrap items-center justify-between gap-2 pt-1 border-t border-[var(--border-subtle)] text-[10.5px]">
                  <div className="flex items-center gap-3 text-[var(--text-dim)]">
                    <span>
                      Reporter: <strong className="text-[var(--text-muted)] font-medium capitalize">{report.reporter_type.toLowerCase().replace('_', ' ')}</strong>
                    </span>
                    {report.media_count > 0 && (
                      <span className="flex items-center gap-1 text-sky-500 font-medium">
                        <ImageIcon className="h-3 w-3" />
                        {report.media_count} photo evidence
                      </span>
                    )}
                  </div>

                  {report.potential_duplicate && (
                    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-amber-500/10 text-amber-500 border border-amber-500/20 text-[9.5px] font-semibold">
                      <Copy className="h-2.5 w-2.5" />
                      Similar report nearby
                    </span>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Scientific Notice */}
      <div className="bg-[var(--subcard-bg)] border border-[var(--border-subtle)] p-3 rounded-lg text-[10px] text-[var(--text-muted)] space-y-1">
        <p className="font-semibold text-emerald-500 font-mono">ℹ️ Scientific & Operational Guidance:</p>
        <p className="text-[var(--text-dim)] leading-normal">
          Field observations are qualitative human intelligence reports. They provide ground context to corroborate environmental sensors and radar change analyses without modifying mathematical ML susceptibility models.
        </p>
      </div>
    </div>
  );
}
