
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
import desktop.api as api

NAV = [
    ("dashboard", "🏠  Dashboard",         DashboardPage),
    ("farms",     "🗺  Farms & Fields",    FarmsPage),
    ("imagery",   "🛰  Satellite Imagery", ImageryPage),
    ("analytics", "📊  Analytics",          AnalyticsPage),
    ("map",       "🗺  Map View",           MapPage),
    ("bands",     "🛰  Band View",          BandViewPage),
]

G = "#1a6b35"; GB = "#0d2414"; W = "#ffffff"; P = "#f4f6f4"
T = "#111827"; M = "#6b7280"; B = "#e2e8e4"

class MainWindow(QMainWindow):
    def __init__(self, user):
        super().__init__()
        self.user = user
        self.setWindowTitle("AgroSense — Crop Intelligence")
        self.resize(1200, 760)
        self.setMinimumSize(1000, 650)
        self._btns = {}
        self._pages = {}
        self._build()
        self._go("dashboard")

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

        # Logo
        logo = QWidget()
        logo.setFixedHeight(64)
        logo.setStyleSheet(f"background:{GB}; border-bottom: 1px solid rgba(255,255,255,0.08);")
        ll = QHBoxLayout(logo)
        ll.setContentsMargins(18,0,18,0)
        ic = QLabel("🌿"); ic.setStyleSheet("font-size:20px; background:transparent; color:white;")
        nm = QLabel("AgroSense"); nm.setStyleSheet("color:#f0ede6; font-size:15px; font-weight:700; background:transparent;")
        ll.addWidget(ic); ll.addWidget(nm); ll.addStretch()
        vl.addWidget(logo)

        sec = QLabel("MAIN MENU")
        sec.setStyleSheet("color:#3a6b4a; font-size:9px; font-weight:700; letter-spacing:2px; padding:14px 20px 6px; background:transparent;")
        vl.addWidget(sec)

        nav = QWidget(); nav.setStyleSheet(f"background:{GB};")
        nl = QVBoxLayout(nav); nl.setContentsMargins(10,0,10,8); nl.setSpacing(2)
        for key, label, Cls in NAV:
            b = QPushButton(label)
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

        # User
        uw = QWidget(); uw.setStyleSheet(f"background:{GB};")
        ul = QVBoxLayout(uw); ul.setContentsMargins(18,12,18,14); ul.setSpacing(3)
        rb = QLabel(f" {self.user.get('role','').upper()} ")
        rb.setFixedWidth(60)
        rb.setAlignment(Qt.AlignmentFlag.AlignCenter)
        rb.setStyleSheet("background:#1a4a2a; color:#4ade80; font-size:9px; font-weight:700; border-radius:4px; padding:2px 0;")
        nm2 = QLabel(self.user.get("name",""))
        nm2.setStyleSheet("color:#f0ede6; font-size:13px; font-weight:600; background:transparent;")
        em = QLabel(self.user.get("email",""))
        em.setStyleSheet("color:#5a9470; font-size:10px; background:transparent;")
        lo = QPushButton("⎋  Sign out")
        lo.setStyleSheet("QPushButton{background:transparent;border:none;color:#4a7a5a;font-size:11px;text-align:left;padding:4px 0;} QPushButton:hover{color:#f87171;}")
        lo.clicked.connect(self._logout)
        ul.addWidget(rb); ul.addSpacing(4)
        ul.addWidget(nm2); ul.addWidget(em); ul.addSpacing(6); ul.addWidget(lo)
        vl.addWidget(uw)
        return sb

    def _content(self):
        cw = QWidget(); cw.setStyleSheet(f"background:{P};")
        cl = QVBoxLayout(cw); cl.setContentsMargins(0,0,0,0); cl.setSpacing(0)

        # Topbar
        tb = QWidget(); tb.setFixedHeight(54)
        tb.setStyleSheet(f"background:{W}; border-bottom:1px solid {B};")
        tl = QHBoxLayout(tb); tl.setContentsMargins(28,0,28,0)
        self.tb_title = QLabel("Dashboard")
        self.tb_title.setStyleSheet(f"color:{T}; font-size:15px; font-weight:600; background:transparent;")
        self.tb_sub = QLabel("Crop intelligence overview")
        self.tb_sub.setStyleSheet(f"color:{M}; font-size:12px; background:transparent;")
        dot = QLabel("● Connected")
        dot.setStyleSheet("color:#16a34a; font-size:11px; background:transparent;")
        tl.addWidget(self.tb_title); tl.addSpacing(10)
        tl.addWidget(self.tb_sub); tl.addStretch(); tl.addWidget(dot)
        cl.addWidget(tb)

        # Pages
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
            return f"QPushButton{{background:{G};color:white;border:none;border-radius:8px;font-size:13px;text-align:left;padding:0 14px;}}"
        return f"QPushButton{{background:transparent;color:#7aaa8a;border:none;border-radius:8px;font-size:13px;text-align:left;padding:0 14px;}} QPushButton:hover{{background:rgba(255,255,255,0.07);color:#c8e6d0;}}"

    def _go(self, key):
        subs = {"dashboard":"Crop intelligence overview","farms":"Manage farms and fields",
                "imagery":"Fetch and analyse Sentinel-2 data","analytics":"Index trends over time",
                "map":"Farm locations on satellite map","bands":"Sentinel-2 band composites per field"}
        titles = {"dashboard":"Dashboard","farms":"Farms & Fields","imagery":"Satellite Imagery",
                  "analytics":"Analytics","map":"Map View","bands":"Band View"}
        self.tb_title.setText(titles.get(key, key))
        self.tb_sub.setText(subs.get(key,""))
        if key in self._pages:
            self.stack.setCurrentWidget(self._pages[key])
        for k,b in self._btns.items():
            b.setStyleSheet(self._ns(k==key))

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

# Scrollbar fix applied at module level
