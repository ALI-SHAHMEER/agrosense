"""
AgroSense Model Training Script
Trains all 5 ML models and saves them to disk.
Run: python -m app.ml.training.train_all
"""
import joblib
import numpy as np
import pandas as pd
from pathlib import Path
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor, GradientBoostingRegressor
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    classification_report, mean_absolute_error,
    mean_squared_error, r2_score,
)
from xgboost import XGBClassifier

DATA_DIR   = Path("app/ml/data")
MODELS_DIR = Path("models")
MODELS_DIR.mkdir(exist_ok=True)


def load_data(filename: str) -> pd.DataFrame:
    path = DATA_DIR / filename
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found. Run: python app/ml/data/generate_data.py"
        )
    return pd.read_csv(path)


# ── 1. Crop Stress Detection ──────────────────────────────────────────────────
def train_crop_stress():
    print("\n🌿 Training Crop Stress Detection Model...")
    df = load_data("crop_stress.csv")

    features = ["ndvi", "evi", "ndwi", "ndre", "lai", "ndvi_std", "ndvi_min", "ndvi_max"]
    X = df[features].values
    y = df["label"].values

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    scaler = StandardScaler()
    X_train_s = scaler.fit_transform(X_train)
    X_test_s  = scaler.transform(X_test)

    model = RandomForestClassifier(
        n_estimators=200,
        max_depth=12,
        min_samples_split=5,
        class_weight="balanced",
        random_state=42,
        n_jobs=-1,
    )
    model.fit(X_train_s, y_train)

    y_pred = model.predict(X_test_s)
    print(classification_report(y_test, y_pred,
          target_names=["Healthy", "Stressed", "Diseased"]))

    # Save model + scaler + metadata
    joblib.dump({
        "model":    model,
        "scaler":   scaler,
        "features": features,
        "classes":  ["Healthy", "Stressed", "Diseased"],
        "version":  "1.0.0",
    }, MODELS_DIR / "crop_stress.pkl")
    print("✅ Saved → models/crop_stress.pkl")


# ── 2. Irrigation Recommendation ──────────────────────────────────────────────
def train_irrigation():
    print("\n💧 Training Irrigation Recommendation Model...")
    df = load_data("irrigation.csv")

    features = ["ndwi", "ndvi", "lai", "soil_moisture_pct", "temp_celsius", "rainfall_mm"]
    X = df[features].values
    y = df["label"].values

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    scaler = StandardScaler()
    X_train_s = scaler.fit_transform(X_train)
    X_test_s  = scaler.transform(X_test)

    model = XGBClassifier(
        n_estimators=200,
        max_depth=6,
        learning_rate=0.1,
        subsample=0.8,
        colsample_bytree=0.8,
        use_label_encoder=False,
        eval_metric="mlogloss",
        random_state=42,
    )
    model.fit(X_train_s, y_train)

    y_pred = model.predict(X_test_s)
    labels = ["irrigate_now", "irrigate_soon", "adequate", "overwatered"]
    print(classification_report(y_test, y_pred, target_names=labels))

    joblib.dump({
        "model":    model,
        "scaler":   scaler,
        "features": features,
        "classes":  labels,
        "version":  "1.0.0",
    }, MODELS_DIR / "irrigation.pkl")
    print("✅ Saved → models/irrigation.pkl")


# ── 3. VRA Zones ──────────────────────────────────────────────────────────────
def train_vra_zones():
    print("\n🗺️  Training VRA Zone Model (K-Means + RF)...")
    df = load_data("vra_zones.csv")

    features = ["ndvi", "ndre", "ndwi", "evi", "lai", "ndvi_std"]
    X = df[features].values

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # K-Means for unsupervised zone discovery
    kmeans = KMeans(n_clusters=3, random_state=42, n_init=10)
    kmeans.fit(X_scaled)

    # Random Forest for supervised prediction (using labeled data)
    y = df["label"].values
    X_train, X_test, y_train, y_test = train_test_split(
        X_scaled, y, test_size=0.2, random_state=42
    )
    rf = RandomForestClassifier(n_estimators=150, random_state=42, n_jobs=-1)
    rf.fit(X_train, y_train)
    y_pred = rf.predict(X_test)
    print(classification_report(y_test, y_pred,
          target_names=["Low", "Medium", "High"]))

    joblib.dump({
        "kmeans":   kmeans,
        "rf_model": rf,
        "scaler":   scaler,
        "features": features,
        "zones":    ["Low", "Medium", "High"],
        "version":  "1.0.0",
    }, MODELS_DIR / "vra_zones.pkl")
    print("✅ Saved → models/vra_zones.pkl")


# ── 4. Yield Prediction ───────────────────────────────────────────────────────
def train_yield():
    print("\n📈 Training Yield Prediction Model...")
    df = load_data("yield.csv")

    features = [
        "ndvi_mean", "ndvi_max", "evi_mean", "ndre_mean", "lai_mean",
        "growing_days", "rainfall_total_mm", "temp_mean_celsius",
    ]
    X = df[features].values
    y = df["yield_tha"].values

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    scaler = StandardScaler()
    X_train_s = scaler.fit_transform(X_train)
    X_test_s  = scaler.transform(X_test)

    model = RandomForestRegressor(
        n_estimators=300,
        max_depth=15,
        min_samples_split=4,
        random_state=42,
        n_jobs=-1,
    )
    model.fit(X_train_s, y_train)

    y_pred = model.predict(X_test_s)
    mae  = mean_absolute_error(y_test, y_pred)
    rmse = np.sqrt(mean_squared_error(y_test, y_pred))
    r2   = r2_score(y_test, y_pred)
    print(f"  MAE:  {mae:.3f} t/ha")
    print(f"  RMSE: {rmse:.3f} t/ha")
    print(f"  R²:   {r2:.3f}")

    # Feature importance
    importances = dict(zip(features, model.feature_importances_))
    top = sorted(importances.items(), key=lambda x: x[1], reverse=True)[:3]
    print(f"  Top features: {top}")

    joblib.dump({
        "model":    model,
        "scaler":   scaler,
        "features": features,
        "version":  "1.0.0",
    }, MODELS_DIR / "yield.pkl")
    print("✅ Saved → models/yield.pkl")


# ── 5. Soil Assessment ────────────────────────────────────────────────────────
def train_soil():
    print("\n🧪 Training Soil Assessment Model...")
    df = load_data("soil.csv")

    features = ["ndvi", "ndwi", "bsi", "b2", "b3", "b4", "b8", "b11"]
    targets  = ["soil_ph", "salinity_ds_m", "organic_matter_pct"]

    X = df[features].values
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    models = {}
    for target in targets:
        y = df[target].values
        X_train, X_test, y_train, y_test = train_test_split(
            X_scaled, y, test_size=0.2, random_state=42
        )
        m = GradientBoostingRegressor(
            n_estimators=200,
            max_depth=5,
            learning_rate=0.08,
            subsample=0.8,
            random_state=42,
        )
        m.fit(X_train, y_train)
        y_pred = m.predict(X_test)
        mae = mean_absolute_error(y_test, y_pred)
        r2  = r2_score(y_test, y_pred)
        print(f"  {target}: MAE={mae:.3f}, R²={r2:.3f}")
        models[target] = m

    joblib.dump({
        "models":   models,
        "scaler":   scaler,
        "features": features,
        "targets":  targets,
        "version":  "1.0.0",
    }, MODELS_DIR / "soil.pkl")
    print("✅ Saved → models/soil.pkl")


# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 60)
    print("AgroSense — Model Training Pipeline")
    print("=" * 60)
    train_crop_stress()
    train_irrigation()
    train_vra_zones()
    train_yield()
    train_soil()
    print("\n" + "=" * 60)
    print("✅ All 5 models trained and saved to models/")
    print("=" * 60)
