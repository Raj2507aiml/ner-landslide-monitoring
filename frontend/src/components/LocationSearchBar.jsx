import { useState, useEffect, useRef } from 'react'
import { Search, MapPin, X, RefreshCw, Zap, ChevronDown, AlertCircle } from 'lucide-react'

// Curated high-risk landslide corridors across the 8 North Eastern states
export const NER_HOTSPOTS = [
  { name: 'Sonapur Tunnel, NH-06', state: 'Meghalaya', lat: 25.1012, lng: 92.3654, hazard: 'Critical' },
  { name: 'Dzükou Valley / Kohima, NH-29', state: 'Nagaland', lat: 25.6751, lng: 94.1086, hazard: 'High' },
  { name: 'Dima Hasao (Haflong)', state: 'Assam', lat: 25.1667, lng: 93.0167, hazard: 'High' },
  { name: 'Gangtok Corridor, NH-10', state: 'Sikkim', lat: 27.3389, lng: 88.6065, hazard: 'Critical' },
  { name: 'Cherrapunji (Sohra Rim)', state: 'Meghalaya', lat: 25.2986, lng: 91.7086, hazard: 'Moderate' },
  { name: 'Sela Pass / Tawang Highway', state: 'Arunachal Pradesh', lat: 27.5034, lng: 92.1037, hazard: 'Critical' },
  { name: 'Aizawl Slope Corridor', state: 'Mizoram', lat: 23.7271, lng: 92.7176, hazard: 'High' },
  { name: 'Tupul / Imphal West', state: 'Manipur', lat: 24.7865, lng: 93.6322, hazard: 'Critical' }
]

export default function LocationSearchBar({ onSelectLocation }) {
  const [query, setQuery] = useState('')
  const [suggestions, setSuggestions] = useState([])
  const [isSearching, setIsSearching] = useState(false)
  const [showDropdown, setShowDropdown] = useState(false)
  const [showHotspots, setShowHotspots] = useState(false)
  const [searchError, setSearchError] = useState(null)
  
  const containerRef = useRef(null)
  const debounceTimerRef = useRef(null)

  // Close dropdown on click outside
  useEffect(() => {
    const handleClickOutside = (e) => {
      if (containerRef.current && !containerRef.current.contains(e.target)) {
        setShowDropdown(false)
        setShowHotspots(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  // Geocoding query to OpenStreetMap Nominatim with NER bias
  const fetchSuggestions = async (searchQuery) => {
    if (!searchQuery || searchQuery.trim().length < 2) {
      setSuggestions([])
      setSearchError(null)
      return
    }

    setIsSearching(true)
    setSearchError(null)

    try {
      // Nominatim search API with viewbox prioritizing North East India
      const url = `https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(
        searchQuery.trim()
      )}&countrycodes=in&viewbox=88.0,29.5,97.5,21.5&bounded=0&limit=5`

      const res = await fetch(url, {
        headers: {
          'Accept-Language': 'en',
          'User-Agent': 'NERLandslideMonitor/1.0'
        }
      })

      if (!res.ok) {
        throw new Error(`Geocoding HTTP error: ${res.status}`)
      }

      const data = await res.json()
      
      if (Array.isArray(data) && data.length > 0) {
        const formatted = data.map(item => {
          const parts = item.display_name.split(',')
          const title = parts[0] ? parts[0].trim() : item.display_name
          const subtitle = parts.slice(1, 4).join(',').trim()
          return {
            title,
            subtitle,
            lat: parseFloat(item.lat),
            lng: parseFloat(item.lon)
          }
        })
        setSuggestions(formatted)
        setShowDropdown(true)
      } else {
        // Fallback: check local NER Hotspots for matches
        const localMatches = NER_HOTSPOTS.filter(h => 
          h.name.toLowerCase().includes(searchQuery.toLowerCase()) || 
          h.state.toLowerCase().includes(searchQuery.toLowerCase())
        ).map(h => ({
          title: h.name,
          subtitle: `${h.state}, India · ${h.hazard} Hazard Corridor`,
          lat: h.lat,
          lng: h.lng
        }))
        setSuggestions(localMatches)
        setShowDropdown(localMatches.length > 0)
      }
    } catch (err) {
      console.warn('[Location Search] Live geocoding unavailable, falling back to local database:', err)
      const localMatches = NER_HOTSPOTS.filter(h => 
        h.name.toLowerCase().includes(searchQuery.toLowerCase()) || 
        h.state.toLowerCase().includes(searchQuery.toLowerCase())
      ).map(h => ({
        title: h.name,
        subtitle: `${h.state}, India · Hazard Corridor`,
        lat: h.lat,
        lng: h.lng
      }))
      setSuggestions(localMatches)
      if (localMatches.length === 0) {
        setSearchError('Live search unavailable. Try selecting from Quick Hotspots.')
      }
      setShowDropdown(true)
    } finally {
      setIsSearching(false)
    }
  }

  const handleInputChange = (e) => {
    const val = e.target.value
    setQuery(val)
    setShowHotspots(false)

    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current)
    }

    if (val.trim().length >= 2) {
      debounceTimerRef.current = setTimeout(() => {
        fetchSuggestions(val)
      }, 350)
    } else {
      setSuggestions([])
      setShowDropdown(false)
      setSearchError(null)
    }
  }

  const handleSelectLocation = (lat, lng, name) => {
    setQuery(name || `${lat.toFixed(4)}, ${lng.toFixed(4)}`)
    setShowDropdown(false)
    setShowHotspots(false)
    if (onSelectLocation) {
      onSelectLocation({ lat, lng }, name)
    }
  }

  const handleClear = (e) => {
    e.stopPropagation()
    setQuery('')
    setSuggestions([])
    setShowDropdown(false)
    setSearchError(null)
  }

  return (
    <div ref={containerRef} className="relative w-full max-w-[280px] sm:max-w-[320px] pointer-events-auto">
      {/* Search Input Bar */}
      <div className="flex items-center gap-1.5 bg-[var(--card-bg)]/95 backdrop-blur-md border border-[var(--border-subtle)] rounded-lg p-1 shadow-lg transition-all focus-within:border-emerald-500/80 focus-within:ring-2 focus-within:ring-emerald-500/20">
        <div className="pl-1.5 text-[var(--text-dim)] flex items-center">
          {isSearching ? (
            <RefreshCw className="h-3.5 w-3.5 animate-spin text-emerald-500" />
          ) : (
            <Search className="h-3.5 w-3.5 text-emerald-500" />
          )}
        </div>

        <input
          type="text"
          value={query}
          onChange={handleInputChange}
          onFocus={() => {
            if (suggestions.length > 0) setShowDropdown(true)
          }}
          placeholder="Search NER city, town, highway..."
          className="w-full bg-transparent border-none text-[11px] text-[var(--text-main)] placeholder-[var(--text-dim)] outline-none font-medium px-1"
        />

        {query && (
          <button
            onClick={handleClear}
            className="p-1 text-[var(--text-muted)] hover:text-[var(--text-main)] rounded transition"
            title="Clear search"
          >
            <X className="h-3 w-3" />
          </button>
        )}

        {/* Hotspots toggle button */}
        <button
          type="button"
          onClick={() => {
            setShowHotspots(prev => !prev)
            setShowDropdown(false)
          }}
          className={`flex items-center gap-1 text-[10px] font-bold px-2 py-1 rounded-md border transition whitespace-nowrap cursor-pointer ${
            showHotspots
              ? 'bg-emerald-500/20 text-emerald-400 border-emerald-500/40'
              : 'bg-[var(--subcard-bg)] text-[var(--text-muted)] hover:text-[var(--text-main)] border-[var(--border-subtle)]'
          }`}
          title="Quick landslide hazard hotspots"
        >
          <Zap className="h-3 w-3 text-amber-400 fill-amber-400/20" />
          <span className="hidden sm:inline">Hotspots</span>
          <ChevronDown className={`h-2.5 w-2.5 transition-transform ${showHotspots ? 'rotate-180' : ''}`} />
        </button>
      </div>

      {/* Autocomplete Suggestions Dropdown */}
      {showDropdown && (
        <div className="absolute left-0 right-0 top-full mt-1.5 bg-[var(--card-bg)]/95 backdrop-blur-md border border-[var(--border-subtle)] rounded-lg shadow-xl overflow-hidden z-[1050] max-h-56 overflow-y-auto text-xs">
          {searchError ? (
            <div className="p-2.5 text-[10px] text-amber-400 flex items-start gap-1.5">
              <AlertCircle className="h-3.5 w-3.5 shrink-0 mt-0.5" />
              <span>{searchError}</span>
            </div>
          ) : suggestions.length === 0 ? (
            <div className="p-2.5 text-[10px] text-[var(--text-muted)] text-center">
              No matching locations found in NER.
            </div>
          ) : (
            <div className="divide-y divide-[var(--border-subtle)]/50">
              {suggestions.map((item, idx) => (
                <button
                  key={`${item.lat}-${item.lng}-${idx}`}
                  onClick={() => handleSelectLocation(item.lat, item.lng, item.title)}
                  className="w-full text-left p-2 hover:bg-[var(--subcard-bg)] transition flex items-start gap-2 cursor-pointer group"
                >
                  <MapPin className="h-3.5 w-3.5 text-emerald-500 shrink-0 mt-0.5 group-hover:scale-110 transition-transform" />
                  <div className="flex-1 min-w-0">
                    <p className="font-semibold text-[11px] text-[var(--text-main)] truncate">{item.title}</p>
                    {item.subtitle && (
                      <p className="text-[9px] text-[var(--text-muted)] truncate">{item.subtitle}</p>
                    )}
                  </div>
                  <span className="text-[9px] font-mono text-[var(--text-dim)] shrink-0 pt-0.5">
                    {item.lat.toFixed(2)}, {item.lng.toFixed(2)}
                  </span>
                </button>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Quick NER Hotspots Dropdown */}
      {showHotspots && (
        <div className="absolute left-0 right-0 top-full mt-1.5 bg-[var(--card-bg)]/95 backdrop-blur-md border border-[var(--border-subtle)] rounded-lg shadow-xl overflow-hidden z-[1050] max-h-64 overflow-y-auto text-xs">
          <div className="px-2.5 py-1.5 bg-[var(--subcard-bg)] border-b border-[var(--border-subtle)] flex justify-between items-center">
            <span className="text-[10px] font-bold text-emerald-400 uppercase tracking-wider flex items-center gap-1">
              <Zap className="h-3 w-3 text-amber-400" />
              <span>NER Critical Hotspots</span>
            </span>
            <span className="text-[9px] text-[var(--text-dim)] font-mono">8 States</span>
          </div>

          <div className="divide-y divide-[var(--border-subtle)]/50">
            {NER_HOTSPOTS.map((spot, idx) => {
              const hazardBadge =
                spot.hazard === 'Critical'
                  ? 'bg-rose-500/15 text-rose-400 border-rose-500/30'
                  : spot.hazard === 'High'
                  ? 'bg-amber-500/15 text-amber-400 border-amber-500/30'
                  : 'bg-sky-500/15 text-sky-400 border-sky-500/30'

              return (
                <button
                  key={idx}
                  onClick={() => handleSelectLocation(spot.lat, spot.lng, spot.name)}
                  className="w-full text-left p-2 hover:bg-[var(--subcard-bg)] transition flex items-center justify-between gap-2 cursor-pointer group"
                >
                  <div className="min-w-0 flex-1">
                    <p className="font-semibold text-[11px] text-[var(--text-main)] group-hover:text-emerald-400 transition truncate">
                      {spot.name}
                    </p>
                    <p className="text-[9px] text-[var(--text-muted)] truncate">{spot.state}</p>
                  </div>

                  <div className="flex items-center gap-1.5 shrink-0">
                    <span className={`text-[8px] font-bold px-1.5 py-0.5 rounded border ${hazardBadge}`}>
                      {spot.hazard}
                    </span>
                  </div>
                </button>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}
