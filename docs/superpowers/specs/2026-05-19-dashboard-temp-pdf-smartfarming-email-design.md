# Design: Dashboard Temperature, Smart Farming PDF, Email Alert Fix

**Date:** 2026-05-19
**Scope:** Three independent improvements to the AgroSense desktop app

---

## 1. Current Temperature Stat Card on Dashboard

### Goal
Show the current temperature of the selected field's location as a 5th stat card at the top of the Dashboard, alongside Farms / Fields / Health / Yield.

### Backend — `app/routers/weather.py`

New endpoint:
```
GET /weather/current/{field_id}
```

- Loads field → farm → lat/lon. Returns 404 if field not found, 422 if farm has no coordinates.
- Calls Open-Meteo:
  ```
  https://api.open-meteo.com/v1/forecast
    ?latitude=<lat>&longitude=<lon>
    &current=temperature_2m,apparent_temperature,weathercode
    &timezone=auto
  ```
- Returns:
  ```json
  { "temperature_c": 34.1, "feels_like_c": 36.2, "condition": "clear" }
  ```
- Condition string mapped via existing `_wmo_to_condition()`.
- No 7-day forecast, no ML — fast single call.

### Desktop — `desktop/api.py`

New function:
```python
def get_current_weather(field_id):
    return _get(f"/weather/current/{field_id}")
```

### Desktop — `desktop/pages/dashboard.py`

- Add a 5th stat card with i18n key `"stat_temp"`, colour `RED = "#dc2626"`.
- Default value `"—"`.
- Connect `self.combo.currentIndexChanged` signal to `_fetch_temp()`.
- `_fetch_temp()`:
  - Reads `self.combo.currentData()` for the field_id.
  - If empty, resets stat card to `"—"`.
  - Otherwise starts a Worker for `api.get_current_weather(field_id)`.
  - On success: sets stat card to `f"{result['temperature_c']:.0f} °C"`.
  - On error: sets stat card to `"—"` (silent fail — temperature is decorative).
- Also call `_fetch_temp()` inside `_on_loaded()` after populating the combo, so temperature loads on startup.

### i18n — `desktop/i18n.py`

Add key `stat_temp`:
- EN: `"Temperature"`
- UR: `"درجہ حرارت"`

---

## 2. Smart Farming Section in PDF Export

### Goal
The PDF export (triggered from Dashboard) automatically fetches the Smart Farming weather data for the selected field and appends a new section to the report.

### `desktop/pages/dashboard.py` — `PDFWorker.run()`

Before calling `generate_report`, fetch smart farming data:

```python
import requests as _req
sf_data = None
fid = self.data.get("field_id")
tok = self.data.get("_token")
if fid and tok:
    try:
        r = _req.get(
            f"http://localhost:8000/weather/smart-farming/{fid}",
            headers={"Authorization": f"Bearer {tok}"},
            timeout=15,
        )
        if r.status_code == 200:
            sf_data = r.json()
    except Exception:
        pass  # section omitted if fetch fails
generate_report(..., smart_farming_data=sf_data)
```

### `desktop/utils/pdf_export.py` — `generate_report()`

New parameter: `smart_farming_data=None`.

If `smart_farming_data` is not None, insert a new page section **after Section 6 (VRA) and before Section 7 (Band Composites)**:

**Section 8 — Smart Farming Recommendations**

Sub-sections:

1. **Alerts table** (skipped if `alerts` list is empty)
   - Columns: Type | Severity | Title | Recommended Action
   - Row background colour matches severity: red/amber/green tint

2. **Planting Recommendation** — key/value table:
   - Suitability Score (0–1, shown as percentage)
   - Risk Level (low / medium / high)
   - Ideal Planting Date
   - Water Requirement (mm)

3. **Weekly Weather Summary** — 4-column dark banner (matches existing summary banner style):
   - Avg Temp | Total Rain | Avg Humidity | Avg Wind

**Urdu translations** added to `_UR` dict for all new keys:
- `sec8`: `"اسمارٹ فارمنگ سفارشات"`
- `alerts_heading`: `"موسمی انتباہات"`
- `planting_rec`: `"کاشت کاری کی سفارش"`
- `weekly_weather`: `"ہفتہ وار موسمی خلاصہ"`
- `suitability`: `"مناسبیت"`
- `risk_level`: `"خطرے کی سطح"`
- `ideal_date`: `"بہترین تاریخ"`
- `water_req`: `"پانی کی ضرورت"`
- `no_alerts`: `"کوئی موسمی انتباہ نہیں"`

If `smart_farming_data` is `None`, the section is silently omitted — no crash, no placeholder.

---

## 3. Email Alert for All Crop Statuses

### Root Cause
`check_and_alert()` only called `send_crop_alert()` when prediction was `"Stressed"` or `"Diseased"`. The `send_crop_alert()` function also had an early return for `"Healthy"`. Result: users with healthy crops could never receive any email.

### Fix — `desktop/utils/email_alerts.py`

**`send_crop_alert()`:**
- Remove the `if pred == "Healthy": return ...` early return.
- Extend `color_map` to include Healthy: `"Healthy": "#1a6b35"`.
- Subject line:
  - Healthy → `"✅ AgroSense Report: {field} crop is Healthy"`
  - Stressed/Diseased → `"🚨 AgroSense Alert: {pred} crop detected in {field}"` (existing)
- Alert banner text:
  - Healthy → `"CROP STATUS: HEALTHY — No immediate action required"`
  - Others → existing `"IMMEDIATE ATTENTION REQUIRED"`

**`check_and_alert()`:**
- Remove the `if pred in ("Stressed", "Diseased")` guard.
- Always call `send_crop_alert()` regardless of status.

---

## Out of scope

- No changes to the Smart Farming page UI itself.
- No changes to the existing 7-day forecast logic.
- No changes to the PDF band composites section.
- No new tests required for the temperature endpoint beyond what already exists in `tests/test_weather.py` (pattern is identical to existing endpoint tests).

---

## Files changed

| File | Change |
|------|--------|
| `app/routers/weather.py` | Add `GET /weather/current/{field_id}` endpoint |
| `desktop/api.py` | Add `get_current_weather(field_id)` |
| `desktop/pages/dashboard.py` | 5th stat card + combo signal + PDFWorker smart farming fetch |
| `desktop/utils/pdf_export.py` | Add `smart_farming_data` param + Section 8 |
| `desktop/utils/email_alerts.py` | Remove Healthy block, update subject/banner |
| `desktop/i18n.py` | Add `stat_temp` key (EN + UR) |
