from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QPushButton, QComboBox, QGridLayout, QScrollArea, QMessageBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
import desktop.api as api
from desktop.i18n import LM

G="#1a6b35"; GB="#0d2414"; W="#ffffff"; P="#f4f6f4"
T="#111827"; M="#6b7280"; B="#e2e8e4"; A="#e8f5ee"
BLUE="#2563eb"; PURPLE="#7c3aed"; GOLD="#d4a017"
RED="#dc2626"; EMERALD="#22c55e"

def lbl(text, size=13, color="#111827", bold=False, wrap=False):
    l = QLabel(text)
    w = "700" if bold else "400"
    l.setStyleSheet(f"color:{color};font-size:{size}px;font-weight:{w};background:transparent;font-family:'Segoe UI';")
    if wrap: l.setWordWrap(True)
    return l

def card():
    f = QFrame()
    f.setStyleSheet(f"QFrame{{background:{W};border:1px solid {B};border-radius:12px;}}")
    l = QVBoxLayout(f)
    l.setContentsMargins(20,16,20,16)
    l.setSpacing(10)
    return f, l

def btn(text, color=G, hover=None):
    b = QPushButton(text)
    h = hover or color
    b.setFixedHeight(40)
    b.setStyleSheet(f"QPushButton{{background:{color};color:white;border:none;border-radius:9px;font-size:13px;font-weight:600;font-family:'Segoe UI';padding:0 16px;}} QPushButton:hover{{background:{h};}} QPushButton:disabled{{background:#9ca3af;}}")
    return b

class Worker(QThread):
    done = pyqtSignal(object)
    err  = pyqtSignal(str)
    def __init__(self, fn, *a): super().__init__(); self.fn=fn; self.a=a
    def run(self):
        try: self.done.emit(self.fn(*self.a))
        except Exception as e: self.err.emit(str(e))

class PDFWorker(QThread):
    done = pyqtSignal(str)
    err  = pyqtSignal(str)
    def __init__(self, data, path, language="en"):
        super().__init__()
        self.data     = data
        self.path     = path
        self.language = language
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

class DashboardPage(QWidget):
    def __init__(self):
        super().__init__()
        self.setStyleSheet(f"background:{P};")
        self._last_d    = None
        self._workers   = []
        self._pdf_worker = None
        self._build()
        self._load()
        LM.language_changed.connect(self._retranslate)

    def showEvent(self, event):
        super().showEvent(event)
        self._load()

    def _build(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea{border:none;background:transparent;}")
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        c = QWidget(); c.setStyleSheet(f"background:{P};")
        ml = QVBoxLayout(c); ml.setContentsMargins(0,0,8,0); ml.setSpacing(16)

        # Stats
        sr = QHBoxLayout(); sr.setSpacing(14)
        stat_keys = ["stat_farms", "stat_fields", "stat_health", "stat_yield", "stat_temp"]
        stat_cols = [G, BLUE, EMERALD, GOLD, RED]
        self._sv = []
        self._sl = []
        for key, col in zip(stat_keys, stat_cols):
            f = QFrame()
            f.setFixedHeight(110)
            f.setStyleSheet(f"QFrame{{background:{W};border:1px solid {B};border-radius:12px;}}")
            fl = QVBoxLayout(f); fl.setContentsMargins(20,14,20,14)
            sl = lbl(LM.tr(key), 11, M)
            fl.addWidget(sl)
            v = lbl("—", 28, col, True)
            fl.addWidget(v)
            self._sv.append(v)
            self._sl.append((sl, key))
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
        self.combo.currentIndexChanged.connect(self._fetch_temp)
        row.addWidget(self.combo, 1)
        self.run_btn = btn(LM.tr("run_analysis"))
        self.run_btn.setFixedWidth(160)
        self.run_btn.clicked.connect(self._run)
        row.addWidget(self.run_btn)

        ref_btn = QPushButton("🔄")
        ref_btn.setFixedSize(44, 40)
        ref_btn.setStyleSheet("QPushButton{background:#374151;color:white;border:none;border-radius:9px;font-size:14px;} QPushButton:hover{background:#1f2937;}")
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

        # Results
        self.res_f, self.res_l = card()
        self.res_f.hide()
        ml.addWidget(self.res_f)
        ml.addStretch()

        scroll.setWidget(c)
        ol = QVBoxLayout(self); ol.setContentsMargins(0,0,0,0)
        ol.addWidget(scroll)

    def _load(self):
        def fetch():
            farms = api.get_farms()
            fields = []
            for farm in farms:
                for f in api.get_fields(farm["id"]):
                    f["farm_name"] = farm["name"]
                    fields.append(f)
            return farms, fields
        w = Worker(fetch)
        self._workers.append(w)
        w.done.connect(self._on_loaded)
        w.err.connect(self._on_err)
        w.finished.connect(lambda: self._workers.remove(w) if w in self._workers else None)
        w.start()

    def _on_loaded(self, result):
        farms, fields = result
        self._sv[0].setText(str(len(farms)))
        self._sv[1].setText(str(len(fields)))
        self.combo.clear()
        for f in fields:
            self.combo.addItem(
                f"{f.get('name','?')} — {f.get('crop_type','?')} ({f.get('farm_name','')})",
                f["id"])

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
        # Store field_id and token for PDF
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

    def _show(self, d):
        while self.res_l.count():
            item = self.res_l.takeAt(0)
            if item.widget(): item.widget().deleteLater()

        idx    = d.get("vegetation_indices",  {})
        stress = d.get("crop_stress",         {})
        irrig  = d.get("irrigation",          {})
        yld    = d.get("yield_prediction",    {})
        soil   = d.get("soil_assessment",     {})
        vra    = d.get("vra_zones",           {})

        self.res_l.addWidget(lbl(
            f"📊  Results — {d.get('field_name','')} ({d.get('crop_type','')})",
            14, T, True))

        # Index badges
        ir = QHBoxLayout(); ir.setSpacing(10)
        for name, key, col in [("NDVI","ndvi",G),("EVI","evi","#84cc16"),
                                 ("NDWI","ndwi",BLUE),("NDRE","ndre","#d97706")]:
            cell = QFrame()
            cell.setStyleSheet(f"QFrame{{background:{A};border:1px solid #b8d8c4;border-radius:10px;}}")
            cv = QVBoxLayout(cell); cv.setContentsMargins(14,10,14,10)
            cv.addWidget(lbl(name, 10, col, True))
            val = idx.get(key) or 0
            cv.addWidget(lbl(f"{val:.3f}", 22, T, True))
            ir.addWidget(cell)
        self.res_l.addLayout(ir)

        # 2x2 result cards
        grid = QGridLayout(); grid.setSpacing(12)
        pred = stress.get("prediction","—")
        sc   = {"Healthy":G,"Stressed":GOLD,"Diseased":RED}.get(pred, M)
        rec  = irrig.get("recommendation","—").replace("_"," ").title()

        def rcard(title, main, sub, col):
            f = QFrame()
            f.setStyleSheet(f"QFrame{{background:{W};border:1px solid {B};border-radius:10px;}}")
            l = QVBoxLayout(f); l.setContentsMargins(16,14,16,14); l.setSpacing(5)
            l.addWidget(lbl(title, 11, M, True))
            l.addWidget(lbl(main, 18, col, True))
            l.addWidget(lbl(sub, 11, M, False, True))
            return f

        grid.addWidget(rcard("🌿  Crop Health", pred,
            f"Confidence: {stress.get('confidence',0)*100:.0f}%", sc), 0, 0)
        grid.addWidget(rcard("💧  Irrigation", rec,
            f"Soil: {irrig.get('soil_moisture_pct',0):.1f}%  ·  Water: {irrig.get('water_amount_mm',0):.0f} mm",
            BLUE), 0, 1)
        grid.addWidget(rcard("📈  Yield",
            f"{yld.get('predicted_yield_tha',0):.2f} t/ha",
            f"Range: {yld.get('yield_lower_bound',0):.2f}–{yld.get('yield_upper_bound',0):.2f} t/ha",
            PURPLE), 1, 0)
        grid.addWidget(rcard("🧪  Soil",
            f"pH {soil.get('soil_ph',0):.1f}",
            f"Salinity: {soil.get('salinity_ds_m',0):.2f} dS/m  ·  OM: {soil.get('organic_matter_pct',0):.2f}%",
            GOLD), 1, 1)
        self.res_l.addLayout(grid)

        # VRA banner
        vw = QLabel(f"🗺  Fertility Zone: <b>{vra.get('zone','—')}</b>  ·  {vra.get('fertiliser_recommendation','')}")
        vw.setWordWrap(True)
        vw.setStyleSheet(f"color:{T};font-size:13px;padding:12px;background:{A};border-radius:9px;border:1px solid #b8d8c4;font-family:'Segoe UI';")
        self.res_l.addWidget(vw)

        self._sv[2].setText(pred)
        self._sv[3].setText(f"{yld.get('predicted_yield_tha',0):.1f} t/ha")
        self.res_f.show()

    def _retranslate(self):
        for sl, key in self._sl:
            sl.setText(LM.tr(key))
        self.analysis_title_lbl.setText(LM.tr("analysis_title"))
        if self.run_btn.isEnabled():
            self.run_btn.setText(LM.tr("run_analysis"))
        if self.pdf_btn.isEnabled():
            self.pdf_btn.setText(LM.tr("export_pdf"))
        if self.alt_btn.isEnabled():
            self.alt_btn.setText(LM.tr("send_alert"))

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

        self._pdf_worker = PDFWorker(data, self._pdf_path, language=LM.current_lang)
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
