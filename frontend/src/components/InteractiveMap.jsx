import { useState, useEffect, useRef, useMemo } from 'react'
import { MapContainer, TileLayer, Marker, Rectangle, Tooltip, Popup, useMapEvents, ImageOverlay, Polyline, Circle } from 'react-leaflet'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import LocationSearchBar from './LocationSearchBar'
import { computeNearestFacilities, isCoordinateInNER } from '../services/emergencyFacilitiesData'
import { getApiBaseUrl } from '../services/apiConfig'

// Custom pulsing SVG marker icon representing live traveler GPS position
const travelerVehicleIcon = new L.DivIcon({
  className: 'traveler-vehicle-icon',
  html: `
    <div class="relative flex items-center justify-center">
      <span class="absolute inline-flex h-9 w-9 animate-ping rounded-full bg-sky-500 opacity-60"></span>
      <div class="relative rounded-full h-7 w-7 bg-sky-600 border-2 border-white shadow-xl flex items-center justify-center text-white text-xs font-bold">
        🚗
      </div>
    </div>
  `,
  iconSize: [32, 32],
  iconAnchor: [16, 16]
})

// Custom marker icon representing travel destination
const destinationPinIcon = new L.DivIcon({
  className: 'destination-pin-icon',
  html: `
    <div class="relative flex items-center justify-center">
      <div class="rounded-full h-6 w-6 bg-purple-600 border-2 border-white shadow-lg flex items-center justify-center text-white text-[11px] font-bold">
        🏁
      </div>
    </div>
  `,
  iconSize: [26, 26],
  iconAnchor: [13, 13]
})

// Custom marker icon for travel danger corridors with animated warning badge
const getDangerZoneIcon = (zone, isActiveAlert) => {
  const isCritical = (zone.risk_probability || 0) >= 85 || zone.severity === 'CRITICAL'
  const bgColor = isCritical ? 'bg-rose-600' : 'bg-amber-600'
  const pingColor = isCritical ? 'bg-rose-500' : 'bg-amber-500'
  const pingClass = isActiveAlert ? 'h-10 w-10 opacity-90' : 'h-6 w-6 opacity-40'

  return new L.DivIcon({
    className: 'danger-zone-marker',
    html: `
      <div class="relative flex items-center justify-center">
        <span class="absolute inline-flex ${pingClass} animate-ping rounded-full ${pingColor}"></span>
        <div class="relative rounded-full h-6 w-6 ${bgColor} border-2 border-white shadow-lg flex items-center justify-center text-white text-[10px] font-bold">
          ⚠️
        </div>
      </div>
    `,
    iconSize: [26, 26],
    iconAnchor: [13, 13]
  })
}

// Custom pulsing SVG marker icon representing selected location
const selectedLocationIcon = new L.DivIcon({
  className: 'custom-pin-icon',
  html: `
    <div class="relative flex items-center justify-center">
      <span class="absolute inline-flex h-6 w-6 animate-ping rounded-full bg-emerald-500 opacity-75"></span>
      <div class="relative rounded-full h-4.5 w-4.5 bg-emerald-600 border-2 border-white shadow-lg shadow-emerald-500/50"></div>
    </div>
  `,
  iconSize: [24, 24],
  iconAnchor: [12, 12]
})

// Custom pulsing SVG marker icon representing selected location OUTSIDE NER
const outsideNerLocationIcon = new L.DivIcon({
  className: 'custom-pin-icon-outside-ner',
  html: `
    <div class="relative flex items-center justify-center">
      <span class="absolute inline-flex h-6 w-6 animate-ping rounded-full bg-amber-500 opacity-75"></span>
      <div class="relative rounded-full h-4.5 w-4.5 bg-amber-600 border-2 border-white shadow-lg shadow-amber-500/50"></div>
    </div>
  `,
  iconSize: [24, 24],
  iconAnchor: [12, 12]
})

// Custom marker icon representing a GSI historical inventory landslide (orange dot)
const gsiMarkerIcon = new L.DivIcon({
  className: 'gsi-marker-icon',
  html: `
    <div class="relative flex items-center justify-center">
      <div class="rounded-full h-3 w-3 bg-amber-500 border border-white shadow-md"></div>
    </div>
  `,
  iconSize: [12, 12],
  iconAnchor: [6, 6]
})

// Custom marker icon representing a NASA historical landslide event (red dot)
const nasaMarkerIcon = new L.DivIcon({
  className: 'nasa-marker-icon',
  html: `
    <div class="relative flex items-center justify-center">
      <span class="absolute inline-flex h-4 w-4 animate-ping rounded-full bg-rose-500 opacity-60"></span>
      <div class="relative rounded-full h-3 w-3 bg-rose-600 border border-white shadow-md"></div>
    </div>
  `,
  iconSize: [12, 12],
  iconAnchor: [6, 6]
})

// Custom marker generator for Field Intelligence ground reports
const getFieldReportMarkerIcon = (report) => {
  const isVerified = report.status === 'VERIFIED'
  const isCritical = report.severity === 'CRITICAL'
  const bgColor = isCritical ? 'bg-rose-500' : isVerified ? 'bg-emerald-500' : 'bg-amber-500'
  const ringColor = isCritical ? 'bg-rose-500' : isVerified ? 'bg-emerald-500' : 'bg-amber-500'

  return new L.DivIcon({
    className: 'field-report-marker',
    html: `
      <div class="relative flex items-center justify-center">
        <span class="absolute inline-flex h-5 w-5 animate-ping rounded-full ${ringColor} opacity-40"></span>
        <div class="relative rounded-full h-3.5 w-3.5 ${bgColor} border-2 border-white shadow-lg"></div>
      </div>
    `,
    iconSize: [16, 16],
    iconAnchor: [8, 8]
  })
}

// Custom marker icons for Verified Regional Emergency Facilities
const facilityHospitalIcon = new L.DivIcon({
  className: 'facility-hospital-icon',
  html: `
    <div class="relative flex items-center justify-center">
      <div class="rounded-full h-6 w-6 bg-rose-600 border-2 border-white shadow-md flex items-center justify-center text-white text-[12px] font-bold">
        ✚
      </div>
    </div>
  `,
  iconSize: [24, 24],
  iconAnchor: [12, 12]
})

const facilityShelterIcon = new L.DivIcon({
  className: 'facility-shelter-icon',
  html: `
    <div class="relative flex items-center justify-center">
      <div class="rounded-full h-6 w-6 bg-emerald-600 border-2 border-white shadow-md flex items-center justify-center text-white text-[11px] font-bold">
        ⌂
      </div>
    </div>
  `,
  iconSize: [24, 24],
  iconAnchor: [12, 12]
})

const facilityPoliceIcon = new L.DivIcon({
  className: 'facility-police-icon',
  html: `
    <div class="relative flex items-center justify-center">
      <div class="rounded-full h-6 w-6 bg-blue-600 border-2 border-white shadow-md flex items-center justify-center text-white text-[11px] font-bold">
        ★
      </div>
    </div>
  `,
  iconSize: [24, 24],
  iconAnchor: [12, 12]
})

const facilityBroIcon = new L.DivIcon({
  className: 'facility-bro-icon',
  html: `
    <div class="relative flex items-center justify-center">
      <div class="rounded-full h-6 w-6 bg-amber-600 border-2 border-white shadow-md flex items-center justify-center text-white text-[11px] font-bold">
        ⚒
      </div>
    </div>
  `,
  iconSize: [24, 24],
  iconAnchor: [12, 12]
})

// Road Connectivity Visual Styling Matrix
const ROAD_STYLE_CONFIG = {
  NORMAL: {
    color: '#10b981', // Emerald
    weight: 3.5,
    opacity: 0.8,
    dashArray: null,
    label: 'Normal',
    badge: 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30'
  },
  MONITOR: {
    color: '#38bdf8', // Sky
    weight: 4.0,
    opacity: 0.85,
    dashArray: '6, 4',
    label: 'Monitor',
    badge: 'bg-sky-500/15 text-sky-400 border-sky-500/30'
  },
  AT_RISK: {
    color: '#f59e0b', // Amber
    weight: 4.5,
    opacity: 0.9,
    dashArray: '8, 4',
    label: 'At Risk',
    badge: 'bg-amber-500/15 text-amber-400 border-amber-500/30'
  },
  BLOCKED: {
    color: '#ef4444', // Red
    weight: 5.5,
    opacity: 1.0,
    dashArray: '4, 4',
    label: 'Blocked',
    badge: 'bg-rose-500/15 text-rose-400 border-rose-500/30'
  },
  SEVERELY_IMPACTED: {
    color: '#e11d48', // Deep Rose
    weight: 6.0,
    opacity: 1.0,
    dashArray: null,
    label: 'Severely Impacted',
    badge: 'bg-rose-600/20 text-rose-300 border-rose-500/40'
  }
}

// Sub-component to handle map click events
function MapClickHandler({ onMapClick }) {
  useMapEvents({
    click(e) {
      onMapClick(e.latlng);
    },
  });
  return null;
}

// Sub-component to programmatically fit bounds of the AOI bounding box or fly to selected location
function MapController({ aoi, selectedLocation }) {
  const map = useMapEvents({});
  const lastTargetRef = useRef(null);

  useEffect(() => {
    try {
      if (aoi && aoi.bounding_box) {
        const bounds = [
          [aoi.bounding_box.south, aoi.bounding_box.west],
          [aoi.bounding_box.north, aoi.bounding_box.east]
        ];
        map.fitBounds(bounds, { padding: [50, 50], maxZoom: 11, animate: true });
        lastTargetRef.current = null;
      } else if (selectedLocation && typeof selectedLocation.lat === 'number' && typeof selectedLocation.lng === 'number') {
        const isDifferent =
          !lastTargetRef.current ||
          Math.abs(lastTargetRef.current.lat - selectedLocation.lat) > 0.0001 ||
          Math.abs(lastTargetRef.current.lng - selectedLocation.lng) > 0.0001;

        if (isDifferent) {
          lastTargetRef.current = selectedLocation;
          map.flyTo([selectedLocation.lat, selectedLocation.lng], Math.max(map.getZoom(), 11), {
            animate: true,
            duration: 1.2
          });
        }
      }
    } catch (e) {
      console.warn('MapController camera adjustment error:', e);
    }
  }, [aoi, selectedLocation, map]);
  return null;
}

export default function InteractiveMap({
  selectedLocation,
  onLocationSelect,
  aoi,
  historicalData = null,
  activeOverlay = null,
  setActiveOverlay = () => {},
  overlayOpacity = 0.6,
  setOverlayOpacity = () => {},
  terrainData = null,
  weatherData = null,
  fieldReports = [],
  roadData = null,
  isRoadLoading = false,
  roadError = null,
  showRoads = true,
  setShowRoads = () => {},
  travelMonitoringActive = false,
  travelerLocation = null,
  travelDestination = null,
  travelRiskZones = [],
  activeTravelAlert = null
}) {
  // Geographic center of the North Eastern Region (NER) of India
  const centerNER = [26.2006, 92.5000] // Guwahati, Assam area
  const initialZoom = 7

  // Overlay resource states
  const [loadedOverlayUrl, setLoadedOverlayUrl] = useState(null)
  const [loadedOverlayBounds, setLoadedOverlayBounds] = useState(null)
  const [isLoadingOverlay, setIsLoadingOverlay] = useState(false)
  const [overlayError, setOverlayError] = useState(null)
  const [showFacilities, setShowFacilities] = useState(true)

  // Nearest emergency facilities mathematically derived from selectedLocation (only when inside NER)
  const nearestFacilities = useMemo(() => {
    if (!selectedLocation?.lat || !selectedLocation?.lng) return null
    if (!isCoordinateInNER(selectedLocation.lat, selectedLocation.lng)) return null
    return computeNearestFacilities(selectedLocation.lat, selectedLocation.lng)
  }, [selectedLocation?.lat, selectedLocation?.lng])

  const nearestFacilitiesList = useMemo(() => {
    if (!nearestFacilities) return []
    return [
      nearestFacilities.nearest_hospital,
      nearestFacilities.nearest_shelter,
      nearestFacilities.nearest_police,
      nearestFacilities.nearest_clearance_unit
    ].filter(Boolean)
  }, [nearestFacilities])

  // Ref to track loaded URL for clean unmount revocation
  const urlRef = useRef(null)

  useEffect(() => {
    urlRef.current = loadedOverlayUrl
  }, [loadedOverlayUrl])

  // Cleanup Object URL on unmount
  useEffect(() => {
    return () => {
      if (urlRef.current) {
        URL.revokeObjectURL(urlRef.current)
      }
    }
  }, [])

  // Handle overlay download and bounds extraction on layer/scene updates
  useEffect(() => {
    if (loadedOverlayUrl) {
      URL.revokeObjectURL(loadedOverlayUrl)
      setLoadedOverlayUrl(null)
    }
    setLoadedOverlayBounds(null)
    setOverlayError(null)

    if (!activeOverlay || !terrainData || !terrainData.scene_id) {
      return
    }

    const sceneId = terrainData.scene_id
    const controller = new AbortController()

    const apiBase = getApiBaseUrl()
    let endpointUrl = ""
    if (['slope', 'dem', 'aspect'].includes(activeOverlay)) {
      endpointUrl = `${apiBase}/v1/terrain/scenes/${sceneId}/overlay?layer=${activeOverlay}`
    } else if (['vv', 'vh'].includes(activeOverlay)) {
      endpointUrl = `${apiBase}/v1/satellite/scenes/${sceneId}/overlay?layer=${activeOverlay}`
    } else if (activeOverlay === 'risk') {
      const params = new URLSearchParams()
      params.set("resolution", "25")
      if (weatherData) {
        const daily = weatherData.daily_precipitation
        const precip3d = weatherData.three_day_cumulative
        const precip7d = weatherData.seven_day_cumulative
        
        if (typeof daily === 'number' && !isNaN(daily)) {
          params.set("rainfall", daily.toString())
        }
        if (typeof precip3d === 'number' && !isNaN(precip3d)) {
          params.set("rainfall_3d", precip3d.toString())
        }
        if (typeof precip7d === 'number' && !isNaN(precip7d)) {
          params.set("rainfall_7d", precip7d.toString())
        }
      }
      endpointUrl = `${apiBase}/v1/terrain/scenes/${sceneId}/risk?${params.toString()}`
    } else {
      return
    }

    setIsLoadingOverlay(true)

    async function loadRasterOverlay() {
      try {
        const response = await fetch(endpointUrl, { signal: controller.signal })
        if (!response.ok) {
          if (response.status === 404) {
            throw new Error("Overlay unavailable. Process the scene first.")
          } else {
            throw new Error(`HTTP Error ${response.status}: Calculation failed on server.`)
          }
        }

        const boundsHeader = response.headers.get("X-Raster-Bounds")
        if (!boundsHeader) {
          throw new Error("Geographic bounds header missing from response.")
        }

        const bounds = JSON.parse(boundsHeader)
        const blob = await response.blob()
        const objUrl = URL.createObjectURL(blob)

        setLoadedOverlayUrl(objUrl)
        setLoadedOverlayBounds(bounds)
        setIsLoadingOverlay(false)
      } catch (err) {
        if (err.name === 'AbortError') {
          return
        }
        console.error("[Raster Overlay Error] Failed to load overlay:", err)
        setOverlayError(err.message || "Failed to load raster overlay.")
        setIsLoadingOverlay(false)
      }
    }

    loadRasterOverlay()

    return () => {
      controller.abort()
    }
  }, [activeOverlay, terrainData?.scene_id, activeOverlay === 'risk' ? weatherData : null])

  const handleMapClick = (latlng) => {
    if (onLocationSelect) {
      onLocationSelect(latlng)
    }
  }

  const handleClearSelection = (e) => {
    e.stopPropagation()
    if (onLocationSelect) {
      onLocationSelect(null)
    }
  }

  // Dynamic CSS injection for dark command center & light GIS console
  const dynamicMapStyle = `
    .dark .leaflet-tile, [data-theme="dark"] .leaflet-tile {
      filter: invert(1) hue-rotate(180deg) brightness(92%) contrast(92%);
    }
    .light .leaflet-tile, [data-theme="light"] .leaflet-tile {
      filter: contrast(100%) brightness(98%);
    }
    .dark .leaflet-container, [data-theme="dark"] .leaflet-container {
      background: #07100d !important;
      font-family: inherit;
    }
    .light .leaflet-container, [data-theme="light"] .leaflet-container {
      background: #e4e9e4 !important;
      font-family: inherit;
    }
    .dark .leaflet-bar, [data-theme="dark"] .leaflet-bar {
      border: 1px solid #1a2d21 !important;
      box-shadow: none !important;
    }
    .light .leaflet-bar, [data-theme="light"] .leaflet-bar {
      border: 1px solid #cbd5cb !important;
      box-shadow: none !important;
    }
    .dark .leaflet-bar a, [data-theme="dark"] .leaflet-bar a {
      background-color: #0d1a12 !important;
      color: #f1f5f3 !important;
      border-bottom: 1px solid #1a2d21 !important;
    }
    .light .leaflet-bar a, [data-theme="light"] .leaflet-bar a {
      background-color: #ffffff !important;
      color: #121c17 !important;
      border-bottom: 1px solid #cbd5cb !important;
    }
    .dark .leaflet-bar a:hover, [data-theme="dark"] .leaflet-bar a:hover {
      background-color: #172c1f !important;
      color: #ffffff !important;
    }
    .light .leaflet-bar a:hover, [data-theme="light"] .leaflet-bar a:hover {
      background-color: #f1f5f1 !important;
      color: #121c17 !important;
    }
    .leaflet-control-attribution {
      background: var(--card-bg) !important;
      color: var(--text-dim) !important;
      border-top-left-radius: 4px;
      font-size: 9px !important;
    }
    .leaflet-control-attribution a {
      color: #10b981 !important;
    }
    .custom-tooltip {
      background-color: var(--card-bg) !important;
      color: var(--text-main) !important;
      border: 1px solid var(--border-subtle) !important;
      border-radius: 4px !important;
      font-size: 10px !important;
      padding: 2px 6px !important;
    }
  `

  return (
    <div className="relative w-full h-full rounded-lg overflow-hidden border border-[var(--border-subtle)] shadow-inner">
      <style>{dynamicMapStyle}</style>

      {/* Floating Location Search & Hotspots Bar */}
      <div className="absolute top-3 left-12 z-[1000] pointer-events-auto">
        <LocationSearchBar 
          onSelectLocation={onLocationSelect} 
        />
      </div>

      {/* Info Card Overlay inside Map */}
      <div className="absolute top-3 right-3 z-[1000] bg-[var(--panel-bg)] backdrop-blur-md border border-[var(--border-subtle)] p-3 rounded-lg shadow-lg max-w-[260px] pointer-events-auto max-h-[85%] overflow-y-auto text-xs">
        {!selectedLocation ? (
          <div className="space-y-1">
            <h4 className="text-xs font-semibold text-[var(--text-main)]">Select Monitored Coordinate</h4>
            <p className="text-[10px] text-[var(--text-muted)] leading-normal">
              Click anywhere on the map to pinpoint a location and extract geographic coordinates for analysis.
            </p>
          </div>
        ) : (
          <div className="space-y-2">
            <div>
              {isCoordinateInNER(selectedLocation.lat, selectedLocation.lng) ? (
                <span className="text-[10px] font-bold tracking-wider text-emerald-500 uppercase">Selected Location (NER)</span>
              ) : (
                <div className="mb-1.5 p-1.5 bg-amber-500/15 border border-amber-500/30 rounded text-amber-500 text-[10px] font-bold flex items-center gap-1.5">
                  <span>⚠️</span>
                  <span>Outside North Eastern Region</span>
                </div>
              )}
              <div className="grid grid-cols-2 gap-x-2 gap-y-1 mt-1 text-xs">
                <span className="text-[var(--text-dim)]">Latitude:</span>
                <span className="font-mono text-[var(--text-main)] font-bold text-right">{selectedLocation.lat.toFixed(6)}</span>
                <span className="text-[var(--text-dim)]">Longitude:</span>
                <span className="font-mono text-[var(--text-main)] font-bold text-right">{selectedLocation.lng.toFixed(6)}</span>
              </div>
              {!isCoordinateInNER(selectedLocation.lat, selectedLocation.lng) && (
                <p className="mt-1.5 text-[9px] text-amber-600 dark:text-amber-400 leading-tight">
                  Point is outside the 8 monitored NER states. Landslide telemetry is restricted to NER.
                </p>
              )}
            </div>
            <button
              onClick={handleClearSelection}
              className="w-full text-center text-[10px] py-1 bg-[var(--card-bg)] hover:bg-[var(--subcard-bg)] text-[var(--text-muted)] hover:text-[var(--text-main)] rounded border border-[var(--border-subtle)] transition cursor-pointer font-semibold"
            >
              Clear Selection
            </button>

            {/* GIS Raster Overlays Section */}
            <div className="border-t border-[var(--border-subtle)] pt-2.5 mt-2.5 space-y-2">
              <span className="text-[10px] font-bold tracking-wider text-emerald-500 uppercase block">Map Overlays</span>
              
              {!terrainData || !terrainData.scene_id ? (
                <p className="text-[9px] text-[var(--text-dim)] leading-normal italic">
                  Processed satellite scene required for raster layers. Process a scene below to enable overlays.
                </p>
              ) : (
                <div className="space-y-2.5">
                  {/* Layer Selector */}
                  <div className="space-y-1">
                    <label className="text-[9px] text-[var(--text-dim)] uppercase font-semibold block">Active Layer</label>
                    <select
                      value={activeOverlay || 'none'}
                      onChange={(e) => setActiveOverlay(e.target.value === 'none' ? null : e.target.value)}
                      className="w-full bg-[var(--subcard-bg)] border border-[var(--border-subtle)] text-[11px] text-[var(--text-main)] rounded p-1 outline-none cursor-pointer focus:border-emerald-500 font-medium"
                    >
                      <option value="none">Street Map Only</option>
                      <option value="risk">Spatial Risk Heatmap</option>
                      <option value="slope">Slope Gradient (DEM)</option>
                      <option value="dem">Elevation (DEM)</option>
                      <option value="aspect">Aspect Orientation</option>
                      <option value="vv">Sentinel-1 VV Backscatter</option>
                      <option value="vh">Sentinel-1 VH Backscatter</option>
                    </select>
                  </div>
                  
                  {/* Loading State */}
                  {isLoadingOverlay && (
                    <div className="flex items-center gap-1.5 text-[9px] text-[var(--text-muted)] animate-pulse py-0.5">
                      <svg className="animate-spin h-3.5 w-3.5 text-emerald-500" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
                      </svg>
                      <span>Loading raster layer...</span>
                    </div>
                  )}
                  
                  {/* Error State */}
                  {overlayError && (
                    <p className="text-[9px] text-rose-500 leading-normal font-medium bg-rose-500/10 border border-rose-500/20 p-2 rounded">
                      {overlayError}
                    </p>
                  )}
                  
                  {/* Opacity Control */}
                  {activeOverlay && !isLoadingOverlay && !overlayError && (
                    <div className="space-y-1">
                      <div className="flex justify-between text-[9px] text-[var(--text-dim)] uppercase font-semibold">
                        <span>Opacity</span>
                        <span>{Math.round(overlayOpacity * 100)}%</span>
                      </div>
                      <input
                        type="range"
                        min="0.1"
                        max="1.0"
                        step="0.1"
                        value={overlayOpacity}
                        onChange={(e) => setOverlayOpacity(parseFloat(e.target.value))}
                        className="w-full h-1 bg-[var(--subcard-bg)] rounded appearance-none cursor-pointer accent-emerald-500"
                      />
                    </div>
                  )}
                  
                  {/* Dynamic Legend */}
                  {activeOverlay && !isLoadingOverlay && !overlayError && (
                    <div className="border-t border-[var(--border-subtle)] pt-2 space-y-1.5 text-[9px] text-[var(--text-muted)]">
                      <span className="font-bold text-[var(--text-main)] uppercase tracking-wider block">Legend: {activeOverlay.toUpperCase()}</span>
                      
                      {activeOverlay === 'slope' && (
                        <div className="space-y-1">
                          <div className="h-2.5 w-full rounded bg-gradient-to-r from-[rgb(255,255,178)] via-[rgb(254,141,60)] via-[rgb(240,59,32)] to-[rgb(189,0,38)]"></div>
                          <div className="flex justify-between font-mono text-[8px] text-[var(--text-dim)]">
                            <span>0° (Flat)</span>
                            <span>25°</span>
                            <span>50°+</span>
                          </div>
                        </div>
                      )}
                      
                      {activeOverlay === 'dem' && (
                        <div className="space-y-1">
                          <div className="h-2.5 w-full rounded bg-gradient-to-r from-[rgb(34,139,34)] via-[rgb(160,120,90)] to-white"></div>
                          <div className="flex justify-between font-mono text-[8px] text-[var(--text-dim)]">
                            <span>{terrainData?.statistics?.min_elevation || 'Min'}m</span>
                            <span>{terrainData?.statistics?.max_elevation || 'Max'}m</span>
                          </div>
                        </div>
                      )}
                      
                      {activeOverlay === 'aspect' && (
                        <div className="space-y-1">
                          <div className="h-2.5 w-full rounded bg-gradient-to-r from-[rgb(255,0,0)] via-[rgb(255,255,0)] via-[rgb(0,255,0)] to-[rgb(0,0,255)]"></div>
                          <div className="flex justify-between font-mono text-[8px] text-[var(--text-dim)]">
                            <span>N (0°)</span>
                            <span>E (90°)</span>
                            <span>S (180°)</span>
                            <span>W (270°)</span>
                          </div>
                        </div>
                      )}
                      
                      {['vv', 'vh'].includes(activeOverlay) && (
                        <div className="space-y-1">
                          <div className="h-2.5 w-full rounded bg-gradient-to-r from-black to-white"></div>
                          <div className="flex justify-between font-mono text-[8px] text-[var(--text-dim)]">
                            <span>{activeOverlay === 'vv' ? '-25 dB' : '-30 dB'}</span>
                            <span>{activeOverlay === 'vv' ? '0 dB' : '-5 dB'}</span>
                          </div>
                        </div>
                      )}

                      {activeOverlay === 'risk' && (
                        <div className="space-y-2">
                          <div className="h-2.5 w-full rounded bg-gradient-to-r from-[rgb(34,139,34)] via-[rgb(251,192,45)] via-[rgb(245,124,0)] to-[rgb(211,47,47)]"></div>
                          <div className="grid grid-cols-4 gap-1 text-[8px] font-semibold text-[var(--text-muted)] text-center leading-tight">
                            <div>
                              <span className="block font-bold text-emerald-500">0-25</span>
                              <span>Low Risk</span>
                            </div>
                            <div>
                              <span className="block font-bold text-yellow-500">25-50</span>
                              <span>Moderate</span>
                            </div>
                            <div>
                              <span className="block font-bold text-orange-500">50-75</span>
                              <span>High</span>
                            </div>
                            <div>
                              <span className="block font-bold text-rose-500">75-100</span>
                              <span>Very High</span>
                            </div>
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Road Network & Connectivity Intelligence Section */}
            <div className="border-t border-[var(--border-subtle)] pt-2.5 mt-2.5 space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-bold tracking-wider text-emerald-500 uppercase">Road Connectivity</span>
                <label className="relative inline-flex items-center cursor-pointer">
                  <input
                    type="checkbox"
                    checked={showRoads}
                    onChange={(e) => setShowRoads(e.target.checked)}
                    className="sr-only peer"
                  />
                  <div className="w-7 h-4 bg-[var(--subcard-bg)] border border-[var(--border-subtle)] peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-3 after:w-3 after:transition-all peer-checked:bg-emerald-600"></div>
                </label>
              </div>

              {showRoads && (
                <div className="space-y-1.5 text-[9px]">
                  {isRoadLoading && (
                    <div className="flex items-center gap-1.5 text-[var(--text-muted)] animate-pulse py-1">
                      <svg className="animate-spin h-3.5 w-3.5 text-emerald-500" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
                      </svg>
                      <span>Loading road connectivity data...</span>
                    </div>
                  )}

                  {roadError && !isRoadLoading && (
                    <p className="text-rose-500 bg-rose-500/10 border border-rose-500/20 p-1.5 rounded">
                      {roadError}
                    </p>
                  )}

                  {!isRoadLoading && !roadError && roadData && roadData.total_roads === 0 && (
                    <div className="text-[var(--text-dim)] bg-[var(--subcard-bg)] border border-[var(--border-subtle)] p-2 rounded text-[8.5px] space-y-1">
                      <p className="font-semibold text-[var(--text-muted)]">
                        No mapped roads within 5 km radius.
                      </p>
                      <p className="text-[8px] leading-relaxed">
                        This point is located in forested/wilderness terrain. Select a monitored corridor (e.g. ⚡ Hotspots &rarr; Sonapur NH-06) or click near an arterial highway to view live road connectivity.
                      </p>
                    </div>
                  )}

                  {!isRoadLoading && roadData && roadData.total_roads > 0 && (
                    <div className="space-y-1.5 pt-0.5">
                      <div className="flex justify-between text-[var(--text-muted)] font-semibold">
                        <span>Mapped Roads: {roadData.total_roads}</span>
                        {roadData.connectivity_summary?.blocked > 0 && (
                          <span className="text-rose-500 font-bold">{roadData.connectivity_summary.blocked} Blocked</span>
                        )}
                      </div>

                      {/* Road Connectivity Compact Legend */}
                      <div className="space-y-1 bg-[var(--subcard-bg)] p-2 rounded border border-[var(--border-subtle)] text-[8.5px]">
                        <span className="font-bold text-[var(--text-main)] uppercase tracking-wider block mb-1">Road Status Legend</span>
                        <div className="grid grid-cols-2 gap-x-2 gap-y-1">
                          <div className="flex items-center gap-1.5">
                            <span className="h-1 w-3 rounded-full bg-emerald-500 inline-block"></span>
                            <span className="text-[var(--text-muted)]">Normal</span>
                          </div>
                          <div className="flex items-center gap-1.5">
                            <span className="h-1 w-3 rounded-full bg-sky-400 inline-block"></span>
                            <span className="text-[var(--text-muted)]">Monitor</span>
                          </div>
                          <div className="flex items-center gap-1.5">
                            <span className="h-1 w-3 rounded-full bg-amber-500 inline-block"></span>
                            <span className="text-[var(--text-muted)]">At Risk</span>
                          </div>
                          <div className="flex items-center gap-1.5">
                            <span className="h-1 w-3 rounded-full bg-rose-500 inline-block"></span>
                            <span className="text-[var(--text-muted)]">Blocked</span>
                          </div>
                          <div className="col-span-2 flex items-center gap-1.5">
                            <span className="h-1.5 w-3.5 rounded-full bg-rose-600 inline-block"></span>
                            <span className="text-[var(--text-muted)]">Severely Impacted</span>
                          </div>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Emergency Facilities Toggle */}
            <div className="border-t border-[var(--border-subtle)] pt-2.5 mt-2.5 space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-bold tracking-wider text-rose-500 uppercase flex items-center gap-1">
                  <span>Emergency Facilities</span>
                </span>
                <label className="relative inline-flex items-center cursor-pointer">
                  <input
                    type="checkbox"
                    checked={showFacilities}
                    onChange={(e) => setShowFacilities(e.target.checked)}
                    className="sr-only peer"
                  />
                  <div className="w-7 h-4 bg-[var(--subcard-bg)] border border-[var(--border-subtle)] peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-3 after:w-3 after:transition-all peer-checked:bg-rose-600"></div>
                </label>
              </div>

              {showFacilities && nearestFacilities && (
                <div className="space-y-1 bg-[var(--subcard-bg)] p-2 rounded border border-[var(--border-subtle)] text-[8.5px]">
                  <div className="flex items-center justify-between text-[var(--text-muted)]">
                    <span className="flex items-center gap-1 font-medium"><span>🏥</span> Hospital:</span>
                    <span className="font-bold text-emerald-600 dark:text-emerald-400 font-mono">
                      {nearestFacilities.nearest_hospital.distance_km < 1 ? `${Math.round(nearestFacilities.nearest_hospital.distance_km * 1000)} m` : `${nearestFacilities.nearest_hospital.distance_km} km`} ({nearestFacilities.nearest_hospital.bearing})
                    </span>
                  </div>
                  <div className="flex items-center justify-between text-[var(--text-muted)]">
                    <span className="flex items-center gap-1 font-medium"><span>🛡️</span> Shelter:</span>
                    <span className="font-bold text-emerald-600 dark:text-emerald-400 font-mono">
                      {nearestFacilities.nearest_shelter.distance_km < 1 ? `${Math.round(nearestFacilities.nearest_shelter.distance_km * 1000)} m` : `${nearestFacilities.nearest_shelter.distance_km} km`} ({nearestFacilities.nearest_shelter.bearing})
                    </span>
                  </div>
                  <div className="flex items-center justify-between text-[var(--text-muted)]">
                    <span className="flex items-center gap-1 font-medium"><span>🚔</span> Police:</span>
                    <span className="font-bold text-emerald-600 dark:text-emerald-400 font-mono">
                      {nearestFacilities.nearest_police.distance_km < 1 ? `${Math.round(nearestFacilities.nearest_police.distance_km * 1000)} m` : `${nearestFacilities.nearest_police.distance_km} km`} ({nearestFacilities.nearest_police.bearing})
                    </span>
                  </div>
                  <div className="flex items-center justify-between text-[var(--text-muted)]">
                    <span className="flex items-center gap-1 font-medium"><span>🚜</span> BRO:</span>
                    <span className="font-bold text-emerald-600 dark:text-emerald-400 font-mono">
                      {nearestFacilities.nearest_clearance_unit.distance_km < 1 ? `${Math.round(nearestFacilities.nearest_clearance_unit.distance_km * 1000)} m` : `${nearestFacilities.nearest_clearance_unit.distance_km} km`} ({nearestFacilities.nearest_clearance_unit.bearing})
                    </span>
                  </div>
                </div>
              )}
            </div>

          </div>
        )}
      </div>

      {/* Leaflet Map */}
      <MapContainer
        center={centerNER}
        zoom={initialZoom}
        className="w-full h-full min-h-[420px]"
        zoomControl={true}
        scrollWheelZoom={true}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />

        {/* Dynamic Image Overlay */}
        {loadedOverlayUrl && loadedOverlayBounds && (
          <ImageOverlay
            url={loadedOverlayUrl}
            bounds={loadedOverlayBounds}
            opacity={overlayOpacity}
            zIndex={500}
          />
        )}
        
        <MapClickHandler onMapClick={handleMapClick} />
        <MapController aoi={aoi} selectedLocation={selectedLocation} />

        {/* Monitored Origin Location Marker */}
        {selectedLocation && (
          <Marker 
            position={selectedLocation} 
            icon={isCoordinateInNER(selectedLocation.lat, selectedLocation.lng) ? selectedLocationIcon : outsideNerLocationIcon}
          >
            <Popup className="custom-popup">
              {isCoordinateInNER(selectedLocation.lat, selectedLocation.lng) ? (
                <div className="p-1 space-y-1 text-xs text-slate-800">
                  <div className="flex items-center gap-1.5 font-bold text-emerald-700">
                    <span>📍 Selected Analysis Point</span>
                  </div>
                  <div className="font-mono text-[11px] text-slate-600">
                    {selectedLocation.lat?.toFixed(4)}°N, {selectedLocation.lng?.toFixed(4)}°E
                  </div>
                  <div className="text-[11px] text-slate-600">
                    Live satellite telemetry, slope angle & road conditions loaded in the advisory card below.
                  </div>
                </div>
              ) : (
                <div className="p-1 space-y-1.5 text-xs text-slate-800 min-w-[190px]">
                  <div className="flex items-center gap-1.5 font-bold text-amber-700">
                    <span>⚠️ Outside NER Coverage</span>
                  </div>
                  <div className="font-mono text-[11px] text-slate-600">
                    {selectedLocation.lat?.toFixed(4)}°N, {selectedLocation.lng?.toFixed(4)}°E
                  </div>
                  <div className="text-[10.5px] text-amber-800 bg-amber-50 p-1.5 rounded border border-amber-200 leading-tight">
                    Selected coordinate is outside the 8 North Eastern Region states. Landslide monitoring coverage is restricted to NER.
                  </div>
                </div>
              )}
            </Popup>
          </Marker>
        )}

        {/* Verified Regional Emergency Facilities Markers */}
        {showFacilities && nearestFacilitiesList.map((fac) => {
          const icon =
            fac.type === 'HOSPITAL' ? facilityHospitalIcon :
            fac.type === 'SHELTER' ? facilityShelterIcon :
            fac.type === 'POLICE' ? facilityPoliceIcon : facilityBroIcon;

          const badgeColor =
            fac.type === 'HOSPITAL' ? 'bg-rose-500/15 text-rose-600 dark:text-rose-400 border-rose-500/30' :
            fac.type === 'SHELTER' ? 'bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 border-emerald-500/30' :
            fac.type === 'POLICE' ? 'bg-sky-500/15 text-sky-600 dark:text-sky-400 border-sky-500/30' :
            'bg-amber-500/15 text-amber-600 dark:text-amber-400 border-amber-500/30';

          return (
            <Marker key={`facility-${fac.id}`} position={[fac.lat, fac.lng]} icon={icon}>
              <Popup>
                <div className="text-[var(--text-main)] text-xs p-1 space-y-1.5 min-w-[220px]">
                  <div className="flex items-center justify-between border-b border-[var(--border-subtle)] pb-1">
                    <span className="font-bold text-xs truncate max-w-[160px]" title={fac.name}>{fac.name}</span>
                    <span className={`px-1.5 py-0.5 rounded text-[9px] font-bold border ${badgeColor}`}>
                      {fac.type.replace('_', ' ')}
                    </span>
                  </div>
                  <div className="text-[10px] text-[var(--text-muted)] leading-tight">{fac.description}</div>
                  <div className="p-1.5 rounded bg-[var(--subcard-bg)] border border-[var(--border-subtle)] text-[10px] space-y-0.5 font-mono">
                    <div className="flex justify-between">
                      <span className="text-[var(--text-dim)]">Real Distance:</span>
                      <span className="font-bold text-emerald-600 dark:text-emerald-400">
                        {fac.distance_km < 1 ? `${Math.round(fac.distance_km * 1000)} m` : `${fac.distance_km} km`} ({fac.bearing})
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-[var(--text-dim)]">Location:</span>
                      <span>{fac.district}, {fac.state}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-[var(--text-dim)]">Emergency Line:</span>
                      <span className="font-bold text-emerald-500">{fac.phone}</span>
                    </div>
                  </div>
                </div>
              </Popup>
            </Marker>
          );
        })}

        {/* Road Network & Connectivity Intelligence Layer */}
        {showRoads && (roadData?.roads || []).map((road) => {
          const cfg = ROAD_STYLE_CONFIG[road.connectivity_status] || ROAD_STYLE_CONFIG.NORMAL;
          // Leaflet expects [latitude, longitude] while GeoJSON standard is [longitude, latitude]
          const positions = road.geometry.coordinates.map(([lon, lat]) => [lat, lon]);

          return (
            <Polyline
              key={`road-${road.osm_id}`}
              positions={positions}
              pathOptions={{
                color: cfg.color,
                weight: cfg.weight,
                opacity: cfg.opacity,
                dashArray: cfg.dashArray
              }}
            >
              <Popup>
                <div className="text-[var(--text-main)] text-xs p-1 space-y-2 min-w-[240px] max-w-[280px]">
                  <div className="flex items-center justify-between border-b border-[var(--border-subtle)] pb-1.5">
                    <span className="font-bold text-[var(--text-main)] text-xs truncate max-w-[170px]" title={road.name || road.ref || 'Unnamed Road'}>
                      {road.name || road.ref || 'Unnamed Road Segment'}
                    </span>
                    <span className={`px-1.5 py-0.5 rounded text-[9px] font-bold border ${cfg.badge}`}>
                      {cfg.label}
                    </span>
                  </div>

                  <div className="grid grid-cols-2 gap-2 text-[10px]">
                    <div>
                      <span className="text-[var(--text-dim)] uppercase font-semibold block">Route Ref</span>
                      <span className="text-[var(--text-muted)] font-mono">{road.ref || 'N/A'}</span>
                    </div>
                    <div>
                      <span className="text-[var(--text-dim)] uppercase font-semibold block">Class</span>
                      <span className="text-[var(--text-muted)] capitalize">{road.highway_type}</span>
                    </div>
                  </div>

                  <div className="p-2 rounded bg-[var(--subcard-bg)] border border-[var(--border-subtle)] space-y-1 text-[10px]">
                    <div className="flex justify-between">
                      <span className="text-[var(--text-dim)]">Nearest Hazard:</span>
                      <span className="font-mono text-[var(--text-main)] font-semibold">
                        {road.nearest_hazard_distance_m !== null && road.nearest_hazard_distance_m !== undefined
                          ? `${road.nearest_hazard_distance_m} m`
                          : 'None within 1km'}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-[var(--text-dim)]">Verified Evidence:</span>
                      <span className="font-bold text-emerald-700 dark:text-emerald-400">{road.impact_evidence?.verified_reports || 0}</span>
                    </div>
                    {road.impact_evidence?.blocked_road_reports > 0 && (
                      <div className="flex justify-between">
                        <span className="text-rose-700 dark:text-rose-400 font-semibold">Blocked Reports:</span>
                        <span className="font-bold text-rose-700 dark:text-rose-400">{road.impact_evidence.blocked_road_reports}</span>
                      </div>
                    )}
                    {road.impact_evidence?.supporting_report_ids?.length > 0 && (
                      <div className="flex justify-between text-[9px] text-[var(--text-dim)]">
                        <span>Associated IDs:</span>
                        <span className="font-mono">#{road.impact_evidence.supporting_report_ids.join(', #')}</span>
                      </div>
                    )}
                  </div>

                  <p className="text-[10px] text-[var(--text-muted)] leading-normal italic bg-[var(--card-bg)] p-1.5 rounded border border-[var(--border-subtle)]">
                    {road.explanation}
                  </p>
                </div>
              </Popup>
            </Polyline>
          );
        })}

        {/* Field Intelligence Hazard Observation Markers */}
        {(fieldReports || []).map((rep) => {
          const icon = getFieldReportMarkerIcon(rep);
          return (
            <Marker
              key={`field-rep-${rep.id}`}
              position={[rep.latitude, rep.longitude]}
              icon={icon}
            >
              <Popup>
                <div className="text-[var(--text-main)] text-xs p-1 space-y-1.5 min-w-[200px]">
                  <div className="flex items-center justify-between border-b border-[var(--border-subtle)] pb-1">
                    <span className="font-bold text-emerald-700 dark:text-emerald-400">
                      Field Observation #{rep.id}
                    </span>
                    <span className={`px-1.5 py-0.5 rounded text-[9px] font-bold ${
                      rep.status === 'VERIFIED' ? 'bg-emerald-500/10 dark:bg-emerald-950/30 text-emerald-700 dark:text-emerald-400 border border-emerald-500/30' :
                      rep.status === 'UNDER_REVIEW' ? 'bg-sky-500/10 dark:bg-sky-950/30 text-sky-700 dark:text-sky-400 border border-sky-500/30' :
                      rep.status === 'REJECTED' ? 'bg-slate-500/10 dark:bg-slate-800/40 text-slate-700 dark:text-slate-400 border border-slate-500/30' :
                      'bg-amber-500/10 dark:bg-amber-950/30 text-amber-700 dark:text-amber-400 border border-amber-500/30'
                    }`}>
                      {rep.status}
                    </span>
                  </div>
                  <div>
                    <span className="text-[var(--text-dim)] text-[10px] uppercase font-semibold block">Hazard Type</span>
                    <span className="font-semibold text-[var(--text-main)]">{rep.report_type}</span>
                  </div>
                  <div>
                    <span className="text-[var(--text-dim)] text-[10px] uppercase font-semibold block">Description</span>
                    <span className="text-[var(--text-muted)] text-[11px] leading-snug line-clamp-3">{rep.description}</span>
                  </div>
                  <div className="flex justify-between border-t border-[var(--border-subtle)] pt-1 text-[9px] text-[var(--text-dim)]">
                    <span>Severity: <strong className="text-[var(--text-main)]">{rep.severity}</strong></span>
                    <span>Distance: <strong className="text-[var(--text-main)]">{rep.distance_km !== undefined ? `${rep.distance_km.toFixed(2)} km` : '0.0 km'}</strong></span>
                  </div>
                </div>
              </Popup>
            </Marker>
          );
        })}

        {/* GSI Historical Markers */}
        {historicalData && (historicalData.gsi_incidents || []).map((inc) => (
          <Marker
            key={`gsi-${inc.source_id}`}
            position={[inc.latitude, inc.longitude]}
            icon={gsiMarkerIcon}
          >
            <Popup>
              <div className="text-[var(--text-main)] text-xs p-1 space-y-2 min-w-[220px] max-w-[280px]">
                {/* Header & Primary Slide Name */}
                <div className="border-b border-[var(--border-subtle)] pb-1.5 space-y-0.5">
                  <span className="text-[9.5px] font-black uppercase tracking-wider text-amber-700 dark:text-amber-400 block">
                    GSI Landslide Inventory Record
                  </span>
                  <h4 className="text-sm font-bold text-[var(--text-main)] leading-snug break-words">
                    {inc.slide_name || 'Unnamed Landslide Record'}
                  </h4>
                </div>

                {/* High-Priority Operational Badges & Distance */}
                <div className="space-y-1.5">
                  {(inc.activity || inc.movement_rate) && (
                    <div className="flex flex-wrap items-center gap-1.5">
                      {inc.activity && (
                        <span className={`px-2 py-0.5 rounded text-[9.5px] font-bold uppercase tracking-wide border ${
                          inc.activity.toUpperCase() === 'ACTIVE'
                            ? 'bg-rose-500/10 dark:bg-rose-950/30 text-rose-700 dark:text-rose-400 border-rose-500/30'
                            : inc.activity.toUpperCase() === 'INACTIVE'
                            ? 'bg-slate-500/10 dark:bg-slate-800/40 text-slate-700 dark:text-slate-400 border-slate-500/30'
                            : 'bg-amber-500/10 dark:bg-amber-950/30 text-amber-700 dark:text-amber-400 border-amber-500/30'
                        }`}>
                          {inc.activity}
                        </span>
                      )}
                      {inc.movement_rate && (
                        <span className="px-2 py-0.5 bg-[var(--subcard-bg)] text-[var(--text-muted)] border border-[var(--border-subtle)] rounded text-[9.5px] font-semibold tracking-wide">
                          {inc.movement_rate}
                        </span>
                      )}
                    </div>
                  )}

                  <div className="bg-[var(--subcard-bg)] px-2 py-1 rounded border border-[var(--border-subtle)] text-[10px] text-[var(--text-muted)] flex items-center justify-between font-mono">
                    <span className="text-[var(--text-dim)]">Proximity:</span>
                    <span className="text-[var(--text-main)] font-semibold">{inc.distance_km.toFixed(2)} km from location</span>
                  </div>
                </div>

                {/* Administrative Location */}
                {(inc.district || inc.state) && (
                  <div className="bg-[var(--card-bg)] p-2 rounded-lg border border-[var(--border-subtle)] space-y-0.5">
                    <span className="text-[var(--text-dim)] text-[9px] uppercase font-bold tracking-wider block">Location</span>
                    <span className="text-[var(--text-main)] text-xs font-medium">
                      {[inc.district, inc.state].filter(Boolean).join(', ')}
                    </span>
                  </div>
                )}

                {/* Geological & Hazard Profile */}
                {(inc.landslide_type || inc.material || inc.trigger) && (
                  <div className="bg-[var(--card-bg)] p-2 rounded-lg border border-[var(--border-subtle)] space-y-1.5">
                    <span className="text-[var(--text-dim)] text-[9px] uppercase font-bold tracking-wider block border-b border-[var(--border-subtle)] pb-0.5">
                      Geological & Hazard Profile
                    </span>
                    <div className="grid grid-cols-2 gap-x-2 gap-y-1 text-[10px]">
                      {inc.landslide_type && (
                        <div>
                          <span className="text-[var(--text-dim)] block text-[9px]">Type:</span>
                          <span className="text-[var(--text-main)] font-medium">{inc.landslide_type}</span>
                        </div>
                      )}
                      {inc.material && (
                        <div>
                          <span className="text-[var(--text-dim)] block text-[9px]">Material:</span>
                          <span className="text-[var(--text-main)] font-medium">{inc.material}</span>
                        </div>
                      )}
                      {inc.trigger && (
                        <div className="col-span-2">
                          <span className="text-[var(--text-dim)] block text-[9px]">Trigger:</span>
                          <span className="text-[var(--text-main)] font-medium">{inc.trigger}</span>
                        </div>
                      )}
                    </div>
                  </div>
                )}

                {/* Footer Attribution */}
                <div className="border-t border-[var(--border-subtle)] pt-1.5 text-[9px] text-[var(--text-dim)] font-mono flex items-center justify-between">
                  <span>Source: Geological Survey of India (GSI)</span>
                  {inc.source_ref && (
                    <span className="text-[var(--text-muted)] truncate max-w-[80px]" title={inc.source_ref}>
                      Ref: {inc.source_ref}
                    </span>
                  )}
                </div>
              </div>
            </Popup>
          </Marker>
        ))}

        {/* NASA Historical Markers */}
        {historicalData && (historicalData.nasa_events || []).map((event) => (
          <Marker
            key={`nasa-${event.source_id}`}
            position={[event.latitude, event.longitude]}
            icon={nasaMarkerIcon}
          >
            <Popup>
              <div className="text-[var(--text-main)] text-xs p-1 space-y-1.5 min-w-[200px]">
                <div className="font-bold text-rose-700 dark:text-rose-400 border-b border-[var(--border-subtle)] pb-1">
                  Historical NASA Event
                </div>
                {event.location_description && (
                  <div>
                    <span className="text-[var(--text-dim)] text-[10px] uppercase font-semibold block">Location</span>
                    <span className="font-medium text-[var(--text-main)]">{event.location_description}</span>
                  </div>
                )}
                <div className="grid grid-cols-2 gap-2">
                  {event.state && (
                    <div>
                      <span className="text-[var(--text-dim)] text-[10px] uppercase font-semibold block">State</span>
                      <span className="text-[var(--text-muted)]">{event.state}</span>
                    </div>
                  )}
                  {event.event_date && (
                    <div>
                      <span className="text-[var(--text-dim)] text-[10px] uppercase font-semibold block">Event Date</span>
                      <span className="text-[var(--text-muted)]">{event.event_date}</span>
                    </div>
                  )}
                </div>
                <div className="grid grid-cols-2 gap-2">
                  {event.landslide_type && (
                    <div>
                      <span className="text-[var(--text-dim)] text-[10px] uppercase font-semibold block">Type</span>
                      <span className="text-[var(--text-muted)]">{event.landslide_type}</span>
                    </div>
                  )}
                  {event.trigger && (
                    <div>
                      <span className="text-[var(--text-dim)] text-[10px] uppercase font-semibold block">Trigger</span>
                      <span className="text-[var(--text-muted)]">{event.trigger}</span>
                    </div>
                  )}
                </div>
                <div className="grid grid-cols-2 gap-2">
                  {event.fatalities !== null && event.fatalities !== undefined && (
                    <div>
                      <span className="text-[var(--text-dim)] text-[10px] uppercase font-semibold block">Fatalities</span>
                      <span className={event.fatalities > 0 ? "text-rose-700 dark:text-rose-400 font-bold" : "text-[var(--text-muted)]"}>
                        {event.fatalities}
                      </span>
                    </div>
                  )}
                  {event.injuries !== null && event.injuries !== undefined && (
                    <div>
                      <span className="text-[var(--text-dim)] text-[10px] uppercase font-semibold block">Injuries</span>
                      <span className="text-[var(--text-muted)]">{event.injuries}</span>
                    </div>
                  )}
                </div>
                {event.location_accuracy && (
                  <div>
                    <span className="text-[var(--text-dim)] text-[10px] uppercase font-semibold block">Accuracy</span>
                    <span className="text-[var(--text-muted)]">{event.location_accuracy}</span>
                  </div>
                )}
                <div className="border-t border-[var(--border-subtle)] pt-1 text-[9px] text-[var(--text-dim)] font-mono flex justify-between">
                  <span>Distance:</span>
                  <span>{event.distance_km.toFixed(2)} km</span>
                </div>
              </div>
            </Popup>
          </Marker>
        ))}

        {aoi && aoi.bounding_box && (
          <Rectangle
            bounds={[
              [aoi.bounding_box.south, aoi.bounding_box.west],
              [aoi.bounding_box.north, aoi.bounding_box.east]
            ]}
            pathOptions={{
              color: '#6366f1',
              weight: 1.5,
              fillColor: '#6366f1',
              fillOpacity: 0.1,
              dashArray: '4, 4'
            }}
          >
            <Tooltip permanent direction="top" className="custom-tooltip">
              Analysis Area ({aoi.radius_km} km)
            </Tooltip>
          </Rectangle>
        )}

        {/* ======================================================== */}
        {/* TRAVEL SAFETY LAYERS (Route, Vehicle, Hazard Perimeters) */}
        {/* ======================================================== */}
        {travelMonitoringActive && (
          <>
            {/* Navigational Route to Destination */}
            {travelerLocation && travelDestination && travelDestination.lat != null && (
              <Polyline
                positions={[
                  [travelerLocation.lat, travelerLocation.lng],
                  [travelDestination.lat, travelDestination.lng]
                ]}
                pathOptions={{
                  color: '#0284c7',
                  weight: 4.5,
                  dashArray: '8, 6',
                  opacity: 0.85
                }}
              >
                <Tooltip sticky>
                  Travel Route: To {travelDestination.name || 'Destination'}
                </Tooltip>
              </Polyline>
            )}

            {/* Destination Marker */}
            {travelDestination && travelDestination.lat != null && (
              <Marker
                position={[travelDestination.lat, travelDestination.lng]}
                icon={destinationPinIcon}
              >
                <Popup>
                  <div className="text-[var(--text-main)] text-xs p-1 space-y-1">
                    <div className="font-bold text-purple-600 dark:text-purple-400 border-b border-[var(--border-subtle)] pb-1 flex items-center gap-1.5">
                      <span>🏁 Planned Destination</span>
                    </div>
                    <p className="font-semibold text-[var(--text-main)]">{travelDestination.name || 'Selected Destination'}</p>
                    <p className="font-mono text-[10px] text-[var(--text-dim)]">
                      {travelDestination.lat.toFixed(4)}°N, {travelDestination.lng.toFixed(4)}°E
                    </p>
                  </div>
                </Popup>
              </Marker>
            )}

            {/* Monitored Travel Hazard Corridors & 10 km Early Warning Perimeter */}
            {(travelRiskZones || []).map((zone) => {
              const isZoneActiveAlert = activeTravelAlert?.zone?.id === zone.id
              const isCritical = (zone.risk_probability || 0) >= 85 || zone.severity === 'CRITICAL'
              const circleColor = isZoneActiveAlert ? '#ef4444' : isCritical ? '#f43f5e' : '#f59e0b'

              return (
                <span key={`travel-hazard-${zone.id}`}>
                  {/* 10 km Early Warning Perimeter Buffer */}
                  {(zone.risk_probability || 0) >= 70 && (
                    <Circle
                      center={[zone.latitude, zone.longitude]}
                      radius={10000}
                      pathOptions={{
                        color: circleColor,
                        fillColor: circleColor,
                        fillOpacity: isZoneActiveAlert ? 0.22 : 0.08,
                        weight: isZoneActiveAlert ? 2.5 : 1.2,
                        dashArray: isZoneActiveAlert ? '4, 4' : '6, 6'
                      }}
                    >
                      <Tooltip permanent={isZoneActiveAlert} direction="top" className="custom-tooltip">
                        {isZoneActiveAlert ? `🚨 10 km Early Warning Active: ${zone.name}` : `10 km Buffer: ${zone.name}`}
                      </Tooltip>
                    </Circle>
                  )}

                  {/* Hazard Center Marker */}
                  <Marker
                    position={[zone.latitude, zone.longitude]}
                    icon={getDangerZoneIcon(zone, isZoneActiveAlert)}
                  >
                    <Popup>
                      <div className="text-[var(--text-main)] text-xs p-1 space-y-1.5 min-w-[210px]">
                        <div className="flex items-center justify-between border-b border-[var(--border-subtle)] pb-1">
                          <span className="font-bold text-rose-600 dark:text-rose-400">⚠️ Landslide Hazard Zone</span>
                          <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${
                            isCritical ? 'bg-rose-500/20 text-rose-500' : 'bg-amber-500/20 text-amber-500'
                          }`}>
                            {zone.risk_probability}% Risk
                          </span>
                        </div>
                        <p className="font-bold text-sm text-[var(--text-main)]">{zone.name}</p>
                        {zone.highway && (
                          <div className="text-[11px] text-[var(--text-muted)]">
                            <span className="font-semibold text-[var(--text-dim)]">Highway: </span>
                            <span className="font-mono">{zone.highway}</span>
                          </div>
                        )}
                        {zone.advisory && (
                          <p className="text-[11px] text-[var(--text-dim)] bg-[var(--card-bg)] p-1.5 rounded border border-[var(--border-subtle)]">
                            {zone.advisory}
                          </p>
                        )}
                        <div className="font-mono text-[9px] text-[var(--text-dim)] pt-1 border-t border-[var(--border-subtle)] flex justify-between">
                          <span>Source: {zone.source || 'CompositeRiskEngine'}</span>
                          <span>{zone.latitude.toFixed(4)}, {zone.longitude.toFixed(4)}</span>
                        </div>
                      </div>
                    </Popup>
                  </Marker>
                </span>
              )
            })}

            {/* Live Traveler Vehicle Marker */}
            {travelerLocation && travelerLocation.lat != null && (
              <Marker
                position={[travelerLocation.lat, travelerLocation.lng]}
                icon={travelerVehicleIcon}
                zIndexOffset={1000}
              >
                <Popup>
                  <div className="text-[var(--text-main)] text-xs p-1 space-y-1 min-w-[180px]">
                    <div className="font-bold text-sky-600 dark:text-sky-400 border-b border-[var(--border-subtle)] pb-1 flex items-center gap-1.5">
                      <span>🚗 Traveler Position (Live GPS)</span>
                    </div>
                    <div className="font-mono text-xs text-[var(--text-main)] font-semibold">
                      {travelerLocation.lat.toFixed(5)}°N, {travelerLocation.lng.toFixed(5)}°E
                    </div>
                    {travelerLocation.heading != null && !isNaN(travelerLocation.heading) && (
                      <p className="text-[10px] text-[var(--text-dim)]">
                        Bearing: <span className="font-mono font-bold">{Math.round(travelerLocation.heading)}°</span>
                      </p>
                    )}
                    {travelerLocation.speed != null && !isNaN(travelerLocation.speed) && (
                      <p className="text-[10px] text-[var(--text-dim)]">
                        Speed: <span className="font-mono font-bold">{(travelerLocation.speed * 3.6).toFixed(1)} km/h</span>
                      </p>
                    )}
                    <span className="inline-block text-[9px] px-1.5 py-0.5 rounded bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">
                      ● Active Early Warning Corridor
                    </span>
                  </div>
                </Popup>
              </Marker>
            )}
          </>
        )}
      </MapContainer>
    </div>
  )
}
