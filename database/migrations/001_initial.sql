-- ============================================================
-- AgroSense — Initial Database Schema
-- Migration: 001_initial.sql
-- Run via: make migrate
-- ============================================================

-- Enable PostGIS and UUID extensions
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS pg_trgm;   -- for text search

-- ── USERS ─────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
    user_id     UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name        VARCHAR(100) NOT NULL,
    email       VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role        VARCHAR(20) NOT NULL DEFAULT 'farmer'
                    CHECK (role IN ('admin', 'agronomist', 'farmer')),
    is_active   BOOLEAN NOT NULL DEFAULT true,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_users_email ON users(email);

-- ── FARMS ─────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS farms (
    farm_id         UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    name            VARCHAR(200) NOT NULL,
    location_geom   GEOMETRY(Polygon, 4326),   -- WGS84 lat/lng
    area_ha         FLOAT,
    province        VARCHAR(100),
    district        VARCHAR(100),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_farms_user_id ON farms(user_id);
CREATE INDEX idx_farms_geom ON farms USING GIST(location_geom);

-- ── FIELDS (individual crop plots within a farm) ──────────────
CREATE TABLE IF NOT EXISTS fields (
    field_id        UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    farm_id         UUID NOT NULL REFERENCES farms(farm_id) ON DELETE CASCADE,
    name            VARCHAR(200),
    crop_type       VARCHAR(100),
    planting_date   DATE,
    expected_harvest DATE,
    boundary_geom   GEOMETRY(Polygon, 4326),
    area_ha         FLOAT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_fields_farm_id ON fields(farm_id);
CREATE INDEX idx_fields_geom ON fields USING GIST(boundary_geom);

-- ── SATELLITE_IMAGES ──────────────────────────────────────────
CREATE TABLE IF NOT EXISTS satellite_images (
    image_id        UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    field_id        UUID NOT NULL REFERENCES fields(field_id) ON DELETE CASCADE,
    source          VARCHAR(20) NOT NULL CHECK (source IN ('sentinel2', 'landsat8')),
    acquisition_date DATE NOT NULL,
    cloud_cover_pct FLOAT,
    gee_asset_id    VARCHAR(500),          -- GEE image ID
    gcs_path        VARCHAR(500),          -- GCS bucket path for GeoTIFF
    bands           JSONB,                 -- {B2: float, B3: float, ...}
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_sat_images_field_id ON satellite_images(field_id);
CREATE INDEX idx_sat_images_date ON satellite_images(acquisition_date DESC);

-- ── VEGETATION_INDICES ────────────────────────────────────────
CREATE TABLE IF NOT EXISTS vegetation_indices (
    index_id        UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    image_id        UUID NOT NULL REFERENCES satellite_images(image_id) ON DELETE CASCADE,
    ndvi            FLOAT,    -- Normalised Difference Vegetation Index
    evi             FLOAT,    -- Enhanced Vegetation Index
    ndwi            FLOAT,    -- Normalised Difference Water Index
    ndre            FLOAT,    -- Normalised Difference Red Edge
    lai             FLOAT,    -- Leaf Area Index
    savi            FLOAT,    -- Soil Adjusted Vegetation Index
    ndvi_raster_path VARCHAR(500),   -- GCS path to full-resolution NDVI raster
    calculated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_veg_indices_image_id ON vegetation_indices(image_id);

-- ── ML_PREDICTIONS ────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS ml_predictions (
    prediction_id   UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    field_id        UUID NOT NULL REFERENCES fields(field_id) ON DELETE CASCADE,
    model_type      VARCHAR(50) NOT NULL
                        CHECK (model_type IN (
                            'crop_stress', 'irrigation',
                            'vra_zones', 'yield', 'soil'
                        )),
    model_version   VARCHAR(20),
    result_data     JSONB NOT NULL,        -- model-specific output
    confidence      FLOAT,                 -- 0.0 – 1.0
    raster_path     VARCHAR(500),          -- GCS path to prediction raster
    predicted_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_predictions_field_id ON ml_predictions(field_id);
CREATE INDEX idx_predictions_type ON ml_predictions(model_type);
CREATE INDEX idx_predictions_date ON ml_predictions(predicted_at DESC);

-- ── IRRIGATION_RECS ───────────────────────────────────────────
CREATE TABLE IF NOT EXISTS irrigation_recs (
    rec_id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    field_id            UUID NOT NULL REFERENCES fields(field_id) ON DELETE CASCADE,
    soil_moisture_pct   FLOAT,
    recommendation      VARCHAR(20) NOT NULL
                            CHECK (recommendation IN ('irrigate', 'hold', 'drain')),
    water_deficit_mm    FLOAT,
    recommended_amount_mm FLOAT,
    priority            VARCHAR(10) CHECK (priority IN ('high', 'medium', 'low')),
    valid_until         TIMESTAMPTZ,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_irrigation_field_id ON irrigation_recs(field_id);

-- ── YIELD_PREDICTIONS ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS yield_predictions (
    yield_id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    field_id            UUID NOT NULL REFERENCES fields(field_id) ON DELETE CASCADE,
    predicted_yield_tha FLOAT,           -- tons per hectare
    yield_lower_tha     FLOAT,           -- confidence interval lower bound
    yield_upper_tha     FLOAT,           -- confidence interval upper bound
    estimated_harvest   DATE,
    harvest_readiness   VARCHAR(20)
                            CHECK (harvest_readiness IN (
                                'early', 'on_track', 'delayed'
                            )),
    model_version       VARCHAR(20),
    predicted_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_yield_field_id ON yield_predictions(field_id);

-- ── Trigger: auto-update updated_at ───────────────────────────
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER users_updated_at  BEFORE UPDATE ON users  FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER farms_updated_at  BEFORE UPDATE ON farms  FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER fields_updated_at BEFORE UPDATE ON fields FOR EACH ROW EXECUTE FUNCTION update_updated_at();
