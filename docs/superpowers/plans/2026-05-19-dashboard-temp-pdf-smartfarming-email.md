# Dashboard Temperature, Smart Farming PDF, Email Alert Fix — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a live temperature stat card to the Dashboard, include a Smart Farming section in PDF exports, and allow email alerts for all crop statuses (not just Stressed/Diseased).

**Architecture:** Three independent changes sharing no state. Backend gains one new endpoint. Desktop gains one API wrapper, one UI element, a PDF section, and an email fix. Each task produces a working, committable unit.

**Tech Stack:** FastAPI, PyQt6, ReportLab, smtplib, Open-Meteo API, pytest

---

## File Map

| File | Change |
|------|--------|
| `app/routers/weather.py` | Add `_parse_current_response()` pure fn + `GET /weather/current/{field_id}` |
| `tests/test_weather.py` | Tests for `_parse_current_response` |
| `desktop/api.py` | Add `get_current_weather(field_id)` |
| `desktop/i18n.py` | Add `stat_temp` key (EN + UR) |
| `desktop/pages/dashboard.py` | 5th stat card, `_fetch_temp()`, combo signal, PDFWorker smart-farming fetch |
| `desktop/utils/pdf_export.py` | `smart_farming_data` param, Section 8 |
| `desktop/utils/email_alerts.py` | Remove Healthy block, update subject + banner |
| `tests/test_email_alerts.py` | New test file for email fix |

---

## Task 1: Backend — `_parse_current_response` + `GET /weather/current/{field_id}`

**Files:**
- Modify: `app/routers/weather.py` (after `_fetch_forecast`, before the smart-farming endpoint)
- Modify: `tests/test_weather.py`

### Step 1.1 — Write the failing tests

Open `tests/test_weather.py`. Add to the top-of-file import:

```python
from app.routers.weather import _wmo_to_condition, _apply_rules, _planting_recommendation, _parse_current_response
```

Append at the bottom of the file:

```python
# ── _parse_current_response ───────────────────────────────────────────────────

def test_parse_current_response_clear_sky():
    data = {"current": {"temperature_2m": 34.1, "apparent_temperature": 36.2, "weathercode": 0}}
    result = _parse_current_response(data)
    assert result["temperature_c"] == 34.1
    assert result["feels_like_c"] == 36.2
    assert result["condition"] == "clear"

def test_parse_current_response_thunderstorm():
    data = {"current": {"temperature_2m": 22.0, "apparent_temperature": 21.0, "weathercode": 95}}
    result = _parse_current_response(data)
    assert result["condition"] == "thunderstorm"

def test_parse_current_response_missing_current_key():
    result = _parse_current_response({})
    assert result["temperature_c"] == 0.0
    assert result["feels_like_c"] == 0.0
    assert result["condition"] == "clear"

def test_parse_current_response_null_values():
    data = {"current": {"temperature_2m": None, "apparent_temperature": None, "weathercode": None}}
    result = _parse_current_response(data)
    assert result["temperature_c"] == 0.0
    assert result["feels_like_c"] == 0.0
    assert result["condition"] == "clear"
```

### Step 1.2 — Run tests to confirm they fail

```bash
conda run -n agrosense pytest tests/test_weather.py -k "parse_current" -v
```

Expected: `ImportError: cannot import name '_parse_current_response'`

### Step 1.3 — Implement `_parse_current_response` and `_fetch_current` in `app/routers/weather.py`

Find the line `# ── Open-Meteo fetch ─────...` (just before `_DAY_NAMES`). Insert the two new functions **before** `_DAY_NAMES`:

```python
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
```

### Step 1.4 — Add the endpoint at the bottom of `app/routers/weather.py`

Append after the existing `smart_farming` endpoint:

```python
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
```

### Step 1.5 — Run tests to confirm they pass

```bash
conda run -n agrosense pytest tests/test_weather.py -k "parse_current" -v
```

Expected: 4 tests PASSED

### Step 1.6 — Run full weather test suite to confirm no regressions

```bash
conda run -n agrosense pytest tests/test_weather.py -v
```

Expected: all 34 + 4 = 38 tests PASSED

### Step 1.7 — Commit

```bash
git add app/routers/weather.py tests/test_weather.py
git commit -m "feat: add GET /weather/current/{field_id} for live temperature"
```

---

## Task 2: Desktop API wrapper + i18n key

**Files:**
- Modify: `desktop/api.py` (after `get_smart_farming` at line 78)
- Modify: `desktop/i18n.py` (after `stat_yield` at line 66)

### Step 2.1 — Add `get_current_weather` to `desktop/api.py`

Find the line `def get_smart_farming(field_id):` and insert after the function body:

```python
def get_current_weather(field_id):
    return _get(f"/weather/current/{field_id}")
```

### Step 2.2 — Add `stat_temp` to `desktop/i18n.py`

Find the line:
```python
    "stat_yield":             {"en": "Est. Yield",                            "ur": "متوقع پیداوار"},
```

Add immediately after it:
```python
    "stat_temp":              {"en": "Temperature",                           "ur": "درجہ حرارت"},
```

### Step 2.3 — Commit

```bash
git add desktop/api.py desktop/i18n.py
git commit -m "feat: add get_current_weather API wrapper and stat_temp i18n key"
```

---

## Task 3: Dashboard — 5th temperature stat card

**Files:**
- Modify: `desktop/pages/dashboard.py`

### Step 3.1 — Add `stat_temp` to `stat_keys` and `stat_cols`

Find in `_build()`:
```python
        stat_keys = ["stat_farms", "stat_fields", "stat_health", "stat_yield"]
        stat_cols = [G, BLUE, EMERALD, GOLD]
```

Replace with:
```python
        stat_keys = ["stat_farms", "stat_fields", "stat_health", "stat_yield", "stat_temp"]
        stat_cols = [G, BLUE, EMERALD, GOLD, RED]
```

### Step 3.2 — Connect `currentIndexChanged` signal in `_build()`

Find the line after `self.combo = QComboBox()` setup (around line 126) where `row.addWidget(self.combo, 1)` is. Add the signal connection just after the combo is created but before it's added to the layout:

```python
        self.combo.currentIndexChanged.connect(self._fetch_temp)
```

Place it immediately after `self.combo.setStyleSheet(...)` and before `row.addWidget(self.combo, 1)`.

### Step 3.3 — Add `_fetch_temp` method

Add the following method to the `DashboardPage` class, after `_on_err`:

```python
    def _fetch_temp(self):
        fid = self.combo.currentData()
        if not fid:
            self._sv[4].setText("—")
            return
        w = Worker(api.get_current_weather, fid)
        self._workers.append(w)
        w.done.connect(lambda r: self._sv[4].setText(f"{r['temperature_c']:.0f} °C"))
        w.err.connect(lambda _: self._sv[4].setText("—"))
        w.finished.connect(lambda: self._workers.remove(w) if w in self._workers else None)
        w.start()
```

### Step 3.4 — Verify the app loads without error

```bash
conda run -n agrosense uvicorn app.main:app --port 8000 &
sleep 2
conda run -n agrosense python desktop/main.py
```

Log in, open Dashboard. Confirm a 5th card labelled "Temperature" appears at top-right. Select a different field in the combo — temperature should update. Kill the server (`kill %1`).

### Step 3.5 — Commit

```bash
git add desktop/pages/dashboard.py
git commit -m "feat: add live temperature stat card to Dashboard"
```

---

## Task 4: PDFWorker — fetch Smart Farming data before export

**Files:**
- Modify: `desktop/pages/dashboard.py` — `PDFWorker.run()` (lines 53–65)

### Step 4.1 — Replace `PDFWorker.run()` body

Find the current `run` method of `PDFWorker`:

```python
    def run(self):
        import traceback, logging
        logging.basicConfig(filename='/tmp/agrosense_pdf.log', level=logging.DEBUG,
                            format='%(asctime)s %(levelname)s %(message)s')
        try:
            logging.info('PDFWorker started, path=%s lang=%s', self.path, self.language)
            from desktop.utils.pdf_export import generate_report
            generate_report(self.data, self.path, include_bands=True, language=self.language)
            logging.info('PDF generated OK')
            self.done.emit(self.path)
        except BaseException as e:
            tb = traceback.format_exc()
            logging.error('PDFWorker failed: %s\n%s', e, tb)
            self.err.emit(f"{e}\n{tb[-500:]}")
```

Replace it entirely with:

```python
    def run(self):
        import traceback, logging, requests as _req
        logging.basicConfig(filename='/tmp/agrosense_pdf.log', level=logging.DEBUG,
                            format='%(asctime)s %(levelname)s %(message)s')
        try:
            logging.info('PDFWorker started, path=%s lang=%s', self.path, self.language)
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
                        logging.info("Smart farming data fetched OK")
                except Exception as sf_exc:
                    logging.warning("Smart farming fetch failed (section omitted): %s", sf_exc)
            from desktop.utils.pdf_export import generate_report
            generate_report(self.data, self.path, include_bands=True,
                            language=self.language, smart_farming_data=sf_data)
            logging.info('PDF generated OK')
            self.done.emit(self.path)
        except BaseException as e:
            tb = traceback.format_exc()
            logging.error('PDFWorker failed: %s\n%s', e, tb)
            self.err.emit(f"{e}\n{tb[-500:]}")
```

### Step 4.2 — Commit

```bash
git add desktop/pages/dashboard.py
git commit -m "feat: fetch smart farming data in PDFWorker before PDF generation"
```

---

## Task 5: PDF export — Section 8 Smart Farming Recommendations

**Files:**
- Modify: `desktop/utils/pdf_export.py`

### Step 5.1 — Add Urdu translations to `_UR` dict

Find the last entry in `_UR` (the `"footer"` key). Add the following entries **before** the closing `}`:

```python
    # smart farming section
    "sec8":           "اسمارٹ فارمنگ سفارشات",
    "sf_alerts":      "موسمی انتباہات",
    "sf_planting":    "کاشت کاری کی سفارش",
    "sf_weekly":      "ہفتہ وار موسمی خلاصہ",
    "sf_suitability": "مناسبیت",
    "sf_risk":        "خطرے کی سطح",
    "sf_ideal_date":  "بہترین تاریخ",
    "sf_water_req":   "پانی کی ضرورت",
    "sf_no_alerts":   "اس ہفتے کوئی موسمی انتباہ نہیں",
    "sf_avg_temp":    "اوسط درجہ حرارت",
    "sf_total_rain":  "کل بارش",
    "sf_avg_humidity":"اوسط نمی",
    "sf_avg_wind":    "اوسط ہوا",
    "sf_type":        "قسم",
    "sf_severity":    "شدت",
    "sf_alert_title": "انتباہ",
    "sf_action":      "تجویز کردہ عمل",
```

### Step 5.2 — Add English translations to `en_map` inside `T()`

Find the line `"ndvi_low":      "🔴 Low",` inside the `en_map` dict in `T()`. Add after it:

```python
            "sec8":           "8. Smart Farming Recommendations",
            "sf_alerts":      "Weather Alerts",
            "sf_planting":    "Planting Recommendation",
            "sf_weekly":      "Weekly Weather Summary",
            "sf_suitability": "Suitability Score",
            "sf_risk":        "Risk Level",
            "sf_ideal_date":  "Ideal Planting Date",
            "sf_water_req":   "Water Requirement",
            "sf_no_alerts":   "No weather alerts this week.",
            "sf_avg_temp":    "Avg Temp",
            "sf_total_rain":  "Total Rain",
            "sf_avg_humidity":"Avg Humidity",
            "sf_avg_wind":    "Avg Wind",
            "sf_type":        "Type",
            "sf_severity":    "Severity",
            "sf_alert_title": "Alert",
            "sf_action":      "Recommended Action",
```

### Step 5.3 — Update `generate_report` signature

Find:
```python
def generate_report(analysis_data, output_path, user=None, include_bands=True, language="en"):
```

Replace with:
```python
def generate_report(analysis_data, output_path, user=None, include_bands=True, language="en", smart_farming_data=None):
```

### Step 5.4 — Add `h3` helper inside `generate_report`

Find the `def h2(txt):` function defined inside `generate_report`. Add `h3` immediately after it:

```python
    def h3(txt):
        return P(txt, S("h3", fontSize=fs_body + 1, textColor=C_DARK,
                         fontName=fn_bold, spaceAfter=4, spaceBefore=8,
                         alignment=align))
```

### Step 5.5 — Insert Section 8 before the Band Composites block

Find the comment line:
```python
    # ── 7. BAND COMPOSITES ────────────────────────────────────────────────────
```

Insert the entire Section 8 block **immediately before** that comment:

```python
    # ── 8. SMART FARMING ─────────────────────────────────────────────────────
    if smart_farming_data:
        story.append(PageBreak())
        story.append(h2(T("sec8")))

        sf_alerts  = smart_farming_data.get("alerts", [])
        sf_plant   = smart_farming_data.get("planting_recommendation", {})
        sf_weekly  = smart_farming_data.get("weekly_summary", {})

        # 8a — Alerts
        story.append(h3(T("sf_alerts")))
        if sf_alerts:
            a_hdr = [T("sf_type"), T("sf_severity"), T("sf_alert_title"), T("sf_action")]
            a_rows = [a_hdr]
            sev_bg = {"high": colors.HexColor("#fef2f2"),
                      "medium": colors.HexColor("#fffbeb"),
                      "low":   colors.HexColor("#f0fdf4")}
            row_extras = []
            for i, a in enumerate(sf_alerts, 1):
                bg = sev_bg.get(a.get("severity", ""), C_WHITE)
                row_extras.append(("BACKGROUND", (0, i), (-1, i), bg))
                a_rows.append([
                    a.get("type", "—").replace("_", " ").title(),
                    a.get("severity", "—").title(),
                    a.get("title", "—"),
                    a.get("action", "—"),
                ])
            at = Table(a_rows, colWidths=[W*0.15, W*0.12, W*0.28, W*0.45])
            at.setStyle(TableStyle([
                ("BACKGROUND",  (0, 0), (-1, 0), C_DARK),
                ("TEXTCOLOR",   (0, 0), (-1, 0), C_WHITE),
                ("FONTNAME",    (0, 0), (-1, 0), fn_bold),
                ("FONTNAME",    (0, 1), (-1, -1), fn),
                ("FONTSIZE",    (0, 0), (-1, -1), fs_body),
                ("GRID",        (0, 0), (-1, -1), 0.5, C_BORDER),
                ("TOPPADDING",  (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING",(0, 0), (-1, -1), 7),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ] + row_extras))
            story.append(at)
        else:
            no_a = _ur(T("sf_no_alerts")) if is_ur else T("sf_no_alerts")
            story.append(P(no_a, S("sfna", fontSize=fs_body, fontName=fn,
                                   textColor=C_MUTED, alignment=align)))
        story.append(Spacer(1, 0.3*cm))

        # 8b — Planting Recommendation
        if sf_plant:
            story.append(h3(T("sf_planting")))
            ideal = sf_plant.get("ideal_date") or "—"
            story.append(make_kv([
                (T("sf_suitability"), f"{sf_plant.get('suitability_score', 0)*100:.0f}%"),
                (T("sf_risk"),        sf_plant.get("risk_level", "—").title()),
                (T("sf_ideal_date"),  ideal),
                (T("sf_water_req"),   f"{sf_plant.get('water_requirement_mm', 0):.0f} mm"),
            ], [W*0.40, W*0.60]))
            story.append(Spacer(1, 0.3*cm))

        # 8c — Weekly Weather Summary
        if sf_weekly:
            story.append(h3(T("sf_weekly")))

            def sf_cell(lbl_key, val_str):
                lbl = _ur(T(lbl_key)) if is_ur else T(lbl_key)
                val = _ur(val_str) if is_ur else val_str
                return P(
                    f"<b>{lbl}</b><br/>"
                    f"<font size='{'13' if is_ur else '14'}' color='#86efac'>{val}</font>",
                    S("sfbc", fontSize=fs_body, textColor=C_WHITE, fontName=fn,
                      leading=22, alignment=TA_CENTER))

            sf_banner = Table([[
                sf_cell("sf_avg_temp",    f"{sf_weekly.get('avg_temp', 0):.1f} °C"),
                sf_cell("sf_total_rain",  f"{sf_weekly.get('total_rain_mm', 0):.1f} mm"),
                sf_cell("sf_avg_humidity",f"{sf_weekly.get('avg_humidity', 0):.0f}%"),
                sf_cell("sf_avg_wind",    f"{sf_weekly.get('avg_wind_kmh', 0):.0f} km/h"),
            ]], colWidths=[W/4]*4)
            sf_banner.setStyle(TableStyle([
                ("BACKGROUND",    (0, 0), (-1, -1), C_DARK),
                ("TOPPADDING",    (0, 0), (-1, -1), 12),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
                ("LINEAFTER",     (0, 0), (2, -1), 0.5, colors.HexColor("#1a3a24")),
                ("ALIGN",         (0, 0), (-1, -1), "CENTER"),
                ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
            ]))
            story.append(sf_banner)
        story.append(Spacer(1, 0.4*cm))

```

### Step 5.6 — Smoke-test the PDF from Python REPL

```bash
conda run -n agrosense python - <<'EOF'
from desktop.utils.pdf_export import generate_report
import tempfile, os

dummy_analysis = {
    "field_name": "Test Field", "crop_type": "wheat",
    "vegetation_indices": {"ndvi": 0.45, "evi": 0.30, "ndwi": -0.10, "ndre": 0.22, "lai": 0.60},
    "crop_stress": {"prediction": "Healthy", "confidence": 0.92,
                    "probabilities": {"Healthy": 0.92, "Stressed": 0.06, "Diseased": 0.02}},
    "irrigation": {"recommendation": "moderate_irrigation", "soil_moisture_pct": 38.0,
                   "water_amount_mm": 22.0, "confidence": 0.85},
    "yield_prediction": {"predicted_yield_tha": 2.4, "yield_lower_bound": 1.9,
                         "yield_upper_bound": 2.9, "harvest_readiness_pct": 72.0},
    "soil_assessment": {"soil_ph": 7.2, "salinity_ds_m": 0.85, "organic_matter_pct": 1.4,
                        "ph_status": "Optimal", "salinity_status": "Low", "organic_matter_status": "Fair"},
    "vra_zones": {"zone": "Zone B", "fertiliser_recommendation": "Apply 80 kg/ha NPK",
                  "confidence": 0.78},
}

dummy_sf = {
    "alerts": [{"type": "heatwave", "severity": "high", "title": "Heatwave Warning",
                "action": "Increase irrigation", "days_until": 1}],
    "planting_recommendation": {"ideal_date": "2026-06-01", "risk_level": "low",
                                 "water_requirement_mm": 18.0, "suitability_score": 0.78},
    "weekly_summary": {"avg_temp": 34.2, "total_rain_mm": 2.5,
                       "avg_humidity": 52.0, "avg_wind_kmh": 17.0},
}

path = os.path.join(tempfile.gettempdir(), "agrosense_test.pdf")
generate_report(dummy_analysis, path, include_bands=False, smart_farming_data=dummy_sf)
print(f"OK — {path}")
EOF
```

Expected: `OK — /tmp/agrosense_test.pdf`. Open that file and verify Section 8 appears with the alerts table, planting recommendation, and weekly weather banner.

Also run Urdu variant:

```bash
conda run -n agrosense python - <<'EOF'
from desktop.utils.pdf_export import generate_report
import tempfile, os

dummy_analysis = {
    "field_name": "ٹیسٹ فیلڈ", "crop_type": "گندم",
    "vegetation_indices": {"ndvi": 0.45, "evi": 0.30, "ndwi": -0.10, "ndre": 0.22, "lai": 0.60},
    "crop_stress": {"prediction": "Healthy", "confidence": 0.92,
                    "probabilities": {"Healthy": 0.92, "Stressed": 0.06, "Diseased": 0.02}},
    "irrigation": {"recommendation": "moderate_irrigation", "soil_moisture_pct": 38.0,
                   "water_amount_mm": 22.0, "confidence": 0.85},
    "yield_prediction": {"predicted_yield_tha": 2.4, "yield_lower_bound": 1.9,
                         "yield_upper_bound": 2.9, "harvest_readiness_pct": 72.0},
    "soil_assessment": {"soil_ph": 7.2, "salinity_ds_m": 0.85, "organic_matter_pct": 1.4,
                        "ph_status": "Optimal", "salinity_status": "Low", "organic_matter_status": "Fair"},
    "vra_zones": {"zone": "Zone B", "fertiliser_recommendation": "Apply 80 kg/ha NPK",
                  "confidence": 0.78},
}
dummy_sf = {
    "alerts": [],
    "planting_recommendation": {"ideal_date": "2026-06-01", "risk_level": "medium",
                                 "water_requirement_mm": 20.0, "suitability_score": 0.65},
    "weekly_summary": {"avg_temp": 34.2, "total_rain_mm": 2.5,
                       "avg_humidity": 52.0, "avg_wind_kmh": 17.0},
}
path = os.path.join(tempfile.gettempdir(), "agrosense_test_ur.pdf")
generate_report(dummy_analysis, path, include_bands=False, language="ur", smart_farming_data=dummy_sf)
print(f"OK — {path}")
EOF
```

Expected: `OK — /tmp/agrosense_test_ur.pdf` with Urdu Section 8 and "no alerts" message.

### Step 5.7 — Commit

```bash
git add desktop/utils/pdf_export.py
git commit -m "feat: add Smart Farming section (Section 8) to PDF export"
```

---

## Task 6: Email alert — allow all crop statuses

**Files:**
- Modify: `desktop/utils/email_alerts.py`
- Create: `tests/test_email_alerts.py`

### Step 6.1 — Write failing tests

Create `tests/test_email_alerts.py`:

```python
import sys, os, unittest.mock as mock
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def _analysis(pred="Healthy"):
    return {
        "crop_stress": {"prediction": pred, "confidence": 0.92, "probabilities": {}},
        "field_name":  "Test Field",
        "crop_type":   "wheat",
        "irrigation":  {"recommendation": "moderate", "soil_moisture_pct": 40.0,
                        "water_amount_mm": 20.0},
        "soil_assessment": {},
        "yield_prediction": {"predicted_yield_tha": 2.4, "harvest_readiness_pct": 70.0},
        "vegetation_indices": {"ndvi": 0.45, "ndre": 0.22},
    }


# ── check_and_alert ───────────────────────────────────────────────────────────

def test_check_and_alert_sends_for_healthy():
    """check_and_alert must call send_crop_alert even when crop is Healthy."""
    from desktop.utils.email_alerts import check_and_alert
    with mock.patch("desktop.utils.email_alerts.send_crop_alert") as m:
        m.return_value = {"success": True, "message": "sent"}
        check_and_alert(_analysis("Healthy"), {"email": "farmer@example.com"})
        m.assert_called_once()


def test_check_and_alert_sends_for_stressed():
    from desktop.utils.email_alerts import check_and_alert
    with mock.patch("desktop.utils.email_alerts.send_crop_alert") as m:
        m.return_value = {"success": True, "message": "sent"}
        check_and_alert(_analysis("Stressed"), {"email": "farmer@example.com"})
        m.assert_called_once()


def test_check_and_alert_sends_for_diseased():
    from desktop.utils.email_alerts import check_and_alert
    with mock.patch("desktop.utils.email_alerts.send_crop_alert") as m:
        m.return_value = {"success": True, "message": "sent"}
        check_and_alert(_analysis("Diseased"), {"email": "farmer@example.com"})
        m.assert_called_once()


# ── send_crop_alert ───────────────────────────────────────────────────────────

def _run_send(pred):
    """Helper: run send_crop_alert with mocked SMTP and env vars."""
    from desktop.utils.email_alerts import send_crop_alert
    with mock.patch.dict(os.environ, {"GMAIL_USER": "bot@gmail.com",
                                      "GMAIL_APP_PASSWORD": "testpass"}):
        with mock.patch("smtplib.SMTP_SSL") as mock_ssl:
            srv = mock.MagicMock()
            mock_ssl.return_value.__enter__.return_value = srv
            result = send_crop_alert(_analysis(pred), "farmer@example.com")
            return result, srv


def test_send_healthy_does_not_return_early():
    result, srv = _run_send("Healthy")
    assert result["success"] is True
    srv.sendmail.assert_called_once()


def test_send_healthy_subject_contains_healthy():
    from desktop.utils.email_alerts import send_crop_alert
    captured = {}
    def fake_sendmail(frm, to, msg_str):
        captured["msg"] = msg_str
    with mock.patch.dict(os.environ, {"GMAIL_USER": "bot@gmail.com",
                                      "GMAIL_APP_PASSWORD": "testpass"}):
        with mock.patch("smtplib.SMTP_SSL") as mock_ssl:
            srv = mock.MagicMock()
            srv.sendmail.side_effect = fake_sendmail
            mock_ssl.return_value.__enter__.return_value = srv
            send_crop_alert(_analysis("Healthy"), "farmer@example.com")
    assert "Healthy" in captured["msg"]
    assert "🚨" not in captured["msg"]


def test_send_diseased_subject_contains_alert_emoji():
    from desktop.utils.email_alerts import send_crop_alert
    captured = {}
    def fake_sendmail(frm, to, msg_str):
        captured["msg"] = msg_str
    with mock.patch.dict(os.environ, {"GMAIL_USER": "bot@gmail.com",
                                      "GMAIL_APP_PASSWORD": "testpass"}):
        with mock.patch("smtplib.SMTP_SSL") as mock_ssl:
            srv = mock.MagicMock()
            srv.sendmail.side_effect = fake_sendmail
            mock_ssl.return_value.__enter__.return_value = srv
            send_crop_alert(_analysis("Diseased"), "farmer@example.com")
    assert "🚨" in captured["msg"]
```

### Step 6.2 — Run tests to confirm they fail

```bash
conda run -n agrosense pytest tests/test_email_alerts.py -v
```

Expected: `test_check_and_alert_sends_for_healthy` and `test_send_healthy_does_not_return_early` FAIL; others may pass.

### Step 6.3 — Fix `send_crop_alert` in `desktop/utils/email_alerts.py`

**Remove** the early-return block (lines 51–53):
```python
    # Only send alert for stressed or diseased crops
    if pred == "Healthy":
        return {"success": False, "message": "Crop is healthy — no alert needed"}
```

**Replace** the `color_map` and `subject` lines:
```python
    color_map = {"Stressed": "#d4a017", "Diseased": "#dc2626"}
    alert_color = color_map.get(pred, "#6b7280")

    subject = f"🚨 AgroSense Alert: {pred} crop detected in {field}"
```

With:
```python
    color_map = {"Healthy": "#1a6b35", "Stressed": "#d4a017", "Diseased": "#dc2626"}
    alert_color = color_map.get(pred, "#6b7280")

    if pred == "Healthy":
        subject      = f"✅ AgroSense Report: {field} crop is Healthy"
        banner_text  = "CROP STATUS: HEALTHY — No immediate action required"
    else:
        subject      = f"🚨 AgroSense Alert: {pred} crop detected in {field}"
        banner_text  = f"⚠  {pred.upper()} CROP DETECTED — Immediate attention required"
```

**Replace** the banner div line in `html_body`:
```python
  <div class="alert-banner">
    ⚠  {pred.upper()} CROP DETECTED — Immediate attention required
  </div>
```

With:
```python
  <div class="alert-banner">
    {banner_text}
  </div>
```

### Step 6.4 — Fix `check_and_alert` in `desktop/utils/email_alerts.py`

Replace the entire `check_and_alert` function body:

```python
def check_and_alert(analysis_data: dict, user: dict, admin_email: str = None) -> dict:
    """Send an email report for any crop status (Healthy, Stressed, or Diseased)."""
    return send_crop_alert(
        analysis_data=analysis_data,
        user_email=user.get("email", ""),
        admin_email=admin_email,
    )
```

### Step 6.5 — Run all email tests

```bash
conda run -n agrosense pytest tests/test_email_alerts.py -v
```

Expected: all 7 tests PASSED

### Step 6.6 — Run full test suite to confirm no regressions

```bash
conda run -n agrosense pytest tests/ -v --ignore=tests/test_api.py
```

Expected: all tests PASSED (test_api.py skipped because it needs a live server).

### Step 6.7 — Commit

```bash
git add desktop/utils/email_alerts.py tests/test_email_alerts.py
git commit -m "fix: send email alert for all crop statuses, not just Stressed/Diseased"
```

---

## Self-Review Checklist (pre-execution)

- [x] **Spec section 1** (temperature endpoint + stat card): covered by Tasks 1, 2, 3
- [x] **Spec section 2** (Smart Farming PDF section): covered by Tasks 4, 5
- [x] **Spec section 3** (email for all statuses): covered by Task 6
- [x] **No placeholders**: every step has full code
- [x] **Type consistency**: `_parse_current_response` imported in test matches function defined in Task 1.3; `smart_farming_data` parameter added in Task 5.3 matches call in Task 4.1; `send_crop_alert` signature unchanged
- [x] **`self._sv[4]`**: the 5th stat card is index 4 (0-based) — Task 3 adds `stat_temp` as 5th element in `stat_keys` and `stat_cols`, so `self._sv[4]` is always the temperature card
- [x] **`banner_text` variable**: defined before `html_body` f-string in Task 6.3 ✓
