/**
 * Offline Emergency Shelter, First-Aid & 2G SMS Service
 * 100% Client-side bundled knowledge base that operates with ZERO mobile data / internet.
 */

import { VERIFIED_REGIONAL_FACILITIES } from './emergencyFacilitiesData';

// Mountain Landslide Survival & First-Aid Knowledge Base
export const MOUNTAIN_SURVIVAL_GUIDELINES = [
  {
    id: 'escape-protocol',
    title: 'Immediate Mountain Landslide Escape',
    category: 'IMMEDIATE_ACTION',
    badge: 'Urgent Life Safety',
    summary: 'What to do the second you hear ground rumbling or see tree tilt.',
    steps: [
      'Listen for unusual sounds: cracking trees, falling boulders, or a deep freight-train roar.',
      'DO NOT flee downstream or down-valley. Mudflows and debris surges accelerate along drainage channels.',
      'Move uphill and sideways onto bedrock ridges or stable slope shoulders away from natural gullies.',
      'If trapped inside a vehicle, unbuckle immediately. If vehicle is being shifted by mud, escape out the uphill side door or window.',
      'If escape is impossible, curl into a tight ball shielding your head, neck, and chest behind solid bedrock.'
    ]
  },
  {
    id: 'trauma-crush-care',
    title: 'Crush Injury & Trauma First-Aid',
    category: 'MEDICAL_CARE',
    badge: 'First-Aid Protocol',
    summary: 'Emergency stabilization for debris strikes, fractures, and severe bleeding.',
    steps: [
      'Severe Bleeding: Apply firm, continuous direct pressure using sterile gauze, clean clothing, or a scarf. Elevate the wounded limb above heart level.',
      'Crush Injury Management: If a limb is pinned under a rock/tree for >15 minutes, prepare for sudden toxin release upon removal. Keep victim hydrated with clean water if conscious.',
      'Bone Fracture Splinting: Immobilize joints above and below the fracture using straight branches, rolled jackets, or trekking poles secured with strips of cloth.',
      'Spinal & Neck Precaution: If a victim fell down a slope, assume neck/spine injury. DO NOT move them unless active rockfall directly threatens their position.'
    ]
  },
  {
    id: 'hypothermia-shelter',
    title: 'Mountain Ridge Hypothermia & Exposure',
    category: 'SHELTER_SURVIVAL',
    badge: 'Weather Protection',
    summary: 'Surviving cold monsoonal nights stranded on North Eastern ridges (1000m - 2800m).',
    steps: [
      'Get off the wet ground: Insulate yourself from cold soil using dry leaves, vehicle floor mats, tree boughs, or rucksacks.',
      'Emergency Windbreak: Erect tarpaulins or vehicle seat covers facing away from prevailing mountain wind against an overhanging rock scarp.',
      'Layering: Squeeze excess water from clothing. Wrap core torso in plastic bags or emergency foil blankets beneath outer rain jackets to trap body heat.',
      'Huddle Protocol: If stranded in a group, sit back-to-back in a tight circle to conserve mutual body heat. Never sleep directly on bare mud.'
    ]
  },
  {
    id: 'zero-internet-signaling',
    title: 'Signaling Search Teams (Zero 4G / 5G Data)',
    category: 'RESCUE_SIGNALING',
    badge: '2G / Acoustic Signaling',
    summary: 'Guiding NDRF, SDRF, BRO, and air rescue units without cellular internet.',
    steps: [
      'Acoustic Distress Code: 3 loud whistle blasts or horn honks, pause 1 minute, repeat 3 blasts. Rescuers acknowledge with 2 blasts.',
      'High-Visibility Ground Marker: Lay bright orange, red, or white fabrics in a large "V" (Requires Assistance) or "X" (Require Medical) on an open ridge for helicopters.',
      'Night Signaling: Flash a torch or vehicle headlights in groups of 3 flashes. Conserve vehicle battery by running headlights only on schedule (top of each hour).',
      'Mirror Reflection: On cloudy breaks, direct compact mirror or phone screen flashes toward rescue drones or observation towers.'
    ]
  }
];

// Pre-configured government emergency dispatch lines
export const EMERGENCY_SMS_TARGETS = [
  {
    number: '112',
    name: 'National Emergency Response (ERSS 112)',
    badge: '24/7 National Dispatch',
    priority: 'PRIMARY'
  },
  {
    number: '1070',
    name: 'State Disaster Management EOC',
    badge: 'State Disaster EOC',
    priority: 'STATE'
  },
  {
    number: '1077',
    name: 'District Disaster Control Center',
    badge: 'District Magistrate',
    priority: 'DISTRICT'
  }
];

/**
 * Builds a standardized GSM-compatible SMS emergency distress payload.
 * Formatted cleanly under 160 characters (or multi-part GSM-7) for 2G cellular towers.
 */
export function buildEmergencySmsPayload(data = {}) {
  const {
    lat,
    lng,
    sectorName = 'North Eastern Mountain Corridor',
    state = 'North East India',
    incidentType = 'LANDSLIDE_BLOCKAGE',
    personsAffected = 1,
    injuries = 0,
    additionalNote = ''
  } = data;

  const latStr = lat ? Number(lat).toFixed(4) : 'UNKNOWN';
  const lngStr = lng ? Number(lng).toFixed(4) : 'UNKNOWN';

  const typeLabels = {
    LANDSLIDE_BLOCKAGE: 'Active Landslide / Road Blocked',
    VEHICLE_STRANDED: 'Vehicles Stranded on Mountain Pass',
    MEDICAL_EMERGENCY: 'Casualties / Urgent Medical Need',
    FLASH_FLOOD: 'River Surge / Flash Flood Cutoff'
  };

  const situation = typeLabels[incidentType] || 'Landslide Emergency';

  return `[EMERGENCY SOS - NER RESCUE]
Loc: ${sectorName}, ${state}
GPS: ${latStr}N, ${lngStr}E
Situation: ${situation}
Persons: ${personsAffected} | Injuries: ${injuries}
${additionalNote ? `Note: ${additionalNote}\n` : ''}Need urgent SAR / Clearance dispatch.
Sent via NER Safety Portal`.trim();
}

/**
 * Generates mobile cross-platform SMS URI string.
 * Android standard: sms:<number>?body=<encoded_text>
 * iOS fallback compatible: sms:<number>&body=<encoded_text>
 */
export function generateSmsUri(number, bodyText) {
  const isIOS = typeof navigator !== 'undefined' && /iPad|iPhone|iPod/.test(navigator.userAgent);
  const separator = isIOS ? '&' : '?';
  return `sms:${number}${separator}body=${encodeURIComponent(bodyText)}`;
}

/**
 * Filter verified emergency facilities by state or type offline.
 */
export function getOfflineFacilitiesByState(stateFilter = 'ALL', typeFilter = 'ALL') {
  return VERIFIED_REGIONAL_FACILITIES.filter(fac => {
    const matchState = stateFilter === 'ALL' || fac.state.toLowerCase() === stateFilter.toLowerCase();
    const matchType = typeFilter === 'ALL' || fac.type === typeFilter;
    return matchState && matchType;
  });
}
