import { useState, useEffect, useRef } from 'react';
import { 
  Navigation, 
  MapPin, 
  AlertTriangle, 
  Volume2, 
  VolumeX, 
  Radio, 
  ShieldAlert, 
  Compass, 
  Route, 
  Sparkles, 
  CheckCircle2, 
  ExternalLink,
  Search,
  X,
  Play,
  RotateCcw
} from 'lucide-react';
import { 
  isAudioMuted, 
  isVoiceEnabled, 
  setVoiceEnabled, 
  playTravelSafetyVoiceAlert, 
  testTravelVoiceAlert 
} from '../services/emergencyAudioService';
import { 
  fetchTravelRiskZones, 
  evaluateTravelSafety, 
  startGeolocationWatch, 
  resetTravelAlertStates 
} from '../services/travelSafetyService';

// Curated NER Travel Destinations for rapid selection
const POPULAR_DESTINATIONS = [
  { name: 'Shillong (Meghalaya)', lat: 25.5788, lng: 91.8933 },
  { name: 'Gangtok (Sikkim)', lat: 27.3389, lng: 88.6065 },
  { name: 'Tawang (Arunachal Pradesh)', lat: 27.5861, lng: 91.8594 },
  { name: 'Kohima (Nagaland)', lat: 25.6751, lng: 94.1086 },
  { name: 'Haflong (Assam)', lat: 25.1667, lng: 93.0167 },
  { name: 'Aizawl (Mizoram)', lat: 23.7271, lng: 92.7176 },
  { name: 'Imphal (Manipur)', lat: 24.8170, lng: 93.9368 },
  { name: 'Silchar (Assam)', lat: 24.8333, lng: 92.7789 }
];

export default function TravelSafetyCard({
  onLocateOnMap,
  onTravelStateChange,
  className = ""
}) {
  // Core Travel Monitoring States
  const [isMonitoring, setIsMonitoring] = useState(false);
  const [voiceAlertsActive, setVoiceAlertsActive] = useState(() => isVoiceEnabled());
  const [gpsStatus, setGpsStatus] = useState('DISCONNECTED'); // CONNECTED, SEARCHING, DISCONNECTED, ERROR
  const [gpsError, setGpsError] = useState(null);
  
  // Real-time Position & Previous Position
  const [currentLocation, setCurrentLocation] = useState(null);
  const [previousLocation, setPreviousLocation] = useState(null);

  // Destination & Routes
  const [destinationQuery, setDestinationQuery] = useState('');
  const [selectedDestination, setSelectedDestination] = useState(null);
  const [showDestDropdown, setShowDestDropdown] = useState(false);

  // Hazard Zones & Active Alert
  const [riskZones, setRiskZones] = useState([]);
  const [activeAlert, setActiveAlert] = useState(null);
  const [isDemoMode, setIsDemoMode] = useState(false);

  const prevLocationRef = useRef(null);
  const stopWatchRef = useRef(null);

  // Synchronize state changes to parent (for InteractiveMap overlays)
  useEffect(() => {
    if (onTravelStateChange) {
      onTravelStateChange({
        isMonitoring,
        travelerLocation: currentLocation,
        travelDestination: selectedDestination,
        riskZones,
        activeAlert,
        voiceAlertsActive
      });
    }
  }, [isMonitoring, currentLocation, selectedDestination, riskZones, activeAlert, voiceAlertsActive, onTravelStateChange]);

  // Load hazard corridors on mount
  useEffect(() => {
    fetchTravelRiskZones(0.0).then((zones) => {
      setRiskZones(zones || []);
    });
  }, []);

  // Handle Travel Monitoring Toggle
  const toggleMonitoring = () => {
    if (isMonitoring) {
      // Turn OFF
      if (stopWatchRef.current) {
        stopWatchRef.current();
        stopWatchRef.current = null;
      }
      setIsMonitoring(false);
      setGpsStatus('DISCONNECTED');
      setActiveAlert(null);
      setIsDemoMode(false);
      resetTravelAlertStates();
    } else {
      // Turn ON
      setIsMonitoring(true);
      setGpsStatus('SEARCHING');
      setGpsError(null);
      setIsDemoMode(false);

      // Start Browser Geolocation Watcher
      const stopFn = startGeolocationWatch({
        onLocationUpdate: (pos) => {
          setGpsStatus('CONNECTED');
          setGpsError(null);
          setPreviousLocation(prevLocationRef.current);
          setCurrentLocation({
            lat: pos.lat,
            lng: pos.lng,
            heading: pos.heading,
            speed: pos.speed
          });
          prevLocationRef.current = { lat: pos.lat, lng: pos.lng };
        },
        onError: (err) => {
          setGpsStatus('ERROR');
          setGpsError(err.message);
        }
      });
      stopWatchRef.current = stopFn;
    }
  };

  // Evaluate safety whenever location or hazard zones update
  useEffect(() => {
    if (!isMonitoring || !currentLocation || isDemoMode) return;

    const { activeAlert: detectedAlert } = evaluateTravelSafety({
      prevLoc: previousLocation,
      currLoc: currentLocation,
      zones: riskZones,
      voiceAlertsEnabled: voiceAlertsActive && !isAudioMuted()
    });

    setActiveAlert(detectedAlert);
  }, [currentLocation, previousLocation, riskZones, isMonitoring, voiceAlertsActive, isDemoMode]);

  // Clean up watcher on unmount
  useEffect(() => {
    return () => {
      if (stopWatchRef.current) {
        stopWatchRef.current();
      }
      resetTravelAlertStates();
    };
  }, []);

  // Toggle Voice Alerts
  const handleToggleVoice = () => {
    const next = !voiceAlertsActive;
    setVoiceAlertsActive(next);
    setVoiceEnabled(next);
  };

  // Developer & SIH Demo Simulation: Simulate user approaching Sonapur Tunnel at 9.2 km with 85% risk
  const handleStartDemoSimulation = () => {
    setIsDemoMode(true);
    setIsMonitoring(true);
    setGpsStatus('CONNECTED');
    setGpsError(null);

    // Sonapur Tunnel is at 25.1012, 92.3654.
    // 9.2 km north-west is approx 25.1650, 92.3150
    const simLat = 25.1650;
    const simLng = 92.3150;
    const simLocation = { lat: simLat, lng: simLng, heading: 145, speed: 14.5 };

    setCurrentLocation(simLocation);
    setSelectedDestination({ name: 'Silchar (via NH-06)', lat: 24.8333, lng: 92.7789 });

    const demoZone = {
      id: 'corridor-nh06-sonapur',
      name: 'Sonapur Tunnel Corridor (NH-06)',
      highway: 'NH-06',
      state: 'Meghalaya',
      latitude: 25.1012,
      longitude: 92.3654,
      risk_probability: 85.0,
      severity: 'CRITICAL',
      source: 'CompositeRiskEngine (Simulation)',
      advisory: 'Critical mudflow & rockfall warning ahead. Road partially constricted.'
    };

    setActiveAlert({
      zone: demoZone,
      distanceKm: 9.2,
      isUrgent: false,
      riskScore: 85.0
    });

    // Play Voice Alert
    if (voiceAlertsActive && !isAudioMuted()) {
      playTravelSafetyVoiceAlert({
        riskScore: 85,
        distanceKm: 9.2,
        regionName: 'Sonapur Tunnel Corridor (NH-06)',
        isUrgent: false,
        force: true
      });
    }

    if (onLocateOnMap) {
      onLocateOnMap(simLat, simLng);
    }
  };

  const handleResetDemo = () => {
    setIsDemoMode(false);
    setActiveAlert(null);
    setCurrentLocation(null);
    setPreviousLocation(null);
    setSelectedDestination(null);
    setDestinationQuery('');
    setGpsStatus('DISCONNECTED');
    setIsMonitoring(false);
    resetTravelAlertStates();
  };

  return (
    <div className={`bg-[var(--card-bg)] border border-[var(--border-subtle)] rounded-xl shadow-md overflow-hidden transition ${className}`}>
      {/* Card Header */}
      <div className="bg-[var(--panel-bg)] border-b border-[var(--border-subtle)] p-4 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded-lg bg-sky-500/10 text-sky-500 border border-sky-500/25 shrink-0">
            <Navigation className="h-5 w-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="font-bold text-sm sm:text-base text-[var(--text-main)]">Travel Safety Mode</h3>
              {isDemoMode && (
                <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-400 border border-amber-500/30">
                  TEST / SIMULATION
                </span>
              )}
            </div>
            <p className="text-[11px] text-[var(--text-muted)]">
              Highway route monitoring & 10 km landslide voice warning
            </p>
          </div>
        </div>

        {/* Monitoring Master Switch */}
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold text-[var(--text-dim)]">Monitoring:</span>
            <button
              onClick={toggleMonitoring}
              className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors cursor-pointer ${
                isMonitoring ? 'bg-emerald-600' : 'bg-slate-700'
              }`}
              title={isMonitoring ? 'Disable travel route monitoring' : 'Enable live GPS route monitoring'}
            >
              <span
                className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                  isMonitoring ? 'translate-x-6' : 'translate-x-1'
                }`}
              />
            </button>
            <span className={`text-xs font-bold font-mono ${isMonitoring ? 'text-emerald-500' : 'text-[var(--text-muted)]'}`}>
              {isMonitoring ? 'ON' : 'OFF'}
            </span>
          </div>
        </div>
      </div>

      <div className="p-4 sm:p-5 space-y-4">
        {/* Telemetry Status Bar */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          {/* GPS Connection */}
          <div className="bg-[var(--subcard-bg)] border border-[var(--border-subtle)] rounded-lg p-2.5 space-y-1">
            <div className="flex items-center justify-between text-[11px]">
              <span className="text-[var(--text-dim)] font-medium">GPS Signal</span>
              <span className={`inline-flex items-center gap-1 font-bold text-[10px] uppercase ${
                gpsStatus === 'CONNECTED' ? 'text-emerald-500' :
                gpsStatus === 'SEARCHING' ? 'text-amber-500 animate-pulse' :
                gpsStatus === 'ERROR' ? 'text-rose-500' : 'text-[var(--text-muted)]'
              }`}>
                <span className={`h-2 w-2 rounded-full ${
                  gpsStatus === 'CONNECTED' ? 'bg-emerald-500' :
                  gpsStatus === 'SEARCHING' ? 'bg-amber-500' :
                  gpsStatus === 'ERROR' ? 'bg-rose-500' : 'bg-slate-500'
                }`} />
                {gpsStatus}
              </span>
            </div>
            <p className="text-xs font-mono font-bold text-[var(--text-main)] truncate">
              {currentLocation
                ? `${currentLocation.lat.toFixed(4)}°N, ${currentLocation.lng.toFixed(4)}°E`
                : 'Awaiting Location...'}
            </p>
          </div>

          {/* Voice Alerts Toggle */}
          <div className="bg-[var(--subcard-bg)] border border-[var(--border-subtle)] rounded-lg p-2.5 flex items-center justify-between">
            <div className="space-y-0.5">
              <span className="text-[11px] text-[var(--text-dim)] font-medium block">Voice Alerts</span>
              <span className={`text-xs font-bold ${voiceAlertsActive ? 'text-emerald-500' : 'text-[var(--text-muted)]'}`}>
                {voiceAlertsActive ? 'Enabled (Active)' : 'Muted'}
              </span>
            </div>
            <button
              onClick={handleToggleVoice}
              className={`p-2 rounded-lg border transition cursor-pointer ${
                voiceAlertsActive
                  ? 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30 hover:bg-emerald-500/25'
                  : 'bg-[var(--card-bg)] text-[var(--text-muted)] border-[var(--border-subtle)] hover:text-[var(--text-main)]'
              }`}
              title={voiceAlertsActive ? 'Disable voice alerts' : 'Enable automated voice alerts'}
            >
              {voiceAlertsActive ? <Volume2 className="h-4 w-4" /> : <VolumeX className="h-4 w-4" />}
            </button>
          </div>

          {/* Quick Voice Audio Test */}
          <div className="bg-[var(--subcard-bg)] border border-[var(--border-subtle)] rounded-lg p-2.5 flex items-center justify-between">
            <div className="space-y-0.5">
              <span className="text-[11px] text-[var(--text-dim)] font-medium block">Audio Synthesizer</span>
              <span className="text-[10px] text-[var(--text-muted)]">Web Speech API</span>
            </div>
            <button
              onClick={() => testTravelVoiceAlert()}
              className="px-2.5 py-1.5 bg-sky-600/20 hover:bg-sky-600/30 text-sky-400 border border-sky-500/30 rounded-lg text-xs font-bold flex items-center gap-1.5 transition cursor-pointer"
              title="Test authoritative EBS chime and dynamic voice announcement"
            >
              <Play className="h-3 w-3" />
              <span>Test Audio</span>
            </button>
          </div>
        </div>

        {/* GPS Error Warning Notice */}
        {gpsError && (
          <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/25 text-rose-500 text-xs flex items-start gap-2">
            <AlertTriangle className="h-4 w-4 shrink-0 mt-0.5" />
            <div className="space-y-0.5">
              <p className="font-bold">GPS Access Limited</p>
              <p className="text-[11px] text-rose-400/90">{gpsError}</p>
            </div>
          </div>
        )}

        {/* Destination Selection Bar */}
        <div className="space-y-1.5 relative">
          <label className="text-[11px] font-bold uppercase tracking-wider text-[var(--text-dim)] flex items-center gap-1.5">
            <Route className="h-3.5 w-3.5 text-purple-500" />
            <span>Planned Travel Destination (Optional Corridor Analysis)</span>
          </label>

          <div className="flex gap-2">
            <div className="relative flex-1">
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-[var(--text-muted)]">
                <Search className="h-4 w-4" />
              </div>
              <input
                type="text"
                value={destinationQuery || (selectedDestination ? selectedDestination.name : '')}
                onChange={(e) => {
                  setDestinationQuery(e.target.value);
                  setSelectedDestination(null);
                  setShowDestDropdown(true);
                }}
                onFocus={() => setShowDestDropdown(true)}
                placeholder="Search destination town or highway (e.g., Shillong, Gangtok, Tawang)..."
                className="w-full pl-9 pr-8 py-2 bg-[var(--input-bg)] border border-[var(--border-subtle)] rounded-lg text-xs text-[var(--text-main)] placeholder-[var(--text-muted)] focus:outline-none focus:border-sky-500 transition"
              />
              {(destinationQuery || selectedDestination) && (
                <button
                  onClick={() => {
                    setDestinationQuery('');
                    setSelectedDestination(null);
                  }}
                  className="absolute inset-y-0 right-0 pr-2.5 flex items-center text-[var(--text-muted)] hover:text-[var(--text-main)] cursor-pointer"
                >
                  <X className="h-3.5 w-3.5" />
                </button>
              )}
            </div>

            {selectedDestination && onLocateOnMap && (
              <button
                onClick={() => onLocateOnMap(selectedDestination.lat, selectedDestination.lng)}
                className="px-3 py-2 bg-[var(--subcard-bg)] hover:bg-[var(--card-bg)] border border-[var(--border-subtle)] rounded-lg text-xs font-semibold text-[var(--text-main)] flex items-center gap-1 transition cursor-pointer"
                title="View Destination on Map"
              >
                <MapPin className="h-3.5 w-3.5 text-purple-500" />
                <span className="hidden sm:inline">View</span>
              </button>
            )}
          </div>

          {/* Autocomplete Dropdown */}
          {showDestDropdown && (
            <div className="absolute z-50 left-0 right-0 mt-1 bg-[var(--modal-bg)] border border-[var(--border-subtle)] rounded-lg shadow-xl overflow-hidden max-h-48 overflow-y-auto text-xs">
              <div className="p-1.5 text-[10px] font-bold text-[var(--text-dim)] uppercase tracking-wider bg-[var(--subcard-bg)] border-b border-[var(--border-subtle)]">
                Popular NER Corridors
              </div>
              {POPULAR_DESTINATIONS
                .filter(d => !destinationQuery || d.name.toLowerCase().includes(destinationQuery.toLowerCase()))
                .map((dest) => (
                  <button
                    key={dest.name}
                    onClick={() => {
                      setSelectedDestination(dest);
                      setDestinationQuery(dest.name);
                      setShowDestDropdown(false);
                    }}
                    className="w-full text-left px-3 py-2 hover:bg-[var(--subcard-bg)] flex items-center justify-between text-[var(--text-main)] transition cursor-pointer border-b border-[var(--border-subtle)]/50 last:border-0"
                  >
                    <span className="font-semibold">{dest.name}</span>
                    <span className="text-[10px] font-mono text-[var(--text-dim)]">
                      {dest.lat.toFixed(2)}°N, {dest.lng.toFixed(2)}°E
                    </span>
                  </button>
                ))}
            </div>
          )}
        </div>

        {/* ======================================================= */}
        {/* ACTIVE TRAVEL SAFETY WARNING BANNER (When Danger Ahead) */}
        {/* ======================================================= */}
        {activeAlert && (
          <div className="p-4 rounded-xl bg-gradient-to-r from-rose-900/30 via-rose-800/20 to-amber-900/20 border-2 border-rose-500/60 shadow-lg animate-pulse-slow space-y-3">
            <div className="flex items-start justify-between gap-3">
              <div className="flex items-center gap-2.5">
                <div className="p-2 rounded-lg bg-rose-600 text-white shadow-md shadow-rose-600/40 shrink-0">
                  <ShieldAlert className="h-5 w-5 animate-bounce" />
                </div>
                <div>
                  <span className="text-[10px] font-black uppercase tracking-wider px-2 py-0.5 rounded bg-rose-500/20 text-rose-400 border border-rose-500/40">
                    🚨 Travel Safety Warning
                  </span>
                  <h4 className="text-base font-black text-white mt-1">
                    HIGH LANDSLIDE RISK AHEAD
                  </h4>
                </div>
              </div>

              {/* View on Map Button */}
              {onLocateOnMap && activeAlert.zone && (
                <button
                  onClick={() => onLocateOnMap(activeAlert.zone.latitude, activeAlert.zone.longitude)}
                  className="px-3 py-1.5 bg-rose-600 hover:bg-rose-500 text-white rounded-lg text-xs font-bold shadow transition flex items-center gap-1.5 cursor-pointer shrink-0"
                >
                  <ExternalLink className="h-3.5 w-3.5" />
                  <span>View on Map</span>
                </button>
              )}
            </div>

            {/* Dynamic Telemetry Metric Pills */}
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 text-xs">
              <div className="bg-black/30 border border-rose-500/30 rounded-lg p-2">
                <span className="text-[10px] text-rose-300/80 block font-bold uppercase">Estimated Risk</span>
                <span className="text-lg font-black text-rose-400 font-mono">
                  {Math.round(activeAlert.riskScore)}%
                </span>
              </div>
              <div className="bg-black/30 border border-rose-500/30 rounded-lg p-2">
                <span className="text-[10px] text-rose-300/80 block font-bold uppercase">Hazard Distance</span>
                <span className="text-lg font-black text-amber-300 font-mono">
                  {activeAlert.distanceKm} km
                </span>
              </div>
              <div className="bg-black/30 border border-rose-500/30 rounded-lg p-2 col-span-2 sm:col-span-1">
                <span className="text-[10px] text-rose-300/80 block font-bold uppercase">Corridor / Region</span>
                <span className="text-xs font-bold text-white truncate block" title={activeAlert.zone.name}>
                  {activeAlert.zone.name}
                </span>
              </div>
            </div>

            {/* Travel Advisory Message */}
            <p className="text-xs text-rose-200/90 leading-relaxed bg-black/20 p-2.5 rounded-lg border border-rose-500/20">
              ⚠️ You are actively approaching a monitored high-risk landslide zone within 10 km.
              Please consider an alternative route, reduce transit speed, and follow local safety advisories.
            </p>

            {/* Voice Alert Active Indicator */}
            <div className="flex items-center justify-between text-[11px] text-rose-300/80 pt-1 border-t border-rose-500/20">
              <div className="flex items-center gap-1.5">
                <Radio className="h-3.5 w-3.5 text-rose-400 animate-pulse" />
                <span>{voiceAlertsActive ? 'Voice Alert Dispatched' : 'Voice Alert Muted (Visual Only)'}</span>
              </div>
              <span className="font-mono text-[10px]">Threshold: &gt;70% Risk within 10 km</span>
            </div>
          </div>
        )}

        {/* Developer / SIH Demo Simulation Bar */}
        <div className="pt-2 border-t border-[var(--border-subtle)] flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-1.5 text-xs text-[var(--text-dim)]">
            <Sparkles className="h-3.5 w-3.5 text-amber-500" />
            <span className="font-medium">SIH 2026 Demonstration Suite:</span>
          </div>

          <div className="flex items-center gap-2">
            {!isDemoMode ? (
              <button
                onClick={handleStartDemoSimulation}
                className="px-3 py-1.5 bg-amber-500/15 hover:bg-amber-500/25 text-amber-400 border border-amber-500/30 rounded-lg text-xs font-bold flex items-center gap-1.5 transition cursor-pointer"
                title="Simulate approaching traveler 9.2 km from Sonapur Tunnel (85% risk) with dynamic voice alert"
              >
                <span>Simulate Danger Ahead (9.2 km @ 85%)</span>
              </button>
            ) : (
              <button
                onClick={handleResetDemo}
                className="px-3 py-1.5 bg-slate-700 hover:bg-slate-600 text-slate-200 rounded-lg text-xs font-bold flex items-center gap-1.5 transition cursor-pointer"
                title="Reset simulation and return to standby"
              >
                <RotateCcw className="h-3 w-3" />
                <span>Reset Simulation</span>
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
