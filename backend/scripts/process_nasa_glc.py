"""
Process NASA Global Landslide Catalog — Phase 2.6C Checkpoint 2

Reads:  backend/data/historical/raw/nasa_global_landslide_catalog_original.csv
Writes: backend/data/historical/processed/nasa_glc_ner_standardized.csv

Raw file is NEVER modified.

Standardized output schema
---------------------------
source                     : "NASA_GLC"
source_id                  : str  (event_id)
source_ref                 : str  (OBJECTID or FID)
latitude                   : float
longitude                  : float
state                      : str
district                   : None (not available in NASA GLC)
location_description       : str  (location_d)
landslide_type             : str  (landslide_)
trigger                    : str  (landslide1)
event_date                 : str  (ISO 8601 formatted YYYY-MM-DD or raw if parsing fails)
temporal_precision         : str  ("day" or "unknown")
fatalities                 : int | None (fatality_c)
injuries                   : int | None (injury_cou)
location_accuracy          : str  (location_a)
original_record_reference  : str  (source_nam)
valid_coordinates          : bool
valid_date                 : bool
duplicate_source_id        : bool
duplicate_coordinates      : bool
"""

import csv
import os
from datetime import datetime, timezone
from collections import Counter

# ── paths (resolved relative to project root) ──────────────────────────────
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
RAW_PATH = os.path.join(PROJECT_ROOT, "backend", "data", "historical", "raw",
                        "nasa_global_landslide_catalog_original.csv")
OUT_DIR  = os.path.join(PROJECT_ROOT, "backend", "data", "historical", "processed")
OUT_PATH = os.path.join(OUT_DIR, "nasa_glc_ner_standardized.csv")

# ── NER state names (canonical, case-insensitive matching) ─────────────────
NER_STATES = {
    "arunachal pradesh", "assam", "manipur",
    "meghalaya", "mizoram", "nagaland", "sikkim", "tripura",
}

# ── helpers ────────────────────────────────────────────────────────────────

def _clean_str(val) -> str | None:
    """Return stripped string or None for blank/whitespace-only values."""
    if val is None:
        return None
    s = str(val).strip()
    return s if s else None


def _is_ner_state(state_val: str | None) -> bool:
    if not state_val:
        return False
    return state_val.strip().lower() in NER_STATES


def _valid_coord(lat: float, lon: float) -> bool:
    return -90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0


def _to_int(val) -> int | None:
    if val is None:
        return None
    s = str(val).strip()
    if not s:
        return None
    try:
        return int(float(s))
    except ValueError:
        return None


def parse_nasa_date(date_str: str | None) -> tuple[str | None, bool]:
    """Parse date into YYYY-MM-DD format.

    Returns (formatted_date_string, is_valid).
    If parsing fails, returns original string and False.
    """
    if not date_str:
        return None, False

    date_str_clean = date_str.strip()
    if not date_str_clean:
        return None, False

    # formats to try
    for fmt in ("%Y/%m/%d %H:%M:%S%z", "%Y/%m/%d %H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(date_str_clean, fmt)
            return dt.strftime("%Y-%m-%d"), True
        except ValueError:
            pass

    # parse via prefix splitting
    if len(date_str_clean) >= 10:
        date_part = date_str_clean[:10]
        for sep in ("/", "-"):
            parts = date_part.split(sep)
            if len(parts) == 3:
                try:
                    y, m, d = int(parts[0]), int(parts[1]), int(parts[2])
                    if 1900 <= y <= 2100 and 1 <= m <= 12 and 1 <= d <= 31:
                        return f"{y:04d}-{m:02d}-{d:02d}", True
                except ValueError:
                    pass

    return date_str_clean, False


def process():
    os.makedirs(OUT_DIR, exist_ok=True)

    print(f"Loading raw NASA GLC CSV from: {RAW_PATH}")
    with open(RAW_PATH, "r", encoding="utf-8") as f:
        # Some CSVs may have BOM, strip it if found
        raw_text = f.read()
        if raw_text.startswith(chr(0xFEFF)):
            raw_text = raw_text.lstrip(chr(0xFEFF))
        reader = csv.DictReader(raw_text.splitlines())
        rows = list(reader)

    raw_count = len(rows)
    print(f"  Raw record count: {raw_count}")

    # ── pre-pass: collect all event_ids for duplicate detection ───────────
    event_ids = [r.get("event_id", "").strip() for r in rows if r.get("event_id")]
    event_id_counter = Counter(event_ids)
    duplicate_event_ids = {k for k, v in event_id_counter.items() if v > 1}

    # ── first pass: filter to India and NER states ────────────────────────
    ner_rows = []
    excluded_outside_ner = 0
    for r in rows:
        country = _clean_str(r.get("country_na"))
        state = _clean_str(r.get("admin_divi"))

        # filter to India first
        if not country or country.lower() != "india":
            excluded_outside_ner += 1
            continue

        # filter to Northeast India
        if not _is_ner_state(state):
            excluded_outside_ner += 1
            continue

        ner_rows.append(r)

    # ── duplicate coordinate/date check within NER ─────────────────────────
    # (since we are filtering to NER, checking duplication of coordinate/date combination in NER)
    coord_date_list = []
    for r in ner_rows:
        lat_str = r.get("latitude", "").strip()
        lon_str = r.get("longitude", "").strip()
        date_str = r.get("event_date", "").strip()
        coord_date_list.append((lat_str, lon_str, date_str))

    coord_date_counter = Counter(coord_date_list)
    duplicate_coord_dates = {k for k, v in coord_date_counter.items() if v > 1}

    # ── counters for NER ──────────────────────────────────────────────────
    missing_coords   = 0
    invalid_coords   = 0
    missing_dates    = 0
    invalid_dates    = 0
    dup_src_id       = 0
    dup_coord_date   = 0
    state_counts     = {s: 0 for s in sorted(NER_STATES)}
    parsed_dates     = []

    processed_records = []

    # ── second pass: standardization ──────────────────────────────────────
    for r in ner_rows:
        # extract coordinates
        lat_str = r.get("latitude")
        lon_str = r.get("longitude")

        if not lat_str or not lon_str:
            valid_coords = False
            missing_coords += 1
            lat, lon = None, None
        else:
            try:
                lat = float(lat_str)
                lon = float(lon_str)
                if _valid_coord(lat, lon):
                    valid_coords = True
                else:
                    valid_coords = False
                    invalid_coords += 1
            except ValueError:
                valid_coords = False
                invalid_coords += 1
                lat, lon = None, None

        # parse date
        raw_date = r.get("event_date")
        if not raw_date or not raw_date.strip():
            event_date = None
            valid_date = False
            missing_dates += 1
            temporal_precision = "unknown"
        else:
            event_date, valid_date = parse_nasa_date(raw_date)
            if not valid_date:
                invalid_dates += 1
                temporal_precision = "unknown"
            else:
                temporal_precision = "day"
                parsed_dates.append(event_date)

        # duplicate flags
        ev_id = _clean_str(r.get("event_id"))
        is_dup_id = (ev_id in duplicate_event_ids) if ev_id else False

        lat_raw = r.get("latitude", "").strip()
        lon_raw = r.get("longitude", "").strip()
        date_raw = r.get("event_date", "").strip()
        is_dup_coord_date = ((lat_raw, lon_raw, date_raw) in duplicate_coord_dates)

        if is_dup_id:
            dup_src_id += 1
        if is_dup_coord_date:
            dup_coord_date += 1

        # state count
        state_val = _clean_str(r.get("admin_divi"))
        state_key = state_val.lower() if state_val else ""
        if state_key in state_counts:
            state_counts[state_key] += 1

        # standardized fields mapping
        std_row = {
            "source":                    "NASA_GLC",
            "source_id":                 ev_id,
            "source_ref":                _clean_str(r.get("OBJECTID") or r.get("FID")),
            "latitude":                  lat if lat is not None else "",
            "longitude":                 lon if lon is not None else "",
            "state":                     state_val,
            "district":                  "",  # not in NASA GLC
            "location_description":      _clean_str(r.get("location_d")),
            "landslide_type":            _clean_str(r.get("landslide_")),
            "trigger":                   _clean_str(r.get("landslide1")),
            "event_date":                event_date if event_date is not None else "",
            "temporal_precision":        temporal_precision,
            "fatalities":                _to_int(r.get("fatality_c")) if r.get("fatality_c") else "",
            "injuries":                  _to_int(r.get("injury_cou")) if r.get("injury_cou") else "",
            "location_accuracy":         _clean_str(r.get("location_a")),
            "original_record_reference": _clean_str(r.get("source_nam")),
            "valid_coordinates":         str(valid_coords).upper(),
            "valid_date":                str(valid_date).upper(),
            "duplicate_source_id":       str(is_dup_id).upper(),
            "duplicate_coordinates":     str(is_dup_coord_date).upper()
        }

        processed_records.append(std_row)

    # ── write output to CSV ────────────────────────────────────────────────
    headers = [
        "source", "source_id", "source_ref", "latitude", "longitude", "state", "district",
        "location_description", "landslide_type", "trigger", "event_date", "temporal_precision",
        "fatalities", "injuries", "location_accuracy", "original_record_reference",
        "valid_coordinates", "valid_date", "duplicate_source_id", "duplicate_coordinates"
    ]

    with open(OUT_PATH, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(processed_records)

    # date range calculation
    min_date = min(parsed_dates) if parsed_dates else None
    max_date = max(parsed_dates) if parsed_dates else None

    # ── summary ───────────────────────────────────────────────────────────
    summary = {
        "dataset":                    "NASA_GLC",
        "raw_record_count":           raw_count,
        "ner_filtered_count":         len(processed_records),
        "excluded_outside_ner":       excluded_outside_ner,
        "missing_coordinates":        missing_coords,
        "invalid_coordinates":        invalid_coords,
        "missing_dates":              missing_dates,
        "invalid_dates":              invalid_dates,
        "date_range_min":             min_date,
        "date_range_max":             max_date,
        "duplicate_source_ids":      dup_src_id,
        "duplicate_coordinate_pairs": dup_coord_date,
        "has_event_date":             True,
        "state_counts":               state_counts,
        "output_file":                os.path.basename(OUT_PATH),
    }

    print("\n-- NASA Processing Summary --")
    print(f"  Raw records:          {raw_count}")
    print(f"  NER filtered records: {len(processed_records)}")
    print(f"  Excluded (non-NER):   {excluded_outside_ner}")
    print(f"  Missing coords:       {missing_coords}")
    print(f"  Invalid coords:       {invalid_coords}")
    print(f"  Missing dates:        {missing_dates}")
    print(f"  Invalid dates:        {invalid_dates}")
    if min_date and max_date:
        print(f"  Date range:           {min_date} to {max_date}")
    print(f"  Dup source IDs:       {dup_src_id}")
    print(f"  Dup coordinate/dates: {dup_coord_date}")
    print("  State counts:")
    for s, c in sorted(state_counts.items()):
        print(f"    {s.title():25s}: {c}")
    print(f"  Output: {OUT_PATH}")

    return summary


if __name__ == "__main__":
    process()
