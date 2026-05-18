# Smart Farming Recommendations — Design Spec

**Date:** 2026-05-18  
**Project:** AgroSense Desktop  
**Status:** Approved

---

## Goal

Add a Smart Farming page to the AgroSense desktop app that gives farmers a 7-day weather forecast for their field's location, automated crop protection alerts, and AI-powered planting recommendations — all in one screen.

## Architecture

**Approach:** Backend router handles all logic. Desktop page is display-only.

**New files:**
- `app/routers/weather.py` — FastAPI router: fetches Open-Meteo, runs rule engine, calls existing ML models, returns unified JSON
- `desktop/pages/smart_farming.py` — PyQt6 page: fetches one endpoint, renders result

**Modified files:**
- `app/main.py` — register `weather` router with prefix `/weather`
- `desktop/api.py` — add `get_smart_farming(field_id)` function
- `desktop/windows/main_window.py` — add `("smart", "nav_smart", "topbar_sub_smart", SmartFarmingPage)` to NAV
- `desktop/i18n.py` — add ~30 new EN/UR translation keys

**Data flow:**
1. User selects farm then field from combo boxes on the Smart Farming page
2. Desktop calls `GET /weather/smart-farming/{field_id}`
3. Backend fetches field → farm from DB, extracts lat/lon
4. Backend calls Open-Meteo `https://api.open-meteo.com/v1/forecast` with farm coordinates
5. Backend rule engine scans 7-day forecast → produces alerts list
6. Backend calls existing ML endpoints (crop_stress, irrigation, yield) using forecast avg weather
7. Backend assembles and returns unified JSON response
8. Desktop Worker thread receives response, renders all UI sections

---

## Backend: `app/routers/weather.py`

### Endpoint

```
GET /weather/smart-farming/{field_id}
Authorization: Bearer <token>
```

### Open-Meteo parameters

```
latitude, longitude
daily: temperature_2m_max, temperature_2m_min, temperature_2m_mean,
       precipitation_sum, precipitation_probability_max,
       windspeed_10m_max, relative_humidity_2m_mean,
       weathercode
forecast_days: 7
timezone: auto
```

### Response schema

```json
{
  "field_name": "string",
  "crop_type": "string",
  "location": { "lat": 30.1, "lon": 71.5 },
  "forecast": [
    {
      "date": "2026-05-18",
      "day_name": "Monday",
      "temp_max": 38,
      "temp_min": 22,
      "temp_avg": 30,
      "rain_mm": 5.2,
      "rain_probability": 65,
      "humidity": 72,
      "wind_kmh": 18,
      "condition": "partly_cloudy"
    }
  ],
  "alerts": [
    {
      "type": "heatwave",
      "severity": "high",
      "title": "Heatwave Warning",
      "message": "Temperature exceeding 38°C for 3 consecutive days",
      "action": "Increase irrigation frequency",
      "days_until": 1
    }
  ],
  "planting_recommendation": {
    "ideal_date": "2026-05-25",
    "risk_level": "low",
    "water_requirement_mm": 22,
    "suitability_score": 0.85,
    "reasons": ["Moderate temperature", "Good soil moisture forecast"]
  },
  "ml_summary": {
    "crop_health": "Healthy",
    "irrigation": "moderate_irrigation",
    "predicted_yield_tha": 3.42
  },
  "weekly_summary": {
    "avg_temp": 31.2,
    "total_rain_mm": 18.5,
    "avg_humidity": 68,
    "avg_wind_kmh": 15
  }
}
```

### Weather condition mapping (WMO weathercode → string)

| Codes | condition string |
|-------|-----------------|
| 0 | clear |
| 1–3 | partly_cloudy |
| 45, 48 | foggy |
| 51–67 | drizzle |
| 71–77 | snow |
| 80–82 | rain_showers |
| 95–99 | thunderstorm |

### Rule engine — alert triggers

| Alert type | Trigger condition | Severity |
|-----------|-------------------|----------|
| `heatwave` | temp_max > 38°C for 2+ consecutive days | high |
| `heavy_rain` | daily rain_mm > 25 | high |
| `frost` | temp_min < 4°C on any day | high |
| `drought` | total 7-day rain_mm < 5 AND avg temp_avg > 30°C | medium |
| `strong_wind` | wind_kmh > 40 on any day | medium |
| `spray_delay` | rain_probability > 60% on day 0 or day 1 | low |
| `fungal_risk` | humidity > 85 for 3+ consecutive days | low |

### Planting recommendation logic

```
temp_score     = 1.0 if 20 ≤ avg_temp ≤ 30, else max(0, 1 - abs(avg_temp - 25) / 15)
moisture_score = irrigation_confidence from ML model (0.0–1.0)
risk_score     = 1.0 - (high_alerts * 0.4 + medium_alerts * 0.2 + low_alerts * 0.1)
suitability    = (temp_score * 0.4) + (moisture_score * 0.4) + (risk_score * 0.2)

ideal_date     = first forecast day where suitability > 0.7, else None
risk_level     = "high" if any high alert, "medium" if any medium alert, else "low"
water_req      = water_amount_mm from ML irrigation model
reasons        = up to 3 human-readable strings explaining the score
```

### ML model calls inside the endpoint

The endpoint reuses the existing internal ML predictor (not HTTP calls — direct Python import of `app.ml.predictor`):
- `predict_crop_stress(field_id, weather)` using forecast avg temp + rain
- `predict_irrigation(field_id, weather)` — provides moisture_score and water_req
- `predict_yield(field_id, weather)` — provides predicted_yield_tha

If any ML call fails, `ml_summary` returns null values gracefully — the weather + alerts sections still render.

---

## Desktop: `desktop/pages/smart_farming.py`

### Page structure (inside QScrollArea)

**Row 1 — Header + selectors**
- Title label: `LM.tr("smart_title")`
- Farm QComboBox (`self.farm_combo`)
- Field QComboBox (`self.field_combo`, populated on farm selection)
- Refresh QPushButton 🔄

**Row 2 — Alerts section**
- Section heading: `LM.tr("alerts_title")`
- Horizontal QHBoxLayout of alert QFrame cards (one per alert)
- Each card: severity colour background, type icon, title, message, action text
- If no alerts: single green card "No weather risks detected this week"
- Severity colours: high=`#dc2626`, medium=`#d4a017`, low=`#22c55e`

**Row 3 — 7-Day Forecast**
- Section heading: `LM.tr("forecast_title")`
- Horizontal QHBoxLayout of 7 day QFrame cards
- Each card: day name, condition emoji, temp_max/temp_min, rain %, humidity, wind

**Row 4 — Recommendations (side by side)**
- Left card: Planting Recommendation
  - Ideal date, risk level badge, water requirement, suitability score bar, bullet reasons
- Right card: ML Summary
  - Crop health (coloured), irrigation recommendation, predicted yield

**Row 5 — Weekly Summary**
- 4 stat badge QFrames: Avg Temp, Total Rain, Avg Humidity, Avg Wind

### Threading

Uses the existing `Worker(QThread)` pattern from `dashboard.py`:
```python
w = Worker(api.get_smart_farming, field_id)
w.done.connect(self._on_data)
w.err.connect(self._on_err)
```

Loading state: disable refresh button + show "Loading…" label. On error: show red error label.

### i18n keys to add to `desktop/i18n.py`

```python
"nav_smart":          {"en": "🌱 Smart Farming",   "ur": "🌱 ذہین زراعت"},
"topbar_sub_smart":   {"en": "Weather & Recommendations", "ur": "موسم اور سفارشات"},
"smart_title":        {"en": "Smart Farming Recommendations", "ur": "ذہین زراعت سفارشات"},
"select_farm_first":  {"en": "Select a farm to continue", "ur": "جاری رکھنے کے لیے فارم منتخب کریں"},
"loading_smart":      {"en": "Fetching weather data…", "ur": "موسمی ڈیٹا حاصل ہو رہا ہے…"},
"alerts_title":       {"en": "⚠  Crop Protection Alerts", "ur": "⚠  فصل حفاظت الرٹس"},
"no_alerts":          {"en": "✅  No weather risks detected this week", "ur": "✅  اس ہفتے کوئی موسمی خطرہ نہیں"},
"forecast_title":     {"en": "📅  7-Day Weather Forecast", "ur": "📅  7 روزہ موسمی پیش گوئی"},
"planting_rec_title": {"en": "🌾  Planting Recommendation", "ur": "🌾  بوائی کی سفارش"},
"ml_summary_title":   {"en": "🤖  ML Analysis Summary", "ur": "🤖  ML تجزیہ خلاصہ"},
"weekly_summary":     {"en": "📊  Weekly Summary", "ur": "📊  ہفتہ وار خلاصہ"},
"ideal_date":         {"en": "Ideal Planting Date", "ur": "بہترین بوائی تاریخ"},
"not_favorable":      {"en": "Not favorable this week", "ur": "اس ہفتے موزوں نہیں"},
"risk_level":         {"en": "Risk Level", "ur": "خطرے کی سطح"},
"water_req":          {"en": "Water Requirement", "ur": "پانی کی ضرورت"},
"suitability":        {"en": "Suitability Score", "ur": "موزونیت اسکور"},
"avg_temp":           {"en": "Avg Temp", "ur": "اوسط درجہ حرارت"},
"total_rain":         {"en": "Total Rain", "ur": "کل بارش"},
"avg_humidity":       {"en": "Avg Humidity", "ur": "اوسط نمی"},
"avg_wind":           {"en": "Avg Wind", "ur": "اوسط ہوا"},
# Alert type titles
"alert_heatwave":     {"en": "🔥 Heatwave Warning", "ur": "🔥 گرمی کی لہر"},
"alert_heavy_rain":   {"en": "🌧 Heavy Rain Alert", "ur": "🌧 شدید بارش الرٹ"},
"alert_frost":        {"en": "❄ Frost Warning", "ur": "❄ پالہ انتباہ"},
"alert_drought":      {"en": "☀ Drought Risk", "ur": "☀ خشک سالی خطرہ"},
"alert_strong_wind":  {"en": "💨 Strong Wind Alert", "ur": "💨 تیز ہوا الرٹ"},
"alert_spray_delay":  {"en": "🚫 Delay Pesticide Spraying", "ur": "🚫 کیڑے مار دوا دیر سے چھڑکیں"},
"alert_fungal_risk":  {"en": "🍄 Fungal Disease Risk", "ur": "🍄 پھپھوندی بیماری خطرہ"},
```

---

## Error handling

- Open-Meteo unreachable: return HTTP 503 with `{"detail": "Weather service unavailable"}`
- Farm has no coordinates: return HTTP 422 with `{"detail": "Farm location not set"}`
- ML model fails: log warning, return `ml_summary: null` — page shows alerts + forecast without ML section
- Field not found: return HTTP 404

---

## Out of scope

- Historical weather data or charts
- Push notifications / background polling
- Saving/caching forecast results to DB
- Custom alert thresholds per farm
