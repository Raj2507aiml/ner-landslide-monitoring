import React from 'react';
import {
  ShieldAlert,
  AlertTriangle,
  CheckCircle2,
  Clock,
  Eye,
  Activity,
  Radio,
  MapPin,
  TrafficCone,
  Info,
  RefreshCw,
  Layers,
  ArrowRight,
  OctagonAlert,
  ListChecks,
  Compass
} from 'lucide-react';

const PRIORITY_THEMES = {
  ROUTINE: {
    label: 'ROUTINE MONITORING',
    badge: 'bg-emerald-500/10 dark:bg-emerald-950/30 border-emerald-500/30 text-emerald-700 dark:text-emerald-400',
    banner: 'bg-emerald-500/10 border-emerald-500/30 text-emerald-800 dark:bg-emerald-950/30 dark:text-emerald-300',
    icon: CheckCircle2,
    tagline: 'Baseline conditions. Standard telemetry and routine monitoring protocols active.'
  },
  ATTENTION_REQUIRED: {
    label: 'ATTENTION REQUIRED',
    badge: 'bg-sky-500/10 dark:bg-sky-950/30 border-sky-500/30 text-sky-700 dark:text-sky-400',
    banner: 'bg-sky-500/10 border-sky-500/30 text-sky-800 dark:bg-sky-950/30 dark:text-sky-300',
    icon: Eye,
    tagline: 'Observational review or preliminary meteorological trigger monitoring flagged.'
  },
  HIGH_PRIORITY: {
    label: 'HIGH PRIORITY',
    badge: 'bg-amber-500/10 dark:bg-amber-950/30 border-amber-500/30 text-amber-700 dark:text-amber-400',
    banner: 'bg-amber-500/10 border-amber-500/30 text-amber-800 dark:bg-amber-950/30 dark:text-amber-300',
    icon: AlertTriangle,
    tagline: 'Heightened operational readiness. Active slope hazards or road corridor impacts detected.'
  },
  CRITICAL_PRIORITY: {
    label: 'CRITICAL PRIORITY',
    badge: 'bg-rose-500/10 dark:bg-rose-950/30 border-rose-500/40 text-rose-700 dark:text-rose-400 animate-pulse',
    banner: 'bg-rose-500/10 border-rose-500/30 text-rose-800 dark:bg-rose-950/40 dark:text-rose-200',
    icon: OctagonAlert,
    tagline: 'Urgent operational review and coordinated multi-agency emergency response required.'
  }
};

const WARNING_BADGE = {
  NORMAL: 'bg-emerald-500/10 dark:bg-emerald-950/30 text-emerald-700 dark:text-emerald-300 border-emerald-500/30',
  WATCH: 'bg-sky-500/10 dark:bg-sky-950/30 text-sky-700 dark:text-sky-300 border-sky-500/30',
  ALERT: 'bg-amber-500/10 dark:bg-amber-950/30 text-amber-700 dark:text-amber-300 border-amber-500/30',
  CRITICAL: 'bg-rose-500/10 dark:bg-rose-950/30 text-rose-700 dark:text-rose-300 border-rose-500/40'
};

const RISK_BADGE = {
  Low: 'text-emerald-700 dark:text-emerald-400',
  Moderate: 'text-sky-700 dark:text-sky-400',
  High: 'text-amber-700 dark:text-amber-400',
  'Very High': 'text-rose-700 dark:text-rose-400'
};

export default function OperationalSituationCard({
  assessmentData,
  isLoading,
  error,
  onRetry,
  selectedLocation
}) {
  // 1. Loading State
  if (isLoading) {
    return (
      <div className="bg-[var(--panel-bg)] backdrop-blur-md border border-[var(--border-subtle)] rounded-xl p-5 shadow-md animate-pulse space-y-3">
        <div className="flex items-center justify-between border-b border-[var(--border-subtle)] pb-2.5">
          <div className="flex items-center gap-2">
            <Activity className="h-4.5 w-4.5 text-emerald-500 animate-spin" />
            <span className="text-xs font-bold text-[var(--text-main)]">
              Analyzing operational situation...
            </span>
          </div>
          <div className="h-5 w-24 bg-[var(--card-bg)] rounded-full"></div>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-2.5">
          <div className="h-16 bg-[var(--card-bg)] rounded-lg"></div>
          <div className="h-16 bg-[var(--card-bg)] rounded-lg"></div>
          <div className="h-16 bg-[var(--card-bg)] rounded-lg"></div>
          <div className="h-16 bg-[var(--card-bg)] rounded-lg"></div>
        </div>
        <div className="h-20 bg-[var(--card-bg)] rounded-lg"></div>
      </div>
    );
  }

  // 2. Error State
  if (error) {
    return (
      <div className="bg-[var(--panel-bg)] backdrop-blur-md border border-[var(--border-subtle)] rounded-xl p-5 shadow-md space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 text-rose-500 font-bold text-xs">
            <ShieldAlert className="h-4.5 w-4.5" />
            <span>Operational Situation Assessment</span>
          </div>
          {onRetry && (
            <button
              onClick={onRetry}
              className="flex items-center gap-1 text-xs px-2.5 py-1 bg-[var(--card-bg)] hover:bg-[var(--subcard-bg)] text-[var(--text-main)] rounded border border-[var(--border-subtle)] transition cursor-pointer"
            >
              <RefreshCw className="h-3 w-3" />
              <span>Retry</span>
            </button>
          )}
        </div>
        <div className="p-3 bg-rose-500/10 border border-rose-500/25 text-rose-500 text-xs rounded-lg flex items-center gap-2">
          <AlertTriangle className="h-4 w-4 shrink-0" />
          <span>{error || 'Unable to retrieve operational situation assessment.'}</span>
        </div>
      </div>
    );
  }

  // 3. No Location Selected State
  if (!selectedLocation && !assessmentData) {
    return (
      <div className="bg-[var(--panel-bg)] backdrop-blur-md border border-[var(--border-subtle)] rounded-xl p-5 shadow-md text-center space-y-2">
        <Compass className="h-7 w-7 text-emerald-500 mx-auto" />
        <h3 className="text-xs font-bold text-[var(--text-main)] uppercase tracking-wider">
          Operational Situation Assessment
        </h3>
        <p className="text-[11px] text-[var(--text-muted)] max-w-md mx-auto leading-relaxed">
          Select a location on the map to generate an integrated operational assessment synthesizing environmental hazard, early warning, ground observations, and road disruption intelligence.
        </p>
      </div>
    );
  }

  if (!assessmentData) {
    return null;
  }

  const priorityKey = assessmentData.operational_priority || 'ROUTINE';
  const theme = PRIORITY_THEMES[priorityKey] || PRIORITY_THEMES.ROUTINE;
  const PriorityIcon = theme.icon;

  const env = assessmentData.environmental_context || {};
  const ew = assessmentData.early_warning || {};
  const ground = assessmentData.ground_intelligence || {};
  const infra = assessmentData.infrastructure_impact || {};

  return (
    <div className="bg-[var(--panel-bg)] backdrop-blur-md border border-[var(--border-subtle)] rounded-xl p-4 sm:p-5 shadow-md space-y-4">
      
      {/* SECTION A — OVERALL PRIORITY BANNER */}
      <div className="space-y-2">
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-[var(--border-subtle)] pb-3">
          <div className="flex items-center gap-2.5">
            <div className="p-1.5 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-500">
              <Layers className="h-4.5 w-4.5" />
            </div>
            <div>
              <h3 className="text-sm sm:text-base font-bold text-[var(--text-main)] tracking-tight">
                Operational Situation Assessment
              </h3>
              <p className="text-[11px] text-[var(--text-muted)]">
                Integrated multi-source decision support & prioritized response directives
              </p>
            </div>
          </div>

          {/* Prominent Operational Priority Badge */}
          <div className={`flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold uppercase border shadow-xs ${theme.badge}`}>
            <PriorityIcon className="h-3.5 w-3.5 shrink-0" />
            <span>{theme.label}</span>
          </div>
        </div>

        {/* Priority Tagline Banner */}
        <div className={`p-2.5 rounded-lg border text-xs leading-relaxed flex items-start gap-2 ${theme.banner}`}>
          <PriorityIcon className="h-4 w-4 shrink-0 mt-0.5" />
          <div>
            <span className="font-bold block mb-0.5">Priority Directive:</span>
            <span className="text-[11px]">{theme.tagline}</span>
          </div>
        </div>
      </div>

      {/* SECTION B — INTELLIGENCE SUMMARY GRID (2x2 Desktop / 1 Col Mobile) */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-2.5 text-xs">
        
        {/* 1. Environmental Hazard Risk Card */}
        <div className="bg-[var(--card-bg)] p-3 rounded-lg border border-[var(--border-subtle)] flex flex-col justify-between space-y-1.5">
          <div className="flex items-center justify-between border-b border-[var(--border-subtle)] pb-1.5">
            <div className="flex items-center gap-1.5 text-[var(--text-main)] font-semibold">
              <Activity className="h-3.5 w-3.5 text-emerald-500" />
              <span>Environmental Risk</span>
            </div>
            <span className={`font-black text-xs ${RISK_BADGE[env.risk_level] || 'text-[var(--text-main)]'}`}>
              {env.risk_level || 'N/A'}
            </span>
          </div>
          <div className="flex items-baseline justify-between">
            <span className="text-[var(--text-dim)] text-[11px]">Composite Risk Index:</span>
            <span className="font-mono text-base font-bold text-[var(--text-main)]">
              {env.composite_risk_index !== undefined ? env.composite_risk_index.toFixed(1) : '0.0'}{' '}
              <span className="text-[10px] text-[var(--text-dim)] font-normal">/ 100</span>
            </span>
          </div>
        </div>

        {/* 2. Early Warning Context Card */}
        <div className="bg-[var(--card-bg)] p-3 rounded-lg border border-[var(--border-subtle)] flex flex-col justify-between space-y-1.5">
          <div className="flex items-center justify-between border-b border-[var(--border-subtle)] pb-1.5">
            <div className="flex items-center gap-1.5 text-[var(--text-main)] font-semibold">
              <Radio className="h-3.5 w-3.5 text-sky-500" />
              <span>Early Warning Level</span>
            </div>
            <span className={`px-2 py-0.5 rounded text-[10px] font-bold border ${WARNING_BADGE[ew.warning_level] || WARNING_BADGE.NORMAL}`}>
              {ew.warning_level || 'NORMAL'}
            </span>
          </div>
          <div className="flex items-baseline justify-between text-[11px]">
            <span className="text-[var(--text-dim)]">Decision Mode:</span>
            <span className="font-mono text-[var(--text-muted)] font-medium capitalize">
              {ew.operational_mode ? ew.operational_mode.replace(/_/g, ' ').toLowerCase() : 'Standard'}
            </span>
          </div>
        </div>

        {/* 3. Ground Intelligence Context Card */}
        <div className="bg-[var(--card-bg)] p-3 rounded-lg border border-[var(--border-subtle)] flex flex-col justify-between space-y-1.5">
          <div className="flex items-center justify-between border-b border-[var(--border-subtle)] pb-1.5">
            <div className="flex items-center gap-1.5 text-[var(--text-main)] font-semibold">
              <MapPin className="h-3.5 w-3.5 text-teal-500" />
              <span>Ground Intelligence</span>
            </div>
            <span className="font-mono text-[10px] text-[var(--text-dim)]">
              Score: <strong className="text-teal-500">{ground.verified_signal_score?.toFixed(1) || '0.0'}</strong>
            </span>
          </div>
          <div className="flex items-center justify-between text-[11px]">
            <span className="text-[var(--text-dim)]">Report Status:</span>
            <span className="font-medium text-[var(--text-main)]">
              {ground.verified_reports || 0} Verified · {ground.unverified_reports || 0} Unverified
            </span>
          </div>
        </div>

        {/* 4. Road Disruption Context Card */}
        <div className="bg-[var(--card-bg)] p-3 rounded-lg border border-[var(--border-subtle)] flex flex-col justify-between space-y-1.5">
          <div className="flex items-center justify-between border-b border-[var(--border-subtle)] pb-1.5">
            <div className="flex items-center gap-1.5 text-[var(--text-main)] font-semibold">
              <TrafficCone className="h-3.5 w-3.5 text-amber-500" />
              <span>Road Disruption</span>
            </div>
            <span className="text-[10px] font-bold text-amber-500">
              {infra.disruption_status ? infra.disruption_status.replace(/_/g, ' ') : 'NORMAL'}
            </span>
          </div>
          <div className="flex items-center justify-between text-[11px]">
            <span className="text-[var(--text-dim)]">Affected Corridors:</span>
            <span className="font-medium text-[var(--text-main)]">
              {infra.affected_roads || 0} Affected ({infra.priority_road_count || 0} Priority)
            </span>
          </div>
        </div>

      </div>

      {/* SECTION C — PRIORITY REASONS */}
      <div className="space-y-1.5 pt-1 border-t border-[var(--border-subtle)]">
        <h4 className="text-xs font-bold text-[var(--text-main)] uppercase tracking-wider flex items-center gap-1.5">
          <Info className="h-3.5 w-3.5 text-emerald-500" />
          Priority Assessment Rationale
        </h4>
        <div className="bg-[var(--card-bg)] p-3 rounded-lg border border-[var(--border-subtle)] space-y-1.5 text-xs text-[var(--text-muted)]">
          {assessmentData.priority_reasons && assessmentData.priority_reasons.length > 0 ? (
            assessmentData.priority_reasons.map((reason, idx) => (
              <div key={`reason-${idx}`} className="flex items-start gap-2">
                <span className="text-emerald-500 font-bold shrink-0 mt-0.5">•</span>
                <span className="leading-relaxed">{reason}</span>
              </div>
            ))
          ) : (
            <p className="text-[var(--text-dim)] italic text-[11px]">
              All baseline indicators are within standard normal operational limits.
            </p>
          )}
        </div>
      </div>

      {/* SECTION D — RECOMMENDED OPERATIONAL ACTIONS */}
      <div className="space-y-1.5 pt-1 border-t border-[var(--border-subtle)]">
        <h4 className="text-xs font-bold text-[var(--text-main)] uppercase tracking-wider flex items-center gap-1.5">
          <ListChecks className="h-3.5 w-3.5 text-emerald-500" />
          Recommended Operational Directives
        </h4>
        <div className="space-y-1.5">
          {assessmentData.recommended_actions && assessmentData.recommended_actions.length > 0 ? (
            assessmentData.recommended_actions.map((action, idx) => (
              <div 
                key={`action-${idx}`}
                className="p-2.5 rounded-lg bg-[var(--card-bg)] border border-[var(--border-subtle)] flex items-start gap-2.5 text-xs text-[var(--text-main)] shadow-xs"
              >
                <span className="flex items-center justify-center h-4 w-4 rounded-full bg-emerald-500/20 text-emerald-500 font-mono font-bold text-[10px] shrink-0 mt-0.5">
                  {idx + 1}
                </span>
                <span className="leading-snug">{action}</span>
              </div>
            ))
          ) : (
            <p className="text-[var(--text-dim)] italic text-[11px]">
              Continue routine baseline monitoring. Check system telemetry daily.
            </p>
          )}
        </div>
      </div>

      {/* SECTION E — DISCLAIMER */}
      <div className="pt-2 border-t border-[var(--border-subtle)] text-[10px] text-[var(--text-dim)] leading-normal bg-[var(--card-bg)] p-2.5 rounded-lg border">
        ℹ️ <strong>Decision Support Notice:</strong> {assessmentData.disclaimer}
      </div>

    </div>
  );
}
