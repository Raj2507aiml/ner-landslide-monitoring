import React from 'react';
import { 
  AlertTriangle, 
  CheckCircle2, 
  ShieldAlert, 
  Clock, 
  Compass, 
  Layers, 
  MapPin, 
  ExternalLink,
  OctagonAlert,
  TrafficCone,
  Info
} from 'lucide-react';

const STATUS_BADGE_CONFIG = {
  NORMAL: {
    label: 'Normal Connectivity',
    badge: 'bg-emerald-500/10 dark:bg-emerald-950/30 border-emerald-500/30 text-emerald-700 dark:text-emerald-400',
    icon: CheckCircle2
  },
  MONITORING_REQUIRED: {
    label: 'Monitoring Required',
    badge: 'bg-sky-500/10 dark:bg-sky-950/30 border-sky-500/30 text-sky-700 dark:text-sky-400',
    icon: Clock
  },
  ELEVATED_DISRUPTION: {
    label: 'Elevated Disruption',
    badge: 'bg-amber-500/10 dark:bg-amber-950/30 border-amber-500/30 text-amber-700 dark:text-amber-400',
    icon: AlertTriangle
  },
  HIGH_DISRUPTION: {
    label: 'High Disruption',
    badge: 'bg-orange-500/10 dark:bg-orange-950/30 border-orange-500/30 text-orange-700 dark:text-orange-400',
    icon: TrafficCone
  },
  CRITICAL_DISRUPTION: {
    label: 'Critical Disruption',
    badge: 'bg-rose-500/10 dark:bg-rose-950/30 border-rose-500/40 text-rose-700 dark:text-rose-400',
    icon: OctagonAlert
  }
};

const PRIORITY_BADGE_CONFIG = {
  CRITICAL: 'bg-rose-500/10 dark:bg-rose-950/30 text-rose-700 dark:text-rose-300 border-rose-500/40',
  HIGH: 'bg-orange-500/10 dark:bg-orange-950/30 text-orange-700 dark:text-orange-400 border-orange-500/30',
  MEDIUM: 'bg-amber-500/10 dark:bg-amber-950/30 text-amber-700 dark:text-amber-400 border-amber-500/30',
  LOW: 'bg-sky-500/10 dark:bg-sky-950/30 text-sky-700 dark:text-sky-400 border-sky-500/30'
};

const HAZARD_LABELS = {
  CRACK: 'Ground Cracks',
  SLOPE_MOVEMENT: 'Slope Movement',
  BLOCKED_ROAD: 'Blocked Roads',
  LANDSLIDE: 'Landslides',
  DEBRIS: 'Debris Flow',
  OTHER: 'Other Hazards'
};

export default function RoadDisruptionCard({ disruptionData, isLoading, error }) {
  if (isLoading) {
    return (
      <div className="bg-[var(--panel-bg)] backdrop-blur-md border border-[var(--border-subtle)] rounded-xl p-5 shadow-md animate-pulse space-y-3">
        <div className="flex items-center justify-between border-b border-[var(--border-subtle)] pb-2.5">
          <div className="h-4 w-44 bg-[var(--card-bg)] rounded"></div>
          <div className="h-5 w-28 bg-[var(--card-bg)] rounded-full"></div>
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
          <div className="h-14 bg-[var(--card-bg)] rounded-lg"></div>
          <div className="h-14 bg-[var(--card-bg)] rounded-lg"></div>
          <div className="h-14 bg-[var(--card-bg)] rounded-lg"></div>
          <div className="h-14 bg-[var(--card-bg)] rounded-lg"></div>
        </div>
        <div className="h-16 bg-[var(--card-bg)] rounded-lg"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-[var(--panel-bg)] backdrop-blur-md border border-[var(--border-subtle)] rounded-xl p-5 shadow-md space-y-3">
        <div className="flex items-center gap-2 text-[var(--text-main)]">
          <TrafficCone className="h-4.5 w-4.5 text-amber-500" />
          <h3 className="text-sm font-bold">Road Disruption Intelligence</h3>
        </div>
        <div className="p-3 bg-rose-500/10 border border-rose-500/25 text-rose-500 text-xs rounded-lg flex items-center gap-2">
          <AlertTriangle className="h-4 w-4 shrink-0" />
          <span>{error}</span>
        </div>
      </div>
    );
  }

  if (!disruptionData) {
    return null;
  }

  const statusCfg = STATUS_BADGE_CONFIG[disruptionData.disruption_status] || STATUS_BADGE_CONFIG.NORMAL;
  const StatusIcon = statusCfg.icon;

  return (
    <div className="bg-[var(--panel-bg)] backdrop-blur-md border border-[var(--border-subtle)] rounded-xl p-4 sm:p-5 shadow-md space-y-4">
      
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-2.5 border-b border-[var(--border-subtle)] pb-3">
        <div className="flex items-center gap-2.5">
          <div className="p-1.5 rounded-lg bg-amber-500/10 border border-amber-500/20 text-amber-500">
            <TrafficCone className="h-4.5 w-4.5" />
          </div>
          <div>
            <h3 className="text-sm sm:text-base font-bold text-[var(--text-main)] tracking-tight">
              Road Disruption Intelligence
            </h3>
            <p className="text-[11px] text-[var(--text-muted)]">
              Operational corridor impact & prioritized connectivity assessment
            </p>
          </div>
        </div>

        <div className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold border ${statusCfg.badge}`}>
          <StatusIcon className="h-3.5 w-3.5" />
          <span>{statusCfg.label}</span>
        </div>
      </div>

      {/* KPI Tiles */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs">
        <div className="bg-[var(--card-bg)] p-2.5 rounded-lg border border-[var(--border-subtle)] flex flex-col justify-between">
          <span className="text-[var(--text-dim)] text-[9.5px] uppercase font-semibold">Total Roads</span>
          <span className="text-lg font-bold text-[var(--text-main)] mt-0.5">{disruptionData.road_counts?.total || 0}</span>
        </div>

        <div className="bg-[var(--card-bg)] p-2.5 rounded-lg border border-[var(--border-subtle)] flex flex-col justify-between">
          <span className="text-amber-500 text-[9.5px] uppercase font-semibold">Affected Corridors</span>
          <span className="text-lg font-bold text-amber-500 mt-0.5">{disruptionData.affected_roads || 0}</span>
        </div>

        <div className="bg-[var(--card-bg)] p-2.5 rounded-lg border border-[var(--border-subtle)] flex flex-col justify-between">
          <span className="text-rose-500 text-[9.5px] uppercase font-semibold">Confirmed Blocked</span>
          <span className="text-lg font-bold text-rose-500 mt-0.5">{disruptionData.road_counts?.blocked || 0}</span>
        </div>

        <div className="bg-[var(--card-bg)] p-2.5 rounded-lg border border-[var(--border-subtle)] flex flex-col justify-between">
          <span className="text-sky-500 text-[9.5px] uppercase font-semibold">Under Monitoring</span>
          <span className="text-lg font-bold text-sky-500 mt-0.5">{disruptionData.monitored_roads || 0}</span>
        </div>
      </div>

      {/* Operational Narrative Message */}
      <div className="p-3 bg-[var(--card-bg)] rounded-lg border border-[var(--border-subtle)] text-xs text-[var(--text-main)] leading-relaxed flex items-start gap-2.5">
        <Info className="h-4 w-4 text-amber-500 shrink-0 mt-0.5" />
        <div>
          <span className="font-bold text-[var(--text-main)] block mb-0.5">Operational Assessment:</span>
          <span className="text-[var(--text-muted)] text-[11px]">{disruptionData.operational_message}</span>
        </div>
      </div>

      {/* Top Priority Disrupted Roads Section */}
      {disruptionData.priority_roads && disruptionData.priority_roads.length > 0 && (
        <div className="space-y-2.5">
          <div className="flex items-center justify-between">
            <h4 className="text-xs font-bold text-[var(--text-main)] uppercase tracking-wider">
              Top Priority Disrupted Road Corridors
            </h4>
            <span className="text-[10px] text-[var(--text-dim)] font-mono">
              Ranked by Severity & Evidence
            </span>
          </div>

          <div className="space-y-2">
            {disruptionData.priority_roads.map((road) => (
              <div 
                key={`p-road-${road.osm_id}`}
                className="p-3 rounded-lg bg-[var(--card-bg)] border border-[var(--border-subtle)] hover:border-[var(--border-strong)] transition space-y-2 text-xs shadow-xs"
              >
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <span className="px-1.5 py-0.5 rounded text-[10px] font-mono font-bold bg-[var(--subcard-bg)] text-[var(--text-main)] border border-[var(--border-subtle)]">
                      #{road.priority_rank}
                    </span>
                    <span className="font-bold text-[var(--text-main)] text-xs">
                      {road.road_name || road.road_ref || 'Unnamed Road'}
                    </span>
                    {road.road_ref && (
                      <span className="px-1.5 py-0.2 rounded text-[10px] font-mono bg-[var(--subcard-bg)] text-[var(--text-dim)] border border-[var(--border-subtle)]">
                        {road.road_ref}
                      </span>
                    )}
                    <span className="text-[10px] text-[var(--text-dim)] capitalize">
                      ({road.highway_type})
                    </span>
                  </div>

                  <div className="flex items-center gap-1.5">
                    <span className={`px-2 py-0.5 rounded text-[10px] font-bold border ${PRIORITY_BADGE_CONFIG[road.disruption_priority] || PRIORITY_BADGE_CONFIG.LOW}`}>
                      {road.disruption_priority} PRIORITY
                    </span>
                    <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-[var(--subcard-bg)] text-[var(--text-main)] border border-[var(--border-subtle)]">
                      {road.connectivity_status}
                    </span>
                  </div>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 text-[11px] text-[var(--text-muted)] bg-[var(--subcard-bg)] p-2 rounded-lg border border-[var(--border-subtle)]">
                  <div>
                    <span className="text-[var(--text-dim)] text-[9.5px] block">Nearest Hazard:</span>
                    <span className="font-mono text-[var(--text-main)] font-semibold">
                      {road.nearest_hazard_distance_m !== null ? `${road.nearest_hazard_distance_m} m` : 'N/A'}
                    </span>
                  </div>
                  <div>
                    <span className="text-[var(--text-dim)] text-[9.5px] block">Verified Evidence:</span>
                    <span className="font-semibold text-emerald-500">
                      {road.verified_reports} report(s)
                    </span>
                  </div>
                  <div>
                    <span className="text-[var(--text-dim)] text-[9.5px] block">Supporting IDs:</span>
                    <span className="font-mono text-[var(--text-main)]">
                      {road.supporting_report_ids?.length > 0 ? `#${road.supporting_report_ids.join(', #')}` : 'None'}
                    </span>
                  </div>
                </div>

                <p className="text-[11px] text-[var(--text-muted)] italic">
                  {road.explanation}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Hazard Impact Breakdown */}
      {disruptionData.hazard_impact_breakdown && Object.values(disruptionData.hazard_impact_breakdown).some(v => v > 0) && (
        <div className="space-y-1.5 pt-2 border-t border-[var(--border-subtle)]">
          <span className="text-[10px] font-bold text-[var(--text-dim)] uppercase tracking-wider block">
            Corridor Hazard Impact Breakdown
          </span>
          <div className="flex flex-wrap gap-1.5 text-xs">
            {Object.entries(disruptionData.hazard_impact_breakdown).map(([key, count]) => {
              if (count === 0) return null;
              return (
                <div 
                  key={`breakdown-${key}`}
                  className="px-2 py-0.5 rounded-md bg-[var(--card-bg)] border border-[var(--border-subtle)] flex items-center gap-1.5 text-[10.5px]"
                >
                  <span className="text-[var(--text-dim)]">{HAZARD_LABELS[key] || key}:</span>
                  <span className="font-bold text-amber-500">{count}</span>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Disclaimer */}
      <div className="pt-2 border-t border-[var(--border-subtle)] text-[10px] text-[var(--text-dim)]">
        ℹ️ {disruptionData.disclaimer}
      </div>

    </div>
  );
}
