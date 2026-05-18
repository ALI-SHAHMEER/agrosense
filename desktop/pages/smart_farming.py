from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QPushButton, QComboBox, QScrollArea, QProgressBar, QGridLayout
)
from PyQt6.QtCore import Qt
import desktop.api as api
from desktop.i18n import LM
from desktop.pages.dashboard import Worker, lbl, card

# ── Palette (mirrors dashboard.py exactly) ────────────────────────────────────
G = "#1a6b35"; GB = "#0d2414"; W = "#ffffff"; P = "#f4f6f4"
T = "#111827"; M = "#6b7280"; B = "#e2e8e4"; A = "#e8f5ee"
BLUE = "#2563eb"; PURPLE = "#7c3aed"; GOLD = "#d4a017"
RED = "#dc2626"; EMERALD = "#22c55e"

SEVERITY_COLOR  = {"high": RED,     "medium": GOLD,    "low": EMERALD}
SEVERITY_BG     = {"high": "#fef2f2","medium": "#fffbeb","low": "#f0fdf4"}
SEVERITY_BORDER = {"high": "#fecaca","medium": "#fde68a","low": "#bbf7d0"}

# Simple single-codepoint symbols that render reliably on Linux Qt
CONDITION_ICON = {
    "clear":        "☀",
    "partly_cloudy":"⛅",
    "foggy":        "—",
    "drizzle":      "🌦",
    "rain_showers": "🌧",
    "snow":         "❄",
    "thunderstorm": "⛈",
}


def _combo():
    c = QComboBox()
    c.setFixedHeight(40)
    c.setStyleSheet(f"""
        QComboBox{{color:{T};background:{W};border:1.5px solid {B};border-radius:9px;
                   padding:0 12px;font-size:13px;font-family:'Segoe UI';}}
        QComboBox:focus{{border-color:{G};}}
        QComboBox QAbstractItemView{{color:{T};background:{W};border:1px solid {B};
            selection-background-color:{A};outline:0;}}
        QComboBox QAbstractItemView::item{{color:{T};padding:8px 12px;
            min-height:28px;background:{W};}}
        QComboBox QAbstractItemView::item:hover{{background:{A};color:{T};}}
    """)
    return c


def _stat_card(label, value, color):
    """Matches the dashboard top-stat card exactly."""
    f = QFrame()
    f.setFixedHeight(100)
    f.setStyleSheet(f"QFrame{{background:{W};border:1px solid {B};border-radius:12px;}}")
    fl = QVBoxLayout(f); fl.setContentsMargins(20, 14, 20, 14)
    fl.addWidget(lbl(label, 11, M))
    fl.addWidget(lbl(value, 26, color, True))
    return f


def _result_card(title, main, sub, color):
    """Matches the rcard() helper from dashboard.py."""
    f = QFrame()
    f.setStyleSheet(f"QFrame{{background:{W};border:1px solid {B};border-radius:10px;}}")
    fl = QVBoxLayout(f); fl.setContentsMargins(16, 14, 16, 14); fl.setSpacing(5)
    fl.addWidget(lbl(title, 11, M, True))
    fl.addWidget(lbl(main,  18, color, True))
    fl.addWidget(lbl(sub,   11, M, False, True))
    return f


class SmartFarmingPage(QWidget):
    def __init__(self):
        super().__init__()
        self.setStyleSheet(f"background:{P};")
        self._farms   = []
        self._workers = []
        self._data    = None
        self._build()
        self._load_farms()
        LM.language_changed.connect(self._retranslate)

    # ── Layout ────────────────────────────────────────────────────────────────

    def _build(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea{border:none;background:transparent;}")
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        c = QWidget(); c.setStyleSheet(f"background:{P};")
        ml = QVBoxLayout(c); ml.setContentsMargins(0, 0, 8, 0); ml.setSpacing(16)

        # ── Selector card ────────────────────────────────────────────────────
        sf, sl = card()
        self.title_lbl = lbl(LM.tr("smart_title"), 14, T, True)
        sl.addWidget(self.title_lbl)
        sel_row = QHBoxLayout(); sel_row.setSpacing(10)
        self.farm_combo  = _combo(); self.farm_combo.setFixedWidth(210)
        self.farm_combo.currentIndexChanged.connect(self._on_farm_changed)
        self.field_combo = _combo(); self.field_combo.setFixedWidth(230)
        self.refresh_btn = QPushButton("🔄")
        self.refresh_btn.setFixedSize(44, 40)
        self.refresh_btn.setStyleSheet(
            "QPushButton{background:#374151;color:white;border:none;"
            "border-radius:9px;font-size:14px;}"
            "QPushButton:hover{background:#1f2937;}"
            "QPushButton:disabled{background:#9ca3af;}")
        self.refresh_btn.clicked.connect(self._fetch)
        sel_row.addWidget(lbl("Farm:", 12, M))
        sel_row.addWidget(self.farm_combo)
        sel_row.addWidget(lbl("Field:", 12, M))
        sel_row.addWidget(self.field_combo)
        sel_row.addWidget(self.refresh_btn)
        sel_row.addStretch()
        sl.addLayout(sel_row)
        self.status_lbl = lbl("", 12, M); self.status_lbl.hide()
        sl.addWidget(self.status_lbl)
        ml.addWidget(sf)

        # ── Alerts ───────────────────────────────────────────────────────────
        self.alerts_frame, self.alerts_layout = card()
        self.alerts_title_lbl = lbl(LM.tr("alerts_title"), 14, T, True)
        self.alerts_layout.addWidget(self.alerts_title_lbl)
        self.alerts_row = QHBoxLayout(); self.alerts_row.setSpacing(10)
        self.alerts_layout.addLayout(self.alerts_row)
        ml.addWidget(self.alerts_frame)

        # ── 7-Day Forecast ───────────────────────────────────────────────────
        self.forecast_frame, self.forecast_layout = card()
        self.forecast_title_lbl = lbl(LM.tr("forecast_title"), 14, T, True)
        self.forecast_layout.addWidget(self.forecast_title_lbl)
        self.forecast_row = QHBoxLayout(); self.forecast_row.setSpacing(8)
        self.forecast_layout.addLayout(self.forecast_row)
        ml.addWidget(self.forecast_frame)

        # ── Planting rec + ML summary ─────────────────────────────────────
        bot_row = QHBoxLayout(); bot_row.setSpacing(12)

        self.planting_frame, self.planting_layout = card()
        self.planting_title_lbl = lbl(LM.tr("planting_rec_title"), 14, T, True)
        self.planting_layout.addWidget(self.planting_title_lbl)
        self.planting_body = QVBoxLayout(); self.planting_body.setSpacing(10)
        self.planting_layout.addLayout(self.planting_body)
        bot_row.addWidget(self.planting_frame, 1)

        self.ml_frame, self.ml_layout = card()
        self.ml_title_lbl = lbl(LM.tr("ml_summary_title"), 14, T, True)
        self.ml_layout.addWidget(self.ml_title_lbl)
        self.ml_body = QGridLayout(); self.ml_body.setSpacing(10)
        self.ml_layout.addLayout(self.ml_body)
        bot_row.addWidget(self.ml_frame, 1)
        ml.addLayout(bot_row)

        # ── Weekly Summary ────────────────────────────────────────────────
        self.weekly_frame, self.weekly_layout = card()
        self.weekly_title_lbl = lbl(LM.tr("weekly_summary"), 14, T, True)
        self.weekly_layout.addWidget(self.weekly_title_lbl)
        self.weekly_row = QHBoxLayout(); self.weekly_row.setSpacing(14)
        self.weekly_layout.addLayout(self.weekly_row)
        ml.addWidget(self.weekly_frame)

        ml.addStretch()
        scroll.setWidget(c)
        ol = QVBoxLayout(self); ol.setContentsMargins(0, 0, 0, 0)
        ol.addWidget(scroll)

        for w in (self.alerts_frame, self.forecast_frame,
                  self.planting_frame, self.ml_frame, self.weekly_frame):
            w.hide()

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

    def _on_farm_changed(self, _):
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
            self.field_combo.addItem(
                f"{f['name']} — {f.get('crop_type', '')}", f["id"])

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
            f"color:{color};font-size:12px;background:transparent;"
            "font-family:'Segoe UI';")
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
        for w in (self.alerts_frame, self.forecast_frame,
                  self.planting_frame, self.ml_frame, self.weekly_frame):
            w.show()

    # ── Alerts ────────────────────────────────────────────────────────────────

    def _render_alerts(self, alerts):
        self._clear_layout(self.alerts_row)
        if not alerts:
            nf = QFrame()
            nf.setStyleSheet(
                f"QFrame{{background:#f0fdf4;border:1px solid #bbf7d0;border-radius:10px;}}")
            nl = QVBoxLayout(nf); nl.setContentsMargins(16, 12, 16, 12)
            nl.addWidget(lbl(LM.tr("no_alerts"), 13, EMERALD, True))
            self.alerts_row.addWidget(nf)
            self.alerts_row.addStretch()
            return

        for alert in alerts:
            sev = alert["severity"]
            fg  = SEVERITY_COLOR.get(sev, M)
            bg  = SEVERITY_BG.get(sev, W)
            bdr = SEVERITY_BORDER.get(sev, B)
            f = QFrame()
            f.setFixedWidth(250)
            f.setStyleSheet(
                f"QFrame{{background:{bg};border:1px solid {bdr};border-radius:10px;}}")
            fl = QVBoxLayout(f); fl.setContentsMargins(14, 12, 14, 12); fl.setSpacing(6)
            fl.addWidget(lbl(alert["title"],   12, fg,       True))
            fl.addWidget(lbl(alert["message"], 11, T,        False, True))
            div = QFrame(); div.setFixedHeight(1)
            div.setStyleSheet(f"background:{bdr};border:none;")
            fl.addWidget(div)
            fl.addWidget(lbl(f"→ {alert['action']}", 10, "#374151", False, True))
            self.alerts_row.addWidget(f)
        self.alerts_row.addStretch()

    # ── Forecast ──────────────────────────────────────────────────────────────

    def _render_forecast(self, forecast):
        self._clear_layout(self.forecast_row)
        for day in forecast:
            icon = CONDITION_ICON.get(day["condition"], "~")
            f = QFrame()
            f.setFixedWidth(115)
            f.setStyleSheet(
                f"QFrame{{background:{W};border:1px solid {B};border-radius:12px;}}")
            fl = QVBoxLayout(f); fl.setContentsMargins(10, 12, 10, 12); fl.setSpacing(4)
            fl.setAlignment(Qt.AlignmentFlag.AlignHCenter)

            dn = lbl(day["day_name"][:3].upper(), 9, M, True)
            dn.setAlignment(Qt.AlignmentFlag.AlignCenter)
            fl.addWidget(dn)

            ic = QLabel(icon)
            ic.setAlignment(Qt.AlignmentFlag.AlignCenter)
            ic.setStyleSheet(
                "font-size:20px;background:transparent;padding:4px 0;")
            fl.addWidget(ic)

            tmp = lbl(f"{day['temp_max']:.0f}° / {day['temp_min']:.0f}°", 11, T, True)
            tmp.setAlignment(Qt.AlignmentFlag.AlignCenter)
            fl.addWidget(tmp)

            div = QFrame(); div.setFixedHeight(1)
            div.setStyleSheet(f"background:{B};border:none;margin:2px 0;")
            fl.addWidget(div)

            for txt, color in [
                (f"Rain  {day['rain_probability']:.0f}%",    BLUE),
                (f"Hum   {day['humidity']:.0f}%",            M),
                (f"Wind  {day['wind_kmh']:.0f} km/h",        "#374151"),
            ]:
                ll = lbl(txt, 9, color)
                ll.setAlignment(Qt.AlignmentFlag.AlignCenter)
                fl.addWidget(ll)

            self.forecast_row.addWidget(f)
        self.forecast_row.addStretch()

    # ── Planting recommendation ───────────────────────────────────────────────

    def _render_planting(self, rec):
        self._clear_layout(self.planting_body)
        if not rec:
            self.planting_body.addWidget(lbl("—", 13, M))
            return

        risk_colors = {"low": EMERALD, "medium": GOLD, "high": RED}
        rc = risk_colors.get(rec.get("risk_level", "low"), M)

        # Ideal date + risk level
        idate = rec.get("ideal_date")
        date_text = idate if idate else LM.tr("not_favorable")
        top = QHBoxLayout()
        top.addWidget(_result_card(
            LM.tr("ideal_date"),
            date_text,
            "",
            G if idate else RED))
        badge_f = QFrame()
        badge_f.setStyleSheet(
            f"QFrame{{background:{W};border:1px solid {B};border-radius:10px;}}")
        bf = QVBoxLayout(badge_f); bf.setContentsMargins(16, 14, 16, 14); bf.setSpacing(5)
        bf.addWidget(lbl(LM.tr("risk_level"), 11, M, True))
        badge = QLabel(f"  {rec.get('risk_level','—').upper()}  ")
        badge.setFixedHeight(28)
        badge.setStyleSheet(
            f"background:{rc};color:white;font-size:12px;font-weight:700;"
            "border-radius:6px;padding:0 8px;font-family:'Segoe UI';")
        bf.addWidget(badge)
        top.addWidget(badge_f)
        self.planting_body.addLayout(top)

        # Water req + suitability score
        mid = QHBoxLayout()
        mid.addWidget(_result_card(
            LM.tr("water_req"),
            f"{rec.get('water_requirement_mm', 0):.0f} mm",
            "",
            BLUE))

        score_f = QFrame()
        score_f.setStyleSheet(
            f"QFrame{{background:{W};border:1px solid {B};border-radius:10px;}}")
        sf = QVBoxLayout(score_f); sf.setContentsMargins(16, 14, 16, 14); sf.setSpacing(6)
        sf.addWidget(lbl(LM.tr("suitability"), 11, M, True))
        score = rec.get("suitability_score", 0)
        bar_color = EMERALD if score >= 0.7 else (GOLD if score >= 0.4 else RED)
        bar = QProgressBar()
        bar.setFixedHeight(10); bar.setRange(0, 100); bar.setValue(int(score * 100))
        bar.setTextVisible(False)
        bar.setStyleSheet(f"""
            QProgressBar{{border:1px solid {B};border-radius:5px;background:#f1f5f1;}}
            QProgressBar::chunk{{background:{bar_color};border-radius:4px;}}""")
        sf.addWidget(bar)
        sf.addWidget(lbl(f"{score:.0%}", 18, bar_color, True))
        mid.addWidget(score_f)
        self.planting_body.addLayout(mid)

        # Reasons banner
        reasons = rec.get("reasons", [])
        if reasons:
            rb = QLabel("  ·  ".join(reasons))
            rb.setWordWrap(True)
            rb.setStyleSheet(
                f"color:{T};font-size:12px;padding:10px 12px;background:{A};"
                "border-radius:8px;border:1px solid #b8d8c4;font-family:'Segoe UI';")
            self.planting_body.addWidget(rb)

    # ── ML summary ────────────────────────────────────────────────────────────

    def _render_ml(self, ml):
        self._clear_layout(self.ml_body)
        if not ml:
            self.ml_body.addWidget(
                lbl(LM.tr("ml_unavailable"), 11, M, False, True), 0, 0)
            return

        health_colors = {"Healthy": EMERALD, "Stressed": GOLD, "Diseased": RED}
        hc = health_colors.get(ml.get("crop_health", ""), M)

        cards = [
            ("🌿  " + LM.tr("crop_health_lbl"),
             ml.get("crop_health", "—"), "", hc),
            ("💧  " + LM.tr("irrigation_lbl"),
             ml.get("irrigation", "—").replace("_", " ").title(), "", BLUE),
            ("📈  " + LM.tr("yield_lbl"),
             f"{ml.get('predicted_yield_tha', 0):.2f} t/ha", "", PURPLE),
        ]
        for i, (title, main, sub, color) in enumerate(cards):
            self.ml_body.addWidget(_result_card(title, main, sub, color), i // 2, i % 2)

    # ── Weekly summary ────────────────────────────────────────────────────────

    def _render_weekly(self, ws):
        self._clear_layout(self.weekly_row)
        stats = [
            (LM.tr("avg_temp"),     f"{ws.get('avg_temp', 0):.1f}°C",       G,        "#e8f5ee", "#b8d8c4"),
            (LM.tr("total_rain"),   f"{ws.get('total_rain_mm', 0):.1f} mm",  BLUE,     "#eff6ff", "#bfdbfe"),
            (LM.tr("avg_humidity"), f"{ws.get('avg_humidity', 0):.0f}%",     "#0891b2","#ecfeff", "#a5f3fc"),
            (LM.tr("avg_wind"),     f"{ws.get('avg_wind_kmh', 0):.0f} km/h", "#374151","#f8fafc", "#e2e8f0"),
        ]
        for label, value, color, bg, border in stats:
            f = QFrame()
            f.setFixedHeight(100)
            f.setStyleSheet(
                f"QFrame{{background:{bg};border:1px solid {border};border-radius:12px;}}")
            fl = QVBoxLayout(f); fl.setContentsMargins(20, 14, 20, 14)
            fl.addWidget(lbl(label, 11, M))
            fl.addWidget(lbl(value, 26, color, True))
            self.weekly_row.addWidget(f, 1)

    # ── i18n ─────────────────────────────────────────────────────────────────

    def _retranslate(self):
        self.title_lbl.setText(LM.tr("smart_title"))
        self.alerts_title_lbl.setText(LM.tr("alerts_title"))
        self.forecast_title_lbl.setText(LM.tr("forecast_title"))
        self.planting_title_lbl.setText(LM.tr("planting_rec_title"))
        self.ml_title_lbl.setText(LM.tr("ml_summary_title"))
        self.weekly_title_lbl.setText(LM.tr("weekly_summary"))
        if self._data:
            self._render(self._data)
