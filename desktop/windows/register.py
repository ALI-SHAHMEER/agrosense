from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QFrame, QComboBox, QMessageBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
import desktop.api as api
from desktop.i18n import LM

T="#111827"; G="#1a6b35"; B="#e2e8e4"; W="#ffffff"; R="#dc2626"; M="#6b7280"

def inp(ph="", pw=False):
    i = QLineEdit()
    i.setPlaceholderText(ph)
    i.setFixedHeight(42)
    if pw: i.setEchoMode(QLineEdit.EchoMode.Password)
    i.setStyleSheet(
        f"QLineEdit{{color:{T};background:{W};border:1.5px solid {B};"
        f"border-radius:9px;padding:0 14px;font-size:13px;font-family:'Segoe UI';}}"
        f"QLineEdit:focus{{border-color:{G};}}")
    return i


class RegWorker(QThread):
    success = pyqtSignal()
    error   = pyqtSignal(str)
    def __init__(self, name, email, password, role):
        super().__init__()
        self.name=name; self.email=email
        self.password=password; self.role=role
    def run(self):
        try:
            api.register(self.name, self.email, self.password, self.role)
            self.success.emit()
        except Exception as e:
            self.error.emit(str(e))


class RegisterWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AgroSense — Register")
        self.setFixedSize(460, 580)
        self.setStyleSheet("background:#0b1f10;")
        self._build()
        LM.language_changed.connect(self._retranslate)

    def _build(self):
        root = QVBoxLayout(self)
        root.setAlignment(Qt.AlignmentFlag.AlignCenter)

        card = QFrame()
        card.setStyleSheet(f"QFrame{{background:{W};border-radius:16px;}}")
        card.setFixedWidth(400)
        cl = QVBoxLayout(card)
        cl.setContentsMargins(40, 32, 40, 32)
        cl.setSpacing(0)

        def lbl(text, size=13, color="#374151", bold=False):
            l = QLabel(text)
            l.setStyleSheet(
                f"color:{color};font-size:{size}px;"
                f"font-weight:{'700' if bold else '400'};"
                f"background:transparent;font-family:'Segoe UI';")
            return l

        self.title_lbl = lbl(LM.tr("create_account_title"), 22, T, True)
        cl.addWidget(self.title_lbl)
        cl.addSpacing(4)
        self.sub_lbl = lbl(LM.tr("monitor_crops"), 13, M)
        cl.addWidget(self.sub_lbl)
        cl.addSpacing(24)

        self.err = QLabel("")
        self.err.setStyleSheet(
            f"color:{R};background:#fef2f2;border:1px solid #fecaca;"
            f"border-radius:8px;padding:8px 12px;font-size:12px;font-family:'Segoe UI';")
        self.err.hide()
        cl.addWidget(self.err)
        cl.addSpacing(4)

        self.name_lbl = lbl(LM.tr("full_name_label"), 12, "#374151", True)
        cl.addWidget(self.name_lbl)
        cl.addSpacing(4)
        self.name_in = inp("Ali Hassan")
        cl.addWidget(self.name_in)
        cl.addSpacing(12)

        self.email_lbl = lbl(LM.tr("email_reg_label"), 12, "#374151", True)
        cl.addWidget(self.email_lbl)
        cl.addSpacing(4)
        self.email_in = inp("ali@agrosense.pk")
        cl.addWidget(self.email_in)
        cl.addSpacing(12)

        self.pw_lbl = lbl(LM.tr("password_reg_label"), 12, "#374151", True)
        cl.addWidget(self.pw_lbl)
        cl.addSpacing(4)
        self.pw_in = inp(LM.tr("reg_password_ph"), pw=True)
        cl.addWidget(self.pw_in)
        cl.addSpacing(12)

        self.role_lbl = lbl(LM.tr("role_label"), 12, "#374151", True)
        cl.addWidget(self.role_lbl)
        cl.addSpacing(4)
        self.role = QComboBox()
        self.role.addItems(["farmer", "analyst", "admin"])
        self.role.setFixedHeight(42)
        self.role.setStyleSheet(f"""
            QComboBox{{color:{T};background:{W};border:1.5px solid {B};border-radius:9px;
                       padding:0 14px;font-size:13px;font-family:'Segoe UI';}}
            QComboBox QAbstractItemView{{color:{T};background:{W};border:1px solid {B};}}
            QComboBox QAbstractItemView::item{{color:{T};padding:8px;background:{W};}}
            QComboBox QAbstractItemView::item:hover{{background:#e8f5ee;}}
        """)
        cl.addWidget(self.role)
        cl.addSpacing(20)

        self.btn = QPushButton(LM.tr("create_account_btn"))
        self.btn.setFixedHeight(46)
        self.btn.setStyleSheet(f"""
            QPushButton{{background:{G};color:white;border:none;border-radius:10px;
                         font-size:14px;font-weight:600;font-family:'Segoe UI';}}
            QPushButton:hover{{background:#145a2b;}}
            QPushButton:disabled{{background:#9ca3af;}}
        """)
        self.btn.clicked.connect(self._register)
        cl.addWidget(self.btn)

        root.addWidget(card)

    def _retranslate(self):
        self.title_lbl.setText(LM.tr("create_account_title"))
        self.sub_lbl.setText(LM.tr("monitor_crops"))
        self.name_lbl.setText(LM.tr("full_name_label"))
        self.email_lbl.setText(LM.tr("email_reg_label"))
        self.pw_lbl.setText(LM.tr("password_reg_label"))
        self.pw_in.setPlaceholderText(LM.tr("reg_password_ph"))
        self.role_lbl.setText(LM.tr("role_label"))
        if self.btn.isEnabled():
            self.btn.setText(LM.tr("create_account_btn"))

    def _register(self):
        name  = self.name_in.text().strip()
        email = self.email_in.text().strip()
        pw    = self.pw_in.text()
        role  = self.role.currentText()
        if not all([name, email, pw]):
            self.err.setText(LM.tr("all_fields_required"))
            self.err.show()
            return
        self.btn.setEnabled(False)
        self.btn.setText(LM.tr("creating_account"))
        self._w = RegWorker(name, email, pw, role)
        self._w.success.connect(self._ok)
        self._w.error.connect(self._fail)
        self._w.start()

    def _ok(self):
        self.btn.setEnabled(True)
        self.btn.setText(LM.tr("create_account_btn"))
        QMessageBox.information(self, "AgroSense", LM.tr("reg_success_msg"))
        self.close()

    def _fail(self, msg):
        self.btn.setEnabled(True)
        self.btn.setText(LM.tr("create_account_btn"))
        self.err.setText(f"{LM.tr('error_title')}: {msg}")
        self.err.show()
