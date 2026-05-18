# Smart Farming Recommendations Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a Smart Farming page to AgroSense that shows a 7-day weather forecast, automated crop protection alerts, and AI-powered planting recommendations for the user's selected field.

**Architecture:** A new FastAPI router (`app/routers/weather.py`) fetches Open-Meteo data, runs a rule-based alert engine, calls the existing ML predictors, and returns a single unified JSON payload. The desktop page (`desktop/pages/smart_farming.py`) is display-only — it calls one API endpoint and renders the response.

**Tech Stack:** FastAPI, SQLAlchemy, Open-Meteo (free, no key), PyQt6, requests, existing `app.ml.predictor` functions.

---

## File Map

| Action | File | Purpose |
|--------|------|---------|
| Create | `app/routers/weather.py` | Endpoint + rule engine + planting scorer |
| Create | `tests/test_weather.py` | Unit tests for rule engine and scorer |
| Modify | `app/main.py` | Register weather router |
| Modify | `desktop/api.py` | Add `get_smart_farming()` |
| Modify | `desktop/i18n.py` | Add 30 translation keys |
| Create | `desktop/pages/smart_farming.py` | Smart Farming desktop page |
| Modify | `desktop/windows/main_window.py` | Add to NAV + import |

---

## Task 1: Backend weather router and tests

**Files:**
- Create: `app/routers/weather.py`
- Create: `tests/test_weather.py`

### Step 1.1: Write failing tests for the rule engine

Create `tests/test_weather.py`:

```python
import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# We import only the pure functions — no DB, no HTTP needed
from app.routers.weather import _wmo_to_condition, _apply_rules, _planting_recommendation


def _day(temp_max=25, temp_min=15, temp_avg=20, rain_mm=0,
         rain_probability=10, humidity=60, wind_kmh=15,
         date="2026-05-18", day_name="Monday", condition="clear"):
    return dict(temp_max=temp_max, temp_min=temp_min, temp_avg=temp_avg,
                rain_mm=rain_mm, rain_probability=rain_probability,
                humidity=humidity, wind_kmh=wind_kmh, date=date,
                day_name=day_name, condition=condition)


# ── WMO condition map ─────────────────────────────────────────────────────────

def test_wmo_clear():
    assert _wmo_to_condition(0) == "clear"

def test_wmo_partly_cloudy():
    for code in (1, 2, 3):
        assert _wmo_to_condition(code) == "partly_cloudy"

def test_wmo_foggy():
    assert _wmo_to_condition(45) == "foggy"
    assert _wmo_to_condition(48) == "foggy"

def test_wmo_drizzle():
    for code in (51, 55, 61, 65, 67):
        assert _wmo_to_condition(code) == "drizzle"

def test_wmo_snow():
    assert _wmo_to_condition(71) == "snow"
    assert _wmo_to_condition(77) == "snow"

def test_wmo_rain_showers():
    for code in (80, 81, 82):
        assert _wmo_to_condition(code) == "rain_showers"

def test_wmo_thunderstorm():
    for code in (95, 96, 99):
        assert _wmo_to_condition(code) == "thunderstorm"

def test_wmo_unknown_returns_partly_cloudy():
    assert _wmo_to_condition(999) == "partly_cloudy"


# ── Rule engine — heatwave ────────────────────────────────────────────────────

def test_heatwave_triggered_on_two_consecutive_hot_days():
    forecast = [_day(temp_max=39)] * 7
    alerts = _apply_rules(forecast)
    types = [a["type"] for a in alerts]
    assert "heatwave" in types

def test_heatwave_not_triggered_on_single_hot_day():
    forecast = [_day(temp_max=39)] + [_day()] * 6
    alerts = _apply_rules(forecast)
    assert not any(a["type"] == "heatwave" for a in alerts)

def test_heatwave_not_triggered_below_threshold():
    forecast = [_day(temp_max=37)] * 7
    alerts = _apply_rules(forecast)
    assert not any(a["type"] == "heatwave" for a in alerts)


# ── Rule engine — heavy rain ──────────────────────────────────────────────────

def test_heavy_rain_triggered():
    forecast = [_day(rain_mm=30)] + [_day()] * 6
    alerts = _apply_rules(forecast)
    assert any(a["type"] == "heavy_rain" for a in alerts)

def test_heavy_rain_not_triggered_below_25():
    forecast = [_day(rain_mm=24)] * 7
    alerts = _apply_rules(forecast)
    assert not any(a["type"] == "heavy_rain" for a in alerts)


# ── Rule engine — frost ───────────────────────────────────────────────────────

def test_frost_triggered():
    forecast = [_day(temp_min=2)] + [_day()] * 6
    alerts = _apply_rules(forecast)
    assert any(a["type"] == "frost" for a in alerts)

def test_frost_not_triggered_above_4():
    forecast = [_day(temp_min=5)] * 7
    alerts = _apply_rules(forecast)
    assert not any(a["type"] == "frost" for a in alerts)


# ── Rule engine — drought ─────────────────────────────────────────────────────

def test_drought_triggered():
    forecast = [_day(rain_mm=0, temp_avg=32)] * 7
    alerts = _apply_rules(forecast)
    assert any(a["type"] == "drought" for a in alerts)

def test_drought_not_triggered_enough_rain():
    forecast = [_day(rain_mm=2, temp_avg=32)] * 7  # total = 14mm
    alerts = _apply_rules(forecast)
    assert not any(a["type"] == "drought" for a in alerts)

def test_drought_not_triggered_cool_weather():
    forecast = [_day(rain_mm=0, temp_avg=28)] * 7
    alerts = _apply_rules(forecast)
    assert not any(a["type"] == "drought" for a in alerts)


# ── Rule engine — strong wind ─────────────────────────────────────────────────

def test_strong_wind_triggered():
    forecast = [_day(wind_kmh=50)] + [_day()] * 6
    alerts = _apply_rules(forecast)
    assert any(a["type"] == "strong_wind" for a in alerts)

def test_strong_wind_not_triggered():
    forecast = [_day(wind_kmh=39)] * 7
    alerts = _apply_rules(forecast)
    assert not any(a["type"] == "strong_wind" for a in alerts)


# ── Rule engine — spray delay ─────────────────────────────────────────────────

def test_spray_delay_triggered_day0():
    forecast = [_day(rain_probability=65)] + [_day()] * 6
    alerts = _apply_rules(forecast)
    assert any(a["type"] == "spray_delay" for a in alerts)

def test_spray_delay_triggered_day1():
    forecast = [_day()] + [_day(rain_probability=70)] + [_day()] * 5
    alerts = _apply_rules(forecast)
    assert any(a["type"] == "spray_delay" for a in alerts)

def test_spray_delay_not_triggered_after_day1():
    forecast = [_day()] * 2 + [_day(rain_probability=80)] + [_day()] * 4
    alerts = _apply_rules(forecast)
    assert not any(a["type"] == "spray_delay" for a in alerts)


# ── Rule engine — fungal risk ─────────────────────────────────────────────────

def test_fungal_risk_triggered_three_consecutive_humid_days():
    forecast = [_day(humidity=90)] * 7
    alerts = _apply_rules(forecast)
    assert any(a["type"] == "fungal_risk" for a in alerts)

def test_fungal_risk_not_triggered_two_days():
    forecast = [_day(humidity=90), _day(humidity=90)] + [_day()] * 5
    alerts = _apply_rules(forecast)
    assert not any(a["type"] == "fungal_risk" for a in alerts)


# ── No duplicate alerts ───────────────────────────────────────────────────────

def test_no_duplicate_heatwave_alerts():
    forecast = [_day(temp_max=40)] * 7
    alerts = _apply_rules(forecast)
    assert sum(1 for a in alerts if a["type"] == "heatwave") == 1

def test_no_duplicate_fungal_risk_alerts():
    forecast = [_day(humidity=95)] * 7
    alerts = _apply_rules(forecast)
    assert sum(1 for a in alerts if a["type"] == "fungal_risk") == 1


# ── Planting recommendation ───────────────────────────────────────────────────

def test_suitability_ideal_conditions():
    forecast = [_day(temp_avg=25, rain_mm=3)] * 7
    irrig = {"confidence": 0.8, "water_amount_mm": 20.0}
    rec = _planting_recommendation(forecast, [], irrig)
    assert rec["suitability_score"] > 0.7
    assert rec["risk_level"] == "low"

def test_suitability_low_when_high_alerts():
    forecast = [_day(temp_avg=25)] * 7
    alerts = [{"type": "heatwave", "severity": "high"}]
    rec = _planting_recommendation(forecast, alerts, None)
    assert rec["risk_level"] == "high"
    # risk_score reduced by 0.4, pulling suitability down
    assert rec["suitability_score"] < 0.85

def test_ideal_date_set_when_suitability_exceeds_threshold():
    forecast = [_day(temp_avg=25, rain_mm=2, date=f"2026-05-{18+i:02d}") for i in range(7)]
    rec = _planting_recommendation(forecast, [], {"confidence": 0.9, "water_amount_mm": 15.0})
    assert rec["ideal_date"] is not None

def test_ideal_date_none_when_all_days_unsuitable():
    # Extreme heat makes all days score low
    forecast = [_day(temp_avg=50, date=f"2026-05-{18+i:02d}") for i in range(7)]
    alerts = [{"type": "heatwave", "severity": "high"}, {"type": "drought", "severity": "medium"}]
    rec = _planting_recommendation(forecast, alerts, None)
    assert rec["ideal_date"] is None

def test_water_requirement_from_irrig_model():
    forecast = [_day()] * 7
    irrig = {"confidence": 0.7, "water_amount_mm": 35.0}
    rec = _planting_recommendation(forecast, [], irrig)
    assert rec["water_requirement_mm"] == 35.0

def test_reasons_list_max_three():
    forecast = [_day()] * 7
    rec = _planting_recommendation(forecast, [], None)
    assert len(rec["reasons"]) <= 3
```

- [ ] **Step 1.2: Run tests to verify they fail**

```bash
cd /home/ali/Agrosense/agrosense && conda run -n agrosense pytest tests/test_weather.py -v 2>&1 | head -30
```

Expected: `ImportError` or `ModuleNotFoundError` — `app.routers.weather` doesn't exist yet.

- [ ] **Step 1.3: Create `app/routers/weather.py` with all pure functions**

```python
"""
Smart Farming Recommendations — Weather Router
GET /weather/smart-farming/{field_id}
"""
import logging
import requests as _requests
from datetime import date as _date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Farm, Field
from app.routers.auth import get_current_user

log = logging.getLogger(__name__)

router = APIRouter(prefix="/weather", tags=["Weather"])


# ── WMO weathercode → condition string ───────────────────────────────────────

def _wmo_to_condition(code: int) -> str:
    if code == 0:
        return "clear"
    if code in (1, 2, 3):
        return "partly_cloudy"
    if code in (45, 48):
        return "foggy"
    if 51 <= code <= 67:
        return "drizzle"
    if 71 <= code <= 77:
        return "snow"
    if 80 <= code <= 82:
        return "rain_showers"
    if 95 <= code <= 99:
        return "thunderstorm"
    return "partly_cloudy"


# ── Rule engine ───────────────────────────────────────────────────────────────

def _apply_rules(forecast: list) -> list:
    alerts = []
    n = len(forecast)

    # Heatwave: temp_max > 38 for 2+ consecutive days
    streak, first_day = 0, None
    for i, day in enumerate(forecast):
        if day["temp_max"] > 38:
            if streak == 0:
                first_day = i
            streak += 1
            if streak >= 2 and not any(a["type"] == "heatwave" for a in alerts):
                alerts.append({
                    "type": "heatwave", "severity": "high",
                    "title": "Heatwave Warning",
                    "message": f"Temperature exceeding 38°C for {streak} consecutive days",
                    "action": "Increase irrigation frequency and provide shade",
                    "days_until": first_day,
                })
        else:
            streak = 0

    # Heavy rain: daily rain > 25 mm
    for i, day in enumerate(forecast):
        if day["rain_mm"] > 25:
            alerts.append({
                "type": "heavy_rain", "severity": "high",
                "title": "Heavy Rain Alert",
                "message": f"Heavy rainfall of {day['rain_mm']:.0f} mm expected",
                "action": "Delay irrigation; inspect for waterlogging",
                "days_until": i,
            })
            break

    # Frost: temp_min < 4°C on any day
    for i, day in enumerate(forecast):
        if day["temp_min"] < 4:
            alerts.append({
                "type": "frost", "severity": "high",
                "title": "Frost Warning",
                "message": f"Temperature dropping to {day['temp_min']:.0f}°C",
                "action": "Cover crops or use frost protection measures",
                "days_until": i,
            })
            break

    # Drought: total rain < 5 mm AND avg temp > 30°C
    total_rain = sum(d["rain_mm"] for d in forecast)
    avg_temp = sum(d["temp_avg"] for d in forecast) / n if n else 0
    if total_rain < 5 and avg_temp > 30:
        alerts.append({
            "type": "drought", "severity": "medium",
            "title": "Drought Risk",
            "message": f"Only {total_rain:.1f} mm rain expected with avg temp {avg_temp:.0f}°C",
            "action": "Prepare supplemental irrigation immediately",
            "days_until": 0,
        })

    # Strong wind: wind > 40 km/h on any day
    for i, day in enumerate(forecast):
        if day["wind_kmh"] > 40:
            alerts.append({
                "type": "strong_wind", "severity": "medium",
                "title": "Strong Wind Alert",
                "message": f"Wind speeds of {day['wind_kmh']:.0f} km/h expected",
                "action": "Secure structures; delay spraying operations",
                "days_until": i,
            })
            break

    # Spray delay: rain probability > 60% on day 0 or day 1
    for i in range(min(2, n)):
        if forecast[i]["rain_probability"] > 60:
            alerts.append({
                "type": "spray_delay", "severity": "low",
                "title": "Delay Pesticide Spraying",
                "message": f"{forecast[i]['rain_probability']}% chance of rain on day {i + 1}",
                "action": "Postpone spraying by at least 2 days",
                "days_until": i,
            })
            break

    # Fungal risk: humidity > 85% for 3+ consecutive days
    streak, first_day = 0, None
    for i, day in enumerate(forecast):
        if day["humidity"] > 85:
            if streak == 0:
                first_day = i
            streak += 1
            if streak >= 3 and not any(a["type"] == "fungal_risk" for a in alerts):
                alerts.append({
                    "type": "fungal_risk", "severity": "low",
                    "title": "Fungal Disease Risk",
                    "message": f"Humidity above 85% for {streak}+ consecutive days",
                    "action": "Apply fungicide preventatively",
                    "days_until": first_day,
                })
        else:
            streak = 0

    return alerts


# ── Planting recommendation ───────────────────────────────────────────────────

def _planting_recommendation(forecast: list, alerts: list, irrig_result: dict | None) -> dict:
    n = len(forecast)
    avg_temp = sum(d["temp_avg"] for d in forecast) / n if n else 25
    total_rain = sum(d["rain_mm"] for d in forecast)

    # Temperature score: 1.0 if 20–30°C, decays linearly outside that band
    temp_score = 1.0 if 20 <= avg_temp <= 30 else max(0.0, 1.0 - abs(avg_temp - 25) / 15)

    # Moisture score from irrigation model confidence (0.0–1.0)
    moisture_score = 0.5
    water_req = 0.0
    if irrig_result:
        moisture_score = float(irrig_result.get("confidence", 0.5))
        water_req = float(irrig_result.get("water_amount_mm", 0.0))

    # Risk score: penalise high/medium/low alerts
    high_n   = sum(1 for a in alerts if a["severity"] == "high")
    medium_n = sum(1 for a in alerts if a["severity"] == "medium")
    low_n    = sum(1 for a in alerts if a["severity"] == "low")
    risk_score = max(0.0, 1.0 - (high_n * 0.4 + medium_n * 0.2 + low_n * 0.1))

    suitability = round((temp_score * 0.4) + (moisture_score * 0.4) + (risk_score * 0.2), 3)

    risk_level = "high" if high_n > 0 else ("medium" if medium_n > 0 else "low")

    # Ideal date: first forecast day whose per-day suitability > 0.7
    ideal_date = None
    for day in forecast:
        day_temp = day["temp_avg"]
        day_ts = 1.0 if 20 <= day_temp <= 30 else max(0.0, 1.0 - abs(day_temp - 25) / 15)
        if (day_ts * 0.4) + (moisture_score * 0.4) + (risk_score * 0.2) > 0.7:
            ideal_date = day["date"]
            break

    # Human-readable reasons (up to 3)
    reasons = []
    if 20 <= avg_temp <= 30:
        reasons.append("Moderate temperature forecast")
    elif avg_temp > 30:
        reasons.append(f"High temperature ({avg_temp:.0f}°C) reduces suitability")
    else:
        reasons.append(f"Cool temperature ({avg_temp:.0f}°C) may slow germination")

    if total_rain >= 10:
        reasons.append(f"Adequate rainfall forecast ({total_rain:.0f} mm)")
    elif total_rain > 0:
        reasons.append(f"Low rainfall ({total_rain:.0f} mm) — irrigation recommended")
    else:
        reasons.append("No rainfall forecast — irrigation required")

    if high_n == 0 and medium_n == 0:
        reasons.append("No significant weather risks this week")
    elif high_n > 0:
        reasons.append(f"{high_n} high-severity weather risk(s) detected")
    elif medium_n > 0:
        reasons.append(f"{medium_n} medium-severity weather risk(s) detected")

    return {
        "ideal_date": ideal_date,
        "risk_level": risk_level,
        "water_requirement_mm": round(water_req, 1),
        "suitability_score": suitability,
        "reasons": reasons[:3],
    }


# ── Open-Meteo fetch ──────────────────────────────────────────────────────────

_DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday",
              "Friday", "Saturday", "Sunday"]


def _fetch_forecast(lat: float, lon: float) -> list:
    """Fetch 7-day daily forecast from Open-Meteo. Returns list of day dicts."""
    url = "https://api.open-meteo.com/v1/forecast"
    resp = _requests.get(url, params={
        "latitude": lat,
        "longitude": lon,
        "daily": [
            "temperature_2m_max", "temperature_2m_min", "temperature_2m_mean",
            "precipitation_sum", "precipitation_probability_max",
            "windspeed_10m_max", "weathercode",
        ],
        "hourly": ["relative_humidity_2m"],
        "forecast_days": 7,
        "timezone": "auto",
    }, timeout=10)

    if resp.status_code != 200:
        raise RuntimeError(f"Open-Meteo returned {resp.status_code}")

    data = resp.json()
    daily = data["daily"]
    hourly = data.get("hourly", {})
    humidity_hourly = hourly.get("relative_humidity_2m", [])

    days = []
    for i, date_str in enumerate(daily["time"]):
        # Average 24 hourly humidity values for this day
        h_start = i * 24
        h_slice = humidity_hourly[h_start: h_start + 24]
        humidity = round(sum(h_slice) / len(h_slice), 1) if h_slice else 0

        date_obj = _date.fromisoformat(date_str)
        days.append({
            "date": date_str,
            "day_name": _DAY_NAMES[date_obj.weekday()],
            "temp_max": daily["temperature_2m_max"][i],
            "temp_min": daily["temperature_2m_min"][i],
            "temp_avg": daily["temperature_2m_mean"][i],
            "rain_mm": daily["precipitation_sum"][i] or 0,
            "rain_probability": daily["precipitation_probability_max"][i] or 0,
            "humidity": humidity,
            "wind_kmh": daily["windspeed_10m_max"][i] or 0,
            "condition": _wmo_to_condition(daily["weathercode"][i] or 0),
        })
    return days


# ── Main endpoint ─────────────────────────────────────────────────────────────

@router.get("/smart-farming/{field_id}")
def smart_farming(
    field_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Return 7-day forecast, alerts, planting recommendation, and ML summary."""
    from app.models import SatelliteImage, VegetationIndex
    from app.ml.predictor import predict_crop_stress, predict_irrigation, predict_yield

    # 1. Load field + farm
    field = (
        db.query(Field)
        .join(Farm)
        .filter(Field.id == field_id, Farm.user_id == current_user.id)
        .first()
    )
    if not field:
        raise HTTPException(status_code=404, detail="Field not found")

    farm = field.farm
    lat = farm.latitude
    lon = farm.longitude
    if lat is None or lon is None:
        raise HTTPException(status_code=422, detail="Farm location not set")

    # 2. Fetch weather forecast
    try:
        forecast = _fetch_forecast(lat, lon)
    except Exception as exc:
        log.warning("Open-Meteo fetch failed: %s", exc)
        raise HTTPException(status_code=503, detail="Weather service unavailable")

    # 3. Run rule engine
    alerts = _apply_rules(forecast)

    # 4. Weekly summary
    n = len(forecast)
    weekly_summary = {
        "avg_temp":      round(sum(d["temp_avg"] for d in forecast) / n, 1),
        "total_rain_mm": round(sum(d["rain_mm"]  for d in forecast), 1),
        "avg_humidity":  round(sum(d["humidity"] for d in forecast) / n, 1),
        "avg_wind_kmh":  round(sum(d["wind_kmh"] for d in forecast) / n, 1),
    }

    # 5. Try ML predictions (optional — graceful on failure or missing indices)
    ml_summary = None
    irrig_result = None
    latest_indices = (
        db.query(VegetationIndex)
        .join(SatelliteImage)
        .filter(SatelliteImage.field_id == field_id)
        .order_by(VegetationIndex.calculated_at.desc())
        .first()
    )
    if latest_indices:
        indices = {
            "ndvi": latest_indices.ndvi, "evi": latest_indices.evi,
            "ndwi": latest_indices.ndwi, "ndre": latest_indices.ndre,
            "lai": latest_indices.lai, "ndvi_std": latest_indices.ndvi_std,
            "ndvi_min": latest_indices.ndvi_min, "ndvi_max": latest_indices.ndvi_max,
        }
        avg_w = {
            "temp_celsius": weekly_summary["avg_temp"],
            "rainfall_mm":  weekly_summary["total_rain_mm"],
        }
        try:
            stress = predict_crop_stress(indices)
            irrig_result = predict_irrigation(indices, avg_w)
            yld = predict_yield(
                indices,
                growing_days=120,
                rainfall_mm=weekly_summary["total_rain_mm"],
                temp_celsius=weekly_summary["avg_temp"],
                crop_type=field.crop_type or "wheat",
            )
            ml_summary = {
                "crop_health": stress["prediction"],
                "irrigation":  irrig_result["recommendation"],
                "predicted_yield_tha": round(yld["predicted_yield_tha"], 2),
            }
        except Exception as exc:
            log.warning("ML prediction failed for field %s: %s", field_id, exc)

    # 6. Planting recommendation
    planting = _planting_recommendation(forecast, alerts, irrig_result)

    return {
        "field_name": field.name,
        "crop_type":  field.crop_type or "unknown",
        "location":   {"lat": lat, "lon": lon},
        "forecast":   forecast,
        "alerts":     alerts,
        "planting_recommendation": planting,
        "ml_summary": ml_summary,
        "weekly_summary": weekly_summary,
    }
```

- [ ] **Step 1.4: Run tests — they should all pass now**

```bash
cd /home/ali/Agrosense/agrosense && conda run -n agrosense pytest tests/test_weather.py -v
```

Expected: All tests PASS.

- [ ] **Step 1.5: Commit**

```bash
git add app/routers/weather.py tests/test_weather.py
git commit -m "feat: add weather router with rule engine, planting scorer, and tests"
```

---

## Task 2: Register weather router in app/main.py

**Files:**
- Modify: `app/main.py:4-6` (imports + include_router)

- [ ] **Step 2.1: Add the import and router registration**

In `app/main.py`, add after the existing router imports:

```python
from app.routers.weather import router as weather_router
```

And add after `app.include_router(ml_router)`:

```python
app.include_router(weather_router)
```

- [ ] **Step 2.2: Verify the server starts without error**

```bash
cd /home/ali/Agrosense/agrosense && conda run -n agrosense uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &
sleep 3
curl -s http://localhost:8000/docs | grep -c "smart-farming"
pkill -f "uvicorn app.main"
```

Expected: output is `1` (route appears in OpenAPI docs).

- [ ] **Step 2.3: Commit**

```bash
git add app/main.py
git commit -m "feat: register weather router at /weather prefix"
```

---

## Task 3: Desktop API function and i18n keys

**Files:**
- Modify: `desktop/api.py`
- Modify: `desktop/i18n.py`

- [ ] **Step 3.1: Add `get_smart_farming()` to `desktop/api.py`**

Add after the `health_check` function:

```python
def get_smart_farming(field_id):
    return _get(f"/weather/smart-farming/{field_id}")
```

- [ ] **Step 3.2: Add 30 i18n keys to `desktop/i18n.py`**

In `desktop/i18n.py`, find the last `"topbar_sub_*"` entry (currently `"topbar_sub_bands"`) and add these keys immediately after it:

```python
    "nav_smart":          {"en": "🌱  Smart Farming",              "ur": "🌱  ذہین زراعت"},
    "topbar_sub_smart":   {"en": "Weather & Recommendations",       "ur": "موسم اور سفارشات"},
    "smart_title":        {"en": "Smart Farming Recommendations",   "ur": "ذہین زراعت سفارشات"},
    "select_farm_first":  {"en": "Select a farm to continue",       "ur": "جاری رکھنے کے لیے فارم منتخب کریں"},
    "loading_smart":      {"en": "Fetching weather data…",          "ur": "موسمی ڈیٹا حاصل ہو رہا ہے…"},
    "alerts_title":       {"en": "⚠  Crop Protection Alerts",      "ur": "⚠  فصل حفاظت الرٹس"},
    "no_alerts":          {"en": "✅  No weather risks detected this week", "ur": "✅  اس ہفتے کوئی موسمی خطرہ نہیں"},
    "forecast_title":     {"en": "📅  7-Day Weather Forecast",      "ur": "📅  7 روزہ موسمی پیش گوئی"},
    "planting_rec_title": {"en": "🌾  Planting Recommendation",     "ur": "🌾  بوائی کی سفارش"},
    "ml_summary_title":   {"en": "🤖  ML Analysis Summary",        "ur": "🤖  ML تجزیہ خلاصہ"},
    "weekly_summary":     {"en": "📊  Weekly Summary",             "ur": "📊  ہفتہ وار خلاصہ"},
    "ideal_date":         {"en": "Ideal Planting Date",             "ur": "بہترین بوائی تاریخ"},
    "not_favorable":      {"en": "Not favorable this week",         "ur": "اس ہفتے موزوں نہیں"},
    "risk_level":         {"en": "Risk Level",                      "ur": "خطرے کی سطح"},
    "water_req":          {"en": "Water Requirement",               "ur": "پانی کی ضرورت"},
    "suitability":        {"en": "Suitability Score",               "ur": "موزونیت اسکور"},
    "avg_temp":           {"en": "Avg Temp",                        "ur": "اوسط درجہ حرارت"},
    "total_rain":         {"en": "Total Rain",                      "ur": "کل بارش"},
    "avg_humidity":       {"en": "Avg Humidity",                    "ur": "اوسط نمی"},
    "avg_wind":           {"en": "Avg Wind",                        "ur": "اوسط ہوا"},
    "alert_heatwave":     {"en": "🔥 Heatwave Warning",            "ur": "🔥 گرمی کی لہر"},
    "alert_heavy_rain":   {"en": "🌧 Heavy Rain Alert",            "ur": "🌧 شدید بارش الرٹ"},
    "alert_frost":        {"en": "❄ Frost Warning",                "ur": "❄ پالہ انتباہ"},
    "alert_drought":      {"en": "☀ Drought Risk",                 "ur": "☀ خشک سالی خطرہ"},
    "alert_strong_wind":  {"en": "💨 Strong Wind Alert",           "ur": "💨 تیز ہوا الرٹ"},
    "alert_spray_delay":  {"en": "🚫 Delay Pesticide Spraying",    "ur": "🚫 کیڑے مار دوا دیر سے چھڑکیں"},
    "alert_fungal_risk":  {"en": "🍄 Fungal Disease Risk",         "ur": "🍄 پھپھوندی بیماری خطرہ"},
    "ml_unavailable":     {"en": "ML analysis unavailable (run field analysis first)", "ur": "ML تجزیہ دستیاب نہیں (پہلے فیلڈ تجزیہ چلائیں)"},
    "crop_health_lbl":    {"en": "Crop Health",                    "ur": "فصل کی صحت"},
    "irrigation_lbl":     {"en": "Irrigation",                     "ur": "آبپاشی"},
    "yield_lbl":          {"en": "Predicted Yield",                "ur": "متوقع پیداوار"},
```

- [ ] **Step 3.3: Verify i18n keys are accessible**

```bash
cd /home/ali/Agrosense/agrosense && conda run -n agrosense python -c "
from desktop.i18n import LM
print(LM.tr('nav_smart'))
print(LM.tr('alerts_title'))
LM.toggle()
print(LM.tr('nav_smart'))
"
```

Expected:
```
🌱  Smart Farming
⚠  Crop Protection Alerts
🌱  ذہین زراعت
```

- [ ] **Step 3.4: Commit**

```bash
git add desktop/api.py desktop/i18n.py
git commit -m "feat: add get_smart_farming() API function and 30 i18n keys"
```

---

## Task 4: Smart Farming desktop page

**Files:**
- Create: `desktop/pages/smart_farming.py`

- [ ] **Step 4.1: Write the full SmartFarmingPage**

Create `desktop/pages/smart_farming.py`:

```python
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QPushButton, QComboBox, QScrollArea, QProgressBar, QSizePolicy
)
from PyQt6.QtCore import Qt
import desktop.api as api
from desktop.i18n import LM
from desktop.pages.dashboard import Worker, lbl, btn, card

G = "#1a6b35"; W = "#ffffff"; P = "#f4f6f4"
T = "#111827"; M = "#6b7280"; B = "#e2e8e4"; A = "#e8f5ee"
BLUE = "#2563eb"; RED = "#dc2626"; GOLD = "#d4a017"; EMERALD = "#22c55e"

SEVERITY_COLOR = {"high": RED, "medium": GOLD, "low": EMERALD}

CONDITION_EMOJI = {
    "clear": "☀️", "partly_cloudy": "⛅", "foggy": "🌫️",
    "drizzle": "🌦️", "rain_showers": "🌧️", "snow": "❄️",
    "thunderstorm": "⛈️",
}


def _combo():
    c = QComboBox()
    c.setFixedHeight(38)
    c.setStyleSheet(f"""
        QComboBox{{color:{T};background:{W};border:1.5px solid {B};border-radius:9px;
                   padding:0 12px;font-size:13px;font-family:'Segoe UI';}}
        QComboBox:focus{{border-color:{G};}}
        QComboBox QAbstractItemView{{color:{T};background:{W};border:1px solid {B};
            selection-background-color:{A};outline:0;}}
        QComboBox QAbstractItemView::item{{color:{T};padding:8px 12px;min-height:28px;background:{W};}}
        QComboBox QAbstractItemView::item:hover{{background:{A};color:{T};}}
    """)
    return c


class SmartFarmingPage(QWidget):
    def __init__(self):
        super().__init__()
        self.setStyleSheet(f"background:{P};")
        self._farms = []
        self._workers = []
        self._data = None
        self._build()
        self._load_farms()
        LM.language_changed.connect(self._retranslate)

    # ── Build layout ──────────────────────────────────────────────────────────

    def _build(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea{border:none;background:transparent;}")
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        c = QWidget(); c.setStyleSheet(f"background:{P};")
        ml = QVBoxLayout(c); ml.setContentsMargins(0, 0, 8, 0); ml.setSpacing(16)

        # Row 1 — Header + selectors
        hf, hl = card()
        top_row = QHBoxLayout(); top_row.setSpacing(10)
        self.title_lbl = lbl(LM.tr("smart_title"), 15, T, True)
        top_row.addWidget(self.title_lbl)
        top_row.addStretch()
        self.farm_combo = _combo()
        self.farm_combo.setFixedWidth(200)
        self.farm_combo.currentIndexChanged.connect(self._on_farm_changed)
        self.field_combo = _combo()
        self.field_combo.setFixedWidth(220)
        self.refresh_btn = QPushButton("🔄")
        self.refresh_btn.setFixedSize(38, 38)
        self.refresh_btn.setStyleSheet(
            "QPushButton{background:#374151;color:white;border:none;border-radius:9px;font-size:14px;}"
            "QPushButton:hover{background:#1f2937;}"
            "QPushButton:disabled{background:#9ca3af;}")
        self.refresh_btn.clicked.connect(self._fetch)
        top_row.addWidget(lbl("Farm:", 12, M))
        top_row.addWidget(self.farm_combo)
        top_row.addWidget(lbl("Field:", 12, M))
        top_row.addWidget(self.field_combo)
        top_row.addWidget(self.refresh_btn)
        hl.addLayout(top_row)

        self.status_lbl = lbl("", 12, M)
        self.status_lbl.hide()
        hl.addWidget(self.status_lbl)
        ml.addWidget(hf)

        # Row 2 — Alerts
        self.alerts_frame, self.alerts_layout = card()
        self.alerts_title_lbl = lbl(LM.tr("alerts_title"), 13, T, True)
        self.alerts_layout.addWidget(self.alerts_title_lbl)
        self.alerts_row = QHBoxLayout(); self.alerts_row.setSpacing(10)
        self.alerts_layout.addLayout(self.alerts_row)
        ml.addWidget(self.alerts_frame)

        # Row 3 — 7-Day Forecast
        self.forecast_frame, self.forecast_layout = card()
        self.forecast_title_lbl = lbl(LM.tr("forecast_title"), 13, T, True)
        self.forecast_layout.addWidget(self.forecast_title_lbl)
        self.forecast_row = QHBoxLayout(); self.forecast_row.setSpacing(8)
        self.forecast_layout.addLayout(self.forecast_row)
        ml.addWidget(self.forecast_frame)

        # Row 4 — Planting rec + ML summary (side by side)
        rec_row = QHBoxLayout(); rec_row.setSpacing(12)
        self.planting_frame, self.planting_layout = card()
        self.planting_title_lbl = lbl(LM.tr("planting_rec_title"), 13, T, True)
        self.planting_layout.addWidget(self.planting_title_lbl)
        self.planting_body = QVBoxLayout()
        self.planting_layout.addLayout(self.planting_body)
        rec_row.addWidget(self.planting_frame, 1)

        self.ml_frame, self.ml_layout = card()
        self.ml_title_lbl = lbl(LM.tr("ml_summary_title"), 13, T, True)
        self.ml_layout.addWidget(self.ml_title_lbl)
        self.ml_body = QVBoxLayout()
        self.ml_layout.addLayout(self.ml_body)
        rec_row.addWidget(self.ml_frame, 1)
        ml.addLayout(rec_row)

        # Row 5 — Weekly summary
        self.weekly_frame, self.weekly_layout = card()
        self.weekly_title_lbl = lbl(LM.tr("weekly_summary"), 13, T, True)
        self.weekly_layout.addWidget(self.weekly_title_lbl)
        self.weekly_row = QHBoxLayout(); self.weekly_row.setSpacing(10)
        self.weekly_layout.addLayout(self.weekly_row)
        ml.addWidget(self.weekly_frame)

        ml.addStretch()
        scroll.setWidget(c)
        ol = QVBoxLayout(self); ol.setContentsMargins(0, 0, 0, 0)
        ol.addWidget(scroll)

        # Start with sections hidden
        self.alerts_frame.hide()
        self.forecast_frame.hide()
        self.planting_frame.hide()
        self.ml_frame.hide()
        self.weekly_frame.hide()

    # ── Data loading ──────────────────────────────────────────────────────────

    def _load_farms(self):
        w = Worker(api.get_farms)
        self._workers.append(w)
        w.done.connect(self._on_farms_loaded)
        w.err.connect(lambda e: None)
        w.finished.connect(lambda: self._workers.remove(w) if w in self._workers else None)
        w.start()

    def _on_farms_loaded(self, farms):
        self._farms = farms
        self.farm_combo.blockSignals(True)
        self.farm_combo.clear()
        self.farm_combo.addItem("— Select Farm —", None)
        for f in farms:
            self.farm_combo.addItem(f["name"], f["id"])
        self.farm_combo.blockSignals(False)

    def _on_farm_changed(self, idx):
        farm_id = self.farm_combo.currentData()
        self.field_combo.clear()
        self.field_combo.addItem("— Select Field —", None)
        if not farm_id:
            return
        w = Worker(api.get_fields, farm_id)
        self._workers.append(w)
        w.done.connect(self._on_fields_loaded)
        w.err.connect(lambda e: None)
        w.finished.connect(lambda: self._workers.remove(w) if w in self._workers else None)
        w.start()

    def _on_fields_loaded(self, fields):
        for f in fields:
            self.field_combo.addItem(f"{f['name']} ({f.get('crop_type','')})", f["id"])

    def _fetch(self):
        field_id = self.field_combo.currentData()
        if not field_id:
            self._show_status(LM.tr("select_farm_first"))
            return
        self.refresh_btn.setEnabled(False)
        self._show_status(LM.tr("loading_smart"))
        w = Worker(api.get_smart_farming, field_id)
        self._workers.append(w)
        w.done.connect(self._on_data)
        w.err.connect(self._on_err)
        w.finished.connect(lambda: self._workers.remove(w) if w in self._workers else None)
        w.start()

    def _on_data(self, d):
        self._data = d
        self.refresh_btn.setEnabled(True)
        self.status_lbl.hide()
        self._render(d)

    def _on_err(self, msg):
        self.refresh_btn.setEnabled(True)
        self._show_status(f"⚠  {msg}", RED)

    def _show_status(self, text, color=M):
        self.status_lbl.setText(text)
        self.status_lbl.setStyleSheet(
            f"color:{color};font-size:12px;background:transparent;font-family:'Segoe UI';")
        self.status_lbl.show()

    # ── Rendering ─────────────────────────────────────────────────────────────

    def _clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                self._clear_layout(item.layout())

    def _render(self, d):
        self._render_alerts(d.get("alerts", []))
        self._render_forecast(d.get("forecast", []))
        self._render_planting(d.get("planting_recommendation", {}))
        self._render_ml(d.get("ml_summary"))
        self._render_weekly(d.get("weekly_summary", {}))

        self.alerts_frame.show()
        self.forecast_frame.show()
        self.planting_frame.show()
        self.ml_frame.show()
        self.weekly_frame.show()

    def _render_alerts(self, alerts):
        self._clear_layout(self.alerts_row)
        if not alerts:
            f = QFrame()
            f.setStyleSheet(f"QFrame{{background:#f0fdf4;border:1px solid #bbf7d0;border-radius:10px;}}")
            fl = QVBoxLayout(f); fl.setContentsMargins(16, 12, 16, 12)
            fl.addWidget(lbl(LM.tr("no_alerts"), 13, EMERALD, True))
            self.alerts_row.addWidget(f)
            self.alerts_row.addStretch()
            return

        for alert in alerts:
            color = SEVERITY_COLOR.get(alert["severity"], M)
            f = QFrame()
            f.setFixedWidth(220)
            f.setStyleSheet(
                f"QFrame{{background:{color}18;border:1.5px solid {color}55;border-radius:10px;}}")
            fl = QVBoxLayout(f); fl.setContentsMargins(14, 12, 14, 12); fl.setSpacing(4)
            fl.addWidget(lbl(alert["title"], 12, color, True))
            fl.addWidget(lbl(alert["message"], 11, T, wrap=True))
            action_lbl = lbl(f"→ {alert['action']}", 10, M, wrap=True)
            fl.addWidget(action_lbl)
            self.alerts_row.addWidget(f)
        self.alerts_row.addStretch()

    def _render_forecast(self, forecast):
        self._clear_layout(self.forecast_row)
        for day in forecast:
            emoji = CONDITION_EMOJI.get(day["condition"], "🌤️")
            f = QFrame()
            f.setFixedWidth(110)
            f.setStyleSheet(f"QFrame{{background:{W};border:1px solid {B};border-radius:10px;}}")
            fl = QVBoxLayout(f); fl.setContentsMargins(10, 10, 10, 10); fl.setSpacing(3)
            fl.setAlignment(Qt.AlignmentFlag.AlignHCenter)
            fl.addWidget(lbl(day["day_name"][:3], 10, M, True))
            em = QLabel(emoji)
            em.setAlignment(Qt.AlignmentFlag.AlignCenter)
            em.setStyleSheet("font-size:20px;background:transparent;")
            fl.addWidget(em)
            fl.addWidget(lbl(f"{day['temp_max']:.0f}°/{day['temp_min']:.0f}°", 12, T, True))
            fl.addWidget(lbl(f"💧 {day['rain_probability']:.0f}%", 10, BLUE))
            fl.addWidget(lbl(f"💦 {day['humidity']:.0f}%", 10, M))
            fl.addWidget(lbl(f"💨 {day['wind_kmh']:.0f}", 10, M))
            self.forecast_row.addWidget(f)
        self.forecast_row.addStretch()

    def _render_planting(self, rec):
        self._clear_layout(self.planting_body)
        if not rec:
            self.planting_body.addWidget(lbl("—", 13, M))
            return

        risk_colors = {"low": EMERALD, "medium": GOLD, "high": RED}
        rc = risk_colors.get(rec.get("risk_level", "low"), M)

        # Ideal date
        idate = rec.get("ideal_date")
        date_text = idate if idate else LM.tr("not_favorable")
        row = QHBoxLayout()
        row.addWidget(lbl(LM.tr("ideal_date") + ":", 12, M))
        row.addWidget(lbl(date_text, 12, G if idate else RED, True))
        row.addStretch()
        self.planting_body.addLayout(row)

        # Risk level badge
        row2 = QHBoxLayout()
        row2.addWidget(lbl(LM.tr("risk_level") + ":", 12, M))
        badge = QLabel(f" {rec.get('risk_level','—').upper()} ")
        badge.setStyleSheet(
            f"background:{rc}22;color:{rc};font-size:10px;font-weight:700;"
            "border-radius:4px;padding:2px 6px;font-family:'Segoe UI';")
        row2.addWidget(badge)
        row2.addStretch()
        self.planting_body.addLayout(row2)

        # Water requirement
        row3 = QHBoxLayout()
        row3.addWidget(lbl(LM.tr("water_req") + ":", 12, M))
        row3.addWidget(lbl(f"{rec.get('water_requirement_mm', 0):.0f} mm", 12, BLUE, True))
        row3.addStretch()
        self.planting_body.addLayout(row3)

        # Suitability score bar
        score = rec.get("suitability_score", 0)
        row4 = QHBoxLayout()
        row4.addWidget(lbl(LM.tr("suitability") + ":", 12, M))
        bar = QProgressBar()
        bar.setFixedHeight(10)
        bar.setRange(0, 100)
        bar.setValue(int(score * 100))
        bar_color = EMERALD if score >= 0.7 else (GOLD if score >= 0.4 else RED)
        bar.setStyleSheet(f"""
            QProgressBar{{border:1px solid {B};border-radius:5px;background:#f1f5f1;text-align:center;}}
            QProgressBar::chunk{{background:{bar_color};border-radius:4px;}}
        """)
        bar.setTextVisible(False)
        row4.addWidget(bar, 1)
        row4.addWidget(lbl(f"{score:.0%}", 11, bar_color, True))
        self.planting_body.addLayout(row4)

        # Reasons
        for reason in rec.get("reasons", []):
            self.planting_body.addWidget(lbl(f"• {reason}", 11, M, wrap=True))

    def _render_ml(self, ml):
        self._clear_layout(self.ml_body)
        if not ml:
            self.ml_body.addWidget(lbl(LM.tr("ml_unavailable"), 11, M, wrap=True))
            return

        health_colors = {"Healthy": EMERALD, "Stressed": GOLD, "Diseased": RED}
        hc = health_colors.get(ml.get("crop_health", ""), M)

        rows = [
            (LM.tr("crop_health_lbl"), ml.get("crop_health", "—"), hc),
            (LM.tr("irrigation_lbl"),
             ml.get("irrigation", "—").replace("_", " ").title(), BLUE),
            (LM.tr("yield_lbl"),
             f"{ml.get('predicted_yield_tha', 0):.2f} t/ha", "#7c3aed"),
        ]
        for label, value, color in rows:
            row = QHBoxLayout()
            row.addWidget(lbl(label + ":", 12, M))
            row.addWidget(lbl(value, 12, color, True))
            row.addStretch()
            self.ml_body.addLayout(row)

    def _render_weekly(self, ws):
        self._clear_layout(self.weekly_row)
        stats = [
            (LM.tr("avg_temp"),    f"{ws.get('avg_temp', 0):.1f}°C",      G),
            (LM.tr("total_rain"),  f"{ws.get('total_rain_mm', 0):.1f} mm", BLUE),
            (LM.tr("avg_humidity"),f"{ws.get('avg_humidity', 0):.0f}%",    "#0891b2"),
            (LM.tr("avg_wind"),    f"{ws.get('avg_wind_kmh', 0):.0f} km/h","#374151"),
        ]
        for label, value, color in stats:
            f = QFrame()
            f.setStyleSheet(f"QFrame{{background:{A};border:1px solid #b8d8c4;border-radius:10px;}}")
            fl = QVBoxLayout(f); fl.setContentsMargins(16, 12, 16, 12); fl.setSpacing(4)
            fl.addWidget(lbl(label, 10, M))
            fl.addWidget(lbl(value, 20, color, True))
            self.weekly_row.addWidget(f, 1)

    # ── i18n retranslate ──────────────────────────────────────────────────────

    def _retranslate(self):
        self.title_lbl.setText(LM.tr("smart_title"))
        self.alerts_title_lbl.setText(LM.tr("alerts_title"))
        self.forecast_title_lbl.setText(LM.tr("forecast_title"))
        self.planting_title_lbl.setText(LM.tr("planting_rec_title"))
        self.ml_title_lbl.setText(LM.tr("ml_summary_title"))
        self.weekly_title_lbl.setText(LM.tr("weekly_summary"))
        if self._data:
            self._render(self._data)
```

- [ ] **Step 4.2: Verify the module imports cleanly**

```bash
cd /home/ali/Agrosense/agrosense && conda run -n agrosense python -c "from desktop.pages.smart_farming import SmartFarmingPage; print('OK')"
```

Expected: `OK`

- [ ] **Step 4.3: Commit**

```bash
git add desktop/pages/smart_farming.py
git commit -m "feat: add SmartFarmingPage with forecast, alerts, planting rec, and ML summary"
```

---

## Task 5: Wire SmartFarmingPage into the main window NAV

**Files:**
- Modify: `desktop/windows/main_window.py`

- [ ] **Step 5.1: Add import and NAV entry**

In `desktop/windows/main_window.py`, add the import after the existing page imports:

```python
from desktop.pages.smart_farming import SmartFarmingPage
```

And extend the `NAV` list with one new entry at the end:

```python
NAV = [
    ("dashboard", "nav_dashboard", "topbar_sub_dashboard", DashboardPage),
    ("farms",     "nav_farms",     "topbar_sub_farms",     FarmsPage),
    ("imagery",   "nav_imagery",   "topbar_sub_imagery",   ImageryPage),
    ("analytics", "nav_analytics", "topbar_sub_analytics", AnalyticsPage),
    ("map",       "nav_map",       "topbar_sub_map",       MapPage),
    ("bands",     "nav_bands",     "topbar_sub_bands",     BandViewPage),
    ("smart",     "nav_smart",     "topbar_sub_smart",     SmartFarmingPage),
]
```

- [ ] **Step 5.2: Verify the desktop app launches without error**

```bash
cd /home/ali/Agrosense/agrosense && conda run -n agrosense python -c "
import sys
from PyQt6.QtWidgets import QApplication
app = QApplication(sys.argv)
from desktop.windows.main_window import MainWindow, NAV
print('NAV entries:', [n[0] for n in NAV])
print('smart in NAV:', any(n[0] == 'smart' for n in NAV))
"
```

Expected:
```
NAV entries: ['dashboard', 'farms', 'imagery', 'analytics', 'map', 'bands', 'smart']
smart in NAV: True
```

- [ ] **Step 5.3: Run the app and test the Smart Farming page end-to-end**

```bash
cd /home/ali/Agrosense/agrosense && conda run -n agrosense python -m desktop.main &
```

Manual test steps:
1. Log in.
2. Click "🌱  Smart Farming" in the sidebar.
3. Select a farm with GPS coordinates set.
4. Select a field.
5. Click 🔄 — verify the page loads weather data with forecast cards, alerts section, and weekly summary.
6. If ML shows "ML analysis unavailable", that is correct when the field has no satellite analysis yet.
7. Toggle language — verify Urdu labels appear.

- [ ] **Step 5.4: Commit**

```bash
git add desktop/windows/main_window.py
git commit -m "feat: wire SmartFarmingPage into sidebar navigation"
```

---

## Self-review

### Spec coverage
- ✅ 7-day weather forecast per farm location (Task 1 `_fetch_forecast`)
- ✅ 7 alert types with severity and action text (Task 1 `_apply_rules`)
- ✅ Planting recommendation with suitability score (Task 1 `_planting_recommendation`)
- ✅ ML summary (crop health, irrigation, yield) with graceful fallback (Task 1 endpoint)
- ✅ Weekly aggregate summary (Task 1 endpoint)
- ✅ Farm + field combo selectors on page (Task 4)
- ✅ Alert cards with severity colour coding (Task 4 `_render_alerts`)
- ✅ 7 day forecast cards with emoji, temp, rain %, humidity, wind (Task 4 `_render_forecast`)
- ✅ Planting rec card with ideal date, risk badge, water req, suitability bar, reasons (Task 4 `_render_planting`)
- ✅ ML summary card (Task 4 `_render_ml`)
- ✅ Weekly summary stat badges (Task 4 `_render_weekly`)
- ✅ Worker thread for async API call (Task 4)
- ✅ Loading state + error label (Task 4 `_fetch`, `_on_err`)
- ✅ i18n retranslate on language change (Task 4 `_retranslate`)
- ✅ Router registered at `/weather` prefix (Task 2)
- ✅ 30 translation keys in both EN and UR (Task 3)
- ✅ Error responses: 404 field not found, 422 no coordinates, 503 Open-Meteo down (Task 1 endpoint)
- ✅ ML failure returns `ml_summary: null` gracefully (Task 1 endpoint)

### Type consistency
- `_apply_rules` returns `list[dict]` with keys: `type, severity, title, message, action, days_until` — consistent across all 7 rule branches and the desktop `_render_alerts` consumer.
- `_planting_recommendation` returns `dict` with keys: `ideal_date, risk_level, water_requirement_mm, suitability_score, reasons` — matches the desktop `_render_planting` consumer.
- `_fetch_forecast` returns `list[dict]` with keys: `date, day_name, temp_max, temp_min, temp_avg, rain_mm, rain_probability, humidity, wind_kmh, condition` — consumed by `_apply_rules` and `_render_forecast` with identical key names.
