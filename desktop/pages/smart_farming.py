from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QPushButton, QComboBox, QScrollArea, QProgressBar
)
from PyQt6.QtCore import Qt
import desktop.api as api
from desktop.i18n import LM
from desktop.pages.dashboard import Worker, lbl, card

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

        # Sections hidden until data loads
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
            self.field_combo.addItem(f"{f['name']} ({f.get('crop_type', '')})", f["id"])

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
            f.setStyleSheet("QFrame{background:#f0fdf4;border:1px solid #bbf7d0;border-radius:10px;}")
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
            fl.addWidget(lbl(f"→ {alert['action']}", 10, M, wrap=True))
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
        badge = QLabel(f" {rec.get('risk_level', '—').upper()} ")
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
            QProgressBar{{border:1px solid {B};border-radius:5px;background:#f1f5f1;}}
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
            (LM.tr("avg_temp"),     f"{ws.get('avg_temp', 0):.1f}°C",      G),
            (LM.tr("total_rain"),   f"{ws.get('total_rain_mm', 0):.1f} mm", BLUE),
            (LM.tr("avg_humidity"), f"{ws.get('avg_humidity', 0):.0f}%",    "#0891b2"),
            (LM.tr("avg_wind"),     f"{ws.get('avg_wind_kmh', 0):.0f} km/h", "#374151"),
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
