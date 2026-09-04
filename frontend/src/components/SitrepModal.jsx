import React, { useState, useMemo } from 'react';
import {
  X,
  Printer,
  Download,
  Copy,
  Check,
  FileText,
  ShieldAlert,
  MapPin,
  Compass,
  AlertTriangle,
  Radio,
  CheckCircle2,
  ExternalLink
} from 'lucide-react';
import {
  compileSitrepPayload,
  printSitrepDocument,
  downloadSitrepFile,
  formatSitrepText
} from '../services/sitrepService';

export default function SitrepModal({
  isOpen,
  onClose,
  reportContext = {}
}) {
  const [copied, setCopied] = useState(false);
  const [downloadSuccess, setDownloadSuccess] = useState(null);

  // Compile data whenever modal opens or context changes
  const sitrepData = useMemo(() => {
    if (!isOpen) return null;
    return compileSitrepPayload(reportContext);
  }, [isOpen, reportContext]);

  if (!isOpen || !sitrepData) return null;

  const {
    sitrepId,
    timestamp,
    locationName,
    coordinates,
    aoi,
    risk,
    terrain,
    weather,
    radar,
    roads,
    verifiedReports,
    dispatchHistory,
    nearestFacilities
  } = sitrepData;

  const tierColorClass =
    risk.warningTier === 'CRITICAL'
      ? 'text-rose-500 bg-rose-500/15 border-rose-500/40'
      : risk.warningTier === 'WARNING'
      ? 'text-orange-500 bg-orange-500/15 border-orange-500/40'
      : risk.warningTier === 'ALERT'
      ? 'text-amber-500 bg-amber-500/15 border-amber-500/40'
      : 'text-emerald-500 bg-emerald-500/15 border-emerald-500/40';

  const handlePrintPdf = () => {
    printSitrepDocument(sitrepData);
    setDownloadSuccess('Print dialogue opened — Select "Save as PDF" to export PDF file.');
    setTimeout(() => setDownloadSuccess(null), 4000);
  };

  const handleDownloadHtml = () => {
    downloadSitrepFile(sitrepData);
    setDownloadSuccess(`Downloaded standalone file: ${sitrepId}.html`);
    setTimeout(() => setDownloadSuccess(null), 4000);
  };

  const handleCopyText = () => {
    const text = formatSitrepText(sitrepData);
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2500);
    setDownloadSuccess('SITREP text copied to clipboard for field radio / satellite dispatch.');
    setTimeout(() => setDownloadSuccess(null), 4000);
  };

  return (
    <div className="fixed inset-0 z-[2100] flex items-center justify-center p-2 sm:p-4 bg-black/70 backdrop-blur-xs animate-in fade-in duration-150">
      <div className="bg-[var(--panel-bg)] border border-[var(--border-subtle)] rounded-xl shadow-2xl w-full max-w-4xl max-h-[94vh] flex flex-col overflow-hidden text-[var(--text-main)]">
        
        {/* Modal Top Control Bar */}
        <div className="px-4 py-3 bg-[var(--card-bg)] border-b border-[var(--border-subtle)] flex flex-wrap items-center justify-between gap-2.5 shrink-0">
          <div className="flex items-center gap-2">
            <div className="p-1.5 rounded-lg bg-emerald-500/15 border border-emerald-500/30 text-emerald-500">
              <FileText className="h-4 w-4" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="font-bold text-xs sm:text-sm uppercase tracking-wider text-[var(--text-main)]">
                  Disaster Situation Report (SITREP)
                </h3>
                <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded border font-mono ${tierColorClass}`}>
                  {risk.warningTier}
                </span>
              </div>
              <p className="text-[10px] text-[var(--text-muted)] font-mono">
                {sitrepId} · {timestamp}
              </p>
            </div>
          </div>

          {/* Action Buttons */}
          <div className="flex items-center gap-1.5">
            <button
              onClick={handlePrintPdf}
              className="px-3 py-1.5 bg-rose-600 hover:bg-rose-500 text-white rounded-lg font-bold text-xs flex items-center gap-1.5 shadow-sm transition cursor-pointer"
              title="Open print dialog to save as A4 PDF or print physical briefing"
            >
              <Printer className="h-3.5 w-3.5" />
              <span>Print / Save as PDF</span>
            </button>

            <button
              onClick={handleDownloadHtml}
              className="px-2.5 py-1.5 bg-[var(--subcard-bg)] hover:bg-[var(--card-bg)] border border-[var(--border-subtle)] hover:border-[var(--border-strong)] text-[var(--text-main)] rounded-lg font-bold text-xs flex items-center gap-1.5 transition cursor-pointer"
              title="Download standalone HTML file for offline field use"
            >
              <Download className="h-3.5 w-3.5 text-emerald-500" />
              <span className="hidden sm:inline">HTML Export</span>
            </button>

            <button
              onClick={handleCopyText}
              className="px-2.5 py-1.5 bg-[var(--subcard-bg)] hover:bg-[var(--card-bg)] border border-[var(--border-subtle)] hover:border-[var(--border-strong)] text-[var(--text-main)] rounded-lg font-bold text-xs flex items-center gap-1.5 transition cursor-pointer"
              title="Copy radio / text dispatch briefing"
            >
              {copied ? <Check className="h-3.5 w-3.5 text-emerald-500" /> : <Copy className="h-3.5 w-3.5" />}
              <span className="hidden sm:inline">{copied ? 'Copied' : 'Copy Text'}</span>
            </button>

            <button
              onClick={onClose}
              className="p-1.5 rounded-lg text-[var(--text-muted)] hover:text-[var(--text-main)] hover:bg-[var(--subcard-bg)] transition ml-1 cursor-pointer"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        </div>

        {/* Feedback Alert Toast */}
        {downloadSuccess && (
          <div className="bg-emerald-500/10 border-b border-emerald-500/25 px-4 py-2 text-[11px] text-emerald-400 flex items-center gap-2">
            <CheckCircle2 className="h-3.5 w-3.5 shrink-0" />
            <span>{downloadSuccess}</span>
          </div>
        )}

        {/* Report Preview Document Body */}
        <div className="p-4 sm:p-6 overflow-y-auto flex-1 bg-slate-100 dark:bg-slate-900/60">
          <div className="max-w-3xl mx-auto bg-white text-slate-900 shadow-xl rounded-lg p-6 sm:p-8 space-y-5 border border-slate-200">
            
            {/* Document Letterhead */}
            <div className="border-b-2 border-slate-800 pb-3 flex justify-between items-start">
              <div>
                <p className="text-[9px] font-extrabold uppercase tracking-widest text-slate-500">
                  Government of India · National Disaster Management Authority (NDMA)
                </p>
                <h2 className="text-lg sm:text-xl font-black uppercase tracking-tight text-slate-900 mt-0.5">
                  Disaster Situation Report (SITREP)
                </h2>
                <p className="text-xs font-semibold text-emerald-700">
                  North Eastern Region Early Warning & Rapid Response Network
                </p>
              </div>
              <div className="text-right">
                <span className={`inline-block px-2.5 py-0.5 text-[10px] font-black uppercase rounded border ${
                  risk.warningTier === 'CRITICAL' ? 'bg-rose-100 text-rose-800 border-rose-400' :
                  risk.warningTier === 'WARNING' ? 'bg-orange-100 text-orange-800 border-orange-400' :
                  risk.warningTier === 'ALERT' ? 'bg-amber-100 text-amber-800 border-amber-400' :
                  'bg-emerald-100 text-emerald-800 border-emerald-400'
                }`}>
                  {risk.warningTier} OPERATIONAL TIER
                </span>
                <p className="font-mono text-[9px] font-bold text-slate-700 mt-1">{sitrepId}</p>
                <p className="text-[8.5px] text-slate-500">{timestamp}</p>
              </div>
            </div>

            {/* Section 1: Geographic AOI Bounding Box & Sector Blueprint */}
            <div className="space-y-2">
              <div className="bg-slate-100 px-2.5 py-1 border-l-4 border-emerald-600 text-slate-800 font-bold text-[10.5px] uppercase tracking-wider">
                1. Geographic AOI Bounding Box & Target Sector
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 bg-slate-50 border border-slate-200 rounded-md p-3">
                
                {/* AOI Schematic Box */}
                <div className="bg-slate-900 text-slate-200 rounded p-2.5 font-mono text-[9px] flex flex-col justify-between border border-slate-700 min-h-[120px]">
                  <div className="text-center text-slate-400">▲ NORTH: {aoi.bounds.north}°N</div>
                  <div className="flex justify-between items-center my-1 text-slate-400">
                    <span>◀ WEST: {aoi.bounds.west}°E</span>
                    <span>EAST: {aoi.bounds.east}°E ▶</span>
                  </div>
                  <div className="text-center bg-emerald-950/70 border border-emerald-600/80 rounded py-1.5 px-2 my-auto">
                    <span className="text-emerald-400 font-bold">🎯 TARGET CENTROID PIN</span>
                    <p className="text-white font-bold text-[11px]">{coordinates.lat.toFixed(4)}°N, {coordinates.lng.toFixed(4)}°E</p>
                    <p className="text-[8px] text-emerald-200">{locationName}</p>
                  </div>
                  <div className="text-center text-slate-400">▼ SOUTH: {aoi.bounds.south}°N</div>
                </div>

                {/* Parameters List */}
                <div className="flex flex-col justify-around text-[10.5px] space-y-1">
                  <div className="flex justify-between border-b border-dashed border-slate-200 pb-1">
                    <span className="text-slate-500">Monitored Sector:</span>
                    <span className="font-bold text-slate-800 font-mono text-right">{locationName}</span>
                  </div>
                  <div className="flex justify-between border-b border-dashed border-slate-200 pb-1">
                    <span className="text-slate-500">AOI Dimensions:</span>
                    <span className="font-bold text-slate-800 font-mono">{aoi.radiusKm} km radius ({aoi.areaKm2} km²)</span>
                  </div>
                  <div className="flex justify-between border-b border-dashed border-slate-200 pb-1">
                    <span className="text-slate-500">Mean Terrain Elevation:</span>
                    <span className="font-bold text-slate-800 font-mono">{terrain.meanElevation} m a.s.l.</span>
                  </div>
                  <div className="flex justify-between border-b border-dashed border-slate-200 pb-1">
                    <span className="text-slate-500">Hazard Zonation:</span>
                    <span className="font-bold text-rose-700">{risk.category}</span>
                  </div>
                  <div className="flex justify-between pb-0.5">
                    <span className="text-slate-500">Emergency Helplines:</span>
                    <span className="font-bold text-slate-800 font-mono">1070 (SEOC) · 1077 (DEOC)</span>
                  </div>
                </div>

              </div>
            </div>

            {/* Section 2: Multi-Sensor Hazard Telemetry & Risk Indicators */}
            <div className="space-y-2">
              <div className="bg-slate-100 px-2.5 py-1 border-l-4 border-emerald-600 text-slate-800 font-bold text-[10.5px] uppercase tracking-wider">
                2. Multi-Sensor Hazard Telemetry & Risk Indicators
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                <div className="border border-slate-200 rounded p-2.5 text-center bg-white border-t-2 border-t-rose-600">
                  <span className="text-[8.5px] font-bold text-slate-500 uppercase block">Composite Risk</span>
                  <span className="text-base font-black text-rose-700 font-mono">{risk.compositeScore} / 100</span>
                  <span className="text-[8px] text-slate-500 block">{risk.warningTier} Tier</span>
                </div>

                <div className="border border-slate-200 rounded p-2.5 text-center bg-white border-t-2 border-t-amber-500">
                  <span className="text-[8.5px] font-bold text-slate-500 uppercase block">Slope Steepness</span>
                  <span className="text-base font-black text-slate-800 font-mono">{terrain.meanSlope}°</span>
                  <span className="text-[8px] text-slate-500 block">Peak: {terrain.maxSlope}°</span>
                </div>

                <div className="border border-slate-200 rounded p-2.5 text-center bg-white border-t-2 border-t-sky-600">
                  <span className="text-[8.5px] font-bold text-slate-500 uppercase block">24h Rainfall</span>
                  <span className="text-base font-black text-sky-800 font-mono">{weather.precip24h} mm</span>
                  <span className="text-[8px] text-slate-500 block">3-Day: {weather.precip3d} mm</span>
                </div>

                <div className="border border-slate-200 rounded p-2.5 text-center bg-white border-t-2 border-t-purple-600">
                  <span className="text-[8.5px] font-bold text-slate-500 uppercase block">Radar Delta (SAR)</span>
                  <span className="text-base font-black text-purple-800 font-mono">{radar.vvDelta} dB</span>
                  <span className="text-[8px] text-slate-500 block">Area: {radar.changePercentage}%</span>
                </div>
              </div>

              <div className="text-[9.5px] text-slate-600 bg-slate-50 border border-slate-200 p-2 rounded">
                <strong>Surface Geomorphology Assessment:</strong> {radar.surfaceChangeStatus}. 
                Soil saturation is rated <strong>{weather.soilMoisture}</strong>, with antecedent rainfall triggering high slope liquefaction probability.
              </div>
            </div>

            {/* Section 3: Critical Road Lifelines & Blockages */}
            <div className="space-y-2">
              <div className="bg-slate-100 px-2.5 py-1 border-l-4 border-emerald-600 text-slate-800 font-bold text-[10.5px] uppercase tracking-wider">
                3. Critical Lifelines & Road Infrastructure Disruption
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-[9.5px] border border-slate-200 border-collapse">
                  <thead>
                    <tr className="bg-slate-100 text-slate-700">
                      <th className="border border-slate-200 p-1.5 text-left uppercase text-[8px]">Highway / Corridor</th>
                      <th className="border border-slate-200 p-1.5 text-left uppercase text-[8px]">Connectivity</th>
                      <th className="border border-slate-200 p-1.5 text-left uppercase text-[8px]">Distance</th>
                      <th className="border border-slate-200 p-1.5 text-left uppercase text-[8px]">Operational Impact Notes</th>
                      <th className="border border-slate-200 p-1.5 text-left uppercase text-[8px]">Designated Bypass Route</th>
                    </tr>
                  </thead>
                  <tbody>
                    {roads.map((r, idx) => (
                      <tr key={idx} className={idx % 2 === 1 ? 'bg-slate-50' : 'bg-white'}>
                        <td className="border border-slate-200 p-1.5 font-bold">{r.name} ({r.ref})</td>
                        <td className="border border-slate-200 p-1.5">
                          <span className={`px-1.5 py-0.5 rounded font-black text-[8px] ${
                            r.status === 'BLOCKED' ? 'bg-rose-100 text-rose-800' :
                            r.status === 'AT_RISK' ? 'bg-amber-100 text-amber-800' :
                            'bg-emerald-100 text-emerald-800'
                          }`}>
                            {r.status}
                          </span>
                        </td>
                        <td className="border border-slate-200 p-1.5 font-mono">{r.distanceKm} km</td>
                        <td className="border border-slate-200 p-1.5 text-slate-700">{r.notes}</td>
                        <td className="border border-slate-200 p-1.5 text-slate-500 text-[8.5px]">{r.bypass}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Section 4: Verified Ground Field Intelligence */}
            <div className="space-y-2">
              <div className="bg-slate-100 px-2.5 py-1 border-l-4 border-emerald-600 text-slate-800 font-bold text-[10.5px] uppercase tracking-wider">
                4. Active Verified Ground Reports & Observations
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-[9.5px] border border-slate-200 border-collapse">
                  <thead>
                    <tr className="bg-slate-100 text-slate-700">
                      <th className="border border-slate-200 p-1.5 text-left uppercase text-[8px]">Report ID</th>
                      <th className="border border-slate-200 p-1.5 text-left uppercase text-[8px]">Time</th>
                      <th className="border border-slate-200 p-1.5 text-left uppercase text-[8px]">Incident Nature</th>
                      <th className="border border-slate-200 p-1.5 text-left uppercase text-[8px]">Severity</th>
                      <th className="border border-slate-200 p-1.5 text-left uppercase text-[8px]">Field Observer Observations</th>
                    </tr>
                  </thead>
                  <tbody>
                    {verifiedReports.map((fr, idx) => (
                      <tr key={idx} className={idx % 2 === 1 ? 'bg-slate-50' : 'bg-white'}>
                        <td className="border border-slate-200 p-1.5 font-mono font-bold">{fr.id}</td>
                        <td className="border border-slate-200 p-1.5 font-mono text-slate-500">{fr.time}</td>
                        <td className="border border-slate-200 p-1.5 font-bold">{fr.title}</td>
                        <td className="border border-slate-200 p-1.5">
                          <span className={`px-1.5 py-0.5 rounded font-black text-[8px] ${
                            fr.severity === 'HIGH' || fr.severity === 'CRITICAL' ? 'bg-rose-100 text-rose-800' : 'bg-amber-100 text-amber-800'
                          }`}>
                            {fr.severity}
                          </span>
                        </td>
                        <td className="border border-slate-200 p-1.5 text-slate-700">{fr.description}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Section 5: Emergency Inter-Agency Dispatch Audit */}
            <div className="space-y-2">
              <div className="bg-slate-100 px-2.5 py-1 border-l-4 border-emerald-600 text-slate-800 font-bold text-[10.5px] uppercase tracking-wider">
                5. Emergency Contact Dispatch & Response Status
              </div>

              <div className="bg-slate-50 border border-slate-200 rounded p-2.5 text-[9.5px] text-slate-700 space-y-1.5">
                <p>
                  <strong>Designated Response Authorities:</strong> NDRF (1st & 12th Bns), State Disaster Management Authority (SDMA), District Emergency Operation Center (DEOC), Border Roads Organisation (Project Vartak / Pushpak / Sewak), and State Traffic Police.
                </p>
                {dispatchHistory && dispatchHistory.length > 0 ? (
                  <div className="border-t border-dashed border-slate-300 pt-1.5 font-mono text-[8.5px] space-y-0.5 text-slate-600">
                    <span className="font-bold text-slate-800 block uppercase">Session Transmission Log:</span>
                    {dispatchHistory.slice(0, 3).map((h, i) => (
                      <div key={i}>• [{new Date(h.timestamp).toLocaleTimeString()}] {h.channel} to {h.agency} — Status: {h.status}</div>
                    ))}
                  </div>
                ) : (
                  <p className="text-slate-500 italic text-[9px]">
                    Multi-channel emergency broadcasts standing by in console. Helplines active: 1070 (State EOC) / 1077 (District EOC).
                  </p>
                )}

                {nearestFacilities && (
                  <div className="border-t border-slate-200 pt-2 space-y-1.5">
                    <span className="font-bold text-[9px] uppercase tracking-wider text-slate-800 block">
                      Nearest Emergency Facilities (Verified Haversine Proximity):
                    </span>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-[8.5px]">
                      <div className="bg-white p-2 rounded border border-slate-200 shadow-2xs">
                        <div className="font-bold text-slate-900">🏥 Medical Facility</div>
                        <div className="text-slate-700 truncate">{nearestFacilities.nearest_hospital.name}</div>
                        <div className="text-emerald-700 font-bold">{nearestFacilities.nearest_hospital.distance_km} km ({nearestFacilities.nearest_hospital.bearing}) • {nearestFacilities.nearest_hospital.phone}</div>
                      </div>
                      <div className="bg-white p-2 rounded border border-slate-200 shadow-2xs">
                        <div className="font-bold text-slate-900">🛡️ Public Shelter</div>
                        <div className="text-slate-700 truncate">{nearestFacilities.nearest_shelter.name}</div>
                        <div className="text-emerald-700 font-bold">{nearestFacilities.nearest_shelter.distance_km} km ({nearestFacilities.nearest_shelter.bearing}) • {nearestFacilities.nearest_shelter.phone}</div>
                      </div>
                      <div className="bg-white p-2 rounded border border-slate-200 shadow-2xs">
                        <div className="font-bold text-slate-900">🚔 Police Highway Patrol</div>
                        <div className="text-slate-700 truncate">{nearestFacilities.nearest_police.name}</div>
                        <div className="text-emerald-700 font-bold">{nearestFacilities.nearest_police.distance_km} km ({nearestFacilities.nearest_police.bearing}) • {nearestFacilities.nearest_police.phone}</div>
                      </div>
                      <div className="bg-white p-2 rounded border border-slate-200 shadow-2xs">
                        <div className="font-bold text-slate-900">🚜 Road Clearance Base</div>
                        <div className="text-slate-700 truncate">{nearestFacilities.nearest_clearance_unit.name}</div>
                        <div className="text-emerald-700 font-bold">{nearestFacilities.nearest_clearance_unit.distance_km} km ({nearestFacilities.nearest_clearance_unit.bearing}) • {nearestFacilities.nearest_clearance_unit.phone}</div>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* Sign-off Block */}
            <div className="pt-3 border-t border-slate-300 flex justify-between items-end text-[9px] text-slate-600">
              <div>
                <p><strong>Issued By:</strong> NER Landslide Early Warning & Decision Support System (EWDSS)</p>
                <p><strong>Classification:</strong> OFFICIAL INCIDENT SITUATION REPORT · IMMEDIATE DISPATCH</p>
              </div>
              <div className="text-right w-48">
                <p className="font-semibold text-slate-800">Duty Incident Commander</p>
                <div className="border-b border-dashed border-slate-500 my-2"></div>
                <p className="text-[8px] text-slate-500">Official Stamp & Digital Signature</p>
              </div>
            </div>

          </div>
        </div>

      </div>
    </div>
  );
}
