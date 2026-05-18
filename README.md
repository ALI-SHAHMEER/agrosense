# AgroSense — Satellite-Based AI Crop Monitoring System

AgroSense is a full-stack agricultural intelligence platform built for Pakistani farmers. It pulls satellite imagery from Google Earth Engine, computes vegetation indices (NDVI, NDRE, EVI, NDWI, LAI), and runs ML models to detect crop stress, recommend irrigation, forecast yield, and assess soil health — all surfaced through a desktop app and REST API. A built-in Smart Farming screen delivers 7-day weather forecasts, automated crop-protection alerts, and AI planting recommendations without needing to run a satellite analysis first.

---

## How It Works

```
Satellite (Sentinel-2 / Landsat-8)
        │
        ▼
Google Earth Engine Pipeline
  - Pulls imagery for a field's GPS boundary
  - Computes spectral indices (NDVI, NDRE, EVI, NDWI, LAI)
        │
        ▼
ML Models (scikit-learn / XGBoost)
  ┌─────────────────┬──────────────────┬──────────────────┬──────────────┐
  │  Crop Stress    │   Irrigation     │ Yield Prediction │    Soil      │
  │ Healthy /       │ Recommend water  │ t/ha forecast    │ Assessment   │
  │ Stressed /      │ amount & timing  │ + harvest date   │ + VRA zones  │
  │ Diseased        │                  │                  │              │
  └─────────────────┴──────────────────┴──────────────────┴──────────────┘
        │
        ▼                              Open-Meteo (free weather API)
FastAPI Backend  ←→  PostgreSQL + PostGIS      │
        │              ◄────────────────────────┘
   ┌────┴────┐           Smart Farming: 7-day forecast
   │         │           + rule-based alerts
PyQt6      React         + planting recommendations
Desktop    Dashboard
  App      (web)
```

Email alerts are sent via Gmail SMTP whenever a crop is detected as Stressed or Diseased.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend API | FastAPI, Uvicorn, SQLAlchemy, Alembic |
| Database | PostgreSQL 16 + PostGIS |
| Satellite Pipeline | Google Earth Engine API (Sentinel-2, Landsat-8) |
| ML Models | scikit-learn, XGBoost |
| Weather Data | Open-Meteo (free, no API key required) |
| Desktop App | PyQt6 (bilingual EN/UR, PDF export) |
| Web Dashboard | React, Vite, Tailwind CSS |
| Auth | JWT (python-jose), bcrypt (passlib) |
| CI | GitHub Actions |

---

## Prerequisites

- Python 3.11
- [Miniconda](https://docs.conda.io/en/latest/miniconda.html) or Anaconda
- PostgreSQL 16 with PostGIS extension
- A [Google Earth Engine](https://earthengine.google.com/) service account and key file

---

## Local Setup

### 1. Clone the repo

```bash
git clone https://github.com/ALI-SHAHMEER/agrosense.git
cd agrosense
```

### 2. Create the conda environment

```bash
conda env create -f environment.yml
conda activate agrosense
```

### 3. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env` and fill in your values:

```env
# Database
DATABASE_URL=postgresql://agrosense_user:yourpassword@localhost:5432/agrosense_db

# Security — generate with: python -c "import secrets; print(secrets.token_hex(32))"
SECRET_KEY=your-secret-key-here

# Google Earth Engine
GEE_SERVICE_ACCOUNT=your-service-account@project.iam.gserviceaccount.com
GEE_KEY_FILE=secrets/gee-key.json

# Gmail (for crop stress email alerts)
GMAIL_USER=your-gmail@gmail.com
GMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx
ADMIN_EMAIL=your-admin@gmail.com
```

### 4. Set up the GEE service account key

Place your Google Earth Engine service account JSON key at:

```
secrets/gee-key.json
```

To create a service account:
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a service account and download the JSON key
3. Register the service account email at [earthengine.google.com](https://earthengine.google.com/signup/)

### 5. Set up the database

```bash
# Create the database and user in PostgreSQL
psql -U postgres -c "CREATE USER agrosense_user WITH PASSWORD 'yourpassword';"
psql -U postgres -c "CREATE DATABASE agrosense_db OWNER agrosense_user;"
psql -U postgres -c "CREATE EXTENSION IF NOT EXISTS postgis;" -d agrosense_db

# Run migrations
alembic upgrade head
```

### 6. Start the API

```bash
uvicorn app.main:app --reload --port 8000
```

API docs available at **http://localhost:8000/docs**

### 7. Launch the desktop app

Open a second terminal:

```bash
conda activate agrosense
python desktop/main.py
```

---

## Project Structure

```
agrosense/
├── app/                        # FastAPI backend
│   ├── core/
│   │   ├── config.py           # Settings from .env
│   │   └── security.py         # JWT + bcrypt helpers
│   ├── models/                 # SQLAlchemy ORM models
│   ├── routers/                # API route handlers
│   │   ├── auth.py             # Register / login / me
│   │   ├── farms.py            # Farm CRUD
│   │   ├── fields.py           # Field CRUD
│   │   ├── imagery.py          # Satellite analysis endpoint
│   │   ├── ml.py               # ML prediction endpoints
│   │   ├── predictions.py      # Prediction history
│   │   └── weather.py          # Smart Farming: forecast, alerts, planting rec
│   ├── schemas/                # Pydantic request/response models
│   ├── services/
│   │   ├── gee_auth.py         # Google Earth Engine init
│   │   ├── sentinel2.py        # Sentinel-2 imagery service
│   │   ├── indices.py          # Vegetation index computation
│   │   └── pipeline.py         # Full analysis pipeline
│   ├── ml/
│   │   ├── predictor.py        # Unified ML predictor
│   │   └── training/           # Model training scripts
│   ├── database.py             # SQLAlchemy engine + session
│   └── main.py                 # FastAPI app entry point
│
├── desktop/                    # PyQt6 desktop application
│   ├── main.py                 # App entry point
│   ├── api.py                  # HTTP client to backend API
│   ├── i18n.py                 # EN/UR LanguageManager (live toggle)
│   ├── windows/                # Login, register, main window
│   ├── pages/
│   │   ├── dashboard.py        # Dashboard with top-stats and charts
│   │   ├── farms.py            # Farm management
│   │   ├── imagery.py          # Satellite analysis
│   │   ├── analytics.py        # ML predictions & history
│   │   ├── map_view.py         # Field map viewer
│   │   ├── band_view.py        # Spectral band viewer
│   │   └── smart_farming.py    # Smart Farming: weather, alerts, planting rec
│   └── utils/
│       ├── email_alerts.py     # Gmail SMTP alert sender
│       └── pdf_export.py       # Bilingual PDF report generation (EN + UR)
│
├── services/
│   ├── api/                    # Standalone API service (Docker target)
│   ├── dashboard/              # React web dashboard (Vite + Tailwind)
│   ├── gee_pipeline/           # Google Earth Engine pipeline module
│   └── ml_models/              # Individual ML model packages
│       ├── crop_stress/
│       ├── irrigation/
│       ├── soil_assessment/
│       ├── vra_zones/
│       └── yield_prediction/
│
├── alembic/                    # Database migrations
├── tests/                      # pytest test suite
│   ├── test_api.py             # Integration tests (requires running server)
│   └── test_weather.py         # Unit tests for Smart Farming pure functions
├── .env.example                # Environment variable template
├── environment.yml             # Conda environment definition
└── Makefile                    # Dev shortcuts
```

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| POST | `/auth/register` | Register a new user |
| POST | `/auth/login` | Login and get JWT token |
| GET | `/auth/me` | Get current user profile |
| GET/POST | `/farms` | List / create farms |
| GET/PUT/DELETE | `/farms/{id}` | Get / update / delete a farm |
| GET/POST | `/fields` | List / create fields |
| POST | `/imagery/analyze` | Run satellite analysis on a field |
| GET | `/imagery/history/{field_id}` | Get analysis history |
| POST | `/ml/full-analysis` | Full ML pipeline (stress + irrigation + yield + soil) |
| POST | `/ml/crop-stress` | Crop stress prediction only |
| POST | `/ml/irrigation` | Irrigation recommendation only |
| POST | `/ml/yield` | Yield prediction only |
| GET | `/weather/smart-farming/{field_id}` | 7-day forecast + alerts + planting rec |
| GET | `/health` | API health check |

Full interactive docs: **http://localhost:8000/docs**

---

## ML Models

| Model | Input Features | Output |
|---|---|---|
| **Crop Stress** | NDVI, NDRE, EVI, NDWI, LAI, crop type | Healthy / Stressed / Diseased + confidence |
| **Irrigation** | Soil moisture, NDWI, crop type, season | Water amount (mm) + recommendation |
| **Yield Prediction** | NDVI, LAI, crop type, field area | Yield (t/ha) + harvest date estimate |
| **Soil Assessment** | Spectral indices, location | Soil health score + fertility rating |
| **VRA Zones** | NDVI variability across field | Variable rate application zones map |

---

## Desktop App Features

### Smart Farming

The Smart Farming page (`desktop/pages/smart_farming.py`) provides a single screen for actionable field intelligence without requiring a satellite analysis first:

- **7-day weather forecast** — condition icons, min/max temperature, rainfall, humidity, wind speed; data sourced from Open-Meteo (no API key required)
- **Crop-protection alerts** — rule engine detects 7 alert types with severity levels:
  | Alert | Trigger | Severity |
  |---|---|---|
  | Heatwave | >38 °C on 2+ consecutive days | High |
  | Heavy rain | >25 mm in one day | High |
  | Frost | <4 °C | High |
  | Drought | <5 mm total + avg temp >30 °C | Medium |
  | Strong wind | >40 km/h | Medium |
  | Spray delay | Rain probability >60% (day 0 or 1) | Low |
  | Fungal risk | Humidity >85% for 3+ consecutive days | Low |
- **AI planting recommendation** — suitability score `= temp×0.4 + moisture×0.4 + risk×0.2`, ideal planting date (first day >0.7), and reasons list
- **ML summary** — crop health, irrigation need, and yield forecast pulled from the latest satellite analysis (shown only when satellite imagery data exists for the field)
- **Weekly summary** — aggregate stats for the 7-day window (avg temp, total rain, avg humidity, avg wind)

### Bilingual Interface (EN / UR)

A live language toggle switches the entire desktop UI between English and Urdu without restarting. All 31 Smart Farming keys and all other UI strings are defined in `desktop/i18n.py` via the `LanguageManager` singleton. Urdu text is right-to-left aligned automatically.

### PDF Export

`desktop/utils/pdf_export.py` generates bilingual PDF reports using ReportLab. Urdu text is pre-processed with `arabic_reshaper` + `python-bidi` and rendered with the NotoNaskhArabic font (which has static Presentation Form glyphs, making it compatible with ReportLab without OpenType shaping).

---

## Running Tests

Unit tests (no server required):

```bash
conda run -n agrosense pytest tests/test_weather.py -v
```

Integration tests (requires running API):

```bash
uvicorn app.main:app --port 8000 &
conda run -n agrosense pytest tests/test_api.py -v
```

Run everything:

```bash
conda run -n agrosense pytest tests/ -v
```

The test suite has **34+ tests** covering: auth flow, farm/field CRUD, satellite analysis, all ML endpoints, and Smart Farming pure functions (WMO weathercode mapping, all 7 alert types, planting recommendation scoring).

---

## CI / CD

GitHub Actions runs the full test suite on every push and pull request to `main`:

1. Spins up a PostGIS 16 database container
2. Installs all Python dependencies
3. Runs `alembic upgrade head`
4. Starts the API with uvicorn
5. Runs all pytest tests

See `.github/workflows/ci.yml` for the full workflow.

---

## Environment Variables Reference

| Variable | Description |
|---|---|
| `DATABASE_URL` | PostgreSQL connection string |
| `SECRET_KEY` | JWT signing secret (min 32 chars) |
| `ALGORITHM` | JWT algorithm (default: `HS256`) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Token expiry (default: `60`) |
| `GEE_SERVICE_ACCOUNT` | GEE service account email |
| `GEE_KEY_FILE` | Path to GEE JSON key file |
| `GMAIL_USER` | Gmail address for sending alerts |
| `GMAIL_APP_PASSWORD` | Gmail app password (not account password) |
| `ADMIN_EMAIL` | Admin email to CC on all alerts |
| `APP_ENV` | `development` / `testing` / `production` |
| `DEBUG` | Enable debug mode (`true` / `false`) |
