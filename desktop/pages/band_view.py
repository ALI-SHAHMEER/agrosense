"""
AgroSense — Satellite Band Viewer
Shows real Sentinel-2 band composites fetched from Google Earth Engine.
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QComboBox, QPushButton, QDateEdit, QScrollArea,
    QGridLayout, QSizePolicy
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QDate
from PyQt6.QtGui import QPixmap, QImage, QColor, QPainter, QFont
import desktop.api as api

G="#1a6b35"; W="#ffffff"; P="#f4f6f4"; T="#111827"
M="#6b7280"; B="#e2e8e4"; A="#e8f5ee"; R="#dc2626"; DB="#0b1f10"

COMPOSITES = [
    {
        "name": "Agriculture Composite",
        "bands": ["B11","B8","B2"],
        "desc": "SWIR + NIR + Blue — Vigorous crops appear bright green, bare soil appears brown",
        "color": "#22c55e",
        "min": 0, "max": 3000,
    },
    {
        "name": "Vegetation Analysis",
        "bands": ["B8A","B4","B3"],
        "desc": "Narrow NIR + Red + Green — Better canopy penetration, shows plant density",
        "color": "#84cc16",
        "min": 0, "max": 3000,
    },
    {
        "name": "NDRE Visualization",
        "bands": ["B5","B4","B3"],
        "desc": "Red Edge + Red + Green — Late season crop monitoring, avoids NDVI saturation",
        "color": "#f59e0b",
        "min": 0, "max": 3000,
    },
    {
        "name": "True Color (RGB)",
        "bands": ["B4","B3","B2"],
        "desc": "Natural color — Red + Green + Blue as seen by human eye",
        "color": "#2563eb",
        "min": 0, "max": 3000,
    },
    {
        "name": "False Color (NIR)",
        "bands": ["B8","B4","B3"],
        "desc": "NIR + Red + Green — Healthy vegetation appears bright red",
        "color": "#dc2626",
        "min": 0, "max": 3000,
    },
    {
        "name": "NDVI Colormap",
        "bands": ["NDVI"],
        "desc": "Normalized Difference Vegetation Index — Green=healthy, Red=stressed",
        "color": "#1a6b35",
        "min": -0.2, "max": 0.8,
    },
]


class BandWorker(QThread):
    done  = pyqtSignal(str, bytes)   # composite_name, png_bytes
    error = pyqtSignal(str, str)     # composite_name, error_msg

    def __init__(self, composite, field_id, boundary, start, end):
        super().__init__()
        self.composite  = composite
        self.field_id   = field_id
        self.boundary   = boundary
        self.date_start = start
        self.date_end   = end

    def run(self):
        try:
            import desktop.api as api
            band_type_map = {
                "Agriculture Composite": "agriculture",
                "Vegetation Analysis":   "vegetation",
                "NDRE Visualization":    "ndre",
                "True Color (RGB)":      "truecolor",
                "False Color (NIR)":     "falsecolor",
                "NDVI Colormap":         "ndvi",
            }
            name      = self.composite["name"]
            band_type = band_type_map.get(name, "truecolor")
            png_bytes = api.get_band_thumbnail(
                self.field_id, band_type,
                self.date_start, self.date_end
            )
            self.done.emit(name, png_bytes)
        except Exception as e:
            self.error.emit(self.composite["name"], str(e)[:100])


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


class BandCard(QFrame):
    """Card showing one band composite image."""
    def __init__(self, composite):
        super().__init__()
        self.composite = composite
        self.setStyleSheet(
            f"QFrame{{background:{DB};border:1px solid #1a3a24;"
            f"border-radius:12px;}}")
        self.setFixedSize(360, 420)
        self._build()

    def _build(self):
        l = QVBoxLayout(self)
        l.setContentsMargins(0, 0, 0, 12)
        l.setSpacing(8)

        # Header
        hdr = QWidget()
        hdr.setStyleSheet(
            f"background:{self.composite['color']}22;"
            f"border-radius:10px 10px 0 0;")
        hl = QVBoxLayout(hdr)
        hl.setContentsMargins(12, 10, 12, 10)

        title = QLabel(self.composite["name"])
        title.setStyleSheet(
            f"color:{self.composite['color']};font-size:12px;"
            f"font-weight:700;font-family:'Segoe UI';background:transparent;")

        bands_txt = " + ".join(self.composite["bands"])
        bands_lbl = QLabel(f"Bands: {bands_txt}")
        bands_lbl.setStyleSheet(
            f"color:#94a3b8;font-size:10px;font-family:'Segoe UI';"
            f"background:transparent;")

        hl.addWidget(title)
        hl.addWidget(bands_lbl)
        l.addWidget(hdr)

        # Image area
        self.img_lbl = QLabel()
        self.img_lbl.setFixedSize(358, 320)
        self.img_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.img_lbl.setStyleSheet("background:#0a0f1e;border:none;")
        self._set_placeholder()
        l.addWidget(self.img_lbl)

        # Description
        desc = QLabel(self.composite["desc"])
        desc.setWordWrap(True)
        desc.setStyleSheet(
            f"color:#64748b;font-size:9px;font-family:'Segoe UI';"
            f"background:transparent;padding:0 12px;")
        l.addWidget(desc)

    def _set_placeholder(self):
        """Show loading placeholder."""
        pm = QPixmap(318, 280)
        pm.fill(QColor("#0a0f1e"))
        p = QPainter(pm)
        p.setPen(QColor("#1e3a2a"))
        p.setFont(QFont("Segoe UI", 9))
        p.drawText(pm.rect(), Qt.AlignmentFlag.AlignCenter,
                   f"⏳  Loading {self.composite['name']}...")
        p.end()
        self.img_lbl.setPixmap(pm)

    def set_image(self, png_bytes: bytes):
        pm = QPixmap()
        pm.loadFromData(png_bytes)
        if not pm.isNull():
            pm = pm.scaled(358, 320,
                           Qt.AspectRatioMode.KeepAspectRatio,
                           Qt.TransformationMode.SmoothTransformation)
        self.img_lbl.setPixmap(pm)

    def set_error(self, msg: str):
        pm = QPixmap(318, 280)
        pm.fill(QColor("#1a0a0a"))
        p = QPainter(pm)
        p.setPen(QColor("#dc2626"))
        p.setFont(QFont("Segoe UI", 8))
        p.drawText(pm.rect(), Qt.AlignmentFlag.AlignCenter,
                   f"❌  Error\n{msg[:60]}")
        p.end()
        self.img_lbl.setPixmap(pm)


class BandViewPage(QWidget):
    def __init__(self):
        super().__init__()
        self.setStyleSheet(f"background:{P};")
        self.fields   = []
        self._workers = []
        self._cards   = {}
        self._build()
        self._load_fields()

    def _build(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0,0,0,0)
        outer.setSpacing(14)

        # ── Controls ──────────────────────────────────────────────────────────
        ctrl = QFrame()
        ctrl.setStyleSheet(
            f"QFrame{{background:{W};border:1px solid {B};border-radius:12px;}}")
        cl = QHBoxLayout(ctrl)
        cl.setContentsMargins(16,12,16,12)
        cl.setSpacing(12)

        def lbl(t):
            l = QLabel(t)
            l.setStyleSheet(
                f"color:{T};font-size:13px;font-family:'Segoe UI';"
                f"background:transparent;")
            return l

        cs = f"""
            QComboBox{{color:{T};background:{W};border:1.5px solid {B};
                       border-radius:8px;padding:0 12px;font-size:13px;
                       font-family:'Segoe UI';}}
            QComboBox:focus{{border-color:{G};}}
            QComboBox QAbstractItemView{{color:{T};background:{W};
                border:1px solid {B};selection-background-color:{A};}}
            QComboBox QAbstractItemView::item{{color:{T};padding:8px 12px;
                min-height:28px;background:{W};}}
            QComboBox QAbstractItemView::item:hover{{background:{A};}}
        """
        ds = f"""
            QDateEdit{{color:{T};background:{W};border:1.5px solid {B};
                       border-radius:8px;padding:0 10px;font-size:13px;
                       font-family:'Segoe UI';}}
            QDateEdit:focus{{border-color:{G};}}
        """

        self.field_combo = QComboBox()
        self.field_combo.setFixedHeight(36)
        self.field_combo.setStyleSheet(cs)

        self.start_date = QDateEdit(QDate(2024,1,1))
        self.start_date.setFixedHeight(36)
        self.start_date.setCalendarPopup(True)
        self.start_date.setStyleSheet(ds)

        self.end_date = QDateEdit(QDate(2024,3,1))
        self.end_date.setFixedHeight(36)
        self.end_date.setCalendarPopup(True)
        self.end_date.setStyleSheet(ds)

        self.fetch_btn = QPushButton("🛰  Fetch Band Composites")
        self.fetch_btn.setFixedHeight(36)
        self.fetch_btn.setStyleSheet(f"""
            QPushButton{{background:{G};color:white;border:none;border-radius:9px;
                         font-size:13px;font-weight:600;font-family:'Segoe UI';
                         padding:0 16px;}}
            QPushButton:hover{{background:#145a2b;}}
            QPushButton:disabled{{background:#9ca3af;}}
        """)
        self.fetch_btn.clicked.connect(self._fetch)

        cl.addWidget(lbl("Field:"))
        cl.addWidget(self.field_combo, 2)
        cl.addWidget(lbl("Start:"))
        cl.addWidget(self.start_date)
        cl.addWidget(lbl("End:"))
        cl.addWidget(self.end_date)
        cl.addWidget(self.fetch_btn)
        outer.addWidget(ctrl)

        # Status
        self.status = QLabel("Select a field and click Fetch Band Composites")
        self.status.setStyleSheet(
            f"color:{M};font-size:12px;background:transparent;font-family:'Segoe UI';")
        outer.addWidget(self.status)

        # ── Band cards grid ───────────────────────────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("QScrollArea{border:none;background:transparent;}")

        grid_w = QWidget()
        grid_w.setStyleSheet(f"background:{P};")
        self.grid = QGridLayout(grid_w)
        self.grid.setSpacing(16)
        self.grid.setContentsMargins(0,0,0,0)

        # Create cards for all composites
        for i, comp in enumerate(COMPOSITES):
            card = BandCard(comp)
            row, col = divmod(i, 3)
            self.grid.addWidget(card, row, col)
            self._cards[comp["name"]] = card

        scroll.setWidget(grid_w)
        outer.addWidget(scroll, 1)

    def _load_fields(self):
        self._lw = LoadWorker()
        self._lw.done.connect(self._on_loaded)
        self._lw.err.connect(lambda msg: self.status.setText(f"❌  {msg}"))
        self._lw.start()

    def _on_loaded(self, farms, fields):
        self.fields = fields
        self.field_combo.clear()
        for f in fields:
            self.field_combo.addItem(
                f"{f.get('name','?')} — {f.get('crop_type','?')} ({f.get('farm_name','')})",
                f["id"]
            )

    def showEvent(self, event):
        super().showEvent(event)
        self._load_fields()

    def _fetch(self):
        field_id = self.field_combo.currentData()
        if not field_id:
            self.status.setText("⚠  Please select a field")
            return

        # Get boundary from field
        field = next((f for f in self.fields if f["id"] == field_id), None)
        if not field:
            return

        # Build boundary coords from field geometry
        boundary = self._get_boundary(field)

        date_start = self.start_date.date().toString("yyyy-MM-dd")
        date_end   = self.end_date.date().toString("yyyy-MM-dd")

        self.fetch_btn.setEnabled(False)
        self.fetch_btn.setText("⏳  Fetching from GEE...")
        self.status.setText(
            f"🛰  Fetching {len(COMPOSITES)} band composites from Google Earth Engine...")

        # Reset all cards to loading state
        for card in self._cards.values():
            card._set_placeholder()

        # Launch a worker for each composite
        self._workers = []
        for comp in COMPOSITES:
            w = BandWorker(comp, field_id, boundary, date_start, date_end)
            w.done.connect(self._on_image)
            w.error.connect(self._on_error)
            w.finished.connect(self._check_done)
            self._workers.append(w)
            w.start()

    def _get_boundary(self, field):
        """Get boundary polygon coordinates for a field."""
        # Try to get from API, fallback to farm GPS
        try:
            import requests
            import desktop.api as api
            token = api.get_token()
            r = requests.get(
                f"http://localhost:8000/fields/{field['id']}",
                headers={"Authorization": f"Bearer {token}"},
                timeout=10
            )
            data = r.json()
            coords = data.get("boundary_coords")
            if coords and len(coords) >= 3:
                return coords
        except:
            pass

        # Fallback: generate boundary from farm GPS or default Pakistan location
        lat = field.get("latitude") or 25.396
        lon = field.get("longitude") or 68.374
        area_ha = field.get("area_ha") or 10
        import math
        d = math.sqrt(float(area_ha) * 10000) / 111000
        return [
            [lon-d, lat-d],
            [lon+d, lat-d],
            [lon+d, lat+d],
            [lon-d, lat+d],
            [lon-d, lat-d],
        ]

    def _on_image(self, name, png_bytes):
        card = self._cards.get(name)
        if card:
            card.set_image(png_bytes)

    def _on_error(self, name, msg):
        card = self._cards.get(name)
        if card:
            card.set_error(msg)

    def _check_done(self):
        running = sum(1 for w in self._workers if w.isRunning())
        if running == 0:
            self.fetch_btn.setEnabled(True)
            self.fetch_btn.setText("🛰  Fetch Band Composites")
            self.status.setText(
                f"✅  All {len(COMPOSITES)} band composites loaded!")
