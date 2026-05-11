from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QPushButton, QComboBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QDateEdit, QDoubleSpinBox, QScrollArea
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QDate
from PyQt6.QtGui import QColor
import desktop.api as api

G="#1a6b35"; W="#ffffff"; P="#f4f6f4"; T="#111827"
M="#6b7280"; B="#e2e8e4"; A="#e8f5ee"; R="#dc2626"
DB="#0b1f10"; GOLD="#d4a017"

def lbl(text, size=13, color="#111827", bold=False, wrap=False):
    l = QLabel(text)
    l.setStyleSheet(f"color:{color};font-size:{size}px;font-weight:{'700' if bold else '400'};background:transparent;font-family:'Segoe UI';")
    if wrap: l.setWordWrap(True)
    return l

def combo_style():
    return f"""
        QComboBox{{color:{T};background:{W};border:1.5px solid {B};border-radius:8px;
                   padding:0 12px;font-size:13px;font-family:'Segoe UI';}}
        QComboBox:focus{{border-color:{G};}}
        QComboBox QAbstractItemView{{color:{T};background:{W};border:1px solid {B};
            selection-background-color:{A};outline:0;}}
        QComboBox QAbstractItemView::item{{color:{T};padding:8px 12px;min-height:28px;background:{W};}}
        QComboBox QAbstractItemView::item:hover{{background:{A};color:{T};}}
    """

def date_style():
    return f"QDateEdit{{color:{T};background:{W};border:1.5px solid {B};border-radius:8px;padding:0 10px;font-size:13px;font-family:'Segoe UI';}} QDateEdit:focus{{border-color:{G};}}"

def spin_style():
    return f"QDoubleSpinBox{{color:{T};background:{W};border:1.5px solid {B};border-radius:8px;padding:0 8px;font-size:13px;font-family:'Segoe UI';}} QDoubleSpinBox:focus{{border-color:{G};}}"


class Worker(QThread):
    done = pyqtSignal(object)
    err  = pyqtSignal(str)
    def __init__(self, fn, *a): super().__init__(); self.fn=fn; self.a=a
    def run(self):
        try: self.done.emit(self.fn(*self.a))
        except Exception as e: self.err.emit(str(e))


class ImageryPage(QWidget):
    def __init__(self):
        super().__init__()
        self.setStyleSheet(f"background:{P};")
        self.farms = []
        self.fields = []
        self._build()
        self._load_farms()

    def showEvent(self, event):
        super().showEvent(event)
        self._load_farms()

    def _build(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("QScrollArea{border:none;background:transparent;}")

        c = QWidget(); c.setStyleSheet(f"background:{P};")
        ml = QVBoxLayout(c); ml.setContentsMargins(0,0,8,0); ml.setSpacing(16)

        # ── Config card ───────────────────────────────────────────────────────
        cf = QFrame()
        cf.setStyleSheet(f"QFrame{{background:{W};border:1px solid {B};border-radius:12px;}}")
        cl = QVBoxLayout(cf); cl.setContentsMargins(20,16,20,16); cl.setSpacing(12)
        cl.addWidget(lbl("📡  Configure Satellite Analysis", 14, T, True))

        # Farm + Field row
        r1 = QHBoxLayout(); r1.setSpacing(12)
        r1.addWidget(lbl("Farm:", 12, M, True))
        self.farm_combo = QComboBox()
        self.farm_combo.setFixedHeight(38)
        self.farm_combo.setStyleSheet(combo_style())
        self.farm_combo.currentIndexChanged.connect(self._on_farm)
        r1.addWidget(self.farm_combo, 1)
        r1.addWidget(lbl("Field:", 12, M, True))
        self.field_combo = QComboBox()
        self.field_combo.setFixedHeight(38)
        self.field_combo.setEnabled(False)
        self.field_combo.setStyleSheet(combo_style())
        r1.addWidget(self.field_combo, 1)
        cl.addLayout(r1)

        # Date + Cloud + Button row
        r2 = QHBoxLayout(); r2.setSpacing(12)
        r2.addWidget(lbl("Start:", 12, M, True))
        self.start = QDateEdit(QDate(2024,1,1))
        self.start.setFixedHeight(38); self.start.setCalendarPopup(True)
        self.start.setStyleSheet(date_style())
        r2.addWidget(self.start)
        r2.addWidget(lbl("End:", 12, M, True))
        self.end = QDateEdit(QDate(2024,3,1))
        self.end.setFixedHeight(38); self.end.setCalendarPopup(True)
        self.end.setStyleSheet(date_style())
        r2.addWidget(self.end)
        r2.addWidget(lbl("Max Cloud:", 12, M, True))
        self.cloud = QDoubleSpinBox()
        self.cloud.setRange(0,100); self.cloud.setValue(30)
        self.cloud.setFixedHeight(38); self.cloud.setSuffix(" %")
        self.cloud.setStyleSheet(spin_style())
        r2.addWidget(self.cloud)
        cl.addLayout(r2)

        self.run_btn = QPushButton("🛰  Fetch & Analyse")
        self.run_btn.setFixedHeight(42)
        self.run_btn.setStyleSheet(f"QPushButton{{background:{G};color:white;border:none;border-radius:9px;font-size:13px;font-weight:600;font-family:'Segoe UI';}} QPushButton:hover{{background:#145a2b;}} QPushButton:disabled{{background:#9ca3af;}}")
        self.run_btn.clicked.connect(self._run)
        cl.addWidget(self.run_btn)

        self.status = lbl("", 12, M)
        cl.addWidget(self.status)
        ml.addWidget(cf)

        # ── Results card ──────────────────────────────────────────────────────
        self.res_f = QFrame()
        self.res_f.setStyleSheet(f"QFrame{{background:{W};border:1px solid {B};border-radius:12px;}}")
        self.res_l = QVBoxLayout(self.res_f)
        self.res_l.setContentsMargins(20,16,20,16); self.res_l.setSpacing(10)
        self.res_l.addWidget(lbl("📊  Latest Results", 14, T, True))
        self.idx_row = QHBoxLayout(); self.idx_row.setSpacing(10)
        self.res_l.addLayout(self.idx_row)
        self.interp_lbl = lbl("", 13, T, wrap=True)
        self.interp_lbl.setStyleSheet(f"color:{T};font-size:13px;padding:10px;background:#fefce8;border-radius:8px;border:1px solid #fde68a;font-family:'Segoe UI';")
        self.res_l.addWidget(self.interp_lbl)
        self.res_f.hide()
        ml.addWidget(self.res_f)

        # ── History table ─────────────────────────────────────────────────────
        hf = QFrame()
        hf.setStyleSheet(f"QFrame{{background:{W};border:1px solid {B};border-radius:12px;}}")
        hl = QVBoxLayout(hf); hl.setContentsMargins(20,16,20,16); hl.setSpacing(10)
        hl.addWidget(lbl("📅  Index History", 14, T, True))

        self.hist = QTableWidget()
        self.hist.setColumnCount(6)
        self.hist.setHorizontalHeaderLabels(["Date","NDVI","EVI","NDWI","NDRE","LAI"])
        self.hist.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.hist.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.hist.verticalHeader().setVisible(False)
        self.hist.setFixedHeight(200)
        self.hist.setAlternatingRowColors(True)
        self.hist.setStyleSheet(f"""
            QTableWidget{{color:{T};background:{W};border:none;font-size:13px;
                          font-family:'Segoe UI';gridline-color:#f3f4f6;
                          alternate-background-color:#f9fafb;}}
            QTableWidget::item{{color:{T};padding:8px 10px;}}
            QTableWidget::item:selected{{background:{A};color:{T};}}
            QHeaderView::section{{background:{DB};color:#f0ede6;padding:10px;
                                  font-size:12px;font-weight:600;border:none;font-family:'Segoe UI';}}
        """)
        hl.addWidget(self.hist)
        ml.addWidget(hf)
        ml.addStretch()

        scroll.setWidget(c)
        ol = QVBoxLayout(self); ol.setContentsMargins(0,0,0,0)
        ol.addWidget(scroll)

    def _load_farms(self):
        self._w = Worker(api.get_farms)
        self._w.done.connect(self._on_farms)
        self._w.start()

    def _on_farms(self, farms):
        self.farms = farms
        self.farm_combo.clear()
        self.farm_combo.addItem("Select farm...", None)
        for f in farms:
            self.farm_combo.addItem(f["name"], f["id"])

    def _on_farm(self):
        fid = self.farm_combo.currentData()
        if not fid: return
        self._fw = Worker(api.get_fields, fid)
        self._fw.done.connect(self._on_fields)
        self._fw.start()

    def _on_fields(self, fields):
        self.fields = fields
        self.field_combo.clear()
        self.field_combo.addItem("Select field...", None)
        for f in fields:
            self.field_combo.addItem(f"{f.get('name','')} ({f.get('crop_type','')})", f["id"])
        self.field_combo.setEnabled(True)

    def _run(self):
        fid = self.field_combo.currentData()
        if not fid:
            self.status.setText("⚠  Please select a field")
            self.status.setStyleSheet(f"color:{R};font-size:12px;background:transparent;")
            return
        self.run_btn.setEnabled(False)
        self.run_btn.setText("⏳  Fetching from GEE...")
        self.status.setStyleSheet(f"color:{M};font-size:12px;background:transparent;")
        self.status.setText("Contacting Google Earth Engine...")

        start = self.start.date().toString("yyyy-MM-dd")
        end   = self.end.date().toString("yyyy-MM-dd")
        cloud = self.cloud.value()

        self._rw = Worker(api.analyze_imagery, fid, start, end, cloud)
        self._rw.done.connect(self._on_result)
        self._rw.err.connect(self._on_err)
        self._rw.start()

    def _on_result(self, d):
        self.run_btn.setEnabled(True)
        self.run_btn.setText("🛰  Fetch & Analyse")

        if d.get("status") == "no_images":
            self.status.setStyleSheet(f"color:{GOLD};font-size:12px;background:transparent;")
            self.status.setText(f"⚠  {d.get('message','No images found')}")
            return

        self.status.setStyleSheet(f"color:{G};font-size:12px;background:transparent;")
        self.status.setText(f"✅  Found {d.get('images_found',0)} images — analysis complete")
        self._show_results(d)

        # Load history
        fid = self.field_combo.currentData()
        self._hw = Worker(api.get_index_history, fid)
        self._hw.done.connect(self._show_history)
        self._hw.start()

    def _on_err(self, msg):
        self.run_btn.setEnabled(True)
        self.run_btn.setText("🛰  Fetch & Analyse")
        self.status.setStyleSheet(f"color:{R};font-size:12px;background:transparent;")
        self.status.setText(f"❌  {msg}")

    def _show_results(self, d):
        # Clear index row
        while self.idx_row.count():
            item = self.idx_row.takeAt(0)
            if item.widget(): item.widget().deleteLater()

        idx = d.get("indices", {})
        colors = {"NDVI":G,"EVI":"#84cc16","NDWI":"#2563eb","NDRE":"#d97706"}
        for name, key in [("NDVI","ndvi"),("EVI","evi"),("NDWI","ndwi"),("NDRE","ndre")]:
            cell = QFrame()
            cell.setStyleSheet(f"QFrame{{background:{A};border:1px solid #b8d8c4;border-radius:10px;}}")
            cv = QVBoxLayout(cell); cv.setContentsMargins(14,10,14,10)
            cv.addWidget(lbl(name, 10, colors[name], True))
            cv.addWidget(lbl(f"{idx.get(key,0):.3f}", 22, T, True))
            self.idx_row.addWidget(cell)

        interp = d.get("interpretation", {})
        self.interp_lbl.setText(
            f"🌿 {interp.get('crop_health_status','')}  |  "
            f"💧 {interp.get('moisture_status','')}")
        self.res_f.show()

    def _show_history(self, history):
        self.hist.setRowCount(len(history))
        for r, row in enumerate(history):
            date = row.get("calculated_at","")[:10]
            item = QTableWidgetItem(date)
            item.setForeground(QColor(T))
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.hist.setItem(r, 0, item)
            for c, key in enumerate(["ndvi","evi","ndwi","ndre","lai"], 1):
                val = row.get(key)
                txt = f"{val:.3f}" if val is not None else "—"
                it = QTableWidgetItem(txt)
                it.setForeground(QColor(T))
                it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.hist.setItem(r, c, it)
