/**
 * NER Multilingual Internationalization (i18n) Service
 * Provides native bridge language support across the 8 North Eastern Region states:
 * - English: Universal government / education / inter-tribal lingua franca (Official in NL, MZ, ML)
 * - Assamese (অসমীয়া): Largest native language in NER, widely used for trade in Arunachal and Nagaland
 * - Hindi (हिन्दी): Widely taught in schools, commerce, tourism, Arunachali Hindi bridge language
 * - Bengali (বাংলা): Official in Tripura, widely spoken in Barak Valley of Assam
 * - Nagamese: Crucial pidgin lingua franca allowing Nagaland's 16+ tribes to communicate
 * - Nepali (नेपाली): Official in Sikkim, dominant lingua franca across Sikkim and hill tracts
 */

import { useState, useEffect } from 'react';

export const SUPPORTED_LANGUAGES = [
  {
    code: 'en',
    name: 'English',
    native: 'English',
    status: 'Official in NL, MZ, ML',
    bridgeRole: 'Universal language for government, signs & inter-tribal connection'
  },
  {
    code: 'as',
    name: 'Assamese',
    native: 'অসমীয়া',
    status: 'Official in Assam',
    bridgeRole: 'Largest native language; used for trade in Arunachal & Nagaland'
  },
  {
    code: 'hi',
    name: 'Hindi',
    native: 'हिन्दी',
    status: 'Pan-NER Commerce',
    bridgeRole: 'Used for commerce, tourism & Arunachali Hindi bridge dialect'
  },
  {
    code: 'bn',
    name: 'Bengali',
    native: 'বাংলা',
    status: 'Official in Tripura',
    bridgeRole: 'Majority in Tripura & widely spoken in Barak Valley of Assam'
  },
  {
    code: 'nag',
    name: 'Nagamese',
    native: 'Nagamese',
    status: 'Spoken across Nagaland',
    bridgeRole: 'Crucial bridge pidgin connecting Nagaland\'s 16+ distinct tribes'
  },
  {
    code: 'ne',
    name: 'Nepali',
    native: 'नेपाली',
    status: 'Official in Sikkim',
    bridgeRole: 'Dominant lingua franca across Sikkim and hill tracts of Assam'
  }
];

const LANG_STORAGE_KEY = 'ner_preferred_language';
const languageListeners = new Set();

export function getLanguage() {
  try {
    const saved = localStorage.getItem(LANG_STORAGE_KEY);
    if (saved && SUPPORTED_LANGUAGES.some(l => l.code === saved)) {
      return saved;
    }
  } catch {}
  return 'en';
}

export function setLanguage(code) {
  if (!SUPPORTED_LANGUAGES.some(l => l.code === code)) return;
  try {
    localStorage.setItem(LANG_STORAGE_KEY, code);
  } catch {}
  languageListeners.forEach(fn => {
    try {
      fn(code);
    } catch {}
  });
  return code;
}

export function subscribeLanguage(callback) {
  languageListeners.add(callback);
  return () => languageListeners.delete(callback);
}

/**
 * React Hook to access current language and translation helper
 */
export function useTranslation() {
  const [lang, setLang] = useState(getLanguage());

  useEffect(() => {
    return subscribeLanguage(newLang => {
      setLang(newLang);
    });
  }, []);

  return {
    lang,
    setLang: (code) => setLanguage(code),
    t: (key, fallback) => t(key, fallback, lang),
    languages: SUPPORTED_LANGUAGES
  };
}

export const TRANSLATIONS = {
  // English (Universal Default)
  en: {
    // Header & Brand
    system_title: 'NER Landslide Risk Monitoring',
    system_sub: 'North Eastern Space Applications & Disaster Management',
    gov_seal: 'Government of India · NDMA · North Eastern Council',
    helpline_title: 'Helpline: 1070',
    alarm_active: 'Alarm ON',
    alarm_muted: 'Muted',
    light_mode: 'Light',
    dark_mode: 'Dark',
    logout_btn: 'Logout',
    select_language: 'Select Language',
    language: 'Language',

    // Landing Page / Auth
    citizen_portal_tab: 'Citizen Safety Portal',
    admin_portal_tab: 'Official Admin Login',
    citizen_portal_subtitle: 'Public Citizen Safety Network',
    citizen_portal_desc: 'Access interactive regional landslide maps, rainfall telemetry, and submit community hazard reports.',
    admin_portal_subtitle: 'Disaster Authority & Incident Command',
    admin_portal_desc: 'Secure sign-in for Incident Commanders, District Magistrates, NDRF coordinators, and BRO officers.',
    restricted_access_badge: 'Restricted Access · Authorized Personnel Only',
    sign_in_tab: 'User Sign In',
    register_tab: 'Register New Citizen',
    full_name_label: 'Full Name',
    email_label: 'Registered Email Address',
    password_label: 'Password',
    phone_label: 'Mobile Number (for SMS Alerts)',
    state_label: 'Resident State',
    sign_in_button: 'Enter Citizen Safety Portal',
    register_button: 'Create Citizen Account & Enter',
    admin_login_button: 'Authenticate Commander Access',
    demo_credentials_title: '1-Click Verification Test Credentials:',
    citizen_demo_tag: 'Pema Tashi (Citizen)',
    admin_demo_tag: 'Col. Sanjeev Roy (Admin)',

    // Citizen Advisory Card & Telemetry
    public_safety_guide: 'Public Safety Guide',
    ner_hill_corridors: 'North Eastern Hill Slopes & Highways',
    select_location_heading: 'Select Any Location to Inspect Landslide & Highway Safety',
    select_location_subtext: 'Click anywhere on the interactive map above or search your town / highway corridor. You will immediately receive live landslide threat levels, 24h & 72h rainfall measurements, road clearance status, nearest emergency shelters, and verified government helplines.',
    select_corridor_prompt: 'Select a Critical Mountain Highway Corridor to Inspect:',
    red_alert_title: 'CRITICAL RED ALERT: LIFE SAFETY WARNING',
    red_alert_desc: 'Severe landslide hazard detected across this mountain corridor. Saturated slope cut, active rockfall potential, and heavy rainfall threshold breached. Non-essential vehicular transit is strictly discouraged.',
    warning_title: 'WARNING: HIGH LANDSLIDE SUSCEPTIBILITY',
    normal_title: 'NORMAL: MOUNTAIN CORRIDOR STABLE',
    dial_helpline: 'Helpline: 1070',
    shelter_btn: 'Nearest Shelters',
    sound_on: 'Sound ON',
    sound_muted_btn: 'Muted',
    dismiss_btn: 'Dismiss',
    share_advisory: 'Share Safety Advisory',
    advisory_copied: 'Advisory Copied!',
    report_hazard: 'Report Landslide Hazard',
    rainfall_24h: '24h Rainfall',
    rainfall_72h: '72h Infiltration',
    elevation_m: 'Elevation',
    slope_angle: 'Slope Angle',
    soil_saturation: 'Soil Saturation',
    highway_status: 'Highway Status',
    status_blocked: 'BLOCKED BY DEBRIS',
    status_at_risk: 'SLOW / CAUTION',
    status_clear: 'CLEAR & OPEN',
    tab_advisory: 'Advisory',
    tab_roads: 'Road Lifelines',
    tab_shelters: 'Shelters & Trauma',
    tab_safety_tips: 'Safety Guidelines',
    hospitals_trauma: 'Verified Emergency Hospitals & Trauma Units',
    public_shelters: 'Public Emergency Relief Shelters',
    bro_detachments: 'Border Roads Organisation (BRO) Clearance Bases',
    police_patrol: 'Highway Police Patrol Outposts',
    direct_call: 'Emergency Call',

    // Outside NER Coverage Notice
    outside_ner_title: 'Selected Region is Outside North Eastern Region',
    outside_ner_badge: 'OUT OF MONITORING COVERAGE',
    outside_ner_desc: 'The selected coordinates lie outside India\'s North Eastern Region (NER). This early warning portal specifically monitors landslide hazards, satellite InSAR radar deformation, and emergency relief across the 8 North Eastern states (Assam, Arunachal Pradesh, Manipur, Meghalaya, Mizoram, Nagaland, Sikkim, and Tripura).',
    outside_ner_states_covered: '8 Monitored States: Assam, Arunachal Pradesh, Meghalaya, Manipur, Mizoram, Nagaland, Sikkim, Tripura',
    outside_ner_prompt: 'Please select a monitored North Eastern mountain corridor below to inspect live hazard data:',
    outside_ner_clear: 'Clear Map Selection',

    // Voice Alert Phrase
    audio_alert_phrase: 'Warning: Critical landslide hazard alert in this sector. Travel is not advised.'
  },

  // Assamese (অসমীয়া - Official in Assam; trade lingua franca in Arunachal & Nagaland)
  as: {
    system_title: 'উত্তৰ-পূব ভূমিস্খলন নিৰীক্ষণ প্ৰণালী',
    system_sub: 'উত্তৰ-পূব মহাকাশ প্ৰয়োগ কেন্দ্ৰ আৰু দুৰ্যোগ ব্যৱস্থাপনা',
    gov_seal: 'ভাৰত চৰকাৰ · এনডিএমএ · উত্তৰ-পূব পৰিষদ',
    helpline_title: 'হেল্পলাইন: ১০৭০',
    alarm_active: 'এলাৰ্ম অন',
    alarm_muted: 'শব্দহীন',
    light_mode: 'দিনৰ পোহৰ',
    dark_mode: 'নিশাৰ দৃশ্য',
    logout_btn: 'লগআউট',
    select_language: 'ভাষা বাছক',
    language: 'ভাষা',

    citizen_portal_tab: 'নাগৰিক সুৰক্ষা পোৰ্টেল',
    admin_portal_tab: 'চৰকাৰী বিষয়াৰ প্ৰৱেশ',
    citizen_portal_subtitle: 'ৰাজহুৱা নাগৰিক সুৰক্ষা নেটৱৰ্ক',
    citizen_portal_desc: 'উত্তৰ-পূৰ্বাঞ্চলৰ ইন্টাৰেক্টিভ ভূমিস্খলন মানচিত্ৰ, বৰষুণৰ তথ্য আৰু জৰুৰী সতৰ্কতা লাভ কৰক।',
    admin_portal_subtitle: 'দুৰ্যোগ ব্যৱস্থাপনা আৰু অভিযান কক্ষ',
    admin_portal_desc: 'জিলা উপায়ুক্ত, এনডিআৰএফ আৰু বিআৰঅ বিষয়াৰ সুৰক্ষিত প্ৰৱেশ।',
    restricted_access_badge: 'সংৰক্ষিত প্ৰৱেশ · কেৱল কৰ্তৃত্বপ্ৰাপ্ত বিষয়াৰ বাবে',
    sign_in_tab: 'নাগৰিক প্ৰৱেশ',
    register_tab: 'নতুন নাগৰিক পঞ্জীয়ন',
    full_name_label: 'সম্পূৰ্ণ নাম',
    email_label: 'পঞ্জীকৃত ইমেইল',
    password_label: 'পাছৱৰ্ড',
    phone_label: 'মবাইল নম্বৰ (এছএমএছ সতৰ্কতাৰ বাবে)',
    state_label: 'বাসস্থান ৰাজ্য',
    sign_in_button: 'সুৰক্ষা পোৰ্টেলত প্ৰৱেশ কৰক',
    register_button: 'নাগৰিক একাউণ্ট সৃষ্টি কৰক',
    admin_login_button: 'বিষয়া হিচাপে প্ৰৱেশ নিশ্চিত কৰক',
    demo_credentials_title: '১-ক্লিক পৰীক্ষামূলক একাউণ্ট:',
    citizen_demo_tag: 'পেমা তাশী (নাগৰিক)',
    admin_demo_tag: 'কৰ্ণেল সঞ্জীৱ ৰয় (বিষয়া)',

    public_safety_guide: 'ৰাজহুৱা সুৰক্ষা নিৰ্দেশনা',
    ner_hill_corridors: 'উত্তৰ-পূৰ্বাঞ্চলৰ পাহাৰীয়া পথ আৰু ঘাইপথ',
    select_location_heading: 'ভূমিস্খলন আৰু পথৰ সুৰক্ষা নিৰীক্ষণৰ বাবে স্থান বাছক',
    select_location_subtext: 'ওপৰৰ মানচিত্ৰত ক্লিক কৰক বা আপোনাৰ অঞ্চল সন্ধান কৰক। আপুনি তাৎক্ষণিকভাৱে বৰষুণ, পথৰ অৱস্থা আৰু নিকটৱৰ্তী আশ্ৰয় শিবিৰৰ তথ্য পাব।',
    select_corridor_prompt: 'গুৰুত্বপূৰ্ণ পাহাৰীয়া ঘাইপথ পৰিদৰ্শন কৰিবলৈ বাছক:',
    red_alert_title: 'জৰুৰীকালীন ৰঙা সংকেত: জীৱন সুৰক্ষা সতৰ্কবাণী',
    red_alert_desc: 'এই পাহাৰীয়া অঞ্চলত ভয়ংকৰ ভূমিস্খলনৰ সম্ভাৱনা ধৰা পৰিছে। প্ৰচণ্ড বৰষুণ আৰু মাটি খহি পৰাৰ সম্ভাৱনা বেছি। যান-বাহন চলাচল নকৰিবলৈ অনুৰোধ জনোৱা হৈছে।',
    warning_title: 'সতৰ্কবাণী: উচ্চ ভূমিস্খলন আশংকা',
    normal_title: 'স্বাভাৱিক: পাহাৰীয়া অঞ্চল স্থিৰ',
    dial_helpline: 'হেল্পলাইন: ১০৭০',
    shelter_btn: 'আশ্ৰয় শিবিৰ',
    sound_on: 'শব্দ অন',
    sound_muted_btn: 'শব্দহীন',
    dismiss_btn: 'বাতিল কৰক',
    share_advisory: 'সতৰ্কবাণী শ্বেয়াৰ কৰক',
    advisory_copied: 'অনুলিপি কৰা হ’ল!',
    report_hazard: 'ভূমিস্খলনৰ খবৰ দিয়ক',
    rainfall_24h: '২৪ ঘণ্টাৰ বৰষুণ',
    rainfall_72h: '৭২ ঘণ্টাৰ বৰষুণ',
    elevation_m: 'উচ্চতা',
    slope_angle: 'ঢালৰ কোণ',
    soil_saturation: 'মাটিৰ সংপৃক্ততা',
    highway_status: 'ঘাইপথৰ স্থিতি',
    status_blocked: 'আৱৰ্জনাৰে পথ বন্ধ',
    status_at_risk: 'ধীৰে চলোৱক / সতৰ্কতা',
    status_clear: 'খোলা আৰু নিৰাপদ',
    tab_advisory: 'পৰামৰ্শৱলী',
    tab_roads: 'পথ সংযোগ',
    tab_shelters: 'আশ্ৰয় আৰু চিকিৎসা',
    tab_safety_tips: 'সুৰক্ষা নিয়ম',
    hospitals_trauma: 'পৰীক্ষিত জৰুৰী চিকিৎসালয় আৰু ট্ৰমা ইউনিট',
    public_shelters: 'ৰাজহুৱা জৰুৰীকালীন আশ্ৰয় শিবিৰ',
    bro_detachments: 'বিআৰঅ’ (BRO) পথ পৰিষ্কাৰ শিবিৰ',
    police_patrol: 'ঘাইপথ আৰক্ষী চকী',
    direct_call: 'জৰুৰী ফোন কৰক',

    // Outside NER Coverage Notice
    outside_ner_title: 'নিৰ্বাচিত স্থান উত্তৰ-পূৰ্বাঞ্চলৰ বাহিৰত',
    outside_ner_badge: 'নিৰীক্ষণ পৰিসৰৰ বাহিৰত',
    outside_ner_desc: 'নিৰ্বাচিত স্থানাংক ভাৰতৰ উত্তৰ-পূৰ্বাঞ্চলৰ (NER) সীমাৰ বাহিৰত অৱস্থিত। এই ব্যৱস্থাই বিশেষভাৱে উত্তৰ-পূৰ্বাঞ্চলৰ ৮ খন ৰাজ্যৰ (অসম, অৰুণাচল, মণিপুৰ, মেঘালয়, মিজোৰাম, নাগালেণ্ড, ছিকিম আৰু ত্ৰিপুৰা) ভূমিস্খলন আৰু জৰুৰী সাহায্য নিৰীক্ষণ কৰে।',
    outside_ner_states_covered: '৮ খন নিৰীক্ষিত ৰাজ্য: অসম, অৰুণাচল প্ৰদেশ, মেঘালয়, মণিপুৰ, মিজোৰাম, নাগালেণ্ড, ছিকিম, ত্ৰিপুৰা',
    outside_ner_prompt: 'লাইভ তথ্য চাবলৈ তলত দিয়া উত্তৰ-পূৰ্বাঞ্চলৰ পাহাৰীয়া পথ বাছক:',
    outside_ner_clear: 'স্থান নিৰ্বাচন বাতিল কৰক',

    audio_alert_phrase: 'সতৰ্কবাণী: এই অঞ্চলত ভয়ংকৰ ভূমিস্খলনৰ সতৰ্কতা। ভ্ৰমণ নকৰিবলৈ পৰামৰ্শ দিয়া হৈছে।'
  },

  // Hindi (हिन्दी - Pan-NER Commerce, Tourism & Arunachali Hindi bridge)
  hi: {
    system_title: 'पूर्वोत्तर भूस्खलन जोखिम निगरानी प्रणाली',
    system_sub: 'उत्तर-पूर्वी अंतरिक्ष उपयोग केंद्र एवं आपदा प्रबंधन',
    gov_seal: 'भारत सरकार · राष्ट्रीय आपदा प्रबंधन प्राधिकरण (NDMA) · पूर्वोत्तर परिषद',
    helpline_title: 'हेल्पलाइन: 1070',
    alarm_active: 'अलार्म चालू',
    alarm_muted: 'म्यूट',
    light_mode: 'डे मोड',
    dark_mode: 'डार्क मोड',
    logout_btn: 'लॉगआउट',
    select_language: 'भाषा चुनें',
    language: 'भाषा',

    citizen_portal_tab: 'नागरिक सुरक्षा पोर्टल',
    admin_portal_tab: 'अधिकारी एडमिन लॉगिन',
    citizen_portal_subtitle: 'सार्वजनिक नागरिक सुरक्षा नेटवर्क',
    citizen_portal_desc: 'पहाड़ी क्षेत्रों के भूस्खलन मानचित्र, वर्षा टेलीमेट्री देखें और आपदा संबंधी रिपोर्ट दर्ज करें।',
    admin_portal_subtitle: 'आपदा प्रबंधन एवं नियंत्रण कक्ष',
    admin_portal_desc: 'कमांडरों, जिलाधिकारियों, एनडीआरएफ समन्वयकों और बीआरओ अधिकारियों के लिए सुरक्षित लॉगिन।',
    restricted_access_badge: 'प्रतिबंधित पहुंच · केवल अधिकृत अधिकारियों के लिए',
    sign_in_tab: 'नागरिक लॉगिन',
    register_tab: 'नया नागरिक पंजीकरण',
    full_name_label: 'पूरा नाम',
    email_label: 'पंजीकृत ईमेल पता',
    password_label: 'पासवर्ड',
    phone_label: 'मोबाइल नंबर (एसएमएस चेतावनी हेतु)',
    state_label: 'निवासी राज्य',
    sign_in_button: 'नागरिक सुरक्षा पोर्टल में प्रवेश करें',
    register_button: 'नागरिक खाता बनाएं और प्रवेश करें',
    admin_login_button: 'अधिकारी के रूप में लॉगिन करें',
    demo_credentials_title: '1-क्लिक परीक्षण खाता:',
    citizen_demo_tag: 'पेमा ताशी (नागरिक)',
    admin_demo_tag: 'कर्नल संजीव रॉय (एडमिन)',

    public_safety_guide: 'सार्वजनिक सुरक्षा निर्देशिका',
    ner_hill_corridors: 'पूर्वोत्तर पर्वतीय ढलान एवं राजमार्ग',
    select_location_heading: 'भूस्खलन एवं राजमार्ग सुरक्षा की जांच हेतु स्थान चुनें',
    select_location_subtext: 'मानचित्र पर किसी भी स्थान पर क्लिक करें या अपने शहर/राजमार्ग की खोज करें। आपको तुरंत वर्षा का स्तर, मार्ग की स्थिति, निकटतम आश्रय केंद्र और आपातकालीन हेल्पलाइन प्राप्त होगी।',
    select_corridor_prompt: 'जांच हेतु महत्वपूर्ण पर्वतीय राजमार्ग चुनें:',
    red_alert_title: 'अति गंभीर रेड अलर्ट: जीवन सुरक्षा चेतावनी',
    red_alert_desc: 'इस पर्वतीय मार्ग पर भीषण भूस्खलन का गंभीर खतरा है। अत्यधिक वर्षा से मिट्टी धंसने की आशंका है। गैर-जरूरी यात्रा पूरी तरह से वर्जित है।',
    warning_title: 'चेतावनी: भूस्खलन का उच्च जोखिम',
    normal_title: 'सामान्य: पर्वतीय मार्ग सुरक्षित',
    dial_helpline: 'हेल्पलाइन: 1070',
    shelter_btn: 'निकटतम आश्रय केंद्र',
    sound_on: 'ध्वनि चालू',
    sound_muted_btn: 'म्यूट',
    dismiss_btn: 'हटाएं',
    share_advisory: 'सुरक्षा चेतावनी साझा करें',
    advisory_copied: 'कॉपी कर लिया गया!',
    report_hazard: 'भूस्खलन की सूचना दें',
    rainfall_24h: '24 घंटे की वर्षा',
    rainfall_72h: '72 घंटे की संचयी वर्षा',
    elevation_m: 'ऊंचाई',
    slope_angle: 'ढलान कोण',
    soil_saturation: 'मिट्टी संतृप्ति',
    highway_status: 'राजमार्ग की स्थिति',
    status_blocked: 'मलबे से मार्ग अवरुद्ध',
    status_at_risk: 'धीमी गति / सतर्क रहें',
    status_clear: 'खुला एवं सुरक्षित',
    tab_advisory: 'सलाह / चेतावनी',
    tab_roads: 'सड़क कनेक्टिविटी',
    tab_shelters: 'आश्रय एवं अस्पताल',
    tab_safety_tips: 'सुरक्षा नियम',
    hospitals_trauma: 'प्रमाणित आपातकालीन अस्पताल एवं ट्रॉमा यूनिट',
    public_shelters: 'सार्वजनिक आपातकालीन राहत आश्रय केंद्र',
    bro_detachments: 'सीमा सड़क संगठन (BRO) मार्ग निकासी केंद्र',
    police_patrol: 'राजमार्ग पुलिस गश्ती चौकी',
    direct_call: 'तुरंत कॉल करें',

    // Outside NER Coverage Notice
    outside_ner_title: 'चयनित क्षेत्र उत्तर-पूर्वी क्षेत्र (NER) के बाहर है',
    outside_ner_badge: 'निगरानी क्षेत्र के बाहर',
    outside_ner_desc: 'चयनित निर्देशांक भारत के उत्तर-पूर्वी क्षेत्र (NER) की सीमा से बाहर हैं। यह अर्ली वार्निंग पोर्टल विशेष रूप से पूर्वोत्तर के 8 राज्यों (असम, अरुणाचल प्रदेश, मणिपुर, मेघालय, मिजोरम, नागालैंड, सिक्किम और त्रिपुरा) के भूस्खलन और आपदा राहत की निगरानी करता है।',
    outside_ner_states_covered: '8 निगरानी वाले राज्य: असम, अरुणाचल प्रदेश, मेघालय, मणिपुर, मिजोरम, नागालैंड, सिक्किम, त्रिपुरा',
    outside_ner_prompt: 'लाइव डेटा देखने हेतु नीचे दिए गए पूर्वोत्तर के मुख्य पर्वतीय मार्ग को चुनें:',
    outside_ner_clear: 'चयन रद्द करें',

    audio_alert_phrase: 'चेतावनी: इस क्षेत्र में गंभीर भूस्खलन का खतरा है। यात्रा न करने की सलाह दी जाती है।'
  },

  // Bengali (বাংলা - Official in Tripura; majority in Barak Valley of Assam)
  bn: {
    system_title: 'উত্তর-পূর্ব ভূমিধস ঝুঁকি পর্যবেক্ষণ ব্যবস্থা',
    system_sub: 'উত্তর-পূর্ব মহাকাশ প্রয়োগ কেন্দ্র ও দুর্যোগ ব্যবস্থাপনা',
    gov_seal: 'ভারত সরকার · এনডিএমএ · উত্তর-পূর্ব পরিষদ',
    helpline_title: 'হেল্পলাইন: ১০৭০',
    alarm_active: 'অ্যালার্ম চালু',
    alarm_muted: 'নীরব',
    light_mode: 'দিন',
    dark_mode: 'রাত',
    logout_btn: 'লগআউট',
    select_language: 'ভাষা নির্বাচন করুন',
    language: 'ভাষা',

    citizen_portal_tab: 'নাগরিক সুরক্ষা পোর্টাল',
    admin_portal_tab: 'অফিসিয়াল অ্যাডমিন লগইন',
    citizen_portal_subtitle: 'সর্বসাধারণের নাগরিক সুরক্ষা নেটওয়ার্ক',
    citizen_portal_desc: 'উত্তর-পূর্বাঞ্চলের ইন্টারেক্টিভ ভূমিধসের মানচিত্র, বৃষ্টিপাতের তথ্য ও সতর্কতা পর্যবেক্ষণ করুন।',
    admin_portal_subtitle: 'দুর্যোগ ব্যবস্থাপনা ও কমান্ড সেন্টার',
    admin_portal_desc: 'জেলা শাসক, এনডিআরএফ ও বিআরও আধিকারিকদের সুরক্ষিত প্রবেশাধিকার।',
    restricted_access_badge: 'সুরক্ষিত অ্যাক্সেস · কেবলমাত্র অনুমোদিত কর্মকর্তাদের জন্য',
    sign_in_tab: 'নাগরিক লগইন',
    register_tab: 'নতুন নাগরিক নিবন্ধন',
    full_name_label: 'সম্পূর্ণ নাম',
    email_label: 'নিবন্ধিত ইমেল ঠিকানা',
    password_label: 'পাসওয়ার্ড',
    phone_label: 'মোবাইল নম্বর (এসএমএস সতর্কতার জন্য)',
    state_label: 'বসবাসের রাজ্য',
    sign_in_button: 'নাগরিক পোর্টালে প্রবেশ করুন',
    register_button: 'অ্যাকাউন্ট তৈরি করে প্রবেশ করুন',
    admin_login_button: 'কর্মকর্তা হিসেবে লগইন নিশ্চিত করুন',
    demo_credentials_title: '১-ক্লিক পরীক্ষামূলক অ্যাকাউন্ট:',
    citizen_demo_tag: 'পেমা তাশি (নাগরিক)',
    admin_demo_tag: 'কর্নেল সঞ্জীব রায় (অ্যাডমিন)',

    public_safety_guide: 'জনসাধারণের সুরক্ষা নির্দেশিকা',
    ner_hill_corridors: 'উত্তর-পূর্ব পাহাড়ি ঢাল ও মহাসড়ক',
    select_location_heading: 'ভূমিধস ও মহাসড়কের সুরক্ষা যাচাই করতে স্থান নির্বাচন করুন',
    select_location_subtext: 'মানচিত্রে যেকোনো স্থানে ক্লিক করুন বা আপনার এলাকা অনুসন্ধান করুন। সাথে সাথে বৃষ্টিপাতের পরিমাণ, রাস্তার পরিস্থিতি এবং নিকটবর্তী ত্রাণ শিবিরের তথ্য পাবেন।',
    select_corridor_prompt: 'গুরুত্বপূর্ণ পাহাড়ি মহাসড়ক পর্যবেক্ষণ করতে নির্বাচন করুন:',
    red_alert_title: 'জরুরি লাল সংকেত: জীবন সুরক্ষা সতর্কতা',
    red_alert_desc: 'এই পাহাড়ি অঞ্চলে মারাত্মক ভূমিধসের আশঙ্কা দেখা দিয়েছে। অতিবৃষ্টির কারণে পাহাড় ধসের সম্ভাবনা অত্যন্ত প্রবল। জরুরি প্রয়োজন ছাড়া যাতায়াত না করার পরামর্শ দেওয়া হচ্ছে।',
    warning_title: 'সতর্কতা: উচ্চ ভূমিধস ঝুঁকি',
    normal_title: 'স্বাভাবিক: পাহাড়ি পথ স্থিতিশীল',
    dial_helpline: 'হেল্পলাইন: ১০৭০',
    shelter_btn: 'নিকটবর্তী আশ্রয়কেন্দ্র',
    sound_on: 'শব্দ চালু',
    sound_muted_btn: 'নীরব',
    dismiss_btn: 'বন্ধ করুন',
    share_advisory: 'সতর্কবার্তা শেয়ার করুন',
    advisory_copied: 'অনুলিপি করা হয়েছে!',
    report_hazard: 'ভূমিধসের তথ্য দিন',
    rainfall_24h: '২৪ ঘণ্টার বৃষ্টিপাত',
    rainfall_72h: '৭২ ঘণ্টার বৃষ্টিপাত',
    elevation_m: 'উচ্চতা',
    slope_angle: 'ঢালের কোণ',
    soil_saturation: 'মাটির আর্দ্রতা',
    highway_status: 'মহাসড়কের অবস্থা',
    status_blocked: 'ধ্বংসস্তূপে পথ অবরুদ্ধ',
    status_at_risk: 'ধীরে চলুন / সতর্ক থাকুন',
    status_clear: 'খোলা ও নিরাপদ',
    tab_advisory: 'পরামর্শ',
    tab_roads: 'সড়ক যোগাযোগ',
    tab_shelters: 'আশ্রয় ও চিকিৎসা',
    tab_safety_tips: 'সুরক্ষা নির্দেশিকা',
    hospitals_trauma: 'যাচাইকৃত জরুরি হাসপাতাল ও ট্রমা ইউনিট',
    public_shelters: 'জরুরি ত্রাণ ও আশ্রয়কেন্দ্র',
    bro_detachments: 'বর্ডার রোডস অর্গানাইজেশন (BRO) ক্যাম্প',
    police_patrol: 'হাইওয়ে পুলিশ ফাঁড়ি',
    direct_call: 'জরুরি কল করুন',

    // Outside NER Coverage Notice
    outside_ner_title: 'নির্বাচিত স্থানটি উত্তর-পূর্ব অঞ্চলের (NER) বাইরে',
    outside_ner_badge: 'পর্যবেক্ষণ সীমার বাইরে',
    outside_ner_desc: 'নির্বাচিত স্থানাঙ্ক ভারতের উত্তর-পূর্ব অঞ্চলের (NER) সীমার বাইরে অবস্থিত। এই ব্যবস্থা বিশেষভাবে উত্তর-পূর্বের ৮টি রাজ্য (আসাম, অরুণাচল প্রদেশ, মণিপুর, মেঘালয়, মিজোরাম, নাগাল্যান্ড, সিকিম ও ত্রিপুরা) পর্যবেক্ষণ ও জরুরি ত্রাণ সেবা প্রদান করে।',
    outside_ner_states_covered: '৮টি পর্যবেক্ষিত রাজ্য: আসাম, অরুণাচল প্রদেশ, মেঘালয়, মণিপুর, মিজোরাম, নাগাল্যান্ড, সিকিম, ত্রিপুরা',
    outside_ner_prompt: 'লাইভ তথ্য দেখতে নিচে দেওয়া উত্তর-পূর্বের পাহাড়ি পথ নির্বাচন করুন:',
    outside_ner_clear: 'নির্বাচন মুছুন',

    audio_alert_phrase: 'সতর্কবার্তা: এই অঞ্চলে মারাত্মক ভূমিধসের সতর্কতা জারি করা হয়েছে। ভ্রমণ না করার পরামর্শ দেওয়া হচ্ছে।'
  },

  // Nagamese (Inter-Tribal Bridge Lingua Franca spoken across Nagaland's 16+ tribes)
  nag: {
    system_title: 'NER Pahar Mati Giribole Monitoring System',
    system_sub: 'North Eastern Space Applications & Disaster Management',
    gov_seal: 'Government of India · NDMA · North Eastern Council',
    helpline_title: 'Helpline: 1070',
    alarm_active: 'Alarm Chalu Asey',
    alarm_muted: 'Awaz Bandh',
    light_mode: 'Din Laga Light',
    dark_mode: 'Raati Laga Mode',
    logout_btn: 'Logout',
    select_language: 'Bhasha Chunibi',
    language: 'Bhasha',

    citizen_portal_tab: 'Nagaland & NER Manu Laga Portal',
    admin_portal_tab: 'Official Commander Login',
    citizen_portal_subtitle: 'Manu Khan Laga Safety Network',
    citizen_portal_desc: 'Pahar rasta, boroshun ketiya ase, aru landslide report submit kuribole eitu use kuribi.',
    admin_portal_subtitle: 'Disaster Authority & Control Room',
    admin_portal_desc: 'DC, NDRF, Police aru BRO official khan karne secure sign-in.',
    restricted_access_badge: 'Official Manu Karne Matro · Private Access',
    sign_in_tab: 'Manu Login',
    register_tab: 'Notun Account Khulibi',
    full_name_label: 'Apuni Laga Pura Naam',
    email_label: 'Registered Email Address',
    password_label: 'Password',
    phone_label: 'Mobile Number (SMS Alert Karne)',
    state_label: 'Apuni Kon State Te Thake',
    sign_in_button: 'Safety Portal Te Ghusibi',
    register_button: 'Account Bonai Kena Ghusibi',
    admin_login_button: 'Commander Login Confirm Kuribi',
    demo_credentials_title: '1-Click Test Account:',
    citizen_demo_tag: 'Pema Tashi (Citizen)',
    admin_demo_tag: 'Col. Sanjeev Roy (Admin)',

    public_safety_guide: 'Manu Khan Nimite Safety Rules',
    ner_hill_corridors: 'North East Pahar Rasta & Highway',
    select_location_heading: 'Landslide Aru Highway Check Kuribole Jaga Select Kuribi',
    select_location_subtext: 'Map te click kuribi ba apuni laga town search kuribi. Apuni boroshun kiman girise, rasta bandh asey naki, aru usor shelter kote asey joldi janibo.',
    select_corridor_prompt: 'Check kuribole pahar highway corridor select kuribi:',
    red_alert_title: 'DANGOR RED ALERT: JAAN BACHABOLE WARNING',
    red_alert_desc: 'Eitu pahar rasta te bishi dangor landslide giribole chance asey. Mati puro gila hoi kena pathor guri giribo pare. Bishi dorkar nathakile gari loikena travel nakuribi.',
    warning_title: 'WARNING: LANDSLIDE LAGA DANGER ASEY',
    normal_title: 'NORMAL: RASTA SAFE ASEY',
    dial_helpline: 'Helpline: 1070',
    shelter_btn: 'Usor Laga Shelter',
    sound_on: 'Awaz Chalu',
    sound_muted_btn: 'Awaz Bandh',
    dismiss_btn: 'Hatai Dibi',
    share_advisory: 'Safety Alert Share Kuribi',
    advisory_copied: 'Copy Hoise!',
    report_hazard: 'Landslide Laga Khabar Dibi',
    rainfall_24h: '24 Ghonta Boroshun',
    rainfall_72h: '72 Ghonta Boroshun',
    elevation_m: 'Pahar Laga Height',
    slope_angle: 'Pahar Khara Angle',
    soil_saturation: 'Mati Gilap Percentage',
    highway_status: 'Rasta Laga Halat',
    status_blocked: 'Mati Girikena RASTA BONDH',
    status_at_risk: 'SLOW CHALABI / DANGER ASEY',
    status_clear: 'RASTA KHULA & SAFE',
    tab_advisory: 'Safety Alert',
    tab_roads: 'Rasta Khabar',
    tab_shelters: 'Shelter aru Hospital',
    tab_safety_tips: 'Bacha Laga Niyam',
    hospitals_trauma: 'Verified Hospital aru Trauma Center',
    public_shelters: 'Public Emergency Relief Camp',
    bro_detachments: 'BRO Road Clearing Camp',
    police_patrol: 'Highway Police Outpost',
    direct_call: 'Emergency Call Kuribi',

    // Outside NER Coverage Notice
    outside_ner_title: 'Select Kura Jaga North Eastern Region Laga Baahr Te Asey',
    outside_ner_badge: 'Monitoring Area Laga Baahr',
    outside_ner_desc: 'Apuni select kura coordinate North Eastern Region (NER) laga boundary baahr te asey. Eitu early warning system 8 ta North Eastern states (Assam, Arunachal Pradesh, Manipur, Meghalaya, Mizoram, Nagaland, Sikkim, aru Tripura) karne banai thakise.',
    outside_ner_states_covered: '8 ta NER States: Assam, Arunachal Pradesh, Meghalaya, Manipur, Mizoram, Nagaland, Sikkim, Tripura',
    outside_ner_prompt: 'Live landslide aru rasta halat sabole tolot thaka NER rasta select kuribi:',
    outside_ner_clear: 'Selection Hatai Dibi',

    audio_alert_phrase: 'Hoshiyar: Eitu jaga te landslide laga bishi dangor danger asey. Travel nakuribi.'
  },

  // Nepali (नेपाली - Official in Sikkim, dominant lingua franca across Sikkim and hills)
  ne: {
    system_title: 'पूर्वोत्तर पहिरो जोखिम अनुगमन प्रणाली',
    system_sub: 'उत्तर-पूर्वी अन्तरिक्ष उपयोग केन्द्र तथा विपद् व्यवस्थापन',
    gov_seal: 'भारत सरकार · राष्ट्रिय विपद् व्यवस्थापन प्राधिकरण (NDMA) · पूर्वोत्तर परिषद्',
    helpline_title: 'हेल्पलाइन: १०७०',
    alarm_active: 'अलार्म चालु',
    alarm_muted: 'म्युट',
    light_mode: 'दिनको मोड',
    dark_mode: 'रातको मोड',
    logout_btn: 'लगआउट',
    select_language: 'भाषा रोज्नुहोस्',
    language: 'भाषा',

    citizen_portal_tab: 'नागरिक सुरक्षा पोर्टल',
    admin_portal_tab: 'सरकारी अधिकारी लगइन',
    citizen_portal_subtitle: 'सार्वजनिक नागरिक सुरक्षा नेटवर्क',
    citizen_portal_desc: 'सिक्किम तथा पूर्वोत्तरका पहाडी पहिरो नक्सा, वर्षाको अवस्था हेर्नुहोस् र रिपोर्ट दर्ता गर्नुहोस्।',
    admin_portal_subtitle: 'विपद् व्यवस्थापन तथा कमाण्ड सेन्टर',
    admin_portal_desc: 'कमाण्डर, जिल्ला मजिस्ट्रेट, एनडीआरएफ र बिआरओ अधिकारीहरूको लागि सुरक्षित पहुँच।',
    restricted_access_badge: 'प्रतिबन्धित पहुँच · आधिकारिक अधिकारीहरूका लागि मात्र',
    sign_in_tab: 'नागरिक लगइन',
    register_tab: 'नयाँ नागरिक दर्ता',
    full_name_label: 'पूरा नाम',
    email_label: 'दर्ता भएको इमेल',
    password_label: 'पासवर्ड',
    phone_label: 'मोबाइल नम्बर (एसएमएस सतर्कताको लागि)',
    state_label: 'बस्ने राज्य',
    sign_in_button: 'सुरक्षा पोर्टलमा प्रवेश गर्नुहोस्',
    register_button: 'खाता बनाउनुहोस् र प्रवेश गर्नुहोस्',
    admin_login_button: 'अधिकारीको रूपमा लगइन गर्नुहोस्',
    demo_credentials_title: '१-क्लिक परीक्षण खाता:',
    citizen_demo_tag: 'पेमा ताशी (नागरिक)',
    admin_demo_tag: 'कर्नेल संजीव रोय (एडमिन)',

    public_safety_guide: 'सार्वजनिक सुरक्षा निर्देशिका',
    ner_hill_corridors: 'पूर्वोत्तर पहाडी भिर तथा राजमार्गहरू',
    select_location_heading: 'पहिरो तथा राजमार्ग सुरक्षा जाँच गर्न स्थान रोज्नुहोस्',
    select_location_subtext: 'नक्सामा कुनै पनि स्थानमा क्लिक गर्नुहोस् वा आफ्नो सहर/राजमार्ग खोज्नुहोस्। तपाईंले तुरुन्तै वर्षाको नाप, सडकको स्थिति र नजिकको राहत शिविरको जानकारी पाउनुहुनेछ।',
    select_corridor_prompt: 'जाँचको लागि मुख्य पहाडी राजमार्ग रोज्नुहोस्:',
    red_alert_title: 'गम्भीर रेड अलर्ट: जीवन सुरक्षा चेतावनी',
    red_alert_desc: 'यस पहाडी खण्डमा भीषण पहिरोको गम्भीर जोखिम देखिएको छ। भारी वर्षाका कारण भिर खस्ने सम्भावना उच्च छ। अति आवश्यक बाहेक यात्रा नगर्न कडा आग्रह गरिन्छ।',
    warning_title: 'चेतावनी: पहिरोको उच्च जोखिम',
    normal_title: 'सामान्य: पहाडी बाटो सुरक्षित',
    dial_helpline: 'हेल्पलाइन: १०७०',
    shelter_btn: 'नजिकको राहत शिविर',
    sound_on: 'ध्वनि चालु',
    sound_muted_btn: 'म्युट',
    dismiss_btn: 'हटाउनुहोस्',
    share_advisory: 'सुरक्षा सल्लाह सेयर गर्नुहोस्',
    advisory_copied: 'कपी गरियो!',
    report_hazard: 'पहिरोको जानकारी दिनुहोस्',
    rainfall_24h: '२४ घण्टाको वर्षा',
    rainfall_72h: '७२ घण्टाको वर्षा',
    elevation_m: 'उचाइ',
    slope_angle: 'भिरको कोण',
    soil_saturation: 'माटोको ओसिलोपन',
    highway_status: 'राजमार्गको अवस्था',
    status_blocked: 'पहिरोले सडक अवरुद्ध',
    status_at_risk: 'सावधानीपूर्वक चलाउनुहोस्',
    status_clear: 'खुला र सुरक्षित',
    tab_advisory: 'सल्लाह',
    tab_roads: 'सडक स्थिति',
    tab_shelters: 'शिविर तथा अस्पताल',
    tab_safety_tips: 'सुरक्षा नियमहरू',
    hospitals_trauma: 'प्रमाणित आपतकालीन अस्पताल तथा ट्रमा युनिट',
    public_shelters: 'सार्वजनिक आपतकालीन राहत शिविरहरू',
    bro_detachments: 'सीमा सडक संगठन (BRO) मार्ग निकासी क्याम्प',
    police_patrol: 'राजमार्ग प्रहरी चौकी',
    direct_call: 'तुरुन्तै फोन गर्नुहोस्',

    // Outside NER Coverage Notice
    outside_ner_title: 'चयन गरिएको स्थान उत्तर-पूर्वी क्षेत्र (NER) भन्दा बाहिर छ',
    outside_ner_badge: 'अनुगमन सीमा भन्दा बाहिर',
    outside_ner_desc: 'चयन गरिएको निर्देशांक भारतको उत्तर-पूर्वी क्षेत्र (NER) को सीमा भन्दा बाहिर पर्दछ। यो अर्ली वार्निङ पोर्टल विशेष रूपमा पूर्वोत्तरका ८ राज्यहरू (सिक्किम, असम, अरुणाचल, मेघालय, नागाल्यान्ड, मणिपुर, मिजोरम र त्रिपुरा) को पहिरो अनुगमनका लागि समर्पित छ।',
    outside_ner_states_covered: '८ अनुगमित राज्यहरू: सिक्किम, असम, अरुणाचल, मेघालय, नागाल्यान्ड, मणिपुर, मिजोरम, त्रिपुरा',
    outside_ner_prompt: 'लाइभ पहिरो डाटा हेर्न तल दिइएको पूर्वोत्तरको मुख्य पहाडी खण्ड रोज्नुहोस्:',
    outside_ner_clear: 'चयन हटाउनुहोस्',

    audio_alert_phrase: 'चेतावनी: यस क्षेत्रमा गम्भीर पहिरोको जोखिम छ। यात्रा नगर्न सल्लाह दिइन्छ।'
  }
};

/**
 * Universal translation resolver
 * @param {string} key - The translation key
 * @param {string} [fallback] - Optional fallback string if key not found
 * @param {string} [lang] - Optional specific language code (defaults to active language)
 */
export function t(key, fallback = '', lang = null) {
  const currentLang = lang || getLanguage();
  const dict = TRANSLATIONS[currentLang] || TRANSLATIONS.en;
  if (dict && dict[key]) {
    return dict[key];
  }
  // Fallback to English dictionary
  if (TRANSLATIONS.en && TRANSLATIONS.en[key]) {
    return TRANSLATIONS.en[key];
  }
  return fallback || key;
}
