"""
Static Susceptibility Probability Threshold Calibration - Phase 3 Checkpoint 11C

Recreates the 5-fold Spatial GroupKFold CV, generates out-of-fold predicted probabilities,
evaluates threshold levels (0.20 to 0.80), selects the optimal threshold maximizing
Recall (>= 0.85) while minimizing FPR, updates the model_metadata.json, and evaluates
on the Sikkim holdout using the calibrated threshold.
"""

import os
import sys
import csv
import json
import math
import numpy as np
import joblib

# Resolve backend directory and inject into path for imports
SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.abspath(os.path.join(SCRIPTS_DIR, ".."))
sys.path.insert(0, BACKEND_DIR)

from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import GroupKFold
from sklearn.metrics import confusion_matrix, recall_score, precision_score, f1_score

# ── Re-implementing Sikkim polygon checks ──────────────────────────────────
def _point_in_ring(x: float, y: float, ring: list) -> bool:
    inside = False
    n = len(ring)
    if n < 3:
        return False
    p1x, p1y = ring[0]
    for i in range(n + 1):
        p2x, p2y = ring[i % n]
        if y > min(p1y, p2y):
            if y <= max(p1y, p2y):
                if x <= max(p1x, p2x):
                    if p1y != p2y:
                        xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                    if p1x == p2x or x <= xinters:
                        inside = not inside
        p1x, p1y = p2x, p2y
    return inside

def _point_in_polygon(x: float, y: float, polygon: list) -> bool:
    if not _point_in_ring(x, y, polygon[0]):
        return False
    for hole in polygon[1:]:
        if _point_in_ring(x, y, hole):
            return False
    return True

def load_sikkim_polygon():
    geojson_path = os.path.join(BACKEND_DIR, "app", "data", "ner_boundary.geojson")
    if not os.path.exists(geojson_path):
        return None
    with open(geojson_path, "r", encoding="utf-8") as f:
        geojson = json.load(f)
    for feature in geojson.get("features", []):
        props = feature.get("properties", {})
        if props.get("state_name") == "Sikkim":
            geometry = feature.get("geometry", {})
            geom_type = geometry.get("type")
            coords = geometry.get("coordinates", [])
            bboxes = []
            if geom_type == "Polygon":
                ext = coords[0]
                lons = [p[0] for p in ext]
                lats = [p[1] for p in ext]
                bboxes.append((min(lons), min(lats), max(lons), max(lats)))
            elif geom_type == "MultiPolygon":
                for poly in coords:
                    ext = poly[0]
                    lons = [p[0] for p in ext]
                    lats = [p[1] for p in ext]
                    bboxes.append((min(lons), min(lats), max(lons), max(lats)))
            geometry["bboxes"] = bboxes
            return feature
    return None

def is_in_sikkim(latitude: float, longitude: float, sikkim_feature) -> bool:
    if not sikkim_feature:
        return 27.0 <= latitude <= 28.2 and 88.0 <= longitude <= 89.0
    geometry = sikkim_feature.get("geometry", {})
    geom_type = geometry.get("type")
    coords = geometry.get("coordinates", [])
    bboxes = geometry.get("bboxes", [])

    if geom_type == "Polygon":
        min_lon, min_lat, max_lon, max_lat = bboxes[0]
        if not (min_lon <= longitude <= max_lon and min_lat <= latitude <= max_lat):
            return False
        return _point_in_polygon(longitude, latitude, coords)
    elif geom_type == "MultiPolygon":
        for i, poly in enumerate(coords):
            min_lon, min_lat, max_lon, max_lat = bboxes[i]
            if not (min_lon <= longitude <= max_lon and min_lat <= latitude <= max_lat):
                continue
            if _point_in_polygon(longitude, latitude, poly):
                return True
        return False
    return False

def calculate_metrics_at_threshold(y_true, y_probs, threshold):
    y_pred = (y_probs >= threshold).astype(int)
    rec = recall_score(y_true, y_pred, zero_division=0)
    prec = precision_score(y_true, y_pred, zero_division=0)
    f1 = f1_score(y_true, y_pred, zero_division=0)
    
    cm = confusion_matrix(y_true, y_pred)
    tn, fp, fn, tp = cm.ravel()
    
    fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0
    fnr = fn / (fn + tp) if (fn + tp) > 0 else 0.0
    
    return {
        "threshold": float(threshold),
        "recall": float(rec),
        "precision": float(prec),
        "f1": float(f1),
        "fpr": float(fpr),
        "fnr": float(fnr),
        "confusion_matrix": [int(tn), int(fp), int(fn), int(tp)]
    }

def run_calibration():
    print("=== Commencing Susceptibility Threshold Calibration ===")
    
    csv_path = os.path.join(BACKEND_DIR, "data", "ml", "static_training_terrain.csv")
    model_path = os.path.join(BACKEND_DIR, "data", "ml", "models", "static_susceptibility_model.pkl")
    metadata_path = os.path.join(BACKEND_DIR, "data", "ml", "models", "model_metadata.json")
    
    if not os.path.exists(csv_path) or not os.path.exists(model_path) or not os.path.exists(metadata_path):
        print("Error: Missing required training data or trained model files.")
        sys.exit(1)
        
    # 1. Load data
    samples = []
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            r["latitude"] = float(r["latitude"])
            r["longitude"] = float(r["longitude"])
            r["elevation"] = float(r["elevation"])
            r["slope"] = float(r["slope"])
            r["aspect_sin"] = float(r["aspect_sin"])
            r["aspect_cos"] = float(r["aspect_cos"])
            r["landslide_label"] = int(r["landslide_label"])
            samples.append(r)
            
    # Split Sikkim vs non-Sikkim
    sikkim_poly = load_sikkim_polygon()
    train_region = [s for s in samples if not is_in_sikkim(s["latitude"], s["longitude"], sikkim_poly)]
    holdout_region = [s for s in samples if is_in_sikkim(s["latitude"], s["longitude"], sikkim_poly)]
    
    features = ["elevation", "slope", "aspect_sin", "aspect_cos"]
    X_train = np.array([[s[f] for f in features] for s in train_region])
    y_train = np.array([s["landslide_label"] for s in train_region])
    groups = np.array([s["spatial_block_id"] for s in train_region])
    
    X_holdout = np.array([[s[f] for f in features] for s in holdout_region])
    y_holdout = np.array([s["landslide_label"] for s in holdout_region])
    
    # 2. Re-run GroupKFold cross-validation to get Out-Of-Fold probabilities
    print("Re-running GroupKFold CV to gather out-of-fold predicted probabilities...")
    gkf = GroupKFold(n_splits=5)
    oof_probs = np.zeros(len(X_train))
    
    for train_idx, val_idx in gkf.split(X_train, y_train, groups):
        clf = RandomForestClassifier(
            n_estimators=100, max_depth=6, min_samples_leaf=5,
            class_weight="balanced", random_state=42, n_jobs=-1
        )
        clf.fit(X_train[train_idx], y_train[train_idx])
        oof_probs[val_idx] = clf.predict_proba(X_train[val_idx])[:, 1]
        
    # 3. Evaluate thresholds from 0.20 to 0.80 in steps of 0.05
    thresholds = np.arange(0.20, 0.81, 0.05)
    comparison_summary = []
    
    print("\nEvaluating thresholds on out-of-fold spatial CV predictions:")
    print("Thresh | Recall | Prec   | F1-Score | FPR    | FNR    | Confusion Matrix [TN, FP, FN, TP]")
    print("------------------------------------------------------------------------------------------")
    for t in thresholds:
        metrics = calculate_metrics_at_threshold(y_train, oof_probs, t)
        comparison_summary.append(metrics)
        cm_str = str(metrics["confusion_matrix"])
        print(f"{t:.2f}   | {metrics['recall']:.4f} | {metrics['precision']:.4f} | {metrics['f1']:.4f}   | {metrics['fpr']:.4f} | {metrics['fnr']:.4f} | {cm_str}")
        
    # 4. Select operating threshold:
    # Rule 1: Recall >= 0.85
    # Rule 2: Minimize False Positive Rate (FPR)
    # Rule 3: Prefer better F1-score
    candidates = [m for m in comparison_summary if m["recall"] >= 0.85]
    if not candidates:
        # Fallback to the one with max recall if none satisfy >= 0.85
        selected = max(comparison_summary, key=lambda x: x["recall"])
        print("\n[WARNING] No thresholds satisfied Recall >= 0.85. Selected threshold maximizing Recall.")
    else:
        # Sort by minimum FPR, then by maximum F1-score
        selected = min(candidates, key=lambda x: (x["fpr"], -x["f1"]))
        
    selected_threshold = selected["threshold"]
    print(f"\nOptimal Operating Threshold Selected: {selected_threshold:.2f}")
    
    # 5. Evaluate default 0.50 threshold vs Selected
    default_metrics = next(m for m in comparison_summary if abs(m["threshold"] - 0.50) < 0.001)
    
    # 6. Evaluate the already-trained model (from model_path) on the Sikkim holdout
    print("\nLoading finalized trained model binary for stress testing on Sikkim holdout...")
    model = joblib.load(model_path)
    
    holdout_probs = model.predict_proba(X_holdout)[:, 1]
    holdout_metrics_cal = calculate_metrics_at_threshold(y_holdout, holdout_probs, selected_threshold)
    holdout_metrics_def = calculate_metrics_at_threshold(y_holdout, holdout_probs, 0.50)
    
    print("\n=== Sikkim holdout stress test comparison ===")
    print(f"Sikkim holdout results (Default 0.50):  Recall={holdout_metrics_def['recall']:.4f} | Prec={holdout_metrics_def['precision']:.4f} | FPR={holdout_metrics_def['fpr']:.4f}")
    print(f"Sikkim holdout results (Calibrated {selected_threshold:.2f}): Recall={holdout_metrics_cal['recall']:.4f} | Prec={holdout_metrics_cal['precision']:.4f} | FPR={holdout_metrics_cal['fpr']:.4f}")
    print("  *Caveat: Sikkim holdout scores are inflated by high-altitude easy negatives, use for secondary stress test only.*")
    
    # 7. Update model_metadata.json
    with open(metadata_path, "r", encoding="utf-8") as f:
        meta = json.load(f)
        
    # Append calibration section
    meta["calibration"] = {
        "selected_threshold": selected_threshold,
        "threshold_selection_method": "Recall >= 0.85, then minimize FPR, then maximize F1 on Spatial OOF CV predictions",
        "default_threshold_metrics_oof": {
            "recall": default_metrics["recall"],
            "precision": default_metrics["precision"],
            "f1": default_metrics["f1"],
            "fpr": default_metrics["fpr"],
            "confusion_matrix": default_metrics["confusion_matrix"]
        },
        "calibrated_threshold_metrics_oof": {
            "recall": selected["recall"],
            "precision": selected["precision"],
            "f1": selected["f1"],
            "fpr": selected["fpr"],
            "confusion_matrix": selected["confusion_matrix"]
        },
        "sikkim_holdout_evaluation": {
            "evaluation_caveat": "Sikkim holdout scores are geographically inflated by northern high-altitude barren rock/ice regions, acting as a secondary stress test only.",
            "metrics_at_default_0.50": {
                "recall": holdout_metrics_def["recall"],
                "precision": holdout_metrics_def["precision"],
                "fpr": holdout_metrics_def["fpr"],
                "confusion_matrix": holdout_metrics_def["confusion_matrix"]
            },
            "metrics_at_calibrated": {
                "recall": holdout_metrics_cal["recall"],
                "precision": holdout_metrics_cal["precision"],
                "fpr": holdout_metrics_cal["fpr"],
                "confusion_matrix": holdout_metrics_cal["confusion_matrix"]
            }
        },
        "threshold_comparison_table": comparison_summary
    }
    
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)
        
    print(f"\nMetadata JSON file updated: {metadata_path}")
    
    # Final Output Summary
    print("\n=== Calibration Summary ===")
    print(f"Selected operating threshold: {selected_threshold:.2f}")
    print(f"CV metrics at calibrated threshold: Recall={selected['recall']:.4f} | Precision={selected['precision']:.4f} | FPR={selected['fpr']:.4f}")
    print(f"CV metrics at default 0.50 threshold:  Recall={default_metrics['recall']:.4f} | Precision={default_metrics['precision']:.4f} | FPR={default_metrics['fpr']:.4f}")
    print("Confirmation: Threshold selection used strictly spatial out-of-fold training region predictions.")
    print("===========================")

if __name__ == "__main__":
    run_calibration()
