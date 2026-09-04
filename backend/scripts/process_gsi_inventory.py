"""
Process GSI Landslide Inventory — Phase 2.6C Checkpoint 2

Reads:  backend/data/historical/raw/gsi_landslide_inventory_original.geojson
Writes: backend/data/historical/processed/gsi_ner_standardized.geojson

Raw file is NEVER modified.

Standardized output schema
---------------------------
source                  : "GSI"
source_id               : int  (OBJECTID)
source_ref              : str  (SLIDE_NO)
latitude                : float
longitude               : float
state                   : str
district                : str
slide_name              : str | None
landslide_type          : str | None  (MOVEMENT_TYPE)
material                : str | None  (MATERIAL_TYPE)
trigger                 : str | None  (TRIGGERING)
activity                : str | None  (ACTIVITY)
movement_rate           : str | None  (MOVEMENT_RATE)
geology                 : str | None  (GEOLOGY)
geoscientific_cause     : str | None  (GEOSCIENTIFIC_CAUSE)
persons_death           : str | None  (PERSONS_DEATH – kept as string; inconsistent source)
people_affected         : str | None  (PEOPLE_AFFECTED)
infrastructure_affected : str | None  (INFRASTRUCTURE_AFFECTED)
event_date              : None        (not present in GSI)
temporal_precision      : "unknown"
location_accuracy       : None        (not in GSI)
valid_coordinates       : bool
duplicate_coordinates   : bool
duplicate_source_ref    : bool
"""

import json
import os
import sys
from datetime import datetime, timezone

# ── paths (resolved relative to project root) ──────────────────────────────
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
RAW_PATH = os.path.join(PROJECT_ROOT, "backend", "data", "historical", "raw",
                        "gsi_landslide_inventory_original.geojson")
OUT_DIR  = os.path.join(PROJECT_ROOT, "backend", "data", "historical", "processed")
OUT_PATH = os.path.join(OUT_DIR, "gsi_ner_standardized.geojson")

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


def process():
    os.makedirs(OUT_DIR, exist_ok=True)

    # ── load raw GeoJSON ───────────────────────────────────────────────────
    print(f"Loading raw GSI GeoJSON from: {RAW_PATH}")
    with open(RAW_PATH, "r", encoding="utf-8") as f:
        raw = json.load(f)

    features = raw.get("features", [])
    raw_count = len(features)
    print(f"  Raw feature count: {raw_count}")

    # ── pre-pass: collect SLIDE_NOs for duplicate detection ───────────────
    from collections import Counter
    slide_no_counter = Counter(
        str(f["properties"].get("SLIDE_NO", "")).strip()
        for f in features
    )
    duplicate_slide_nos = {k for k, v in slide_no_counter.items() if v > 1 and k}

    # ── first pass: collect all coord pairs among NER features ────────────
    # (we need the full NER set before we can flag duplicate coords)
    ner_raw = []
    for feat in features:
        props = feat.get("properties", {})
        state_val = _clean_str(props.get("STATE"))
        if not _is_ner_state(state_val):
            continue
        geom = feat.get("geometry", {})
        coords = geom.get("coordinates", [None, None])
        lon_raw, lat_raw = coords[0], coords[1]
        ner_raw.append((feat, props, lat_raw, lon_raw, state_val))

    # build coord-pair duplicate set within NER
    coord_counter = Counter(
        (r[2], r[3]) for r in ner_raw
    )
    duplicate_coord_pairs = {k for k, v in coord_counter.items() if v > 1}

    # ── counters ──────────────────────────────────────────────────────────
    excluded_outside_ner = raw_count - len(ner_raw)
    missing_coords   = 0
    invalid_coords   = 0
    dup_src_ref      = 0
    dup_coord        = 0
    state_counts     = {s: 0 for s in sorted(NER_STATES)}

    processed_features = []

    for feat, props, lat_raw, lon_raw, state_val in ner_raw:
        # ── coordinate validation ─────────────────────────────────────────
        if lat_raw is None or lon_raw is None:
            valid_coords = False
            missing_coords += 1
        elif not _valid_coord(float(lat_raw), float(lon_raw)):
            valid_coords = False
            invalid_coords += 1
        else:
            valid_coords = True

        lat = float(lat_raw) if valid_coords else None
        lon = float(lon_raw) if valid_coords else None

        # ── duplicate flags ───────────────────────────────────────────────
        slide_no = _clean_str(props.get("SLIDE_NO"))
        is_dup_ref   = (slide_no in duplicate_slide_nos) if slide_no else False
        is_dup_coord = ((lat_raw, lon_raw) in duplicate_coord_pairs) if valid_coords else False

        if is_dup_ref:
            dup_src_ref += 1
        if is_dup_coord:
            dup_coord += 1

        # ── state count ───────────────────────────────────────────────────
        state_key = state_val.strip().lower()
        if state_key in state_counts:
            state_counts[state_key] += 1

        # ── build standardized properties ─────────────────────────────────
        std_props = {
            "source":                  "GSI",
            "source_id":               props.get("OBJECTID"),
            "source_ref":              slide_no,
            "latitude":                lat,
            "longitude":               lon,
            "state":                   state_val,
            "district":                _clean_str(props.get("DISTRICT")),
            "slide_name":              _clean_str(props.get("SLIDE_NAME")),
            "landslide_type":          _clean_str(props.get("MOVEMENT_TYPE")),
            "material":                _clean_str(props.get("MATERIAL_TYPE")),
            "trigger":                 _clean_str(props.get("TRIGGERING")),
            "activity":                _clean_str(props.get("ACTIVITY")),
            "movement_rate":           _clean_str(props.get("MOVEMENT_RATE")),
            "geology":                 _clean_str(props.get("GEOLOGY")),
            "geoscientific_cause":     _clean_str(props.get("GEOSCIENTIFIC_CAUSE")),
            "persons_death":           _clean_str(props.get("PERSONS_DEATH")),
            "people_affected":         _clean_str(props.get("PEOPLE_AFFECTED")),
            "infrastructure_affected": _clean_str(props.get("INFRASTRUCTURE_AFFECTED")),
            # temporal
            "event_date":              None,
            "temporal_precision":      "unknown",
            "location_accuracy":       None,
            # quality flags
            "valid_coordinates":       valid_coords,
            "duplicate_source_ref":    is_dup_ref,
            "duplicate_coordinates":   is_dup_coord,
        }

        std_geom = (
            {"type": "Point", "coordinates": [lon, lat]}
            if valid_coords else None
        )

        processed_features.append({
            "type": "Feature",
            "geometry": std_geom,
            "properties": std_props,
        })

    # ── write output ──────────────────────────────────────────────────────
    output_fc = {
        "type": "FeatureCollection",
        "metadata": {
            "source":             "GSI Landslide Inventory (via Bharatlas/CC0-1.0)",
            "raw_file":           os.path.basename(RAW_PATH),
            "processing_script":  os.path.basename(__file__),
            "processed_at":       datetime.now(timezone.utc).isoformat(),
            "region_filter":      "Northeast India (NER)",
        },
        "features": processed_features,
    }

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(output_fc, f, ensure_ascii=False, separators=(",", ":"))

    # ── summary ───────────────────────────────────────────────────────────
    summary = {
        "dataset":                    "GSI",
        "raw_record_count":           raw_count,
        "ner_filtered_count":         len(processed_features),
        "excluded_outside_ner":       excluded_outside_ner,
        "missing_coordinates":        missing_coords,
        "invalid_coordinates":        invalid_coords,
        "duplicate_source_refs":      dup_src_ref,
        "duplicate_coordinate_pairs": dup_coord,
        "has_event_date":             False,
        "state_counts":               state_counts,
        "output_file":                os.path.basename(OUT_PATH),
    }

    print("\n-- GSI Processing Summary --")
    print(f"  Raw records:          {raw_count}")
    print(f"  NER filtered records: {len(processed_features)}")
    print(f"  Excluded (non-NER):   {excluded_outside_ner}")
    print(f"  Missing coords:       {missing_coords}")
    print(f"  Invalid coords:       {invalid_coords}")
    print(f"  Dup source refs:      {dup_src_ref}")
    print(f"  Dup coord pairs:      {dup_coord}")
    print("  State counts:")
    for s, c in sorted(state_counts.items()):
        print(f"    {s.title():25s}: {c}")
    print(f"  Output: {OUT_PATH}")

    return summary


if __name__ == "__main__":
    process()
