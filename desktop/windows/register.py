from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QFrame, QComboBox, QMessageBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
import desktop.api as api

T="#111827"; G="#1a6b35"; B="#e2e8e4"; W="#ffffff"; R="#dc2626"; M="#6b7280"

def inp(ph="", pw=False):
    i = QLineEdit()
    i.setPlaceholderText(ph)
    i.setFixedHeight(42)
    if pw: i.setEchoMode(QLineEdit.EchoMode.Password)
    i.setStyleSheet(f"QLineEdit{{color:{T};background:{W};border:1.5px solid {B};border-radius:9px;padding:0 14px;font-size:13px;font-family:'Segoe UI';}} QLineEdit:focus{{border-color:{G};}}")
    return i

def lbl(text, size=13, color="#374151", bold=False):
    l = QLabel(text)
    l.setStyleSheet(f"color:{color};font-size:{size}px;font-weight:{'700' if bold else '400'};background:transparent;font-family:'Segoe UI';")
    return l


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
        self.setFixedSize(460, 560)
        self.setStyleSheet(f"background:#0b1f10;")
        self._build()

    def _build(self):
        root = QVBoxLayout(self)
        root.setAlignment(Qt.AlignmentFlag.AlignCenter)

        card = QFrame()
        card.setStyleSheet(f"QFrame{{background:{W};border-radius:16px;}}")
        card.setFixedWidth(400)
        cl = QVBoxLayout(card)
        cl.setContentsMargins(40,32,40,32)
        cl.setSpacing(0)

        cl.addWidget(lbl("Create Account", 22, T, True))
        cl.addSpacing(4)
        cl.addWidget(lbl("Start monitoring your crops", 13, M))
        cl.addSpacing(24)

        self.err = QLabel("")
        self.err.setStyleSheet(f"color:{R};background:#fef2f2;border:1px solid #fecaca;border-radius:8px;padding:8px 12px;font-size:12px;font-family:'Segoe UI';")
        self.err.hide()
        cl.addWidget(self.err)
        cl.addSpacing(4)

        self.inputs = {}
        for label, key, ph, pw in [
            ("Full Name",  "name",     "Ali Hassan",          False),
            ("Email",      "email",    "ali@agrosense.pk",    False),
            ("Password",   "password", "min 8 characters",    True),
        ]:
            cl.addWidget(lbl(label, 12, "#374151", True))
            cl.addSpacing(4)
            i = inp(ph, pw)
            cl.addWidget(i)
            cl.addSpacing(12)
            self.inputs[key] = i

        cl.addWidget(lbl("Role", 12, "#374151", True))
        cl.addSpacing(4)
        self.role = QComboBox()
        self.role.addItems(["farmer","analyst","admin"])
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

        self.btn = QPushButton("Create Account")
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

    def _register(self):
        name  = self.inputs["name"].text().strip()
        email = self.inputs["email"].text().strip()
        pw    = self.inputs["password"].text()
        role  = self.role.currentText()
        if not all([name, email, pw]):
            self.err.setText("All fields are required")
            self.err.show(); return
        self.btn.setEnabled(False)
        self.btn.setText("Creating account...")
        self._w = RegWorker(name, email, pw, role)
        self._w.success.connect(self._ok)
        self._w.error.connect(self._fail)
        self._w.start()

    def _ok(self):
        self.btn.setEnabled(True)
        self.btn.setText("Create Account")
        QMessageBox.information(self, "Success",
            "Account created! You can now sign in.")
        self.close()

    def _fail(self, msg):
        self.btn.setEnabled(True)
        self.btn.setText("Create Account")
        self.err.setText(f"Error: {msg}")
        self.err.show()
