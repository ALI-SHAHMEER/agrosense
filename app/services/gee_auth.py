"""
GEE Authentication & Initialization
Call init_gee() once at app startup.
"""
import ee
from google.oauth2 import service_account

from app.core.config import settings

_initialized = False


def init_gee():
    global _initialized
    if _initialized:
        return
    credentials = service_account.Credentials.from_service_account_file(
        settings.GEE_KEY_FILE,
        scopes=["https://www.googleapis.com/auth/earthengine"],
    )
    ee.Initialize(credentials, project="agrosense-495406")
    _initialized = True
    print("✅ GEE initialized successfully")
