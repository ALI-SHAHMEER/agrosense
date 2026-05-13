"""
Tests for /predictions/* history endpoints and data persistence.
Verifies ML runs are saved and retrievable, filter params work,
and field/farm CRUD operations behave correctly.
"""
import pytest
import requests

BASE = "http://localhost:8000"
EMAIL    = "areo5459@gmail.com"
PASSWORD = "12345678"

_token = None
_farm_id = None
_field_id = None   # field with imagery data
_new_farm_id = None
_new_field_id = None


def get_token():
    global _token
    if _token:
        return _token
    r = requests.post(f"{BASE}/auth/login",
                      data={"username": EMAIL, "password": PASSWORD}, timeout=10)
    _token = r.json()["access_token"]
    return _token


def hdr():
    return {"Authorization": f"Bearer {get_token()}"}


def field_with_data():
    """Return first field_id that has vegetation index data."""
    global _field_id, _farm_id
    if _field_id:
        return _field_id, _farm_id
    farms = requests.get(f"{BASE}/farms/", headers=hdr(), timeout=10).json()
    for farm in farms:
        fields = requests.get(f"{BASE}/fields/farm/{farm['id']}", headers=hdr(), timeout=10).json()
        for f in fields:
            r = requests.post(f"{BASE}/ml/field/{f['id']}/crop-stress",
                               headers=hdr(), timeout=30)
            if r.status_code == 200:
                _field_id = f["id"]
                _farm_id  = farm["id"]
                return _field_id, _farm_id
    pytest.skip("No field with imagery data available")


# ---------------------------------------------------------------------------
# Predictions history — ML
# ---------------------------------------------------------------------------

class TestMLPredictionHistory:
    def test_ml_history_returns_list(self):
        fid, _ = field_with_data()
        r = requests.get(f"{BASE}/predictions/field/{fid}/ml", headers=hdr(), timeout=10)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_ml_history_has_entries_after_stress_run(self):
        fid, _ = field_with_data()
        requests.post(f"{BASE}/ml/field/{fid}/crop-stress", headers=hdr(), timeout=30)
        r = requests.get(f"{BASE}/predictions/field/{fid}/ml", headers=hdr(), timeout=10)
        assert len(r.json()) >= 1

    def test_ml_history_entry_schema(self):
        fid, _ = field_with_data()
        requests.post(f"{BASE}/ml/field/{fid}/crop-stress", headers=hdr(), timeout=30)
        r = requests.get(f"{BASE}/predictions/field/{fid}/ml", headers=hdr(), timeout=10)
        entry = r.json()[0]
        for key in ("id", "field_id", "model_type", "result_data", "predicted_at"):
            assert key in entry, f"Missing key: {key}"

    def test_model_type_filter_crop_stress(self):
        fid, _ = field_with_data()
        requests.post(f"{BASE}/ml/field/{fid}/crop-stress", headers=hdr(), timeout=30)
        r = requests.get(f"{BASE}/predictions/field/{fid}/ml?model_type=crop_stress",
                         headers=hdr(), timeout=10)
        assert r.status_code == 200
        for entry in r.json():
            assert entry["model_type"] == "crop_stress"

    def test_model_type_filter_vra(self):
        fid, _ = field_with_data()
        requests.post(f"{BASE}/ml/field/{fid}/vra-zones", headers=hdr(), timeout=30)
        r = requests.get(f"{BASE}/predictions/field/{fid}/ml?model_type=vra_zones",
                         headers=hdr(), timeout=10)
        assert r.status_code == 200
        for entry in r.json():
            assert entry["model_type"] == "vra_zones"

    def test_ml_history_unknown_field_returns_404(self):
        r = requests.get(f"{BASE}/predictions/field/00000000-0000-0000-0000-000000000000/ml",
                         headers=hdr(), timeout=10)
        assert r.status_code == 404

    def test_ml_history_no_auth_returns_401(self):
        fid, _ = field_with_data()
        r = requests.get(f"{BASE}/predictions/field/{fid}/ml", timeout=5)
        assert r.status_code == 401

    def test_multiple_runs_accumulate(self):
        fid, _ = field_with_data()
        r_before = requests.get(f"{BASE}/predictions/field/{fid}/ml?model_type=crop_stress",
                                headers=hdr(), timeout=10)
        count_before = len(r_before.json())
        requests.post(f"{BASE}/ml/field/{fid}/crop-stress", headers=hdr(), timeout=30)
        requests.post(f"{BASE}/ml/field/{fid}/crop-stress", headers=hdr(), timeout=30)
        r_after = requests.get(f"{BASE}/predictions/field/{fid}/ml?model_type=crop_stress",
                               headers=hdr(), timeout=10)
        assert len(r_after.json()) >= count_before + 2

    def test_ml_history_ordered_by_recency(self):
        fid, _ = field_with_data()
        r = requests.get(f"{BASE}/predictions/field/{fid}/ml", headers=hdr(), timeout=10)
        entries = r.json()
        if len(entries) >= 2:
            assert entries[0]["predicted_at"] >= entries[1]["predicted_at"]


# ---------------------------------------------------------------------------
# Predictions history — Irrigation
# ---------------------------------------------------------------------------

class TestIrrigationHistory:
    def test_irrigation_history_returns_list(self):
        fid, _ = field_with_data()
        r = requests.get(f"{BASE}/predictions/field/{fid}/irrigation", headers=hdr(), timeout=10)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_irrigation_history_has_entry_after_run(self):
        fid, _ = field_with_data()
        requests.post(f"{BASE}/ml/field/{fid}/irrigation",
                      json={"temp_celsius": 28, "rainfall_mm": 20},
                      headers=hdr(), timeout=30)
        r = requests.get(f"{BASE}/predictions/field/{fid}/irrigation", headers=hdr(), timeout=10)
        assert len(r.json()) >= 1

    def test_irrigation_history_schema(self):
        fid, _ = field_with_data()
        requests.post(f"{BASE}/ml/field/{fid}/irrigation", json={}, headers=hdr(), timeout=30)
        r = requests.get(f"{BASE}/predictions/field/{fid}/irrigation", headers=hdr(), timeout=10)
        entry = r.json()[0]
        for key in ("id", "field_id", "recommendation", "soil_moisture_pct", "water_amount_mm"):
            assert key in entry, f"Missing key: {key}"

    def test_irrigation_history_no_auth_returns_401(self):
        fid, _ = field_with_data()
        r = requests.get(f"{BASE}/predictions/field/{fid}/irrigation", timeout=5)
        assert r.status_code == 401


# ---------------------------------------------------------------------------
# Predictions history — Yield
# ---------------------------------------------------------------------------

class TestYieldHistory:
    def test_yield_history_returns_list(self):
        fid, _ = field_with_data()
        r = requests.get(f"{BASE}/predictions/field/{fid}/yield", headers=hdr(), timeout=10)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_yield_history_has_entry_after_run(self):
        fid, _ = field_with_data()
        requests.post(f"{BASE}/ml/field/{fid}/yield",
                      json={"growing_days": 90, "rainfall_mm": 180, "temp_celsius": 27},
                      headers=hdr(), timeout=30)
        r = requests.get(f"{BASE}/predictions/field/{fid}/yield", headers=hdr(), timeout=10)
        assert len(r.json()) >= 1

    def test_yield_history_schema(self):
        fid, _ = field_with_data()
        requests.post(f"{BASE}/ml/field/{fid}/yield", json={}, headers=hdr(), timeout=30)
        r = requests.get(f"{BASE}/predictions/field/{fid}/yield", headers=hdr(), timeout=10)
        entry = r.json()[0]
        for key in ("id", "field_id", "predicted_yield_tha",
                    "yield_lower_bound", "yield_upper_bound"):
            assert key in entry, f"Missing key: {key}"

    def test_yield_bounds_sane_in_history(self):
        fid, _ = field_with_data()
        requests.post(f"{BASE}/ml/field/{fid}/yield", json={}, headers=hdr(), timeout=30)
        r = requests.get(f"{BASE}/predictions/field/{fid}/yield", headers=hdr(), timeout=10)
        entry = r.json()[0]
        assert entry["yield_lower_bound"] <= entry["predicted_yield_tha"] <= entry["yield_upper_bound"]


# ---------------------------------------------------------------------------
# Field CRUD (update and delete — not in original test suite)
# ---------------------------------------------------------------------------

class TestFieldCRUD:
    def _create_farm_and_field(self):
        global _new_farm_id, _new_field_id
        if _new_farm_id is None:
            fr = requests.post(f"{BASE}/farms/",
                               json={"name": "History Test Farm", "district": "Karachi",
                                     "province": "Sindh", "area_ha": 8.0,
                                     "latitude": 24.8, "longitude": 67.0},
                               headers=hdr(), timeout=10)
            assert fr.status_code == 201
            _new_farm_id = fr.json()["id"]
        if _new_field_id is None:
            r = requests.post(f"{BASE}/fields/",
                              json={"farm_id": _new_farm_id, "name": "History Test Field",
                                    "crop_type": "rice", "area_ha": 4.0},
                              headers=hdr(), timeout=10)
            assert r.status_code == 201
            _new_field_id = r.json()["id"]
        return _new_farm_id, _new_field_id

    def test_update_field_name(self):
        _, field_id = self._create_farm_and_field()
        r = requests.patch(f"{BASE}/fields/{field_id}",
                           json={"name": "Renamed Field"},
                           headers=hdr(), timeout=10)
        assert r.status_code == 200
        assert r.json()["name"] == "Renamed Field"

    def test_update_field_crop_type(self):
        _, field_id = self._create_farm_and_field()
        r = requests.patch(f"{BASE}/fields/{field_id}",
                           json={"crop_type": "cotton"},
                           headers=hdr(), timeout=10)
        assert r.status_code == 200
        assert r.json()["crop_type"] == "cotton"

    def test_update_nonexistent_field_returns_404(self):
        r = requests.patch(f"{BASE}/fields/00000000-0000-0000-0000-000000000000",
                           json={"name": "Ghost"},
                           headers=hdr(), timeout=10)
        assert r.status_code == 404

    def test_delete_field(self):
        global _new_field_id
        _, field_id = self._create_farm_and_field()
        r = requests.delete(f"{BASE}/fields/{field_id}", headers=hdr(), timeout=10)
        assert r.status_code == 204
        _new_field_id = None  # reset so next test re-creates

    def test_deleted_field_is_gone(self):
        global _new_field_id
        farm_id, _ = self._create_farm_and_field()
        field_id = _new_field_id
        requests.delete(f"{BASE}/fields/{field_id}", headers=hdr(), timeout=10)
        _new_field_id = None
        r = requests.get(f"{BASE}/fields/{field_id}", headers=hdr(), timeout=10)
        assert r.status_code == 404

    def test_field_no_imagery_returns_400_on_ml(self):
        global _new_farm_id, _new_field_id
        _new_farm_id = None
        _new_field_id = None
        farm_id, field_id = self._create_farm_and_field()
        r = requests.post(f"{BASE}/ml/field/{field_id}/crop-stress",
                          headers=hdr(), timeout=10)
        assert r.status_code == 400
        assert "No vegetation indices" in r.json()["detail"]
