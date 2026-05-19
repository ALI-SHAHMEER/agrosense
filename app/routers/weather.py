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
from app.ml.predictor import predict_crop_stress, predict_irrigation, predict_yield
from app.models import Farm, Field, SatelliteImage, User, VegetationIndex
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


# ── Current weather fetch ─────────────────────────────────────────────────────

def _parse_current_response(data: dict) -> dict:
    cur = data.get("current", {})
    return {
        "temperature_c": cur.get("temperature_2m") or 0.0,
        "feels_like_c":  cur.get("apparent_temperature") or 0.0,
        "condition":     _wmo_to_condition(cur.get("weathercode") or 0),
    }


def _fetch_current(lat: float, lon: float) -> dict:
    resp = _requests.get(
        "https://api.open-meteo.com/v1/forecast",
        params={
            "latitude":  lat,
            "longitude": lon,
            "current":   ["temperature_2m", "apparent_temperature", "weathercode"],
            "timezone":  "auto",
        },
        timeout=10,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"Open-Meteo returned {resp.status_code}")
    return _parse_current_response(resp.json())


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
            "temp_max": daily["temperature_2m_max"][i] or 0,
            "temp_min": daily["temperature_2m_min"][i] or 0,
            "temp_avg": daily["temperature_2m_mean"][i] or 0,
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
    current_user: User = Depends(get_current_user),
):
    """Return 7-day forecast, alerts, planting recommendation, and ML summary."""

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


@router.get("/current/{field_id}")
def current_weather(
    field_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return current temperature and condition for the field's farm location."""
    field = (
        db.query(Field)
        .join(Farm)
        .filter(Field.id == field_id, Farm.user_id == current_user.id)
        .first()
    )
    if not field:
        raise HTTPException(status_code=404, detail="Field not found")
    farm = field.farm
    if farm.latitude is None or farm.longitude is None:
        raise HTTPException(status_code=422, detail="Farm location not set")
    try:
        return _fetch_current(farm.latitude, farm.longitude)
    except Exception as exc:
        log.warning("Open-Meteo current fetch failed: %s", exc)
        raise HTTPException(status_code=503, detail="Weather service unavailable")
