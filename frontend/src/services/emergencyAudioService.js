/**
 * Emergency Audio Warning Service
 * Synthesizes official disaster broadcast warning chimes using the HTML5 Web Audio API.
 * Zero external mp3/wav dependencies, zero latency, 100% offline resilient.
 * Includes global mute/unmute persistence and session cooldown protection.
 */

import { getLanguage, t } from './i18nService.js';

const MUTE_STORAGE_KEY = 'ner_emergency_audio_muted';
const VOICE_STORAGE_KEY = 'ner_emergency_voice_enabled';

// Audio context singleton
let audioCtx = null;
let lastPlayedSector = null;
let lastPlayedTimestamp = 0;
const COOLDOWN_MS = 15000; // 15 seconds debounce per sector

// Listeners for mute state changes
const muteChangeListeners = new Set();

function getAudioContext() {
  if (!audioCtx || audioCtx.state === 'closed') {
    const AudioContextClass = typeof window !== 'undefined' ? (window.AudioContext || window.webkitAudioContext) : null;
    if (AudioContextClass) {
      audioCtx = new AudioContextClass();
    }
  }
  return audioCtx;
}

// Browser Autoplay Policy unlocker: resumes AudioContext upon first user gesture anywhere
if (typeof window !== 'undefined') {
  const unlockAudio = () => {
    try {
      const ctx = getAudioContext();
      if (ctx && ctx.state === 'suspended') {
        ctx.resume().catch(() => {});
      }
    } catch {}
  };
  ['click', 'touchstart', 'keydown', 'pointerdown'].forEach(evt => {
    window.addEventListener(evt, unlockAudio, { passive: true });
  });
}

/**
 * Returns true if emergency audio is currently muted by the user.
 */
export function isAudioMuted() {
  try {
    return localStorage.getItem(MUTE_STORAGE_KEY) === 'true';
  } catch {
    return false;
  }
}

/**
 * Updates the global mute state and notifies all subscribed components.
 */
export function setAudioMuted(muted) {
  try {
    localStorage.setItem(MUTE_STORAGE_KEY, muted ? 'true' : 'false');
  } catch {}
  muteChangeListeners.forEach(listener => {
    try {
      listener(muted);
    } catch {}
  });
  return muted;
}

/**
 * Toggles the global audio mute state.
 */
export function toggleAudioMute() {
  const current = isAudioMuted();
  return setAudioMuted(!current);
}

/**
 * Subscribe to audio mute state changes.
 */
export function subscribeAudioMute(callback) {
  muteChangeListeners.add(callback);
  return () => muteChangeListeners.delete(callback);
}

/**
 * Checks if voice announcement is enabled.
 */
export function isVoiceEnabled() {
  try {
    return localStorage.getItem(VOICE_STORAGE_KEY) !== 'false'; // default true
  } catch {
    return true;
  }
}

/**
 * Toggles voice announcement.
 */
export function setVoiceEnabled(enabled) {
  try {
    localStorage.setItem(VOICE_STORAGE_KEY, enabled ? 'true' : 'false');
  } catch {}
  return enabled;
}

/**
 * Plays an authoritative dual/tri-tone emergency warning chime.
 * Simulates standard emergency broadcast system (EBS) alerting frequencies.
 * Frequencies: 880 Hz (A5) -> 659.25 Hz (E5) -> 880 Hz (A5) with smooth exponential envelope.
 * 
 * @param {Object} options
 * @param {string} options.sectorKey - Unique key for the active sector to prevent click spamming
 * @param {boolean} options.force - If true, bypasses cooldown
 */
export function playEmergencyAlertSound(options = {}) {
  const { sectorKey = 'default', force = false } = options;

  if (isAudioMuted()) {
    return false;
  }

  const now = Date.now();
  if (!force && sectorKey === lastPlayedSector && (now - lastPlayedTimestamp) < COOLDOWN_MS) {
    return false;
  }

  lastPlayedSector = sectorKey;
  lastPlayedTimestamp = now;

  try {
    const ctx = getAudioContext();
    if (!ctx) return false;

    const executePlayback = () => {
      try {
        const startTime = ctx.currentTime + 0.05;
        const masterGain = ctx.createGain();
        masterGain.gain.setValueAtTime(0.35, startTime); // Clear, audible alert volume (35%)
        masterGain.connect(ctx.destination);

        // Tone sequence: [Frequency, StartOffset, Duration]
        const tones = [
          { freq: 880.0, offset: 0.00, dur: 0.22 }, // High Tone (A5)
          { freq: 659.25, offset: 0.24, dur: 0.22 }, // Mid Tone (E5)
          { freq: 880.0, offset: 0.48, dur: 0.40 }  // Final Attention Tone (A5)
        ];

        tones.forEach(({ freq, offset, dur }) => {
          const osc = ctx.createOscillator();
          const gain = ctx.createGain();

          osc.type = 'sine';
          osc.frequency.setValueAtTime(freq, startTime + offset);

          // Attack & decay envelope
          gain.gain.setValueAtTime(0.0001, startTime + offset);
          gain.gain.exponentialRampToValueAtTime(1.0, startTime + offset + 0.04);
          gain.gain.exponentialRampToValueAtTime(0.001, startTime + offset + dur);

          osc.connect(gain);
          gain.connect(masterGain);

          osc.start(startTime + offset);
          osc.stop(startTime + offset + dur + 0.05);
        });

        // Optional synthesized voice dispatch after chime finishes
        if (isVoiceEnabled() && 'speechSynthesis' in window) {
          setTimeout(() => {
            if (!isAudioMuted()) {
              try {
                window.speechSynthesis.cancel(); // Cancel any ongoing speech
                const currentLang = getLanguage();
                const alertText = t('audio_alert_phrase', 'Warning: Critical landslide hazard alert in this sector. Travel is not advised.', currentLang);
                const utterance = new SpeechSynthesisUtterance(alertText);
                utterance.rate = 0.95;
                utterance.pitch = 1.0;
                utterance.volume = 0.90;
                if (currentLang === 'hi') utterance.lang = 'hi-IN';
                else if (currentLang === 'bn') utterance.lang = 'bn-IN';
                else if (currentLang === 'ne') utterance.lang = 'ne-NP';
                else utterance.lang = 'en-IN';
                window.speechSynthesis.speak(utterance);
              } catch {}
            }
          }, 950);
        }
      } catch (err) {
        console.warn('[Emergency Audio] Error synthesizing tones:', err);
      }
    };

    if (ctx.state === 'suspended') {
      ctx.resume().then(executePlayback).catch(executePlayback);
    } else {
      executePlayback();
    }

    return true;
  } catch (err) {
    console.warn('[Emergency Audio] Unable to play sound:', err);
    return false;
  }
}

/**
 * Manual test function: Unconditionally triggers the emergency warning chime.
 */
export function testEmergencyAlarmSound() {
  return playEmergencyAlertSound({
    sectorKey: `test_${Date.now()}`,
    force: true
  });
}

/**
 * Immediately silences all ongoing sounds and speech.
 */
export function stopAllEmergencyAudio() {
  if (audioCtx && audioCtx.state === 'running') {
    try {
      audioCtx.suspend();
    } catch {}
  }
  if ('speechSynthesis' in window) {
    try {
      window.speechSynthesis.cancel();
    } catch {}
  }
}

let lastTravelAlertVoiceTimestamp = 0;
const TRAVEL_VOICE_GLOBAL_COOLDOWN_MS = 20000; // 20s minimum between speech calls

/**
 * Dispatches an automated voice alert for travel route hazards.
 * Plays EBS attention chime, then speaks the advisory dynamically with distance & risk percentage.
 * 
 * @param {Object} params
 * @param {number} params.riskScore - Landslide risk percentage (e.g. 82)
 * @param {number} params.distanceKm - Distance to hazard in km (e.g. 8.7)
 * @param {string} params.regionName - Affected corridor or landmark name
 * @param {boolean} params.isUrgent - True if approaching close (<= 5 km)
 * @param {boolean} params.force - If true, bypasses cooldown (used for manual test)
 */
export function playTravelSafetyVoiceAlert({
  riskScore = 75,
  distanceKm = 9.0,
  regionName = 'High-Risk Landslide Corridor',
  isUrgent = false,
  force = false
} = {}) {
  if (isAudioMuted() || !isVoiceEnabled()) {
    return false;
  }

  const now = Date.now();
  if (!force && (now - lastTravelAlertVoiceTimestamp) < TRAVEL_VOICE_GLOBAL_COOLDOWN_MS) {
    return false;
  }
  lastTravelAlertVoiceTimestamp = now;

  // 1. Play attention chime
  playEmergencyAlertSound({
    sectorKey: `travel_${regionName}`,
    force: true
  });

  // 2. Synthesize dynamic voice warning
  if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
    setTimeout(() => {
      if (isAudioMuted() || !isVoiceEnabled()) return;
      try {
        window.speechSynthesis.cancel(); // Stop any pending speech
        const roundedDistance = Math.max(1, Math.round(distanceKm));
        const roundedRisk = Math.round(riskScore);
        const currentLang = getLanguage();

        let alertSpeech = "";
        if (currentLang === 'hi') {
          alertSpeech = isUrgent
            ? `चेतावनी। आगे तीव्र भूस्खलन का खतरा है। आप ${regionName} से मात्र ${roundedDistance} किलोमीटर दूर हैं। अनुमानित जोखिम ${roundedRisk} प्रतिशत है। तुरंत सुरक्षित स्थान खोजें।`
            : `चेतावनी। आगे उच्च भूस्खलन जोखिम क्षेत्र है। आप ${regionName} से लगभग ${roundedDistance} किलोमीटर की दूरी पर हैं। अनुमानित जोखिम ${roundedRisk} प्रतिशत है। कृपया वैकल्पिक मार्ग चुनें।`;
        } else if (currentLang === 'bn') {
          alertSpeech = `সতর্কবার্তা। সামনে উচ্চ ভূমিধসের ঝুঁকি। আপনি ${regionName} থেকে প্রায় ${roundedDistance} কিলোমিটার দূরে। আনুমানিক ঝুঁকি ${roundedRisk} শতাংশ। বিকল্প পথ ব্যবহার করুন।`;
        } else if (currentLang === 'ne') {
          alertSpeech = `चेतावनी। अगाडि पहिरोको उच्च जोखिम छ। तपाईं ${regionName} बाट लगभग ${roundedDistance} किलोमिटर टाढा हुनुहुन्छ। अनुमानित जोखिम ${roundedRisk} प्रतिशत छ। वैकल्पिक बाटो रोज्नुहोस्।`;
        } else {
          alertSpeech = isUrgent
            ? `Warning. Critical landslide danger ahead. You are only ${roundedDistance} kilometers from ${regionName}. Estimated risk is ${roundedRisk} percent. Please seek immediate shelter or turn back.`
            : `Warning. High landslide risk ahead. You are approximately ${roundedDistance} kilometers from ${regionName}. The estimated landslide risk is ${roundedRisk} percent. Please consider an alternative route and follow local safety advisories.`;
        }

        const utterance = new SpeechSynthesisUtterance(alertSpeech);
        utterance.rate = 0.92;
        utterance.pitch = 1.0;
        utterance.volume = 1.0;

        if (currentLang === 'hi') utterance.lang = 'hi-IN';
        else if (currentLang === 'bn') utterance.lang = 'bn-IN';
        else if (currentLang === 'ne') utterance.lang = 'ne-NP';
        else utterance.lang = 'en-IN';

        window.speechSynthesis.speak(utterance);
      } catch (err) {
        console.warn('[Emergency Audio] Travel speech error:', err);
      }
    }, 1100);
  }

  return true;
}

/**
 * Developer and SIH demo helper: Unconditionally triggers simulated travel voice warning.
 */
export function testTravelVoiceAlert() {
  return playTravelSafetyVoiceAlert({
    riskScore: 85,
    distanceKm: 9.2,
    regionName: 'Sonapur Tunnel Corridor (NH-06)',
    isUrgent: false,
    force: true
  });
}

