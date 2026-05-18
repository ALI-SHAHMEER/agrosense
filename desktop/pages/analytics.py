from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QFrame, QComboBox, QTableWidget, QTableWidgetItem, QHeaderView
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QRect
from PyQt6.QtGui import QPainter, QColor, QFont, QPen, QBrush
from desktop.theme import *
import desktop.api as api
from desktop.i18n import LM


class HistoryWorker(QThread):
    done = pyqtSignal(list)
    def __init__(self, field_id):
        super().__init__()
        self.field_id = field_id
    def run(self):
        try: self.done.emit(api.get_index_history(self.field_id))
        except: self.done.emit([])


class BarChart(QWidget):
    """Simple custom bar chart drawn with QPainter."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.data   = []   # list of (label, value, color)
        self.title  = ""
        self.y_max  = 1.0
        self.y_min  = -0.5
        self.setMinimumHeight(200)

    def set_data(self, title, data, y_min=-0.5, y_max=1.0):
        self.title = title
        self.data  = data
        self.y_min = y_min
        self.y_max = y_max
        self.update()

    def paintEvent(self, event):
        if not self.data:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        W, H = self.width(), self.height()
        pad_l, pad_r, pad_t, pad_b = 48, 16, 32, 40
        chart_w = W - pad_l - pad_r
        chart_h = H - pad_t - pad_b

        # Background
        p.fillRect(0, 0, W, H, QColor(WHITE))

        # Title
        p.setPen(QColor(TEXT))
        f = QFont("Segoe UI", 10, QFont.Weight.Bold)
        p.setFont(f)
        p.drawText(pad_l, 18, self.title)

        # Y axis grid
        p.setFont(QFont("Segoe UI", 8))
        y_range = self.y_max - self.y_min
        for i in range(5):
            val = self.y_min + y_range * i / 4
            y   = pad_t + chart_h - int((val - self.y_min) / y_range * chart_h)
            p.setPen(QPen(QColor("#e5e7eb"), 1, Qt.PenStyle.DashLine))
            p.drawLine(pad_l, y, W - pad_r, y)
            p.setPen(QColor(MUTED))
            p.drawText(2, y + 4, f"{val:.2f}")

        # Bars
        n    = len(self.data)
        bar_w = max(8, min(40, int(chart_w / n * 0.6)))
        gap   = chart_w / n

        for i, (label, value, color) in enumerate(self.data):
            cx = pad_l + int(gap * i + gap / 2)
            val_clamped = max(self.y_min, min(self.y_max, value or 0))
            bar_h = int(abs(val_clamped - max(0, self.y_min)) / y_range * chart_h)
            zero_y = pad_t + chart_h - int((max(0, self.y_min) - self.y_min) / y_range * chart_h)

            if val_clamped >= 0:
                bar_y = zero_y - bar_h
            else:
                bar_y = zero_y
                bar_h = int(abs(val_clamped) / y_range * chart_h)

            p.fillRect(cx - bar_w//2, bar_y, bar_w, bar_h, QColor(color))

            # Value label
            p.setPen(QColor(TEXT))
            p.setFont(QFont("Segoe UI", 7))
            v_txt = f"{value:.3f}" if value is not None else "—"
            p.drawText(cx - 18, bar_y - 4, 36, 12,
                       Qt.AlignmentFlag.AlignHCenter, v_txt)

            # X label
            p.setPen(QColor(MUTED))
            p.setFont(QFont("Segoe UI", 7))
            label_short = label[:8] if len(label) > 8 else label
            p.drawText(cx - 22, H - pad_b + 4, 44, 16,
                       Qt.AlignmentFlag.AlignHCenter, label_short)

        p.end()


class AnalyticsPage(QWidget):
    def __init__(self):
        super().__init__()
        self.setStyleSheet(f"background:{PAPER};")
        self._build()
        self._load_farms()
        LM.language_changed.connect(self._retranslate)

    def showEvent(self, event):
        super().showEvent(event)
        self._load_farms()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)

        combo_style = f"""
            QComboBox{{color:#111827;background:#ffffff;border:1.5px solid {BORDER};
                       border-radius:8px;padding:0 12px;font-size:13px;font-family:'Segoe UI';}}
            QComboBox:focus{{border-color:{GREEN};}}
            QComboBox QAbstractItemView{{color:#111827;background:#ffffff;
                border:1px solid {BORDER};selection-background-color:{ACCENT};}}
            QComboBox QAbstractItemView::item{{color:#111827;padding:8px 12px;min-height:28px;}}
            QComboBox QAbstractItemView::item:hover{{background:{ACCENT};}}
        """

        # Selector row
        sel = QFrame()
        sel.setStyleSheet(f"QFrame{{background:{WHITE};border:1px solid {BORDER};border-radius:12px;}}")
        sl = QHBoxLayout(sel)
        sl.setContentsMargins(16,12,16,12); sl.setSpacing(12)

        def lbl(t):
            l = QLabel(t)
            l.setStyleSheet(f"color:{TEXT};font-size:13px;font-family:'Segoe UI';background:transparent;")
            return l

        self.farm_combo = QComboBox()
        self.farm_combo.setFixedHeight(36)
        self.farm_combo.setStyleSheet(combo_style)
        self.farm_combo.currentIndexChanged.connect(self._on_farm_changed)

        self.field_combo = QComboBox()
        self.field_combo.setFixedHeight(36)
        self.field_combo.setEnabled(False)
        self.field_combo.setStyleSheet(combo_style)
        self.field_combo.currentIndexChanged.connect(self._on_field_changed)

        self.farm_lbl = lbl(LM.tr("farm_label"))
        self.field_lbl = lbl(LM.tr("field_label"))
        sl.addWidget(self.farm_lbl); sl.addWidget(self.farm_combo, 1)
        sl.addWidget(self.field_lbl); sl.addWidget(self.field_combo, 1)
        layout.addWidget(sel)

        # Charts row
        charts_row = QHBoxLayout()
        charts_row.setSpacing(14)

        veg_frame = QFrame()
        veg_frame.setStyleSheet(f"QFrame{{background:{WHITE};border:1px solid {BORDER};border-radius:12px;}}")
        vl = QVBoxLayout(veg_frame); vl.setContentsMargins(12,12,12,12)
        self.veg_chart = BarChart()
        self.veg_chart.setMinimumHeight(220)
        vl.addWidget(self.veg_chart)
        charts_row.addWidget(veg_frame, 1)

        wat_frame = QFrame()
        wat_frame.setStyleSheet(f"QFrame{{background:{WHITE};border:1px solid {BORDER};border-radius:12px;}}")
        wl = QVBoxLayout(wat_frame); wl.setContentsMargins(12,12,12,12)
        self.wat_chart = BarChart()
        self.wat_chart.setMinimumHeight(220)
        wl.addWidget(self.wat_chart)
        charts_row.addWidget(wat_frame, 1)
        layout.addLayout(charts_row)

        # History table
        tbl_frame = QFrame()
        tbl_frame.setStyleSheet(f"QFrame{{background:{WHITE};border:1px solid {BORDER};border-radius:12px;}}")
        tl = QVBoxLayout(tbl_frame); tl.setContentsMargins(16,14,16,14); tl.setSpacing(10)
        self.hist_title = QLabel(LM.tr("index_history_title"))
        self.hist_title.setStyleSheet(
            f"font-size:13.5px;font-weight:600;color:{TEXT};background:transparent;font-family:'Segoe UI';")
        tl.addWidget(self.hist_title)

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            LM.tr("tbl_date"), LM.tr("tbl_ndvi"), LM.tr("tbl_evi"),
            LM.tr("tbl_ndwi"), LM.tr("tbl_ndre"), LM.tr("tbl_lai")])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.setFixedHeight(160)
        self.table.setStyleSheet(f"""
            QTableWidget{{background:{WHITE};border:none;font-size:12.5px;font-family:'Segoe UI';color:{TEXT};}}
            QTableWidget::item{{color:{TEXT};padding:6px 10px;}}
            QTableWidget::item:selected{{background:{ACCENT};color:{TEXT};}}
            QHeaderView::section{{background:{DARK_BG};color:#f0ede6;padding:8px;font-size:11.5px;font-weight:600;border:none;}}
        """)
        tl.addWidget(self.table)
        layout.addWidget(tbl_frame)

        self.status_lbl = QLabel(LM.tr("select_farm_field_msg"))
        self.status_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_lbl.setStyleSheet(f"color:{MUTED};font-size:13px;background:transparent;font-family:'Segoe UI';")
        layout.addWidget(self.status_lbl)

    def _load_farms(self):
        from desktop.pages.farms import Worker as DataWorker
        self._w = DataWorker(api.get_farms)
        self._w.done.connect(self._populate_farms)
        self._w.start()

    def _populate_farms(self, farms):
        self.farm_combo.clear()
        self.farm_combo.addItem(LM.tr("select_farm_opt"), None)
        for f in farms:
            self.farm_combo.addItem(f["name"], f["id"])

    def _on_farm_changed(self):
        farm_id = self.farm_combo.currentData()
        if not farm_id: return
        from desktop.pages.farms import Worker as DataWorker
        self._fw = DataWorker(api.get_fields, farm_id)
        self._fw.done.connect(self._populate_fields)
        self._fw.start()

    def _populate_fields(self, fields):
        self.field_combo.clear()
        self.field_combo.addItem(LM.tr("select_field_opt"), None)
        for f in fields:
            self.field_combo.addItem(f"{f.get('name','')} ({f.get('crop_type','')})", f["id"])
        self.field_combo.setEnabled(True)

    def _on_field_changed(self):
        field_id = self.field_combo.currentData()
        if not field_id: return
        self.status_lbl.setText(LM.tr("loading_txt"))
        self._hw = HistoryWorker(field_id)
        self._hw.done.connect(self._render)
        self._hw.start()

    def _retranslate(self):
        self.farm_lbl.setText(LM.tr("farm_label"))
        self.field_lbl.setText(LM.tr("field_label"))
        self.hist_title.setText(LM.tr("index_history_title"))
        self.table.setHorizontalHeaderLabels([
            LM.tr("tbl_date"), LM.tr("tbl_ndvi"), LM.tr("tbl_evi"),
            LM.tr("tbl_ndwi"), LM.tr("tbl_ndre"), LM.tr("tbl_lai")])

    def _render(self, history):
        if not history:
            self.status_lbl.setText(LM.tr("no_history_msg"))
            return
        self.status_lbl.setText(f"{len(history)} data point(s)")
        rev = list(reversed(history))
        dates = [h.get("calculated_at","")[:10] for h in rev]

        # Vegetation chart
        veg_data = []
        colors = ["#16a34a","#84cc16","#d97706"]
        for key, color in zip(["ndvi","ndre","evi"], colors):
            for i, h in enumerate(rev):
                veg_data.append((dates[i] if len(rev)==1 else f"{key[:3]}{i+1}",
                                 h.get(key,0) or 0, color))
        # Simpler: one series per date
        self.veg_chart.set_data(
            "Vegetation Indices (NDVI per date)",
            [(dates[i], rev[i].get("ndvi",0) or 0, "#16a34a") for i in range(len(rev))],
            y_min=-0.2, y_max=1.0
        )
        self.wat_chart.set_data(
            "Water Index (NDWI per date)",
            [(dates[i], rev[i].get("ndwi",0) or 0, "#2563eb") for i in range(len(rev))],
            y_min=-0.5, y_max=0.5
        )

        # Table
        self.table.setRowCount(len(history))
        for r, row in enumerate(history):
            self.table.setItem(r, 0, QTableWidgetItem(row.get("calculated_at","")[:10]))
            for c, key in enumerate(["ndvi","evi","ndwi","ndre","lai"], 1):
                val = row.get(key)
                item = QTableWidgetItem(f"{val:.3f}" if val is not None else "—")
                item.setForeground(QColor(TEXT))
                self.table.setItem(r, c, item)
