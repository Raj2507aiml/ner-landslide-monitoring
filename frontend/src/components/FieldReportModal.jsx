import { useState, useEffect, useRef } from 'react';
import { createPortal } from 'react-dom';
import { 
  X, 
  Upload, 
  Image as ImageIcon, 
  MapPin, 
  Navigation, 
  AlertTriangle, 
  CheckCircle2, 
  ShieldAlert, 
  FileText, 
  Trash2, 
  Loader2 
} from 'lucide-react';
import { createFieldReport, uploadFieldReportMedia } from '../services/fieldReportService';

const REPORT_TYPES = [
  { value: 'CRACK', label: 'Ground Crack / Fissure', desc: 'Tension cracks, surface openings, road fissures' },
  { value: 'SLOPE_MOVEMENT', label: 'Slope Movement / Creep', desc: 'Tilted trees, bulging slopes, slow deformation' },
  { value: 'BLOCKED_ROAD', label: 'Blocked Road / Pass', desc: 'Rockfall, mud accumulation blocking transit' },
  { value: 'LANDSLIDE', label: 'Active Landslide / Debris Flow', desc: 'Mass earth or rock displacement in progress' },
  { value: 'DEBRIS', label: 'Debris Accumulation', desc: 'Talus, loose rock or soil build-up on slopes' },
  { value: 'OTHER', label: 'Other Hazard Observation', desc: 'Drainage failure, retaining wall distress, etc.' },
];

const SEVERITY_LEVELS = [
  { value: 'LOW', label: 'Low', color: 'border-emerald-500/40 text-emerald-700 dark:text-emerald-400 bg-emerald-500/10 dark:bg-emerald-950/30' },
  { value: 'MEDIUM', label: 'Medium', color: 'border-amber-500/40 text-amber-700 dark:text-amber-400 bg-amber-500/10 dark:bg-amber-950/30' },
  { value: 'HIGH', label: 'High', color: 'border-orange-500/40 text-orange-700 dark:text-orange-400 bg-orange-500/10 dark:bg-orange-950/30' },
  { value: 'CRITICAL', label: 'Critical', color: 'border-rose-500/40 text-rose-700 dark:text-rose-400 bg-rose-500/10 dark:bg-rose-950/30' },
];

const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10 MB limit
const ALLOWED_TYPES = ['image/jpeg', 'image/png', 'image/webp'];

export default function FieldReportModal({ isOpen, onClose, selectedLocation, onReportSubmitted }) {
  const [reportType, setReportType] = useState('CRACK');
  const [severity, setSeverity] = useState('MEDIUM');
  const [reporterType, setReporterType] = useState('CITIZEN');
  const [description, setDescription] = useState('');
  const [latitude, setLatitude] = useState('');
  const [longitude, setLongitude] = useState('');

  // Media files state: array of { id, file, previewUrl, name, size }
  const [selectedFiles, setSelectedFiles] = useState([]);
  
  // Submission & UI states
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitProgressText, setSubmitProgressText] = useState('');
  const [errorMessage, setErrorMessage] = useState(null);
  const [successData, setSuccessData] = useState(null);
  const [isGettingGps, setIsGettingGps] = useState(false);

  const fileInputRef = useRef(null);

  // Sync initial coordinates from selected map location
  useEffect(() => {
    if (isOpen) {
      if (selectedLocation && selectedLocation.lat && selectedLocation.lng) {
        setLatitude(selectedLocation.lat.toString());
        setLongitude(selectedLocation.lng.toString());
      }
      setErrorMessage(null);
      setSuccessData(null);
    }
  }, [isOpen, selectedLocation]);

  // Lock body scroll and register escape key handler when open
  useEffect(() => {
    if (!isOpen) return;

    const originalOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';

    const handleKeyDown = (e) => {
      if (e.key === 'Escape' && !isSubmitting) {
        onClose();
      }
    };

    window.addEventListener('keydown', handleKeyDown);

    return () => {
      document.body.style.overflow = originalOverflow;
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [isOpen, isSubmitting, onClose]);

  // Clean up object URLs to prevent memory leaks
  useEffect(() => {
    return () => {
      selectedFiles.forEach(item => {
        if (item.previewUrl) {
          URL.revokeObjectURL(item.previewUrl);
        }
      });
    };
  }, [selectedFiles]);

  if (!isOpen) return null;

  const handleUseMapLocation = () => {
    if (selectedLocation && selectedLocation.lat && selectedLocation.lng) {
      setLatitude(selectedLocation.lat.toString());
      setLongitude(selectedLocation.lng.toString());
      setErrorMessage(null);
    } else {
      setErrorMessage('Please select a location on the dashboard map first.');
    }
  };

  const handleUseDeviceGps = () => {
    if (!navigator.geolocation) {
      setErrorMessage('Geolocation is not supported by your browser.');
      return;
    }

    setIsGettingGps(true);
    setErrorMessage(null);

    navigator.geolocation.getCurrentPosition(
      (position) => {
        setLatitude(position.coords.latitude.toFixed(6));
        setLongitude(position.coords.longitude.toFixed(6));
        setIsGettingGps(false);
      },
      (error) => {
        setIsGettingGps(false);
        if (error.code === error.PERMISSION_DENIED) {
          setErrorMessage('Location permission was denied. Please enter coordinates manually.');
        } else {
          setErrorMessage('Unable to retrieve device GPS location.');
        }
      },
      { enableHighAccuracy: true, timeout: 10000 }
    );
  };

  const handleFileChange = (e) => {
    const files = Array.from(e.target.files || []);
    if (!files.length) return;

    const newValidFiles = [];
    let hasInvalid = false;
    let errorText = '';

    for (const file of files) {
      if (!ALLOWED_TYPES.includes(file.type)) {
        hasInvalid = true;
        errorText = `File '${file.name}' is not supported. Only JPEG, PNG, and WebP images are allowed.`;
        continue;
      }
      if (file.size > MAX_FILE_SIZE) {
        hasInvalid = true;
        errorText = `File '${file.name}' exceeds the 10 MB size limit.`;
        continue;
      }

      newValidFiles.push({
        id: Math.random().toString(36).substring(2, 9),
        file,
        name: file.name,
        size: (file.size / (1024 * 1024)).toFixed(2) + ' MB',
        previewUrl: URL.createObjectURL(file)
      });
    }

    if (hasInvalid && errorText) {
      setErrorMessage(errorText);
    } else {
      setErrorMessage(null);
    }

    setSelectedFiles(prev => [...prev, ...newValidFiles]);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const handleRemoveFile = (idToRemove) => {
    setSelectedFiles(prev => {
      const itemToRemove = prev.find(item => item.id === idToRemove);
      if (itemToRemove && itemToRemove.previewUrl) {
        URL.revokeObjectURL(itemToRemove.previewUrl);
      }
      return prev.filter(item => item.id !== idToRemove);
    });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setErrorMessage(null);

    // Validation
    const latNum = parseFloat(latitude);
    const lonNum = parseFloat(longitude);

    if (isNaN(latNum) || latNum < -90 || latNum > 90) {
      setErrorMessage('Please provide a valid latitude between -90 and 90 degrees.');
      return;
    }
    if (isNaN(lonNum) || lonNum < -180 || lonNum > 180) {
      setErrorMessage('Please provide a valid longitude between -180 and 180 degrees.');
      return;
    }
    if (!description.trim() || description.trim().length < 3) {
      setErrorMessage('Please provide an observation description (minimum 3 characters).');
      return;
    }

    setIsSubmitting(true);
    setSubmitProgressText('Submitting field observation report...');

    // Step 1: Create Field Report
    const reportPayload = {
      report_type: reportType,
      description: description.trim(),
      latitude: latNum,
      longitude: lonNum,
      reporter_type: reporterType,
      severity: severity
    };

    const createResult = await createFieldReport(reportPayload);

    if (!createResult.ok) {
      setIsSubmitting(false);
      setSubmitProgressText('');
      setErrorMessage(createResult.error || 'Failed to submit report. Please verify coordinates are within NER.');
      return;
    }

    const createdReport = createResult.data;
    const reportId = createdReport.id;
    let uploadedMediaCount = 0;
    let mediaErrors = 0;

    // Step 2: Upload Photo Evidence if attached
    if (selectedFiles.length > 0) {
      for (let i = 0; i < selectedFiles.length; i++) {
        setSubmitProgressText(`Uploading evidence photo (${i + 1}/${selectedFiles.length})...`);
        const item = selectedFiles[i];
        const mediaResult = await uploadFieldReportMedia(reportId, item.file);
        if (mediaResult.ok) {
          uploadedMediaCount++;
        } else {
          mediaErrors++;
        }
      }
    }

    setIsSubmitting(false);
    setSubmitProgressText('');
    
    setSuccessData({
      reportId: createdReport.id,
      reportType: createdReport.report_type,
      severity: createdReport.severity,
      mediaCount: uploadedMediaCount,
      mediaErrors
    });

    if (onReportSubmitted) {
      onReportSubmitted(createdReport);
    }
  };

  const handleResetForm = () => {
    setDescription('');
    setSelectedFiles([]);
    setSuccessData(null);
    setErrorMessage(null);
  };

  const handleBackdropClick = (e) => {
    if (e.target === e.currentTarget && !isSubmitting) {
      onClose();
    }
  };

  const modalContent = (
    <div 
      className="fixed inset-0 z-[99999] flex items-center justify-center p-3 sm:p-4 md:p-6 bg-[var(--overlay-backdrop)] backdrop-blur-md overflow-hidden"
      onClick={handleBackdropClick}
      onWheel={(e) => e.stopPropagation()}
    >
      <div 
        className="relative w-full max-w-2xl max-h-[90vh] flex flex-col bg-[var(--modal-bg)] border border-[var(--border-subtle)] text-[var(--text-main)] rounded-2xl shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-150"
        onClick={(e) => e.stopPropagation()}
        onWheel={(e) => e.stopPropagation()}
      >
        
        {/* Modal Header (Fixed at top of modal) */}
        <div className="flex-none flex items-center justify-between px-6 py-4 border-b border-[var(--border-subtle)] bg-[var(--modal-header-bg)]">
          <div className="flex items-center gap-2.5">
            <div className="p-2 bg-emerald-500/10 text-emerald-500 rounded-lg border border-emerald-500/20">
              <ShieldAlert className="h-5 w-5" />
            </div>
            <div>
              <h2 className="text-base font-bold text-[var(--text-main)] tracking-tight">
                Report Field Hazard Observation
              </h2>
              <p className="text-xs text-[var(--text-muted)]">
                Submit geo-tagged ground intelligence for disaster response & monitoring
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            disabled={isSubmitting}
            className="p-1.5 rounded-lg text-[var(--text-dim)] hover:text-[var(--text-main)] hover:bg-[var(--card-bg)] transition disabled:opacity-50 cursor-pointer"
            title="Close modal (Esc)"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Modal Body (Scrollable interior) */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6 overscroll-contain">
          
          {/* Success State */}
          {successData ? (
            <div className="space-y-6 py-4 text-center">
              <div className="inline-flex p-3 bg-emerald-500/10 border border-emerald-500/30 rounded-2xl text-emerald-500">
                <CheckCircle2 className="h-10 w-10" />
              </div>

              <div className="space-y-2">
                <h3 className="text-xl font-bold text-[var(--text-main)]">Observation Submitted Successfully</h3>
                <p className="text-sm text-[var(--text-muted)] max-w-md mx-auto">
                  Report <span className="font-mono font-bold text-emerald-500">#{successData.reportId}</span> has been recorded and queued for operational verification by geological response teams.
                </p>
                {successData.mediaCount > 0 && (
                  <p className="text-xs text-[var(--text-dim)]">
                    Attached {successData.mediaCount} photo evidence {successData.mediaCount === 1 ? 'file' : 'files'}.
                  </p>
                )}
                {successData.mediaErrors > 0 && (
                  <p className="text-xs text-amber-500">
                    Note: {successData.mediaErrors} evidence file(s) could not be uploaded, but your report is securely saved.
                  </p>
                )}
              </div>

              <div className="bg-[var(--subcard-bg)] border border-[var(--border-subtle)] rounded-xl p-3.5 text-left text-xs text-[var(--text-muted)] space-y-1 max-w-lg mx-auto">
                <p className="font-semibold text-emerald-500 font-mono">ℹ️ Operational Intelligence Notice:</p>
                <p className="text-[var(--text-dim)] leading-relaxed">
                  Field reports represent human observational intelligence. They are evaluated alongside environmental sensor telemetry and satellite radar surface change analysis.
                </p>
              </div>

              <div className="flex items-center justify-center gap-3 pt-2">
                <button
                  type="button"
                  onClick={handleResetForm}
                  className="px-4 py-2 rounded-xl bg-[var(--card-bg)] hover:bg-[var(--subcard-bg)] text-[var(--text-main)] border border-[var(--border-subtle)] text-xs font-semibold transition cursor-pointer"
                >
                  Submit Another Observation
                </button>
                <button
                  type="button"
                  onClick={onClose}
                  className="px-5 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold shadow-md shadow-emerald-950/40 transition cursor-pointer"
                >
                  Done
                </button>
              </div>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-5">
              
              {/* Error Banner */}
              {errorMessage && (
                <div className="flex items-start gap-2.5 p-3.5 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-500 text-xs">
                  <AlertTriangle className="h-4 w-4 shrink-0 mt-0.5 text-rose-500" />
                  <p className="leading-relaxed font-medium">{errorMessage}</p>
                </div>
              )}

              {/* Field 1: Report Type */}
              <div className="space-y-2">
                <label className="block text-xs font-semibold text-[var(--text-dim)] uppercase tracking-wider">
                  Hazard Observation Type *
                </label>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                  {REPORT_TYPES.map((t) => {
                    const isSelected = reportType === t.value;
                    return (
                      <button
                        key={t.value}
                        type="button"
                        onClick={() => setReportType(t.value)}
                        className={`p-3 rounded-xl border text-left transition flex flex-col justify-between cursor-pointer ${
                          isSelected
                            ? 'bg-emerald-600/15 border-emerald-500/60 ring-1 ring-emerald-500/50'
                            : 'bg-[var(--subcard-bg)] border-[var(--border-subtle)] hover:border-[var(--border-strong)] hover:bg-[var(--card-bg)]'
                        }`}
                      >
                        <span className={`text-xs font-bold ${isSelected ? 'text-emerald-500' : 'text-[var(--text-main)]'}`}>
                          {t.label}
                        </span>
                        <span className="text-[10.5px] text-[var(--text-dim)] mt-1 leading-snug">
                          {t.desc}
                        </span>
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Field 2 & 3: Severity & Submitter Role */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                
                {/* Severity */}
                <div className="space-y-2">
                  <label className="block text-xs font-semibold text-[var(--text-dim)] uppercase tracking-wider">
                    Observed Severity *
                  </label>
                  <div className="grid grid-cols-2 gap-1.5">
                    {SEVERITY_LEVELS.map((s) => {
                      const isSelected = severity === s.value;
                      return (
                        <button
                          key={s.value}
                          type="button"
                          onClick={() => setSeverity(s.value)}
                          className={`py-2 px-2.5 rounded-lg border text-xs font-bold transition flex items-center justify-center gap-1.5 cursor-pointer ${
                            isSelected
                              ? `${s.color} ring-1 ring-current`
                              : 'bg-[var(--subcard-bg)] border-[var(--border-subtle)] text-[var(--text-muted)] hover:text-[var(--text-main)] hover:bg-[var(--card-bg)]'
                          }`}
                        >
                          <span className={`h-2 w-2 rounded-full ${isSelected ? 'bg-current' : 'bg-slate-400'}`} />
                          {s.label}
                        </button>
                      );
                    })}
                  </div>
                </div>

                {/* Reporter Type */}
                <div className="space-y-2">
                  <label className="block text-xs font-semibold text-[var(--text-dim)] uppercase tracking-wider">
                    Reporter Role *
                  </label>
                  <div className="grid grid-cols-2 gap-1.5">
                    <button
                      type="button"
                      onClick={() => setReporterType('CITIZEN')}
                      className={`py-2 px-2.5 rounded-lg border text-xs font-bold transition cursor-pointer ${
                        reporterType === 'CITIZEN'
                          ? 'bg-sky-500/15 border-sky-500/50 text-sky-500 ring-1 ring-sky-500/40'
                          : 'bg-[var(--subcard-bg)] border-[var(--border-subtle)] text-[var(--text-muted)] hover:text-[var(--text-main)] hover:bg-[var(--card-bg)]'
                      }`}
                    >
                      Citizen / Resident
                    </button>
                    <button
                      type="button"
                      onClick={() => setReporterType('FIELD_OFFICIAL')}
                      className={`py-2 px-2.5 rounded-lg border text-xs font-bold transition cursor-pointer ${
                        reporterType === 'FIELD_OFFICIAL'
                          ? 'bg-emerald-500/15 border-emerald-500/50 text-emerald-500 ring-1 ring-emerald-500/40'
                          : 'bg-[var(--subcard-bg)] border-[var(--border-subtle)] text-[var(--text-muted)] hover:text-[var(--text-main)] hover:bg-[var(--card-bg)]'
                      }`}
                    >
                      Field Official
                    </button>
                  </div>
                </div>
              </div>

              {/* Field 4: Description */}
              <div className="space-y-2">
                <div className="flex justify-between items-center">
                  <label className="block text-xs font-semibold text-[var(--text-dim)] uppercase tracking-wider">
                    Observation Details *
                  </label>
                  <span className="text-[10px] text-[var(--text-dim)] font-mono">
                    {description.length} / 2000 chars
                  </span>
                </div>
                <textarea
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="Describe location markers, ground cracks, road blockages, recent heavy rains, or infrastructure damage..."
                  rows={3}
                  maxLength={2000}
                  className="w-full px-3.5 py-2.5 rounded-xl bg-[var(--subcard-bg)] border border-[var(--border-subtle)] text-[var(--text-main)] text-xs placeholder:text-[var(--text-dim)] focus:outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 transition leading-relaxed resize-none"
                />
              </div>

              {/* Field 5: Location Coordinates */}
              <div className="space-y-2">
                <div className="flex justify-between items-center">
                  <label className="block text-xs font-semibold text-[var(--text-dim)] uppercase tracking-wider">
                    Geo-Location (NER Coordinates) *
                  </label>
                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      onClick={handleUseMapLocation}
                      className="text-[10.5px] text-emerald-500 hover:text-emerald-400 font-semibold flex items-center gap-1 transition cursor-pointer"
                    >
                      <MapPin className="h-3 w-3" />
                      Use Map Point
                    </button>
                    <span className="text-[var(--border-subtle)]">|</span>
                    <button
                      type="button"
                      onClick={handleUseDeviceGps}
                      disabled={isGettingGps}
                      className="text-[10.5px] text-sky-500 hover:text-sky-400 font-semibold flex items-center gap-1 transition disabled:opacity-50 cursor-pointer"
                    >
                      {isGettingGps ? (
                        <Loader2 className="h-3 w-3 animate-spin" />
                      ) : (
                        <Navigation className="h-3 w-3" />
                      )}
                      Use GPS
                    </button>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <span className="text-[10px] text-[var(--text-dim)] block mb-1">Latitude</span>
                    <input
                      type="number"
                      step="any"
                      value={latitude}
                      onChange={(e) => setLatitude(e.target.value)}
                      placeholder="e.g. 27.3314"
                      className="w-full px-3 py-2 rounded-lg bg-[var(--subcard-bg)] border border-[var(--border-subtle)] text-[var(--text-main)] text-xs font-mono placeholder:text-[var(--text-dim)] focus:outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 transition"
                    />
                  </div>
                  <div>
                    <span className="text-[10px] text-[var(--text-dim)] block mb-1">Longitude</span>
                    <input
                      type="number"
                      step="any"
                      value={longitude}
                      onChange={(e) => setLongitude(e.target.value)}
                      placeholder="e.g. 88.6138"
                      className="w-full px-3 py-2 rounded-lg bg-[var(--subcard-bg)] border border-[var(--border-subtle)] text-[var(--text-main)] text-xs font-mono placeholder:text-[var(--text-dim)] focus:outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 transition"
                    />
                  </div>
                </div>
              </div>

              {/* Field 6: Photo Evidence Upload */}
              <div className="space-y-2">
                <label className="block text-xs font-semibold text-[var(--text-dim)] uppercase tracking-wider">
                  Photo Evidence (Optional, max 10MB per image)
                </label>

                <div 
                  onClick={() => fileInputRef.current?.click()}
                  className="border-2 border-dashed border-[var(--border-subtle)] hover:border-emerald-500/60 bg-[var(--subcard-bg)] hover:bg-[var(--card-bg)] p-4 rounded-xl text-center cursor-pointer transition space-y-1.5"
                >
                  <div className="inline-flex p-2 bg-[var(--card-bg)] border border-[var(--border-subtle)] rounded-lg text-[var(--text-dim)]">
                    <Upload className="h-4 w-4" />
                  </div>
                  <p className="text-xs text-[var(--text-main)] font-medium">
                    Click or drag photos to attach evidence
                  </p>
                  <p className="text-[10px] text-[var(--text-dim)]">
                    Supports JPEG, PNG, WebP (EXIF GPS will be extracted if present)
                  </p>
                  <input
                    ref={fileInputRef}
                    type="file"
                    multiple
                    accept="image/jpeg,image/png,image/webp"
                    onChange={handleFileChange}
                    className="hidden"
                  />
                </div>

                {/* Previews Grid */}
                {selectedFiles.length > 0 && (
                  <div className="grid grid-cols-2 sm:grid-cols-3 gap-2.5 pt-1">
                    {selectedFiles.map((item) => (
                      <div 
                        key={item.id}
                        className="relative group bg-[var(--subcard-bg)] border border-[var(--border-subtle)] rounded-lg overflow-hidden p-1.5 flex items-center gap-2"
                      >
                        <img 
                          src={item.previewUrl} 
                          alt={item.name} 
                          className="h-12 w-12 object-cover rounded bg-[var(--card-bg)] shrink-0"
                        />
                        <div className="min-w-0 flex-1">
                          <p className="text-[11px] text-[var(--text-main)] font-medium truncate" title={item.name}>
                            {item.name}
                          </p>
                          <p className="text-[9.5px] text-[var(--text-dim)] font-mono">
                            {item.size}
                          </p>
                        </div>
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            handleRemoveFile(item.id);
                          }}
                          className="p-1 rounded bg-rose-500/10 hover:bg-rose-500/20 text-rose-500 hover:text-rose-400 transition cursor-pointer"
                          title="Remove image"
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Progress status if uploading */}
              {isSubmitting && (
                <div className="flex items-center gap-2 p-3 bg-[var(--subcard-bg)] border border-[var(--border-subtle)] rounded-xl text-[var(--text-muted)] text-xs font-medium">
                  <Loader2 className="h-4 w-4 animate-spin shrink-0 text-emerald-500" />
                  <span>{submitProgressText}</span>
                </div>
              )}

              {/* Action Buttons */}
              <div className="flex items-center justify-end gap-3 pt-2 border-t border-[var(--border-subtle)]">
                <button
                  type="button"
                  onClick={onClose}
                  disabled={isSubmitting}
                  className="px-4 py-2 rounded-xl text-[var(--text-dim)] hover:text-[var(--text-main)] hover:bg-[var(--card-bg)] text-xs font-semibold transition disabled:opacity-50 cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="px-5 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold shadow-md shadow-emerald-950/40 transition disabled:opacity-50 flex items-center gap-2 cursor-pointer"
                >
                  {isSubmitting ? (
                    <>
                      <Loader2 className="h-4 w-4 animate-spin" />
                      Submitting...
                    </>
                  ) : (
                    <>
                      <ShieldAlert className="h-4 w-4" />
                      Submit Report
                    </>
                  )}
                </button>
              </div>
            </form>
          )}

        </div>
      </div>
    </div>
  );

  return typeof document !== 'undefined' ? createPortal(modalContent, document.body) : null;
}
