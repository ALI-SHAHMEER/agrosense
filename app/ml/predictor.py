"""
ML Prediction Service
Loads trained models from disk and runs inference on field vegetation indices.
"""
import joblib
import numpy as np
from pathlib import Path
from functools import lru_cache

MODELS_DIR = Path("models")


@lru_cache(maxsize=None)
def _load(name: str) -> dict:
    path = MODELS_DIR / f"{name}.pkl"
    if not path.exists():
        raise FileNotFoundError(
            f"Model '{name}' not found at {path}. "
            f"Run: python -m app.ml.training.train_all"
        )
    return joblib.load(path)


# ── 1. Crop Stress ────────────────────────────────────────────────────────────

def predict_crop_stress(indices: dict) -> dict:
    """
    Predict crop health status from vegetation indices.
    Returns class label + probabilities for all classes.
    """
    bundle = _load("crop_stress")
    model  = bundle["model"]
    scaler = bundle["scaler"]

    X = np.array([[
        indices.get("ndvi",     0),
        indices.get("evi",      0),
        indices.get("ndwi",     0),
        indices.get("ndre",     0),
        indices.get("lai",      0),
        indices.get("ndvi_std", 0),
        indices.get("ndvi_min", 0),
        indices.get("ndvi_max", 0),
    ]])
    X_scaled = scaler.transform(X)
    pred     = model.predict(X_scaled)[0]
    probs    = model.predict_proba(X_scaled)[0]
    classes  = bundle["classes"]

    return {
        "prediction":   classes[pred],
        "confidence":   round(float(probs[pred]), 4),
        "probabilities": {
            cls: round(float(p), 4)
            for cls, p in zip(classes, probs)
        },
    }


# ── 2. Irrigation ─────────────────────────────────────────────────────────────

def predict_irrigation(indices: dict, weather: dict = None) -> dict:
    """
    Predict irrigation recommendation.
    weather: optional dict with temp_celsius, rainfall_mm
    """
    bundle = _load("irrigation")
    model  = bundle["model"]
    scaler = bundle["scaler"]
    weather = weather or {}

    # Estimate soil moisture from NDWI if not provided
    ndwi = indices.get("ndwi", 0)
    soil_moisture = weather.get("soil_moisture_pct") or max(0, (ndwi + 0.6) * 60)

    X = np.array([[
        ndwi,
        indices.get("ndvi", 0),
        indices.get("lai",  0),
        soil_moisture,
        weather.get("temp_celsius", 28),
        weather.get("rainfall_mm",  10),
    ]])
    X_scaled = scaler.transform(X)
    pred     = model.predict(X_scaled)[0]
    probs    = model.predict_proba(X_scaled)[0]
    classes  = bundle["classes"]

    # Recommended water amount (mm) based on soil moisture deficit
    water_needed = max(0, round((60 - soil_moisture) * 0.5, 1))

    return {
        "recommendation":    classes[pred],
        "confidence":        round(float(probs[pred]), 4),
        "soil_moisture_pct": round(soil_moisture, 1),
        "water_amount_mm":   water_needed,
        "probabilities": {
            cls: round(float(p), 4)
            for cls, p in zip(classes, probs)
        },
    }


# ── 3. VRA Zones ──────────────────────────────────────────────────────────────

def predict_vra_zone(indices: dict) -> dict:
    """
    Predict fertility zone for variable rate application.
    Returns zone label + fertiliser recommendation.
    """
    bundle = _load("vra_zones")
    scaler = bundle["scaler"]
    rf     = bundle["rf_model"]

    X = np.array([[
        indices.get("ndvi",     0),
        indices.get("ndre",     0),
        indices.get("ndwi",     0),
        indices.get("evi",      0),
        indices.get("lai",      0),
        indices.get("ndvi_std", 0),
    ]])
    X_scaled = scaler.transform(X)
    pred     = rf.predict(X_scaled)[0]
    probs    = rf.predict_proba(X_scaled)[0]
    zones    = bundle["zones"]

    fertiliser_map = {
        "Low":    "Apply 120 kg/ha NPK — soil needs full nutrition",
        "Medium": "Apply 80 kg/ha NPK — moderate supplementation",
        "High":   "Apply 40 kg/ha NPK — soil is fertile, reduce input",
    }
    zone_name = zones[pred]

    return {
        "zone":                  zone_name,
        "confidence":            round(float(probs[pred]), 4),
        "fertiliser_recommendation": fertiliser_map[zone_name],
        "probabilities": {
            z: round(float(p), 4)
            for z, p in zip(zones, probs)
        },
    }


# ── 4. Yield Prediction ───────────────────────────────────────────────────────

def predict_yield(indices: dict, growing_days: int = 120, rainfall_mm: float = 200,
                  temp_celsius: float = 26, crop_type: str = 'wheat') -> dict:
    """
    Predict crop yield in tons per hectare.
    Returns point estimate + 95% confidence interval.
    """
    bundle = _load("yield")
    model  = bundle["model"]
    scaler = bundle["scaler"]

    crop_map  = bundle.get("crop_map",
                    {"wheat":0,"rice":1,"cotton":2,"sugarcane":3,"mango":4})
    crop_enc  = float(crop_map.get(str(crop_type).lower(), 0))
    X = np.array([[
        float(indices.get("ndvi",  0)),
        float(indices.get("ndvi",  0)) + 0.1,
        float(indices.get("evi",   0)),
        float(indices.get("ndre",  0)),
        float(indices.get("lai",   0)),
        float(growing_days),
        float(rainfall_mm),
        float(temp_celsius),
        crop_enc,
    ]])
    X_scaled     = scaler.transform(X)
    yield_pred   = float(model.predict(X_scaled)[0])

    # Estimate uncertainty from tree variance
    tree_preds   = np.array([t.predict(X_scaled)[0] for t in model.estimators_])
    std          = float(np.std(tree_preds))
    lower        = round(max(0, yield_pred - 1.96 * std), 3)
    upper        = round(yield_pred + 1.96 * std, 3)

    return {
        "predicted_yield_tha":  round(yield_pred, 3),
        "yield_lower_bound":    lower,
        "yield_upper_bound":    upper,
        "harvest_readiness_pct": min(100, round((growing_days / 120) * 100, 1)),
    }


# ── 5. Soil Assessment ────────────────────────────────────────────────────────

def predict_soil(indices: dict, bands: dict = None) -> dict:
    """
    Predict soil properties from spectral indices and bands.
    bands: optional dict with b2, b3, b4, b8, b11
    """
    bundle = _load("soil")
    scaler = bundle["scaler"]
    models = bundle["models"]
    bands  = bands or {}

    ndvi = indices.get("ndvi", 0)
    ndwi = indices.get("ndwi", 0)
    b2   = bands.get("b2", 0.05)
    b3   = bands.get("b3", 0.08)
    b4   = bands.get("b4", 0.07)
    b8   = bands.get("b8", 0.30)
    b11  = bands.get("b11", 0.15)
    bsi  = ((b11 + b4) - (b8 + b2)) / ((b11 + b4) + (b8 + b2) + 1e-6)

    X = np.array([[ndvi, ndwi, bsi, b2, b3, b4, b8, b11]])
    X_scaled = scaler.transform(X)

    results = {}
    for target, model in models.items():
        results[target] = round(float(model.predict(X_scaled)[0]), 3)

    # Interpretation
    ph = results.get("soil_ph", 7.0)
    sal = results.get("salinity_ds_m", 1.0)
    om  = results.get("organic_matter_pct", 2.0)

    ph_status  = "Optimal" if 6.0 <= ph <= 7.5 else ("Acidic" if ph < 6.0 else "Alkaline")
    sal_status = "Normal" if sal < 2.0 else ("Moderate" if sal < 4.0 else "High — leaching needed")
    om_status  = "Good" if om > 2.5 else ("Low — add compost" if om > 1.0 else "Very low — critical")

    return {
        "soil_ph":               results.get("soil_ph"),
        "salinity_ds_m":         results.get("salinity_ds_m"),
        "organic_matter_pct":    results.get("organic_matter_pct"),
        "ph_status":             ph_status,
        "salinity_status":       sal_status,
        "organic_matter_status": om_status,
    }
