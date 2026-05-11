from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QComboBox, QPushButton
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QPointF, QRectF
from PyQt6.QtGui import (
    QPainter, QColor, QPen, QBrush, QFont, QLinearGradient,
    QPainterPath, QRadialGradient, QConicalGradient
)
import math
import desktop.api as api

G="#1a6b35"; W="#ffffff"; P="#f4f6f4"; T="#111827"; M="#6b7280"; B="#e2e8e4"; A="#e8f5ee"


class FarmWorker(QThread):
    done = pyqtSignal(list)
    def run(self):
        try:
            farms = api.get_farms()
            for farm in farms:
                fields = api.get_fields(farm["id"])
                # Fetch latest satellite indices for each field
                for f in fields:
                    try:
                        history = api.get_index_history(f["id"])
                        if history:
                            f["latest_indices"] = history[0]
                        else:
                            f["latest_indices"] = None
                    except:
                        f["latest_indices"] = None
                farm["fields"] = fields
            self.done.emit(farms)
        except:
            self.done.emit([])


class EarthMapCanvas(QWidget):
    LAT_MIN, LAT_MAX = 23.0, 38.5
    LON_MIN, LON_MAX = 59.5, 78.5

    PAK_COORDS = [
        (37.1,74.6),(36.9,75.9),(36.5,76.8),(36.2,77.3),(35.5,77.0),
        (35.0,76.2),(34.5,75.8),(34.0,74.0),(33.5,73.2),(33.0,72.0),
        (32.5,70.8),(32.0,69.5),(31.5,68.8),(31.0,68.2),(30.5,67.5),
        (30.0,66.8),(29.5,66.2),(29.0,65.5),(28.0,64.2),(27.0,63.5),
        (26.0,62.5),(25.0,61.5),(24.0,62.0),(23.5,63.5),(23.7,65.0),
        (24.0,66.5),(24.5,67.5),(25.0,68.5),(25.5,69.5),(26.0,70.5),
        (26.5,71.5),(27.0,72.0),(28.0,72.5),(29.0,73.0),(30.0,73.5),
        (31.0,74.0),(32.0,74.2),(33.0,74.5),(34.0,74.8),(35.0,74.5),
        (36.0,74.8),(37.1,74.6),
    ]

    CITIES = [
        (33.72,73.06,"Islamabad",True),
        (31.55,74.35,"Lahore",True),
        (24.86,67.01,"Karachi",True),
        (25.40,68.37,"Hyderabad",False),
        (30.18,66.99,"Quetta",False),
        (34.01,71.58,"Peshawar",False),
        (27.70,68.86,"Sukkur",False),
        (26.24,68.42,"Nawabshah",False),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.farms     = []
        self.selected  = None
        self.zoom      = 1.0
        self.offset    = QPointF(0.0, 0.0)
        self._drag     = None
        self._press_pos = None
        self.setMinimumHeight(440)
        self.setStyleSheet("background:#0a0f1e;border-radius:12px;")
        self.setMouseTracking(True)

    def set_farms(self, farms, selected_id=None):
        self.farms    = farms
        self.selected = selected_id
        self.update()

    def reset_view(self):
        self.zoom   = 1.0
        self.offset = QPointF(0.0, 0.0)
        self.update()

    def _geo_to_px(self, lat, lon, w, h):
        bx = (lon - self.LON_MIN) / (self.LON_MAX - self.LON_MIN) * w
        by = (1.0 - (lat - self.LAT_MIN) / (self.LAT_MAX - self.LAT_MIN)) * h
        cx, cy = w/2.0, h/2.0
        x = cx + (bx - cx) * self.zoom + self.offset.x()
        y = cy + (by - cy) * self.zoom + self.offset.y()
        return x, y

    def wheelEvent(self, e):
        f = 1.15 if e.angleDelta().y() > 0 else 0.87
        self.zoom = max(0.4, min(self.zoom * f, 12.0))
        self.update()

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._drag = e.position()
            self._press_pos = e.position()

    def mouseMoveEvent(self, e):
        if self._drag:
            d = e.position() - self._drag
            self.offset += d
            self._drag = e.position()
            self.update()

    def mouseReleaseEvent(self, e):
        self._drag = None
        moved = 0
        if self._press_pos:
            moved = (e.position() - self._press_pos).manhattanLength()
        self._press_pos = None

        if moved < 5 and e.button() == Qt.MouseButton.LeftButton:
            w, h = self.width(), self.height()
            pos = e.position()
            show = ([f for f in self.farms if f["id"]==self.selected]
                    if self.selected else self.farms)
            for farm in show:
                lat = farm.get("latitude") or 25.396
                lon = farm.get("longitude") or 68.374
                fx, fy = self._geo_to_px(lat, lon, w, h)
                if (pos.x()-fx)**2 + (pos.y()-fy)**2 < 600:
                    self.zoom = 6.0
                    bx = (lon-self.LON_MIN)/(self.LON_MAX-self.LON_MIN)*w
                    by = (1-(lat-self.LAT_MIN)/(self.LAT_MAX-self.LAT_MIN))*h
                    cx, cy = w/2.0, h/2.0
                    self.offset = QPointF(
                        (cx - bx) * self.zoom,
                        (cy - by) * self.zoom
                    )
                    self.update()
                    break

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()

        # ── Deep space background ──────────────────────────────────────────
        p.fillRect(0, 0, w, h, QColor("#0a0f1e"))

        # Stars
        import random; rng = random.Random(42)
        p.setPen(QPen(QColor(255,255,255,120), 1))
        for _ in range(80):
            sx = rng.randint(0, w)
            sy = rng.randint(0, h)
            p.drawPoint(sx, sy)

        # ── Ocean / water areas ────────────────────────────────────────────
        ocean_grad = QLinearGradient(0, 0, w, h)
        ocean_grad.setColorAt(0, QColor("#0d2137"))
        ocean_grad.setColorAt(1, QColor("#0a1a2e"))
        p.fillRect(0, 0, w, h, QBrush(ocean_grad))

        # ── Lat/Lon grid ───────────────────────────────────────────────────
        p.setPen(QPen(QColor(255,255,255,18), 1, Qt.PenStyle.DotLine))
        for lat in range(24, 38, 2):
            x1, y1 = self._geo_to_px(lat, self.LON_MIN, w, h)
            x2, y2 = self._geo_to_px(lat, self.LON_MAX, w, h)
            p.drawLine(int(x1), int(y1), int(x2), int(y2))
        for lon in range(61, 78, 2):
            x1, y1 = self._geo_to_px(self.LAT_MIN, lon, w, h)
            x2, y2 = self._geo_to_px(self.LAT_MAX, lon, w, h)
            p.drawLine(int(x1), int(y1), int(x2), int(y2))

        # ── Pakistan terrain ───────────────────────────────────────────────
        # Base land
        path = QPainterPath()
        for i, (lat, lon) in enumerate(self.PAK_COORDS):
            x, y = self._geo_to_px(lat, lon, w, h)
            if i == 0: path.moveTo(x, y)
            else:      path.lineTo(x, y)
        path.closeSubpath()

        land_grad = QLinearGradient(0, 0, w, h)
        land_grad.setColorAt(0.0, QColor("#3d5a1e"))   # north green
        land_grad.setColorAt(0.3, QColor("#6b7c3a"))   # mid
        land_grad.setColorAt(0.6, QColor("#8b7355"))   # south tan
        land_grad.setColorAt(1.0, QColor("#a08060"))   # desert
        p.fillPath(path, QBrush(land_grad))

        # Border glow
        p.setPen(QPen(QColor("#88cc66"), 1.5))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(path)

        # Outer glow
        p.setPen(QPen(QColor(136,204,102,60), 4))
        p.drawPath(path)

        # ── Sindh region highlight ─────────────────────────────────────────
        sindh = [(25.5,68.0),(26.0,68.5),(26.5,69.0),(27.0,69.5),
                 (27.5,68.5),(27.0,67.5),(26.5,67.0),(26.0,67.5),(25.5,68.0)]
        sp = QPainterPath()
        for i,(lat,lon) in enumerate(sindh):
            x,y = self._geo_to_px(lat,lon,w,h)
            if i==0: sp.moveTo(x,y)
            else:    sp.lineTo(x,y)
        sp.closeSubpath()
        p.fillPath(sp, QBrush(QColor(180,140,80,60)))

        # ── Indus River ────────────────────────────────────────────────────
        river = [(36.5,73.5),(35.0,72.5),(33.0,71.5),(31.5,71.0),
                 (30.0,70.5),(28.5,69.5),(27.0,68.5),(25.5,68.2),(24.0,67.5)]
        p.setPen(QPen(QColor("#4a90d9"), 2))
        p.setBrush(Qt.BrushStyle.NoBrush)
        rp = QPainterPath()
        for i,(lat,lon) in enumerate(river):
            x,y = self._geo_to_px(lat,lon,w,h)
            if i==0: rp.moveTo(x,y)
            else:    rp.lineTo(x,y)
        p.drawPath(rp)

        # ── Cities ─────────────────────────────────────────────────────────
        for lat, lon, name, major in self.CITIES:
            x, y = self._geo_to_px(lat, lon, w, h)
            if major:
                # City glow
                cg = QRadialGradient(x, y, 12)
                cg.setColorAt(0, QColor(255,220,100,150))
                cg.setColorAt(1, QColor(255,200,50,0))
                p.setBrush(QBrush(cg))
                p.setPen(Qt.PenStyle.NoPen)
                p.drawEllipse(QPointF(x,y), 12, 12)
                p.setBrush(QBrush(QColor("#ffdc64")))
                p.drawEllipse(QPointF(x,y), 3, 3)
            else:
                p.setBrush(QBrush(QColor("#ffffff")))
                p.setPen(Qt.PenStyle.NoPen)
                p.drawEllipse(QPointF(x,y), 2, 2)

            p.setPen(QPen(QColor("#e8e8e8")))
            p.setFont(QFont("Segoe UI", 7 if major else 6))
            p.drawText(int(x)+5, int(y)+4, name)

        # ── Farm markers ───────────────────────────────────────────────────
        show = ([f for f in self.farms if f["id"]==self.selected]
                if self.selected else self.farms)

        for farm in show:
            lat  = farm.get("latitude")  or 25.396
            lon  = farm.get("longitude") or 68.374
            fx, fy = self._geo_to_px(lat, lon, w, h)

            # Outer pulse ring
            for r, alpha in [(28,30),(20,60),(13,100)]:
                rg = QRadialGradient(fx, fy, r)
                rg.setColorAt(0, QColor(50,255,100,alpha))
                rg.setColorAt(1, QColor(50,255,100,0))
                p.setBrush(QBrush(rg))
                p.setPen(Qt.PenStyle.NoPen)
                p.drawEllipse(QPointF(fx,fy), r, r)

            # Pin circle
            p.setBrush(QBrush(QColor("#22c55e")))
            p.setPen(QPen(QColor("#ffffff"), 2))
            p.drawEllipse(QPointF(fx,fy), 9, 9)

            # Inner dot
            p.setBrush(QBrush(QColor("#ffffff")))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(QPointF(fx,fy), 3, 3)

            # Info panel
            name  = farm.get("name","Farm")
            dist  = farm.get("district","")
            area  = farm.get("area_ha","")
            flds  = len(farm.get("fields",[]))
            lw, lh = 150, 64
            lx = min(fx+16, w-lw-4)
            ly = max(fy-lh/2, 4.0)

            # Panel background
            p.setBrush(QBrush(QColor(10,20,40,210)))
            p.setPen(QPen(QColor("#22c55e"), 1))
            p.drawRoundedRect(QRectF(lx,ly,lw,lh), 8, 8)

            # Green top bar
            p.setBrush(QBrush(QColor("#1a6b35")))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawRoundedRect(QRectF(lx,ly,lw,20), 8, 8)
            p.drawRect(QRectF(lx,ly+10,lw,10))

            p.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
            p.setPen(QPen(QColor("#ffffff")))
            p.drawText(int(lx)+8, int(ly)+14, name)

            p.setFont(QFont("Segoe UI", 7))
            p.setPen(QPen(QColor("#86efac")))
            p.drawText(int(lx)+8, int(ly)+30, "📍 {}, {} ha".format(dist,area))
            p.setPen(QPen(QColor("#94a3b8")))
            p.drawText(int(lx)+8, int(ly)+44, "🌾 {} field(s)".format(flds))
            p.drawText(int(lx)+8, int(ly)+57,
                       "🌐 {:.3f}°N {:.3f}°E".format(lat,lon))

        # ── Compass ────────────────────────────────────────────────────────
        cx2, cy2 = w-36, 36
        p.setBrush(QBrush(QColor(0,0,0,120)))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QPointF(cx2,cy2), 22, 22)
        p.setPen(QPen(QColor("#ffffff"), 1))
        p.setBrush(QBrush(QColor("#ffffff")))
        # N arrow
        pts_n = [QPointF(cx2,cy2-16), QPointF(cx2-5,cy2+4), QPointF(cx2+5,cy2+4)]
        p.drawPolygon(*pts_n)
        p.setBrush(QBrush(QColor("#ef4444")))
        pts_s = [QPointF(cx2,cy2+16), QPointF(cx2-5,cy2-4), QPointF(cx2+5,cy2-4)]
        p.drawPolygon(*pts_s)
        p.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))
        p.setPen(QPen(QColor("#ffffff")))
        p.drawText(int(cx2)-3, int(cy2)-18, "N")

        # ── Scale bar ──────────────────────────────────────────────────────
        p.setPen(QPen(QColor("#ffffff"), 2))
        p.drawLine(12, h-12, 82, h-12)
        p.drawLine(12, h-12, 12, h-18)
        p.drawLine(82, h-12, 82, h-18)
        p.setFont(QFont("Segoe UI", 7))
        p.drawText(20, h-15, "~200 km")

        # ── HUD info ───────────────────────────────────────────────────────
        p.setBrush(QBrush(QColor(0,0,0,140)))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(QRectF(w-130, h-30, 126, 22), 4, 4)
        p.setFont(QFont("Segoe UI", 7))
        p.setPen(QPen(QColor("#94a3b8")))
        p.drawText(w-124, h-14, "Zoom {:.1f}x  ·  Pakistan".format(self.zoom))

        p.end()


class MapPage(QWidget):
    def __init__(self):
        super().__init__()
        self.setStyleSheet(f"background:{P};")
        self.farms = []
        self._workers = []
        self._build()
        self._load()

    def showEvent(self, event):
        super().showEvent(event)
        self._load()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0,0,0,0)
        layout.setSpacing(12)

        ctrl = QFrame()
        ctrl.setStyleSheet("QFrame{background:#0d2414;border:1px solid #1a4a2a;border-radius:12px;}")
        cl = QHBoxLayout(ctrl)
        cl.setContentsMargins(16,10,16,10)
        cl.setSpacing(12)

        fl = QLabel("🌍  Farm:")
        fl.setStyleSheet("color:#86efac;font-size:13px;font-family:'Segoe UI';background:transparent;font-weight:600;")

        self.farm_combo = QComboBox()
        self.farm_combo.setFixedHeight(34)
        self.farm_combo.setStyleSheet("""
            QComboBox{color:#f0ede6;background:#1a3a24;border:1px solid #2d6a3f;
                      border-radius:8px;padding:0 12px;font-size:13px;font-family:'Segoe UI';}
            QComboBox QAbstractItemView{color:#111827;background:#ffffff;
                border:1px solid #2d6a3f;selection-background-color:#e8f5ee;}
            QComboBox QAbstractItemView::item{color:#111827;padding:8px 12px;min-height:28px;background:#ffffff;}
            QComboBox QAbstractItemView::item:hover{background:#e8f5ee;}
        """)
        self.farm_combo.currentIndexChanged.connect(self._on_farm)

        ref = QPushButton("🔄")
        ref.setFixedSize(34,34)
        ref.setToolTip("Refresh farms")
        ref.setStyleSheet("QPushButton{background:#1a3a24;color:#86efac;border:1px solid #2d6a3f;border-radius:8px;font-size:14px;} QPushButton:hover{background:#2d6a3f;}")
        ref.clicked.connect(self._load)

        rst = QPushButton("🔍  Reset")
        rst.setFixedHeight(34)
        rst.setStyleSheet("QPushButton{background:#1a3a24;color:#86efac;border:1px solid #2d6a3f;border-radius:8px;padding:0 12px;font-size:12px;font-family:'Segoe UI';} QPushButton:hover{background:#2d6a3f;}")
        rst.clicked.connect(lambda: self.canvas.reset_view())

        cl.addWidget(fl)
        cl.addWidget(self.farm_combo, 1)
        cl.addWidget(ref)
        cl.addWidget(rst)
        layout.addWidget(ctrl)

        self.canvas = EarthMapCanvas()
        layout.addWidget(self.canvas, 1)

        self.status = QLabel("Loading farms...")
        self.status.setStyleSheet("color:#6b7280;font-size:11px;background:transparent;font-family:'Segoe UI';")
        layout.addWidget(self.status)

    def _load(self):
        w = FarmWorker()
        self._workers.append(w)
        w.done.connect(self._on_loaded)
        w.finished.connect(lambda: self._workers.remove(w) if w in self._workers else None)
        w.start()

    def _on_loaded(self, farms):
        self.farms = farms
        self.canvas.reset_view()
        self.farm_combo.clear()
        self.farm_combo.addItem("🌍  All Farms", None)
        for f in farms:
            self.farm_combo.addItem(f"📍  {f['name']}", f["id"])
        self.status.setText(f"{len(farms)} farm(s) loaded  ·  Click marker to zoom  ·  Scroll to zoom  ·  Drag to pan")
        self.canvas.set_farms(farms)

    def _on_farm(self):
        fid = self.farm_combo.currentData()
        self.canvas.set_farms(self.farms, fid)
