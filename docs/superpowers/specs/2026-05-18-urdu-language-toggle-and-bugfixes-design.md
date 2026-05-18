# AgroSense — Urdu Language Toggle & Bug Fixes Design

**Date:** 2026-05-18  
**Author:** Ali Shahmeer  
**Stack:** PyQt6 desktop app

---

## 1. Overview

Add a one-click language toggle button to the AgroSense desktop app that switches the entire UI between English and Urdu, including a full RTL layout flip. Simultaneously fix four confirmed bugs in the existing codebase.

---

## 2. Feature: Urdu Language Toggle

### 2.1 Goals

- A single button in the `MainWindow` topbar switches between English (LTR) and Urdu (RTL).
- Every visible string in all 6 pages, the login window, and the register window is translated.
- Layout direction flips globally via `QApplication.setLayoutDirection()`.
- An appropriate Urdu font (Noto Nastaliq Urdu or Traditional Arabic) is applied when Urdu is active.
- The language preference persists for the session (not across restarts — out of scope).

### 2.2 Architecture

**New file: `desktop/i18n.py`**

```
LanguageManager (singleton)
  Attributes:
    - current_lang: str  ("en" | "ur")
  Signal:
    - language_changed(str)
  Methods:
    - tr(key: str) → str          # returns translated string for current lang
    - toggle()                    # flips lang, updates QApp direction, emits signal
    - is_urdu() → bool

Module-level instance:
  LM = LanguageManager()          # imported as: from desktop.i18n import LM
```

**Translation dictionary** — flat dict inside `i18n.py`, keyed by semantic string ID:

```python
STRINGS = {
    "app_name":          {"en": "AgroSense",            "ur": "ایگرو سینس"},
    "nav_dashboard":     {"en": "🏠  Dashboard",         "ur": "🏠  ڈیش بورڈ"},
    "nav_farms":         {"en": "🗺  Farms & Fields",   "ur": "🗺  کھیت اور زمین"},
    ...  # all UI strings
}
```

Covers: sidebar nav labels, topbar titles/subtitles, page section headings, form labels, button text, table column headers, placeholder text, status messages, error/success messages, dialog titles.

**Font management** — `LanguageManager.toggle()` also calls a helper that sets the app font to `Noto Nastaliq Urdu` (or `Traditional Arabic` as fallback, then system default) when switching to Urdu, and restores `Segoe UI` when switching to English.

### 2.3 Toggle Button

Location: `MainWindow` topbar, right side, next to the "● Connected" status label.

Appearance:
- English active: `🌐 اردو` (click to switch to Urdu)
- Urdu active: `🌐 EN` (click to switch to English)
- Style: secondary outlined button, consistent with existing topbar style.

### 2.4 Data Flow

```
User clicks toggle button
  → LM.toggle()
    → flip current_lang ("en" ↔ "ur")
    → QApplication.instance().setLayoutDirection(RightToLeft | LeftToRight)
    → update app font
    → emit language_changed(new_lang)
      → MainWindow._retranslate()       updates sidebar buttons, topbar
      → DashboardPage._retranslate()    updates all labels/buttons
      → FarmsPage._retranslate()
      → ImageryPage._retranslate()
      → AnalyticsPage._retranslate()
      → MapPage._retranslate()
      → BandViewPage._retranslate()
      → LoginWindow._retranslate()      (if visible)
      → RegisterWindow._retranslate()  (if visible)
```

Each widget connects `LM.language_changed` to its own `_retranslate()` in `__init__`. `_retranslate()` calls `widget.setText(LM.tr("key"))` for every stored label/button reference.

### 2.5 Widget Changes

Every translatable string that is currently a hardcoded string literal becomes a `LM.tr("key")` call. Labels that need retranslation are stored as instance variables (e.g. `self.tb_title`, `self.tb_sub` — already stored in `MainWindow`; others need to be promoted from local variables to `self.*`).

---

## 3. Bug Fixes

### Bug 1 — Farm UUID debug label exposed to user
**File:** `desktop/pages/farms.py`, `AddFieldDialog._build()`, line 94  
**Problem:** `fid_lbl = mk_label(f"Farm ID: {self.farm_id[:8]}...", 10, M)` is added to the dialog, leaking an internal UUID to the user.  
**Fix:** Remove the `fid_lbl` widget and the `l.addWidget(fid_lbl)` call.

### Bug 2 — Delete farm has no UI button
**File:** `desktop/pages/farms.py`  
**Problem:** `_del_farm(farm_id)` method exists but nothing calls it — farms cannot be deleted from the UI.  
**Fix:** Add a "Delete Farm" button to the `FarmsPage` header row. Wire it to `_del_farm(self._selected_farm_id)`. The button is disabled until a farm is selected.

### Bug 3 — Worker threads not cleaned up (memory leak)
**Files:** `desktop/pages/farms.py` (`_load_farms`, `_load_fields`)  
**Problem:** Workers are appended to `self._workers` but no `w.finished.connect` removes them when done. Workers pile up over time.  
**Fix:** Add `w.finished.connect(lambda: self._workers.remove(w) if w in self._workers else None)` to both worker launch sequences, matching the pattern already used in `dashboard.py`.

### Bug 4 — Silent bare `except` blocks swallow errors
**Files:** `desktop/pages/map_view.py` (`FarmWorker.run`), `desktop/pages/band_view.py` (`LoadWorker.run`)  
**Problem:** Bare `except: self.done.emit([])` or `except: self.done.emit([], [])` hide all errors silently.  
**Fix:** Add an `err` signal to both workers. Emit the error message on failure. Connect to a visible status label update in the parent page.

---

## 4. Files Changed

| File | Change |
|------|--------|
| `desktop/i18n.py` | **New** — LanguageManager singleton + full translation dict |
| `desktop/windows/main_window.py` | Add language toggle button to topbar; connect `_retranslate()` |
| `desktop/windows/login.py` | Promote labels to `self.*`; add `_retranslate()` |
| `desktop/windows/register.py` | Promote labels to `self.*`; add `_retranslate()` |
| `desktop/pages/dashboard.py` | Promote labels to `self.*`; add `_retranslate()` |
| `desktop/pages/farms.py` | Bug fixes 1–3; promote labels; add `_retranslate()` |
| `desktop/pages/imagery.py` | Promote labels to `self.*`; add `_retranslate()` |
| `desktop/pages/analytics.py` | Promote labels to `self.*`; add `_retranslate()` |
| `desktop/pages/map_view.py` | Bug fix 4; promote labels; add `_retranslate()` |
| `desktop/pages/band_view.py` | Bug fix 4; promote labels; add `_retranslate()` |

---

## 5. Out of Scope

- Persisting language preference across app restarts (would need QSettings)
- Translating dynamic data from the API (farm names, field names entered by the user)
- Eastern Arabic numerals in Urdu mode
- Adding new translations for languages other than Urdu

---

## 6. Testing Checklist

- [ ] Toggle button visible in topbar
- [ ] Clicking once → all UI strings switch to Urdu, layout flips RTL, sidebar moves right
- [ ] Clicking again → all UI strings switch to English, layout flips LTR, sidebar moves left
- [ ] Login window shows Urdu correctly if toggled before login
- [ ] Register dialog shows Urdu correctly
- [ ] No farm UUID visible in Add Field dialog
- [ ] Delete Farm button appears, is disabled with no selection, enabled after row click
- [ ] Running analysis and switching language mid-session shows no crashes
- [ ] Map page and Band View errors surface as visible messages (not silent failures)
