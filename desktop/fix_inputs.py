# Run this to patch theme.py with working input styles
import re

fix = """
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

with open("desktop/theme.py", "r") as f:
    content = f.read()

# Append fix at end
with open("desktop/theme.py", "w") as f:
    f.write(content + f'\nINPUT_FIX = """{fix}"""\n')

print("Done")
