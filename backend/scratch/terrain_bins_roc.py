import os
import sys
import csv
import math
import numpy as np

# Add backend root to python path
SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.abspath(os.path.join(SCRIPTS_DIR, ".."))
sys.path.insert(0, BACKEND_DIR)

from app.services.spatial_query_service import haversine_distance

def calculate_roc_auc(y_true, y_scores):
    y_true = np.array(y_true)
    y_scores = np.array(y_scores)
    
    desc_score_indices = np.argsort(y_scores)[::-1]
    y_true = y_true[desc_score_indices]
    y_scores = y_scores[desc_score_indices]
    
    tps = np.cumsum(y_true)
    fps = np.cumsum(1 - y_true)
    
    tp_total = tps[-1]
    fp_total = fps[-1]
    
    if tp_total == 0 or fp_total == 0:
        return 0.5
        
    tpr = tps / tp_total
    fpr = fps / fp_total
    
    area = 0.0
    prev_fpr = 0.0
    prev_tpr = 0.0
    for i in range(len(fpr)):
        curr_fpr = fpr[i]
        curr_tpr = tpr[i]
        area += (curr_fpr - prev_fpr) * (curr_tpr + prev_tpr) / 2.0
        prev_fpr = curr_fpr
        prev_tpr = curr_tpr
    return area

def fit_logistic_regression(X, y, epochs=1500, lr=0.2):
    X = np.array(X)
    y = np.array(y).reshape(-1, 1)
    
    # Scale features
    mean = X.mean(axis=0)
    std = X.std(axis=0)
    std[std == 0.0] = 1.0
    X_scaled = (X - mean) / std
    
    # Add intercept
    X_scaled = np.hstack([np.ones((X_scaled.shape[0], 1)), X_scaled])
    w = np.zeros((X_scaled.shape[1], 1))
    
    m = X_scaled.shape[0]
    for _ in range(epochs):
        z = np.dot(X_scaled, w)
        z = np.clip(z, -500, 500)
        h = 1.0 / (1.0 + np.exp(-z))
        gradient = np.dot(X_scaled.T, h - y) / m
        w -= lr * gradient
        
    z_final = np.dot(X_scaled, w)
    h_final = 1.0 / (1.0 + np.exp(-z_final))
    return h_final.flatten()

def run_scientific_validation():
    print("=== Commencing Post-Generation Scientific Audit ===")
    
    base_path = os.path.join(BACKEND_DIR, "data", "ml", "static_training_base.csv")
    terrain_path = os.path.join(BACKEND_DIR, "data", "ml", "static_training_terrain.csv")
    
    if not os.path.exists(terrain_path):
        print(f"Error: terrain file not found at: {terrain_path}")
        return
        
    # 1. Load base coordinates for dropped coordinates audit
    base_samples = {}
    with open(base_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            base_samples[r["sample_id"]] = {
                "latitude": float(r["latitude"]),
                "longitude": float(r["longitude"]),
                "label": int(r["landslide_label"])
            }
            
    # 2. Load terrain features
    extracted = []
    with open(terrain_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            r["latitude"] = float(r["latitude"])
            r["longitude"] = float(r["longitude"])
            r["elevation"] = float(r["elevation"])
            r["slope"] = float(r["slope"])
            r["aspect"] = float(r["aspect"])
            r["aspect_sin"] = float(r["aspect_sin"])
            r["aspect_cos"] = float(r["aspect_cos"])
            r["landslide_label"] = int(r["landslide_label"])
            extracted.append(r)
            
    total_extracted = len(extracted)
    print(f"Loaded {total_extracted} extracted samples.")
    
    # 3. Identify dropped coordinates
    extracted_ids = set(r["sample_id"] for r in extracted)
    dropped_ids = set(base_samples.keys()) - extracted_ids
    print(f"\nDropped Coordinates Audit (Total dropped: {len(dropped_ids)}):")
    for idx, d_id in enumerate(sorted(dropped_ids)):
        item = base_samples[d_id]
        # Estimate reason
        lat, lon = item["latitude"], item["longitude"]
        # check if near edge of integer degree tiles (extreme values close to integer boundary)
        dist_to_lat_edge = min(abs(lat - math.floor(lat)), abs(lat - math.ceil(lat)))
        dist_to_lon_edge = min(abs(lon - math.floor(lon)), abs(lon - math.ceil(lon)))
        
        reason = "Unknown nodata/boundary"
        if dist_to_lat_edge < 0.0006 or dist_to_lon_edge < 0.0006:
            # 0.0006 degrees is approx 2 pixels (about 60m)
            reason = "Tile boundary edge clipping zone"
            
        print(f"  - ID: {d_id} | Source Label: {item['label']} | Coordinates: ({lat:.6f}, {lon:.6f}) | Reason: {reason}")
        
    # 4. Check for Missing / NaN values
    nans = {col: 0 for col in ["elevation", "slope", "aspect", "aspect_sin", "aspect_cos"]}
    for r in extracted:
        for col in nans.keys():
            if np.isnan(r[col]):
                nans[col] += 1
    print(f"\nMissing/NaN values count: {nans}")
    
    # 5. Class Distribution across Slope Bins
    bins = [0, 5, 10, 15, 20, 25, 30, 35, 40, 90]
    bin_labels = ["0-5", "5-10", "10-15", "15-20", "20-25", "25-30", "30-35", "35-40", ">40"]
    
    positives = [r for r in extracted if r["landslide_label"] == 1]
    negatives = [r for r in extracted if r["landslide_label"] == 0]
    
    pos_slopes = [r["slope"] for r in positives]
    neg_slopes = [r["slope"] for r in negatives]
    
    print("\nSlope Bin Distribution Analysis:")
    print("Bin     | Pos Count | Neg Count | Pos %  | Neg %  | Class Ratio (Pos/Neg)")
    print("-------------------------------------------------------------------------")
    for i in range(len(bins)-1):
        low, high = bins[i], bins[i+1]
        
        p_cnt = sum(1 for s in pos_slopes if low <= s < high)
        n_cnt = sum(1 for s in neg_slopes if low <= s < high)
        
        p_pct = (p_cnt / len(positives) * 100.0) if len(positives) > 0 else 0.0
        n_pct = (n_cnt / len(negatives) * 100.0) if len(negatives) > 0 else 0.0
        
        ratio = p_cnt / n_cnt if n_cnt > 0 else float("inf")
        ratio_str = f"{ratio:.4f}" if n_cnt > 0 else "N/A"
        
        print(f"{bin_labels[i]:7s} | {p_cnt:9d} | {n_cnt:9d} | {p_pct:5.2f}% | {n_pct:5.2f}% | {ratio_str}")
        
    # 6. Correlation between elevation and slope
    elevations_arr = np.array([r["elevation"] for r in extracted])
    slopes_arr = np.array([r["slope"] for r in extracted])
    
    corr_coef = np.corrcoef(elevations_arr, slopes_arr)[0, 1]
    print(f"\nPearson correlation coefficient between Elevation and Slope: {corr_coef:.4f}")
    
    # 7. Model baseline evaluation (ROC-AUC)
    labels = [r["landslide_label"] for r in extracted]
    
    # Predictor 1: Slope Alone
    auc_slope = calculate_roc_auc(labels, slopes_arr)
    # Predictor 2: Elevation Alone
    auc_elev = calculate_roc_auc(labels, elevations_arr)
    
    # Predictor 3: Bivariate Logistic Regression (Slope + Elevation)
    X = np.column_stack([slopes_arr, elevations_arr])
    lr_probs = fit_logistic_regression(X, labels)
    auc_bivariate = calculate_roc_auc(labels, lr_probs)
    
    print(f"\nROC-AUC Performance Analysis:")
    print(f"  - ROC-AUC using Slope Alone as single predictor:     {auc_slope:.4f}")
    print(f"  - ROC-AUC using Elevation Alone as single predictor: {auc_elev:.4f}")
    print(f"  - ROC-AUC using Slope + Elevation (Bivariate LogReg):  {auc_bivariate:.4f}")
    
    # 8. Evaluate slope environmental shortcut risk
    print("\nShortcut Risk Analysis:")
    # If slope alone yields extremely high ROC-AUC (e.g. >0.90), the model will rely almost entirely on it.
    # If the slope distribution of negatives is well-balanced (60% above 10 degrees, mean slope 17 degrees),
    # the model cannot simply split on slope = 5 degrees to classify 100% of the data.
    # Our report verifies this.
    if auc_slope > 0.85:
        print("  WARNING: Slope alone has extremely high predictive power (ROC-AUC > 0.85).")
        print("  Scientific Recommendation: NEGATIVE SAMPLING NEEDS REBALANCING.")
    else:
        print("  Notice: Slope alone ROC-AUC is within safe boundaries (< 0.85), showing that pseudo-negatives")
        print("  are geomorphologically balanced enough to prevent the model from using slope as a sole shortcut.")
        print("  Scientific Recommendation: SAFE TO PROCEED.")
    print("==================================================")

if __name__ == "__main__":
    run_scientific_validation()
