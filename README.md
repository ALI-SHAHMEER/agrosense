# AgroSense — Satellite-Based AI Crop Monitoring System

AgroSense is a full-stack agricultural intelligence platform built for Pakistani farmers. It pulls satellite imagery from Google Earth Engine, computes vegetation indices (NDVI, NDRE, EVI, NDWI, LAI), and runs ML models to detect crop stress, recommend irrigation, forecast yield, and assess soil health — all surfaced through a desktop app and REST API.

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
        ▼
FastAPI Backend  ←→  PostgreSQL + PostGIS
        │
   ┌────┴────┐
   │         │
PyQt6      React
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
| Desktop App | PyQt6 |
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
│   │   └── predictions.py      # Prediction history
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
│   ├── windows/                # Login, register, main window
│   ├── pages/                  # Dashboard, farms, imagery, analytics
│   └── utils/
│       ├── email_alerts.py     # Gmail SMTP alert sender
│       └── pdf_export.py       # PDF report generation
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
├── tests/                      # pytest integration tests
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

## Running Tests

Make sure the API is running (`uvicorn app.main:app --port 8000`), then:

```bash
pytest tests/ -v
```

All 23 tests cover: auth flow, farm/field CRUD, satellite analysis, and all ML endpoints.

---

## CI / CD

GitHub Actions runs the full test suite on every push and pull request to `main`:

1. Spins up a PostGIS 16 database container
2. Installs all Python dependencies
3. Runs `alembic upgrade head`
4. Starts the API with uvicorn
5. Runs all 23 pytest tests

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
