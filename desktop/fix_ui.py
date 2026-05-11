"""Run this once to fix UI issues in all pages."""
import re, os

fixes = {
    "desktop/pages/dashboard.py": [
        # Remove duplicate header
        ('self.main_layout.addWidget(self._make_header())\n\n        ', ''),
        ('    def _make_header(self):\n        w = QWidget()\n        v = QVBoxLayout(w)\n        v.setContentsMargins(0, 0, 0, 0)\n        v.setSpacing(2)\n        t = QLabel("Dashboard")\n        t.setObjectName("page-title")\n        s = QLabel("Crop intelligence overview")\n        s.setObjectName("page-sub")\n        v.addWidget(t)\n        v.addWidget(s)\n        return w\n\n    ', '    '),
    ],
    "desktop/pages/farms.py": [
        # Remove duplicate header from farms
        ('        hdr = QHBoxLayout()\n        left = QVBoxLayout()\n        t = QLabel("Farms & Fields")\n        t.setObjectName("page-title")\n        s = QLabel("Manage your farms and fields")\n        s.setObjectName("page-sub")\n        left.addWidget(t)\n        left.addWidget(s)\n        hdr.addLayout(left)\n        hdr.addStretch()', '        hdr = QHBoxLayout()\n        hdr.addStretch()'),
    ],
    "desktop/pages/imagery.py": [
        ('        t = QLabel("Satellite Imagery")\n        t.setObjectName("page-title")\n        s = QLabel("Fetch Sentinel-2 data and compute vegetation indices")\n        s.setObjectName("page-sub")\n        layout.addWidget(t)\n        layout.addWidget(s)\n\n        ', '        '),
    ],
    "desktop/pages/analytics.py": [
        # No duplicate headers in analytics
    ],
}

for filepath, replacements in fixes.items():
    if not os.path.exists(filepath):
        print(f"SKIP: {filepath}")
        continue
    with open(filepath, 'r') as f:
        content = f.read()
    for old, new in replacements:
        if old in content:
            content = content.replace(old, new)
            print(f"Fixed: {filepath}")
        else:
            print(f"Pattern not found in {filepath} (may already be fixed)")
    with open(filepath, 'w') as f:
        f.write(content)

print("Done!")
