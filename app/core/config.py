from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Database
    DATABASE_URL: str = "postgresql://agrosense_user:yourpassword@localhost:5432/agrosense_db"

    # Security
    SECRET_KEY: str = "change-me"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # App
    APP_ENV: str = "development"
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    DEBUG: bool = True

    # GEE
    GEE_SERVICE_ACCOUNT: str = ""
    GEE_KEY_FILE: str = "secrets/gee-key.json"
    # Email Alerts
    GMAIL_USER: str = ""
    GMAIL_APP_PASSWORD: str = ""
    ADMIN_EMAIL: str = ""

settings = Settings()
