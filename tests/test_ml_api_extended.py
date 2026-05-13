"""
Extended ML API tests — schema validation, untested endpoints (VRA, soil),
weather params, yield crop types, prediction persistence.
Requires: server running + imagery already analyzed for FIELD_WITH_DATA_ID.
"""
import pytest
import requests

BASE = "http://localhost:8000"
EMAIL    = "areo5459@gmail.com"
PASSWORD = "12345678"

# Field IDs that already have imagery data (from existing test farms)
_token  = None
_field_ids_with_data = []


def get_token():
    global _token
    if _token:
        return _token
    r = requests.post(f"{BASE}/auth/login",
                      data={"username": EMAIL, "password": PASSWORD}, timeout=10)
    assert r.status_code == 200, f"Login failed: {r.text}"
    _token = r.json()["access_token"]
    return _token


def headers():
    return {"Authorization": f"Bearer {get_token()}"}


def field_with_data():
    """Return a field_id guaranteed to have vegetation index data."""
    global _field_ids_with_data
    if _field_ids_with_data:
        return _field_ids_with_data[0]

    farms = requests.get(f"{BASE}/farms/", headers=headers(), timeout=10).json()
    for farm in farms:
        fields = requests.get(f"{BASE}/fields/farm/{farm['id']}", headers=headers(), timeout=10).json()
        for f in fields:
            # Check if this field has imagery data by calling crop-stress
            r = requests.post(f"{BASE}/ml/field/{f['id']}/crop-stress",
                               headers=headers(), timeout=30)
            if r.status_code == 200:
                _field_ids_with_data.append(f["id"])

    assert _field_ids_with_data, "No fields with imagery data found — run imagery/analyze first"
    return _field_ids_with_data[0]


# ---------------------------------------------------------------------------
# VRA Zones endpoint (previously untested)
# ---------------------------------------------------------------------------

class TestVRAZonesAPI:
    def test_vra_zones_status_200(self):
        fid = field_with_data()
        r = requests.post(f"{BASE}/ml/field/{fid}/vra-zones", headers=headers(), timeout=30)
        assert r.status_code == 200, r.text

    def test_vra_zones_response_schema(self):
        fid = field_with_data()
        r = requests.post(f"{BASE}/ml/field/{fid}/vra-zones", headers=headers(), timeout=30)
        d = r.json()
        assert "field_id" in d
        assert "field_name" in d
        assert "zone" in d
        assert "confidence" in d
        assert "fertiliser_recommendation" in d
        assert "probabilities" in d

    def test_vra_zone_value_is_valid(self):
        fid = field_with_data()
        r = requests.post(f"{BASE}/ml/field/{fid}/vra-zones", headers=headers(), timeout=30)
        assert r.json()["zone"] in ("Low", "Medium", "High")

    def test_vra_confidence_in_range(self):
        fid = field_with_data()
        r = requests.post(f"{BASE}/ml/field/{fid}/vra-zones", headers=headers(), timeout=30)
        c = r.json()["confidence"]
        assert 0.0 <= c <= 1.0

    def test_vra_probabilities_sum_to_one(self):
        fid = field_with_data()
        r = requests.post(f"{BASE}/ml/field/{fid}/vra-zones", headers=headers(), timeout=30)
        total = sum(r.json()["probabilities"].values())
        assert abs(total - 1.0) < 1e-3

    def test_vra_fertiliser_is_non_empty_string(self):
        fid = field_with_data()
        r = requests.post(f"{BASE}/ml/field/{fid}/vra-zones", headers=headers(), timeout=30)
        assert len(r.json()["fertiliser_recommendation"]) > 5

    def test_vra_unknown_field_returns_404(self):
        r = requests.post(f"{BASE}/ml/field/00000000-0000-0000-0000-000000000000/vra-zones",
                          headers=headers(), timeout=10)
        assert r.status_code == 404

    def test_vra_no_auth_returns_401(self):
        fid = field_with_data()
        r = requests.post(f"{BASE}/ml/field/{fid}/vra-zones", timeout=10)
        assert r.status_code == 401


# ---------------------------------------------------------------------------
# Soil endpoint (previously untested)
# ---------------------------------------------------------------------------

class TestSoilAPI:
    def test_soil_status_200(self):
        fid = field_with_data()
        r = requests.post(f"{BASE}/ml/field/{fid}/soil", headers=headers(), timeout=30)
        assert r.status_code == 200, r.text

    def test_soil_response_schema(self):
        fid = field_with_data()
        r = requests.post(f"{BASE}/ml/field/{fid}/soil", headers=headers(), timeout=30)
        d = r.json()
        for key in ("field_id", "field_name", "soil_ph", "salinity_ds_m",
                    "organic_matter_pct", "ph_status", "salinity_status",
                    "organic_matter_status"):
            assert key in d, f"Missing key: {key}"

    def test_soil_ph_realistic_range(self):
        fid = field_with_data()
        r = requests.post(f"{BASE}/ml/field/{fid}/soil", headers=headers(), timeout=30)
        ph = r.json()["soil_ph"]
        assert 3.0 <= ph <= 10.0, f"pH out of range: {ph}"

    def test_soil_salinity_non_negative(self):
        fid = field_with_data()
        r = requests.post(f"{BASE}/ml/field/{fid}/soil", headers=headers(), timeout=30)
        assert r.json()["salinity_ds_m"] >= 0

    def test_soil_organic_matter_non_negative(self):
        fid = field_with_data()
        r = requests.post(f"{BASE}/ml/field/{fid}/soil", headers=headers(), timeout=30)
        assert r.json()["organic_matter_pct"] >= 0

    def test_soil_ph_status_valid(self):
        fid = field_with_data()
        r = requests.post(f"{BASE}/ml/field/{fid}/soil", headers=headers(), timeout=30)
        assert r.json()["ph_status"] in ("Optimal", "Acidic", "Alkaline")

    def test_soil_no_auth_returns_401(self):
        fid = field_with_data()
        r = requests.post(f"{BASE}/ml/field/{fid}/soil", timeout=10)
        assert r.status_code == 401


# ---------------------------------------------------------------------------
# Crop Stress schema validation
# ---------------------------------------------------------------------------

class TestCropStressAPI:
    def test_response_schema(self):
        fid = field_with_data()
        r = requests.post(f"{BASE}/ml/field/{fid}/crop-stress", headers=headers(), timeout=30)
        assert r.status_code == 200
        d = r.json()
        assert "field_id" in d
        assert "field_name" in d
        assert "prediction" in d
        assert "confidence" in d
        assert "probabilities" in d

    def test_probabilities_sum_to_one(self):
        fid = field_with_data()
        r = requests.post(f"{BASE}/ml/field/{fid}/crop-stress", headers=headers(), timeout=30)
        total = sum(r.json()["probabilities"].values())
        assert abs(total - 1.0) < 1e-3

    def test_prediction_is_valid_class(self):
        fid = field_with_data()
        r = requests.post(f"{BASE}/ml/field/{fid}/crop-stress", headers=headers(), timeout=30)
        assert r.json()["prediction"] in ("Healthy", "Stressed", "Diseased")


# ---------------------------------------------------------------------------
# Irrigation weather param variations
# ---------------------------------------------------------------------------

class TestIrrigationWeatherParams:
    def test_default_weather_works(self):
        fid = field_with_data()
        r = requests.post(f"{BASE}/ml/field/{fid}/irrigation",
                          json={}, headers=headers(), timeout=30)
        assert r.status_code == 200

    def test_explicit_weather_works(self):
        fid = field_with_data()
        r = requests.post(f"{BASE}/ml/field/{fid}/irrigation",
                          json={"temp_celsius": 35, "rainfall_mm": 5},
                          headers=headers(), timeout=30)
        assert r.status_code == 200
        d = r.json()
        assert d["recommendation"] in ("irrigate_now", "irrigate_soon", "no_irrigation")

    def test_irrigation_schema(self):
        fid = field_with_data()
        r = requests.post(f"{BASE}/ml/field/{fid}/irrigation",
                          json={"temp_celsius": 28, "rainfall_mm": 50},
                          headers=headers(), timeout=30)
        d = r.json()
        for k in ("recommendation", "confidence", "soil_moisture_pct", "water_amount_mm"):
            assert k in d

    def test_high_rainfall_accepted(self):
        fid = field_with_data()
        r = requests.post(f"{BASE}/ml/field/{fid}/irrigation",
                          json={"temp_celsius": 20, "rainfall_mm": 500},
                          headers=headers(), timeout=30)
        assert r.status_code == 200

    def test_cold_temperature_accepted(self):
        fid = field_with_data()
        r = requests.post(f"{BASE}/ml/field/{fid}/irrigation",
                          json={"temp_celsius": 5, "rainfall_mm": 10},
                          headers=headers(), timeout=30)
        assert r.status_code == 200


# ---------------------------------------------------------------------------
# Yield endpoint — all crop types and param ranges
# ---------------------------------------------------------------------------

class TestYieldAPI:
    def test_default_params(self):
        fid = field_with_data()
        r = requests.post(f"{BASE}/ml/field/{fid}/yield",
                          json={}, headers=headers(), timeout=30)
        assert r.status_code == 200

    def test_yield_schema(self):
        fid = field_with_data()
        r = requests.post(f"{BASE}/ml/field/{fid}/yield",
                          json={"growing_days": 120, "rainfall_mm": 200, "temp_celsius": 26},
                          headers=headers(), timeout=30)
        d = r.json()
        for k in ("field_id", "field_name", "predicted_yield_tha",
                  "yield_lower_bound", "yield_upper_bound", "harvest_readiness_pct"):
            assert k in d

    def test_yield_positive(self):
        fid = field_with_data()
        r = requests.post(f"{BASE}/ml/field/{fid}/yield",
                          json={"growing_days": 120, "rainfall_mm": 200, "temp_celsius": 26},
                          headers=headers(), timeout=30)
        assert r.json()["predicted_yield_tha"] > 0

    def test_bounds_ordered_correctly(self):
        fid = field_with_data()
        r = requests.post(f"{BASE}/ml/field/{fid}/yield",
                          json={"growing_days": 120, "rainfall_mm": 200, "temp_celsius": 26},
                          headers=headers(), timeout=30)
        d = r.json()
        assert d["yield_lower_bound"] <= d["predicted_yield_tha"] <= d["yield_upper_bound"]

    def test_harvest_readiness_at_120_days(self):
        fid = field_with_data()
        r = requests.post(f"{BASE}/ml/field/{fid}/yield",
                          json={"growing_days": 120}, headers=headers(), timeout=30)
        assert r.json()["harvest_readiness_pct"] == pytest.approx(100.0, abs=1.0)

    def test_harvest_readiness_at_60_days(self):
        fid = field_with_data()
        r = requests.post(f"{BASE}/ml/field/{fid}/yield",
                          json={"growing_days": 60}, headers=headers(), timeout=30)
        assert r.json()["harvest_readiness_pct"] == pytest.approx(50.0, abs=1.0)


# ---------------------------------------------------------------------------
# Full analysis schema
# ---------------------------------------------------------------------------

class TestFullAnalysisAPI:
    def test_all_sections_present(self):
        fid = field_with_data()
        r = requests.post(f"{BASE}/ml/field/{fid}/full-analysis",
                          json={"weather": {"temp_celsius": 28, "rainfall_mm": 50},
                                "yield_params": {"growing_days": 120, "rainfall_mm": 200, "temp_celsius": 26}},
                          headers=headers(), timeout=60)
        assert r.status_code == 200
        d = r.json()
        for section in ("crop_stress", "irrigation", "vra_zones", "yield_prediction", "soil_assessment"):
            assert section in d, f"Missing section: {section}"

    def test_field_metadata_present(self):
        fid = field_with_data()
        r = requests.post(f"{BASE}/ml/field/{fid}/full-analysis",
                          json={}, headers=headers(), timeout=60)
        d = r.json()
        assert "field_id" in d
        assert "field_name" in d
        assert "analysed_at" in d
        assert "vegetation_indices" in d

    def test_vegetation_indices_have_ndvi(self):
        fid = field_with_data()
        r = requests.post(f"{BASE}/ml/field/{fid}/full-analysis",
                          json={}, headers=headers(), timeout=60)
        assert "ndvi" in r.json()["vegetation_indices"]

    def test_crop_type_in_response(self):
        fid = field_with_data()
        r = requests.post(f"{BASE}/ml/field/{fid}/full-analysis",
                          json={}, headers=headers(), timeout=60)
        assert "crop_type" in r.json()

    def test_unknown_field_returns_404(self):
        r = requests.post(f"{BASE}/ml/field/00000000-0000-0000-0000-000000000000/full-analysis",
                          json={}, headers=headers(), timeout=10)
        assert r.status_code == 404
