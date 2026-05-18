from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QLineEdit, QComboBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QDialog, QMessageBox, QFrame
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QColor
import desktop.api as api
from desktop.i18n import LM

G="#1a6b35"; W="#ffffff"; P="#f4f6f4"; T="#111827"
M="#6b7280"; B="#e2e8e4"; A="#e8f5ee"; R="#dc2626"; DB="#0b1f10"

def mk_label(text, size=13, color="#111827", bold=False):
    l = QLabel(text)
    l.setStyleSheet(f"color:{color};font-size:{size}px;font-weight:{'700' if bold else '400'};background:transparent;font-family:'Segoe UI';")
    return l

def mk_input(ph=""):
    i = QLineEdit(); i.setPlaceholderText(ph); i.setFixedHeight(38)
    i.setStyleSheet(f"QLineEdit{{color:{T};background:{W};border:1.5px solid {B};border-radius:8px;padding:0 12px;font-size:13px;font-family:'Segoe UI';}} QLineEdit:focus{{border-color:{G};}}")
    return i

def mk_btn(text, color=G, w=None):
    b = QPushButton(text); b.setFixedHeight(38)
    if w: b.setFixedWidth(w)
    b.setStyleSheet(f"QPushButton{{background:{color};color:white;border:none;border-radius:8px;font-size:13px;font-weight:600;font-family:'Segoe UI';padding:0 14px;}} QPushButton:hover{{opacity:0.9;}}")
    return b

class Worker(QThread):
    done = pyqtSignal(object)
    err  = pyqtSignal(str)
    def __init__(self, fn, *a): super().__init__(); self.fn=fn; self.a=a
    def run(self):
        try: self.done.emit(self.fn(*self.a))
        except Exception as e: self.err.emit(str(e))

class AddFarmDialog(QDialog):
    created = pyqtSignal()
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(LM.tr("add_farm_dialog_title"))
        self.setFixedWidth(400)
        self.setStyleSheet(f"background:{W};")
        self._build()

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
        self.sb = mk_btn(LM.tr("add_farm_save_btn"))
        self.sb.clicked.connect(self._save)
        row.addWidget(cb); row.addStretch(); row.addWidget(self.sb)
        l.addLayout(row)

    def _save(self):
        name = self.inputs["name"].text().strip()
        if not name:
            self.err.setText(LM.tr("form_farm_name") + " required")
            self.err.show(); return
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

class AddFieldDialog(QDialog):
    created = pyqtSignal()
    def __init__(self, farm_id, farm_name, parent=None):
        super().__init__(parent)
        self.farm_id = farm_id
        self.setWindowTitle(f"{LM.tr('add_field_dialog_title')} — {farm_name}")
        self.setFixedWidth(400)
        self.setStyleSheet(f"background:{W};")
        self._build(farm_name)

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
        self.sb = mk_btn(LM.tr("add_field_save_btn"))
        self.sb.clicked.connect(self._save)
        row.addWidget(cb); row.addStretch(); row.addWidget(self.sb)
        l.addLayout(row)

    def _save(self):
        self.sb.setEnabled(False); self.sb.setText(LM.tr("saving_btn"))
        try:
            result = api.create_field(
                self.farm_id,
                self.inputs["name"].text().strip(),
                self.crop_combo.currentText(),
                self.inputs["area_ha"].text() or None)
            print(f"✅ Field created: {result}")
            self.created.emit(); self.accept()
        except Exception as e:
            self.err.setText(str(e)); self.err.show()
            self.sb.setEnabled(True); self.sb.setText(LM.tr("add_field_save_btn"))

class FarmsPage(QWidget):
    def __init__(self):
        super().__init__()
        self.setStyleSheet(f"background:{P};")
        self._farms = []
        self._selected_farm_id = None
        self._selected_farm_name = ""
        self._workers = []
        self._build()
        self._load_farms()
        LM.language_changed.connect(self._retranslate)

    def _build(self):
        l = QVBoxLayout(self); l.setContentsMargins(0,0,0,0); l.setSpacing(14)

        # Header row
        hr = QHBoxLayout(); hr.addStretch()
        add_btn = mk_btn(LM.tr("add_farm_btn"), w=140)
        add_btn.clicked.connect(self._add_farm)
        hr.addWidget(add_btn)
        self.del_farm_btn = mk_btn(LM.tr("del_farm_btn"), color=R, w=160)
        self.del_farm_btn.setEnabled(False)
        self.del_farm_btn.clicked.connect(
            lambda: self._del_farm(self._selected_farm_id))
        hr.addWidget(self.del_farm_btn)
        l.addLayout(hr)

        # Selected farm indicator
        self.sel_lbl = QLabel(LM.tr("no_farm_selected"))
        self.sel_lbl.setStyleSheet(f"color:{M};font-size:12px;background:#fffbeb;border:1px solid #fde68a;border-radius:8px;padding:8px 14px;font-family:'Segoe UI';")
        l.addWidget(self.sel_lbl)

        # Farms table
        self.farm_tbl = QTableWidget()
        self.farm_tbl.setColumnCount(4)
        self.farm_tbl.setHorizontalHeaderLabels([
            LM.tr("farm_tbl_name"), LM.tr("farm_tbl_district"),
            LM.tr("farm_tbl_province"), LM.tr("farm_tbl_area"),
        ])
        self.farm_tbl.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.farm_tbl.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.farm_tbl.verticalHeader().setVisible(False)
        self.farm_tbl.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.farm_tbl.setAlternatingRowColors(True)
        self.farm_tbl.setFixedHeight(180)
        self.farm_tbl.setStyleSheet(f"""
            QTableWidget{{color:{T};background:{W};border:1px solid {B};border-radius:10px;
                          font-size:13px;font-family:'Segoe UI';alternate-background-color:#f9fafb;}}
            QTableWidget::item{{color:{T};padding:8px 12px;}}
            QTableWidget::item:selected{{background:#dbeafe;color:{T};}}
            QHeaderView::section{{background:{DB};color:#f0ede6;padding:10px;font-size:12px;font-weight:600;border:none;}}
        """)
        self.farm_tbl.selectionModel().selectionChanged.connect(self._on_selection)
        l.addWidget(self.farm_tbl)

        # Fields section
        fhr = QHBoxLayout()
        self.fields_section_lbl = mk_label(LM.tr("fields_section"), 14, T, True)
        fhr.addWidget(self.fields_section_lbl)
        fhr.addStretch()
        self.add_field_btn = mk_btn(LM.tr("add_field_btn"), w=130)
        self.add_field_btn.setEnabled(False)
        self.add_field_btn.clicked.connect(self._add_field)
        fhr.addWidget(self.add_field_btn)
        l.addLayout(fhr)

        self.field_tbl = QTableWidget()
        self.field_tbl.setColumnCount(4)
        self.field_tbl.setHorizontalHeaderLabels([
            LM.tr("field_tbl_name"), LM.tr("field_tbl_crop"),
            LM.tr("field_tbl_area"), LM.tr("field_tbl_id"),
        ])
        self.field_tbl.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.field_tbl.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.field_tbl.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.field_tbl.verticalHeader().setVisible(False)
        self.field_tbl.setAlternatingRowColors(True)
        self.field_tbl.setStyleSheet(f"""
            QTableWidget{{color:{T};background:{W};border:1px solid {B};border-radius:10px;
                          font-size:13px;font-family:'Segoe UI';alternate-background-color:#f9fafb;}}
            QTableWidget::item{{color:{T};padding:8px 12px;}}
            QTableWidget::item:selected{{background:{A};color:{T};}}
            QHeaderView::section{{background:{DB};color:#f0ede6;padding:10px;font-size:12px;font-weight:600;border:none;}}
        """)
        l.addWidget(self.field_tbl)

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

    def _load_farms(self):
        w = Worker(api.get_farms)
        self._workers.append(w)
        w.done.connect(self._on_farms_loaded)
        w.err.connect(lambda e: self.sel_lbl.setText(f"Error: {e}"))
        w.finished.connect(lambda: self._workers.remove(w) if w in self._workers else None)
        w.start()

    def _on_farms_loaded(self, farms):
        self._farms = farms
        self.farm_tbl.clearContents()
        self.farm_tbl.setRowCount(len(farms))
        for r, farm in enumerate(farms):
            for c, val in enumerate([farm.get("name",""), farm.get("district",""),
                                      farm.get("province",""), str(farm.get("area_ha",""))]):
                item = QTableWidgetItem(val)
                item.setForeground(QColor(T))
                item.setData(Qt.ItemDataRole.UserRole, farm["id"])
                self.farm_tbl.setItem(r, c, item)
        self.sel_lbl.setText(f"{len(farms)} farm(s) — click a row to select it")

    def _on_selection(self, selected, deselected):
        indexes = selected.indexes()
        if not indexes: return
        row = indexes[0].row()
        if row < 0 or row >= len(self._farms): return
        farm = self._farms[row]
        self._selected_farm_id   = farm["id"]
        self._selected_farm_name = farm.get("name","Farm")
        self.add_field_btn.setEnabled(True)
        self.del_farm_btn.setEnabled(True)
        self.sel_lbl.setStyleSheet(
            f"color:#15803d;font-size:12px;background:#f0fdf4;"
            f"border:1px solid #86efac;border-radius:8px;padding:8px 14px;font-family:'Segoe UI';")
        self.sel_lbl.setText(f"✅ Selected: {self._selected_farm_name}")
        self._load_fields(farm["id"])

    def _load_fields(self, farm_id):
        w = Worker(api.get_fields, farm_id)
        self._workers.append(w)
        w.done.connect(self._on_fields_loaded)
        w.finished.connect(lambda: self._workers.remove(w) if w in self._workers else None)
        w.start()

    def _on_fields_loaded(self, fields):
        self.field_tbl.clearContents()
        self.field_tbl.setRowCount(len(fields))
        for r, f in enumerate(fields):
            for c, val in enumerate([f.get("name",""), f.get("crop_type",""),
                                      str(f.get("area_ha","")), f.get("id","")]):
                item = QTableWidgetItem(val)
                item.setForeground(QColor(T))
                self.field_tbl.setItem(r, c, item)

    def _add_farm(self):
        d = AddFarmDialog(self)
        d.created.connect(self._load_farms)
        d.exec()

    def _add_field(self):
        if not self._selected_farm_id:
            QMessageBox.information(self, LM.tr("no_farm_sel_title"), LM.tr("no_farm_sel_msg"))
            return
        d = AddFieldDialog(self._selected_farm_id, self._selected_farm_name, self)
        d.created.connect(lambda: self._load_fields(self._selected_farm_id))
        d.exec()

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
                QMessageBox.warning(self, LM.tr("error_title"), str(e))
