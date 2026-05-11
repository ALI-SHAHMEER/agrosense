"""
AgroSense Desktop Application
Run: python desktop/main.py
"""
import sys
import os
import faulthandler
faulthandler.enable(file=open('/tmp/agrosense_crash.log', 'w'), all_threads=True)

# Ensure we run from project root
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.getcwd())

from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from desktop.windows.login import LoginWindow
from desktop.windows.main_window import MainWindow
import desktop.api as api


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("AgroSense")
    app.setOrganizationName("SMIU")

    # Set default font
    font = QFont("Segoe UI", 10)
    app.setFont(font)

    # Global scrollbar styling
    app.setStyleSheet("""
        QScrollBar:vertical {
            background: #f0f4f0;
            width: 10px;
            border-radius: 5px;
            margin: 0;
        }
        QScrollBar::handle:vertical {
            background: #a8d4b4;
            border-radius: 5px;
            min-height: 40px;
        }
        QScrollBar::handle:vertical:hover {
            background: #1a6b35;
        }
        QScrollBar::handle:vertical:pressed {
            background: #145a2b;
        }
        QScrollBar::add-line:vertical,
        QScrollBar::sub-line:vertical {
            height: 0px;
            background: none;
        }
        QScrollBar::add-page:vertical,
        QScrollBar::sub-page:vertical {
            background: none;
        }
        QScrollBar:horizontal {
            height: 0px;
        }
    """)

    # Check backend is running
    if not api.health_check():
        msg = QMessageBox()
        msg.setWindowTitle("Backend Not Running")
        msg.setText(
            "Cannot connect to AgroSense API at localhost:8000.\n\n"
            "Please start the backend first:\n"
            "  cd ~/Agrosense/agrosense\n"
            "  conda activate agrosense\n"
            "  uvicorn app.main:app --reload --port 8000"
        )
        msg.setIcon(QMessageBox.Icon.Warning)
        msg.exec()
        sys.exit(1)

    # Show login
    login = LoginWindow()
    _wins = []  # keep strong references so GC never collects windows

    def on_login(user):
        login.close()
        main_win = MainWindow(user)
        _wins.append(main_win)
        main_win.show()

    login.login_success.connect(on_login)
    login.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
