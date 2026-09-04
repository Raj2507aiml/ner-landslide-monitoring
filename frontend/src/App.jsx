import { useState, useEffect } from 'react'
import { 
  Activity, 
  AlertTriangle, 
  CheckCircle, 
  MapPin, 
  RefreshCw, 
  Shield,
  ShieldCheck, 
  ShieldAlert, 
  Layers, 
  Map,
  Home,
  Radio,
  CloudRain,
  Cpu,
  ClipboardList,
  TrafficCone,
  Settings,
  Menu,
  X,
  ChevronRight,
  Mountain,
  Database,
  FileText,
  FileDown,
  Sun,
  Moon,
  Users,
  User,
  Lock,
  LogOut,
  Volume2,
  VolumeX
} from 'lucide-react'
import { isAudioMuted, toggleAudioMute, subscribeAudioMute, testEmergencyAlarmSound } from './services/emergencyAudioService'
import { getApiBaseUrl } from './services/apiConfig'
import InteractiveMap from './components/InteractiveMap'
import FieldReportModal from './components/FieldReportModal'
import FieldIntelligenceCard from './components/FieldIntelligenceCard'
import FieldIntelligenceWorkspace from './components/FieldIntelligenceWorkspace'
import RoadDisruptionCard from './components/RoadDisruptionCard'
import OperationalSituationCard from './components/OperationalSituationCard'
import OperationalIncidentCommand from './components/OperationalIncidentCommand'
import RecentAlertsPanel from './components/RecentAlertsPanel'
import AlertDispatchModal from './components/AlertDispatchModal'
import SitrepModal from './components/SitrepModal'
import LoginModal from './components/LoginModal'
import AuthLandingPage from './components/AuthLandingPage'
import UserRoleSelector from './components/UserRoleSelector'
import CitizenAdvisoryCard from './components/CitizenAdvisoryCard'
import ErrorBoundary from './components/ErrorBoundary'
import EmergencySmsModal from './components/EmergencySmsModal'
import { useOnlineStatus } from './hooks/useOnlineStatus'
import LanguageSwitcher from './components/LanguageSwitcher'
import { useTranslation } from './services/i18nService'
import { getCurrentUser, USER_ROLES, switchUserRole, DEMO_USERS, logoutUser } from './services/authService'
import { analyzeLocation, searchSatelliteData, getSatelliteSceneDetail, processSatelliteScene, getWeatherTelemetry, processTerrainData, fetchNearbyHistoricalLandslides, fetchSusceptibilityScore, fetchStaticMLSusceptibility, fetchCompositeLandslideRisk, fetchAutomaticSatelliteChange, fetchEarlyWarningAnalysis } from './services/locationService'
import { getNearbyFieldReports, getFieldIntelligenceSummary, getReviewQueue } from './services/fieldReportService'
import { getNearbyRoads, getRoadDisruptionSummary } from './services/infrastructureService'
import { getSituationAssessment } from './services/operationsService'
import { evaluateIncident, getIncidents } from './services/incidentService'
import { apiFetch } from './services/apiConfig'
import './App.css'

function App() {
  const { t } = useTranslation()
  const [theme, setTheme] = useState(() => {
    try {
      const urlParams = new URLSearchParams(window.location.search);
      const urlTheme = urlParams.get('theme');
      if (urlTheme === 'light' || urlTheme === 'dark') return urlTheme;
      return localStorage.getItem('ner_dashboard_theme') || 'dark'
    } catch {
      return 'dark'
    }
  })

  useEffect(() => {
    try {
      localStorage.setItem('ner_dashboard_theme', theme)
      const root = document.documentElement
      if (theme === 'light') {
        root.classList.add('light')
        root.classList.remove('dark')
        root.setAttribute('data-theme', 'light')
      } else {
        root.classList.add('dark')
        root.classList.remove('light')
        root.setAttribute('data-theme', 'dark')
      }
    } catch (e) {
      console.warn('Failed to save theme to localStorage:', e)
    }
  }, [theme])

  const toggleTheme = () => {
    setTheme(prev => (prev === 'dark' ? 'light' : 'dark'))
  }

  // Role-Based Authentication & Session State
  const [currentUser, setCurrentUser] = useState(() => {
    try {
      const urlParams = new URLSearchParams(window.location.search);
      const urlRole = urlParams.get('role');
      if (urlRole?.toLowerCase() === 'citizen') return DEMO_USERS.CITIZEN;
      if (urlRole?.toLowerCase() === 'admin') return DEMO_USERS.ADMIN;
    } catch {}
    return getCurrentUser();
  })
  const [isLoginModalOpen, setIsLoginModalOpen] = useState(false)
  const [loginModalTab, setLoginModalTab] = useState('USER_LOGIN')
  const isAdmin = currentUser?.role === USER_ROLES.ADMIN

  // Route Guard & Portal Selection
  const [initialPortal, setInitialPortal] = useState(() => {
    try {
      const hash = (window.location.hash || '').toLowerCase();
      const path = (window.location.pathname || '').toLowerCase();
      const search = (window.location.search || '').toLowerCase();
      if (hash.includes('admin') || path.includes('/admin') || search.includes('admin')) {
        return 'ADMIN';
      }
    } catch {}
    return 'USER';
  });
  const [accessDeniedMessage, setAccessDeniedMessage] = useState(null);

  // Monitor URL routes to protect Admin resources and block unauthorized citizens
  useEffect(() => {
    const handleRouteCheck = () => {
      const hash = (window.location.hash || '').toLowerCase();
      const path = (window.location.pathname || '').toLowerCase();
      const search = (window.location.search || '').toLowerCase();
      const isAdminRoute = hash.includes('admin') || path.includes('/admin') || search.includes('role=admin');

      if (isAdminRoute) {
        if (!currentUser) {
          setInitialPortal('ADMIN');
        } else if (currentUser.role !== USER_ROLES.ADMIN) {
          // A regular citizen tried accessing an admin URL!
          setAccessDeniedMessage('Access Denied: Administrative privileges required. Public citizen accounts are not authorized to access the Operational Incident Command.');
          if (window.location.hash.includes('admin')) {
            window.location.hash = '#dashboard';
          }
          if (window.location.pathname.includes('/admin')) {
            window.history.replaceState(null, '', '/');
          }
          setTimeout(() => {
            setAccessDeniedMessage(null);
          }, 6000);
        }
      }
    };

    handleRouteCheck();
    window.addEventListener('hashchange', handleRouteCheck);
    window.addEventListener('popstate', handleRouteCheck);
    return () => {
      window.removeEventListener('hashchange', handleRouteCheck);
      window.removeEventListener('popstate', handleRouteCheck);
    };
  }, [currentUser]);

  const handleAuthSuccess = (user) => {
    setCurrentUser(user);
    if (user?.role === USER_ROLES.ADMIN) {
      window.location.hash = '#admin';
    } else {
      window.location.hash = '#dashboard';
    }
  };

  const handleLogout = () => {
    logoutUser();
    setCurrentUser(null);
    window.location.hash = '#login';
  };

  const [isSidebarOpen, setIsSidebarOpen] = useState(false)
  const [backendStatus, setBackendStatus] = useState('Checking...')
  const [isConnected, setIsConnected] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [selectedLocation, setSelectedLocation] = useState(null)
  
  const [aoi, setAoi] = useState(null)
  const [analysisResult, setAnalysisResult] = useState(null)
  const [analysisError, setAnalysisError] = useState(null)
  const [isAnalyzing, setIsAnalyzing] = useState(false)

  // Emergency Alert Dispatcher Modal States
  const [isAlertModalOpen, setIsAlertModalOpen] = useState(false)
  const [alertModalData, setAlertModalData] = useState(null)

  // Offline PWA & 2G SMS Dispatcher States
  const isOnline = useOnlineStatus()
  const [isSmsModalOpen, setIsSmsModalOpen] = useState(false)

  const handleOpenAlertDispatch = (customData = {}) => {
    setAlertModalData({
      locationName: selectedLocation ? `${selectedLocation.lat.toFixed(4)}°N, ${selectedLocation.lng.toFixed(4)}°E` : 'NER Monitored Sector',
      lat: selectedLocation?.lat,
      lng: selectedLocation?.lng,
      warningLevel: earlyWarningData?.warning_level || 'ALERT',
      riskScore: compositeRiskData?.composite_risk_score ?? compositeRiskData?.overall_risk_score ?? null,
      rainfallMm: weatherData?.current_precipitation_mm ?? weatherData?.precipitation_24h_mm ?? null,
      roadStatus: roadData?.roads ? `${roadData.roads.filter(r => r.connectivity_status === 'BLOCKED' || r.connectivity_status === 'AT_RISK').length} disrupted road segments` : null,
      slopeDeg: terrainData?.statistics?.mean_slope ?? null,
      ...customData
    })
    setIsAlertModalOpen(true)
  }

  // Situation Report (SITREP) Modal State
  const [isSitrepModalOpen, setIsSitrepModalOpen] = useState(false)

  // Emergency Alert Audio State
  const [isAudioMutedState, setIsAudioMutedState] = useState(isAudioMuted())

  useEffect(() => {
    return subscribeAudioMute(newMuted => {
      setIsAudioMutedState(newMuted)
    })
  }, [])

  // Satellite scene discovery states
  const [satelliteScenes, setSatelliteScenes] = useState([])
  const [isSearchingSatellite, setIsSearchingSatellite] = useState(false)
  const [satelliteError, setSatelliteError] = useState(null)

  // Satellite scene inspection states
  const [inspectingScene, setInspectingScene] = useState(null)
  const [inspectingDetail, setInspectingDetail] = useState(null)
  const [isInspecting, setIsInspecting] = useState(false)
  const [inspectError, setInspectError] = useState(null)

  const formatBytes = (bytes) => {
    if (!bytes) return 'N/A';
    if (bytes < 1024) return bytes + ' B';
    const k = 1024;
    const dm = 1;
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
  }

  const handleInspectScene = async (sceneId) => {
    setInspectingScene(sceneId)
    setIsInspecting(true)
    setInspectError(null)
    setInspectingDetail(null)

    const result = await getSatelliteSceneDetail(sceneId)
    if (result.ok) {
      setInspectingDetail(result.data)
    } else {
      setInspectError(result.error || 'Failed to retrieve scene asset metadata.')
    }
    setIsInspecting(false)
  }

  // Satellite scene processing states
  const [processingStatus, setProcessingStatus] = useState({})
  const [processingError, setProcessingError] = useState(null)

  const handleProcessScene = async (sceneId) => {
    if (!selectedLocation || !aoi) return
    setActiveOverlay(null)
    setOverlayOpacity(0.6)
    setProcessingStatus(prev => ({ ...prev, [sceneId]: 'Downloading' }))
    setProcessingError(null)

    // Simulate switching to "Clipping" state after 2 seconds for visual indication
    const clippingTimer = setTimeout(() => {
      setProcessingStatus(prev => {
        if (prev[sceneId] === 'Downloading') {
          return { ...prev, [sceneId]: 'Clipping' }
        }
        return prev
      })
    }, 2000)

    const result = await processSatelliteScene(
      sceneId,
      selectedLocation.lat,
      selectedLocation.lng,
      aoi.radius_km
    )

    clearTimeout(clippingTimer)

    if (result.ok) {
      setProcessingStatus(prev => ({ ...prev, [sceneId]: 'Cached' }))
      fetchTerrain(sceneId, selectedLocation.lat, selectedLocation.lng, aoi.radius_km)
    } else {
      setProcessingStatus(prev => ({ ...prev, [sceneId]: 'Failed' }))
      setProcessingError(result.error || 'Failed to process scene assets on the backend.')
    }
  }

  // Weather telemetry states
  const [weatherData, setWeatherData] = useState(null)
  const [isWeatherLoading, setIsWeatherLoading] = useState(false)
  const [weatherError, setWeatherError] = useState(null)

  const fetchWeather = async (lat, lng) => {
    setIsWeatherLoading(true)
    setWeatherError(null)
    setWeatherData(null)
    const result = await getWeatherTelemetry(lat, lng)
    if (result.ok) {
      setWeatherData(result.data)
      setIsWeatherLoading(false)
      return result.data
    } else {
      setWeatherError(result.error || 'Weather telemetry data is currently unavailable.')
      setIsWeatherLoading(false)
      return null
    }
  }

  // Terrain analysis states
  const [terrainData, setTerrainData] = useState(null)
  const [isTerrainLoading, setIsTerrainLoading] = useState(false)
  const [terrainError, setTerrainError] = useState(null)

  const fetchTerrain = async (sceneId, lat, lng, radiusKm) => {
    setIsTerrainLoading(true)
    setTerrainError(null)
    setTerrainData(null)
    const result = await processTerrainData(sceneId, lat, lng, radiusKm)
    if (result.ok) {
      setTerrainData(result.data)
      const slope = result.data.statistics?.mean_slope;
      const rainfall = weatherData ? weatherData.daily_precipitation : null;
      const rainfall3d = weatherData ? weatherData.three_day_cumulative : null;
      const rainfall7d = weatherData ? weatherData.seven_day_cumulative : null;
      fetchSusceptibility(lat, lng, radiusKm, slope, rainfall, rainfall3d, rainfall7d);
    } else {
      setTerrainError(result.error || 'Terrain data is currently unavailable.')
    }
    setIsTerrainLoading(false)
  }

  // Historical landslide intelligence states
  const [historicalData, setHistoricalData] = useState(null)
  const [isHistoricalLoading, setIsHistoricalLoading] = useState(false)
  const [historicalError, setHistoricalError] = useState(null)

  const fetchHistorical = async (lat, lng, radiusKm = 10.0) => {
    setIsHistoricalLoading(true)
    setHistoricalError(null)
    setHistoricalData(null)
    console.log(`[Historical API Request] Fetching landslide context for Lat: ${lat}, Lng: ${lng}, Radius: ${radiusKm}`);
    try {
      const result = await fetchNearbyHistoricalLandslides(lat, lng, radiusKm)
      if (result.ok) {
        setHistoricalData(result.data)
        console.log('[Historical API Response] Received context:', result.data)
      } else {
        setHistoricalError(result.error || 'Historical landslide data is currently unavailable.')
        console.error('[Historical API Error] Mapped error:', result.error)
      }
    } catch (err) {
      setHistoricalError(err.message || 'An unexpected error occurred during spatial lookup.')
      console.error('[Historical API Exception] Exception occurred:', err)
    } finally {
      setIsHistoricalLoading(false)
    }
  }

  // Susceptibility scoring states
  const [susceptibilityData, setSusceptibilityData] = useState(null)
  const [isSusceptibilityLoading, setIsSusceptibilityLoading] = useState(false)
  const [susceptibilityError, setSusceptibilityError] = useState(null)

  // Machine Learning Susceptibility States
  const [mlSusceptibilityData, setMlSusceptibilityData] = useState(null)
  const [isMlSusceptibilityLoading, setIsMlSusceptibilityLoading] = useState(false)
  const [mlSusceptibilityError, setMlSusceptibilityError] = useState(null)

  // Composite Risk States
  const [compositeRiskData, setCompositeRiskData] = useState(null)
  const [isCompositeRiskLoading, setIsCompositeRiskLoading] = useState(false)
  const [compositeRiskError, setCompositeRiskError] = useState(null)

  // Satellite Surface Change States
  const [satelliteChangeData, setSatelliteChangeData] = useState(null)
  const [satelliteChangeLoading, setSatelliteChangeLoading] = useState(false)
  const [satelliteChangeError, setSatelliteChangeError] = useState(null)

  // Early Warning Decision States
  const [earlyWarningData, setEarlyWarningData] = useState(null)
  const [earlyWarningLoading, setEarlyWarningLoading] = useState(false)
  const [earlyWarningError, setEarlyWarningError] = useState(null)

  // Field Intelligence States
  const [isReportModalOpen, setIsReportModalOpen] = useState(false)
  const [isWorkspaceOpen, setIsWorkspaceOpen] = useState(false)
  const [fieldReports, setFieldReports] = useState([])
  const [fieldIntelligenceSummary, setFieldIntelligenceSummary] = useState(null)
  const [isFieldReportsLoading, setIsFieldReportsLoading] = useState(false)
  const [fieldReportsError, setFieldReportsError] = useState(null)

  const fetchFieldIntelligence = async (lat, lng, radiusKm = 5.0) => {
    setIsFieldReportsLoading(true)
    setFieldReportsError(null)
    try {
      const [reportsRes, summaryRes] = await Promise.all([
        getNearbyFieldReports(lat, lng, radiusKm),
        getFieldIntelligenceSummary(lat, lng, radiusKm)
      ])
      if (reportsRes.ok) {
        setFieldReports(reportsRes.data || [])
      } else {
        setFieldReports([])
      }
      if (summaryRes.ok) {
        setFieldIntelligenceSummary(summaryRes.data || null)
      } else {
        setFieldIntelligenceSummary(null)
      }
    } catch (err) {
      setFieldReportsError('Failed to retrieve field intelligence.')
    } finally {
      setIsFieldReportsLoading(false)
    }
  }

  // Road Network & Connectivity States
  const [roadData, setRoadData] = useState(null)
  const [isRoadLoading, setIsRoadLoading] = useState(false)
  const [roadError, setRoadError] = useState(null)
  const [showRoads, setShowRoads] = useState(true)

  // Road Disruption Intelligence States
  const [disruptionData, setDisruptionData] = useState(null)
  const [isDisruptionLoading, setIsDisruptionLoading] = useState(false)
  const [disruptionError, setDisruptionError] = useState(null)

  // Operational Situation Assessment States
  const [situationData, setSituationData] = useState(null)
  const [isSituationLoading, setIsSituationLoading] = useState(false)
  const [situationError, setSituationError] = useState(null)

  // Incident Command Refresh Key
  const [incidentRefreshKey, setIncidentRefreshKey] = useState(0)

  // Top Dashboard Summary Metrics States
  const [activeIncidentsCount, setActiveIncidentsCount] = useState(null)
  const [criticalIncidentsCount, setCriticalIncidentsCount] = useState(null)
  const [isIncidentsCountLoading, setIsIncidentsCountLoading] = useState(false)
  const [incidentsCountError, setIncidentsCountError] = useState(null)

  const [totalFieldReportsCount, setTotalFieldReportsCount] = useState(null)
  const [isFieldReportsCountLoading, setIsFieldReportsCountLoading] = useState(false)
  const [fieldReportsCountError, setFieldReportsCountError] = useState(null)

  const fetchTopSummaryMetrics = async () => {
    // 1. Fetch Incidents Metrics (Active & Critical)
    setIsIncidentsCountLoading(true)
    setIncidentsCountError(null)
    try {
      const incRes = await getIncidents({ limit: 100 })
      if (incRes && incRes.ok && incRes.data) {
        const list = Array.isArray(incRes.data)
          ? incRes.data
          : (incRes.data.incidents || incRes.data.items || incRes.data.data || [])
        const activeStatuses = ['OPEN', 'ACKNOWLEDGED', 'IN_PROGRESS']
        const activeCount = list.filter(i => activeStatuses.includes((i.status || '').toUpperCase())).length
        const criticalCount = list.filter(i => 
          (i.severity || '').toUpperCase() === 'CRITICAL' && 
          activeStatuses.includes((i.status || '').toUpperCase())
        ).length
        setActiveIncidentsCount(activeCount)
        setCriticalIncidentsCount(criticalCount)
      } else {
        setIncidentsCountError(incRes?.error || 'Failed to fetch incident metrics')
      }
    } catch (err) {
      setIncidentsCountError('Incident service connection error')
    } finally {
      setIsIncidentsCountLoading(false)
    }

    // 2. Fetch Total Field Reports Metric
    setIsFieldReportsCountLoading(true)
    setFieldReportsCountError(null)
    try {
      const queueRes = await getReviewQueue({ limit: 1 })
      if (queueRes && queueRes.ok && queueRes.data) {
        const total = typeof queueRes.data.total === 'number'
          ? queueRes.data.total
          : typeof queueRes.data.count === 'number'
          ? queueRes.data.count
          : typeof queueRes.data.total_count === 'number'
          ? queueRes.data.total_count
          : typeof queueRes.data.total_reports === 'number'
          ? queueRes.data.total_reports
          : Array.isArray(queueRes.data.items)
          ? queueRes.data.items.length
          : Array.isArray(queueRes.data)
          ? queueRes.data.length
          : 0
        setTotalFieldReportsCount(total)
      } else {
        setFieldReportsCountError(queueRes?.error || 'Failed to fetch report metrics')
      }
    } catch (err) {
      setFieldReportsCountError('Field reports service connection error')
    } finally {
      setIsFieldReportsCountLoading(false)
    }
  }

  useEffect(() => {
    fetchTopSummaryMetrics()
  }, [incidentRefreshKey])

  const fetchSituationAssessment = async (lat, lng, radiusKm = 5.0) => {
    setIsSituationLoading(true)
    setSituationError(null)
    try {
      const res = await getSituationAssessment(lat, lng, radiusKm)
      if (res.ok && res.data) {
        setSituationData(res.data)
      } else {
        setSituationData(null)
        setSituationError(res.error || 'Unable to retrieve operational situation assessment.')
      }
    } catch (err) {
      setSituationData(null)
      setSituationError('Failed to connect to operational assessment service.')
    } finally {
      setIsSituationLoading(false)
    }
  }

  const fetchRoadInfrastructure = async (lat, lng, radiusKm = 5.0) => {
    setIsRoadLoading(true)
    setRoadError(null)
    setIsDisruptionLoading(true)
    setDisruptionError(null)
    try {
      const [roadsRes, disruptionRes] = await Promise.all([
        getNearbyRoads(lat, lng, radiusKm),
        getRoadDisruptionSummary(lat, lng, radiusKm)
      ])

      if (roadsRes.ok && roadsRes.data) {
        setRoadData(roadsRes.data)
      } else {
        setRoadData(null)
        setRoadError(roadsRes.error || 'Road infrastructure data is temporarily unavailable.')
      }

      if (disruptionRes.ok && disruptionRes.data) {
        setDisruptionData(disruptionRes.data)
      } else {
        setDisruptionData(null)
        setDisruptionError(disruptionRes.error || 'Road disruption intelligence is temporarily unavailable.')
      }
    } catch (err) {
      setRoadData(null)
      setRoadError('Unable to retrieve road connectivity data.')
      setDisruptionData(null)
      setDisruptionError('Unable to retrieve road disruption summary.')
    } finally {
      setIsRoadLoading(false)
      setIsDisruptionLoading(false)
    }
  }

  const handleReportSubmitted = (newReport) => {
    fetchTopSummaryMetrics()
    if (selectedLocation && selectedLocation.lat && selectedLocation.lng) {
      const radius = aoi?.radius_km || 5.0
      fetchFieldIntelligence(selectedLocation.lat, selectedLocation.lng, radius)
      fetchRoadInfrastructure(selectedLocation.lat, selectedLocation.lng, radius)
      fetchSituationAssessment(selectedLocation.lat, selectedLocation.lng, radius)
      evaluateIncident(selectedLocation.lat, selectedLocation.lng, radius).then(() => {
        setIncidentRefreshKey(prev => prev + 1)
      }).catch(() => {})
    }
  }

  const [activeOverlay, setActiveOverlay] = useState(null)
  const [overlayOpacity, setOverlayOpacity] = useState(0.6)

  const fetchSusceptibility = async (lat, lng, radiusKm = 10.0, slope = null, rainfall = null, rainfall3d = null, rainfall7d = null) => {
    setIsSusceptibilityLoading(true)
    setSusceptibilityError(null)
    setSusceptibilityData(null)
    console.log(`[Susceptibility API Request] Fetching score for Lat: ${lat}, Lng: ${lng}, Radius: ${radiusKm}, Slope: ${slope}, Rainfall: ${rainfall}, Rainfall3d: ${rainfall3d}, Rainfall7d: ${rainfall7d}`);
    try {
      const result = await fetchSusceptibilityScore(lat, lng, radiusKm, slope, rainfall, rainfall3d, rainfall7d)
      if (result.ok) {
        setSusceptibilityData(result.data)
        console.log('[Susceptibility API Response] Received score:', result.data)
      } else {
        setSusceptibilityError(result.error || 'Hazard susceptibility scoring is currently unavailable.')
        console.error('[Susceptibility API Error] Mapped error:', result.error)
      }
    } catch (err) {
      setSusceptibilityError(err.message || 'An unexpected error occurred during susceptibility calculation.')
      console.error('[Susceptibility API Exception] Exception occurred:', err)
    } finally {
      setIsSusceptibilityLoading(false)
    }
  }

  const fetchMLSusceptibility = async (lat, lng) => {
    setIsMlSusceptibilityLoading(true)
    setMlSusceptibilityError(null)
    setMlSusceptibilityData(null)
    console.log(`[ML Susceptibility Request] Fetching static ML score for Lat: ${lat}, Lng: ${lng}`);
    try {
      const result = await fetchStaticMLSusceptibility(lat, lng)
      if (result.ok) {
        setMlSusceptibilityData(result.data)
        console.log('[ML Susceptibility Response] Received prediction:', result.data)
      } else {
        setMlSusceptibilityError(result.error || 'AI Static susceptibility scoring is currently unavailable.')
        console.error('[ML Susceptibility Error] Mapped error:', result.error)
      }
    } catch (err) {
      setMlSusceptibilityError(err.message || 'An unexpected error occurred during AI static calculation.')
      console.error('[ML Susceptibility Exception] Exception occurred:', err)
    } finally {
      setIsMlSusceptibilityLoading(false)
    }
  }

  const fetchCompositeRisk = async (lat, lng) => {
    setIsCompositeRiskLoading(true)
    setCompositeRiskError(null)
    setCompositeRiskData(null)
    console.log(`[Composite Risk Request] Fetching unified landslide risk index for Lat: ${lat}, Lng: ${lng}`);
    try {
      const result = await fetchCompositeLandslideRisk(lat, lng)
      if (result.ok) {
        setCompositeRiskData(result.data)
        console.log('[Composite Risk Response] Received risk data:', result.data)
      } else {
        setCompositeRiskError(result.error || 'Unified composite risk scoring is currently unavailable.')
        console.error('[Composite Risk Error] Mapped error:', result.error)
      }
    } catch (err) {
      setCompositeRiskError(err.message || 'An unexpected error occurred during composite risk calculation.')
      console.error('[Composite Risk Exception] Exception occurred:', err)
    } finally {
      setIsCompositeRiskLoading(false)
    }
  }

  const fetchSatelliteChange = async (lat, lng) => {
    setSatelliteChangeLoading(true)
    setSatelliteChangeError(null)
    setSatelliteChangeData(null)
    console.log(`[Satellite Change Request] Fetching automatic Sentinel-1 change analysis for Lat: ${lat}, Lng: ${lng}`);
    try {
      const result = await fetchAutomaticSatelliteChange(lat, lng)
      if (result.ok) {
        setSatelliteChangeData(result.data)
        console.log('[Satellite Change Response] Received change data:', result.data)
      } else if (result.data?.status === 'CREDENTIALS_REQUIRED' || (result.error && (result.error.includes('Copernicus S3 Credentials') || result.error.includes('CDSE_S3')))) {
        setSatelliteChangeData({
          status: 'CREDENTIALS_REQUIRED',
          message: 'Live Sentinel-1 SAR imagery requires Copernicus CDSE S3 credentials. To enable radar change detection, add CDSE_S3_ACCESS_KEY and CDSE_S3_SECRET_KEY in backend settings. System continues operating in meteorological and AI terrain mode.'
        })
        setSatelliteChangeError(null)
      } else {
        setSatelliteChangeError(result.error || 'Satellite change analysis is currently unavailable.')
        console.error('[Satellite Change Error] Mapped error:', result.error)
      }
    } catch (err) {
      setSatelliteChangeError(err.message || 'An unexpected error occurred during satellite change analysis.')
      console.error('[Satellite Change Exception] Exception occurred:', err)
    } finally {
      setSatelliteChangeLoading(false)
    }
  }

  const fetchEarlyWarning = async (lat, lng) => {
    setEarlyWarningLoading(true)
    setEarlyWarningError(null)
    setEarlyWarningData(null)
    console.log(`[Early Warning Request] Fetching operational early warning decision for Lat: ${lat}, Lng: ${lng}`);
    try {
      const result = await fetchEarlyWarningAnalysis(lat, lng)
      if (result.ok) {
        setEarlyWarningData(result.data)
        console.log('[Early Warning Response] Received warning data:', result.data)
      } else {
        setEarlyWarningError(result.error || 'Early warning decision assessment is currently unavailable.')
        console.error('[Early Warning Error] Mapped error:', result.error)
      }
    } catch (err) {
      setEarlyWarningError(err.message || 'An unexpected error occurred during early warning evaluation.')
      console.error('[Early Warning Exception] Exception occurred:', err)
    } finally {
      setEarlyWarningLoading(false)
    }
  }

  const getPastDateString = (daysAgo) => {
    const d = new Date()
    d.setDate(d.getDate() - daysAgo)
    return d.toISOString().split('T')[0]
  }

  const [startDate, setStartDate] = useState(() => getPastDateString(30))
  const [endDate, setEndDate] = useState(() => getPastDateString(0))

  const handleLocationSelect = (latlng) => {
    setSelectedLocation(latlng)
    setAoi(null)
    setAnalysisResult(null)
    setAnalysisError(null)
    setSatelliteScenes([])
    setSatelliteError(null)
    setProcessingStatus({})
    setProcessingError(null)
    setWeatherData(null)
    setWeatherError(null)
    setTerrainData(null)
    setTerrainError(null)
    setHistoricalData(null)
    setHistoricalError(null)
    setSusceptibilityData(null)
    setSusceptibilityError(null)
    setIsSusceptibilityLoading(false)
    setMlSusceptibilityData(null)
    setMlSusceptibilityError(null)
    setIsMlSusceptibilityLoading(false)
    setCompositeRiskData(null)
    setCompositeRiskError(null)
    setIsCompositeRiskLoading(false)
    setSatelliteChangeData(null)
    setSatelliteChangeError(null)
    setSatelliteChangeLoading(false)
    setEarlyWarningData(null)
    setEarlyWarningError(null)
    setEarlyWarningLoading(false)
    setFieldReports([])
    setFieldIntelligenceSummary(null)
    setFieldReportsError(null)
    setIsFieldReportsLoading(false)
    setRoadData(null)
    setIsRoadLoading(false)
    setRoadError(null)
    setDisruptionData(null)
    setIsDisruptionLoading(false)
    setDisruptionError(null)
    setSituationData(null)
    setIsSituationLoading(false)
    setSituationError(null)
    setActiveOverlay(null)
    setOverlayOpacity(0.6)
  }

  const handleSatelliteSearch = async () => {
    if (!selectedLocation || !aoi) return
    setIsSearchingSatellite(true)
    setSatelliteError(null)
    setSatelliteScenes([])

    const result = await searchSatelliteData(
      selectedLocation.lat,
      selectedLocation.lng,
      aoi.radius_km,
      startDate,
      endDate,
      10
    )

    if (result.ok) {
      setSatelliteScenes(result.data.scenes || [])
      if (!result.data.scenes || result.data.scenes.length === 0) {
        setSatelliteError('No Sentinel-1 scenes found for this AOI and date range.')
      }
    } else {
      setSatelliteError(result.error || 'Failed to search Copernicus satellite catalogue.')
    }
    setIsSearchingSatellite(false)
  }

  const handleAnalyzeLocation = async () => {
    if (!selectedLocation) return
    setIsAnalyzing(true)
    setAnalysisError(null)
    setAnalysisResult(null)
    setAoi(null)
    setActiveOverlay(null)
    setOverlayOpacity(0.6)

    const result = await analyzeLocation(selectedLocation.lat, selectedLocation.lng)
    if (result.ok) {
      setAnalysisResult(result.data)
      setAoi(result.data.aoi)
      
      // Fetch weather telemetry and await it to safely pass precipitation
      const weatherInfo = await fetchWeather(selectedLocation.lat, selectedLocation.lng)
      const rainfall = weatherInfo ? weatherInfo.daily_precipitation : null
      const rainfall3d = weatherInfo ? weatherInfo.three_day_cumulative : null
      const rainfall7d = weatherInfo ? weatherInfo.seven_day_cumulative : null
      
      fetchHistorical(selectedLocation.lat, selectedLocation.lng, result.data.aoi?.radius_km)
      
      // Fetch ML Susceptibility on-the-fly from Copernicus DEM and ML model
      fetchMLSusceptibility(selectedLocation.lat, selectedLocation.lng)
      
      // Fetch Composite Risk Index
      fetchCompositeRisk(selectedLocation.lat, selectedLocation.lng)
      
      // Fetch Automatic Satellite Change analysis (RSCI)
      fetchSatelliteChange(selectedLocation.lat, selectedLocation.lng)
      
      // Fetch Early Warning decision evaluation
      fetchEarlyWarning(selectedLocation.lat, selectedLocation.lng)
      
      // Baseline susceptibility (Historical + Rainfall)
      fetchSusceptibility(selectedLocation.lat, selectedLocation.lng, result.data.aoi?.radius_km, null, rainfall, rainfall3d, rainfall7d)

      // Fetch nearby field intelligence & ground observations
      fetchFieldIntelligence(selectedLocation.lat, selectedLocation.lng, result.data.aoi?.radius_km || 5.0)

      // Fetch nearby road network & connectivity intelligence
      fetchRoadInfrastructure(selectedLocation.lat, selectedLocation.lng, result.data.aoi?.radius_km || 5.0)

      // Fetch integrated operational situation assessment
      fetchSituationAssessment(selectedLocation.lat, selectedLocation.lng, result.data.aoi?.radius_km || 5.0)

      // Evaluate automated operational incident creation (triggered only after analysis)
      try {
        const incEvalRes = await evaluateIncident(selectedLocation.lat, selectedLocation.lng, result.data.aoi?.radius_km || 5.0)
        if (incEvalRes.ok && (incEvalRes.data?.action === 'created' || incEvalRes.data?.action === 'duplicate_prevented')) {
          setIncidentRefreshKey(prev => prev + 1)
        }
      } catch (err) {
        console.warn('[Incident Evaluation] Automatic evaluation check failed:', err)
      }
    } else {
      setAnalysisError(result.error || 'Coordinates lie outside India\'s North Eastern Region.')
      if (result.data) {
        setAnalysisResult(result.data)
      }
    }
    setIsAnalyzing(false)
  }

  const checkHealth = async () => {
    setIsLoading(true)
    try {
      const response = await apiFetch('/health')
      if (response.ok) {
        const data = await response.json().catch(() => ({}))
        const statusLower = (data.status || '').toLowerCase()
        if (['healthy', 'ok', 'online', 'operational'].includes(statusLower) || data.service || response.status === 200) {
          setBackendStatus('Connected')
          setIsConnected(true)
        } else if (statusLower === 'degraded') {
          setBackendStatus('Degraded')
          setIsConnected(true)
        } else {
          setBackendStatus('Connected')
          setIsConnected(true)
        }
      } else {
        setBackendStatus('Offline')
        setIsConnected(false)
      }
    } catch (error) {
      setBackendStatus('Offline')
      setIsConnected(false)
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    checkHealth()
  }, [])

  // MANDATORY AUTHENTICATION GATE: Unauthenticated visitors must sign in or register before accessing the dashboard
  if (!currentUser) {
    return (
      <AuthLandingPage
        initialPortal={initialPortal}
        onLoginSuccess={handleAuthSuccess}
      />
    );
  }

  return (
    <div className="min-h-screen bg-[var(--canvas-bg)] text-[var(--text-main)] font-sans flex flex-row relative selection:bg-emerald-500/30 selection:text-emerald-200">
      {/* GLOBAL ATMOSPHERIC BACKGROUND SYSTEM */}
      {/* Layer 1: Atmospheric Mountain/Forest Terrain Image */}
      <div 
        className="fixed inset-0 pointer-events-none z-0 bg-cover bg-center bg-no-repeat transition-opacity duration-500 transform scale-[1.01]"
        style={{ 
          backgroundImage: "url('/terrain_bg.jpg')",
          opacity: "var(--bg-image-opacity, 0.3)"
        }}
      />
      {/* Layer 2: Theme-Aware Environmental Overlay & Vignette */}
      <div 
        className="fixed inset-0 pointer-events-none z-0 transition-colors duration-500" 
        style={{ background: "var(--bg-gradient-vignette)" }}
      />

      {/* MOBILE SIDEBAR DRAWER OVERLAY */}
      {isSidebarOpen && (
        <div 
          onClick={() => setIsSidebarOpen(false)}
          className="fixed inset-0 bg-black/60 z-40 md:hidden backdrop-blur-xs"
        />
      )}

      {/* LEFT SIDEBAR (Desktop Fixed / Mobile Drawer) */}
      <aside className={`
        fixed top-0 bottom-0 left-0 z-50 w-60 bg-[var(--sidebar-bg)] backdrop-blur-xl border-r border-[var(--border-subtle)] 
        flex flex-col justify-between p-3 transition-transform duration-300 ease-in-out select-none
        md:sticky md:translate-x-0 md:h-screen md:shrink-0
        ${isSidebarOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0'}
      `}>
        {/* Top Branding Section */}
        <div className="space-y-3">
          <div className="flex items-center justify-between pb-2 border-b border-[var(--border-subtle)]">
            <div className="flex items-center gap-2.5">
              {/* Circular Emblem Seal */}
              <div className="relative h-9 w-9 rounded-full border border-emerald-500/40 bg-emerald-950/40 flex items-center justify-center shrink-0 shadow-xs">
                <div className="h-7 w-7 rounded-full border border-emerald-500/20 flex items-center justify-center">
                  <ShieldAlert className="h-4 w-4 text-emerald-400" />
                </div>
              </div>
              <div className="min-w-0">
                <h1 className="text-xs font-bold text-[var(--text-main)] leading-tight tracking-normal">
                  NER Landslide
                </h1>
                <p className="text-[11px] text-[var(--text-muted)] font-normal leading-tight">
                  Monitoring &
                </p>
                <p className="text-[10px] text-[var(--text-dim)] font-medium leading-tight">
                  Early Warning System
                </p>
              </div>
            </div>
            <button 
              onClick={() => setIsSidebarOpen(false)}
              className="p-1 rounded-lg text-[var(--text-muted)] hover:text-[var(--text-main)] md:hidden"
            >
              <X className="h-4 w-4" />
            </button>
          </div>

          {/* Navigation Items */}
          <nav className="space-y-0.5 text-xs">
            <button
              onClick={() => { window.scrollTo({ top: 0, behavior: 'smooth' }); setIsSidebarOpen(false); }}
              className="w-full bg-[var(--sidebar-active-bg)] text-[var(--sidebar-active-text)] border border-[var(--sidebar-active-border)] rounded-lg px-2.5 py-1.5 flex items-center gap-2.5 font-medium transition cursor-pointer"
            >
              <Home className="h-4 w-4 shrink-0" />
              <span>{isAdmin ? 'Commander Dashboard' : 'Public Safety Portal'}</span>
            </button>

            <button
              onClick={() => { document.getElementById('map-section')?.scrollIntoView({ behavior: 'smooth' }); setIsSidebarOpen(false); }}
              className="w-full text-[var(--text-muted)] hover:text-[var(--text-main)] hover:bg-[var(--card-bg)] rounded-lg px-2.5 py-1.5 flex items-center gap-2.5 font-normal transition cursor-pointer"
            >
              <Map className="h-4 w-4 shrink-0" />
              <span>Interactive Map & Search</span>
            </button>

            {isAdmin ? (
              <>
                <button
                  onClick={() => { document.getElementById('incident-command-section')?.scrollIntoView({ behavior: 'smooth' }); setIsSidebarOpen(false); }}
                  className="w-full text-[var(--text-muted)] hover:text-[var(--text-main)] hover:bg-[var(--card-bg)] rounded-lg px-2.5 py-1.5 flex items-center gap-2.5 font-normal transition cursor-pointer"
                >
                  <ShieldAlert className="h-4 w-4 shrink-0" />
                  <span>Incident Command</span>
                </button>

                <button
                  onClick={() => { document.getElementById('early-warning-section')?.scrollIntoView({ behavior: 'smooth' }); setIsSidebarOpen(false); }}
                  className="w-full text-[var(--text-muted)] hover:text-[var(--text-main)] hover:bg-[var(--card-bg)] rounded-lg px-2.5 py-1.5 flex items-center gap-2.5 font-normal transition cursor-pointer"
                >
                  <Radio className="h-4 w-4 shrink-0" />
                  <span>Early Warning</span>
                </button>

                <button
                  onClick={() => { document.getElementById('weather-section')?.scrollIntoView({ behavior: 'smooth' }); setIsSidebarOpen(false); }}
                  className="w-full text-[var(--text-muted)] hover:text-[var(--text-main)] hover:bg-[var(--card-bg)] rounded-lg px-2.5 py-1.5 flex items-center gap-2.5 font-normal transition cursor-pointer"
                >
                  <CloudRain className="h-4 w-4 shrink-0" />
                  <span>Weather</span>
                </button>

                <button
                  onClick={() => { document.getElementById('ai-analysis-section')?.scrollIntoView({ behavior: 'smooth' }); setIsSidebarOpen(false); }}
                  className="w-full text-[var(--text-muted)] hover:text-[var(--text-main)] hover:bg-[var(--card-bg)] rounded-lg px-2.5 py-1.5 flex items-center gap-2.5 font-normal transition cursor-pointer"
                >
                  <Cpu className="h-4 w-4 shrink-0" />
                  <span>AI Analysis</span>
                </button>

                <button
                  onClick={() => { document.getElementById('satellite-section')?.scrollIntoView({ behavior: 'smooth' }); setIsSidebarOpen(false); }}
                  className="w-full text-[var(--text-muted)] hover:text-[var(--text-main)] hover:bg-[var(--card-bg)] rounded-lg px-2.5 py-1.5 flex items-center gap-2.5 font-normal transition cursor-pointer"
                >
                  <Layers className="h-4 w-4 shrink-0" />
                  <span>Satellite Data</span>
                </button>

                <button
                  onClick={() => { setIsWorkspaceOpen(true); setIsSidebarOpen(false); }}
                  className="w-full text-[var(--text-muted)] hover:text-[var(--text-main)] hover:bg-[var(--card-bg)] rounded-lg px-2.5 py-1.5 flex items-center gap-2.5 font-normal transition cursor-pointer"
                >
                  <ClipboardList className="h-4 w-4 shrink-0" />
                  <span>Field Reports</span>
                </button>

                <button
                  onClick={() => { document.getElementById('road-section')?.scrollIntoView({ behavior: 'smooth' }); setIsSidebarOpen(false); }}
                  className="w-full text-[var(--text-muted)] hover:text-[var(--text-main)] hover:bg-[var(--card-bg)] rounded-lg px-2.5 py-1.5 flex items-center gap-2.5 font-normal transition cursor-pointer"
                >
                  <TrafficCone className="h-4 w-4 shrink-0" />
                  <span>Road Intelligence</span>
                </button>

                <button
                  onClick={() => { document.getElementById('situation-section')?.scrollIntoView({ behavior: 'smooth' }); setIsSidebarOpen(false); }}
                  className="w-full text-[var(--text-muted)] hover:text-[var(--text-main)] hover:bg-[var(--card-bg)] rounded-lg px-2.5 py-1.5 flex items-center gap-2.5 font-normal transition cursor-pointer"
                >
                  <Activity className="h-4 w-4 shrink-0" />
                  <span>Situation Assessment</span>
                </button>
              </>
            ) : (
              <>
                <button
                  onClick={() => { setIsReportModalOpen(true); setIsSidebarOpen(false); }}
                  className="w-full text-[var(--text-muted)] hover:text-[var(--text-main)] hover:bg-[var(--card-bg)] rounded-lg px-2.5 py-1.5 flex items-center gap-2.5 font-normal transition cursor-pointer"
                >
                  <ShieldAlert className="h-4 w-4 text-emerald-500 shrink-0" />
                  <span>Report Hazard / Rockfall</span>
                </button>
              </>
            )}

            <button
              onClick={() => { checkHealth(); setIsSidebarOpen(false); }}
              className="w-full text-[var(--text-muted)] hover:text-[var(--text-main)] hover:bg-[var(--card-bg)] rounded-lg px-2.5 py-1.5 flex items-center gap-2.5 font-normal transition cursor-pointer"
            >
              <Settings className="h-4 w-4 shrink-0" />
              <span>System Health</span>
            </button>
          </nav>
        </div>

        {/* Sidebar Bottom System Status Card */}
        <div className="bg-[var(--card-bg)] border border-[var(--border-subtle)] rounded-xl p-2.5 space-y-1 mt-2">
          <span className="text-[10px] font-medium text-[var(--text-dim)] uppercase tracking-wider block">System Status</span>
          <div className="flex items-center gap-1.5">
            <span className={`h-2 w-2 rounded-full ${isConnected ? 'bg-emerald-500 animate-pulse' : 'bg-rose-500 animate-pulse'}`} />
            <span className={`text-xs font-bold ${isConnected ? 'text-emerald-500' : 'text-rose-500'}`}>
              {isConnected ? 'Online' : backendStatus === 'Checking...' ? 'Checking...' : 'Offline'}
            </span>
          </div>
          <p className="text-[10px] text-[var(--text-dim)]">
            {isConnected ? 'All systems operational' : 'Backend service unreachable'}
          </p>
        </div>

        {/* Sidebar Sign Out Action (Both User and Admin) */}
        <div className="pt-2 border-t border-[var(--border-subtle)] mt-2">
          <button
            onClick={handleLogout}
            className="w-full text-[var(--text-muted)] hover:text-rose-400 hover:bg-rose-500/10 rounded-lg px-2.5 py-1.5 flex items-center gap-2.5 font-semibold transition cursor-pointer text-xs"
            title="Sign out of account and return to login screen"
          >
            <LogOut className="h-4 w-4 text-rose-400 shrink-0" />
            <span>Sign Out / Logout</span>
          </button>
        </div>
      </aside>

      {/* MAIN APPLICATION COLUMN */}
      <div className="flex-1 min-w-0 flex flex-col z-10 relative min-h-screen">
        
        {/* Top Command Center Header */}
        <header className="sticky top-0 z-30 bg-[var(--header-bg)] backdrop-blur-md border-b border-[var(--border-subtle)] px-4 sm:px-6 py-2 flex items-center justify-between gap-3">
          <div className="flex items-center gap-3 min-w-0">
            <button 
              onClick={() => setIsSidebarOpen(true)}
              className="p-1 rounded-md bg-[var(--card-bg)] text-[var(--text-main)] border border-[var(--border-subtle)] md:hidden cursor-pointer"
              title="Open Navigation"
            >
              <Menu className="h-4 w-4" />
            </button>
            <div className="flex items-center gap-2 text-xs truncate">
              <span className="font-bold text-[var(--text-main)]">
                {isAdmin ? 'Operational Command' : 'Public Portal'}
              </span>
              <span className="text-[var(--text-dim)] font-bold">•</span>
              <span className="text-[var(--text-muted)] truncate hidden sm:inline">
                {isAdmin ? 'NER Landslide Monitoring & Early Warning System' : 'North East Regional Landslide Safety & Public Advisory'}
              </span>
            </div>
          </div>

          <div className="flex items-center gap-2 shrink-0">
            {/* System Status Pill in Top Header (Admin only) */}
            {isAdmin && (
              <div className="hidden lg:flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-[var(--card-bg)] border border-[var(--border-subtle)] text-xs">
                <span className="text-[var(--text-dim)] text-[11px]">System Status:</span>
                <span className="flex items-center gap-1 font-semibold text-emerald-500 text-[11px]">
                  <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse" />
                  {isConnected ? 'Online' : backendStatus}
                </span>
              </div>
            )}

            {/* Admin-only Review Workspace */}
            {isAdmin && (
              <button
                onClick={() => setIsWorkspaceOpen(true)}
                className="hidden sm:flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-[var(--card-bg)] hover:bg-[var(--subcard-bg)] text-[var(--text-main)] border border-[var(--border-subtle)] text-xs font-medium transition cursor-pointer shadow-xs"
                title="Open Field Intelligence review workspace"
              >
                <Layers className="h-3.5 w-3.5 text-emerald-500" />
                <span>Review Reports</span>
              </button>
            )}

            {/* Ground Observation Report Button (Both roles) */}
            <button
              onClick={() => setIsReportModalOpen(true)}
              className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold shadow-xs transition cursor-pointer"
              title="Report ground observation"
            >
              <ShieldAlert className="h-3.5 w-3.5" />
              <span>Report Observation</span>
            </button>

            {/* SITREP Situation Report Briefing Button (Admin only) */}
            {isAdmin && (
              <button
                onClick={() => setIsSitrepModalOpen(true)}
                className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-rose-600 hover:bg-rose-500 text-white text-xs font-semibold shadow-xs transition cursor-pointer"
                title="Download 1-2 page official NDMA SITREP incident briefing (PDF / Printable)"
              >
                <FileDown className="h-3.5 w-3.5" />
                <span>Download SITREP</span>
              </button>
            )}

            {/* Citizen Helpline Quick Link (Citizen only) */}
            {!isAdmin && (
              <a
                href="tel:1070"
                className="hidden sm:flex items-center gap-1 px-2.5 py-1 rounded-md bg-rose-600/15 border border-rose-500/30 text-rose-400 text-xs font-semibold hover:bg-rose-600/25 transition"
                title="Call 24/7 State Disaster Management Helpline"
              >
                <span>📞 {t('helpline_title', 'Helpline: 1070')}</span>
              </a>
            )}

            {/* 1-Click 2G SMS & Offline Emergency Hub */}
            <button
              onClick={() => setIsSmsModalOpen(true)}
              className={`flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-semibold shadow-xs transition cursor-pointer border ${
                !isOnline
                  ? 'bg-amber-500 hover:bg-amber-400 text-slate-950 border-amber-400 animate-pulse font-bold'
                  : 'bg-[var(--card-bg)] hover:bg-[var(--subcard-bg)] text-[var(--text-main)] border-[var(--border-subtle)]'
              }`}
              title="Open Offline Emergency Hub & 1-Click 2G SMS Dispatch (No Data Required)"
            >
              <Radio className={`h-3.5 w-3.5 ${!isOnline ? 'text-slate-950' : 'text-emerald-500'}`} />
              <span className="hidden sm:inline">{!isOnline ? '📴 Offline SOS' : '2G SMS SOS'}</span>
            </button>

            {/* Regional Multilingual Language Switcher */}
            <LanguageSwitcher compact={false} />

            {/* Light / Dark Mode Toggle Switcher */}
            <button
              onClick={toggleTheme}
              className="flex items-center gap-1 px-2 py-1 rounded-md border border-[var(--border-subtle)] bg-[var(--card-bg)] text-[var(--text-main)] hover:border-[var(--border-strong)] transition cursor-pointer text-xs font-medium shadow-xs"
              title={theme === 'dark' ? "Switch to Operational Light Mode" : "Switch to Command Dark Mode"}
            >
              {theme === 'dark' ? (
                <>
                  <Sun className="h-3.5 w-3.5 text-amber-400" />
                  <span className="hidden xl:inline text-[11px] text-[var(--text-muted)]">{t('light_mode', 'Light')}</span>
                </>
              ) : (
                <>
                  <Moon className="h-3.5 w-3.5 text-emerald-700" />
                  <span className="hidden xl:inline text-[11px] text-[var(--text-muted)]">{t('dark_mode', 'Dark')}</span>
                </>
              )}
            </button>

            {/* Global Emergency Audio Mute Toggle */}
            <button
              onClick={() => {
                const newMuted = toggleAudioMute();
                setIsAudioMutedState(newMuted);
                if (!newMuted) {
                  testEmergencyAlarmSound();
                }
              }}
              className={`flex items-center gap-1 px-2 py-1 rounded-md border transition cursor-pointer text-xs font-medium shadow-xs ${
                isAudioMutedState
                  ? 'border-[var(--border-subtle)] bg-[var(--card-bg)] text-[var(--text-dim)] hover:text-[var(--text-main)]'
                  : 'border-emerald-500/40 bg-emerald-500/10 text-emerald-500 hover:bg-emerald-500/20'
              }`}
              title={isAudioMutedState ? "Emergency warning audio is MUTED — Click to unmute & test chime" : "Emergency warning audio is ACTIVE — Click to mute"}
            >
              {isAudioMutedState ? (
                <>
                  <VolumeX className="h-3.5 w-3.5 text-slate-400" />
                  <span className="hidden xl:inline text-[11px] text-slate-400">{t('alarm_muted', 'Muted')}</span>
                </>
              ) : (
                <>
                  <Volume2 className="h-3.5 w-3.5 text-emerald-500 animate-pulse" />
                  <span className="hidden xl:inline text-[11px] text-emerald-500 font-semibold">{t('alarm_active', 'Alarm ON')}</span>
                </>
              )}
            </button>

            <button
              onClick={checkHealth}
              disabled={isLoading}
              className="p-1 rounded-md border border-[var(--border-subtle)] bg-[var(--card-bg)] text-[var(--text-main)] hover:border-[var(--border-strong)] transition disabled:opacity-50 cursor-pointer"
              title="Refresh connection status"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${isLoading ? 'animate-spin text-emerald-500' : ''}`} />
            </button>

            {/* Authenticated User / Admin Profile Dropdown */}
            {currentUser && (
              <UserRoleSelector
                currentUser={currentUser}
                onUserChange={setCurrentUser}
                onOpenLoginModal={() => setIsLoginModalOpen(true)}
              />
            )}

            {/* Direct Logout Button (Both Logged-In User and Admin) */}
            {currentUser && (
              <button
                onClick={handleLogout}
                className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-rose-600/15 hover:bg-rose-600/25 border border-rose-500/30 text-rose-400 hover:text-rose-300 text-xs font-bold transition cursor-pointer shadow-xs"
                title="Sign out of your account"
              >
                <LogOut className="h-3.5 w-3.5 text-rose-400" />
                <span>{t('logout_btn', 'Logout')}</span>
              </button>
            )}
          </div>
        </header>

        {/* Offline Connectivity Banner */}
        {!isOnline && (
          <div className="bg-amber-950/90 border-b border-amber-500/50 px-4 sm:px-6 py-2.5 flex flex-wrap items-center justify-between gap-3 text-xs text-amber-200 shadow-md animate-in fade-in duration-200">
            <div className="flex items-center gap-2">
              <span className="h-2 w-2 rounded-full bg-amber-400 animate-ping shrink-0" />
              <span className="font-bold uppercase tracking-wider text-[10px] bg-amber-500/30 text-amber-300 px-2 py-0.5 rounded border border-amber-500/40">
                Offline Mode Active
              </span>
              <span className="text-[11px] leading-tight">
                Mobile data disconnected. Offline shelter directory, mountain first-aid instructions, and 1-click 2G SMS dispatch are operational.
              </span>
            </div>
            <button
              onClick={() => setIsSmsModalOpen(true)}
              className="px-3 py-1 bg-amber-400 hover:bg-amber-300 text-slate-950 font-bold rounded-lg text-xs transition cursor-pointer shrink-0 shadow-sm"
            >
              Open 2G SMS SOS
            </button>
          </div>
        )}

        {/* Access Denied Alert Banner (When non-admin attempts /admin or restricted action) */}
        {accessDeniedMessage && (
          <div className="bg-rose-950/90 border-b border-rose-500/60 px-4 sm:px-6 py-2.5 flex items-center justify-between gap-3 text-xs text-rose-200 shadow-md animate-in fade-in duration-200">
            <div className="flex items-center gap-2">
              <ShieldAlert className="h-4 w-4 text-rose-400 shrink-0" />
              <span className="font-semibold">{accessDeniedMessage}</span>
            </div>
            <button
              onClick={() => setAccessDeniedMessage(null)}
              className="p-1 rounded text-rose-400 hover:text-white cursor-pointer"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        )}

        {/* Operational Admin Notice Banner (Admin Only) */}
        {isAdmin && (
          <div className="bg-rose-950/40 border-b border-rose-500/30 px-4 sm:px-6 py-2 flex items-center justify-between gap-2 text-xs">
            <div className="flex items-center gap-2">
              <span className="h-2 w-2 rounded-full bg-rose-500 animate-pulse shrink-0" />
              <span className="font-bold text-rose-300">Operational Command Mode Active:</span>
              <span className="text-[var(--text-muted)] hidden sm:inline">
                Full authority access to Sentinel-1 SAR analysis, review workspace, SITREP export, and emergency broadcast dispatch.
              </span>
            </div>
            <button
              onClick={handleLogout}
              className="px-2.5 py-1 rounded bg-rose-600/25 hover:bg-rose-600/40 text-rose-300 border border-rose-500/40 text-[11px] font-bold transition cursor-pointer shrink-0"
            >
              Exit Command Center
            </button>
          </div>
        )}

        {/* Main Content Body */}
        <main className="flex-1 max-w-7xl mx-auto w-full px-4 sm:px-6 lg:px-8 py-3.5 space-y-3.5">
          {isAdmin ? (
            <>
              {/* Dashboard Summary Metric Cards Grid (4 Cards) */}
          <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
            {/* Card 1: Active Incidents */}
            <div className="bg-[var(--metric-bg)] backdrop-blur-md border border-[var(--border-subtle)] rounded-xl p-3.5 flex flex-col justify-between shadow-xs hover:border-[var(--border-strong)] transition min-h-[110px]">
              <div className="flex items-start justify-between">
                <div className="space-y-0.5">
                  <p className="text-[11px] font-medium text-[var(--text-muted)]">Active Incidents</p>
                  {isIncidentsCountLoading && activeIncidentsCount === null ? (
                    <div className="flex items-center gap-1.5 text-[var(--text-dim)] py-0.5">
                      <RefreshCw className="h-3.5 w-3.5 animate-spin text-amber-500" />
                      <span className="text-xs">Loading...</span>
                    </div>
                  ) : incidentsCountError && activeIncidentsCount === null ? (
                    <p className="text-sm font-semibold text-rose-500">Unavailable</p>
                  ) : (
                    <p className="text-2xl sm:text-3xl font-bold text-amber-500 font-mono tracking-tight my-0.5">
                      {activeIncidentsCount !== null ? activeIncidentsCount : 0}
                    </p>
                  )}
                </div>
                <div className="p-2 rounded-full bg-amber-500/10 text-amber-500 border border-amber-500/25 flex items-center justify-center shrink-0">
                  <AlertTriangle className="h-4 w-4" />
                </div>
              </div>
              <button
                onClick={() => document.getElementById('incident-command-section')?.scrollIntoView({ behavior: 'smooth' })}
                className="text-[10px] text-[var(--text-dim)] hover:text-amber-500 font-medium flex items-center gap-0.5 pt-1 border-t border-[var(--border-subtle)] transition text-left cursor-pointer"
              >
                <span>View all</span>
                <ChevronRight className="h-3 w-3" />
              </button>
            </div>

            {/* Card 2: Critical Incidents */}
            <div className="bg-[var(--metric-bg)] backdrop-blur-md border border-[var(--border-subtle)] rounded-xl p-3.5 flex flex-col justify-between shadow-xs hover:border-[var(--border-strong)] transition min-h-[110px]">
              <div className="flex items-start justify-between">
                <div className="space-y-0.5">
                  <p className="text-[11px] font-medium text-[var(--text-muted)]">Critical Incidents</p>
                  {isIncidentsCountLoading && criticalIncidentsCount === null ? (
                    <div className="flex items-center gap-1.5 text-[var(--text-dim)] py-0.5">
                      <RefreshCw className="h-3.5 w-3.5 animate-spin text-rose-500" />
                      <span className="text-xs">Loading...</span>
                    </div>
                  ) : incidentsCountError && criticalIncidentsCount === null ? (
                    <p className="text-sm font-semibold text-rose-500">Unavailable</p>
                  ) : (
                    <p className="text-2xl sm:text-3xl font-bold text-rose-500 font-mono tracking-tight my-0.5">
                      {criticalIncidentsCount !== null ? criticalIncidentsCount : 0}
                    </p>
                  )}
                </div>
                <div className={`p-2 rounded-full border flex items-center justify-center shrink-0 ${criticalIncidentsCount > 0 ? 'bg-rose-500/20 text-rose-500 border-rose-500/40 animate-pulse' : 'bg-[var(--subcard-bg)] text-[var(--text-dim)] border border-[var(--border-subtle)]'}`}>
                  <ShieldAlert className="h-4 w-4" />
                </div>
              </div>
              <button
                onClick={() => document.getElementById('incident-command-section')?.scrollIntoView({ behavior: 'smooth' })}
                className="text-[10px] text-[var(--text-dim)] hover:text-rose-500 font-medium flex items-center gap-0.5 pt-1 border-t border-[var(--border-subtle)] transition text-left cursor-pointer"
              >
                <span>View all</span>
                <ChevronRight className="h-3 w-3" />
              </button>
            </div>

            {/* Card 3: Field Reports */}
            <div className="bg-[var(--metric-bg)] backdrop-blur-md border border-[var(--border-subtle)] rounded-xl p-3.5 flex flex-col justify-between shadow-xs hover:border-[var(--border-strong)] transition min-h-[110px]">
              <div className="flex items-start justify-between">
                <div className="space-y-0.5">
                  <p className="text-[11px] font-medium text-[var(--text-muted)]">Field Reports</p>
                  {isFieldReportsCountLoading && totalFieldReportsCount === null ? (
                    <div className="flex items-center gap-1.5 text-[var(--text-dim)] py-0.5">
                      <RefreshCw className="h-3.5 w-3.5 animate-spin text-sky-500" />
                      <span className="text-xs">Loading...</span>
                    </div>
                  ) : fieldReportsCountError && totalFieldReportsCount === null ? (
                    <p className="text-sm font-semibold text-rose-500">Unavailable</p>
                  ) : (
                    <p className="text-2xl sm:text-3xl font-bold text-sky-500 font-mono tracking-tight my-0.5">
                      {totalFieldReportsCount !== null ? totalFieldReportsCount : 0}
                    </p>
                  )}
                </div>
                <div className="p-2 rounded-full bg-sky-500/10 text-sky-500 border border-sky-500/25 flex items-center justify-center shrink-0">
                  <ClipboardList className="h-4 w-4" />
                </div>
              </div>
              <button
                onClick={() => setIsWorkspaceOpen(true)}
                className="text-[10px] text-[var(--text-dim)] hover:text-sky-500 font-medium flex items-center gap-0.5 pt-1 border-t border-[var(--border-subtle)] transition text-left cursor-pointer"
              >
                <span>View all</span>
                <ChevronRight className="h-3 w-3" />
              </button>
            </div>

            {/* Card 4: System Status */}
            <div className="bg-[var(--metric-bg)] backdrop-blur-md border border-[var(--border-subtle)] rounded-xl p-3.5 flex flex-col justify-between shadow-xs hover:border-[var(--border-strong)] transition min-h-[110px]">
              <div className="flex items-start justify-between">
                <div className="space-y-0.5">
                  <p className="text-[11px] font-medium text-[var(--text-muted)]">System Status</p>
                  <p className={`text-2xl sm:text-3xl font-bold tracking-tight font-mono my-0.5 ${
                    isConnected ? 'text-emerald-500' : backendStatus === 'Checking...' ? 'text-[var(--text-muted)]' : 'text-rose-500'
                  }`}>
                    {isConnected ? 'Online' : backendStatus === 'Degraded' ? 'Degraded' : backendStatus === 'Checking...' ? 'Connecting...' : 'Offline'}
                  </p>
                </div>
                <div className={`p-2 rounded-full border flex items-center justify-center shrink-0 ${
                  isConnected 
                    ? 'bg-emerald-500/10 text-emerald-500 border-emerald-500/25' 
                    : 'bg-rose-500/10 text-rose-500 border-rose-500/25'
                }`}>
                  <CheckCircle className="h-4 w-4" />
                </div>
              </div>
              <p className="text-[10px] text-[var(--text-dim)] font-medium pt-1 border-t border-[var(--border-subtle)] truncate">
                {isConnected ? 'All systems operational' : 'Service connectivity degraded'}
              </p>
            </div>
          </section>

          {/* Middle GIS Map & Recent Alerts Grid Section */}
          <div id="map-section" className="grid grid-cols-1 lg:grid-cols-3 gap-3.5">
            
            {/* Map Column (2/3 width on large screens) */}
            <section className="lg:col-span-2 space-y-3">
              <div className="bg-[var(--panel-bg)] backdrop-blur-md border border-[var(--border-subtle)] rounded-xl p-3.5 shadow-xs space-y-3">
                <div className="flex items-center justify-between border-b border-[var(--border-subtle)] pb-2">
                  <div>
                    <h2 className="text-xs font-bold text-[var(--text-main)] uppercase tracking-wider">Interactive Map</h2>
                    <p className="text-[10px] text-[var(--text-muted)]">Landslide Risk GIS & Spatial Telemetry</p>
                  </div>
                  <span className="text-[11px] px-2 py-0.5 rounded-md bg-[var(--card-bg)] text-[var(--text-main)] font-semibold border border-[var(--border-subtle)] flex items-center gap-1.5 shadow-xs">
                    <Layers className="h-3 w-3 text-emerald-500" />
                    <span>Layers</span>
                  </span>
                </div>
                
                <div className="relative h-[420px] rounded-lg overflow-hidden border border-[var(--border-subtle)]">
                  <InteractiveMap 
                    selectedLocation={selectedLocation} 
                    onLocationSelect={handleLocationSelect} 
                    aoi={aoi} 
                    historicalData={historicalData}
                    activeOverlay={activeOverlay}
                    setActiveOverlay={setActiveOverlay}
                    overlayOpacity={overlayOpacity}
                    setOverlayOpacity={setOverlayOpacity}
                    terrainData={terrainData}
                    weatherData={weatherData}
                    fieldReports={fieldReports}
                    roadData={roadData}
                    isRoadLoading={isRoadLoading}
                    roadError={roadError}
                    showRoads={showRoads}
                    setShowRoads={setShowRoads}
                  />
                </div>

                {/* Selected Location display bar and Analysis Actions */}
                {selectedLocation && (
                  <div className="space-y-2.5 pt-0.5">
                    <div className="bg-[var(--card-bg)] border border-[var(--border-subtle)] rounded-lg p-2.5 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-2 text-xs">
                      <div className="flex items-center gap-2">
                        <div className="p-1.5 bg-emerald-500/10 text-emerald-500 rounded-lg border border-emerald-500/20 shrink-0">
                          <MapPin className="h-3.5 w-3.5" />
                        </div>
                        <div>
                          <p className="font-bold text-[var(--text-main)] text-xs">Selected Coordinate</p>
                          <p className="text-[10px] text-[var(--text-muted)]">Click Analyze to process the Area of Interest (AOI)</p>
                        </div>
                      </div>
                      
                      <div className="flex flex-wrap items-center gap-2 w-full sm:w-auto">
                        <div className="flex gap-1.5 font-mono text-xs flex-1 sm:flex-none">
                          <div className="bg-[var(--subcard-bg)] px-2 py-0.5 rounded border border-[var(--border-subtle)] flex-1 sm:flex-none text-center">
                            <span className="text-[var(--text-dim)] mr-1 font-bold text-[9px]">LAT:</span>
                            <span className="text-[var(--text-main)] font-bold text-xs">{selectedLocation.lat.toFixed(6)}</span>
                          </div>
                          <div className="bg-[var(--subcard-bg)] px-2 py-0.5 rounded border border-[var(--border-subtle)] flex-1 sm:flex-none text-center">
                            <span className="text-[var(--text-dim)] mr-1 font-bold text-[9px]">LNG:</span>
                            <span className="text-[var(--text-main)] font-bold text-xs">{selectedLocation.lng.toFixed(6)}</span>
                          </div>
                        </div>
                        
                        <button
                          onClick={handleAnalyzeLocation}
                          disabled={isAnalyzing}
                          className="w-full sm:w-auto px-3 py-1 bg-emerald-600 hover:bg-emerald-500 disabled:bg-slate-700 text-white disabled:text-slate-400 rounded-lg font-bold border border-emerald-500/30 disabled:border-transparent transition flex items-center justify-center gap-1.5 cursor-pointer disabled:cursor-not-allowed text-xs"
                        >
                          {isAnalyzing && <RefreshCw className="h-3 w-3 animate-spin" />}
                          <span>Analyze Location</span>
                        </button>

                        <button
                          onClick={() => setIsSitrepModalOpen(true)}
                          className="w-full sm:w-auto px-3 py-1 bg-rose-600 hover:bg-rose-500 text-white rounded-lg font-bold border border-rose-500/30 transition flex items-center justify-center gap-1.5 cursor-pointer text-xs"
                          title="Generate official 1-2 page NDMA SITREP incident briefing (PDF / Printable)"
                        >
                          <FileDown className="h-3 w-3" />
                          <span>Download SITREP</span>
                        </button>
                      </div>
                    </div>

                    {/* Error Box: e.g. Location outside NER */}
                    {analysisError && (
                      <div className="bg-rose-500/10 border border-rose-500/25 rounded-lg p-2.5 text-xs text-rose-500 space-y-1">
                        <p className="font-bold flex items-center gap-1.5">
                          <AlertTriangle className="h-3.5 w-3.5 text-rose-500" />
                          Location outside the North Eastern Region
                        </p>
                        <p className="text-[var(--text-muted)] pl-5 text-[10px]">
                          Please select a location within the North Eastern Region of India (Assam, Arunachal Pradesh, Manipur, Meghalaya, Mizoram, Nagaland, Tripura, or Sikkim).
                        </p>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </section>

            {/* Recent Alerts Column (1/3 width on large screens) */}
            <section className="space-y-3">
              <RecentAlertsPanel
                refreshKey={incidentRefreshKey}
                onLocateIncident={(coords) => {
                  if (coords && typeof coords.lat === 'number' && typeof coords.lng === 'number') {
                    setSelectedLocation({ lat: coords.lat, lng: coords.lng });
                  }
                }}
              />
            </section>

          </div>

          {/* Analysis & Intelligence Hub Section (Matching Reference Image) */}
          <section className="space-y-2 pt-0.5">
            <div className="flex items-center justify-between">
              <h2 className="text-xs font-bold text-[var(--text-main)] uppercase tracking-wider flex items-center gap-2">
                <Cpu className="h-3.5 w-3.5 text-emerald-500" />
                <span>Analysis & Intelligence</span>
              </h2>
              <span className="text-[10px] text-[var(--text-dim)] font-medium">9 Operational Modules</span>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-2 text-xs">
              {/* Module 1: Early Warning */}
              <div 
                onClick={() => document.getElementById('early-warning-section')?.scrollIntoView({ behavior: 'smooth' })}
                className="bg-[var(--card-bg)] hover:bg-[var(--subcard-bg)] border border-[var(--border-subtle)] hover:border-[var(--border-strong)] rounded-lg p-2 flex items-center gap-2 transition cursor-pointer group shadow-xs"
              >
                <div className="p-1.5 rounded-md bg-[var(--subcard-bg)] text-emerald-500 border border-[var(--border-subtle)] group-hover:border-emerald-500/40 transition shrink-0">
                  <Radio className="h-3.5 w-3.5" />
                </div>
                <div className="min-w-0">
                  <p className="font-bold text-[var(--text-main)] truncate text-[11px]">Early Warning</p>
                  <p className="text-[9px] text-[var(--text-muted)] truncate">Monitor and evaluate</p>
                </div>
              </div>

              {/* Module 2: Weather Telemetry */}
              <div 
                onClick={() => document.getElementById('weather-section')?.scrollIntoView({ behavior: 'smooth' })}
                className="bg-[var(--card-bg)] hover:bg-[var(--subcard-bg)] border border-[var(--border-subtle)] hover:border-[var(--border-strong)] rounded-lg p-2 flex items-center gap-2 transition cursor-pointer group shadow-xs"
              >
                <div className="p-1.5 rounded-md bg-[var(--subcard-bg)] text-sky-500 border border-[var(--border-subtle)] group-hover:border-sky-500/40 transition shrink-0">
                  <CloudRain className="h-3.5 w-3.5" />
                </div>
                <div className="min-w-0">
                  <p className="font-bold text-[var(--text-main)] truncate text-[11px]">Weather Telemetry</p>
                  <p className="text-[9px] text-[var(--text-muted)] truncate">Live weather data</p>
                </div>
              </div>

              {/* Module 3: Terrain Analysis */}
              <div 
                onClick={() => document.getElementById('terrain-section')?.scrollIntoView({ behavior: 'smooth' })}
                className="bg-[var(--card-bg)] hover:bg-[var(--subcard-bg)] border border-[var(--border-subtle)] hover:border-[var(--border-strong)] rounded-lg p-2 flex items-center gap-2 transition cursor-pointer group shadow-xs"
              >
                <div className="p-1.5 rounded-md bg-[var(--subcard-bg)] text-teal-500 border border-[var(--border-subtle)] group-hover:border-teal-500/40 transition shrink-0">
                  <Mountain className="h-3.5 w-3.5" />
                </div>
                <div className="min-w-0">
                  <p className="font-bold text-[var(--text-main)] truncate text-[11px]">Terrain Analysis</p>
                  <p className="text-[9px] text-[var(--text-muted)] truncate">DEM & terrain data</p>
                </div>
              </div>

              {/* Module 4: AI Susceptibility */}
              <div 
                onClick={() => document.getElementById('ai-analysis-section')?.scrollIntoView({ behavior: 'smooth' })}
                className="bg-[var(--card-bg)] hover:bg-[var(--subcard-bg)] border border-[var(--border-subtle)] hover:border-[var(--border-strong)] rounded-lg p-2 flex items-center gap-2 transition cursor-pointer group shadow-xs"
              >
                <div className="p-1.5 rounded-md bg-[var(--subcard-bg)] text-emerald-500 border border-[var(--border-subtle)] group-hover:border-emerald-500/40 transition shrink-0">
                  <Cpu className="h-3.5 w-3.5" />
                </div>
                <div className="min-w-0">
                  <p className="font-bold text-[var(--text-main)] truncate text-[11px]">AI Susceptibility</p>
                  <p className="text-[9px] text-[var(--text-muted)] truncate">ML risk assessment</p>
                </div>
              </div>

              {/* Module 5: Satellite Analysis */}
              <div 
                onClick={() => document.getElementById('satellite-section')?.scrollIntoView({ behavior: 'smooth' })}
                className="bg-[var(--card-bg)] hover:bg-[var(--subcard-bg)] border border-[var(--border-subtle)] hover:border-[var(--border-strong)] rounded-lg p-2 flex items-center gap-2 transition cursor-pointer group shadow-xs"
              >
                <div className="p-1.5 rounded-md bg-[var(--subcard-bg)] text-sky-500 border border-[var(--border-subtle)] group-hover:border-sky-500/40 transition shrink-0">
                  <Layers className="h-3.5 w-3.5" />
                </div>
                <div className="min-w-0">
                  <p className="font-bold text-[var(--text-main)] truncate text-[11px]">Satellite Analysis</p>
                  <p className="text-[9px] text-[var(--text-muted)] truncate">Sentinel-1 monitoring</p>
                </div>
              </div>

              {/* Module 6: Historical Catalog */}
              <div 
                onClick={() => document.getElementById('historical-section')?.scrollIntoView({ behavior: 'smooth' })}
                className="bg-[var(--card-bg)] hover:bg-[var(--subcard-bg)] border border-[var(--border-subtle)] hover:border-[var(--border-strong)] rounded-lg p-2 flex items-center gap-2 transition cursor-pointer group shadow-xs"
              >
                <div className="p-1.5 rounded-md bg-[var(--subcard-bg)] text-amber-500 border border-[var(--border-subtle)] group-hover:border-amber-500/40 transition shrink-0">
                  <Database className="h-3.5 w-3.5" />
                </div>
                <div className="min-w-0">
                  <p className="font-bold text-[var(--text-main)] truncate text-[11px]">Historical Catalog</p>
                  <p className="text-[9px] text-[var(--text-muted)] truncate">Past landslide data</p>
                </div>
              </div>

              {/* Module 7: Field Intelligence */}
              <div 
                onClick={() => setIsWorkspaceOpen(true)}
                className="bg-[var(--card-bg)] hover:bg-[var(--subcard-bg)] border border-[var(--border-subtle)] hover:border-[var(--border-strong)] rounded-lg p-2 flex items-center gap-2 transition cursor-pointer group shadow-xs"
              >
                <div className="p-1.5 rounded-md bg-[var(--subcard-bg)] text-emerald-500 border border-[var(--border-subtle)] group-hover:border-emerald-500/40 transition shrink-0">
                  <FileText className="h-3.5 w-3.5" />
                </div>
                <div className="min-w-0">
                  <p className="font-bold text-[var(--text-main)] truncate text-[11px]">Field Intelligence</p>
                  <p className="text-[9px] text-[var(--text-muted)] truncate">Ground & official reports</p>
                </div>
              </div>

              {/* Module 8: Road Intelligence */}
              <div 
                onClick={() => document.getElementById('road-section')?.scrollIntoView({ behavior: 'smooth' })}
                className="bg-[var(--card-bg)] hover:bg-[var(--subcard-bg)] border border-[var(--border-subtle)] hover:border-[var(--border-strong)] rounded-lg p-2 flex items-center gap-2 transition cursor-pointer group shadow-xs"
              >
                <div className="p-1.5 rounded-md bg-[var(--subcard-bg)] text-amber-500 border border-[var(--border-subtle)] group-hover:border-amber-500/40 transition shrink-0">
                  <TrafficCone className="h-3.5 w-3.5" />
                </div>
                <div className="min-w-0">
                  <p className="font-bold text-[var(--text-main)] truncate text-[11px]">Road Intelligence</p>
                  <p className="text-[9px] text-[var(--text-muted)] truncate">Access & disruption</p>
                </div>
              </div>

              {/* Module 9: Situation Assessment */}
              <div 
                onClick={() => document.getElementById('situation-section')?.scrollIntoView({ behavior: 'smooth' })}
                className="bg-[var(--card-bg)] hover:bg-[var(--subcard-bg)] border border-[var(--border-subtle)] hover:border-[var(--border-strong)] rounded-lg p-2 flex items-center gap-2 transition cursor-pointer group shadow-xs col-span-2 sm:col-span-1"
              >
                <div className="p-1.5 rounded-md bg-[var(--subcard-bg)] text-emerald-500 border border-[var(--border-subtle)] group-hover:border-emerald-500/40 transition shrink-0">
                  <Activity className="h-3.5 w-3.5" />
                </div>
                <div className="min-w-0">
                  <p className="font-bold text-[var(--text-main)] truncate text-[11px]">Situation Assessment</p>
                  <p className="text-[9px] text-[var(--text-muted)] truncate">Integrated overview</p>
                </div>
              </div>
            </div>
          </section>

        {/* Full Width Location Analysis & Operations Results Section */}
        {analysisResult && analysisResult.status === 'success' && (
          <div className="space-y-6">
            {/* Primary Analysis Result Card */}
            <div id="early-warning-section" className="bg-[var(--panel-bg)] backdrop-blur-md border border-[var(--border-subtle)] rounded-xl p-5 shadow-md space-y-4">
              <div className="flex items-center justify-between border-b border-[var(--border-subtle)] pb-2.5">
                      <h4 className="text-xs font-bold text-[var(--text-main)] uppercase tracking-wider">Analysis Result</h4>
                      <span className="text-xs px-2.5 py-0.5 rounded-full bg-emerald-500/10 text-emerald-500 border border-emerald-500/20 font-medium">
                        ✓ Inside NER
                      </span>
                    </div>

                    {/* Early Warning Status Section */}
                    <div className="border-b border-[var(--border-subtle)] pb-4">
                      <div className="flex items-center justify-between mb-3">
                        <h5 className="text-xs font-black text-[var(--text-main)] uppercase tracking-wider flex items-center gap-1.5">
                          <AlertTriangle className="h-4 w-4 text-emerald-500" />
                          Early Warning Decision Status
                        </h5>
                        {earlyWarningLoading && (
                          <span className="text-[10px] text-slate-400 flex items-center gap-1 animate-pulse">
                            <RefreshCw className="h-3 w-3 animate-spin text-emerald-400" /> Evaluating warning states...
                          </span>
                        )}
                      </div>

                      {earlyWarningLoading && !earlyWarningData && (
                        <div className="bg-[var(--card-bg)] border border-[var(--border-subtle)] rounded-xl p-4 text-center">
                          <RefreshCw className="h-5 w-5 text-emerald-500 animate-spin mx-auto mb-1" />
                          <p className="text-[10px] text-[var(--text-muted)] font-medium">Running early warning decision evaluations...</p>
                        </div>
                      )}

                      {earlyWarningError && (
                        <div className="bg-rose-500/5 border border-rose-500/10 rounded-xl p-3 text-xs text-rose-500 flex items-center gap-2">
                          <AlertTriangle className="h-4 w-4 text-rose-500 shrink-0" />
                          <div>
                            <p className="font-semibold text-[10px]">Early warning system offline.</p>
                            <p className="text-[9px] text-[var(--text-muted)]">{earlyWarningError}</p>
                          </div>
                        </div>
                      )}

                      {earlyWarningData && (
                        <div className="space-y-4">
                          {/* Alert Banner / Header */}
                          <div className={`p-4 rounded-xl border flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3 ${
                            earlyWarningData.warning_level === 'NORMAL' ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-700 dark:text-emerald-400' :
                            earlyWarningData.warning_level === 'WATCH' ? 'bg-amber-500/10 border-amber-500/30 text-amber-700 dark:text-amber-400' :
                            earlyWarningData.warning_level === 'ALERT' ? 'bg-orange-500/10 border-orange-500/30 text-orange-700 dark:text-orange-400' :
                            'bg-rose-500/10 border-rose-500/30 text-rose-700 dark:text-rose-400'
                          }`}>
                            <div className="space-y-0.5">
                              <span className="text-[9px] uppercase font-bold tracking-wider text-[var(--text-dim)]">Operational Warning State</span>
                              <h3 className="text-xl font-black uppercase tracking-wider">{earlyWarningData.warning_level}</h3>
                            </div>
                            
                            <div className="flex flex-col items-start sm:items-end gap-1.5">
                              <div className="flex items-center gap-1.5">
                                <span className="text-[9px] uppercase font-bold tracking-wider text-[var(--text-dim)]">Decision Mode:</span>
                                <span className="text-[10.5px] font-mono px-2 py-0.5 bg-[var(--card-bg)] rounded border border-[var(--border-subtle)] text-[var(--text-main)]">
                                  {earlyWarningData.decision_mode}
                                </span>
                              </div>

                              <div className="flex items-center gap-1.5">
                                <button
                                  onClick={() => handleOpenAlertDispatch({
                                    warningLevel: earlyWarningData.warning_level,
                                    riskScore: earlyWarningData.hazard_context?.composite_hazard_index
                                  })}
                                  className="px-3 py-1 bg-rose-600 hover:bg-rose-500 text-white rounded-lg font-bold text-[10px] flex items-center gap-1.5 shadow-sm transition cursor-pointer"
                                  title="Broadcast Warning to Response Authorities (NDRF/SDRF/DEOC)"
                                >
                                  <Radio className="h-3 w-3 animate-pulse" />
                                  <span>Broadcast Alert</span>
                                </button>

                                <button
                                  onClick={() => setIsSitrepModalOpen(true)}
                                  className="px-3 py-1 bg-[var(--card-bg)] hover:bg-[var(--subcard-bg)] border border-[var(--border-subtle)] text-[var(--text-main)] rounded-lg font-bold text-[10px] flex items-center gap-1.5 shadow-sm transition cursor-pointer"
                                  title="Download official NDMA SITREP incident briefing (PDF / Printable)"
                                >
                                  <FileDown className="h-3 w-3 text-rose-500" />
                                  <span>Download SITREP (PDF)</span>
                                </button>
                              </div>
                            </div>
                          </div>

                          {/* Details Grid */}
                          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-[10px]">
                            {/* Hazard Context */}
                            <div className="bg-[var(--card-bg)] border border-[var(--border-subtle)] p-3 rounded-lg space-y-1">
                              <span className="text-[var(--text-dim)] block uppercase font-bold tracking-wider">Environmental Hazard Context</span>
                              <div className="flex justify-between items-center text-xs mt-1">
                                <span className="text-[var(--text-muted)] font-medium">Composite Hazard Index:</span>
                                <span className="text-[var(--text-main)] font-bold">{earlyWarningData.hazard_context.composite_hazard_index.toFixed(1)} / 100</span>
                              </div>
                              <div className="flex justify-between items-center text-xs">
                                <span className="text-[var(--text-muted)] font-medium">Susceptibility Class:</span>
                                <span className="text-[var(--text-main)] font-bold">{earlyWarningData.hazard_context.hazard_category}</span>
                              </div>
                            </div>

                            {/* Satellite Observational Verification Context */}
                            <div className="bg-[var(--card-bg)] border border-[var(--border-subtle)] p-3 rounded-lg space-y-1">
                              <span className="text-[var(--text-dim)] block uppercase font-bold tracking-wider">Satellite Verification Evidence</span>
                              <div className="flex justify-between items-center text-xs mt-1">
                                <span className="text-[var(--text-muted)] font-medium">Pair Alignment Status:</span>
                                <span className="text-[var(--text-main)] font-bold">{earlyWarningData.satellite_context.status}</span>
                              </div>
                              <div className="flex justify-between items-center text-xs">
                                <span className="text-[var(--text-muted)] font-medium">RSCI Value:</span>
                                <span className="text-[var(--text-main)] font-bold">
                                  {earlyWarningData.satellite_context.rsci !== null 
                                    ? `${earlyWarningData.satellite_context.rsci.toFixed(1)} / 100` 
                                    : 'N/A'}
                                </span>
                              </div>
                            </div>
                          </div>

                          {/* Recommended Action & Reasoning */}
                          <div className="bg-[var(--subcard-bg)] border border-[var(--border-subtle)] rounded-xl p-3.5 space-y-2.5">
                            <div>
                              <span className="text-[9px] text-[var(--text-dim)] uppercase font-black tracking-wide block">Action Guidelines</span>
                              <p className="text-xs text-[var(--text-main)] leading-relaxed font-bold mt-0.5">
                                {earlyWarningData.recommended_action}
                              </p>
                            </div>
                            
                            <div className="border-t border-[var(--border-subtle)] pt-2">
                              <span className="text-[9px] text-[var(--text-dim)] uppercase font-black tracking-wide block">Warning Decision Reasoning</span>
                              <p className="text-[10.5px] text-[var(--text-muted)] leading-relaxed font-medium mt-0.5">
                                {earlyWarningData.reasoning}
                              </p>
                            </div>

                            <div className="border-t border-[var(--border-subtle)] pt-2 text-[9px] text-[var(--text-dim)] font-mono flex justify-between items-center">
                              <span>Observational verification:</span>
                              <span className="text-[var(--text-muted)]">{earlyWarningData.observational_verification}</span>
                            </div>
                          </div>

                          {/* Notices */}
                          <div className="bg-[var(--subcard-bg)] border border-[var(--border-subtle)] p-3 rounded-lg space-y-2">
                            <p className="text-[9px] text-emerald-700 dark:text-emerald-400 leading-normal font-mono">
                              <strong>\* Scientific Notice:</strong> {earlyWarningData.scientific_notice}
                            </p>
                            <p className="text-[9px] text-[var(--text-muted)] leading-normal border-t border-[var(--border-subtle)] pt-1.5 font-medium font-sans">
                              <strong>\* Operational Notice:</strong> Warning Level is an operational decision-support recommendation and NOT a mathematical probability of landslide occurrence. The system does not independently confirm that a landslide has occurred.
                            </p>
                          </div>
                        </div>
                      )}
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-3 gap-6 text-xs">
                      <div>
                        <span className="text-[var(--text-dim)] uppercase tracking-wider font-semibold block mb-1">Target Region</span>
                        <p className="text-[var(--text-main)] font-medium text-sm">North Eastern Region (India)</p>
                        <p className="text-[10px] text-[var(--text-muted)] mt-1">Verified via spatial boundary lookup</p>
                      </div>

                      <div>
                        <span className="text-[var(--text-dim)] uppercase tracking-wider font-semibold block mb-1">Area of Interest (AOI)</span>
                        <p className="text-[var(--text-main)] font-medium text-sm">{aoi?.radius_km} km Radius Bounding Box</p>
                        <p className="text-[10px] text-[var(--text-muted)] mt-1">Geographically scaled at target latitude</p>
                      </div>

                      <div className="md:col-span-1">
                        <span className="text-[var(--text-dim)] uppercase tracking-wider font-semibold block mb-1">Bounding Box Coordinates</span>
                        <div className="grid grid-cols-2 gap-x-2 gap-y-0.5 font-mono text-[10px] bg-[var(--subcard-bg)] p-2 rounded-lg border border-[var(--border-subtle)]">
                          <span className="text-[var(--text-dim)]">North:</span>
                          <span className="text-[var(--text-main)] text-right">{aoi?.bounding_box.north.toFixed(6)}</span>
                          <span className="text-[var(--text-dim)]">South:</span>
                          <span className="text-[var(--text-main)] text-right">{aoi?.bounding_box.south.toFixed(6)}</span>
                          <span className="text-[var(--text-dim)]">East:</span>
                          <span className="text-[var(--text-main)] text-right">{aoi?.bounding_box.east.toFixed(6)}</span>
                          <span className="text-[var(--text-dim)]">West:</span>
                          <span className="text-[var(--text-main)] text-right">{aoi?.bounding_box.west.toFixed(6)}</span>
                        </div>
                      </div>
                    </div>

                    {/* Live Weather Telemetry Section */}
                    <div id="weather-section" className="border-t border-[var(--border-subtle)] pt-4 mt-2">
                      <div className="flex items-center justify-between mb-3">
                        <h5 className="text-[11px] font-bold text-[var(--text-main)] uppercase tracking-wider flex items-center gap-1.5">
                          <Activity className="h-4 w-4 text-sky-500" />
                          Live Weather Telemetry (Open-Meteo)
                        </h5>
                        {isWeatherLoading && (
                          <span className="text-[10px] text-[var(--text-muted)] flex items-center gap-1">
                            <RefreshCw className="h-3 w-3 animate-spin text-sky-500" /> Fetching live conditions...
                          </span>
                        )}
                      </div>

                      {isWeatherLoading && !weatherData && (
                        <div className="bg-[var(--subcard-bg)] border border-[var(--border-subtle)] rounded-xl p-4 text-center">
                          <RefreshCw className="h-5 w-5 text-sky-500 animate-spin mx-auto mb-1" />
                          <p className="text-[10px] text-[var(--text-muted)]">Querying real-time meteorological observations...</p>
                        </div>
                      )}

                      {weatherError && (
                        <div className="bg-rose-500/5 border border-rose-500/10 rounded-xl p-3 text-xs text-rose-500 flex items-center gap-2">
                          <AlertTriangle className="h-4 w-4 text-rose-500 shrink-0" />
                          <div>
                            <p className="font-semibold text-[10px]">Weather Data Unavailable</p>
                            <p className="text-[9px] text-[var(--text-muted)]">{weatherError}</p>
                          </div>
                        </div>
                      )}

                      {weatherData && (
                        <div className="space-y-4">
                          <div className="grid grid-cols-2 sm:grid-cols-4 md:grid-cols-7 gap-3 text-xs">
                            {/* Temperature */}
                            <div className="bg-[var(--subcard-bg)] border border-[var(--border-subtle)] rounded-xl p-3 flex flex-col justify-between">
                              <span className="text-[var(--text-dim)] text-[10px] uppercase font-semibold">Temperature</span>
                              <p className="text-sm font-bold text-[var(--text-main)] mt-1">
                                {weatherData.temperature !== null ? `${weatherData.temperature}${weatherData.temperature_unit}` : 'N/A'}
                              </p>
                            </div>

                            {/* Relative Humidity */}
                            <div className="bg-[var(--subcard-bg)] border border-[var(--border-subtle)] rounded-xl p-3 flex flex-col justify-between">
                              <span className="text-[var(--text-dim)] text-[10px] uppercase font-semibold">Humidity</span>
                              <p className="text-sm font-bold text-[var(--text-main)] mt-1">
                                {weatherData.relative_humidity !== null ? `${weatherData.relative_humidity}${weatherData.relative_humidity_unit}` : 'N/A'}
                              </p>
                            </div>

                            {/* Current Precipitation */}
                            <div className="bg-[var(--subcard-bg)] border border-[var(--border-subtle)] rounded-xl p-3 flex flex-col justify-between">
                              <span className="text-[var(--text-dim)] text-[10px] uppercase font-semibold">Current Rain</span>
                              <p className="text-sm font-bold text-[var(--text-main)] mt-1">
                                {weatherData.current_precipitation !== null ? `${weatherData.current_precipitation} ${weatherData.current_precipitation_unit}` : '0.0 mm'}
                              </p>
                            </div>

                            {/* 24h Precipitation */}
                            <div className="bg-[var(--subcard-bg)] border border-[var(--border-subtle)] rounded-xl p-3 flex flex-col justify-between">
                              <span className="text-[var(--text-dim)] text-[10px] uppercase font-semibold">24h Precip</span>
                              <p className="text-sm font-bold text-[var(--text-main)] mt-1">
                                {weatherData.daily_precipitation !== null ? `${weatherData.daily_precipitation} ${weatherData.daily_precipitation_unit}` : '0.0 mm'}
                              </p>
                            </div>

                            {/* 3-Day Cumulative Precipitation */}
                            <div className="bg-[var(--subcard-bg)] border border-[var(--border-subtle)] rounded-xl p-3 flex flex-col justify-between">
                              <span className="text-[var(--text-dim)] text-[10px] uppercase font-semibold">3-Day Cumul.</span>
                              <p className="text-sm font-bold text-sky-700 dark:text-sky-400 mt-1">
                                {weatherData.three_day_cumulative !== null ? `${weatherData.three_day_cumulative.toFixed(1)} mm` : '0.0 mm'}
                              </p>
                            </div>

                            {/* 7-Day Cumulative Precipitation */}
                            <div className="bg-[var(--subcard-bg)] border border-[var(--border-subtle)] rounded-xl p-3 flex flex-col justify-between">
                              <span className="text-[var(--text-dim)] text-[10px] uppercase font-semibold">7-Day Cumul.</span>
                              <p className="text-sm font-bold text-sky-700 dark:text-sky-300 mt-1">
                                {weatherData.seven_day_cumulative !== null ? `${weatherData.seven_day_cumulative.toFixed(1)} mm` : '0.0 mm'}
                              </p>
                            </div>

                            {/* Saturation Classification */}
                            <div className="bg-[var(--subcard-bg)] border border-[var(--border-subtle)] rounded-xl p-3 flex flex-col justify-between col-span-2 sm:col-span-1">
                              <span className="text-[var(--text-dim)] text-[10px] uppercase font-semibold">Soil Saturation</span>
                              <span className={`inline-block text-center mt-1 text-[10px] font-extrabold uppercase px-2 py-0.5 rounded border ${
                                weatherData.saturation_classification === 'Dry' ? 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border-emerald-500/20' :
                                weatherData.saturation_classification === 'Light' ? 'bg-sky-500/10 text-sky-700 dark:text-sky-400 border-sky-500/20' :
                                weatherData.saturation_classification === 'Moderate' ? 'bg-yellow-500/10 text-yellow-700 dark:text-yellow-400 border-yellow-500/20' :
                                weatherData.saturation_classification === 'Heavy' ? 'bg-orange-500/10 text-orange-700 dark:text-orange-400 border-orange-500/20' :
                                'bg-rose-500/15 text-rose-700 dark:text-rose-400 border-rose-500/30' // Extreme
                              }`}>
                                {weatherData.saturation_classification || 'Dry'}
                              </span>
                            </div>
                          </div>

                          {/* 7-Day Antecedent Rainfall Trend Bar Chart */}
                          {weatherData.daily_precipitation_history && weatherData.daily_precipitation_history.length > 0 && (
                            <div className="bg-[var(--subcard-bg)] border border-[var(--border-subtle)] p-4 rounded-xl space-y-3">
                              <div className="flex justify-between items-center">
                                <span className="text-[var(--text-dim)] text-[10px] uppercase font-bold block">Antecedent Rainfall Trend (Past 7 Days + Today)</span>
                                <span className="text-[9px] text-[var(--text-dim)] font-mono">Unit: mm</span>
                              </div>
                              <div className="flex items-end justify-between h-20 pt-2 px-1 relative">
                                {weatherData.daily_precipitation_history.map((rec, idx) => {
                                  const precip_values = weatherData.daily_precipitation_history.map(h => h.precipitation_mm || 0);
                                  const maxVal = Math.max(...precip_values, 10);
                                  const barHeightPercent = ((rec.precipitation_mm || 0) / maxVal) * 100;
                                  
                                  return (
                                    <div key={idx} className="flex flex-col items-center flex-1 group relative h-full justify-end">
                                      {/* Tooltip on hover */}
                                      <div className="absolute bottom-full mb-1.5 bg-[var(--card-bg)] border border-[var(--border-subtle)] text-[9px] text-[var(--text-main)] px-2 py-0.5 rounded opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none whitespace-nowrap z-10 shadow-lg">
                                        {rec.precipitation_mm?.toFixed(1) || '0.0'} mm ({rec.date})
                                      </div>
                                      {/* Bar */}
                                      <div 
                                        className={`w-4 sm:w-6 rounded-t transition-all duration-300 ${
                                          rec.precipitation_mm > 50 ? 'bg-sky-500 hover:bg-sky-400' :
                                          rec.precipitation_mm > 10 ? 'bg-sky-600 hover:bg-sky-500' :
                                          rec.precipitation_mm > 0 ? 'bg-sky-700/70 hover:bg-sky-600' :
                                          'bg-[var(--border-subtle)] hover:bg-[var(--border-strong)]'
                                        }`}
                                        style={{ height: `${Math.max(4, barHeightPercent)}%` }}
                                      />
                                      {/* Label (Day number of month) */}
                                      <span className="text-[8px] text-[var(--text-dim)] font-mono mt-1.5">
                                        {rec.date ? rec.date.substring(8, 10) : ''}
                                      </span>
                                    </div>
                                  );
                                })}
                              </div>
                            </div>
                          )}
                        </div>
                      )}

                      {weatherData && (
                        <div className="flex justify-between items-center text-[9px] text-[var(--text-dim)] mt-2 font-mono">
                          <span>Source: Open-Meteo API</span>
                          <span>Last Checked: {new Date(weatherData.timestamp).toLocaleTimeString()} (Local)</span>
                        </div>
                      )}
                    </div>

                    {/* Local Terrain Analysis Section */}
                    <div id="terrain-section" className="border-t border-[var(--border-subtle)] pt-4 mt-4">
                      <div className="flex items-center justify-between mb-3">
                        <h5 className="text-[11px] font-bold text-[var(--text-main)] uppercase tracking-wider flex items-center gap-1.5">
                          <Layers className="h-4 w-4 text-teal-500" />
                          Local Terrain Analysis (Copernicus DEM)
                        </h5>
                        {isTerrainLoading && (
                          <span className="text-[10px] text-[var(--text-muted)] flex items-center gap-1">
                            <RefreshCw className="h-3 w-3 animate-spin text-teal-500" /> Analyzing terrain...
                          </span>
                        )}
                      </div>

                      {isTerrainLoading && !terrainData && (
                        <div className="bg-[var(--subcard-bg)] border border-[var(--border-subtle)] rounded-xl p-4 text-center">
                          <RefreshCw className="h-5 w-5 text-teal-500 animate-spin mx-auto mb-1" />
                          <p className="text-[10px] text-[var(--text-muted)] font-medium">Querying and computing local digital elevation parameters...</p>
                        </div>
                      )}

                      {terrainError && (
                        <div className="bg-rose-500/5 border border-rose-500/10 rounded-xl p-3 text-xs text-rose-500 flex items-center gap-2">
                          <AlertTriangle className="h-4 w-4 text-rose-500 shrink-0" />
                          <div>
                            <p className="font-semibold text-[10px]">Terrain data unavailable</p>
                            <p className="text-[9px] text-[var(--text-muted)]">{terrainError}</p>
                          </div>
                        </div>
                      )}

                      {!isTerrainLoading && !terrainData && !terrainError && (
                        <div className="bg-[var(--subcard-bg)] border border-[var(--border-subtle)] rounded-xl p-4 text-center">
                          <Layers className="h-5 w-5 text-[var(--text-dim)] mx-auto mb-1" />
                          <p className="text-[10px] text-[var(--text-muted)] font-medium">Select and process a satellite scene above to trigger local terrain analysis.</p>
                        </div>
                      )}

                      {terrainData && (
                        <div className="space-y-3">
                          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-xs">
                            {/* Min Elevation */}
                            <div className="bg-[var(--subcard-bg)] border border-[var(--border-subtle)] rounded-xl p-3 flex flex-col justify-between">
                              <span className="text-[var(--text-dim)] text-[10px] uppercase font-semibold">Min Elevation</span>
                              <p className="text-base font-bold text-[var(--text-main)] mt-1">
                                {terrainData.statistics.min_elevation !== null ? `${terrainData.statistics.min_elevation} m` : 'N/A'}
                              </p>
                            </div>

                            {/* Max Elevation */}
                            <div className="bg-[var(--subcard-bg)] border border-[var(--border-subtle)] rounded-xl p-3 flex flex-col justify-between">
                              <span className="text-[var(--text-dim)] text-[10px] uppercase font-semibold">Max Elevation</span>
                              <p className="text-base font-bold text-[var(--text-main)] mt-1">
                                {terrainData.statistics.max_elevation !== null ? `${terrainData.statistics.max_elevation} m` : 'N/A'}
                              </p>
                            </div>

                            {/* Average Slope */}
                            <div className="bg-[var(--subcard-bg)] border border-[var(--border-subtle)] rounded-xl p-3 flex flex-col justify-between">
                              <span className="text-[var(--text-dim)] text-[10px] uppercase font-semibold">Average Slope</span>
                              <div className="mt-1 flex items-baseline gap-2">
                                <p className="text-base font-bold text-[var(--text-main)]">
                                  {terrainData.statistics.mean_slope !== null ? `${terrainData.statistics.mean_slope.toFixed(1)}°` : 'N/A'}
                                </p>
                                {terrainData.statistics.mean_slope !== null && (
                                  <span className={`text-[9px] px-1 py-0.5 rounded font-bold uppercase ${
                                    terrainData.statistics.mean_slope < 15.0 ? 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border border-emerald-500/20' :
                                    terrainData.statistics.mean_slope < 30.0 ? 'bg-amber-500/10 text-amber-700 dark:text-amber-400 border border-amber-500/20' :
                                    'bg-rose-500/10 text-rose-700 dark:text-rose-400 border border-rose-500/20'
                                  }`}>
                                    {terrainData.statistics.mean_slope < 15.0 ? 'Normal' :
                                     terrainData.statistics.mean_slope < 30.0 ? 'Moderate' :
                                     'High Risk'}
                                  </span>
                                )}
                              </div>
                            </div>

                            {/* Dominant Aspect */}
                            <div className="bg-[var(--subcard-bg)] border border-[var(--border-subtle)] rounded-xl p-3 flex flex-col justify-between">
                              <span className="text-[var(--text-dim)] text-[10px] uppercase font-semibold">Dominant Aspect</span>
                              <p className="text-base font-bold text-[var(--text-main)] mt-1">
                                {terrainData.statistics.dominant_aspect || 'N/A'}
                              </p>
                            </div>
                          </div>

                          <div className="flex justify-between items-center text-[9px] text-[var(--text-dim)] mt-2 font-mono">
                            <span>Source: Copernicus DEM GLO-30</span>
                            <span>Target CRS: {terrainData.statistics.output_crs || 'UTM zone'}</span>
                          </div>

                          {terrainData.statistics.mean_slope >= 30.0 && (
                            <p className="text-[9px] text-rose-700 dark:text-rose-400 leading-normal border border-rose-500/20 bg-rose-500/5 p-2 rounded-lg">
                              * Warning: High landslide predisposition due to steep terrain slope (&ge; 30°). Landslide susceptibility also depends on geology, soil moisture, and trigger events.
                            </p>
                          )}
                          {terrainData.statistics.mean_slope >= 15.0 && terrainData.statistics.mean_slope < 30.0 && (
                            <p className="text-[9px] text-amber-700 dark:text-amber-400 leading-normal border border-amber-500/20 bg-amber-500/5 p-2 rounded-lg">
                              * Notice: Moderate landslide predisposition due to moderate slope (15°–30°). Landslide susceptibility also depends on geology, soil moisture, and trigger events.
                            </p>
                          )}
                          {terrainData.statistics.mean_slope < 15.0 && (
                            <p className="text-[9px] text-emerald-700 dark:text-emerald-400 leading-normal border border-emerald-500/20 bg-emerald-500/5 p-2 rounded-lg">
                              * Info: Low landslide predisposition due to gentle slope (&lt; 15°). Landslide susceptibility also depends on geology, soil moisture, and trigger events.
                            </p>
                          )}
                        </div>
                      )}
                      {/* Composite Landslide Hazard Index Section */}
                      <div className="border-t border-[var(--border-subtle)] pt-5 mt-5">
                        <div className="flex items-center justify-between mb-3">
                          <h5 className="text-xs font-black text-[var(--text-main)] uppercase tracking-wider flex items-center gap-1.5">
                            <ShieldCheck className="h-5 w-5 text-emerald-500" />
                            Composite Landslide Hazard Index (0-100)
                          </h5>
                          {isCompositeRiskLoading && (
                            <span className="text-[10px] text-[var(--text-muted)] flex items-center gap-1 animate-pulse">
                              <RefreshCw className="h-3 w-3 animate-spin text-emerald-500" /> Evaluating composite hazard...
                            </span>
                          )}
                        </div>

                        {isCompositeRiskLoading && !compositeRiskData && (
                          <div className="bg-[var(--subcard-bg)] border border-[var(--border-subtle)] rounded-xl p-5 text-center">
                            <RefreshCw className="h-6 w-6 text-emerald-500 animate-spin mx-auto mb-2" />
                            <p className="text-xs text-emerald-700 dark:text-emerald-400 font-bold">Generating composite hazard index...</p>
                          </div>
                        )}

                        {compositeRiskError && (
                          <div className="bg-rose-500/5 border border-rose-500/10 rounded-xl p-3 text-xs text-rose-500 flex items-center gap-2">
                            <AlertTriangle className="h-4 w-4 text-rose-500 shrink-0" />
                            <div>
                              <p className="font-semibold text-[10px]">Composite hazard calculation failed.</p>
                              <p className="text-[9px] text-[var(--text-muted)]">{compositeRiskError}</p>
                            </div>
                          </div>
                        )}

                        {!isCompositeRiskLoading && !compositeRiskData && !compositeRiskError && (
                          <div className="bg-[var(--subcard-bg)] border border-[var(--border-subtle)] rounded-xl p-4 text-center">
                            <p className="text-[10px] text-[var(--text-muted)] font-medium">Analyze a location to calculate composite landslide hazard index.</p>
                          </div>
                        )}

                        {compositeRiskData && (
                          <div className="space-y-4 bg-[var(--subcard-bg)] p-4 rounded-xl border border-[var(--border-subtle)] shadow-md">
                            {/* Overall Score Header */}
                            <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3 bg-[var(--card-bg)] p-4 rounded-xl border border-[var(--border-subtle)]">
                              <div>
                                <span className="text-[var(--text-dim)] text-[10px] uppercase font-bold block tracking-wider">Composite Hazard Index</span>
                                <div className="flex items-baseline gap-1 mt-1">
                                  <span className="text-3xl font-black text-emerald-700 dark:text-emerald-400">
                                    {compositeRiskData.composite_risk_index.toFixed(1)}
                                  </span>
                                  <span className="text-[var(--text-dim)] text-[10px] font-mono">/ 100</span>
                                </div>
                              </div>

                              <div className="flex flex-col items-start sm:items-end gap-1">
                                <span className="text-[var(--text-dim)] text-[10px] uppercase font-bold tracking-wider">Overall Hazard Category</span>
                                <span className={`px-3 py-1 rounded-full text-xs font-black uppercase border tracking-wider mt-0.5 shadow-sm ${
                                  compositeRiskData.risk_level === 'Low' ? 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border-emerald-500/30' :
                                  compositeRiskData.risk_level === 'Moderate' ? 'bg-yellow-500/10 text-yellow-700 dark:text-yellow-400 border-yellow-500/30' :
                                  compositeRiskData.risk_level === 'High' ? 'bg-orange-500/10 text-orange-700 dark:text-orange-400 border-orange-500/30' :
                                  'bg-rose-500/15 text-rose-700 dark:text-rose-400 border-rose-500/40' // Very High
                                }`}>
                                  {compositeRiskData.risk_level}
                                </span>
                              </div>
                            </div>

                            {/* Progress bar */}
                            {(() => {
                              const score = compositeRiskData.composite_risk_index;
                              return (
                                <div className="space-y-1">
                                  <div className="w-full bg-[var(--card-bg)] rounded-full h-2.5 overflow-hidden border border-[var(--border-subtle)]">
                                    <div
                                      className={`h-full rounded-full transition-all duration-500 ${
                                        compositeRiskData.risk_level === 'Low' ? 'bg-emerald-500' :
                                        compositeRiskData.risk_level === 'Moderate' ? 'bg-yellow-500' :
                                        compositeRiskData.risk_level === 'High' ? 'bg-orange-500' :
                                        'bg-rose-500'
                                      }`}
                                      style={{ width: `${score}%` }}
                                    />
                                  </div>
                                  <div className="flex justify-between text-[9px] text-[var(--text-dim)] font-mono">
                                    <span>0</span>
                                    <span>25</span>
                                    <span>50</span>
                                    <span>75</span>
                                    <span>100</span>
                                  </div>
                                </div>
                              );
                            })()}

                            {/* Component Breakdown Card */}
                            <div className="bg-[var(--card-bg)] border border-[var(--border-subtle)] rounded-xl p-3 space-y-2.5">
                              <span className="text-[10px] text-[var(--text-dim)] uppercase font-black tracking-wide block border-b border-[var(--border-subtle)] pb-1.5">
                                Hazard Component Breakdown
                              </span>
                              
                              <div className="space-y-2 text-[11px]">
                                {/* ML Susceptibility */}
                                <div className="flex justify-between items-center">
                                  <div className="flex items-center gap-1.5">
                                    <span className="w-1.5 h-1.5 rounded-full bg-teal-500" />
                                    <span className="text-[var(--text-muted)]">ML Static Susceptibility:</span>
                                  </div>
                                  <span className="text-[var(--text-main)] font-medium">
                                    {compositeRiskData.components.static_susceptibility.index.toFixed(1)} / 100 (Prob: {compositeRiskData.components.static_susceptibility.probability.toFixed(3)})
                                  </span>
                                </div>

                                {/* Historical Proximity/Density Multiplier */}
                                <div className="flex justify-between items-center">
                                  <div className="flex items-center gap-1.5">
                                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                                    <span className="text-[var(--text-muted)]">Historical Vulnerability:</span>
                                  </div>
                                  <span className="text-[var(--text-main)] font-medium">
                                    {compositeRiskData.components.historical_context.multiplier.toFixed(2)}x (Score: {compositeRiskData.components.historical_context.historical_score.toFixed(1)})
                                  </span>
                                </div>

                                {/* Rainfall Multiplier */}
                                <div className="flex justify-between items-center">
                                  <div className="flex items-center gap-1.5">
                                    <span className="w-1.5 h-1.5 rounded-full bg-sky-500" />
                                    <span className="text-[var(--text-muted)]">Rainfall Trigger:</span>
                                  </div>
                                  <span className="text-[var(--text-main)] font-medium">
                                    {compositeRiskData.components.rainfall_trigger.multiplier.toFixed(2)}x (Score: {compositeRiskData.components.rainfall_trigger.rainfall_score.toFixed(1)})
                                  </span>
                                </div>
                              </div>
                            </div>

                            {/* Dynamic Explanation */}
                            <div className="bg-[var(--card-bg)] border border-[var(--border-subtle)] p-3 rounded-lg">
                              <span className="text-[9px] text-[var(--text-dim)] uppercase font-black tracking-wider block mb-1">Assessment Analysis</span>
                              <p className="text-[10.5px] text-[var(--text-muted)] leading-relaxed font-medium">
                                {compositeRiskData.explanation}
                              </p>
                            </div>

                            {/* Footer metadata */}
                            <div className="flex justify-between items-center text-[9px] text-[var(--text-dim)] font-mono pt-1 border-b border-[var(--border-subtle)] pb-2">
                              <span>Formula Version: {compositeRiskData.formula_version}</span>
                              <span>Target: NER region</span>
                            </div>

                            {/* Scientific Notice */}
                            <div className="bg-[var(--card-bg)] border border-[var(--border-subtle)] p-2.5 rounded-lg mt-2">
                              <p className="text-[9px] text-emerald-700 dark:text-emerald-400 leading-normal font-sans">
                                * Scientific Notice: This index represents a relative multi-factor hazard level (0–100 scale), combining static terrain predisposition, historical proximity, and dynamic rainfall trigger modulators. A value of 100/100 denotes critical relative susceptibility under severe triggers, NOT a 100% mathematical probability or physical certainty of a landslide event occurring.
                              </p>
                            </div>
                          </div>
                        )}
                      </div>

                      {/* Satellite Surface Change Monitoring Section */}
                      <div className="border-t border-[var(--border-subtle)] pt-5 mt-5">
                        <div className="flex items-center justify-between mb-3">
                          <h5 className="text-xs font-black text-[var(--text-main)] uppercase tracking-wider flex items-center gap-1.5">
                            <Layers className="h-5 w-5 text-emerald-500" />
                            Satellite Surface Change Monitoring
                          </h5>
                          {satelliteChangeLoading && (
                            <span className="text-[10px] text-[var(--text-muted)] flex items-center gap-1 animate-pulse">
                              <RefreshCw className="h-3 w-3 animate-spin text-emerald-500" /> Querying Sentinel-1 radar...
                            </span>
                          )}
                        </div>

                        {satelliteChangeLoading && !satelliteChangeData && (
                          <div className="bg-[var(--subcard-bg)] border border-[var(--border-subtle)] rounded-xl p-5 text-center">
                            <RefreshCw className="h-6 w-6 text-emerald-500 animate-spin mx-auto mb-2" />
                            <p className="text-xs text-emerald-700 dark:text-emerald-400 font-bold">Querying and analyzing Sentinel-1 radar change data...</p>
                          </div>
                        )}

                        {satelliteChangeError && (
                          <div className="bg-rose-500/5 border border-rose-500/10 rounded-xl p-3 text-xs text-rose-500 flex items-center gap-2">
                            <AlertTriangle className="h-4 w-4 text-rose-500 shrink-0" />
                            <div>
                              <p className="font-semibold text-[10px]">Radar analysis failed.</p>
                              <p className="text-[9px] text-[var(--text-muted)]">{satelliteChangeError}</p>
                            </div>
                          </div>
                        )}

                        {!satelliteChangeLoading && !satelliteChangeData && !satelliteChangeError && (
                          <div className="bg-[var(--subcard-bg)] border border-[var(--border-subtle)] rounded-xl p-4 text-center">
                            <p className="text-[10px] text-[var(--text-muted)] font-medium">Analyze a location to request multi-temporal radar surface change data.</p>
                          </div>
                        )}

                        {satelliteChangeData && satelliteChangeData.status !== 'PAIRED_SUCCESS' && (
                          <div className="bg-amber-500/5 border border-amber-500/20 rounded-xl p-4 text-center space-y-2">
                            <AlertTriangle className="h-5 w-5 text-amber-500 mx-auto" />
                            <h6 className="text-[11px] font-bold text-amber-700 dark:text-amber-400 uppercase tracking-wide">Radar Alignment Unavailable</h6>
                            <p className="text-[10.5px] text-[var(--text-muted)] leading-normal">
                              {satelliteChangeData.message || 'No compatible scene pair found for change analysis.'}
                            </p>
                          </div>
                        )}

                        {satelliteChangeData && satelliteChangeData.status === 'PAIRED_SUCCESS' && (
                          <div className="space-y-4 bg-[var(--subcard-bg)] p-4 rounded-xl border border-[var(--border-subtle)] shadow-md">
                            
                            {/* Score header */}
                            <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3 bg-[var(--card-bg)] p-4 rounded-xl border border-[var(--border-subtle)]">
                              <div>
                                <span className="text-[var(--text-dim)] text-[10px] uppercase font-bold block tracking-wider">Radar Surface Change Index (RSCI)</span>
                                <div className="flex items-baseline gap-1 mt-1">
                                  <span className="text-3xl font-black text-emerald-700 dark:text-emerald-400">
                                    {satelliteChangeData.radar_surface_change_signal.radar_surface_change_index.toFixed(1)}
                                  </span>
                                  <span className="text-[var(--text-dim)] text-[10px] font-mono">/ 100</span>
                                </div>
                              </div>

                              <div className="flex flex-col items-start sm:items-end gap-1">
                                <span className="text-[var(--text-dim)] text-[10px] uppercase font-bold tracking-wider">Surface Change Category</span>
                                <span className={`px-3 py-1 rounded-full text-xs font-black uppercase border tracking-wider mt-0.5 shadow-sm ${
                                  satelliteChangeData.radar_surface_change_signal.category === 'Stable' ? 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border-emerald-500/30' :
                                  satelliteChangeData.radar_surface_change_signal.category === 'Minor Surface Change' ? 'bg-sky-500/10 text-sky-700 dark:text-sky-400 border-sky-500/30' :
                                  satelliteChangeData.radar_surface_change_signal.category === 'Moderate Surface Change' ? 'bg-orange-500/10 text-orange-700 dark:text-orange-400 border-orange-500/30' :
                                  'bg-rose-500/15 text-rose-700 dark:text-rose-400 border-rose-500/40'
                                }`}>
                                  {satelliteChangeData.radar_surface_change_signal.category}
                                </span>
                              </div>
                            </div>

                            {/* Progress bar */}
                            {(() => {
                              const score = satelliteChangeData.radar_surface_change_signal.radar_surface_change_index;
                              return (
                                <div className="space-y-1">
                                  <div className="w-full bg-[var(--card-bg)] rounded-full h-2.5 overflow-hidden border border-[var(--border-subtle)]">
                                    <div
                                      className={`h-full rounded-full transition-all duration-500 ${
                                        satelliteChangeData.radar_surface_change_signal.category === 'Stable' ? 'bg-emerald-500' :
                                        satelliteChangeData.radar_surface_change_signal.category === 'Minor Surface Change' ? 'bg-sky-500' :
                                        satelliteChangeData.radar_surface_change_signal.category === 'Moderate Surface Change' ? 'bg-orange-500' :
                                        'bg-rose-500'
                                      }`}
                                      style={{ width: `${score}%` }}
                                    />
                                  </div>
                                  <div className="flex justify-between text-[9px] text-[var(--text-dim)] font-mono">
                                    <span>0</span>
                                    <span>25</span>
                                    <span>50</span>
                                    <span>75</span>
                                    <span>100</span>
                                  </div>
                                </div>
                              );
                            })()}

                            {/* Metadata Grid */}
                            <div className="grid grid-cols-2 gap-2 text-[10px] bg-[var(--card-bg)] border border-[var(--border-subtle)] p-3 rounded-lg">
                              <div>
                                <span className="text-[var(--text-dim)] block uppercase font-semibold">Reference Date</span>
                                <span className="text-[var(--text-main)] font-medium text-[9.5px]">
                                  {new Date(satelliteChangeData.metadata.reference_scene.acquisition_time).toLocaleDateString(undefined, {
                                    year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'
                                  })}
                                </span>
                              </div>
                              <div>
                                <span className="text-[var(--text-dim)] block uppercase font-semibold">Comparison Date</span>
                                <span className="text-[var(--text-main)] font-medium text-[9.5px]">
                                  {new Date(satelliteChangeData.metadata.comparison_scene.acquisition_time).toLocaleDateString(undefined, {
                                    year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'
                                  })}
                                </span>
                              </div>
                              <div>
                                <span className="text-[var(--text-dim)] block uppercase font-semibold">Separation</span>
                                <span className="text-[var(--text-main)] font-medium">{satelliteChangeData.metadata.temporal_separation_days} days</span>
                              </div>
                              <div>
                                <span className="text-[var(--text-dim)] block uppercase font-semibold">Orbit State</span>
                                <span className="text-[var(--text-main)] font-medium capitalize">{satelliteChangeData.metadata.orbit_direction}</span>
                              </div>
                            </div>

                            {/* Technical Metrics Breakdown */}
                            <div className="bg-[var(--card-bg)] border border-[var(--border-subtle)] rounded-xl p-3 space-y-2">
                              <span className="text-[10px] text-[var(--text-dim)] uppercase font-black tracking-wide block border-b border-[var(--border-subtle)] pb-1">
                                Change Metrics Breakdown
                              </span>
                              
                              <div className="space-y-1.5 text-[11px]">
                                <div className="flex justify-between items-center">
                                  <span className="text-[var(--text-muted)]">Spatial Extent Score:</span>
                                  <span className="text-[var(--text-main)] font-medium">{satelliteChangeData.radar_surface_change_signal.spatial_extent_score.toFixed(1)} / 100</span>
                                </div>
                                <div className="flex justify-between items-center">
                                  <span className="text-[var(--text-muted)]">Anomaly Magnitude Score:</span>
                                  <span className="text-[var(--text-main)] font-medium">{satelliteChangeData.radar_surface_change_signal.anomaly_magnitude_score.toFixed(1)} / 100</span>
                                </div>
                                <div className="flex justify-between items-center">
                                  <span className="text-[var(--text-muted)]">VV Backscatter Spread:</span>
                                  <span className="text-[var(--text-main)] font-medium">{satelliteChangeData.radar_surface_change_signal.vv_spread_db.toFixed(2)} dB</span>
                                </div>
                                <div className="flex justify-between items-center">
                                  <span className="text-[var(--text-muted)]">VH Backscatter Spread:</span>
                                  <span className="text-[var(--text-main)] font-medium">{satelliteChangeData.radar_surface_change_signal.vh_spread_db.toFixed(2)} dB</span>
                                </div>
                              </div>
                            </div>

                            {/* Scientific Notice */}
                            <div className="bg-[var(--card-bg)] border border-[var(--border-subtle)] p-3 rounded-lg space-y-1">
                              <span className="text-[9px] text-[var(--text-dim)] uppercase font-black tracking-wider block">Scientific Interpretation</span>
                              <p className="text-[10.5px] text-[var(--text-muted)] leading-relaxed font-medium">
                                {satelliteChangeData.radar_surface_change_signal.scientific_notice}
                              </p>
                              <p className="text-[9px] text-emerald-700 dark:text-emerald-400 leading-normal border-t border-[var(--border-subtle)] pt-1.5 mt-1.5">
                                * Notice: This signal detects relative ground/surface change between satellite observations. It is supporting monitoring evidence and does not independently confirm a landslide.
                              </p>
                            </div>
                          </div>
                        )}
                      </div>

                      {/* AI Static Terrain Susceptibility Section */}
                      <div className="border-t border-[var(--border-subtle)] pt-4 mt-4">
                        <div className="flex items-center justify-between mb-3">
                          <h5 className="text-[11px] font-bold text-[var(--text-main)] uppercase tracking-wider flex items-center gap-1.5">
                            <Activity className="h-4 w-4 text-teal-500" />
                            AI Static Terrain Susceptibility (Random Forest)
                          </h5>
                          {isMlSusceptibilityLoading && (
                            <span className="text-[10px] text-[var(--text-muted)] flex items-center gap-1 animate-pulse">
                              <RefreshCw className="h-3 w-3 animate-spin text-teal-500" /> Analyzing terrain susceptibility...
                            </span>
                          )}
                        </div>

                        {isMlSusceptibilityLoading && !mlSusceptibilityData && (
                          <div className="bg-[var(--subcard-bg)] border border-[var(--border-subtle)] rounded-xl p-4 text-center">
                            <RefreshCw className="h-5 w-5 text-teal-500 animate-spin mx-auto mb-1" />
                            <p className="text-[10px] text-[var(--text-muted)] font-medium">Analyzing terrain susceptibility...</p>
                          </div>
                        )}

                        {mlSusceptibilityError && (
                          <div className="bg-rose-500/5 border border-rose-500/10 rounded-xl p-3 text-xs text-rose-500 flex items-center gap-2">
                            <AlertTriangle className="h-4 w-4 text-rose-500 shrink-0" />
                            <div>
                              <p className="font-semibold text-[10px]">Unable to calculate ML susceptibility.</p>
                              <p className="text-[9px] text-[var(--text-muted)]">{mlSusceptibilityError}</p>
                            </div>
                          </div>
                        )}

                        {!isMlSusceptibilityLoading && !mlSusceptibilityData && !mlSusceptibilityError && (
                          <div className="bg-[var(--subcard-bg)] border border-[var(--border-subtle)] rounded-xl p-4 text-center">
                            <p className="text-[10px] text-[var(--text-muted)] font-medium">Analyze a location to calculate AI static terrain susceptibility.</p>
                          </div>
                        )}

                        {mlSusceptibilityData && (
                          <div className="space-y-4">
                            {/* Score Header & Badge Row */}
                            <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3 bg-[var(--card-bg)] p-4 rounded-xl border border-[var(--border-subtle)]">
                              <div>
                                <span className="text-[var(--text-dim)] text-[10px] uppercase font-bold block">Susceptibility Probability</span>
                                <div className="flex items-baseline gap-1 mt-1">
                                  <span className="text-2xl font-black text-teal-700 dark:text-teal-400">
                                    {(mlSusceptibilityData.ml_prediction.probability * 100).toFixed(1)}%
                                  </span>
                                </div>
                              </div>

                              <div className="flex flex-col items-start sm:items-end gap-1">
                                <span className="text-[var(--text-dim)] text-[10px] uppercase font-bold">Risk Level</span>
                                <span className={`px-3 py-1 rounded-full text-xs font-black uppercase border tracking-wider mt-0.5 ${
                                  mlSusceptibilityData.ml_prediction.risk_level === 'Low' ? 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border-emerald-500/30' :
                                  mlSusceptibilityData.ml_prediction.risk_level === 'Moderate' ? 'bg-yellow-500/10 text-yellow-700 dark:text-yellow-400 border-yellow-500/30' :
                                  mlSusceptibilityData.ml_prediction.risk_level === 'High' ? 'bg-orange-500/10 text-orange-700 dark:text-orange-400 border-orange-500/30' :
                                  'bg-rose-500/15 text-rose-700 dark:text-rose-400 border-rose-500/40' // Very High
                                }`}>
                                  {mlSusceptibilityData.ml_prediction.risk_level}
                                </span>
                              </div>
                            </div>

                            {/* Horizontal Progress Bar */}
                            {(() => {
                              const score = mlSusceptibilityData.ml_prediction.probability * 100;
                              return (
                                <div className="space-y-1">
                                  <div className="w-full bg-[var(--card-bg)] rounded-full h-2 overflow-hidden border border-[var(--border-subtle)]">
                                    <div
                                      className={`h-full rounded-full transition-all duration-500 ${
                                        mlSusceptibilityData.ml_prediction.risk_level === 'Low' ? 'bg-emerald-500' :
                                        mlSusceptibilityData.ml_prediction.risk_level === 'Moderate' ? 'bg-yellow-500' :
                                        mlSusceptibilityData.ml_prediction.risk_level === 'High' ? 'bg-orange-500' :
                                        'bg-rose-600'
                                      }`}
                                      style={{ width: `${score}%` }}
                                    />
                                  </div>
                                  <div className="flex justify-between text-[9px] text-[var(--text-dim)] font-mono">
                                    <span>0%</span>
                                    <span>50% (Threshold)</span>
                                    <span>100%</span>
                                  </div>
                                </div>
                              );
                            })()}

                            {/* Detail Grid */}
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
                              {/* Classification details */}
                              <div className="bg-[var(--card-bg)] border border-[var(--border-subtle)] rounded-xl p-3 flex flex-col justify-between space-y-2 col-span-1 md:col-span-2">
                                <div className="flex justify-between items-center text-[11px] text-[var(--text-muted)]">
                                  <span>Status:</span>
                                  <span className={`font-black ${mlSusceptibilityData.ml_prediction.is_susceptible ? 'text-rose-700 dark:text-rose-400' : 'text-emerald-700 dark:text-emerald-400'}`}>
                                    {mlSusceptibilityData.ml_prediction.is_susceptible ? 'SUSCEPTIBLE' : 'NOT SUSCEPTIBLE'}
                                  </span>
                                </div>
                              </div>
                              
                              {/* Terrain Features Used Card */}
                              <div className="bg-[var(--card-bg)] border border-[var(--border-subtle)] rounded-xl p-3 flex flex-col justify-between space-y-2 col-span-1 md:col-span-2">
                                <div className="border-b border-[var(--border-subtle)] pb-1">
                                  <span className="font-bold text-[var(--text-main)]">Terrain Features Used</span>
                                </div>
                                <div className="space-y-1 text-[11px] text-[var(--text-muted)]">
                                  <div className="flex justify-between">
                                    <span>Elevation:</span>
                                    <span className="text-[var(--text-main)] font-medium">{mlSusceptibilityData.terrain.elevation} m</span>
                                  </div>
                                  <div className="flex justify-between">
                                    <span>Slope:</span>
                                    <span className="text-[var(--text-main)] font-medium">{mlSusceptibilityData.terrain.slope.toFixed(1)}°</span>
                                  </div>
                                  <div className="flex justify-between">
                                    <span>Aspect:</span>
                                    <span className="text-[var(--text-main)] font-medium">
                                      {mlSusceptibilityData.terrain.aspect >= 0 ? `${mlSusceptibilityData.terrain.aspect}°` : 'Flat (-1)'}
                                    </span>
                                  </div>
                                </div>
                              </div>
                            </div>

                            {/* Model Version and Scientific Disclaimer */}
                            <div className="flex justify-between items-center text-[9px] text-[var(--text-dim)] font-mono">
                              <span>Model: Random Forest ({mlSusceptibilityData.ml_prediction.model_version})</span>
                              <span>Threshold: {mlSusceptibilityData.ml_prediction.threshold_used}</span>
                            </div>

                            <div className="bg-[var(--subcard-bg)] border border-[var(--border-subtle)] p-2.5 rounded-lg">
                              <p className="text-[9px] text-teal-700 dark:text-teal-400 leading-normal">
                                * Disclaimer: {mlSusceptibilityData.disclaimer}
                              </p>
                            </div>
                          </div>
                        )}
                      </div>

                    </div>

                    {/* Historical Landslide Hazard Susceptibility Section */}
                    <div className="border-t border-[var(--border-subtle)] pt-4 mt-4">
                      <div className="flex items-center justify-between mb-3">
                        <h5 className="text-[11px] font-bold text-[var(--text-main)] uppercase tracking-wider flex items-center gap-1.5">
                          <AlertTriangle className="h-4 w-4 text-rose-500" />
                          Historical Landslide Hazard Susceptibility
                        </h5>
                        {isSusceptibilityLoading && (
                          <span className="text-[10px] text-[var(--text-muted)] flex items-center gap-1 animate-pulse">
                            <RefreshCw className="h-3 w-3 animate-spin text-rose-500" /> Calculating hazard susceptibility...
                          </span>
                        )}
                      </div>

                      {isSusceptibilityLoading && !susceptibilityData && (
                        <div className="bg-[var(--subcard-bg)] border border-[var(--border-subtle)] rounded-xl p-4 text-center">
                          <RefreshCw className="h-5 w-5 text-rose-500 animate-spin mx-auto mb-1" />
                          <p className="text-[10px] text-[var(--text-muted)] font-medium">Calculating hazard susceptibility...</p>
                        </div>
                      )}

                      {susceptibilityError && (
                        <div className="bg-rose-500/5 border border-rose-500/10 rounded-xl p-3 text-xs text-rose-500 flex items-center gap-2">
                          <AlertTriangle className="h-4 w-4 text-rose-500 shrink-0" />
                          <div>
                            <p className="font-semibold text-[10px]">Unable to calculate hazard susceptibility.</p>
                            <p className="text-[9px] text-[var(--text-muted)]">{susceptibilityError}</p>
                          </div>
                        </div>
                      )}

                      {!isSusceptibilityLoading && !susceptibilityData && !susceptibilityError && (
                        <div className="bg-[var(--subcard-bg)] border border-[var(--border-subtle)] rounded-xl p-4 text-center">
                          <p className="text-[10px] text-[var(--text-muted)] font-medium">Analyze a location to calculate landslide hazard susceptibility.</p>
                        </div>
                      )}

                      {susceptibilityData && (
                        <div className="space-y-4">
                          {/* Score Header & Badge Row */}
                          <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3 bg-[var(--card-bg)] p-4 rounded-xl border border-[var(--border-subtle)]">
                            <div>
                              <span className="text-[var(--text-dim)] text-[10px] uppercase font-bold block">Hazard Score</span>
                              <div className="flex items-baseline gap-1 mt-1">
                                <span className="text-2xl font-black text-[var(--text-main)]">
                                  {Math.min(100, Math.max(0, susceptibilityData.susceptibility_score || 0)).toFixed(1)}
                                </span>
                                <span className="text-[var(--text-dim)] text-xs font-semibold">/ 100</span>
                              </div>
                            </div>

                            <div className="flex flex-col items-start sm:items-end gap-1">
                              <span className="text-[var(--text-dim)] text-[10px] uppercase font-bold">Hazard Level</span>
                              <span className={`px-3 py-1 rounded-full text-xs font-black uppercase border tracking-wider mt-0.5 ${
                                susceptibilityData.hazard_level === 'Low' ? 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border-emerald-500/30' :
                                susceptibilityData.hazard_level === 'Moderate' ? 'bg-yellow-500/10 text-yellow-700 dark:text-yellow-400 border-yellow-500/30' :
                                susceptibilityData.hazard_level === 'High' ? 'bg-orange-500/10 text-orange-700 dark:text-orange-400 border-orange-500/30' :
                                'bg-rose-500/15 text-rose-700 dark:text-rose-400 border-rose-500/40' // Very High
                              }`}>
                                {susceptibilityData.hazard_level}
                              </span>
                            </div>
                          </div>

                          {/* Horizontal Progress Bar */}
                          {(() => {
                            const score = Math.min(100, Math.max(0, susceptibilityData.susceptibility_score || 0));
                            return (
                              <div className="space-y-1">
                                <div className="w-full bg-[var(--card-bg)] rounded-full h-2 overflow-hidden border border-[var(--border-subtle)]">
                                  <div
                                    className={`h-full rounded-full transition-all duration-500 ${
                                      susceptibilityData.hazard_level === 'Low' ? 'bg-emerald-500' :
                                      susceptibilityData.hazard_level === 'Moderate' ? 'bg-yellow-500' :
                                      susceptibilityData.hazard_level === 'High' ? 'bg-orange-500' :
                                      'bg-rose-600'
                                    }`}
                                    style={{ width: `${score}%` }}
                                  />
                                </div>
                                <div className="flex justify-between text-[9px] text-[var(--text-dim)] font-mono">
                                  <span>0</span>
                                  <span>50</span>
                                  <span>100</span>
                                </div>
                              </div>
                            );
                          })()}

                          {/* Component Breakdown Cards */}
                          <div className="space-y-2">
                            <span className="text-[var(--text-dim)] text-[10px] uppercase font-bold block">Heuristic Component Breakdown</span>
                            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
                              
                              {/* Historical Component */}
                              <div className="bg-[var(--card-bg)] border border-[var(--border-subtle)] rounded-xl p-3 flex flex-col justify-between space-y-2">
                                <div className="flex justify-between items-start border-b border-[var(--border-subtle)] pb-1">
                                  <span className="font-bold text-[var(--text-main)]">Historical Evidence</span>
                                  <span className="font-semibold text-amber-700 dark:text-amber-400 font-mono">
                                    {susceptibilityData.historical_component.score.toFixed(1)} / {susceptibilityData.historical_component.max_score.toFixed(0)}
                                  </span>
                                </div>
                                <div className="space-y-1 text-[11px] text-[var(--text-muted)]">
                                  <div className="flex justify-between">
                                    <span>Observations:</span>
                                    <span className="text-[var(--text-main)] font-medium">{susceptibilityData.historical_component.total_observations}</span>
                                  </div>
                                  <div className="flex justify-between">
                                    <span>Nearest:</span>
                                    <span className="text-[var(--text-main)] font-medium">
                                      {susceptibilityData.historical_component.nearest_observation_km !== null
                                        ? `${susceptibilityData.historical_component.nearest_observation_km.toFixed(2)} km`
                                        : 'None'}
                                    </span>
                                  </div>
                                </div>
                              </div>

                              {/* Terrain Component */}
                              <div className="bg-[var(--card-bg)] border border-[var(--border-subtle)] rounded-xl p-3 flex flex-col justify-between space-y-2">
                                <div className="flex justify-between items-start border-b border-[var(--border-subtle)] pb-1">
                                  <span className="font-bold text-[var(--text-main)]">Terrain Predisposition</span>
                                  {susceptibilityData.terrain_component.available ? (
                                    <span className="font-semibold text-teal-700 dark:text-teal-400 font-mono">
                                      {susceptibilityData.terrain_component.score.toFixed(1)} / {susceptibilityData.terrain_component.max_score.toFixed(0)}
                                    </span>
                                  ) : (
                                    <span className="text-[var(--text-dim)] font-bold text-[10px]">Awaiting DEM</span>
                                  )}
                                </div>
                                <div className="space-y-1 text-[11px]">
                                  {susceptibilityData.terrain_component.available ? (
                                    <div className="text-[var(--text-muted)] space-y-1">
                                      <div className="flex justify-between">
                                        <span>Mean Slope:</span>
                                        <span className="text-[var(--text-main)] font-medium">{susceptibilityData.terrain_component.mean_slope_degrees.toFixed(1)}°</span>
                                      </div>
                                      <div className="flex justify-between">
                                        <span>Slope Level:</span>
                                        <span className="text-[var(--text-main)] font-medium">{susceptibilityData.terrain_component.level}</span>
                                      </div>
                                    </div>
                                  ) : (
                                    <div className="text-[var(--text-dim)] italic text-center py-1">
                                      Awaiting terrain analysis
                                    </div>
                                  )}
                                </div>
                              </div>

                              {/* Weather Component */}
                              <div className="bg-[var(--card-bg)] border border-[var(--border-subtle)] rounded-xl p-3 flex flex-col justify-between space-y-2">
                                <div className="flex justify-between items-start border-b border-[var(--border-subtle)] pb-1">
                                  <span className="font-bold text-[var(--text-main)]">Rainfall Trigger</span>
                                  {susceptibilityData.rainfall_component.available ? (
                                    <span className="font-semibold text-sky-700 dark:text-sky-400 font-mono">
                                      {susceptibilityData.rainfall_component.score.toFixed(1)} / {susceptibilityData.rainfall_component.max_score.toFixed(0)}
                                    </span>
                                  ) : (
                                    <span className="text-[var(--text-dim)] font-bold text-[10px]">Unavailable</span>
                                  )}
                                </div>
                                <div className="space-y-1 text-[11px] text-[var(--text-muted)]">
                                  {susceptibilityData.rainfall_component.available ? (
                                    <div className="space-y-1">
                                      <div className="flex justify-between">
                                        <span>Mode:</span>
                                        <span className="text-[var(--text-main)] font-mono text-[9px] uppercase">
                                          {susceptibilityData.rainfall_component.scoring_mode === 'compatibility' ? 'Legacy 24h' :
                                           susceptibilityData.rainfall_component.scoring_mode === 'multi_timescale' ? 'Multi-Timescale' :
                                           'Multi-Timescale (Partial)'}
                                        </span>
                                      </div>
                                      
                                      {susceptibilityData.rainfall_component.scoring_mode === 'compatibility' ? (
                                        <>
                                          <div className="flex justify-between">
                                            <span>24h Rainfall:</span>
                                            <span className="text-[var(--text-main)] font-medium">{susceptibilityData.rainfall_component.precipitation_mm_24h?.toFixed(1) || '0.0'} mm</span>
                                          </div>
                                          <div className="flex justify-between">
                                            <span>Level:</span>
                                            <span className="text-[var(--text-main)] font-medium">{susceptibilityData.rainfall_component.level}</span>
                                          </div>
                                        </>
                                      ) : (
                                        <>
                                          {susceptibilityData.rainfall_component.daily_score !== null && (
                                            <div className="flex justify-between text-[10px]">
                                              <span>24h Intensity:</span>
                                              <span className="text-[var(--text-main)] font-medium">
                                                {susceptibilityData.rainfall_component.precipitation_mm_24h?.toFixed(1) || '0.0'} mm ({susceptibilityData.rainfall_component.daily_score}/10)
                                              </span>
                                            </div>
                                          )}
                                          {susceptibilityData.rainfall_component.three_day_score !== null && (
                                            <div className="flex justify-between text-[10px]">
                                              <span>3-Day Saturation:</span>
                                              <span className="text-[var(--text-main)] font-medium">
                                                {susceptibilityData.rainfall_component.three_day_cumulative_mm?.toFixed(1) || '0.0'} mm ({susceptibilityData.rainfall_component.three_day_score}/10)
                                              </span>
                                            </div>
                                          )}
                                          {susceptibilityData.rainfall_component.seven_day_score !== null && (
                                            <div className="flex justify-between text-[10px]">
                                              <span>7-Day Saturation:</span>
                                              <span className="text-[var(--text-main)] font-medium">
                                                {susceptibilityData.rainfall_component.seven_day_cumulative_mm?.toFixed(1) || '0.0'} mm ({susceptibilityData.rainfall_component.seven_day_score}/10)
                                              </span>
                                            </div>
                                          )}
                                          <div className="flex justify-between border-t border-[var(--border-subtle)] pt-1 mt-1 text-[10px]">
                                            <span>Composite Level:</span>
                                            <span className="text-[var(--text-main)] font-bold">{susceptibilityData.rainfall_component.level}</span>
                                          </div>
                                        </>
                                      )}
                                    </div>
                                  ) : (
                                    <div className="text-[var(--text-dim)] italic text-center py-1">
                                      Weather data unavailable
                                    </div>
                                  )}
                                </div>
                              </div>

                            </div>
                          </div>

                          {/* Narrative Explanation Block */}
                          <div className="bg-[var(--card-bg)] border border-[var(--border-subtle)] p-3 rounded-xl space-y-1">
                            <span className="text-[var(--text-dim)] text-[10px] uppercase font-bold block">Why this score?</span>
                            <p className="text-[var(--text-muted)] text-[11px] leading-relaxed">
                              {susceptibilityData.explanation}
                            </p>
                          </div>
                        </div>
                      )}
                    </div>

                    {/* Historical Landslide Context Section */}
                    <div className="border-t border-[var(--border-subtle)] pt-4 mt-4">
                      <div className="flex items-center justify-between mb-3">
                        <h5 className="text-[11px] font-bold text-[var(--text-main)] uppercase tracking-wider flex items-center gap-1.5">
                          <Activity className="h-4 w-4 text-emerald-500" />
                          Historical Landslide Context
                        </h5>
                        {isHistoricalLoading && (
                          <span className="text-[10px] text-[var(--text-muted)] flex items-center gap-1 animate-pulse">
                            <RefreshCw className="h-3 w-3 animate-spin text-emerald-500" /> Querying databases...
                          </span>
                        )}
                      </div>

                      {isHistoricalLoading && !historicalData && (
                        <div className="bg-[var(--subcard-bg)] border border-[var(--border-subtle)] rounded-xl p-4 text-center">
                          <RefreshCw className="h-5 w-5 text-emerald-500 animate-spin mx-auto mb-1" />
                          <p className="text-[10px] text-[var(--text-muted)] font-medium">Querying nearby historical databases...</p>
                        </div>
                      )}

                      {historicalError && (
                        <div className="bg-rose-500/5 border border-rose-500/10 rounded-xl p-3 text-xs text-rose-500 flex items-center gap-2">
                          <AlertTriangle className="h-4 w-4 text-rose-500 shrink-0" />
                          <div>
                            <p className="font-semibold text-[10px]">Historical Data Query Failed</p>
                            <p className="text-[9px] text-[var(--text-muted)]">{historicalError}</p>
                          </div>
                        </div>
                      )}

                      {!isHistoricalLoading && historicalData && historicalData.combined_summary.total_historical_observations === 0 && (
                        <div className="bg-[var(--subcard-bg)] border border-[var(--border-subtle)] rounded-xl p-4 text-center">
                          <AlertTriangle className="h-5 w-5 text-[var(--text-dim)] mx-auto mb-1" />
                          <p className="text-[10px] text-[var(--text-muted)] font-medium">No historical landslide observations found within the selected search radius.</p>
                        </div>
                      )}

                      {!isHistoricalLoading && historicalData && historicalData.combined_summary.total_historical_observations > 0 && (
                        <div className="space-y-4">
                          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-xs">
                            {/* Total Observations */}
                            <div className="bg-[var(--subcard-bg)] border border-[var(--border-subtle)] rounded-xl p-3 flex flex-col justify-between">
                              <span className="text-[var(--text-dim)] text-[10px] uppercase font-semibold">Total Observations</span>
                              <p className="text-base font-bold text-[var(--text-main)] mt-1">
                                {historicalData.combined_summary.total_historical_observations}
                              </p>
                            </div>

                            {/* Nearest Observation */}
                            <div className="bg-[var(--subcard-bg)] border border-[var(--border-subtle)] rounded-xl p-3 flex flex-col justify-between">
                              <span className="text-[var(--text-dim)] text-[10px] uppercase font-semibold">Nearest Observation</span>
                              <p className="text-base font-bold text-[var(--text-main)] mt-1">
                                {historicalData.combined_summary.nearest_historical_observation_km !== null
                                  ? `${historicalData.combined_summary.nearest_historical_observation_km.toFixed(2)} km`
                                  : 'N/A'}
                              </p>
                            </div>

                            {/* GSI Count */}
                            <div className="bg-[var(--subcard-bg)] border border-[var(--border-subtle)] rounded-xl p-3 flex flex-col justify-between">
                              <span className="text-[var(--text-dim)] text-[10px] uppercase font-semibold">GSI Incidents</span>
                              <p className="text-base font-bold text-amber-700 dark:text-amber-400 mt-1">
                                {historicalData.gsi_summary.total_nearby_incidents}
                              </p>
                            </div>

                            {/* NASA Count */}
                            <div className="bg-[var(--subcard-bg)] border border-[var(--border-subtle)] rounded-xl p-3 flex flex-col justify-between">
                              <span className="text-[var(--text-dim)] text-[10px] uppercase font-semibold">NASA Events</span>
                              <p className="text-base font-bold text-rose-700 dark:text-rose-400 mt-1">
                                {historicalData.nasa_summary.total_nearby_events}
                              </p>
                            </div>
                          </div>

                          {/* Recorded Impact and Temporal Context */}
                          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs border-t border-[var(--border-subtle)] pt-3">
                            <div className="space-y-2">
                              <span className="text-[var(--text-dim)] text-[10px] uppercase font-semibold block">Recorded Human Impact (NASA)</span>
                              <div className="grid grid-cols-2 gap-3">
                                <div className="bg-[var(--card-bg)] border border-[var(--border-subtle)] p-2.5 rounded-lg flex flex-col justify-between">
                                  <span className="text-[var(--text-dim)] text-[9px] uppercase font-medium">Fatalities</span>
                                  <span className={`text-sm font-bold mt-1 ${historicalData.nasa_summary.total_recorded_fatalities > 0 ? "text-rose-700 dark:text-rose-400" : "text-[var(--text-main)]"}`}>
                                    {historicalData.nasa_summary.total_recorded_fatalities}
                                  </span>
                                </div>
                                <div className="bg-[var(--card-bg)] border border-[var(--border-subtle)] p-2.5 rounded-lg flex flex-col justify-between">
                                  <span className="text-[var(--text-dim)] text-[9px] uppercase font-medium">Injuries</span>
                                  <span className="text-sm font-bold text-[var(--text-main)] mt-1">
                                    {historicalData.nasa_summary.total_recorded_injuries}
                                  </span>
                                </div>
                              </div>
                            </div>

                            <div className="space-y-2">
                              <span className="text-[var(--text-dim)] text-[10px] uppercase font-semibold block">Temporal Context (NASA)</span>
                              <div className="bg-[var(--card-bg)] border border-[var(--border-subtle)] p-2.5 rounded-lg text-xs space-y-1.5 h-[62px] flex flex-col justify-center">
                                {historicalData.nasa_summary.earliest_event_date ? (
                                  <>
                                    <div className="flex justify-between">
                                      <span className="text-[var(--text-dim)] text-[9px]">Earliest:</span>
                                      <span className="font-semibold text-[var(--text-muted)] font-mono text-[10px]">{historicalData.nasa_summary.earliest_event_date}</span>
                                    </div>
                                    <div className="flex justify-between">
                                      <span className="text-[var(--text-dim)] text-[9px]">Latest:</span>
                                      <span className="font-semibold text-[var(--text-muted)] font-mono text-[10px]">{historicalData.nasa_summary.latest_event_date}</span>
                                    </div>
                                  </>
                                ) : (
                                  <div className="text-[var(--text-dim)] text-[10px] italic">No dates recorded for nearby events</div>
                                )}
                              </div>
                            </div>
                          </div>

                          {/* Trigger Distributions */}
                          {(Object.keys(historicalData.gsi_summary.trigger_distribution).length > 0 ||
                            Object.keys(historicalData.nasa_summary.trigger_distribution).length > 0) && (
                            <div className="border-t border-[var(--border-subtle)] pt-3 space-y-2">
                              <span className="text-[var(--text-dim)] text-[10px] uppercase font-semibold block">Recorded Triggers</span>
                              <div className="flex flex-wrap gap-2">
                                {/* GSI Triggers */}
                                {Object.entries(historicalData.gsi_summary.trigger_distribution).map(([trigger, count]) => (
                                  <div key={`gsi-trig-${trigger}`} className="flex items-center gap-1.5 bg-[var(--card-bg)] border border-[var(--border-subtle)] px-2 py-1 rounded-lg text-[10px]">
                                    <span className="text-[var(--text-muted)] font-medium">{trigger}:</span>
                                    <span className="font-bold text-amber-700 dark:text-amber-400 font-mono">{count} <span className="text-[8px] text-[var(--text-dim)] font-normal">GSI</span></span>
                                  </div>
                                ))}
                                {/* NASA Triggers */}
                                {Object.entries(historicalData.nasa_summary.trigger_distribution).map(([trigger, count]) => (
                                  <div key={`nasa-trig-${trigger}`} className="flex items-center gap-1.5 bg-[var(--card-bg)] border border-[var(--border-subtle)] px-2 py-1 rounded-lg text-[10px]">
                                    <span className="text-[var(--text-muted)] font-medium">{trigger.replace(/_/g, ' ')}:</span>
                                    <span className="font-bold text-rose-700 dark:text-rose-400 font-mono">{count} <span className="text-[8px] text-[var(--text-dim)] font-normal">NASA</span></span>
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Field Intelligence & Ground Observations Section */}
                  <div id="field-intelligence-section">
                    <FieldIntelligenceCard
                      reports={fieldReports}
                      summary={fieldIntelligenceSummary}
                      isLoading={isFieldReportsLoading}
                      error={fieldReportsError}
                      onOpenReportModal={() => setIsReportModalOpen(true)}
                      selectedLocation={selectedLocation}
                    />
                  </div>

                  {/* Road Disruption Intelligence Section */}
                  <div id="road-section">
                    <RoadDisruptionCard
                      disruptionData={disruptionData}
                      isLoading={isDisruptionLoading}
                      error={disruptionError}
                    />
                  </div>

                  {/* Integrated Operational Situation Assessment Section */}
                  <div id="situation-section">
                    <OperationalSituationCard
                      assessmentData={situationData}
                      isLoading={isSituationLoading}
                      error={situationError}
                      onRetry={() => selectedLocation && fetchSituationAssessment(selectedLocation.lat, selectedLocation.lng, aoi?.radius_km || 5.0)}
                      selectedLocation={selectedLocation}
                    />
                  </div>

                  {/* Operational Incident Command Dashboard Section */}
                  <div id="incident-command-section">
                    <OperationalIncidentCommand
                      key={`incident-cmd-${incidentRefreshKey}`}
                      onLocateIncident={(lat, lng) => setSelectedLocation({ lat, lng })}
                      selectedLocation={selectedLocation}
                    />
                  </div>
          </div>
        )}

        {/* Satellite Data Search Section */}
        <section id="satellite-section" className="bg-[var(--panel-bg)] backdrop-blur-md border border-[var(--border-subtle)] rounded-xl p-5 shadow-md space-y-5">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between border-b border-[var(--border-subtle)] pb-3.5 gap-2">
            <div className="flex items-center gap-2.5">
              <div className="p-1.5 bg-emerald-500/10 text-emerald-500 rounded-lg border border-emerald-500/20">
                <Layers className="h-5 w-5" />
              </div>
              <div>
                <h2 className="text-sm sm:text-base font-bold text-[var(--text-main)]">Satellite Data Discovery</h2>
                <p className="text-[11px] text-[var(--text-muted)]">Query Copernicus catalogue metadata for the target Area of Interest</p>
              </div>
            </div>
            <span className="text-xs px-2.5 py-0.5 rounded-full bg-[var(--card-bg)] text-[var(--text-muted)] font-medium border border-[var(--border-subtle)] self-start sm:self-auto">
              Copernicus STAC API
            </span>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Config panel */}
            <div className="space-y-3.5 bg-[var(--card-bg)] p-4 rounded-xl border border-[var(--border-subtle)]">
              <h3 className="text-xs font-bold text-[var(--text-main)] uppercase tracking-wider">Search Configuration</h3>
              
              <div className="space-y-2 text-xs">
                <div className="flex justify-between py-1.5 border-b border-[var(--border-subtle)]">
                  <span className="text-[var(--text-dim)]">Source Provider</span>
                  <span className="text-[var(--text-main)] font-medium">Copernicus Data Space</span>
                </div>
                <div className="flex justify-between py-1.5 border-b border-[var(--border-subtle)]">
                  <span className="text-[var(--text-dim)]">Satellite Mission</span>
                  <span className="text-[var(--text-main)] font-medium">Sentinel-1</span>
                </div>
                <div className="flex justify-between py-1.5 border-b border-[var(--border-subtle)]">
                  <span className="text-[var(--text-dim)]">Collection ID</span>
                  <span className="text-[var(--text-muted)] font-mono text-[10px]">sentinel-1-grd</span>
                </div>
                <div className="flex justify-between py-1.5 border-b border-[var(--border-subtle)]">
                  <span className="text-[var(--text-dim)]">AOI Size</span>
                  <span className="text-[var(--text-main)] font-medium">{aoi ? `${aoi.radius_km} km Radius` : 'None'}</span>
                </div>
              </div>

              {/* Date pickers to make date range configurable */}
              <div className="grid grid-cols-2 gap-2.5 pt-1">
                <div>
                  <label className="text-[9px] text-[var(--text-dim)] uppercase tracking-wider block mb-1">Start Date</label>
                  <input
                    type="date"
                    value={startDate}
                    onChange={(e) => setStartDate(e.target.value)}
                    className="w-full bg-[var(--subcard-bg)] border border-[var(--border-subtle)] text-xs text-[var(--text-main)] rounded-lg p-1.5 focus:border-emerald-500 outline-none"
                  />
                </div>
                <div>
                  <label className="text-[9px] text-[var(--text-dim)] uppercase tracking-wider block mb-1">End Date</label>
                  <input
                    type="date"
                    value={endDate}
                    onChange={(e) => setEndDate(e.target.value)}
                    className="w-full bg-[var(--subcard-bg)] border border-[var(--border-subtle)] text-xs text-[var(--text-main)] rounded-lg p-1.5 focus:border-emerald-500 outline-none"
                  />
                </div>
              </div>

              <button
                onClick={handleSatelliteSearch}
                disabled={!aoi || isSearchingSatellite}
                className="w-full mt-2 px-3.5 py-2 bg-emerald-600 hover:bg-emerald-500 disabled:bg-slate-700 text-white disabled:text-slate-400 rounded-lg font-bold border border-emerald-500/30 disabled:border-transparent shadow-xs transition flex items-center justify-center gap-2 cursor-pointer disabled:cursor-not-allowed text-xs"
              >
                {isSearchingSatellite ? <RefreshCw className="h-3.5 w-3.5 animate-spin text-white" /> : <Layers className="h-3.5 w-3.5" />}
                <span>Search Satellite Data</span>
              </button>
              
              {!aoi && (
                <p className="text-[10px] text-[var(--text-dim)] text-center leading-normal">
                  * Select a coordinate on the map and run coordinate analysis to enable search.
                </p>
              )}
            </div>

            {/* Results Table / List (2/3 width) */}
            <div className="lg:col-span-2 space-y-3">
              <h3 className="text-xs font-bold text-[var(--text-main)] uppercase tracking-wider">Discovered Scenes</h3>

              {isSearchingSatellite && (
                <div className="border border-[var(--border-subtle)] bg-[var(--card-bg)] rounded-xl p-6 flex flex-col items-center justify-center text-center space-y-2.5 h-[230px]">
                  <RefreshCw className="h-7 w-7 text-emerald-500 animate-spin" />
                  <p className="text-xs text-[var(--text-muted)]">Querying Copernicus catalogue index for overlapping Sentinel-1 data...</p>
                </div>
              )}

              {!isSearchingSatellite && satelliteError && (
                <div className="bg-rose-500/10 border border-rose-500/25 rounded-xl p-5 text-xs text-rose-500 space-y-1 h-[230px] flex flex-col justify-center items-center text-center">
                  <AlertTriangle className="h-7 w-7 text-rose-500 mb-1" />
                  <p className="font-bold">Satellite Catalogue Query Failed</p>
                  <p className="text-[var(--text-muted)] max-w-md">{satelliteError}</p>
                </div>
              )}

              {!isSearchingSatellite && !satelliteError && satelliteScenes.length === 0 && (
                <div className="border border-[var(--border-subtle)] bg-[var(--card-bg)] rounded-xl p-6 flex flex-col items-center justify-center text-center space-y-2 h-[230px]">
                  <Layers className="h-7 w-7 text-[var(--text-dim)] mb-1" />
                  <p className="text-[var(--text-muted)] text-xs">No satellite scenes discovered.</p>
                  <p className="text-[10px] text-[var(--text-dim)] max-w-sm">
                    {aoi 
                      ? 'Configure a broader date range or click "Search Satellite Data" to begin query.' 
                      : 'Select a location on the map and run coordinate analysis first.'}
                  </p>
                </div>
              )}

              {!isSearchingSatellite && !satelliteError && satelliteScenes.length > 0 && (
                <div className="border border-[var(--border-subtle)] rounded-xl overflow-hidden bg-[var(--card-bg)] shadow-inner max-h-[230px] overflow-y-auto">
                  <table className="w-full text-left border-collapse text-xs">
                    <thead>
                      <tr className="bg-[var(--subcard-bg)] border-b border-[var(--border-subtle)] text-[var(--text-dim)] uppercase tracking-wider text-[10px] font-semibold">
                        <th className="p-2.5">Scene ID</th>
                        <th className="p-2.5">Acquisition Date</th>
                        <th className="p-2.5">Orbit</th>
                        <th className="p-2.5">Format</th>
                        <th className="p-2.5 text-right">Actions</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[var(--border-subtle)]">
                      {satelliteScenes.map((scene) => (
                        <tr key={scene.id} className="hover:bg-[var(--subcard-bg)] transition">
                          <td className="p-2.5 font-mono text-[10px] text-emerald-500 select-all truncate max-w-[180px]" title={scene.id}>
                            {scene.id}
                          </td>
                          <td className="p-2.5 text-[var(--text-main)] font-medium">
                            {new Date(scene.datetime).toLocaleString()}
                          </td>
                          <td className="p-2.5">
                            <span className={`px-2 py-0.5 rounded-full text-[10px] font-medium ${
                              scene.orbit_direction.toLowerCase() === 'ascending' 
                                ? 'bg-emerald-500/10 text-emerald-500 border border-emerald-500/20' 
                                : 'bg-blue-500/10 text-blue-500 border border-blue-500/20'
                            }`}>
                              {scene.orbit_direction}
                            </span>
                          </td>
                          <td className="p-2.5 text-[var(--text-dim)] font-mono text-[10px]">{scene.product_type}</td>
                          <td className="p-2.5 text-right">
                            <button
                              onClick={() => handleInspectScene(scene.id)}
                              className="px-2 py-0.5 bg-[var(--subcard-bg)] hover:bg-[var(--card-bg)] text-[var(--text-main)] border border-[var(--border-subtle)] rounded text-[10px] font-semibold transition cursor-pointer"
                            >
                              Inspect Scene
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>
          </section>
            </>
          ) : (
            /* CITIZEN / PUBLIC ADVISORY VIEW */
            <div className="space-y-4">
              
              {/* Public Advisory Header Banner */}
              <div className="bg-[var(--card-bg)] border border-[var(--border-subtle)] rounded-xl p-4 sm:p-5 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 shadow-sm">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] font-black tracking-wider uppercase px-2 py-0.5 rounded bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">
                      Public Citizen Advisory
                    </span>
                    <span className="text-[11px] text-[var(--text-dim)]">North East Regional Safety Portal</span>
                  </div>
                  <h2 className="text-lg sm:text-xl font-bold text-[var(--text-main)]">
                    Community Landslide Awareness & Highway Safety
                  </h2>
                  <p className="text-xs text-[var(--text-muted)] max-w-2xl leading-relaxed">
                    Search your location, town, or highway corridor on the map below to view real-time landslide risk advisories, road conditions, and rainfall alerts. You can also report fallen rocks or slope cracks directly to response authorities.
                  </p>
                </div>

                <div className="flex flex-wrap items-center gap-2 shrink-0">
                  <button
                    onClick={() => setIsReportModalOpen(true)}
                    className="px-3.5 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg font-bold text-xs flex items-center gap-2 shadow-sm transition cursor-pointer"
                  >
                    <ShieldAlert className="h-4 w-4" />
                    <span>Report Hazard / Fallen Rocks</span>
                  </button>
                  <a
                    href="tel:1070"
                    className="px-3 py-2 bg-[var(--subcard-bg)] hover:bg-[var(--card-bg)] border border-[var(--border-subtle)] rounded-lg text-xs font-bold text-[var(--text-main)] flex items-center gap-1.5 transition"
                  >
                    <span>📞 1070 Toll-Free</span>
                  </a>
                </div>
              </div>

              {/* Citizen Map View (Full Width) */}
              <div className="bg-[var(--card-bg)] border border-[var(--border-subtle)] rounded-xl p-3 sm:p-4 shadow-sm space-y-3">
                <div className="flex items-center justify-between text-xs">
                  <div className="flex items-center gap-2">
                    <MapPin className="h-4 w-4 text-emerald-500" />
                    <span className="font-bold text-[var(--text-main)] text-sm">Interactive North East Hazard Map</span>
                  </div>
                  <span className="text-[11px] text-[var(--text-dim)] hidden sm:inline">
                    Use the Search Bar on the map or click any point to inspect
                  </span>
                </div>

                <div className="h-[480px] sm:h-[540px] w-full rounded-lg overflow-hidden border border-[var(--border-subtle)]">
                  <InteractiveMap
                    selectedLocation={selectedLocation}
                    onLocationSelect={handleLocationSelect}
                    aoi={aoi}
                    historicalData={historicalData}
                    terrainData={terrainData}
                    weatherData={weatherData}
                    fieldReports={fieldReports}
                    roadData={roadData}
                    isRoadLoading={isRoadLoading}
                    roadError={roadError}
                    showRoads={showRoads}
                    setShowRoads={setShowRoads}
                  />
                </div>
              </div>

              {/* Citizen Advisory Details Card */}
              <ErrorBoundary onReset={() => handleLocationSelect(null)}>
                <CitizenAdvisoryCard
                  selectedLocation={selectedLocation}
                  earlyWarningData={earlyWarningData}
                  compositeRiskData={compositeRiskData}
                  weatherData={weatherData}
                  terrainData={terrainData}
                  historicalData={historicalData}
                  roadData={roadData}
                  onAnalyze={handleAnalyzeLocation}
                  isAnalyzing={isAnalyzing}
                  onOpenReportModal={() => setIsReportModalOpen(true)}
                  onOpenHotspot={(spot) => {
                    if (spot && spot.lat != null && spot.lng != null) {
                      handleLocationSelect({ lat: spot.lat, lng: spot.lng });
                    } else {
                      handleLocationSelect(null);
                    }
                  }}
                  onOpenSmsModal={() => setIsSmsModalOpen(true)}
                />
              </ErrorBoundary>

            </div>
          )}
        </main>

        {/* Command Center Footer */}
        <footer className="border-t border-[var(--border-subtle)] bg-[var(--card-bg)] py-3 text-[11px] text-[var(--text-dim)] mt-auto">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col md:flex-row justify-between items-center gap-2">
            <p className="font-medium">© {new Date().getFullYear()} NER Landslide Monitoring & Early Warning System | Operational Command Center</p>
            <div className="flex flex-wrap items-center gap-1.5 text-[10px] text-[var(--text-muted)]">
              <span>Data sources:</span>
              <span className="text-[var(--text-main)] font-semibold">IMD</span>
              <span>•</span>
              <span className="text-[var(--text-main)] font-semibold">Sentinel-1</span>
              <span>•</span>
              <span className="text-[var(--text-main)] font-semibold">USGS</span>
              <span>•</span>
              <span className="text-[var(--text-main)] font-semibold">GSI</span>
              <span>•</span>
              <span className="text-[var(--text-main)] font-semibold">Local Authorities</span>
            </div>
            <span className="font-mono text-[10px] text-[var(--text-dim)] font-semibold">v1.0.0</span>
          </div>
        </footer>

      </div>

      {/* Scene Inspection Modal */}
      {inspectingScene && (
        <div className="fixed inset-0 z-[9999] flex items-center justify-center p-4 bg-[var(--overlay-backdrop)] backdrop-blur-sm">
          <div className="bg-[var(--modal-bg)] border border-[var(--border-subtle)] w-full max-w-4xl rounded-2xl shadow-2xl flex flex-col max-h-[90vh] overflow-hidden text-[var(--text-main)]">
            {/* Modal Header */}
            <div className="flex items-center justify-between border-b border-[var(--border-subtle)] bg-[var(--modal-header-bg)] p-4 sm:p-5">
              <div>
                <span className="text-[10px] font-bold tracking-wider text-emerald-500 uppercase">Scene Inspection</span>
                <h2 className="text-sm font-mono text-[var(--text-main)] truncate max-w-[280px] sm:max-w-xl font-bold" title={inspectingScene}>
                  {inspectingScene}
                </h2>
              </div>
              <button 
                onClick={() => setInspectingScene(null)}
                className="text-[var(--text-muted)] hover:text-[var(--text-main)] bg-[var(--card-bg)] hover:bg-[var(--subcard-bg)] p-1.5 rounded-lg border border-[var(--border-subtle)] transition cursor-pointer text-xs font-semibold"
              >
                Close
              </button>
            </div>

            {/* Modal Body */}
            <div className="p-6 overflow-y-auto flex-1 space-y-6">
              {isInspecting && (
                <div className="flex flex-col items-center justify-center py-12 space-y-3">
                  <RefreshCw className="h-8 w-8 text-emerald-500 animate-spin" />
                  <p className="text-xs text-[var(--text-muted)]">Retrieving STAC catalogue record and analyzing asset layout...</p>
                </div>
              )}

              {inspectError && (
                <div className="bg-rose-500/10 border border-rose-500/20 rounded-xl p-6 text-center space-y-2">
                  <AlertTriangle className="h-8 w-8 text-rose-500 mx-auto" />
                  <p className="text-xs font-bold text-rose-500">Failed to Retrieve Scene Detail</p>
                  <p className="text-[11px] text-[var(--text-muted)] max-w-lg mx-auto">{inspectError}</p>
                </div>
              )}

              {inspectingDetail && (
                <div className="space-y-6">
                  {/* Two Column Layout: Left = Thumbnail Preview, Right = Metadata & Core Info */}
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                    {/* Left Column: Visual Preview */}
                    <div className="md:col-span-1 flex flex-col justify-between space-y-3 bg-[var(--card-bg)] p-4 rounded-xl border border-[var(--border-subtle)]">
                      <h4 className="text-[10px] font-bold tracking-wider text-[var(--text-dim)] uppercase">Visual Preview</h4>
                      <div className="flex-1 flex items-center justify-center bg-[var(--subcard-bg)] rounded-lg overflow-hidden border border-[var(--border-subtle)] relative group min-h-[180px]">
                        <img 
                          src={`${getApiBaseUrl()}/v1/satellite/scenes/${inspectingDetail.id}/preview`} 
                          alt="Sentinel-1 Preview Thumbnail"
                          className="max-h-[180px] max-w-full object-contain transition-transform duration-300 group-hover:scale-105"
                          onError={(e) => {
                            e.target.onerror = null;
                            e.target.style.display = 'none';
                            e.target.parentNode.innerHTML = '<div class="text-[10px] text-slate-500 text-center p-4">Preview image not available.<br/>Click S3/HTTPS link to fetch directly.</div>';
                          }}
                        />
                      </div>
                      <div className="text-center text-[10px] text-[var(--text-dim)]">
                        Quicklook Thumbnail (Publicly Accessible)
                      </div>
                    </div>

                    {/* Right Column: Metadata Details */}
                    <div className="md:col-span-2 space-y-4 flex flex-col justify-between">
                      <div>
                        <h4 className="text-[10px] font-bold tracking-wider text-[var(--text-dim)] uppercase mb-3">Scene Parameters</h4>
                        <div className="grid grid-cols-2 gap-4 text-xs bg-[var(--card-bg)] p-4 rounded-xl border border-[var(--border-subtle)]">
                          <div>
                            <span className="text-[var(--text-dim)] block mb-0.5 text-[10px]">Platform</span>
                            <span className="text-[var(--text-main)] font-semibold uppercase">{inspectingDetail.platform}</span>
                          </div>
                          <div>
                            <span className="text-[var(--text-dim)] block mb-0.5 text-[10px]">Acquisition Time</span>
                            <span className="text-[var(--text-main)] font-semibold">{new Date(inspectingDetail.datetime).toLocaleString()}</span>
                          </div>
                          <div>
                            <span className="text-[var(--text-dim)] block mb-0.5 text-[10px]">Orbit Direction</span>
                            <span className="text-[var(--text-main)] font-semibold uppercase">{inspectingDetail.orbit_direction}</span>
                          </div>
                          <div>
                            <span className="text-[var(--text-dim)] block mb-0.5 text-[10px]">Product Type</span>
                            <span className="text-[var(--text-main)] font-semibold uppercase">{inspectingDetail.product_type}</span>
                          </div>
                        </div>
                      </div>

                      {/* AOI Raster Caching Panel */}
                      <div className="space-y-3 bg-[var(--card-bg)] p-4 rounded-xl border border-[var(--border-subtle)]">
                        <div className="flex items-center justify-between">
                          <span className="text-xs font-bold text-[var(--text-main)] uppercase tracking-wider">AOI Raster Caching</span>
                          <span className={`px-2 py-0.5 rounded text-[9px] font-bold uppercase border ${
                            (processingStatus[inspectingDetail.id] || 'Ready') === 'Ready' ? 'bg-[var(--subcard-bg)] text-[var(--text-dim)] border-[var(--border-subtle)]' :
                            (processingStatus[inspectingDetail.id] || 'Ready') === 'Downloading' ? 'bg-blue-500/10 text-blue-500 border-blue-500/20 animate-pulse' :
                            (processingStatus[inspectingDetail.id] || 'Ready') === 'Clipping' ? 'bg-amber-500/10 text-amber-500 border-amber-500/20 animate-pulse' :
                            (processingStatus[inspectingDetail.id] || 'Ready') === 'Cached' ? 'bg-emerald-500/10 text-emerald-500 border-emerald-500/20' :
                            'bg-rose-500/10 text-rose-500 border-rose-500/20'
                          }`}>
                            {processingStatus[inspectingDetail.id] || 'Ready'}
                          </span>
                        </div>
                        
                        <p className="text-[10px] text-[var(--text-muted)] leading-normal">
                          Trigger S3 retrieval to download raw VV/VH bands and crop them to your 5 km AOI bounding box on the backend.
                        </p>

                        {processingError && (
                          <div className="bg-rose-500/10 border border-rose-500/20 rounded-lg p-2.5 text-[10px] text-rose-500 space-y-1">
                            <p className="font-bold flex items-center gap-1">
                              <AlertTriangle className="h-3.5 w-3.5 text-rose-500 shrink-0" />
                              Processing Failed
                            </p>
                            <p className="text-[var(--text-muted)] leading-normal text-[9px] font-medium">{processingError}</p>
                          </div>
                        )}

                        <button
                          onClick={() => handleProcessScene(inspectingDetail.id)}
                          disabled={['Downloading', 'Clipping', 'Cached'].includes(processingStatus[inspectingDetail.id] || 'Ready')}
                          className="w-full px-4 py-2 bg-emerald-600 hover:bg-emerald-500 disabled:bg-[var(--subcard-bg)] text-white disabled:text-[var(--text-dim)] rounded-lg font-semibold border border-emerald-500/30 disabled:border-[var(--border-subtle)] shadow-xs transition flex items-center justify-center gap-2 cursor-pointer disabled:cursor-not-allowed text-xs"
                        >
                          {['Downloading', 'Clipping'].includes(processingStatus[inspectingDetail.id] || 'Ready') ? (
                            <RefreshCw className="h-4 w-4 animate-spin" />
                          ) : (
                            <Layers className="h-4 w-4" />
                          )}
                          {(processingStatus[inspectingDetail.id] || 'Ready') === 'Cached' ? 'Scene Raster Cached' : 'Process Selected Scene'}
                        </button>
                      </div>
                    </div>
                  </div>

                  {/* Core Imagery Assets Grid (VH, VV, Product) */}
                  <div className="space-y-3">
                    <h3 className="text-xs font-bold text-[var(--text-main)] uppercase tracking-wider">Primary Radar Bands & Products</h3>
                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                      {/* VV Band */}
                      <div className="bg-[var(--card-bg)] border border-[var(--border-subtle)] rounded-xl p-4 flex flex-col justify-between space-y-3">
                        <div>
                          <div className="flex justify-between items-center mb-1">
                            <span className="text-xs font-bold text-[var(--text-main)]">VV Polarization</span>
                            <span className="text-[9px] px-1.5 py-0.5 rounded bg-blue-500/10 text-blue-500 border border-blue-500/20 font-mono">VH/VV</span>
                          </div>
                          <p className="text-[10px] text-[var(--text-muted)] leading-normal">Vertical transmit & Vertical receive amplitude data. Essential for surface roughness and soil moisture index calculations.</p>
                        </div>
                        <div className="flex justify-between items-center pt-2 border-t border-[var(--border-subtle)] text-xs">
                          <span className="text-[var(--text-dim)] text-[10px]">Size: {formatBytes(inspectingDetail.assets.find(a => a.key === 'vv')?.size)}</span>
                          <span className="text-[10px] text-[var(--text-dim)] font-medium italic">Backend-Only</span>
                        </div>
                      </div>

                      {/* VH Band */}
                      <div className="bg-[var(--card-bg)] border border-[var(--border-subtle)] rounded-xl p-4 flex flex-col justify-between space-y-3">
                        <div>
                          <div className="flex justify-between items-center mb-1">
                            <span className="text-xs font-bold text-[var(--text-main)]">VH Polarization</span>
                            <span className="text-[9px] px-1.5 py-0.5 rounded bg-blue-500/10 text-blue-500 border border-blue-500/20 font-mono">VH/VV</span>
                          </div>
                          <p className="text-[10px] text-[var(--text-muted)] leading-normal">Vertical transmit & Horizontal receive amplitude data. Critical for volume scattering, vegetation cover and terrain slope analysis.</p>
                        </div>
                        <div className="flex justify-between items-center pt-2 border-t border-[var(--border-subtle)] text-xs">
                          <span className="text-[var(--text-dim)] text-[10px]">Size: {formatBytes(inspectingDetail.assets.find(a => a.key === 'vh')?.size)}</span>
                          <span className="text-[10px] text-[var(--text-dim)] font-medium italic">Backend-Only</span>
                        </div>
                      </div>

                      {/* Zipped SAFE Product */}
                      <div className="bg-[var(--card-bg)] border border-[var(--border-subtle)] rounded-xl p-4 flex flex-col justify-between space-y-3">
                        <div>
                          <div className="flex justify-between items-center mb-1">
                            <span className="text-xs font-bold text-[var(--text-main)]">Full Product Archive</span>
                            <span className="text-[9px] px-1.5 py-0.5 rounded bg-amber-500/10 text-amber-500 border border-amber-500/20 font-mono">ZIP/SAFE</span>
                          </div>
                          <p className="text-[10px] text-[var(--text-muted)] leading-normal">Complete raw product folder. Contains radar calibration schemas, noise configurations, orbit state vectors, and geo-referencing files.</p>
                        </div>
                        <div className="flex justify-between items-center pt-2 border-t border-[var(--border-subtle)] text-xs">
                          <span className="text-[var(--text-dim)] text-[10px]">Size: {formatBytes(inspectingDetail.assets.find(a => a.key === 'Product')?.size)}</span>
                          <span className="text-[10px] text-[var(--text-dim)] font-medium italic">Requires Auth</span>
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* All Catalogue Assets list (Collapsible or full details) */}
                  <div className="space-y-3">
                    <h3 className="text-xs font-bold text-[var(--text-main)] uppercase tracking-wider">All Catalogued Assets ({inspectingDetail.assets.length})</h3>
                    <div className="border border-[var(--border-subtle)] rounded-xl overflow-hidden bg-[var(--card-bg)] overflow-x-auto">
                      <table className="w-full text-left border-collapse text-xs min-w-[700px]">
                        <thead>
                          <tr className="bg-[var(--subcard-bg)] border-b border-[var(--border-subtle)] text-[var(--text-dim)] uppercase tracking-wider text-[10px] font-semibold">
                            <th className="p-3">Asset Key</th>
                            <th className="p-3">Title / Description</th>
                            <th className="p-3">Media Type</th>
                            <th className="p-3">Size</th>
                            <th className="p-3">Access URI (S3 / HTTPS)</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-[var(--border-subtle)]">
                          {inspectingDetail.assets.map((asset) => (
                            <tr key={asset.key} className="hover:bg-[var(--subcard-bg)] transition">
                              <td className="p-3 font-mono font-bold text-emerald-500 text-[11px]">{asset.key}</td>
                              <td className="p-3 text-[var(--text-main)] max-w-[200px] truncate font-medium" title={asset.title}>{asset.title}</td>
                              <td className="p-3 text-[var(--text-dim)] font-mono text-[10px]">{asset.type || 'unknown'}</td>
                              <td className="p-3 text-[var(--text-muted)] font-medium whitespace-nowrap">{formatBytes(asset.size)}</td>
                              <td className="p-3 font-mono text-[10px] text-[var(--text-dim)] max-w-[250px] truncate select-all" title={asset.href}>
                                {asset.href}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Modal Footer */}
            <div className="border-t border-[var(--border-subtle)] p-4 bg-[var(--modal-footer-bg)] flex justify-end">
              <button
                onClick={() => setInspectingScene(null)}
                className="px-4 py-2 bg-[var(--card-bg)] hover:bg-[var(--subcard-bg)] text-[var(--text-main)] border border-[var(--border-subtle)] text-xs font-semibold rounded-lg transition cursor-pointer"
              >
                Close Details
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Field Hazard Report Submission Modal */}
      <FieldReportModal
        isOpen={isReportModalOpen}
        onClose={() => setIsReportModalOpen(false)}
        selectedLocation={selectedLocation}
        onReportSubmitted={handleReportSubmitted}
      />

      {/* Field Intelligence Operational Review Workspace */}
      <FieldIntelligenceWorkspace
        isOpen={isWorkspaceOpen}
        onClose={() => setIsWorkspaceOpen(false)}
        onReportUpdated={handleReportSubmitted}
      />

      {/* Emergency Disaster Alert Dispatch Modal */}
      <AlertDispatchModal
        isOpen={isAlertModalOpen}
        onClose={() => setIsAlertModalOpen(false)}
        alertData={alertModalData || {}}
      />

      {/* Official Disaster Situation Report (SITREP) Modal */}
      <SitrepModal
        isOpen={isSitrepModalOpen}
        onClose={() => setIsSitrepModalOpen(false)}
        reportContext={{
          selectedLocation,
          aoi,
          terrainData,
          weatherData,
          compositeRiskData,
          satelliteChangeData,
          earlyWarningData,
          roadData,
          fieldReports,
          locationName: selectedLocation
            ? `${selectedLocation.lat.toFixed(4)}°N, ${selectedLocation.lng.toFixed(4)}°E (Monitored Sector)`
            : 'NER High-Risk Landslide Corridor'
        }}
      />

      {/* Role-Based Authentication & Login Modal */}
      <LoginModal
        isOpen={isLoginModalOpen}
        initialTab={loginModalTab}
        onClose={() => setIsLoginModalOpen(false)}
        onLoginSuccess={(user) => {
          setCurrentUser(user)
          setIsLoginModalOpen(false)
        }}
      />

      {/* 1-Click Offline 2G SMS & Shelter Modal */}
      <EmergencySmsModal
        isOpen={isSmsModalOpen}
        onClose={() => setIsSmsModalOpen(false)}
        selectedLocation={selectedLocation}
        isOnline={isOnline}
      />
    </div>
  )
}

export default App
