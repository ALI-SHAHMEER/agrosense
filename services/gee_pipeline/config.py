"""
AgroSense GEE Pipeline — Configuration & Authentication
"""

import os
import ee
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


# ── Configuration ─────────────────────────────────────────────
class GEEConfig:
    # GEE Collections
    SENTINEL2_COLLECTION = os.getenv(
        "SENTINEL2_COLLECTION", "COPERNICUS/S2_SR_HARMONIZED"
    )
    LANDSAT8_COLLECTION = os.getenv(
        "LANDSAT8_COLLECTION", "LANDSAT/LC08/C02/T1_L2"
    )

    # Filtering
    MAX_CLOUD_COVER = int(os.getenv("MAX_CLOUD_COVER_PCT", 20))
    DEFAULT_SCALE = int(os.getenv("DEFAULT_SCALE_METERS", 10))

    # GCP
    GCS_BUCKET = os.getenv("GCS_BUCKET_NAME", "agrosense-satellite-data")
    GCP_PROJECT = os.getenv("GCP_PROJECT_ID", "")

    # Auth
    SERVICE_ACCOUNT = os.getenv("GEE_SERVICE_ACCOUNT", "")
    KEY_FILE = Path(os.getenv("GEE_KEY_FILE", "./keys/gee-service-account.json"))


config = GEEConfig()


# ── Authentication ────────────────────────────────────────────
def initialize_gee(use_service_account: bool = True) -> None:
    """
    Initialise Google Earth Engine.

    Args:
        use_service_account: If True, uses service account (for server/CI).
                             If False, uses interactive auth (for notebooks).
    """
    if use_service_account and config.KEY_FILE.exists():
        credentials = ee.ServiceAccountCredentials(
            email=config.SERVICE_ACCOUNT,
            key_file=str(config.KEY_FILE),
        )
        ee.Initialize(credentials, project=config.GCP_PROJECT)
        print(f"✓ GEE initialised with service account: {config.SERVICE_ACCOUNT}")
    else:
        # Interactive auth (for local development / Colab)
        ee.Authenticate()
        ee.Initialize(project=config.GCP_PROJECT)
        print("✓ GEE initialised with interactive auth")


def get_gee_client():
    """Returns an initialised GEE client, initialising if needed."""
    try:
        ee.data.getInfo("projects/earthengine-public")
    except Exception:
        initialize_gee()
    return ee
