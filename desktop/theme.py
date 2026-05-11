# Brand colours
DARK_BG    = "#0b1f10"
SIDEBAR_BG = "#0d2414"
GREEN      = "#1a6b35"
GREEN_HOVER= "#145a2b"
EMERALD    = "#22c55e"
GOLD       = "#d4a017"
PAPER      = "#f4f6f4"
WHITE      = "#ffffff"
BORDER     = "#e2e8e4"
TEXT       = "#111827"
MUTED      = "#6b7280"
ACCENT     = "#e8f5ee"
RED        = "#dc2626"
BLUE       = "#2563eb"
PURPLE     = "#7c3aed"

APP_STYLE = f"""
    QMainWindow {{ background-color: {PAPER}; }}
    QWidget#content {{ background-color: {PAPER}; }}
    QWidget#page-root {{ background-color: transparent; }}

    QLabel {{
        background: transparent;
        color: #111827;
        font-family: 'Segoe UI', sans-serif;
    }}
    QLabel#page-title {{
        font-size: 22px;
        font-weight: 700;
        color: #111827;
    }}
    QLabel#page-sub {{
        font-size: 13px;
        color: {MUTED};
    }}
    QLabel#section-title {{
        font-size: 13.5px;
        font-weight: 600;
        color: #111827;
    }}
    QLabel#stat-value {{
        font-size: 28px;
        font-weight: 700;
        background: transparent;
    }}
    QLabel#stat-label {{
        font-size: 11px;
        color: {MUTED};
        background: transparent;
    }}
    QLabel#error-label {{
        color: {RED};
        background: #fef2f2;
        border: 1px solid #fecaca;
        border-radius: 8px;
        padding: 8px 12px;
        font-size: 12px;
    }}
    QLabel#success-label {{
        color: #15803d;
        background: #f0fdf4;
        border: 1px solid #bbf7d0;
        border-radius: 8px;
        padding: 8px 12px;
        font-size: 12px;
    }}

    QFrame#card {{
        background-color: {WHITE};
        border: 1px solid {BORDER};
        border-radius: 12px;
    }}

    QLineEdit, QDoubleSpinBox, QDateEdit, QComboBox {{
        border: 1.5px solid {BORDER};
        border-radius: 8px;
        padding: 6px 12px;
        font-size: 13px;
        color: #111827;
        background: #ffffff;
        font-family: 'Segoe UI', sans-serif;
        selection-background-color: {GREEN};
    }}
    QLineEdit:focus, QComboBox:focus, QDateEdit:focus, QDoubleSpinBox:focus {{
        border-color: {GREEN};
        background: {WHITE};
    }}
    QComboBox::drop-down {{ border: none; }}
    QComboBox::down-arrow {{
        image: none;
        width: 12px; height: 12px;
    }}

    QPushButton#primary-btn {{
        background-color: {GREEN};
        color: white;
        border: none;
        border-radius: 9px;
        padding: 8px 18px;
        font-size: 13px;
        font-weight: 600;
        font-family: 'Segoe UI', sans-serif;
    }}
    QPushButton#primary-btn:hover   {{ background-color: {GREEN_HOVER}; }}
    QPushButton#primary-btn:pressed {{ background-color: #0f4520; }}
    QPushButton#primary-btn:disabled {{ background-color: #9ca3af; }}

    QPushButton#danger-btn {{
        background: transparent;
        color: {RED};
        border: 1px solid #fecaca;
        border-radius: 7px;
        padding: 5px 12px;
        font-size: 12px;
        font-family: 'Segoe UI', sans-serif;
    }}
    QPushButton#danger-btn:hover {{ background-color: #fef2f2; }}

    QPushButton#secondary-btn {{
        background-color: {ACCENT};
        color: {GREEN};
        border: 1px solid #b8d8c4;
        border-radius: 7px;
        padding: 5px 14px;
        font-size: 12px;
        font-weight: 500;
        font-family: 'Segoe UI', sans-serif;
    }}
    QPushButton#secondary-btn:hover {{ background-color: #d1f0dd; }}

    QTableWidget {{
        background: {WHITE};
        border: 1px solid {BORDER};
        border-radius: 10px;
        gridline-color: #f3f4f6;
        font-size: 13px;
        font-family: 'Segoe UI', sans-serif;
        alternate-background-color: #f9fafb;
    }}
    QTableWidget::item {{ padding: 8px 12px; color: #111827; }}
    QTableWidget::item:selected {{ background-color: {ACCENT}; color: #111827; }}
    QHeaderView::section {{
        background-color: {DARK_BG};
        color: #f0ede6;
        padding: 10px 12px;
        font-size: 11.5px;
        font-weight: 600;
        border: none;
        font-family: 'Segoe UI', sans-serif;
    }}
    QScrollBar:vertical {{ width: 6px; background: transparent; }}
    QScrollBar::handle:vertical {{ background: #d1d5db; border-radius: 3px; min-height: 20px; }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}
    QScrollArea {{ border: none; background: transparent; }}

    QDialog {{ background-color: {WHITE}; }}
    QMessageBox {{ background-color: {WHITE}; }}
    QCalendarWidget {{ background: {WHITE}; }}
"""

# Force input text visibility
EXTRA_INPUT_FIX = """
    QLineEdit {
        color: #111827 !important;
        background-color: #ffffff;
        font-size: 13px;
    }
    QComboBox {
        color: #111827;
        background-color: #ffffff;
    }
    QDateEdit {
        color: #111827;
        background-color: #ffffff;
    }
    QDoubleSpinBox {
        color: #111827;
        background-color: #ffffff;
    }
"""

INPUT_FIX = """
    QLineEdit {
        color: #111827;
        background-color: #ffffff;
        border: 1.5px solid #d1d5db;
        border-radius: 8px;
        padding: 6px 12px;
        font-size: 13px;
        font-family: 'Segoe UI', sans-serif;
    }
    QLineEdit:focus {
        border-color: #1a6b35;
        background-color: #ffffff;
        color: #111827;
    }
    QComboBox {
        color: #111827;
        background-color: #ffffff;
        border: 1.5px solid #d1d5db;
        border-radius: 8px;
        padding: 6px 12px;
        font-size: 13px;
    }
    QDoubleSpinBox, QDateEdit, QSpinBox {
        color: #111827;
        background-color: #ffffff;
        border: 1.5px solid #d1d5db;
        border-radius: 8px;
        padding: 6px 12px;
        font-size: 13px;
    }
    QTableWidget {
        color: #111827;
        background-color: #ffffff;
    }
    QTableWidget::item {
        color: #111827;
        padding: 8px 12px;
    }
"""

COMBO_FIX = """
    QComboBox QAbstractItemView {
        color: #111827;
        background-color: #ffffff;
        border: 1px solid #d1d5db;
        border-radius: 8px;
        selection-background-color: #e8f5ee;
        selection-color: #111827;
        outline: none;
    }
    QComboBox QAbstractItemView::item {
        color: #111827;
        background-color: #ffffff;
        padding: 8px 12px;
        min-height: 30px;
    }
    QComboBox QAbstractItemView::item:hover {
        background-color: #e8f5ee;
        color: #111827;
    }
"""

GLOBAL_FIX = """
    QLabel { color: #111827; background: transparent; font-family: 'Segoe UI'; }
    QComboBox { color: #111827; background: #ffffff; }
    QLineEdit { color: #111827; background: #ffffff; }
    QDateEdit { color: #111827; background: #ffffff; }
    QDoubleSpinBox { color: #111827; background: #ffffff; }
    QTableWidget { color: #111827; }
    QTableWidget QTableCornerButton::section { background: #0b1f10; }
    QHeaderView::section { color: #f0ede6; background: #0b1f10; }
    QPushButton { font-family: 'Segoe UI'; }
    QScrollArea { background: transparent; border: none; }
    QScrollArea > QWidget > QWidget { background: transparent; }
"""
