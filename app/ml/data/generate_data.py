"""
Training Data Generator
Generates realistic synthetic data for all 5 AgroSense ML models.
Based on published agronomic research for South Asian crops.
Run once to create training datasets before model training.
"""
import numpy as np
import pandas as pd
from pathlib import Path

np.random.seed(42)
DATA_DIR = Path("app/ml/data")
DATA_DIR.mkdir(parents=True, exist_ok=True)

N = 5000  # samples per dataset


# ── 1. Crop Stress Dataset ────────────────────────────────────────────────────
def generate_crop_stress_data():
    """
    Features: NDVI, EVI, NDWI, NDRE, LAI, ndvi_std, ndvi_min, ndvi_max
    Labels  : 0=Healthy, 1=Stressed, 2=Diseased
    """
    data = []
    labels = []

    for _ in range(N // 3):
        # Healthy crops (NDVI > 0.5)
        ndvi = np.random.uniform(0.5, 0.9)
        data.append({
            "ndvi":     ndvi,
            "evi":      ndvi * np.random.uniform(0.6, 0.8),
            "ndwi":     np.random.uniform(-0.1, 0.3),
            "ndre":     np.random.uniform(0.3, 0.6),
            "lai":      np.random.uniform(2.5, 6.0),
            "ndvi_std": np.random.uniform(0.02, 0.08),
            "ndvi_min": ndvi - np.random.uniform(0.1, 0.2),
            "ndvi_max": ndvi + np.random.uniform(0.05, 0.15),
        })
        labels.append(0)

        # Stressed crops (NDVI 0.2–0.5)
        ndvi = np.random.uniform(0.2, 0.5)
        data.append({
            "ndvi":     ndvi,
            "evi":      ndvi * np.random.uniform(0.5, 0.7),
            "ndwi":     np.random.uniform(-0.3, 0.0),
            "ndre":     np.random.uniform(0.1, 0.3),
            "lai":      np.random.uniform(0.8, 2.5),
            "ndvi_std": np.random.uniform(0.08, 0.15),
            "ndvi_min": ndvi - np.random.uniform(0.15, 0.25),
            "ndvi_max": ndvi + np.random.uniform(0.05, 0.12),
        })
        labels.append(1)

        # Diseased crops (NDVI < 0.2, irregular pattern)
        ndvi = np.random.uniform(0.0, 0.2)
        data.append({
            "ndvi":     ndvi,
            "evi":      ndvi * np.random.uniform(0.3, 0.6),
            "ndwi":     np.random.uniform(-0.5, -0.1),
            "ndre":     np.random.uniform(0.0, 0.15),
            "lai":      np.random.uniform(0.1, 0.8),
            "ndvi_std": np.random.uniform(0.12, 0.25),
            "ndvi_min": max(0, ndvi - np.random.uniform(0.1, 0.2)),
            "ndvi_max": ndvi + np.random.uniform(0.1, 0.3),
        })
        labels.append(2)

    df = pd.DataFrame(data)
    df["label"] = labels
    df["label_name"] = df["label"].map({0: "Healthy", 1: "Stressed", 2: "Diseased"})
    df.to_csv(DATA_DIR / "crop_stress.csv", index=False)
    print(f"✅ Crop stress dataset: {len(df)} samples → {DATA_DIR}/crop_stress.csv")
    return df


# ── 2. Irrigation Dataset ─────────────────────────────────────────────────────
def generate_irrigation_data():
    """
    Features: ndwi, ndvi, lai, soil_moisture_pct, temp_celsius, rainfall_mm
    Labels  : 0=irrigate_now, 1=irrigate_soon, 2=adequate, 3=overwatered
    """
    data = []
    labels = []

    conditions = [
        # irrigate_now: very dry
        dict(ndwi=(-0.6, -0.3), soil=(5, 20),  temp=(30, 45), rain=(0, 5),   label=0),
        # irrigate_soon: getting dry
        dict(ndwi=(-0.3, -0.0), soil=(20, 40), temp=(25, 35), rain=(5, 20),  label=1),
        # adequate: good moisture
        dict(ndwi=(0.0,  0.3),  soil=(40, 70), temp=(20, 30), rain=(20, 60), label=2),
        # overwatered: too wet
        dict(ndwi=(0.3,  0.6),  soil=(70, 95), temp=(15, 28), rain=(60, 120),label=3),
    ]

    for cond in conditions:
        for _ in range(N // 4):
            ndwi = np.random.uniform(*cond["ndwi"])
            soil = np.random.uniform(*cond["soil"])
            data.append({
                "ndwi":              ndwi,
                "ndvi":              np.random.uniform(0.1, 0.8),
                "lai":               np.random.uniform(0.5, 5.0),
                "soil_moisture_pct": soil,
                "temp_celsius":      np.random.uniform(*cond["temp"]),
                "rainfall_mm":       np.random.uniform(*cond["rain"]),
            })
            labels.append(cond["label"])

    df = pd.DataFrame(data)
    df["label"] = labels
    label_map = {0: "irrigate_now", 1: "irrigate_soon", 2: "adequate", 3: "overwatered"}
    df["label_name"] = df["label"].map(label_map)
    df.to_csv(DATA_DIR / "irrigation.csv", index=False)
    print(f"✅ Irrigation dataset: {len(df)} samples → {DATA_DIR}/irrigation.csv")
    return df


# ── 3. VRA Zones Dataset ──────────────────────────────────────────────────────
def generate_vra_data():
    """
    Features: ndvi, ndre, ndwi, evi, lai, ndvi_std
    Labels  : 0=low_fertility, 1=medium_fertility, 2=high_fertility
    Used for K-Means clustering (unsupervised) but also RF for prediction.
    """
    data = []
    labels = []

    zones = [
        dict(ndvi=(0.0,0.3),  ndre=(0.0,0.15), label=0),  # low
        dict(ndvi=(0.3,0.55), ndre=(0.15,0.35),label=1),  # medium
        dict(ndvi=(0.55,0.9), ndre=(0.35,0.6), label=2),  # high
    ]
    for zone in zones:
        for _ in range(N // 3):
            ndvi = np.random.uniform(*zone["ndvi"])
            ndre = np.random.uniform(*zone["ndre"])
            data.append({
                "ndvi":     ndvi,
                "ndre":     ndre,
                "ndwi":     np.random.uniform(-0.4, 0.4),
                "evi":      ndvi * np.random.uniform(0.5, 0.85),
                "lai":      ndvi * np.random.uniform(3, 7),
                "ndvi_std": np.random.uniform(0.02, 0.2),
            })
            labels.append(zone["label"])

    df = pd.DataFrame(data)
    df["label"] = labels
    df["zone_name"] = df["label"].map({0: "Low", 1: "Medium", 2: "High"})
    df.to_csv(DATA_DIR / "vra_zones.csv", index=False)
    print(f"✅ VRA zones dataset: {len(df)} samples → {DATA_DIR}/vra_zones.csv")
    return df


# ── 4. Yield Prediction Dataset ───────────────────────────────────────────────
def generate_yield_data():
    """
    Features: ndvi_mean, ndvi_max, evi_mean, ndre_mean, lai_mean,
              growing_days, rainfall_total_mm, temp_mean_celsius, area_ha
    Target  : yield_tha (tons per hectare)
    Based on wheat/rice yields for Pakistan (2-6 t/ha typical range)
    """
    data = []
    for _ in range(N):
        ndvi_mean  = np.random.uniform(0.2, 0.8)
        ndvi_max   = ndvi_mean + np.random.uniform(0.05, 0.2)
        evi_mean   = ndvi_mean * np.random.uniform(0.55, 0.75)
        ndre_mean  = np.random.uniform(0.1, 0.5)
        lai_mean   = ndvi_mean * np.random.uniform(4, 8)
        grow_days  = np.random.randint(90, 150)
        rain_mm    = np.random.uniform(50, 400)
        temp_mean  = np.random.uniform(18, 35)

        # Yield formula based on agronomic relationships
        base_yield = (
            ndvi_mean * 4.5 +
            ndre_mean * 2.0 +
            (rain_mm / 200) * 0.8 +
            np.random.normal(0, 0.3)
        )
        yield_tha = np.clip(base_yield, 0.5, 8.0)

        data.append({
            "ndvi_mean":          round(ndvi_mean, 4),
            "ndvi_max":           round(min(ndvi_max, 1.0), 4),
            "evi_mean":           round(evi_mean, 4),
            "ndre_mean":          round(ndre_mean, 4),
            "lai_mean":           round(lai_mean, 4),
            "growing_days":       grow_days,
            "rainfall_total_mm":  round(rain_mm, 1),
            "temp_mean_celsius":  round(temp_mean, 1),
            "yield_tha":          round(yield_tha, 3),
        })

    df = pd.DataFrame(data)
    df.to_csv(DATA_DIR / "yield.csv", index=False)
    print(f"✅ Yield dataset: {len(df)} samples → {DATA_DIR}/yield.csv")
    return df


# ── 5. Soil Assessment Dataset ────────────────────────────────────────────────
def generate_soil_data():
    """
    Features: ndvi, ndwi, bsi (bare soil index), b2, b3, b4, b8, b11
    Targets : soil_ph, salinity_ds_m, organic_matter_pct
    """
    data = []
    for _ in range(N):
        # Bare Soil Index = ((B11+B4)-(B8+B2)) / ((B11+B4)+(B8+B2))
        b2  = np.random.uniform(0.02, 0.15)
        b3  = np.random.uniform(0.03, 0.18)
        b4  = np.random.uniform(0.02, 0.20)
        b8  = np.random.uniform(0.10, 0.50)
        b11 = np.random.uniform(0.05, 0.35)
        bsi = ((b11 + b4) - (b8 + b2)) / ((b11 + b4) + (b8 + b2) + 1e-6)

        ndvi = (b8 - b4) / (b8 + b4 + 1e-6)
        ndwi = (b3 - b8) / (b3 + b8 + 1e-6)

        # Soil properties derived from spectral relationships
        soil_ph  = np.clip(6.5 + bsi * 2.0 + np.random.normal(0, 0.3), 5.0, 9.5)
        salinity = np.clip(0.5 + abs(bsi) * 3.0 + np.random.exponential(0.5), 0.1, 8.0)
        org_matter = np.clip(2.5 - bsi * 3.0 + ndvi * 1.5 + np.random.normal(0, 0.2), 0.1, 6.0)

        data.append({
            "ndvi":               round(ndvi, 4),
            "ndwi":               round(ndwi, 4),
            "bsi":                round(bsi, 4),
            "b2":                 round(b2, 4),
            "b3":                 round(b3, 4),
            "b4":                 round(b4, 4),
            "b8":                 round(b8, 4),
            "b11":                round(b11, 4),
            "soil_ph":            round(soil_ph, 2),
            "salinity_ds_m":      round(salinity, 3),
            "organic_matter_pct": round(org_matter, 3),
        })

    df = pd.DataFrame(data)
    df.to_csv(DATA_DIR / "soil.csv", index=False)
    print(f"✅ Soil dataset: {len(df)} samples → {DATA_DIR}/soil.csv")
    return df


if __name__ == "__main__":
    print("Generating training datasets...\n")
    generate_crop_stress_data()
    generate_irrigation_data()
    generate_vra_data()
    generate_yield_data()
    generate_soil_data()
    print("\n✅ All datasets generated successfully!")
