import requests

BASE_URL = "http://localhost:8000"
_token = None

def set_token(t): global _token; _token = t
def get_token(): return _token
def _h(): return {"Authorization": f"Bearer {_token}"} if _token else {}

def _get(path):
    r = requests.get(f"{BASE_URL}{path}", headers=_h(), timeout=30)
    r.raise_for_status(); return r.json()

def _post(path, data=None, form=False):
    if form:
        r = requests.post(f"{BASE_URL}{path}", data=data, timeout=30)
    else:
        r = requests.post(f"{BASE_URL}{path}", json=data, headers=_h(), timeout=120)
    r.raise_for_status(); return r.json()

def login(email, password):
    return _post("/auth/login", {"username": email, "password": password}, form=True)

def get_me():
    return _get("/auth/me")

def register(name, email, password, role="farmer"):
    return _post("/auth/register", {"name":name,"email":email,"password":password,"role":role})

def get_farms():
    return _get("/farms/")

def create_farm(name, district="", province="", area_ha=None, latitude=None, longitude=None):
    p = {"name":name, "district":district, "province":province}
    if area_ha:   p["area_ha"]   = float(area_ha)
    if latitude:  p["latitude"]  = float(latitude)
    if longitude: p["longitude"] = float(longitude)
    return _post("/farms/", p)

def delete_farm(farm_id):
    r = requests.delete(f"{BASE_URL}/farms/{farm_id}", headers=_h(), timeout=10)
    r.raise_for_status()

def get_fields(farm_id):
    return _get(f"/fields/farm/{farm_id}")

def create_field(farm_id, name, crop_type="", area_ha=None, boundary_coords=None):
    p = {"farm_id": str(farm_id), "name": name, "crop_type": crop_type or ""}
    if area_ha: p["area_ha"] = float(area_ha)
    if boundary_coords: p["boundary_coords"] = boundary_coords
    print(f"POST {BASE_URL}/fields/ payload={p}")
    r = requests.post(f"{BASE_URL}/fields/", json=p, headers=_h(), timeout=30)
    print(f"Response: {r.status_code} - {r.text[:200]}")
    r.raise_for_status()
    return r.json()

def analyze_imagery(field_id, start_date, end_date, max_cloud=30):
    return _post("/imagery/analyze", {
        "field_id": field_id, "start_date": start_date,
        "end_date": end_date, "max_cloud_pct": max_cloud,
    })

def get_index_history(field_id):
    return _get(f"/imagery/field/{field_id}/history")

def full_analysis(field_id, temp=28, rain=10, growing_days=120, rain_yield=200, temp_yield=26):
    return _post(f"/ml/field/{field_id}/full-analysis", {
        "weather": {"temp_celsius": temp, "rainfall_mm": rain},
        "yield_params": {"growing_days": growing_days, "rainfall_mm": rain_yield, "temp_celsius": temp_yield},
    })

def health_check():
    try:
        r = requests.get(f"{BASE_URL}/health", timeout=5)
        return r.status_code == 200
    except: return False

def get_smart_farming(field_id):
    return _get(f"/weather/smart-farming/{field_id}")

def get_current_weather(field_id):
    return _get(f"/weather/current/{field_id}")

def get_band_thumbnail(field_id, band_type, start_date, end_date) -> bytes:
    import requests as req
    r = req.get(
        f"{BASE_URL}/imagery/field/{field_id}/bands/{band_type}",
        params={"start_date": start_date, "end_date": end_date},
        headers=_h(), timeout=90
    )
    r.raise_for_status()
    return r.content
