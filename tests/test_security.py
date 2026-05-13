"""
Security and data isolation tests.
Verifies that users cannot access each other's farms, fields, or ML results.
"""
import pytest
import requests

BASE = "http://localhost:8000"

USER_A = {"email": "pytest_user_a@agrosense.pk", "password": "securepassA1", "name": "User A"}
USER_B = {"email": "pytest_user_b@agrosense.pk", "password": "securepassB2", "name": "User B"}

_tokens  = {}
_farm_ids = {}
_field_ids = {}


def _register_and_login(user: dict) -> str:
    key = user["email"]
    if key in _tokens:
        return _tokens[key]
    requests.post(f"{BASE}/auth/register",
                  json={"name": user["name"], "email": user["email"],
                        "password": user["password"]}, timeout=10)
    r = requests.post(f"{BASE}/auth/login",
                      data={"username": user["email"], "password": user["password"]},
                      timeout=10)
    assert r.status_code == 200, f"Login failed for {key}: {r.text}"
    _tokens[key] = r.json()["access_token"]
    return _tokens[key]


def token_a():
    return _register_and_login(USER_A)


def token_b():
    return _register_and_login(USER_B)


def hdr(token):
    return {"Authorization": f"Bearer {token}"}


def setup_farm(token, user_key, farm_name):
    if user_key in _farm_ids:
        return _farm_ids[user_key]
    r = requests.post(f"{BASE}/farms/",
                      json={"name": farm_name, "district": "Lahore",
                            "province": "Punjab", "area_ha": 10.0,
                            "latitude": 31.5, "longitude": 74.3},
                      headers=hdr(token), timeout=10)
    assert r.status_code == 201
    _farm_ids[user_key] = r.json()["id"]
    return _farm_ids[user_key]


def setup_field(token, user_key, farm_id, field_name):
    if user_key in _field_ids:
        return _field_ids[user_key]
    r = requests.post(f"{BASE}/fields/",
                      json={"farm_id": farm_id, "name": field_name,
                            "crop_type": "wheat", "area_ha": 5.0},
                      headers=hdr(token), timeout=10)
    assert r.status_code == 201
    _field_ids[user_key] = r.json()["id"]
    return _field_ids[user_key]


# ---------------------------------------------------------------------------
# Auth edge cases
# ---------------------------------------------------------------------------

class TestAuthEdgeCases:
    def test_login_nonexistent_user(self):
        r = requests.post(f"{BASE}/auth/login",
                          data={"username": "nobody@nowhere.pk", "password": "x"},
                          timeout=5)
        assert r.status_code == 401

    def test_invalid_token_rejected(self):
        r = requests.get(f"{BASE}/auth/me",
                         headers={"Authorization": "Bearer this.is.garbage"},
                         timeout=5)
        assert r.status_code == 401

    def test_malformed_auth_header(self):
        r = requests.get(f"{BASE}/auth/me",
                         headers={"Authorization": "NotBearer sometoken"},
                         timeout=5)
        assert r.status_code == 401

    def test_empty_auth_header(self):
        r = requests.get(f"{BASE}/auth/me",
                         headers={"Authorization": ""},
                         timeout=5)
        assert r.status_code == 401

    def test_register_duplicate_email(self):
        email = "dup_test_sec@agrosense.pk"
        payload = {"name": "Dup", "email": email, "password": "pass1234"}
        requests.post(f"{BASE}/auth/register", json=payload, timeout=5)
        r = requests.post(f"{BASE}/auth/register", json=payload, timeout=5)
        assert r.status_code == 400

    def test_register_missing_fields_rejected(self):
        r = requests.post(f"{BASE}/auth/register",
                          json={"email": "incomplete@test.pk"}, timeout=5)
        assert r.status_code == 422

    def test_login_wrong_password(self):
        ta = token_a()  # ensure user A exists
        r = requests.post(f"{BASE}/auth/login",
                          data={"username": USER_A["email"], "password": "WRONG"},
                          timeout=5)
        assert r.status_code == 401


# ---------------------------------------------------------------------------
# Cross-user farm isolation
# ---------------------------------------------------------------------------

class TestFarmIsolation:
    def test_user_b_cannot_read_user_a_farm(self):
        ta = token_a()
        tb = token_b()
        farm_a = setup_farm(ta, "a", "Farm A Security Test")
        r = requests.get(f"{BASE}/farms/{farm_a}", headers=hdr(tb), timeout=10)
        assert r.status_code == 404

    def test_user_b_cannot_update_user_a_farm(self):
        ta = token_a()
        tb = token_b()
        farm_a = setup_farm(ta, "a", "Farm A Security Test")
        r = requests.patch(f"{BASE}/farms/{farm_a}",
                           json={"name": "Hacked Farm"},
                           headers=hdr(tb), timeout=10)
        assert r.status_code == 404

    def test_user_b_cannot_delete_user_a_farm(self):
        ta = token_a()
        tb = token_b()
        farm_a = setup_farm(ta, "a", "Farm A Security Test")
        r = requests.delete(f"{BASE}/farms/{farm_a}", headers=hdr(tb), timeout=10)
        assert r.status_code == 404

    def test_user_farms_list_is_isolated(self):
        ta = token_a()
        tb = token_b()
        farm_a = setup_farm(ta, "a", "Farm A Security Test")
        setup_farm(tb, "b", "Farm B Security Test")
        farms_a = requests.get(f"{BASE}/farms/", headers=hdr(ta), timeout=10).json()
        farms_b = requests.get(f"{BASE}/farms/", headers=hdr(tb), timeout=10).json()
        ids_a = {f["id"] for f in farms_a}
        ids_b = {f["id"] for f in farms_b}
        assert ids_a.isdisjoint(ids_b), "Users share farm IDs — isolation broken"


# ---------------------------------------------------------------------------
# Cross-user field isolation
# ---------------------------------------------------------------------------

class TestFieldIsolation:
    def test_user_b_cannot_read_user_a_field(self):
        ta = token_a()
        tb = token_b()
        farm_a  = setup_farm(ta, "a", "Farm A Security Test")
        field_a = setup_field(ta, "a", farm_a, "Field A Sec")
        r = requests.get(f"{BASE}/fields/{field_a}", headers=hdr(tb), timeout=10)
        assert r.status_code == 404

    def test_user_b_cannot_list_user_a_fields(self):
        ta = token_a()
        tb = token_b()
        farm_a = setup_farm(ta, "a", "Farm A Security Test")
        r = requests.get(f"{BASE}/fields/farm/{farm_a}", headers=hdr(tb), timeout=10)
        # Either 404 (farm not visible) or empty list
        assert r.status_code in (200, 404)
        if r.status_code == 200:
            assert r.json() == []

    def test_user_b_cannot_run_ml_on_user_a_field(self):
        ta = token_a()
        tb = token_b()
        farm_a  = setup_farm(ta, "a", "Farm A Security Test")
        field_a = setup_field(ta, "a", farm_a, "Field A Sec")
        r = requests.post(f"{BASE}/ml/field/{field_a}/crop-stress",
                          headers=hdr(tb), timeout=10)
        assert r.status_code == 404

    def test_user_b_cannot_access_user_a_predictions(self):
        ta = token_a()
        tb = token_b()
        farm_a  = setup_farm(ta, "a", "Farm A Security Test")
        field_a = setup_field(ta, "a", farm_a, "Field A Sec")
        r = requests.get(f"{BASE}/predictions/field/{field_a}/ml",
                         headers=hdr(tb), timeout=10)
        assert r.status_code == 404

    def test_user_b_cannot_view_user_a_imagery(self):
        ta = token_a()
        tb = token_b()
        farm_a  = setup_farm(ta, "a", "Farm A Security Test")
        field_a = setup_field(ta, "a", farm_a, "Field A Sec")
        r = requests.get(f"{BASE}/imagery/field/{field_a}/history",
                         headers=hdr(tb), timeout=10)
        assert r.status_code in (200, 404)
        if r.status_code == 200:
            assert r.json() == []


# ---------------------------------------------------------------------------
# No-auth on all ML endpoints
# ---------------------------------------------------------------------------

FAKE_FIELD = "00000000-0000-0000-0000-000000000001"

@pytest.mark.parametrize("endpoint", [
    f"/ml/field/{FAKE_FIELD}/crop-stress",
    f"/ml/field/{FAKE_FIELD}/irrigation",
    f"/ml/field/{FAKE_FIELD}/vra-zones",
    f"/ml/field/{FAKE_FIELD}/yield",
    f"/ml/field/{FAKE_FIELD}/soil",
    f"/ml/field/{FAKE_FIELD}/full-analysis",
    f"/farms/",
    f"/fields/farm/{FAKE_FIELD}",
    f"/predictions/field/{FAKE_FIELD}/ml",
    "/auth/me",
])
def test_unauthenticated_returns_401(endpoint):
    r = requests.get(f"{BASE}{endpoint}", timeout=5)
    if r.status_code != 401:
        r = requests.post(f"{BASE}{endpoint}", timeout=5)
    assert r.status_code == 401, f"{endpoint} returned {r.status_code} without auth"
