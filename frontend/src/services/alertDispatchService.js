/**
 * Disaster Alert Dispatch Service
 * Formats emergency alerts and manages multi-channel dispatch (WhatsApp, SMS, Telegram, NDMA Bulletin).
 */

export const RECIPIENT_AGENCIES = [
  { id: 'ALL', name: 'Combined Emergency Services Broadcast (All Agencies)', short: 'ALL AGENCIES' },
  { id: 'NDRF', name: 'National Disaster Response Force (1st & 12th Bns NER)', short: 'NDRF BNs' },
  { id: 'SDRF', name: 'State Disaster Response Force (State EOC)', short: 'STATE SDRF' },
  { id: 'DEOC', name: 'District Emergency Operation Center (District Magistrate)', short: 'DEOC / DM' },
  { id: 'BRO_POLICE', name: 'Border Roads Organisation (BRO) & Highway Traffic Police', short: 'BRO / POLICE' }
];

const DISPATCH_HISTORY_KEY = 'ner_disaster_dispatch_logs';

export function getDispatchHistory() {
  try {
    const raw = sessionStorage.getItem(DISPATCH_HISTORY_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

export function recordDispatch(entry) {
  try {
    const history = getDispatchHistory();
    const newEntry = {
      id: `DISP-${Date.now()}`,
      timestamp: new Date().toISOString(),
      ...entry
    };
    const updated = [newEntry, ...history].slice(0, 30);
    sessionStorage.setItem(DISPATCH_HISTORY_KEY, JSON.stringify(updated));
    return newEntry;
  } catch (err) {
    console.warn('Failed to save dispatch log to sessionStorage:', err);
    return null;
  }
}

export function formatEmergencyAlertText(data) {
  const {
    locationName = 'North Eastern Region (Monitored Coordinate)',
    lat,
    lng,
    warningLevel = 'ALERT',
    riskScore = null,
    rainfallMm = null,
    roadStatus = null,
    incidentTitle = null,
    targetAgency = 'ALL'
  } = data;

  const agencyObj = RECIPIENT_AGENCIES.find(a => a.id === targetAgency);
  const agencyName = agencyObj ? agencyObj.name : 'Emergency Response Units';
  const coordsStr = (lat !== undefined && lng !== undefined) ? `${Number(lat).toFixed(4)}°N, ${Number(lng).toFixed(4)}°E` : 'Coordinates Pending';

  const riskStr = riskScore !== null ? `${Math.round(riskScore)}%` : 'Active Elevation Risk';
  const rainStr = rainfallMm !== null ? `${Number(rainfallMm).toFixed(1)} mm (24h telemetry)` : 'Heavy precipitation ongoing';
  const roadStr = roadStatus || 'Corridor transit monitoring recommended';

  let alertHeader = '⚠️ HIGH-PRIORITY DISASTER ALERT';
  if (warningLevel === 'EMERGENCY' || warningLevel === 'CRITICAL') {
    alertHeader = '🚨 CRITICAL DISASTER EMERGENCY ALERT';
  } else if (warningLevel === 'WATCH') {
    alertHeader = '⚡ DISASTER WATCH ADVISORY';
  }

  return (
`${alertHeader}
=============================
ATTN: ${agencyName}
SYSTEM: NER Landslide Risk Early Warning Network

● STATUS: ${warningLevel} (Composite Risk: ${riskStr})
● TARGET AREA: ${locationName}
● COORDINATES: ${coordsStr}
● 24H RAINFALL: ${rainStr}
● ROAD CONGESTION / ACCESS: ${roadStr}
${incidentTitle ? `● FIELD OBSERVATION: ${incidentTitle}\n` : ''}
ACTION DIRECTIVES:
1. Mobilize regional disaster assessment teams.
2. Monitor vulnerable highway cuts and slope catchments.
3. Alert local Panchayats and public traffic control.
4. Keep emergency rescue gear and earth-movers on standby.

Emergency Helpline: 1070 (State EOC) / 1077 (District EOC)
Automated Dispatch Timestamp: ${new Date().toLocaleString('en-IN', { timeZone: 'Asia/Kolkata' })} IST`
  );
}

export function formatWhatsAppUrl(alertText, phoneNumber = '') {
  const cleanPhone = phoneNumber.replace(/[^0-9]/g, '');
  const encoded = encodeURIComponent(alertText);
  return cleanPhone 
    ? `https://api.whatsapp.com/send?phone=${cleanPhone}&text=${encoded}`
    : `https://api.whatsapp.com/send?text=${encoded}`;
}

export function formatSmsUrl(alertText, phoneNumber = '') {
  const cleanPhone = phoneNumber.replace(/[^0-9]/g, '');
  const encoded = encodeURIComponent(alertText);
  return cleanPhone 
    ? `sms:${cleanPhone}?body=${encoded}`
    : `sms:?body=${encoded}`;
}

export function formatNdmaBulletin(data) {
  const {
    locationName = 'North Eastern Region (NER)',
    lat,
    lng,
    warningLevel = 'ALERT',
    riskScore = null,
    rainfallMm = null,
    slopeDeg = null,
    roadStatus = null
  } = data;

  const now = new Date();
  const bulletinId = `NDMA-NER-${now.getFullYear()}${String(now.getMonth()+1).padStart(2,'0')}${String(now.getDate()).padStart(2,'0')}-${Math.floor(1000 + Math.random() * 9000)}`;

  return (
`OFFICIAL SITUATION BULLETIN — NATIONAL DISASTER SURVEILLANCE
BULLETIN REF: ${bulletinId}
ISSUED BY: NORTH EASTERN REGION EARLY WARNING COMMAND
DATE/TIME: ${now.toISOString()} (${now.toLocaleTimeString('en-IN')} IST)
----------------------------------------------------------------------
1. REGIONAL THREAT MATRIX
   - Location Reference: ${locationName}
   - Geographic Coordinates: ${lat ? Number(lat).toFixed(6) : 'N/A'} N, ${lng ? Number(lng).toFixed(6) : 'N/A'} E
   - Early Warning Tier: ${warningLevel}
   - Composite Hazard Index: ${riskScore !== null ? `${Math.round(riskScore)} / 100` : 'Assessing'}

2. METEOROLOGICAL & GEOTECHNICAL TELEMETRY
   - Antecedent 24h Precipitation: ${rainfallMm !== null ? `${rainfallMm} mm` : 'Monitored'}
   - Terrain Slope: ${slopeDeg !== null ? `${slopeDeg}°` : 'Steep Terrain (>25°)'}
   - Critical Road Infrastructure: ${roadStatus || 'Trans-NER Highway Sector'}

3. PRECAUTIONARY STANDBY ORDERS
   - NDRF / SDRF: Stage 1 mobilization on standby for immediate debris-clearing.
   - Traffic Police: Restrict heavy vehicular transit along saturated slope segments.
   - Public Advisory: Disseminate caution via local administrative channels.
----------------------------------------------------------------------
APPROVED FOR TRANSMISSION VIA NER LANDSLIDE INTELLIGENCE PLATFORM`
  );
}
