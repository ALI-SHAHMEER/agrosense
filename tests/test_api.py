"""
AgroSense API Test Suite
Run: pytest tests/test_api.py -v
Make sure the backend is running: uvicorn app.main:app --port 8000
"""
import pytest
import requests

BASE = "http://localhost:8000"
TOKEN = None
FARM_ID = None
FIELD_ID = None

TEST_EMAIL    = "test_user_pytest@agrosense.pk"
TEST_PASSWORD = "testpass123"


# ── Helpers ───────────────────────────────────────────────────────────────────

def auth_headers():
    return {"Authorization": f"Bearer {TOKEN}"}


def post(path, data=None, form=False, token=True):
    headers = auth_headers() if token else {}
    if form:
        r = requests.post(f"{BASE}{path}", data=data, headers=headers, timeout=10)
    else:
        r = requests.post(f"{BASE}{path}", json=data, headers=headers, timeout=60)
    return r


def get(path):
    return requests.get(f"{BASE}{path}", headers=auth_headers(), timeout=10)


def delete(path):
    return requests.delete(f"{BASE}{path}", headers=auth_headers(), timeout=10)


# ── Health ────────────────────────────────────────────────────────────────────

def test_health():
    r = requests.get(f"{BASE}/health", timeout=5)
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
    assert data["app"] == "AgroSense"


def test_root():
    r = requests.get(f"{BASE}/", timeout=5)
    assert r.status_code == 200


# ── Auth ──────────────────────────────────────────────────────────────────────

def test_register():
    r = post("/auth/register", {
        "name": "Pytest User",
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD,
        "role": "farmer"
    }, token=False)
    # Accept 201 (created) or 400 (already exists)
    assert r.status_code in (201, 400)
    if r.status_code == 201:
        data = r.json()
        assert data["email"] == TEST_EMAIL
        assert data["role"] == "farmer"


def test_login():
    global TOKEN
    r = post("/auth/login",
             {"username": TEST_EMAIL, "password": TEST_PASSWORD},
             form=True, token=False)
    assert r.status_code == 200
    data = r.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    TOKEN = data["access_token"]


def test_login_wrong_password():
    r = post("/auth/login",
             {"username": TEST_EMAIL, "password": "wrongpassword"},
             form=True, token=False)
    assert r.status_code == 401


def test_get_me():
    r = get("/auth/me")
    assert r.status_code == 200
    data = r.json()
    assert data["email"] == TEST_EMAIL


def test_get_me_no_token():
    r = requests.get(f"{BASE}/auth/me", timeout=5)
    assert r.status_code == 401


# ── Farms ─────────────────────────────────────────────────────────────────────

def test_create_farm():
    global FARM_ID
    r = post("/farms/", {
        "name": "Pytest Farm",
        "district": "Hyderabad",
        "province": "Sindh",
        "area_ha": 25.0,
        "latitude": 25.396,
        "longitude": 68.374,
    })
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == "Pytest Farm"
    assert data["district"] == "Hyderabad"
    FARM_ID = data["id"]


def test_list_farms():
    r = get("/farms/")
    assert r.status_code == 200
    farms = r.json()
    assert isinstance(farms, list)
    assert any(f["id"] == FARM_ID for f in farms)


def test_get_farm():
    r = get(f"/farms/{FARM_ID}")
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == FARM_ID
    assert data["name"] == "Pytest Farm"


def test_get_farm_not_found():
    r = get("/farms/00000000-0000-0000-0000-000000000000")
    assert r.status_code == 404


def test_update_farm():
    r = requests.patch(
        f"{BASE}/farms/{FARM_ID}",
        json={"name": "Pytest Farm Updated"},
        headers=auth_headers(),
        timeout=10,
    )
    assert r.status_code == 200
    assert r.json()["name"] == "Pytest Farm Updated"


# ── Fields ────────────────────────────────────────────────────────────────────

def test_create_field():
    global FIELD_ID
    r = post("/fields/", {
        "farm_id": FARM_ID,
        "name": "Pytest Field",
        "crop_type": "wheat",
        "area_ha": 5.0,
        "boundary_coords": [
            [68.37, 25.39],
            [68.38, 25.39],
            [68.38, 25.40],
            [68.37, 25.40],
            [68.37, 25.39],
        ],
    })
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == "Pytest Field"
    assert data["crop_type"] == "wheat"
    FIELD_ID = data["id"]


def test_list_fields():
    r = get(f"/fields/farm/{FARM_ID}")
    assert r.status_code == 200
    fields = r.json()
    assert isinstance(fields, list)
    assert any(f["id"] == FIELD_ID for f in fields)


def test_get_field():
    r = get(f"/fields/{FIELD_ID}")
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == FIELD_ID


# ── Imagery ───────────────────────────────────────────────────────────────────

def test_imagery_analyze():
    """This test calls GEE — may take 20-30 seconds."""
    r = post("/imagery/analyze", {
        "field_id": FIELD_ID,
        "start_date": "2024-01-01",
        "end_date": "2024-03-01",
        "max_cloud_pct": 30,
    })
    assert r.status_code == 200
    data = r.json()
    assert data["status"] in ("success", "no_images")
    if data["status"] == "success":
        assert "indices" in data
        assert "ndvi" in data["indices"]


def test_index_history():
    r = get(f"/imagery/field/{FIELD_ID}/history")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


# ── ML Models ─────────────────────────────────────────────────────────────────

def test_full_analysis():
    """Requires imagery to have been run first."""
    r = post(f"/ml/field/{FIELD_ID}/full-analysis", {
        "weather": {"temp_celsius": 28, "rainfall_mm": 10},
        "yield_params": {"growing_days": 120, "rainfall_mm": 200, "temp_celsius": 26},
    })
    # May fail with 400 if no imagery data exists yet
    assert r.status_code in (200, 400)
    if r.status_code == 200:
        data = r.json()
        assert "crop_stress" in data
        assert "irrigation" in data
        assert "yield_prediction" in data
        assert "soil_assessment" in data
        assert "vra_zones" in data


def test_crop_stress():
    r = post(f"/ml/field/{FIELD_ID}/crop-stress")
    assert r.status_code in (200, 400)


def test_irrigation():
    r = post(f"/ml/field/{FIELD_ID}/irrigation")
    assert r.status_code in (200, 400)


def test_yield():
    r = post(f"/ml/field/{FIELD_ID}/yield")
    assert r.status_code in (200, 400)


# ── Cleanup ───────────────────────────────────────────────────────────────────

def test_delete_farm():
    """Delete test farm (cascades to fields)."""
    r = delete(f"/farms/{FARM_ID}")
    assert r.status_code == 204


def test_farm_deleted():
    r = get(f"/farms/{FARM_ID}")
    assert r.status_code == 404
