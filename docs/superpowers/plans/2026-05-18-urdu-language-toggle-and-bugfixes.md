# Urdu Language Toggle & Bug Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a full-app English/Urdu language toggle with RTL layout flip to the AgroSense PyQt6 desktop app, and fix four existing bugs (UUID debug label, missing delete-farm button, worker memory leak, and silent exception swallowing).

**Architecture:** A `LanguageManager` singleton in `desktop/i18n.py` holds a flat translation dictionary and emits `language_changed` when the user clicks the toggle button. Every page and window connects to this signal at construction and calls `_retranslate()` — which updates all stored label/button references — whenever the language changes. `QApplication.setLayoutDirection()` handles the global RTL/LTR flip.

**Tech Stack:** PyQt6 6.x, Python 3.11, pytest. Backend is untouched.

---

## File Map

| File | Status | Responsibility |
|------|--------|----------------|
| `desktop/i18n.py` | **Create** | `LanguageManager` singleton + full `STRINGS` translation dict |
| `tests/test_i18n.py` | **Create** | Unit tests for `LanguageManager` |
| `desktop/windows/login.py` | Modify | Add lang toggle button; promote labels to `self.*`; add `_retranslate()` |
| `desktop/windows/register.py` | Modify | Promote labels to `self.*`; add `_retranslate()` |
| `desktop/windows/main_window.py` | Modify | Add topbar toggle button; update `_go()` to use `LM.tr()`; add `_retranslate()` |
| `desktop/pages/dashboard.py` | Modify | Promote stat-title labels; add `_retranslate()` |
| `desktop/pages/farms.py` | Modify | Fix bugs 1–3; promote labels; add `_retranslate()` |
| `desktop/pages/imagery.py` | Modify | Promote form labels; add `_retranslate()` |
| `desktop/pages/analytics.py` | Modify | Promote labels; add `_retranslate()` |
| `desktop/pages/map_view.py` | Modify | Fix bug 4; promote labels; add `_retranslate()` |
| `desktop/pages/band_view.py` | Modify | Fix bug 4; promote labels; add `_retranslate()` |

---

## Task 1: Create `desktop/i18n.py` and unit tests

**Files:**
- Create: `desktop/i18n.py`
- Create: `tests/test_i18n.py`

- [ ] **Step 1.1 — Write the failing unit tests**

Create `tests/test_i18n.py`:

```python
import sys
import pytest
from unittest.mock import patch, MagicMock
from PyQt6.QtWidgets import QApplication

# One QApplication for the whole test session (PyQt6 requires one)
@pytest.fixture(scope="session", autouse=True)
def qapp():
    app = QApplication.instance() or QApplication(sys.argv)
    yield app


def test_tr_returns_english_by_default():
    from desktop.i18n import LanguageManager
    lm = LanguageManager()
    assert lm.tr("nav_dashboard") == "🏠  Dashboard"


def test_tr_returns_urdu_after_toggle():
    from desktop.i18n import LanguageManager
    lm = LanguageManager()
    with patch("desktop.i18n.QApplication") as mock_qapp:
        mock_qapp.instance.return_value = None
        lm.toggle()
    assert lm.tr("nav_dashboard") == "🏠  ڈیش بورڈ"


def test_tr_returns_key_for_unknown_key():
    from desktop.i18n import LanguageManager
    lm = LanguageManager()
    assert lm.tr("nonexistent_key_xyz") == "nonexistent_key_xyz"


def test_is_urdu_false_by_default():
    from desktop.i18n import LanguageManager
    lm = LanguageManager()
    assert lm.is_urdu() is False


def test_toggle_twice_returns_to_english():
    from desktop.i18n import LanguageManager
    lm = LanguageManager()
    with patch("desktop.i18n.QApplication") as mock_qapp:
        mock_qapp.instance.return_value = None
        lm.toggle()
        lm.toggle()
    assert lm.current_lang == "en"
    assert lm.is_urdu() is False


def test_language_changed_signal_fires_on_toggle():
    from desktop.i18n import LanguageManager
    received = []
    lm = LanguageManager()
    lm.language_changed.connect(lambda lang: received.append(lang))
    with patch("desktop.i18n.QApplication") as mock_qapp:
        mock_qapp.instance.return_value = None
        lm.toggle()
    assert received == ["ur"]


def test_all_strings_have_both_languages():
    from desktop.i18n import STRINGS
    for key, val in STRINGS.items():
        assert "en" in val, f"Missing 'en' for key '{key}'"
        assert "ur" in val, f"Missing 'ur' for key '{key}'"


def test_lang_toggle_key_shows_correct_label():
    from desktop.i18n import LanguageManager
    lm = LanguageManager()
    # When English is active, button should show Urdu label (to invite switch)
    assert lm.tr("lang_toggle") == "🌐 اردو"
    with patch("desktop.i18n.QApplication") as mock_qapp:
        mock_qapp.instance.return_value = None
        lm.toggle()
    # When Urdu is active, button should show EN label
    assert lm.tr("lang_toggle") == "🌐 EN"
```

- [ ] **Step 1.2 — Run tests to confirm they all fail (module not found)**

```bash
cd /home/ali/Agrosense/agrosense
python -m pytest tests/test_i18n.py -v 2>&1 | head -30
```

Expected: `ModuleNotFoundError: No module named 'desktop.i18n'`

- [ ] **Step 1.3 — Create `desktop/i18n.py`**

```python
from PyQt6.QtCore import QObject, pyqtSignal, Qt
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QFont

STRINGS = {
    # ── App / MainWindow ──────────────────────────────────────────────────────
    "app_name":               {"en": "AgroSense",                            "ur": "ایگرو سینس"},
    "main_menu":              {"en": "MAIN MENU",                            "ur": "مرکزی مینو"},
    "nav_dashboard":          {"en": "🏠  Dashboard",                        "ur": "🏠  ڈیش بورڈ"},
    "nav_farms":              {"en": "🗺  Farms & Fields",                   "ur": "🗺  کھیت اور زمین"},
    "nav_imagery":            {"en": "🛰  Satellite Imagery",                "ur": "🛰  سیٹلائٹ تصاویر"},
    "nav_analytics":          {"en": "📊  Analytics",                        "ur": "📊  تجزیات"},
    "nav_map":                {"en": "🗺  Map View",                         "ur": "🗺  نقشہ"},
    "nav_bands":              {"en": "🛰  Band View",                        "ur": "🛰  بینڈ ویو"},
    "connected":              {"en": "● Connected",                          "ur": "● متصل"},
    "sign_out":               {"en": "⎋  Sign out",                          "ur": "⎋  باہر نکلیں"},
    "lang_toggle":            {"en": "🌐 اردو",                              "ur": "🌐 EN"},
    "topbar_title_dashboard": {"en": "Dashboard",                            "ur": "ڈیش بورڈ"},
    "topbar_title_farms":     {"en": "Farms & Fields",                       "ur": "کھیت اور زمین"},
    "topbar_title_imagery":   {"en": "Satellite Imagery",                    "ur": "سیٹلائٹ تصاویر"},
    "topbar_title_analytics": {"en": "Analytics",                            "ur": "تجزیات"},
    "topbar_title_map":       {"en": "Map View",                             "ur": "نقشہ"},
    "topbar_title_bands":     {"en": "Band View",                            "ur": "بینڈ ویو"},
    "topbar_sub_dashboard":   {"en": "Crop intelligence overview",           "ur": "فصل انٹیلیجنس کا جائزہ"},
    "topbar_sub_farms":       {"en": "Manage farms and fields",              "ur": "کھیت اور زمین کا انتظام"},
    "topbar_sub_imagery":     {"en": "Fetch and analyse Sentinel-2 data",    "ur": "سینٹینل-2 ڈیٹا کا تجزیہ"},
    "topbar_sub_analytics":   {"en": "Index trends over time",               "ur": "وقت کے ساتھ انڈیکس رجحانات"},
    "topbar_sub_map":         {"en": "Farm locations on satellite map",       "ur": "سیٹلائٹ نقشے پر کھیتوں کا مقام"},
    "topbar_sub_bands":       {"en": "Sentinel-2 band composites per field", "ur": "فی فیلڈ سینٹینل-2 بینڈ"},
    # ── Dashboard ─────────────────────────────────────────────────────────────
    "stat_farms":             {"en": "Total Farms",                          "ur": "کل فارم"},
    "stat_fields":            {"en": "Total Fields",                         "ur": "کل فیلڈز"},
    "stat_health":            {"en": "Crop Health",                          "ur": "فصل کی صحت"},
    "stat_yield":             {"en": "Est. Yield",                           "ur": "متوقع پیداوار"},
    "analysis_title":         {"en": "🔬  Full Field Analysis",              "ur": "🔬  مکمل فیلڈ تجزیہ"},
    "run_analysis":           {"en": "▶  Run Analysis",                      "ur": "▶  تجزیہ چلائیں"},
    "analysing":              {"en": "Analysing...",                         "ur": "تجزیہ ہو رہا ہے..."},
    "export_pdf":             {"en": "📄  Export PDF (with satellite images)","ur": "📄  پی ڈی ایف برآمد کریں"},
    "send_alert":             {"en": "📧  Send Alert",                       "ur": "📧  الرٹ بھیجیں"},
    "fetching_pdf":           {"en": "⏳  Fetching bands & generating PDF...","ur": "⏳  بینڈ حاصل ہو رہے ہیں..."},
    "pdf_ready_title":        {"en": "PDF Ready",                            "ur": "پی ڈی ایف تیار ہے"},
    "pdf_error_title":        {"en": "PDF Error",                            "ur": "پی ڈی ایف میں خرابی"},
    "no_data_title":          {"en": "No Data",                              "ur": "کوئی ڈیٹا نہیں"},
    "run_analysis_first":     {"en": "Please run analysis first.",           "ur": "پہلے تجزیہ چلائیں۔"},
    "alert_title":            {"en": "Alert",                                "ur": "الرٹ"},
    "alert_error_title":      {"en": "Alert Error",                          "ur": "الرٹ میں خرابی"},
    # ── Farms ─────────────────────────────────────────────────────────────────
    "add_farm_btn":           {"en": "+ Add Farm",                           "ur": "+ فارم شامل کریں"},
    "del_farm_btn":           {"en": "🗑  Delete Farm",                      "ur": "🗑  فارم حذف کریں"},
    "no_farm_selected":       {"en": "No farm selected — click a row below", "ur": "کوئی فارم منتخب نہیں — نیچے کلک کریں"},
    "fields_section":         {"en": "Fields",                               "ur": "فیلڈز"},
    "add_field_btn":          {"en": "+ Add Field",                          "ur": "+ فیلڈ شامل کریں"},
    "farm_tbl_name":          {"en": "Farm Name",                            "ur": "فارم کا نام"},
    "farm_tbl_district":      {"en": "District",                             "ur": "ضلع"},
    "farm_tbl_province":      {"en": "Province",                             "ur": "صوبہ"},
    "farm_tbl_area":          {"en": "Area (ha)",                            "ur": "رقبہ (ہیکٹر)"},
    "field_tbl_name":         {"en": "Field Name",                           "ur": "فیلڈ کا نام"},
    "field_tbl_crop":         {"en": "Crop Type",                            "ur": "فصل کی قسم"},
    "field_tbl_area":         {"en": "Area (ha)",                            "ur": "رقبہ (ہیکٹر)"},
    "field_tbl_id":           {"en": "ID",                                   "ur": "شناخت"},
    "del_farm_confirm":       {"en": "Delete this farm and all its fields?", "ur": "یہ فارم اور تمام فیلڈز حذف کریں؟"},
    "del_farm_dialog":        {"en": "Delete Farm",                          "ur": "فارم حذف کریں"},
    "add_farm_dialog_title":  {"en": "Add New Farm",                         "ur": "نیا فارم شامل کریں"},
    "form_farm_name":         {"en": "Farm Name *",                          "ur": "فارم کا نام *"},
    "form_district":          {"en": "District",                             "ur": "ضلع"},
    "form_province":          {"en": "Province",                             "ur": "صوبہ"},
    "form_area_ha":           {"en": "Area (ha)",                            "ur": "رقبہ (ہیکٹر)"},
    "form_latitude":          {"en": "Latitude",                             "ur": "عرض البلد"},
    "form_longitude":         {"en": "Longitude",                            "ur": "طول البلد"},
    "add_farm_save_btn":      {"en": "Add Farm",                             "ur": "فارم شامل کریں"},
    "cancel_btn":             {"en": "Cancel",                               "ur": "منسوخ"},
    "saving_btn":             {"en": "Saving...",                            "ur": "محفوظ ہو رہا ہے..."},
    "add_field_dialog_title": {"en": "Add Field",                            "ur": "فیلڈ شامل کریں"},
    "form_field_name":        {"en": "Field Name",                           "ur": "فیلڈ کا نام"},
    "form_crop_type":         {"en": "Crop Type",                            "ur": "فصل کی قسم"},
    "add_field_save_btn":     {"en": "Add Field",                            "ur": "فیلڈ شامل کریں"},
    "no_farm_sel_title":      {"en": "No Farm Selected",                     "ur": "فارم منتخب نہیں"},
    "no_farm_sel_msg":        {"en": "Please click on a farm row to select it first.", "ur": "پہلے فارم قطار پر کلک کریں۔"},
    # ── Imagery ───────────────────────────────────────────────────────────────
    "imagery_config":         {"en": "📡  Configure Satellite Analysis",     "ur": "📡  سیٹلائٹ تجزیہ ترتیب دیں"},
    "farm_label":             {"en": "Farm:",                                "ur": "فارم:"},
    "field_label":            {"en": "Field:",                               "ur": "فیلڈ:"},
    "start_label":            {"en": "Start:",                               "ur": "شروع:"},
    "end_label":              {"en": "End:",                                  "ur": "اختتام:"},
    "max_cloud_label":        {"en": "Max Cloud:",                           "ur": "زیادہ بادل:"},
    "fetch_analyse":          {"en": "🛰  Fetch & Analyse",                  "ur": "🛰  حاصل کریں اور تجزیہ کریں"},
    "fetching_gee_btn":       {"en": "⏳  Fetching from GEE...",             "ur": "⏳  جی ای ای سے حاصل ہو رہا ہے..."},
    "gee_contact":            {"en": "Contacting Google Earth Engine...",    "ur": "گوگل ارتھ انجن سے رابطہ..."},
    "imagery_results_title":  {"en": "📊  Latest Results",                   "ur": "📊  تازہ ترین نتائج"},
    "index_history_title":    {"en": "📅  Index History",                    "ur": "📅  انڈیکس تاریخ"},
    "select_field_msg":       {"en": "⚠  Please select a field",             "ur": "⚠  فیلڈ منتخب کریں"},
    "select_farm_opt":        {"en": "Select farm...",                       "ur": "فارم منتخب کریں..."},
    "select_field_opt":       {"en": "Select field...",                      "ur": "فیلڈ منتخب کریں..."},
    # ── Analytics ─────────────────────────────────────────────────────────────
    "select_farm_field_msg":  {"en": "Select a farm and field to view analytics", "ur": "تجزیات دیکھنے کے لیے فارم اور فیلڈ منتخب کریں"},
    "loading_txt":            {"en": "Loading...",                           "ur": "لوڈ ہو رہا ہے..."},
    "no_history_msg":         {"en": "No history found. Run imagery analysis first.", "ur": "کوئی تاریخ نہیں۔ پہلے سیٹلائٹ تجزیہ چلائیں۔"},
    # ── Map ───────────────────────────────────────────────────────────────────
    "all_farms_opt":          {"en": "🌍  All Farms",                        "ur": "🌍  تمام فارم"},
    "loading_farms":          {"en": "Loading farms...",                     "ur": "فارم لوڈ ہو رہے ہیں..."},
    "map_farm_label":         {"en": "🌍  Farm:",                            "ur": "🌍  فارم:"},
    "map_reset":              {"en": "🔍  Reset",                            "ur": "🔍  دوبارہ ترتیب"},
    "map_error":              {"en": "Error loading farms",                  "ur": "فارم لوڈ کرنے میں خرابی"},
    # ── Band View ─────────────────────────────────────────────────────────────
    "fetch_bands":            {"en": "🛰  Fetch Band Composites",            "ur": "🛰  بینڈ کمپوزٹ حاصل کریں"},
    "select_field_fetch":     {"en": "Select a field and click Fetch Band Composites", "ur": "فیلڈ منتخب کریں اور بینڈ کمپوزٹ حاصل کریں"},
    "fetching_bands_btn":     {"en": "⏳  Fetching from GEE...",             "ur": "⏳  جی ای ای سے حاصل ہو رہا ہے..."},
    "band_load_error":        {"en": "Error loading fields",                 "ur": "فیلڈز لوڈ کرنے میں خرابی"},
    # ── Login ─────────────────────────────────────────────────────────────────
    "welcome_back":           {"en": "Welcome back",                         "ur": "خوش آمدید"},
    "signin_subtitle":        {"en": "Sign in to your AgroSense account",    "ur": "اپنے اکاؤنٹ میں داخل ہوں"},
    "email_label_login":      {"en": "Email address",                        "ur": "ای میل پتہ"},
    "password_label_login":   {"en": "Password",                             "ur": "پاس ورڈ"},
    "signin_btn":             {"en": "Sign In →",                            "ur": "← داخل ہوں"},
    "signing_in":             {"en": "Signing in...",                        "ur": "داخل ہو رہے ہیں..."},
    "create_account_link":    {"en": "Create a new account",                 "ur": "نیا اکاؤنٹ بنائیں"},
    "login_tagline":          {"en": "Satellite-Based Crop\nIntelligence for Pakistan", "ur": "پاکستان کے لیے\nسیٹلائٹ بنیاد فصل انٹیلیجنس"},
    "invalid_login":          {"en": "Invalid email or password. Please try again.", "ur": "غلط ای میل یا پاس ورڈ۔ دوبارہ کوشش کریں۔"},
    "enter_credentials":      {"en": "Please enter your email and password", "ur": "ای میل اور پاس ورڈ درج کریں"},
    "or_divider":             {"en": "  or  ",                               "ur": "  یا  "},
    # ── Register ──────────────────────────────────────────────────────────────
    "create_account_title":   {"en": "Create Account",                       "ur": "اکاؤنٹ بنائیں"},
    "monitor_crops":          {"en": "Start monitoring your crops",          "ur": "اپنی فصلوں کی نگرانی شروع کریں"},
    "full_name_label":        {"en": "Full Name",                            "ur": "پورا نام"},
    "email_reg_label":        {"en": "Email",                                "ur": "ای میل"},
    "password_reg_label":     {"en": "Password",                             "ur": "پاس ورڈ"},
    "role_label":             {"en": "Role",                                 "ur": "کردار"},
    "create_account_btn":     {"en": "Create Account",                       "ur": "اکاؤنٹ بنائیں"},
    "creating_account":       {"en": "Creating account...",                  "ur": "اکاؤنٹ بنایا جا رہا ہے..."},
    "all_fields_required":    {"en": "All fields are required",              "ur": "تمام خانے ضروری ہیں"},
    "reg_success_msg":        {"en": "Account created! You can now sign in.", "ur": "اکاؤنٹ بن گیا! اب داخل ہو سکتے ہیں۔"},
    "success_title":          {"en": "Success",                              "ur": "کامیابی"},
    "reg_window_title":       {"en": "AgroSense — Register",                 "ur": "ایگرو سینس — رجسٹریشن"},
    # ── Table headers (technical terms kept in EN for Urdu too) ───────────────
    "tbl_date":               {"en": "Date",                                 "ur": "تاریخ"},
    "tbl_ndvi":               {"en": "NDVI",                                 "ur": "NDVI"},
    "tbl_evi":                {"en": "EVI",                                  "ur": "EVI"},
    "tbl_ndwi":               {"en": "NDWI",                                 "ur": "NDWI"},
    "tbl_ndre":               {"en": "NDRE",                                 "ur": "NDRE"},
    "tbl_lai":                {"en": "LAI",                                  "ur": "LAI"},
}


class LanguageManager(QObject):
    language_changed = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self._lang = "en"

    @property
    def current_lang(self) -> str:
        return self._lang

    def tr(self, key: str) -> str:
        entry = STRINGS.get(key, {})
        return entry.get(self._lang, entry.get("en", key))

    def is_urdu(self) -> bool:
        return self._lang == "ur"

    def toggle(self):
        self._lang = "ur" if self._lang == "en" else "en"
        app = QApplication.instance()
        if app:
            if self._lang == "ur":
                app.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
                self._apply_urdu_font(app)
            else:
                app.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
                app.setFont(QFont("Segoe UI", 10))
        self.language_changed.emit(self._lang)

    def _apply_urdu_font(self, app):
        for family in ("Noto Nastaliq Urdu", "Traditional Arabic", "Arial Unicode MS"):
            f = QFont(family, 12)
            if f.family() == family:
                app.setFont(f)
                return
        app.setFont(QFont("Arial", 11))


LM = LanguageManager()
```

- [ ] **Step 1.4 — Run tests to confirm they all pass**

```bash
cd /home/ali/Agrosense/agrosense
python -m pytest tests/test_i18n.py -v
```

Expected output — all 8 tests `PASSED`.

- [ ] **Step 1.5 — Commit**

```bash
git add desktop/i18n.py tests/test_i18n.py
git commit -m "feat: add LanguageManager singleton with full EN/UR translation dict"
```

---

## Task 2: Fix bugs 1–3 in `desktop/pages/farms.py`

**Files:**
- Modify: `desktop/pages/farms.py`

**Bug 1:** Remove debug UUID label from `AddFieldDialog._build()` (line 94).  
**Bug 2:** Add a "Delete Farm" button wired to `_del_farm`.  
**Bug 3:** Add `w.finished.connect` cleanup to `_load_farms` and `_load_fields`.

- [ ] **Step 2.1 — Replace `AddFieldDialog._build()` — remove UUID label**

In `desktop/pages/farms.py`, replace the entire `_build` method of `AddFieldDialog`:

```python
    def _build(self, farm_name):
        l = QVBoxLayout(self); l.setContentsMargins(28,24,28,24); l.setSpacing(10)
        l.addWidget(mk_label(f"Add Field to {farm_name}", 14, T, True))
        self.inputs = {}
        for label, key, ph in [("Field Name","name","e.g. Field A"),
                                ("Area (ha)","area_ha","e.g. 10")]:
            l.addWidget(mk_label(label, 12, "#374151", True))
            inp = mk_input(ph); l.addWidget(inp); self.inputs[key] = inp

        l.addWidget(mk_label("Crop Type", 12, "#374151", True))
        self.crop_combo = QComboBox()
        self.crop_combo.addItems(["wheat", "rice", "cotton", "sugarcane", "mango"])
        self.crop_combo.setFixedHeight(38)
        self.crop_combo.setStyleSheet(f"""
            QComboBox{{color:{T};background:{W};border:1.5px solid {B};border-radius:8px;
                       padding:0 12px;font-size:13px;font-family:'Segoe UI';}}
            QComboBox:focus{{border-color:{G};}}
            QComboBox::drop-down{{border:none;width:28px;}}
            QComboBox QAbstractItemView{{color:{T};background:{W};selection-background-color:{A};
                                         border:1px solid {B};font-size:13px;}}
        """)
        l.addWidget(self.crop_combo)
        self.err = mk_label("", 12, R); self.err.hide(); l.addWidget(self.err)
        row = QHBoxLayout()
        cb = QPushButton("Cancel")
        cb.setStyleSheet(f"QPushButton{{background:{A};color:{G};border:1px solid #b8d8c4;border-radius:8px;padding:6px 14px;font-family:'Segoe UI';}}")
        cb.clicked.connect(self.reject)
        self.sb = mk_btn("Add Field"); self.sb.clicked.connect(self._save)
        row.addWidget(cb); row.addStretch(); row.addWidget(self.sb)
        l.addLayout(row)
```

*(The only change from the original is removing the two `fid_lbl` lines.)*

- [ ] **Step 2.2 — Add Delete Farm button and wire to `_del_farm` in `FarmsPage._build()`**

Replace the `_build` method's header section in `FarmsPage`. Find this block:

```python
        # Header
        hr = QHBoxLayout(); hr.addStretch()
        add_btn = mk_btn("+ Add Farm", w=120)
        add_btn.clicked.connect(self._add_farm)
        hr.addWidget(add_btn); l.addLayout(hr)
```

Replace it with:

```python
        # Header
        hr = QHBoxLayout(); hr.addStretch()
        add_btn = mk_btn("+ Add Farm", w=120)
        add_btn.clicked.connect(self._add_farm)
        hr.addWidget(add_btn)
        self.del_farm_btn = mk_btn("🗑  Delete Farm", color="#dc2626", w=150)
        self.del_farm_btn.setEnabled(False)
        self.del_farm_btn.clicked.connect(
            lambda: self._del_farm(self._selected_farm_id)
        )
        hr.addWidget(self.del_farm_btn)
        l.addLayout(hr)
```

Also update `_on_selection` to enable `self.del_farm_btn` when a farm is selected. Find:

```python
        self.add_field_btn.setEnabled(True)
```

Add the line below it:

```python
        self.del_farm_btn.setEnabled(True)
```

And in `_del_farm`, after clearing `self._selected_farm_id`, disable the button. Find this in `_del_farm`:

```python
                if self._selected_farm_id == farm_id:
                    self._selected_farm_id = None
                    self._selected_farm_name = ""
                    self.add_field_btn.setEnabled(False)
                    self.field_tbl.setRowCount(0)
```

Replace with:

```python
                if self._selected_farm_id == farm_id:
                    self._selected_farm_id = None
                    self._selected_farm_name = ""
                    self.add_field_btn.setEnabled(False)
                    self.del_farm_btn.setEnabled(False)
                    self.field_tbl.setRowCount(0)
```

- [ ] **Step 2.3 — Add worker cleanup to `_load_farms` and `_load_fields`**

Replace `_load_farms` in `FarmsPage`:

```python
    def _load_farms(self):
        w = Worker(api.get_farms)
        self._workers.append(w)
        w.done.connect(self._on_farms_loaded)
        w.err.connect(lambda e: self.sel_lbl.setText(f"Error: {e}"))
        w.finished.connect(lambda: self._workers.remove(w) if w in self._workers else None)
        w.start()
```

Replace `_load_fields` in `FarmsPage`:

```python
    def _load_fields(self, farm_id):
        w = Worker(api.get_fields, farm_id)
        self._workers.append(w)
        w.done.connect(self._on_fields_loaded)
        w.finished.connect(lambda: self._workers.remove(w) if w in self._workers else None)
        w.start()
```

- [ ] **Step 2.4 — Smoke-test: launch the app and verify**

```bash
cd /home/ali/Agrosense/agrosense
uvicorn app.main:app --port 8000 &   # must already be running; skip if so
python desktop/main.py
```

Verify:
- Navigate to Farms & Fields page
- "Add Field" dialog: **no Farm ID line visible**
- "Delete Farm" button is present but greyed out
- Click a farm row → Delete Farm button becomes active
- Click Delete Farm → confirmation dialog → farm is removed

- [ ] **Step 2.5 — Commit**

```bash
git add desktop/pages/farms.py
git commit -m "fix: remove UUID debug label, wire delete-farm button, add worker cleanup"
```

---

## Task 3: Fix bug 4 — silent exceptions in `map_view.py` and `band_view.py`

**Files:**
- Modify: `desktop/pages/map_view.py`
- Modify: `desktop/pages/band_view.py`

- [ ] **Step 3.1 — Add `err` signal to `FarmWorker` and connect it in `MapPage`**

In `desktop/pages/map_view.py`, replace the entire `FarmWorker` class:

```python
class FarmWorker(QThread):
    done = pyqtSignal(list)
    err  = pyqtSignal(str)

    def run(self):
        try:
            farms = api.get_farms()
            for farm in farms:
                fields = api.get_fields(farm["id"])
                for f in fields:
                    try:
                        history = api.get_index_history(f["id"])
                        f["latest_indices"] = history[0] if history else None
                    except Exception:
                        f["latest_indices"] = None
                farm["fields"] = fields
            self.done.emit(farms)
        except Exception as e:
            self.err.emit(str(e))
```

In `MapPage._load()`, connect the new `err` signal:

```python
    def _load(self):
        w = FarmWorker()
        self._workers.append(w)
        w.done.connect(self._on_loaded)
        w.err.connect(lambda msg: self.status.setText(f"❌  {msg}"))
        w.finished.connect(lambda: self._workers.remove(w) if w in self._workers else None)
        w.start()
```

- [ ] **Step 3.2 — Add `err` signal to `LoadWorker` and connect it in `BandViewPage`**

In `desktop/pages/band_view.py`, replace the entire `LoadWorker` class:

```python
class LoadWorker(QThread):
    done = pyqtSignal(list, list)
    err  = pyqtSignal(str)

    def run(self):
        try:
            farms  = api.get_farms()
            fields = []
            for farm in farms:
                for f in api.get_fields(farm["id"]):
                    f["farm_name"] = farm["name"]
                    fields.append(f)
            self.done.emit(farms, fields)
        except Exception as e:
            self.err.emit(str(e))
```

In `BandViewPage._load_fields()`, connect the `err` signal:

```python
    def _load_fields(self):
        self._lw = LoadWorker()
        self._lw.done.connect(self._on_loaded)
        self._lw.err.connect(lambda msg: self.status.setText(f"❌  {msg}"))
        self._lw.start()
```

- [ ] **Step 3.3 — Commit**

```bash
git add desktop/pages/map_view.py desktop/pages/band_view.py
git commit -m "fix: surface FarmWorker and LoadWorker errors to status label instead of swallowing"
```

---

## Task 4: Language toggle button in `LoginWindow` + `_retranslate()`

**Files:**
- Modify: `desktop/windows/login.py`

The login window needs its own language toggle because users may want to switch before they log in. We add a small `🌐` button next to the existing close button in the top-right row. Labels are promoted to `self.*` so `_retranslate()` can update them.

- [ ] **Step 4.1 — Rewrite `desktop/windows/login.py`**

Replace the entire file with:

```python
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QFrame
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QColor, QPainter, QLinearGradient, QBrush
import desktop.api as api
from desktop.i18n import LM


class LoginWorker(QThread):
    success = pyqtSignal(str, dict)
    error   = pyqtSignal(str)
    def __init__(self, email, password):
        super().__init__()
        self.email = email; self.password = password
    def run(self):
        try:
            data  = api.login(self.email, self.password)
            token = data["access_token"]
            api.set_token(token)
            me = api.get_me()
            self.success.emit(token, me)
        except Exception as e:
            self.error.emit(str(e))


class LoginWindow(QWidget):
    login_success = pyqtSignal(dict)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("AgroSense")
        self.setFixedSize(920, 580)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self._worker = None
        self._drag_pos = None
        self._build()
        LM.language_changed.connect(self._retranslate)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        g = QLinearGradient(0, 0, 0, self.height())
        g.setColorAt(0, QColor("#0d2414"))
        g.setColorAt(1, QColor("#1a4a2a"))
        p.fillRect(0, 0, 420, self.height(), QBrush(g))
        p.fillRect(420, 0, self.width()-420, self.height(), QColor("#ffffff"))
        p.end()

    def mousePressEvent(self, e):
        self._drag_pos = e.globalPosition().toPoint()
    def mouseMoveEvent(self, e):
        if self._drag_pos:
            self.move(self.pos() + e.globalPosition().toPoint() - self._drag_pos)
            self._drag_pos = e.globalPosition().toPoint()
    def mouseReleaseEvent(self, e):
        self._drag_pos = None

    def _build(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(0,0,0,0)
        root.setSpacing(0)

        # LEFT panel
        left = QWidget()
        left.setFixedWidth(420)
        left.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        ll = QVBoxLayout(left)
        ll.setContentsMargins(48,44,48,44)
        ll.setSpacing(0)

        # Top-right row: lang toggle + close
        cr = QHBoxLayout()
        cr.addStretch()

        self.lang_btn = QPushButton(LM.tr("lang_toggle"))
        self.lang_btn.setFixedHeight(28)
        self.lang_btn.setStyleSheet(
            "QPushButton{background:rgba(255,255,255,0.12);color:rgba(255,255,255,0.8);"
            "border:none;border-radius:6px;font-size:11px;padding:0 8px;}"
            "QPushButton:hover{background:rgba(255,255,255,0.25);color:white;}")
        self.lang_btn.clicked.connect(LM.toggle)
        cr.addWidget(self.lang_btn)
        cr.addSpacing(6)

        cb = QPushButton("✕")
        cb.setFixedSize(28,28)
        cb.setStyleSheet(
            "QPushButton{background:rgba(255,255,255,0.1);color:rgba(255,255,255,0.6);"
            "border:none;border-radius:14px;font-size:12px;}"
            "QPushButton:hover{background:rgba(255,255,255,0.25);color:white;}")
        cb.clicked.connect(self.close)
        cr.addWidget(cb)
        ll.addLayout(cr)
        ll.addSpacing(20)

        icon = QLabel("🌿")
        icon.setStyleSheet("font-size:38px;background:transparent;")
        ll.addWidget(icon)
        ll.addSpacing(14)

        brand = QLabel("AgroSense")
        brand.setStyleSheet(
            "color:#ffffff;font-size:30px;font-weight:800;font-family:'Segoe UI';"
            "background:transparent;letter-spacing:-0.5px;")
        ll.addWidget(brand)
        ll.addSpacing(6)

        self.tag_lbl = QLabel(LM.tr("login_tagline"))
        self.tag_lbl.setStyleSheet(
            "color:rgba(255,255,255,0.6);font-size:14px;font-family:'Segoe UI';"
            "background:transparent;line-height:1.6;")
        ll.addWidget(self.tag_lbl)
        ll.addSpacing(32)

        feats = [
            ("🛰", "Real-time Sentinel-2 imagery"),
            ("🌿", "AI crop stress detection"),
            ("💧", "Smart irrigation planning"),
            ("📈", "Yield prediction & analytics"),
        ]
        self._feat_lbls = []
        for ico, txt in feats:
            row = QHBoxLayout(); row.setSpacing(10)
            i = QLabel(ico); i.setFixedWidth(22)
            i.setStyleSheet("font-size:13px;background:transparent;")
            t = QLabel(txt)
            t.setStyleSheet(
                "color:rgba(255,255,255,0.7);font-size:12.5px;"
                "font-family:'Segoe UI';background:transparent;")
            row.addWidget(i); row.addWidget(t); row.addStretch()
            ll.addLayout(row)
            ll.addSpacing(8)
            self._feat_lbls.append(t)

        ll.addStretch()
        ver = QLabel("v1.0.0  ·  SMIU FYP 2025–2026")
        ver.setStyleSheet("color:rgba(255,255,255,0.25);font-size:10px;background:transparent;")
        ll.addWidget(ver)
        root.addWidget(left)

        # RIGHT panel
        right = QWidget()
        right.setStyleSheet("QWidget{background:#ffffff;}")
        rl = QVBoxLayout(right)
        rl.setContentsMargins(52,0,52,0)
        rl.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        rl.setSpacing(0)

        def lbl(text, size=13, color="#374151", bold=False, mt=0, mb=0):
            l = QLabel(text)
            w = "700" if bold else "400"
            l.setStyleSheet(
                f"color:{color};font-size:{size}px;font-weight:{w};"
                f"font-family:'Segoe UI';background:transparent;"
                f"margin-top:{mt}px;margin-bottom:{mb}px;")
            return l

        self.welcome_lbl = lbl(LM.tr("welcome_back"), 26, "#111827", True, mb=4)
        rl.addWidget(self.welcome_lbl)
        self.subtitle_lbl = lbl(LM.tr("signin_subtitle"), 13, "#6b7280", mb=28)
        rl.addWidget(self.subtitle_lbl)

        # Error frame
        self.err_frame = QFrame()
        self.err_frame.setStyleSheet(
            "QFrame{background:#fef2f2;border:1.5px solid #fecaca;border-radius:9px;}")
        efl = QHBoxLayout(self.err_frame)
        efl.setContentsMargins(12,9,12,9)
        self.err_lbl = QLabel("")
        self.err_lbl.setStyleSheet(
            "color:#dc2626;font-size:12.5px;font-family:'Segoe UI';background:transparent;")
        efl.addWidget(QLabel("⚠  ")); efl.addWidget(self.err_lbl, 1)
        self.err_frame.hide()
        rl.addWidget(self.err_frame)
        rl.addSpacing(4)

        inp_style = """
            QLineEdit{border:1.5px solid #d1d5db;border-radius:10px;padding:0 14px;
                      font-size:13px;font-family:'Segoe UI';color:#111827;background:#f9fafb;}
            QLineEdit:focus{border-color:#1a6b35;background:#ffffff;}
            QLineEdit:hover{border-color:#9ca3af;}
        """

        self.email_field_lbl = lbl(LM.tr("email_label_login"), 12.5, "#374151", True, mb=5)
        rl.addWidget(self.email_field_lbl)
        self.email_in = QLineEdit()
        self.email_in.setPlaceholderText("ali@agrosense.pk")
        self.email_in.setFixedHeight(44)
        self.email_in.setStyleSheet(inp_style)
        rl.addWidget(self.email_in)
        rl.addSpacing(14)

        self.pw_field_lbl = lbl(LM.tr("password_label_login"), 12.5, "#374151", True, mb=5)
        rl.addWidget(self.pw_field_lbl)
        self.pw_in = QLineEdit()
        self.pw_in.setPlaceholderText("Enter your password")
        self.pw_in.setEchoMode(QLineEdit.EchoMode.Password)
        self.pw_in.setFixedHeight(44)
        self.pw_in.setStyleSheet(inp_style)
        self.pw_in.returnPressed.connect(self._do_login)
        rl.addWidget(self.pw_in)
        rl.addSpacing(22)

        self.login_btn = QPushButton(LM.tr("signin_btn"))
        self.login_btn.setFixedHeight(46)
        self.login_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.login_btn.setStyleSheet("""
            QPushButton{background:#1a6b35;color:white;border:none;border-radius:10px;
                        font-size:14px;font-weight:600;font-family:'Segoe UI';}
            QPushButton:hover{background:#145a2b;}
            QPushButton:pressed{background:#0f4520;}
            QPushButton:disabled{background:#9ca3af;}
        """)
        self.login_btn.clicked.connect(self._do_login)
        rl.addWidget(self.login_btn)
        rl.addSpacing(16)

        drow = QHBoxLayout()
        for _ in range(2):
            ln = QFrame(); ln.setFrameShape(QFrame.Shape.HLine)
            ln.setStyleSheet("background:#e5e7eb;border:none;max-height:1px;")
            drow.addWidget(ln, 1)
        self.or_lbl = QLabel(LM.tr("or_divider"))
        self.or_lbl.setStyleSheet("color:#9ca3af;font-size:11px;background:transparent;")
        drow.insertWidget(1, self.or_lbl)
        rl.addLayout(drow)
        rl.addSpacing(16)

        self.reg_btn = QPushButton(LM.tr("create_account_link"))
        self.reg_btn.setFixedHeight(42)
        self.reg_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.reg_btn.setStyleSheet("""
            QPushButton{background:#f0fdf4;color:#1a6b35;border:1.5px solid #bbf7d0;
                        border-radius:10px;font-size:13px;font-weight:500;font-family:'Segoe UI';}
            QPushButton:hover{background:#dcfce7;border-color:#86efac;}
        """)
        self.reg_btn.clicked.connect(self._show_register)
        rl.addWidget(self.reg_btn)
        root.addWidget(right, 1)

    def _retranslate(self):
        self.lang_btn.setText(LM.tr("lang_toggle"))
        self.tag_lbl.setText(LM.tr("login_tagline"))
        self.welcome_lbl.setText(LM.tr("welcome_back"))
        self.subtitle_lbl.setText(LM.tr("signin_subtitle"))
        self.email_field_lbl.setText(LM.tr("email_label_login"))
        self.pw_field_lbl.setText(LM.tr("password_label_login"))
        if self.login_btn.isEnabled():
            self.login_btn.setText(LM.tr("signin_btn"))
        self.or_lbl.setText(LM.tr("or_divider"))
        self.reg_btn.setText(LM.tr("create_account_link"))

    def _do_login(self):
        email = self.email_in.text().strip()
        pw    = self.pw_in.text()
        if not email or not pw:
            self._show_error(LM.tr("enter_credentials"))
            return
        self.login_btn.setEnabled(False)
        self.login_btn.setText(LM.tr("signing_in"))
        self.err_frame.hide()
        self._worker = LoginWorker(email, pw)
        self._worker.success.connect(self._on_success)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_success(self, token, user):
        self.login_btn.setEnabled(True)
        self.login_btn.setText(LM.tr("signin_btn"))
        self.login_success.emit(user)

    def _on_error(self, msg):
        self.login_btn.setEnabled(True)
        self.login_btn.setText(LM.tr("signin_btn"))
        self._show_error(LM.tr("invalid_login"))

    def _show_error(self, msg):
        self.err_lbl.setText(msg)
        self.err_frame.show()

    def _show_register(self):
        from desktop.windows.register import RegisterWindow
        self._reg = RegisterWindow()
        self._reg.show()
```

- [ ] **Step 4.2 — Launch app and verify login window**

```bash
python desktop/main.py
```

- Login window shows `🌐 اردو` button top-left of green panel
- Click it → all login text switches to Urdu, layout flips RTL
- Click again → back to English

- [ ] **Step 4.3 — Commit**

```bash
git add desktop/windows/login.py
git commit -m "feat: add Urdu language toggle to login window with RTL support"
```

---

## Task 5: Add `_retranslate()` to `RegisterWindow`

**Files:**
- Modify: `desktop/windows/register.py`

- [ ] **Step 5.1 — Rewrite `desktop/windows/register.py`**

Replace the entire file:

```python
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QFrame, QComboBox, QMessageBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
import desktop.api as api
from desktop.i18n import LM

T="#111827"; G="#1a6b35"; B="#e2e8e4"; W="#ffffff"; R="#dc2626"; M="#6b7280"

def inp(ph="", pw=False):
    i = QLineEdit()
    i.setPlaceholderText(ph)
    i.setFixedHeight(42)
    if pw: i.setEchoMode(QLineEdit.EchoMode.Password)
    i.setStyleSheet(
        f"QLineEdit{{color:{T};background:{W};border:1.5px solid {B};"
        f"border-radius:9px;padding:0 14px;font-size:13px;font-family:'Segoe UI';}}"
        f"QLineEdit:focus{{border-color:{G};}}")
    return i

def mk_lbl(text, size=13, color="#374151", bold=False):
    l = QLabel(text)
    l.setStyleSheet(
        f"color:{color};font-size:{size}px;"
        f"font-weight:{'700' if bold else '400'};"
        f"background:transparent;font-family:'Segoe UI';")
    return l


class RegWorker(QThread):
    success = pyqtSignal()
    error   = pyqtSignal(str)
    def __init__(self, name, email, password, role):
        super().__init__()
        self.name=name; self.email=email
        self.password=password; self.role=role
    def run(self):
        try:
            api.register(self.name, self.email, self.password, self.role)
            self.success.emit()
        except Exception as e:
            self.error.emit(str(e))


class RegisterWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(LM.tr("reg_window_title"))
        self.setFixedSize(460, 560)
        self.setStyleSheet("background:#0b1f10;")
        self._build()
        LM.language_changed.connect(self._retranslate)

    def _build(self):
        root = QVBoxLayout(self)
        root.setAlignment(Qt.AlignmentFlag.AlignCenter)

        card = QFrame()
        card.setStyleSheet(f"QFrame{{background:{W};border-radius:16px;}}")
        card.setFixedWidth(400)
        cl = QVBoxLayout(card)
        cl.setContentsMargins(40,32,40,32)
        cl.setSpacing(0)

        self.title_lbl = mk_lbl(LM.tr("create_account_title"), 22, T, True)
        cl.addWidget(self.title_lbl)
        cl.addSpacing(4)
        self.sub_lbl = mk_lbl(LM.tr("monitor_crops"), 13, M)
        cl.addWidget(self.sub_lbl)
        cl.addSpacing(24)

        self.err = QLabel("")
        self.err.setStyleSheet(
            f"color:{R};background:#fef2f2;border:1px solid #fecaca;"
            f"border-radius:8px;padding:8px 12px;font-size:12px;font-family:'Segoe UI';")
        self.err.hide()
        cl.addWidget(self.err)
        cl.addSpacing(4)

        self.inputs = {}
        self._field_lbls = {}
        for label_key, key, ph, pw in [
            ("full_name_label",     "name",     "Ali Hassan",       False),
            ("email_reg_label",     "email",    "ali@agrosense.pk", False),
            ("password_reg_label",  "password", "min 8 characters", True),
        ]:
            lbl_w = mk_lbl(LM.tr(label_key), 12, "#374151", True)
            cl.addWidget(lbl_w)
            cl.addSpacing(4)
            i = inp(ph, pw)
            cl.addWidget(i)
            cl.addSpacing(12)
            self.inputs[key] = i
            self._field_lbls[label_key] = lbl_w

        self.role_lbl = mk_lbl(LM.tr("role_label"), 12, "#374151", True)
        cl.addWidget(self.role_lbl)
        cl.addSpacing(4)
        self.role = QComboBox()
        self.role.addItems(["farmer","analyst","admin"])
        self.role.setFixedHeight(42)
        self.role.setStyleSheet(f"""
            QComboBox{{color:{T};background:{W};border:1.5px solid {B};border-radius:9px;
                       padding:0 14px;font-size:13px;font-family:'Segoe UI';}}
            QComboBox QAbstractItemView{{color:{T};background:{W};border:1px solid {B};}}
            QComboBox QAbstractItemView::item{{color:{T};padding:8px;background:{W};}}
            QComboBox QAbstractItemView::item:hover{{background:#e8f5ee;}}
        """)
        cl.addWidget(self.role)
        cl.addSpacing(20)

        self.btn = QPushButton(LM.tr("create_account_btn"))
        self.btn.setFixedHeight(46)
        self.btn.setStyleSheet(f"""
            QPushButton{{background:{G};color:white;border:none;border-radius:10px;
                         font-size:14px;font-weight:600;font-family:'Segoe UI';}}
            QPushButton:hover{{background:#145a2b;}}
            QPushButton:disabled{{background:#9ca3af;}}
        """)
        self.btn.clicked.connect(self._register)
        cl.addWidget(self.btn)

        root.addWidget(card)

    def _retranslate(self):
        self.setWindowTitle(LM.tr("reg_window_title"))
        self.title_lbl.setText(LM.tr("create_account_title"))
        self.sub_lbl.setText(LM.tr("monitor_crops"))
        for label_key, lbl_w in self._field_lbls.items():
            lbl_w.setText(LM.tr(label_key))
        self.role_lbl.setText(LM.tr("role_label"))
        if self.btn.isEnabled():
            self.btn.setText(LM.tr("create_account_btn"))

    def _register(self):
        name  = self.inputs["name"].text().strip()
        email = self.inputs["email"].text().strip()
        pw    = self.inputs["password"].text()
        role  = self.role.currentText()
        if not all([name, email, pw]):
            self.err.setText(LM.tr("all_fields_required"))
            self.err.show(); return
        self.btn.setEnabled(False)
        self.btn.setText(LM.tr("creating_account"))
        self._w = RegWorker(name, email, pw, role)
        self._w.success.connect(self._ok)
        self._w.error.connect(self._fail)
        self._w.start()

    def _ok(self):
        self.btn.setEnabled(True)
        self.btn.setText(LM.tr("create_account_btn"))
        QMessageBox.information(self, LM.tr("success_title"), LM.tr("reg_success_msg"))
        self.close()

    def _fail(self, msg):
        self.btn.setEnabled(True)
        self.btn.setText(LM.tr("create_account_btn"))
        self.err.setText(f"Error: {msg}")
        self.err.show()
```

- [ ] **Step 5.2 — Commit**

```bash
git add desktop/windows/register.py
git commit -m "feat: add Urdu retranslation support to RegisterWindow"
```

---

## Task 6: Language toggle button in `MainWindow` topbar + `_retranslate()`

**Files:**
- Modify: `desktop/windows/main_window.py`

- [ ] **Step 6.1 — Rewrite `desktop/windows/main_window.py`**

Replace the entire file:

```python
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QLabel, QPushButton, QFrame, QStackedWidget, QScrollArea
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QPainter, QLinearGradient, QBrush

from desktop.pages.dashboard import DashboardPage
from desktop.pages.farms     import FarmsPage
from desktop.pages.imagery   import ImageryPage
from desktop.pages.analytics import AnalyticsPage
from desktop.pages.map_view  import MapPage
from desktop.pages.band_view import BandViewPage
from desktop.i18n import LM
import desktop.api as api

NAV = [
    ("dashboard", "nav_dashboard", DashboardPage),
    ("farms",     "nav_farms",     FarmsPage),
    ("imagery",   "nav_imagery",   ImageryPage),
    ("analytics", "nav_analytics", AnalyticsPage),
    ("map",       "nav_map",       MapPage),
    ("bands",     "nav_bands",     BandViewPage),
]

G = "#1a6b35"; GB = "#0d2414"; W = "#ffffff"; P = "#f4f6f4"
T = "#111827"; M = "#6b7280"; B = "#e2e8e4"


class MainWindow(QMainWindow):
    def __init__(self, user):
        super().__init__()
        self.user = user
        self._current_key = "dashboard"
        self.setWindowTitle("AgroSense — Crop Intelligence")
        self.resize(1200, 760)
        self.setMinimumSize(1000, 650)
        self._btns = {}
        self._pages = {}
        self._build()
        self._go("dashboard")
        LM.language_changed.connect(self._retranslate)

    def _build(self):
        root_w = QWidget()
        root_w.setStyleSheet(f"background:{P};" + """
            QScrollBar:vertical {
                width: 8px; background: #f1f5f1;
                border-radius: 4px; margin: 0;
            }
            QScrollBar::handle:vertical {
                background: #b8d8c4; border-radius: 4px; min-height: 30px;
            }
            QScrollBar::handle:vertical:hover { background: #1a6b35; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: none; }
            QScrollBar:horizontal { height: 0; }
        """)
        self.setCentralWidget(root_w)
        hl = QHBoxLayout(root_w)
        hl.setContentsMargins(0,0,0,0)
        hl.setSpacing(0)
        hl.addWidget(self._sidebar())
        hl.addWidget(self._content(), 1)

    def _sidebar(self):
        sb = QWidget()
        sb.setFixedWidth(220)
        sb.setStyleSheet(f"background:{GB};")
        vl = QVBoxLayout(sb)
        vl.setContentsMargins(0,0,0,0)
        vl.setSpacing(0)

        logo = QWidget()
        logo.setFixedHeight(64)
        logo.setStyleSheet(f"background:{GB}; border-bottom: 1px solid rgba(255,255,255,0.08);")
        ll = QHBoxLayout(logo)
        ll.setContentsMargins(18,0,18,0)
        ic = QLabel("🌿")
        ic.setStyleSheet("font-size:20px; background:transparent; color:white;")
        nm = QLabel("AgroSense")
        nm.setStyleSheet(
            "color:#f0ede6; font-size:15px; font-weight:700; background:transparent;")
        ll.addWidget(ic); ll.addWidget(nm); ll.addStretch()
        vl.addWidget(logo)

        self.sec_lbl = QLabel(LM.tr("main_menu"))
        self.sec_lbl.setStyleSheet(
            "color:#3a6b4a; font-size:9px; font-weight:700; letter-spacing:2px;"
            "padding:14px 20px 6px; background:transparent;")
        vl.addWidget(self.sec_lbl)

        nav = QWidget(); nav.setStyleSheet(f"background:{GB};")
        nl = QVBoxLayout(nav); nl.setContentsMargins(10,0,10,8); nl.setSpacing(2)
        for key, tr_key, Cls in NAV:
            b = QPushButton(LM.tr(tr_key))
            b.setFixedHeight(40)
            b.setStyleSheet(self._ns(False))
            b.clicked.connect(lambda _,k=key: self._go(k))
            nl.addWidget(b)
            self._btns[key] = b
        nl.addStretch()
        vl.addWidget(nav, 1)

        div = QFrame(); div.setFixedHeight(1)
        div.setStyleSheet("background:rgba(255,255,255,0.08);")
        vl.addWidget(div)

        uw = QWidget(); uw.setStyleSheet(f"background:{GB};")
        ul = QVBoxLayout(uw); ul.setContentsMargins(18,12,18,14); ul.setSpacing(3)
        rb = QLabel(f" {self.user.get('role','').upper()} ")
        rb.setFixedWidth(60)
        rb.setAlignment(Qt.AlignmentFlag.AlignCenter)
        rb.setStyleSheet(
            "background:#1a4a2a; color:#4ade80; font-size:9px; font-weight:700;"
            "border-radius:4px; padding:2px 0;")
        nm2 = QLabel(self.user.get("name",""))
        nm2.setStyleSheet(
            "color:#f0ede6; font-size:13px; font-weight:600; background:transparent;")
        em = QLabel(self.user.get("email",""))
        em.setStyleSheet("color:#5a9470; font-size:10px; background:transparent;")
        self.lo_btn = QPushButton(LM.tr("sign_out"))
        self.lo_btn.setStyleSheet(
            "QPushButton{background:transparent;border:none;color:#4a7a5a;font-size:11px;"
            "text-align:left;padding:4px 0;}"
            "QPushButton:hover{color:#f87171;}")
        self.lo_btn.clicked.connect(self._logout)
        ul.addWidget(rb); ul.addSpacing(4)
        ul.addWidget(nm2); ul.addWidget(em); ul.addSpacing(6); ul.addWidget(self.lo_btn)
        vl.addWidget(uw)
        return sb

    def _content(self):
        cw = QWidget(); cw.setStyleSheet(f"background:{P};")
        cl = QVBoxLayout(cw); cl.setContentsMargins(0,0,0,0); cl.setSpacing(0)

        tb = QWidget(); tb.setFixedHeight(54)
        tb.setStyleSheet(f"background:{W}; border-bottom:1px solid {B};")
        tl = QHBoxLayout(tb); tl.setContentsMargins(28,0,28,0)

        self.tb_title = QLabel("Dashboard")
        self.tb_title.setStyleSheet(
            f"color:{T}; font-size:15px; font-weight:600; background:transparent;")
        self.tb_sub = QLabel("Crop intelligence overview")
        self.tb_sub.setStyleSheet(
            f"color:{M}; font-size:12px; background:transparent;")
        self.dot_lbl = QLabel(LM.tr("connected"))
        self.dot_lbl.setStyleSheet("color:#16a34a; font-size:11px; background:transparent;")

        self.lang_toggle_btn = QPushButton(LM.tr("lang_toggle"))
        self.lang_toggle_btn.setFixedHeight(30)
        self.lang_toggle_btn.setStyleSheet(
            f"QPushButton{{background:transparent;color:{M};border:1px solid {B};"
            f"border-radius:7px;font-size:12px;padding:0 10px;}}"
            f"QPushButton:hover{{background:#f3f4f6;color:{T};}}")
        self.lang_toggle_btn.clicked.connect(LM.toggle)

        tl.addWidget(self.tb_title); tl.addSpacing(10)
        tl.addWidget(self.tb_sub); tl.addStretch()
        tl.addWidget(self.lang_toggle_btn); tl.addSpacing(12)
        tl.addWidget(self.dot_lbl)
        cl.addWidget(tb)

        self.stack = QStackedWidget()
        self.stack.setStyleSheet(f"background:{P};")
        for key, _, Cls in NAV:
            pg = Cls()
            wrap = QWidget(); wrap.setStyleSheet(f"background:{P};")
            wl = QVBoxLayout(wrap); wl.setContentsMargins(24,20,24,20)
            wl.addWidget(pg)
            self.stack.addWidget(wrap)
            self._pages[key] = wrap
        cl.addWidget(self.stack, 1)
        return cw

    def _ns(self, active):
        if active:
            return (f"QPushButton{{background:{G};color:white;border:none;border-radius:8px;"
                    f"font-size:13px;text-align:left;padding:0 14px;}}")
        return (f"QPushButton{{background:transparent;color:#7aaa8a;border:none;"
                f"border-radius:8px;font-size:13px;text-align:left;padding:0 14px;}}"
                f"QPushButton:hover{{background:rgba(255,255,255,0.07);color:#c8e6d0;}}")

    _TITLE_KEYS = {
        "dashboard": "topbar_title_dashboard", "farms":     "topbar_title_farms",
        "imagery":   "topbar_title_imagery",   "analytics": "topbar_title_analytics",
        "map":       "topbar_title_map",        "bands":     "topbar_title_bands",
    }
    _SUB_KEYS = {
        "dashboard": "topbar_sub_dashboard", "farms":     "topbar_sub_farms",
        "imagery":   "topbar_sub_imagery",   "analytics": "topbar_sub_analytics",
        "map":       "topbar_sub_map",        "bands":     "topbar_sub_bands",
    }
    _NAV_KEYS = {
        "dashboard": "nav_dashboard", "farms": "nav_farms",
        "imagery":   "nav_imagery",   "analytics": "nav_analytics",
        "map":       "nav_map",       "bands":     "nav_bands",
    }

    def _go(self, key):
        self._current_key = key
        self.tb_title.setText(LM.tr(self._TITLE_KEYS.get(key, key)))
        self.tb_sub.setText(LM.tr(self._SUB_KEYS.get(key, "")))
        if key in self._pages:
            self.stack.setCurrentWidget(self._pages[key])
        for k, b in self._btns.items():
            b.setStyleSheet(self._ns(k == key))

    def _retranslate(self):
        self.lang_toggle_btn.setText(LM.tr("lang_toggle"))
        self.dot_lbl.setText(LM.tr("connected"))
        self.sec_lbl.setText(LM.tr("main_menu"))
        self.lo_btn.setText(LM.tr("sign_out"))
        for key, tr_key, _ in NAV:
            self._btns[key].setText(LM.tr(tr_key))
        self.tb_title.setText(LM.tr(self._TITLE_KEYS.get(self._current_key, self._current_key)))
        self.tb_sub.setText(LM.tr(self._SUB_KEYS.get(self._current_key, "")))

    def _logout(self):
        api.set_token(None)
        from desktop.windows.login import LoginWindow
        self._lw = LoginWindow()
        self._lw.login_success.connect(lambda u: self._reopen(u))
        self._lw.show(); self.close()

    def _reopen(self, user):
        self._lw.close()
        self._new_win = MainWindow(user)
        self._new_win.show()
```

- [ ] **Step 6.2 — Launch app, log in, and verify**

```bash
python desktop/main.py
```

- `🌐 اردو` button visible in topbar, right of "● Connected"
- Clicking toggles all sidebar labels, topbar title/subtitle, sign-out button to Urdu + RTL
- Navigating pages in Urdu mode keeps titles in Urdu

- [ ] **Step 6.3 — Commit**

```bash
git add desktop/windows/main_window.py
git commit -m "feat: add language toggle button to MainWindow topbar with full RTL retranslation"
```

---

## Task 7: Add `_retranslate()` to `DashboardPage`

**Files:**
- Modify: `desktop/pages/dashboard.py`

Key changes: promote stat-title labels to `self._sl[]`; promote analysis card title; connect `LM.language_changed`.

- [ ] **Step 7.1 — Replace the `_build` method and add `_retranslate()` in `DashboardPage`**

Add import at top of file (after existing imports):
```python
from desktop.i18n import LM
```

Replace `_build` entirely:

```python
    def _build(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea{border:none;background:transparent;}")
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        c = QWidget(); c.setStyleSheet(f"background:{P};")
        ml = QVBoxLayout(c); ml.setContentsMargins(0,0,8,0); ml.setSpacing(16)

        # Stats
        sr = QHBoxLayout(); sr.setSpacing(14)
        stat_defs = [
            ("stat_farms",  "—", G),
            ("stat_fields", "—", BLUE),
            ("stat_health", "—", EMERALD),
            ("stat_yield",  "—", GOLD),
        ]
        self._sv = []   # value labels (numbers)
        self._sl = []   # title labels (translatable)
        for key, val, col in stat_defs:
            f = QFrame()
            f.setFixedHeight(110)
            f.setStyleSheet(f"QFrame{{background:{W};border:1px solid {B};border-radius:12px;}}")
            fl = QVBoxLayout(f); fl.setContentsMargins(20,14,20,14)
            tl = lbl(LM.tr(key), 11, M)
            fl.addWidget(tl)
            v = lbl(val, 28, col, True)
            fl.addWidget(v)
            self._sl.append((key, tl))
            self._sv.append(v)
            sr.addWidget(f)
        ml.addLayout(sr)

        # Analysis panel
        af, al = card()
        self.analysis_title_lbl = lbl(LM.tr("analysis_title"), 14, T, True)
        al.addWidget(self.analysis_title_lbl)
        row = QHBoxLayout(); row.setSpacing(10)
        self.combo = QComboBox()
        self.combo.setFixedHeight(40)
        self.combo.setStyleSheet(f"""
            QComboBox{{color:{T};background:{W};border:1.5px solid {B};border-radius:9px;
                       padding:0 12px;font-size:13px;font-family:'Segoe UI';}}
            QComboBox:focus{{border-color:{G};}}
            QComboBox QAbstractItemView{{color:{T};background:{W};border:1px solid {B};
                selection-background-color:{A};outline:0;}}
            QComboBox QAbstractItemView::item{{color:{T};padding:8px 12px;min-height:28px;background:{W};}}
            QComboBox QAbstractItemView::item:hover{{background:{A};color:{T};}}
        """)
        row.addWidget(self.combo, 1)
        self.run_btn = btn(LM.tr("run_analysis"))
        self.run_btn.setFixedWidth(160)
        self.run_btn.clicked.connect(self._run)
        row.addWidget(self.run_btn)

        ref_btn = QPushButton("🔄")
        ref_btn.setFixedSize(44, 40)
        ref_btn.setStyleSheet(
            "QPushButton{background:#374151;color:white;border:none;border-radius:9px;font-size:14px;}"
            "QPushButton:hover{background:#1f2937;}")
        ref_btn.clicked.connect(self._load)
        row.addWidget(ref_btn)
        al.addLayout(row)

        self.err_lbl = lbl("", 12, RED)
        self.err_lbl.hide()
        al.addWidget(self.err_lbl)
        ml.addWidget(af)

        self.pdf_btn = btn(LM.tr("export_pdf"), BLUE, "#1d4ed8")
        self.pdf_btn.setEnabled(False)
        self.pdf_btn.clicked.connect(self._pdf_clicked)
        self.alt_btn = btn(LM.tr("send_alert"), PURPLE, "#6d28d9")
        self.alt_btn.setEnabled(False)
        self.alt_btn.clicked.connect(self._alert_clicked)
        action_row = QHBoxLayout()
        action_row.addWidget(self.pdf_btn)
        action_row.addWidget(self.alt_btn)
        action_row.addStretch()
        ml.addLayout(action_row)

        self.res_f, self.res_l = card()
        self.res_f.hide()
        ml.addWidget(self.res_f)
        ml.addStretch()

        scroll.setWidget(c)
        ol = QVBoxLayout(self); ol.setContentsMargins(0,0,0,0)
        ol.addWidget(scroll)
```

Add the `_retranslate` method and wire it in `__init__`. In `__init__` (after `self._build()` call), add:

```python
        LM.language_changed.connect(self._retranslate)
```

Add `_retranslate` method to the class:

```python
    def _retranslate(self):
        for key, title_lbl in self._sl:
            title_lbl.setText(LM.tr(key))
        self.analysis_title_lbl.setText(LM.tr("analysis_title"))
        if self.run_btn.isEnabled():
            self.run_btn.setText(LM.tr("run_analysis"))
        if self.pdf_btn.isEnabled():
            self.pdf_btn.setText(LM.tr("export_pdf"))
        if self.alt_btn.isEnabled():
            self.alt_btn.setText(LM.tr("send_alert"))
```

Also update `_run` and `_on_result` to use `LM.tr()` for button state text:

```python
    def _run(self):
        fid = self.combo.currentData()
        if not fid: return
        self.run_btn.setEnabled(False)
        self.run_btn.setText(LM.tr("analysing"))
        self.err_lbl.hide()
        w = Worker(api.full_analysis, fid)
        self._workers.append(w)
        w.done.connect(self._on_result)
        w.err.connect(self._on_err)
        w.finished.connect(lambda: self._workers.remove(w) if w in self._workers else None)
        w.start()

    def _on_result(self, d):
        self.run_btn.setEnabled(True)
        self.run_btn.setText(LM.tr("run_analysis"))
        d["field_id"]    = self.combo.currentData()
        d["_token"]      = api.get_token()
        d["_start_date"] = "2024-01-01"
        d["_end_date"]   = "2024-03-01"
        self._last_d = d
        self.pdf_btn.setEnabled(True)
        self.alt_btn.setEnabled(True)
        self._show(d)

    def _on_err(self, msg):
        self.run_btn.setEnabled(True)
        self.run_btn.setText(LM.tr("run_analysis"))
        self.err_lbl.setText(f"⚠  {msg}")
        self.err_lbl.show()

    def _pdf_clicked(self):
        if not self._last_d:
            QMessageBox.information(self, LM.tr("no_data_title"), LM.tr("run_analysis_first"))
            return
        import os, copy
        data  = copy.deepcopy(self._last_d)
        home  = os.path.expanduser("~")
        desk  = os.path.join(home, "Desktop")
        fname = f"AgroSense_{(data.get('field_name') or 'Report').replace(' ','_')}.pdf"
        self._pdf_path = os.path.join(desk if os.path.exists(desk) else home, fname)
        self.pdf_btn.setEnabled(False)
        self.pdf_btn.setText(LM.tr("fetching_pdf"))
        self._pdf_worker = PDFWorker(data, self._pdf_path)
        self._pdf_worker.done.connect(self._on_pdf_done)
        self._pdf_worker.err.connect(self._on_pdf_err)
        self._pdf_worker.start()

    def _on_pdf_done(self, p):
        self.pdf_btn.setEnabled(True)
        self.pdf_btn.setText(LM.tr("export_pdf"))
        QMessageBox.information(self, LM.tr("pdf_ready_title"), f"✅ Report saved!\n\n{p}")

    def _on_pdf_err(self, e):
        self.pdf_btn.setEnabled(True)
        self.pdf_btn.setText(LM.tr("export_pdf"))
        QMessageBox.warning(self, LM.tr("pdf_error_title"), f"❌ {e[:300]}")

    def _alert_clicked(self):
        if not self._last_d:
            return
        try:
            me = api.get_me()
            from desktop.utils.email_alerts import check_and_alert
            import os; from dotenv import load_dotenv; load_dotenv()
            r = check_and_alert(self._last_d, me, os.getenv("ADMIN_EMAIL",""))
            QMessageBox.information(self, LM.tr("alert_title"),
                ("✅  " if r["success"] else "ℹ  ") + r["message"])
        except Exception as e:
            QMessageBox.warning(self, LM.tr("alert_error_title"), str(e))
```

- [ ] **Step 7.2 — Commit**

```bash
git add desktop/pages/dashboard.py
git commit -m "feat: add Urdu retranslation to DashboardPage"
```

---

## Task 8: Add `_retranslate()` to `FarmsPage`

**Files:**
- Modify: `desktop/pages/farms.py`

- [ ] **Step 8.1 — Add import and update `AddFarmDialog` to use `LM.tr()`**

Add at top of file:
```python
from desktop.i18n import LM
```

Replace `AddFarmDialog._build` with a version that uses `LM.tr()` for labels/buttons. The dialog is instantiated fresh each time so it reads `LM.tr()` at creation time automatically (no retranslate needed on dialogs):

```python
    def _build(self):
        l = QVBoxLayout(self); l.setContentsMargins(28,24,28,24); l.setSpacing(10)
        l.addWidget(mk_label(LM.tr("add_farm_dialog_title"), 16, T, True))
        self.inputs = {}
        for label_key, key, ph in [
            ("form_farm_name", "name",      "e.g. Sindh Farm 1"),
            ("form_district",  "district",  "e.g. Hyderabad"),
            ("form_province",  "province",  "e.g. Sindh"),
            ("form_area_ha",   "area_ha",   "e.g. 50"),
            ("form_latitude",  "latitude",  "e.g. 25.396"),
            ("form_longitude", "longitude", "e.g. 68.374"),
        ]:
            l.addWidget(mk_label(LM.tr(label_key), 12, "#374151", True))
            inp = mk_input(ph); l.addWidget(inp); self.inputs[key] = inp
        self.err = mk_label("", 12, R); self.err.hide(); l.addWidget(self.err)
        row = QHBoxLayout()
        cb = QPushButton(LM.tr("cancel_btn"))
        cb.setStyleSheet(f"QPushButton{{background:{A};color:{G};border:1px solid #b8d8c4;border-radius:8px;padding:6px 14px;font-family:'Segoe UI';}}")
        cb.clicked.connect(self.reject)
        self.sb = mk_btn(LM.tr("add_farm_save_btn")); self.sb.clicked.connect(self._save)
        row.addWidget(cb); row.addStretch(); row.addWidget(self.sb)
        l.addLayout(row)
```

Update `AddFarmDialog._save` saving/error state to use `LM.tr()`:
```python
    def _save(self):
        name = self.inputs["name"].text().strip()
        if not name: self.err.setText(LM.tr("form_farm_name") + " required"); self.err.show(); return
        self.sb.setEnabled(False); self.sb.setText(LM.tr("saving_btn"))
        try:
            api.create_farm(name,
                self.inputs["district"].text().strip(),
                self.inputs["province"].text().strip(),
                self.inputs["area_ha"].text() or None,
                self.inputs["latitude"].text() or None,
                self.inputs["longitude"].text() or None)
            self.created.emit(); self.accept()
        except Exception as e:
            self.err.setText(str(e)); self.err.show()
            self.sb.setEnabled(True); self.sb.setText(LM.tr("add_farm_save_btn"))
```

- [ ] **Step 8.2 — Update `AddFieldDialog` to use `LM.tr()`**

Replace `AddFieldDialog._build`:
```python
    def _build(self, farm_name):
        l = QVBoxLayout(self); l.setContentsMargins(28,24,28,24); l.setSpacing(10)
        l.addWidget(mk_label(f"{LM.tr('add_field_dialog_title')} — {farm_name}", 14, T, True))
        self.inputs = {}
        for label_key, key, ph in [
            ("form_field_name", "name",    "e.g. Field A"),
            ("form_area_ha",    "area_ha", "e.g. 10"),
        ]:
            l.addWidget(mk_label(LM.tr(label_key), 12, "#374151", True))
            inp = mk_input(ph); l.addWidget(inp); self.inputs[key] = inp

        l.addWidget(mk_label(LM.tr("form_crop_type"), 12, "#374151", True))
        self.crop_combo = QComboBox()
        self.crop_combo.addItems(["wheat", "rice", "cotton", "sugarcane", "mango"])
        self.crop_combo.setFixedHeight(38)
        self.crop_combo.setStyleSheet(f"""
            QComboBox{{color:{T};background:{W};border:1.5px solid {B};border-radius:8px;
                       padding:0 12px;font-size:13px;font-family:'Segoe UI';}}
            QComboBox:focus{{border-color:{G};}}
            QComboBox::drop-down{{border:none;width:28px;}}
            QComboBox QAbstractItemView{{color:{T};background:{W};selection-background-color:{A};
                                         border:1px solid {B};font-size:13px;}}
        """)
        l.addWidget(self.crop_combo)
        self.err = mk_label("", 12, R); self.err.hide(); l.addWidget(self.err)
        row = QHBoxLayout()
        cb = QPushButton(LM.tr("cancel_btn"))
        cb.setStyleSheet(f"QPushButton{{background:{A};color:{G};border:1px solid #b8d8c4;border-radius:8px;padding:6px 14px;font-family:'Segoe UI';}}")
        cb.clicked.connect(self.reject)
        self.sb = mk_btn(LM.tr("add_field_save_btn")); self.sb.clicked.connect(self._save)
        row.addWidget(cb); row.addStretch(); row.addWidget(self.sb)
        l.addLayout(row)
```

- [ ] **Step 8.3 — Add `_retranslate()` to `FarmsPage` and connect it**

In `FarmsPage.__init__` (after all existing init code), promote the header buttons to `self.*` and add the connection. The header already stores `self.sel_lbl`, `self.add_field_btn`, `self.del_farm_btn`, `self.farm_tbl`, `self.field_tbl`.

Find and update the `_build` method's `Fields` section label to store a reference:

```python
        fhr = QHBoxLayout()
        self.fields_section_lbl = mk_label(LM.tr("fields_section"), 14, T, True)
        fhr.addWidget(self.fields_section_lbl)
        fhr.addStretch()
        self.add_field_btn = mk_btn(LM.tr("add_field_btn"), w=130)
        self.add_field_btn.setEnabled(False)
        self.add_field_btn.clicked.connect(self._add_field)
        fhr.addWidget(self.add_field_btn); l.addLayout(fhr)
```

Also update the `+ Add Farm` and `🗑 Delete Farm` buttons in the header to use `LM.tr()`:

```python
        add_btn = mk_btn(LM.tr("add_farm_btn"), w=120)
        add_btn.clicked.connect(self._add_farm)
        hr.addWidget(add_btn)
        self.del_farm_btn = mk_btn(LM.tr("del_farm_btn"), color="#dc2626", w=150)
```

Update table headers in `_build` to use `LM.tr()`:

```python
        self.farm_tbl.setHorizontalHeaderLabels([
            LM.tr("farm_tbl_name"), LM.tr("farm_tbl_district"),
            LM.tr("farm_tbl_province"), LM.tr("farm_tbl_area"),
        ])
        ...
        self.field_tbl.setHorizontalHeaderLabels([
            LM.tr("field_tbl_name"), LM.tr("field_tbl_crop"),
            LM.tr("field_tbl_area"), LM.tr("field_tbl_id"),
        ])
```

Add at end of `FarmsPage.__init__` (after `self._build()` and `self._load_farms()`):

```python
        LM.language_changed.connect(self._retranslate)
```

Add the `_retranslate` method:

```python
    def _retranslate(self):
        self.fields_section_lbl.setText(LM.tr("fields_section"))
        self.add_field_btn.setText(LM.tr("add_field_btn"))
        self.del_farm_btn.setText(LM.tr("del_farm_btn"))
        self.farm_tbl.setHorizontalHeaderLabels([
            LM.tr("farm_tbl_name"), LM.tr("farm_tbl_district"),
            LM.tr("farm_tbl_province"), LM.tr("farm_tbl_area"),
        ])
        self.field_tbl.setHorizontalHeaderLabels([
            LM.tr("field_tbl_name"), LM.tr("field_tbl_crop"),
            LM.tr("field_tbl_area"), LM.tr("field_tbl_id"),
        ])
```

Also update `_del_farm` to use `LM.tr()`:

```python
    def _del_farm(self, farm_id):
        if QMessageBox.question(self, LM.tr("del_farm_dialog"),
            LM.tr("del_farm_confirm"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        ) == QMessageBox.StandardButton.Yes:
            try:
                api.delete_farm(farm_id)
                if self._selected_farm_id == farm_id:
                    self._selected_farm_id = None
                    self._selected_farm_name = ""
                    self.add_field_btn.setEnabled(False)
                    self.del_farm_btn.setEnabled(False)
                    self.field_tbl.setRowCount(0)
                self._load_farms()
            except Exception as e:
                QMessageBox.warning(self, LM.tr("error_title") if "error_title" in LM.tr("error_title") else "Error", str(e))
```

Update `_add_field` message box:
```python
    def _add_field(self):
        if not self._selected_farm_id:
            QMessageBox.information(self, LM.tr("no_farm_sel_title"), LM.tr("no_farm_sel_msg"))
            return
        d = AddFieldDialog(self._selected_farm_id, self._selected_farm_name, self)
        d.created.connect(lambda: self._load_fields(self._selected_farm_id))
        d.exec()
```

- [ ] **Step 8.4 — Commit**

```bash
git add desktop/pages/farms.py
git commit -m "feat: add Urdu retranslation to FarmsPage and dialogs"
```

---

## Task 9: Add `_retranslate()` to `ImageryPage`

**Files:**
- Modify: `desktop/pages/imagery.py`

- [ ] **Step 9.1 — Add import + promote labels + connect + add `_retranslate()`**

Add at top:
```python
from desktop.i18n import LM
```

In `_build`, promote all form labels to instance variables. Replace the config card section:

```python
        cl.addWidget(lbl("📡  Configure Satellite Analysis", 14, T, True))
```
becomes:
```python
        self.config_title_lbl = lbl(LM.tr("imagery_config"), 14, T, True)
        cl.addWidget(self.config_title_lbl)
```

Replace form row labels (store as instance vars):
```python
        r1 = QHBoxLayout(); r1.setSpacing(12)
        self.farm_lbl = lbl(LM.tr("farm_label"), 12, M, True)
        r1.addWidget(self.farm_lbl)
        self.farm_combo = QComboBox()
        self.farm_combo.setFixedHeight(38)
        self.farm_combo.setStyleSheet(combo_style())
        self.farm_combo.currentIndexChanged.connect(self._on_farm)
        r1.addWidget(self.farm_combo, 1)
        self.field_label_lbl = lbl(LM.tr("field_label"), 12, M, True)
        r1.addWidget(self.field_label_lbl)
        self.field_combo = QComboBox()
        self.field_combo.setFixedHeight(38)
        self.field_combo.setEnabled(False)
        self.field_combo.setStyleSheet(combo_style())
        r1.addWidget(self.field_combo, 1)
        cl.addLayout(r1)

        r2 = QHBoxLayout(); r2.setSpacing(12)
        self.start_lbl = lbl(LM.tr("start_label"), 12, M, True)
        r2.addWidget(self.start_lbl)
        self.start = QDateEdit(QDate(2024,1,1))
        self.start.setFixedHeight(38); self.start.setCalendarPopup(True)
        self.start.setStyleSheet(date_style())
        r2.addWidget(self.start)
        self.end_lbl = lbl(LM.tr("end_label"), 12, M, True)
        r2.addWidget(self.end_lbl)
        self.end = QDateEdit(QDate(2024,3,1))
        self.end.setFixedHeight(38); self.end.setCalendarPopup(True)
        self.end.setStyleSheet(date_style())
        r2.addWidget(self.end)
        self.cloud_lbl = lbl(LM.tr("max_cloud_label"), 12, M, True)
        r2.addWidget(self.cloud_lbl)
        self.cloud = QDoubleSpinBox()
        self.cloud.setRange(0,100); self.cloud.setValue(30)
        self.cloud.setFixedHeight(38); self.cloud.setSuffix(" %")
        self.cloud.setStyleSheet(spin_style())
        r2.addWidget(self.cloud)
        cl.addLayout(r2)
```

Update `run_btn` text to use `LM.tr()`:
```python
        self.run_btn = QPushButton(LM.tr("fetch_analyse"))
```

Store the results title and history title labels:
```python
        self.res_l.addWidget(lbl("📊  Latest Results", 14, T, True))
```
becomes:
```python
        self.results_title_lbl = lbl(LM.tr("imagery_results_title"), 14, T, True)
        self.res_l.addWidget(self.results_title_lbl)
```

```python
        hl.addWidget(lbl("📅  Index History", 14, T, True))
```
becomes:
```python
        self.history_title_lbl = lbl(LM.tr("index_history_title"), 14, T, True)
        hl.addWidget(self.history_title_lbl)
```

Update history table headers:
```python
        self.hist.setHorizontalHeaderLabels([
            LM.tr("tbl_date"), LM.tr("tbl_ndvi"), LM.tr("tbl_evi"),
            LM.tr("tbl_ndwi"), LM.tr("tbl_ndre"), LM.tr("tbl_lai"),
        ])
```

In `__init__`, after `self._build()` and `self._load_farms()`, add:
```python
        LM.language_changed.connect(self._retranslate)
```

Add `_retranslate` method:
```python
    def _retranslate(self):
        self.config_title_lbl.setText(LM.tr("imagery_config"))
        self.farm_lbl.setText(LM.tr("farm_label"))
        self.field_label_lbl.setText(LM.tr("field_label"))
        self.start_lbl.setText(LM.tr("start_label"))
        self.end_lbl.setText(LM.tr("end_label"))
        self.cloud_lbl.setText(LM.tr("max_cloud_label"))
        if self.run_btn.isEnabled():
            self.run_btn.setText(LM.tr("fetch_analyse"))
        self.results_title_lbl.setText(LM.tr("imagery_results_title"))
        self.history_title_lbl.setText(LM.tr("index_history_title"))
        self.hist.setHorizontalHeaderLabels([
            LM.tr("tbl_date"), LM.tr("tbl_ndvi"), LM.tr("tbl_evi"),
            LM.tr("tbl_ndwi"), LM.tr("tbl_ndre"), LM.tr("tbl_lai"),
        ])
```

Update `_run`, `_on_result`, `_on_err` to use `LM.tr()` for dynamic text:
```python
    def _run(self):
        fid = self.field_combo.currentData()
        if not fid:
            self.status.setText(LM.tr("select_field_msg"))
            self.status.setStyleSheet(f"color:{R};font-size:12px;background:transparent;")
            return
        self.run_btn.setEnabled(False)
        self.run_btn.setText(LM.tr("fetching_gee_btn"))
        self.status.setStyleSheet(f"color:{M};font-size:12px;background:transparent;")
        self.status.setText(LM.tr("gee_contact"))
        start = self.start.date().toString("yyyy-MM-dd")
        end   = self.end.date().toString("yyyy-MM-dd")
        cloud = self.cloud.value()
        self._rw = Worker(api.analyze_imagery, fid, start, end, cloud)
        self._rw.done.connect(self._on_result)
        self._rw.err.connect(self._on_err)
        self._rw.start()

    def _on_result(self, d):
        self.run_btn.setEnabled(True)
        self.run_btn.setText(LM.tr("fetch_analyse"))
        if d.get("status") == "no_images":
            self.status.setStyleSheet(f"color:{GOLD};font-size:12px;background:transparent;")
            self.status.setText(f"⚠  {d.get('message','No images found')}")
            return
        self.status.setStyleSheet(f"color:{G};font-size:12px;background:transparent;")
        self.status.setText(f"✅  Found {d.get('images_found',0)} images — analysis complete")
        self._show_results(d)
        fid = self.field_combo.currentData()
        self._hw = Worker(api.get_index_history, fid)
        self._hw.done.connect(self._show_history)
        self._hw.start()

    def _on_err(self, msg):
        self.run_btn.setEnabled(True)
        self.run_btn.setText(LM.tr("fetch_analyse"))
        self.status.setStyleSheet(f"color:{R};font-size:12px;background:transparent;")
        self.status.setText(f"❌  {msg}")
```

- [ ] **Step 9.2 — Commit**

```bash
git add desktop/pages/imagery.py
git commit -m "feat: add Urdu retranslation to ImageryPage"
```

---

## Task 10: Add `_retranslate()` to `AnalyticsPage`

**Files:**
- Modify: `desktop/pages/analytics.py`

- [ ] **Step 10.1 — Add import, promote labels, connect, add `_retranslate()`**

Add at top:
```python
from desktop.i18n import LM
```

In `_build`, store the selector labels and history title:

```python
        self.farm_sel_lbl = lbl("Farm:")
        sl.addWidget(self.farm_sel_lbl)
        sl.addWidget(self.farm_combo, 1)
        self.field_sel_lbl = lbl("Field:")
        sl.addWidget(self.field_sel_lbl)
```
becomes:
```python
        self.farm_sel_lbl = lbl(LM.tr("farm_label"))
        sl.addWidget(self.farm_sel_lbl)
        sl.addWidget(self.farm_combo, 1)
        self.field_sel_lbl = lbl(LM.tr("field_label"))
        sl.addWidget(self.field_sel_lbl)
```

Store the history section title:
```python
        t_title = QLabel("📅  Index History")
        t_title.setStyleSheet(...)
        tl.addWidget(t_title)
```
becomes:
```python
        self.hist_title_lbl = QLabel(LM.tr("index_history_title"))
        self.hist_title_lbl.setStyleSheet(
            f"font-size:13.5px;font-weight:600;color:{TEXT};background:transparent;font-family:'Segoe UI';")
        tl.addWidget(self.hist_title_lbl)
```

Update table headers:
```python
        self.table.setHorizontalHeaderLabels([
            LM.tr("tbl_date"), LM.tr("tbl_ndvi"), LM.tr("tbl_evi"),
            LM.tr("tbl_ndwi"), LM.tr("tbl_ndre"), LM.tr("tbl_lai"),
        ])
```

Update `status_lbl` initial text:
```python
        self.status_lbl = QLabel(LM.tr("select_farm_field_msg"))
```

In `__init__`, add after `self._build()` and `self._load_farms()`:
```python
        LM.language_changed.connect(self._retranslate)
```

Add `_retranslate`:
```python
    def _retranslate(self):
        self.farm_sel_lbl.setText(LM.tr("farm_label"))
        self.field_sel_lbl.setText(LM.tr("field_label"))
        self.hist_title_lbl.setText(LM.tr("index_history_title"))
        self.table.setHorizontalHeaderLabels([
            LM.tr("tbl_date"), LM.tr("tbl_ndvi"), LM.tr("tbl_evi"),
            LM.tr("tbl_ndwi"), LM.tr("tbl_ndre"), LM.tr("tbl_lai"),
        ])
```

Update `_render` to use `LM.tr()` for status messages:
```python
    def _render(self, history):
        if not history:
            self.status_lbl.setText(LM.tr("no_history_msg"))
            return
        self.status_lbl.setText(f"{len(history)} data point(s)")
        ...
```

- [ ] **Step 10.2 — Commit**

```bash
git add desktop/pages/analytics.py
git commit -m "feat: add Urdu retranslation to AnalyticsPage"
```

---

## Task 11: Add `_retranslate()` to `MapPage`

**Files:**
- Modify: `desktop/pages/map_view.py`

- [ ] **Step 11.1 — Add import, promote labels, connect, add `_retranslate()`**

Add at top:
```python
from desktop.i18n import LM
```

In `MapPage._build`, store button/label references:

Replace:
```python
        fl = QLabel("🌍  Farm:")
        fl.setStyleSheet("color:#86efac;font-size:13px;font-family:'Segoe UI';background:transparent;font-weight:600;")
```
with:
```python
        self.farm_label = QLabel(LM.tr("map_farm_label"))
        self.farm_label.setStyleSheet("color:#86efac;font-size:13px;font-family:'Segoe UI';background:transparent;font-weight:600;")
```

Replace:
```python
        rst = QPushButton("🔍  Reset")
```
with:
```python
        self.rst_btn = QPushButton(LM.tr("map_reset"))
```
And update `rst.clicked.connect` → `self.rst_btn.clicked.connect`.

Replace:
```python
        cl.addWidget(fl)
        cl.addWidget(self.farm_combo, 1)
        cl.addWidget(ref)
        cl.addWidget(rst)
```
with:
```python
        cl.addWidget(self.farm_label)
        cl.addWidget(self.farm_combo, 1)
        cl.addWidget(ref)
        cl.addWidget(self.rst_btn)
```

Update initial status label text:
```python
        self.status = QLabel(LM.tr("loading_farms"))
```

In `_on_loaded`, update the status message format:
```python
    def _on_loaded(self, farms):
        self.farms = farms
        self.canvas.reset_view()
        self.farm_combo.clear()
        self.farm_combo.addItem(LM.tr("all_farms_opt"), None)
        for f in farms:
            self.farm_combo.addItem(f"📍  {f['name']}", f["id"])
        self.status.setText(
            f"{len(farms)} farm(s) loaded  ·  Click marker to zoom  ·  Scroll to zoom  ·  Drag to pan")
        self.canvas.set_farms(farms)
```

In `MapPage.__init__`, after `self._build()` and `self._load()`, add:
```python
        LM.language_changed.connect(self._retranslate)
```

Add `_retranslate`:
```python
    def _retranslate(self):
        self.farm_label.setText(LM.tr("map_farm_label"))
        self.rst_btn.setText(LM.tr("map_reset"))
```

- [ ] **Step 11.2 — Commit**

```bash
git add desktop/pages/map_view.py
git commit -m "feat: add Urdu retranslation to MapPage"
```

---

## Task 12: Add `_retranslate()` to `BandViewPage`

**Files:**
- Modify: `desktop/pages/band_view.py`

- [ ] **Step 12.1 — Add import, promote labels, connect, add `_retranslate()`**

Add at top:
```python
from desktop.i18n import LM
```

In `BandViewPage._build`, promote the control labels and button:

Replace:
```python
        cl.addWidget(lbl("Field:"))
        cl.addWidget(self.field_combo, 2)
        cl.addWidget(lbl("Start:"))
        cl.addWidget(self.start_date)
        cl.addWidget(lbl("End:"))
        cl.addWidget(self.end_date)
        cl.addWidget(self.fetch_btn)
```
with:
```python
        self.field_lbl = lbl(LM.tr("field_label"))
        cl.addWidget(self.field_lbl)
        cl.addWidget(self.field_combo, 2)
        self.start_lbl = lbl(LM.tr("start_label"))
        cl.addWidget(self.start_lbl)
        cl.addWidget(self.start_date)
        self.end_lbl = lbl(LM.tr("end_label"))
        cl.addWidget(self.end_lbl)
        cl.addWidget(self.end_date)
        cl.addWidget(self.fetch_btn)
```

Update fetch button initial text:
```python
        self.fetch_btn = QPushButton(LM.tr("fetch_bands"))
```

Update status label initial text:
```python
        self.status = QLabel(LM.tr("select_field_fetch"))
```

In `BandViewPage.__init__`, after `self._build()` and `self._load_fields()`, add:
```python
        LM.language_changed.connect(self._retranslate)
```

Add `_retranslate`:
```python
    def _retranslate(self):
        self.field_lbl.setText(LM.tr("field_label"))
        self.start_lbl.setText(LM.tr("start_label"))
        self.end_lbl.setText(LM.tr("end_label"))
        if self.fetch_btn.isEnabled():
            self.fetch_btn.setText(LM.tr("fetch_bands"))
```

Update `_fetch` method to use `LM.tr()`:
```python
    def _fetch(self):
        field_id = self.field_combo.currentData()
        if not field_id:
            self.status.setText(LM.tr("select_field_msg"))
            return
        field = next((f for f in self.fields if f["id"] == field_id), None)
        if not field:
            return
        boundary = self._get_boundary(field)
        date_start = self.start_date.date().toString("yyyy-MM-dd")
        date_end   = self.end_date.date().toString("yyyy-MM-dd")
        self.fetch_btn.setEnabled(False)
        self.fetch_btn.setText(LM.tr("fetching_bands_btn"))
        self.status.setText(
            f"🛰  Fetching {len(COMPOSITES)} band composites from Google Earth Engine...")
        for card in self._cards.values():
            card._set_placeholder()
        self._workers = []
        for comp in COMPOSITES:
            w = BandWorker(comp, field_id, boundary, date_start, date_end)
            w.done.connect(self._on_image)
            w.error.connect(self._on_error)
            w.finished.connect(self._check_done)
            self._workers.append(w)
            w.start()

    def _check_done(self):
        running = sum(1 for w in self._workers if w.isRunning())
        if running == 0:
            self.fetch_btn.setEnabled(True)
            self.fetch_btn.setText(LM.tr("fetch_bands"))
            self.status.setText(f"✅  All {len(COMPOSITES)} band composites loaded!")
```

- [ ] **Step 12.2 — Run the full test suite**

```bash
cd /home/ali/Agrosense/agrosense
python -m pytest tests/test_i18n.py -v
```

Expected: all 8 tests `PASSED`.

- [ ] **Step 12.3 — Full end-to-end manual test**

```bash
python desktop/main.py
```

Go through the spec testing checklist:
- [ ] Toggle button visible in topbar
- [ ] Click once → all UI strings switch to Urdu, sidebar on right, text right-aligned
- [ ] Click again → all UI strings switch to English, sidebar on left
- [ ] Login window has its own language toggle, switching there propagates everywhere
- [ ] Register dialog shows Urdu when Urdu is active
- [ ] Farms page: no UUID in Add Field dialog, Delete Farm button present and functional
- [ ] Map page errors surface as visible status text (not silent)
- [ ] Band View errors surface as visible status text

- [ ] **Step 12.4 — Commit**

```bash
git add desktop/pages/band_view.py
git commit -m "feat: add Urdu retranslation to BandViewPage"
```

- [ ] **Step 12.5 — Final commit tagging the feature complete**

```bash
git add -A
git commit -m "feat: complete Urdu language toggle with RTL layout and 4 bug fixes

- LanguageManager singleton with full EN/UR translation dictionary
- Language toggle in MainWindow topbar and LoginWindow
- RTL layout flip via QApplication.setLayoutDirection
- Urdu font selection with fallback chain
- All 6 pages + Login + Register retranslated
- Bug fixes: UUID debug label, delete-farm button, worker cleanup, silent exceptions"
```

---

## Self-Review Against Spec

| Spec Requirement | Task |
|-----------------|------|
| LanguageManager singleton with `tr()`, `toggle()`, `is_urdu()` | Task 1 |
| Full STRINGS dict (all pages + login + register) | Task 1 |
| Font management (Noto Nastaliq Urdu → Traditional Arabic → fallback) | Task 1 (`_apply_urdu_font`) |
| Toggle button in MainWindow topbar | Task 6 |
| Toggle button also in LoginWindow (pre-login switching) | Task 4 |
| RTL layout via `QApplication.setLayoutDirection` | Task 1 (`toggle()`) |
| `_retranslate()` on all 6 pages | Tasks 7–12 |
| `_retranslate()` on Login + Register | Tasks 4–5 |
| Bug 1 — UUID debug label removed | Task 2 |
| Bug 2 — Delete Farm button wired | Task 2 |
| Bug 3 — Worker cleanup in FarmsPage | Task 2 |
| Bug 4 — Silent exceptions in FarmWorker + LoadWorker | Task 3 |
| Unit tests for LanguageManager | Task 1 |

All spec requirements covered. No TBDs or placeholders.
