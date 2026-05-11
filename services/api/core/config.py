"""
AgroSense API — Configuration
All settings are loaded from environment variables / .env file.
"""

from functools import lru_cache
from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ───────────────────────────────────────────
    APP_ENV: str = "development"
    APP_SECRET_KEY: str = "dev-secret-change-in-production"
    APP_DEBUG: bool = True
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    CORS_ORIGINS: List[str] = ["http://localhost:3000"]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors(cls, v):
        if isinstance(v, str):
            return [i.strip() for i in v.split(",")]
        return v

    # ── Database ──────────────────────────────────────────────
    DATABASE_URL: str = (
        "postgresql+asyncpg://agrosense_user:localpassword@localhost:5432/agrosense"
    )

    # ── Redis ─────────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"

    # ── JWT ───────────────────────────────────────────────────
    JWT_SECRET_KEY: str = "jwt-secret-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # ── Google Earth Engine ───────────────────────────────────
    GEE_SERVICE_ACCOUNT: str = ""
    GEE_KEY_FILE: str = "./keys/gee-service-account.json"
    GEE_PROJECT: str = ""

    # ── GCP ───────────────────────────────────────────────────
    GCP_PROJECT_ID: str = ""
    GCP_REGION: str = "us-central1"
    GCS_BUCKET_NAME: str = "agrosense-satellite-data"

    # ── ML Models ─────────────────────────────────────────────
    ML_MODELS_DIR: str = "./saved_models"
    CROP_STRESS_MODEL_PATH: str = "./saved_models/crop_stress_effnetv2_rf.pkl"
    IRRIGATION_MODEL_PATH: str = "./saved_models/irrigation_xgboost.pkl"
    YIELD_MODEL_PATH: str = "./saved_models/yield_lstm.h5"
    SOIL_MODEL_PATH: str = "./saved_models/soil_gradboost.pkl"
    VRA_MODEL_PATH: str = "./saved_models/vra_kmeans.pkl"

    # ── Sentinel-2 / Landsat-8 ────────────────────────────────
    SENTINEL2_COLLECTION: str = "COPERNICUS/S2_SR_HARMONIZED"
    LANDSAT8_COLLECTION: str = "LANDSAT/LC08/C02/T1_L2"
    MAX_CLOUD_COVER_PCT: int = 20
    DEFAULT_SCALE_METERS: int = 10

    # ── Logging ───────────────────────────────────────────────
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"

    @property
    def is_development(self) -> bool:
        return self.APP_ENV == "development"


@lru_cache
def get_settings() -> Settings:
    return Settings()


# Module-level singleton
settings = get_settings()
