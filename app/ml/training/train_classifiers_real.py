"""
Retrain the 3 classifiers on 84 real Sentinel-2 samples.

Labels are derived from spectral composite scores using agronomic logic
(no ground-truth labels exist in the field data).  Evaluation is via
5-fold stratified CV — holdout split is too small at n=84.
Final model is fit on all 84 samples before saving.
"""
import numpy as np
import pandas as pd
import joblib
from pathlib import Path
from sklearn.ensemble import RandomForestClassifier
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.metrics import classification_report
from xgboost import XGBClassifier

DATA_PATH  = Path("app/ml/data/real_pakistan_sentinel2.csv")
MODELS_DIR = Path("models")


def load_real() -> pd.DataFrame:
    df = pd.read_csv(DATA_PATH)
    print(f"Loaded {len(df)} samples — "
          f"{df['location_id'].nunique()} sites × {df['season'].nunique()} seasons\n")
    return df


# ── Label derivation ──────────────────────────────────────────────────────────

def make_stress_labels(df: pd.DataFrame) -> np.ndarray:
    """Tertile split on vegetation health composite (NDVI + NDRE + EVI)."""
    score = 0.5 * df["ndvi"] + 0.3 * df["ndre"] + 0.2 * df["evi"]
    q33, q66 = score.quantile([1 / 3, 2 / 3])
    return np.where(score >= q66, 0, np.where(score >= q33, 1, 2))
    # 0=Healthy  1=Stressed  2=Diseased


def make_irrigation_labels(df: pd.DataFrame) -> np.ndarray:
    """Quartile split on water-availability composite (NDWI + soil_moisture)."""
    sm_norm = df["soil_moisture"] / df["soil_moisture"].max()
    score   = 0.6 * df["ndwi"] + 0.4 * sm_norm
    q25, q50, q75 = score.quantile([0.25, 0.50, 0.75])
    return np.where(score < q25, 0,
           np.where(score < q50, 1,
           np.where(score < q75, 2, 3)))
    # 0=irrigate_now  1=irrigate_soon  2=adequate  3=overwatered


def make_vra_labels(df: pd.DataFrame) -> np.ndarray:
    """Tertile split on productivity composite (NDVI + NDRE + LAI)."""
    lai_norm = df["lai"] / df["lai"].max()
    score    = 0.5 * df["ndvi"] + 0.3 * df["ndre"] + 0.2 * lai_norm
    q33, q66 = score.quantile([1 / 3, 2 / 3])
    return np.where(score >= q66, 2, np.where(score >= q33, 1, 0))
    # 0=Low  1=Medium  2=High


# ── Training helpers ──────────────────────────────────────────────────────────

def _cv_eval(model, X: np.ndarray, y: np.ndarray, class_names: list) -> None:
    cv     = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    scores = cross_val_score(model, X, y, cv=cv, scoring="accuracy")
    print(f"  5-fold CV accuracy : {scores.mean():.3f} ± {scores.std():.3f}")
    print(f"  Per-fold           : {[round(s, 3) for s in scores]}")

    # Full-data fit for the classification report (optimistic, shown for reference)
    model.fit(X, y)
    print("\n  Classification report (fit on all 84 — for reference only):")
    print(classification_report(y, model.predict(X), target_names=class_names,
                                zero_division=0))


# ── 1. Crop Stress ────────────────────────────────────────────────────────────

def train_crop_stress(df: pd.DataFrame) -> None:
    print("=" * 55)
    print("🌿  Crop Stress — real data")
    print("=" * 55)
    features = ["ndvi", "evi", "ndwi", "ndre", "lai",
                "ndvi_std", "ndvi_min", "ndvi_max"]
    classes  = ["Healthy", "Stressed", "Diseased"]

    X = df[features].values
    y = make_stress_labels(df)

    vals, counts = np.unique(y, return_counts=True)
    print(f"  Class distribution : "
          + "  ".join(f"{classes[v]}={c}" for v, c in zip(vals, counts)))

    scaler = StandardScaler()
    X_s    = scaler.fit_transform(X)

    model = RandomForestClassifier(
        n_estimators=200, max_depth=8, min_samples_split=4,
        class_weight="balanced", random_state=42, n_jobs=-1,
    )
    _cv_eval(model, X_s, y, classes)

    joblib.dump({
        "model":    model,
        "scaler":   scaler,
        "features": features,
        "classes":  classes,
        "version":  "2.0.0-real",
    }, MODELS_DIR / "crop_stress.pkl")
    print("  ✅ Saved → models/crop_stress.pkl\n")


# ── 2. Irrigation ─────────────────────────────────────────────────────────────

def train_irrigation(df: pd.DataFrame) -> None:
    print("=" * 55)
    print("💧  Irrigation — real data")
    print("=" * 55)
    # soil_moisture in real data == soil_moisture_pct expected by predictor
    features = ["ndwi", "ndvi", "lai", "soil_moisture",
                "temp_celsius", "rainfall_mm"]
    classes  = ["irrigate_now", "irrigate_soon", "adequate", "overwatered"]

    X = df[features].values
    y = make_irrigation_labels(df)

    vals, counts = np.unique(y, return_counts=True)
    print(f"  Class distribution : "
          + "  ".join(f"{classes[v]}={c}" for v, c in zip(vals, counts)))

    scaler = StandardScaler()
    X_s    = scaler.fit_transform(X)

    model = XGBClassifier(
        n_estimators=100, max_depth=4, learning_rate=0.1,
        subsample=0.8, colsample_bytree=0.8,
        eval_metric="mlogloss", random_state=42,
    )
    _cv_eval(model, X_s, y, classes)

    joblib.dump({
        "model":    model,
        "scaler":   scaler,
        "features": features,
        "classes":  classes,
        "version":  "2.0.0-real",
    }, MODELS_DIR / "irrigation.pkl")
    print("  ✅ Saved → models/irrigation.pkl\n")


# ── 3. VRA Zones ──────────────────────────────────────────────────────────────

def train_vra_zones(df: pd.DataFrame) -> None:
    print("=" * 55)
    print("🗺️   VRA Zones — real data")
    print("=" * 55)
    features = ["ndvi", "ndre", "ndwi", "evi", "lai", "ndvi_std"]
    zones    = ["Low", "Medium", "High"]

    X = df[features].values
    y = make_vra_labels(df)

    vals, counts = np.unique(y, return_counts=True)
    print(f"  Class distribution : "
          + "  ".join(f"{zones[v]}={c}" for v, c in zip(vals, counts)))

    scaler = StandardScaler()
    X_s    = scaler.fit_transform(X)

    rf = RandomForestClassifier(
        n_estimators=150, max_depth=8, class_weight="balanced",
        random_state=42, n_jobs=-1,
    )
    _cv_eval(rf, X_s, y, zones)

    kmeans = KMeans(n_clusters=3, random_state=42, n_init=10)
    kmeans.fit(X_s)

    joblib.dump({
        "kmeans":   kmeans,
        "rf_model": rf,
        "scaler":   scaler,
        "features": features,
        "zones":    zones,
        "version":  "2.0.0-real",
    }, MODELS_DIR / "vra_zones.pkl")
    print("  ✅ Saved → models/vra_zones.pkl\n")


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("\n" + "=" * 55)
    print("AgroSense — Retrain Classifiers on Real Sentinel-2 Data")
    print("=" * 55 + "\n")
    df = load_real()
    train_crop_stress(df)
    train_irrigation(df)
    train_vra_zones(df)
    print("=" * 55)
    print("✅ All 3 classifiers retrained on real data")
    print("=" * 55 + "\n")
