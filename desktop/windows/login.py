from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QFrame
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QColor, QPainter, QLinearGradient, QBrush
import desktop.api as api
from desktop.i18n import LM


class LoginWorker(QThread):
    success = pyqtSignal(str, dict)
    error   = pyqtSignal(str)
    def __init__(self, email, password):
        super().__init__()
        self.email = email; self.password = password
    def run(self):
        try:
            data  = api.login(self.email, self.password)
            token = data["access_token"]
            api.set_token(token)
            me = api.get_me()
            self.success.emit(token, me)
        except Exception as e:
            self.error.emit(str(e))


class LoginWindow(QWidget):
    login_success = pyqtSignal(dict)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("AgroSense")
        self.setFixedSize(920, 580)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self._worker = None
        self._drag_pos = None
        self._build()
        LM.language_changed.connect(self._retranslate)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        g = QLinearGradient(0, 0, 0, self.height())
        g.setColorAt(0, QColor("#0d2414"))
        g.setColorAt(1, QColor("#1a4a2a"))
        p.fillRect(0, 0, 420, self.height(), QBrush(g))
        p.fillRect(420, 0, self.width()-420, self.height(), QColor("#ffffff"))
        p.end()

    def mousePressEvent(self, e):
        self._drag_pos = e.globalPosition().toPoint()
    def mouseMoveEvent(self, e):
        if self._drag_pos:
            self.move(self.pos() + e.globalPosition().toPoint() - self._drag_pos)
            self._drag_pos = e.globalPosition().toPoint()
    def mouseReleaseEvent(self, e):
        self._drag_pos = None

    def _build(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(0,0,0,0)
        root.setSpacing(0)

        # LEFT panel
        left = QWidget()
        left.setFixedWidth(420)
        left.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        ll = QVBoxLayout(left)
        ll.setContentsMargins(48,44,48,44)
        ll.setSpacing(0)

        # Top-right row: lang toggle + close
        cr = QHBoxLayout()
        cr.addStretch()
        self.lang_btn = QPushButton(LM.tr("lang_toggle"))
        self.lang_btn.setFixedHeight(28)
        self.lang_btn.setStyleSheet(
            "QPushButton{background:rgba(255,255,255,0.12);color:rgba(255,255,255,0.8);"
            "border:none;border-radius:6px;font-size:11px;padding:0 8px;}"
            "QPushButton:hover{background:rgba(255,255,255,0.25);color:white;}")
        self.lang_btn.clicked.connect(LM.toggle)
        cr.addWidget(self.lang_btn)
        cr.addSpacing(6)
        cb = QPushButton("✕")
        cb.setFixedSize(28,28)
        cb.setStyleSheet(
            "QPushButton{background:rgba(255,255,255,0.1);color:rgba(255,255,255,0.6);"
            "border:none;border-radius:14px;font-size:12px;}"
            "QPushButton:hover{background:rgba(255,255,255,0.25);color:white;}")
        cb.clicked.connect(self.close)
        cr.addWidget(cb)
        ll.addLayout(cr)
        ll.addSpacing(20)

        icon = QLabel("🌿")
        icon.setStyleSheet("font-size:38px;background:transparent;")
        ll.addWidget(icon)
        ll.addSpacing(14)

        brand = QLabel("AgroSense")
        brand.setStyleSheet(
            "color:#ffffff;font-size:30px;font-weight:800;font-family:'Segoe UI';"
            "background:transparent;letter-spacing:-0.5px;")
        ll.addWidget(brand)
        ll.addSpacing(6)

        self.tag_lbl = QLabel(LM.tr("login_tagline"))
        self.tag_lbl.setStyleSheet(
            "color:rgba(255,255,255,0.6);font-size:14px;font-family:'Segoe UI';"
            "background:transparent;")
        ll.addWidget(self.tag_lbl)
        ll.addSpacing(32)

        feats = [
            ("🛰", "Real-time Sentinel-2 imagery"),
            ("🌿", "AI crop stress detection"),
            ("💧", "Smart irrigation planning"),
            ("📈", "Yield prediction & analytics"),
        ]
        for ico, txt in feats:
            row = QHBoxLayout(); row.setSpacing(10)
            i = QLabel(ico); i.setFixedWidth(22)
            i.setStyleSheet("font-size:13px;background:transparent;")
            t = QLabel(txt)
            t.setStyleSheet(
                "color:rgba(255,255,255,0.7);font-size:12.5px;"
                "font-family:'Segoe UI';background:transparent;")
            row.addWidget(i); row.addWidget(t); row.addStretch()
            ll.addLayout(row)
            ll.addSpacing(8)

        ll.addStretch()
        ver = QLabel("v1.0.0  ·  SMIU FYP 2025–2026")
        ver.setStyleSheet("color:rgba(255,255,255,0.25);font-size:10px;background:transparent;")
        ll.addWidget(ver)
        root.addWidget(left)

        # RIGHT panel
        right = QWidget()
        right.setStyleSheet("QWidget{background:#ffffff;}")
        rl = QVBoxLayout(right)
        rl.setContentsMargins(52,0,52,0)
        rl.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        rl.setSpacing(0)

        def lbl(text, size=13, color="#374151", bold=False, mt=0, mb=0):
            l = QLabel(text)
            w = "700" if bold else "400"
            l.setStyleSheet(
                f"color:{color};font-size:{size}px;font-weight:{w};"
                f"font-family:'Segoe UI';background:transparent;"
                f"margin-top:{mt}px;margin-bottom:{mb}px;")
            return l

        self.welcome_lbl = lbl(LM.tr("welcome_back"), 26, "#111827", True, mb=4)
        rl.addWidget(self.welcome_lbl)
        self.subtitle_lbl = lbl(LM.tr("signin_subtitle"), 13, "#6b7280", mb=28)
        rl.addWidget(self.subtitle_lbl)

        # Error frame
        self.err_frame = QFrame()
        self.err_frame.setStyleSheet(
            "QFrame{background:#fef2f2;border:1.5px solid #fecaca;border-radius:9px;}")
        efl = QHBoxLayout(self.err_frame)
        efl.setContentsMargins(12,9,12,9)
        self.err_lbl = QLabel("")
        self.err_lbl.setStyleSheet(
            "color:#dc2626;font-size:12.5px;font-family:'Segoe UI';background:transparent;")
        efl.addWidget(QLabel("⚠  ")); efl.addWidget(self.err_lbl, 1)
        self.err_frame.hide()
        rl.addWidget(self.err_frame)
        rl.addSpacing(4)

        inp_style = """
            QLineEdit{border:1.5px solid #d1d5db;border-radius:10px;padding:0 14px;
                      font-size:13px;font-family:'Segoe UI';color:#111827;background:#f9fafb;}
            QLineEdit:focus{border-color:#1a6b35;background:#ffffff;}
            QLineEdit:hover{border-color:#9ca3af;}
        """

        self.email_field_lbl = lbl(LM.tr("email_label_login"), 12.5, "#374151", True, mb=5)
        rl.addWidget(self.email_field_lbl)
        self.email_in = QLineEdit()
        self.email_in.setPlaceholderText("ali@agrosense.pk")
        self.email_in.setFixedHeight(44)
        self.email_in.setStyleSheet(inp_style)
        rl.addWidget(self.email_in)
        rl.addSpacing(14)

        self.pw_field_lbl = lbl(LM.tr("password_label_login"), 12.5, "#374151", True, mb=5)
        rl.addWidget(self.pw_field_lbl)
        self.pw_in = QLineEdit()
        self.pw_in.setPlaceholderText("Enter your password")
        self.pw_in.setEchoMode(QLineEdit.EchoMode.Password)
        self.pw_in.setFixedHeight(44)
        self.pw_in.setStyleSheet(inp_style)
        self.pw_in.returnPressed.connect(self._do_login)
        rl.addWidget(self.pw_in)
        rl.addSpacing(22)

        self.login_btn = QPushButton(LM.tr("signin_btn"))
        self.login_btn.setFixedHeight(46)
        self.login_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.login_btn.setStyleSheet("""
            QPushButton{background:#1a6b35;color:white;border:none;border-radius:10px;
                        font-size:14px;font-weight:600;font-family:'Segoe UI';}
            QPushButton:hover{background:#145a2b;}
            QPushButton:pressed{background:#0f4520;}
            QPushButton:disabled{background:#9ca3af;}
        """)
        self.login_btn.clicked.connect(self._do_login)
        rl.addWidget(self.login_btn)
        rl.addSpacing(16)

        # Divider
        drow = QHBoxLayout()
        for _ in range(2):
            ln = QFrame(); ln.setFrameShape(QFrame.Shape.HLine)
            ln.setStyleSheet("background:#e5e7eb;border:none;max-height:1px;")
            drow.addWidget(ln, 1)
        self.or_lbl = QLabel(LM.tr("or_divider"))
        self.or_lbl.setStyleSheet("color:#9ca3af;font-size:11px;background:transparent;")
        drow.insertWidget(1, self.or_lbl)
        rl.addLayout(drow)
        rl.addSpacing(16)

        self.reg_btn = QPushButton(LM.tr("create_account_link"))
        self.reg_btn.setFixedHeight(42)
        self.reg_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.reg_btn.setStyleSheet("""
            QPushButton{background:#f0fdf4;color:#1a6b35;border:1.5px solid #bbf7d0;
                        border-radius:10px;font-size:13px;font-weight:500;font-family:'Segoe UI';}
            QPushButton:hover{background:#dcfce7;border-color:#86efac;}
        """)
        self.reg_btn.clicked.connect(self._show_register)
        rl.addWidget(self.reg_btn)
        root.addWidget(right, 1)

    def _retranslate(self):
        self.lang_btn.setText(LM.tr("lang_toggle"))
        self.tag_lbl.setText(LM.tr("login_tagline"))
        self.welcome_lbl.setText(LM.tr("welcome_back"))
        self.subtitle_lbl.setText(LM.tr("signin_subtitle"))
        self.email_field_lbl.setText(LM.tr("email_label_login"))
        self.pw_field_lbl.setText(LM.tr("password_label_login"))
        if self.login_btn.isEnabled():
            self.login_btn.setText(LM.tr("signin_btn"))
        self.or_lbl.setText(LM.tr("or_divider"))
        self.reg_btn.setText(LM.tr("create_account_link"))

    def _do_login(self):
        email = self.email_in.text().strip()
        pw    = self.pw_in.text()
        if not email or not pw:
            self._show_error(LM.tr("enter_credentials"))
            return
        self.login_btn.setEnabled(False)
        self.login_btn.setText(LM.tr("signing_in"))
        self.err_frame.hide()
        self._worker = LoginWorker(email, pw)
        self._worker.success.connect(self._on_success)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_success(self, token, user):
        self.login_btn.setEnabled(True)
        self.login_btn.setText(LM.tr("signin_btn"))
        self.login_success.emit(user)

    def _on_error(self, msg):
        self.login_btn.setEnabled(True)
        self.login_btn.setText(LM.tr("signin_btn"))
        self._show_error(LM.tr("invalid_login"))

    def _show_error(self, msg):
        self.err_lbl.setText(msg)
        self.err_frame.show()

    def _show_register(self):
        from desktop.windows.register import RegisterWindow
        self._reg = RegisterWindow()
        self._reg.show()
