"""
Static Landslide Susceptibility ML Training Pipeline - Phase 3 Checkpoint 11A

Splits the regional terrain dataset into a Sikkim holdout (using authoritative state bounds)
and a training region. Performs 5-fold Spatial GroupKFold CV to compare Logistic Regression
and Random Forest, trains the selected model on the full training region, evaluates on the
untouched Sikkim holdout, and serializes the model and metadata.
"""

import os
import sys
import csv
import json
import math
import time
from datetime import datetime
import numpy as np
import joblib

# Resolve backend directory and inject into path for imports
SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.abspath(os.path.join(SCRIPTS_DIR, ".."))
sys.path.insert(0, BACKEND_DIR)

from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import GroupKFold
from sklearn.metrics import roc_auc_score, precision_recall_curve, auc, recall_score, precision_score, f1_score, confusion_matrix
import sklearn

# ── Re-implementing point in polygon checks to run in-memory without disk overhead ────────
def _point_in_ring(x: float, y: float, ring: list) -> bool:
    """Ray-casting algorithm to check if point (x=lng, y=lat) is in a linear ring."""
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
    """Check if point is inside a polygon with optional holes."""
    if not _point_in_ring(x, y, polygon[0]):
        return False
    for hole in polygon[1:]:
        if _point_in_ring(x, y, hole):
            return False
    return True

def load_sikkim_polygon():
    geojson_path = os.path.join(BACKEND_DIR, "app", "data", "ner_boundary.geojson")
    if not os.path.exists(geojson_path):
        print(f"Warning: Boundary GeoJSON not found at: {geojson_path}. Falling back to bounding box.")
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
        # Fallback to general bounding box
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

def evaluate_predictions(y_true, y_probs, threshold=0.5):
    """Computes all requested metrics for a model predictions."""
    y_true = np.array(y_true)
    y_probs = np.array(y_probs)
    y_pred = (y_probs >= threshold).astype(int)
    
    auc_roc = roc_auc_score(y_true, y_probs)
    
    precision_curve, recall_curve, _ = precision_recall_curve(y_true, y_probs)
    auc_pr = auc(recall_curve, precision_curve)
    
    rec = recall_score(y_true, y_pred, zero_division=0)
    prec = precision_score(y_true, y_pred, zero_division=0)
    f1 = f1_score(y_true, y_pred, zero_division=0)
    
    cm = confusion_matrix(y_true, y_pred)
    tn, fp, fn, tp = cm.ravel()
    
    fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0
    fnr = fn / (fn + tp) if (fn + tp) > 0 else 0.0
    
    return {
        "roc_auc": auc_roc,
        "pr_auc": auc_pr,
        "recall": rec,
        "precision": prec,
        "f1": f1,
        "fpr": fpr,
        "fnr": fnr,
        "confusion_matrix": [int(tn), int(fp), int(fn), int(tp)]
    }

def run_training_pipeline():
    print("=== Starting Phase 3 Checkpoint 11A: Static Susceptibility ML Training ===")
    
    csv_path = os.path.join(BACKEND_DIR, "data", "ml", "static_training_terrain.csv")
    if not os.path.exists(csv_path):
        print(f"Error: training terrain CSV not found at: {csv_path}")
        sys.exit(1)
        
    # 1. Load data
    print(f"Loading dataset from: {csv_path}")
    samples = []
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            row["latitude"] = float(row["latitude"])
            row["longitude"] = float(row["longitude"])
            row["elevation"] = float(row["elevation"])
            row["slope"] = float(row["slope"])
            row["aspect_sin"] = float(row["aspect_sin"])
            row["aspect_cos"] = float(row["aspect_cos"])
            row["landslide_label"] = int(row["landslide_label"])
            samples.append(row)
            
    print(f"Total samples loaded: {len(samples)}")
    
    # 2. Split Sikkim holdout using the authoritative state polygon
    sikkim_poly = load_sikkim_polygon()
    
    train_region_samples = []
    sikkim_holdout_samples = []
    
    for s in samples:
        if is_in_sikkim(s["latitude"], s["longitude"], sikkim_poly):
            sikkim_holdout_samples.append(s)
        else:
            train_region_samples.append(s)
            
    print(f"Sikkim Holdout count:    {len(sikkim_holdout_samples)} (Pos={sum(1 for s in sikkim_holdout_samples if s['landslide_label'] == 1)}, Neg={sum(1 for s in sikkim_holdout_samples if s['landslide_label'] == 0)})")
    print(f"Training Region count:  {len(train_region_samples)} (Pos={sum(1 for s in train_region_samples if s['landslide_label'] == 1)}, Neg={sum(1 for s in train_region_samples if s['landslide_label'] == 0)})")
    
    # 3. Extract feature arrays and labels
    features = ["elevation", "slope", "aspect_sin", "aspect_cos"]
    
    X_train = np.array([[s[f] for f in features] for s in train_region_samples])
    y_train = np.array([s["landslide_label"] for s in train_region_samples])
    groups = np.array([s["spatial_block_id"] for s in train_region_samples])
    
    X_holdout = np.array([[s[f] for f in features] for s in sikkim_holdout_samples])
    y_holdout = np.array([s["landslide_label"] for s in sikkim_holdout_samples])
    
    # Check spatial validation suitability
    unique_blocks = len(np.unique(groups))
    print(f"Number of unique spatial blocks in training region: {unique_blocks}")
    
    # 4. Define cross-validation splitter (GroupKFold)
    gkf = GroupKFold(n_splits=5)
    
    # 5. Model 1: Logistic Regression Baseline
    print("\nRunning Spatial Cross-Validation: Logistic Regression Baseline...")
    lr_pipeline = Pipeline([
        ("scaler", StandardScaler()),
        ("lr", LogisticRegression(random_state=42))
    ])
    
    lr_cv_results = []
    for fold, (train_idx, val_idx) in enumerate(gkf.split(X_train, y_train, groups)):
        X_tr, y_tr = X_train[train_idx], y_train[train_idx]
        X_va, y_va = X_train[val_idx], y_train[val_idx]
        
        # Fit
        lr_pipeline.fit(X_tr, y_tr)
        # Predict probabilities
        y_probs = lr_pipeline.predict_proba(X_va)[:, 1]
        
        # Evaluate
        metrics = evaluate_predictions(y_va, y_probs)
        lr_cv_results.append(metrics)
        print(f"  Fold {fold+1} | ROC-AUC: {metrics['roc_auc']:.4f} | PR-AUC: {metrics['pr_auc']:.4f} | Recall: {metrics['recall']:.4f} | FPR: {metrics['fpr']:.4f}")
        
    # 6. Model 2: Random Forest Primary Model
    print("\nRunning Spatial Cross-Validation: Random Forest Primary Model...")
    rf_classifier = RandomForestClassifier(
        n_estimators=100,
        max_depth=6,
        min_samples_leaf=5,
        class_weight="balanced",
        random_state=42,
        n_jobs=-1
    )
    
    rf_cv_results = []
    for fold, (train_idx, val_idx) in enumerate(gkf.split(X_train, y_train, groups)):
        X_tr, y_tr = X_train[train_idx], y_train[train_idx]
        X_va, y_va = X_train[val_idx], y_train[val_idx]
        
        # Fit
        rf_classifier.fit(X_tr, y_tr)
        # Predict
        y_probs = rf_classifier.predict_proba(X_va)[:, 1]
        
        # Evaluate
        metrics = evaluate_predictions(y_va, y_probs)
        rf_cv_results.append(metrics)
        print(f"  Fold {fold+1} | ROC-AUC: {metrics['roc_auc']:.4f} | PR-AUC: {metrics['pr_auc']:.4f} | Recall: {metrics['recall']:.4f} | FPR: {metrics['fpr']:.4f}")
        
    # 7. Aggregate Cross-Validation Metrics
    lr_summary = {}
    rf_summary = {}
    
    for metric_name in ["roc_auc", "pr_auc", "recall", "precision", "f1", "fpr", "fnr"]:
        lr_vals = [res[metric_name] for res in lr_cv_results]
        rf_vals = [res[metric_name] for res in rf_cv_results]
        
        lr_summary[metric_name] = (np.mean(lr_vals), np.std(lr_vals))
        rf_summary[metric_name] = (np.mean(rf_vals), np.std(rf_vals))
        
    print("\n=== Cross-Validation Aggregated Summary (Mean ± Std) ===")
    print("Metric     | Logistic Regression Baseline | Random Forest Primary Model")
    print("-----------------------------------------------------------------------")
    for k in lr_summary.keys():
        print(f"{k:10s} | {lr_summary[k][0]:.4f} ± {lr_summary[k][1]:.4f}      | {rf_summary[k][0]:.4f} ± {rf_summary[k][1]:.4f}")
        
    # 8. Model Selection Decision
    # Random Forest is selected if it has higher mean PR-AUC and Recall
    rf_selected = (rf_summary["pr_auc"][0] >= lr_summary["pr_auc"][0]) and (rf_summary["recall"][0] >= lr_summary["recall"][0])
    selected_name = "Random Forest Classifier" if rf_selected else "Logistic Regression Pipeline"
    print(f"\nModel Selection: Fused PR-AUC + Recall evaluation selects: {selected_name}")
    
    # 9. Train selected final model on the entire non-Sikkim training region
    print(f"\nTraining final model ({selected_name}) on full training region...")
    if rf_selected:
        final_model = RandomForestClassifier(
            n_estimators=100,
            max_depth=6,
            min_samples_leaf=5,
            class_weight="balanced",
            random_state=42,
            n_jobs=-1
        )
    else:
        final_model = Pipeline([
            ("scaler", StandardScaler()),
            ("lr", LogisticRegression(random_state=42))
        ])
        
    final_model.fit(X_train, y_train)
    
    # 10. Single Evaluation on the Untouched Sikkim Holdout Set
    print("Evaluating final model on untouched Sikkim holdout set...")
    holdout_probs = final_model.predict_proba(X_holdout)[:, 1]
    holdout_metrics = evaluate_predictions(y_holdout, holdout_probs)
    
    print("\n=== Sikkim Holdout Final Performance ===")
    print(f"  ROC-AUC:   {holdout_metrics['roc_auc']:.4f}")
    print(f"  PR-AUC:    {holdout_metrics['pr_auc']:.4f}")
    print(f"  Recall:    {holdout_metrics['recall']:.4f}")
    print(f"  Precision: {holdout_metrics['precision']:.4f}")
    print(f"  F1-Score:  {holdout_metrics['f1']:.4f}")
    print(f"  FPR / FNR: {holdout_metrics['fpr']:.4f} / {holdout_metrics['fnr']:.4f}")
    print(f"  Confusion Matrix [TN, FP, FN, TP]: {holdout_metrics['confusion_matrix']}")
    
    # 11. Save model binaries & metadata
    models_dir = os.path.join(BACKEND_DIR, "data", "ml", "models")
    os.makedirs(models_dir, exist_ok=True)
    
    model_path = os.path.join(models_dir, "static_susceptibility_model.pkl")
    metadata_path = os.path.join(models_dir, "model_metadata.json")
    
    joblib.dump(final_model, model_path)
    print(f"\nSerialized final model binary saved to: {model_path}")
    
    # Build JSON metadata payload
    metadata = {
        "model_type": selected_name,
        "feature_list": features,
        "dataset_sample_counts": {
            "total_records": len(samples),
            "sikkim_holdout_records": len(sikkim_holdout_samples),
            "training_region_records": len(train_region_samples)
        },
        "spatial_block_details": {
            "total_blocks": unique_blocks
        },
        "cross_validation_metrics": {
            "logistic_regression": {
                k: {"mean": float(lr_summary[k][0]), "std": float(lr_summary[k][1])} for k in lr_summary.keys()
            },
            "random_forest": {
                k: {"mean": float(rf_summary[k][0]), "std": float(rf_summary[k][1])} for k in rf_summary.keys()
            }
        },
        "sikkim_holdout_metrics": {
            "roc_auc": float(holdout_metrics["roc_auc"]),
            "pr_auc": float(holdout_metrics["pr_auc"]),
            "recall": float(holdout_metrics["recall"]),
            "precision": float(holdout_metrics["precision"]),
            "f1": float(holdout_metrics["f1"]),
            "fpr": float(holdout_metrics["fpr"]),
            "fnr": float(holdout_metrics["fnr"]),
            "confusion_matrix": holdout_metrics["confusion_matrix"]
        },
        "environment_metadata": {
            "training_timestamp": datetime.utcnow().isoformat() + "Z",
            "random_seed": 42,
            "scikit_learn_version": sklearn.__version__
        }
    }
    
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)
        
    print(f"Serialized model JSON metadata saved to: {metadata_path}")
    print("\n=== Model Training Complete ===")

if __name__ == "__main__":
    run_training_pipeline()
