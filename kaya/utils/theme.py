# kaya/utils/theme.py
from __future__ import annotations
from PySide6 import QtWidgets
import os

# QSS şablonu: literal süslüler ÇİFT, placeholder'lar TEK
_QSS = """
QWidget {{ background: {bg}; color: {fg}; }}
QToolButton#navbtn {{
  border: 1px solid {edge}; padding: 4px 10px; background: {panel};
}}
QToolButton#navbtn:checked {{ background: {panel_hi}; border-color: {neon}; color: {neon}; }}
QLabel {{ color:{fg}; }}
QPlainTextEdit, QTextBrowser {{
  background: {panel}; border:1px solid {edge}; selection-background-color:{neon_dim};
}}
QTreeView, QTableWidget {{
  background:{panel}; alternate-background-color:{alt}; border:1px solid {edge};
}}
QTreeView::item:selected, QTableWidget::item:selected {{ background:{sel}; color:{fg}; }}
QSplitter::handle {{ background:{edge}; }}
QFrame#daycell {{ background:{panel}; border:1px solid {edge}; }}
QToolButton#weekhead {{ border:1px solid {edge}; }}
QToolBar {{ background:{panel}; border:1px solid {edge}; }}
QMenu {{ background:{panel}; border:1px solid {edge}; }}
QMenu::item:selected {{ background:{sel}; }}
"""

THEMES = {
    "matrix": {  # mevcut yeşil retro (default)
        "bg": "#06110D", "panel": "#0B1F18", "panel_hi": "#0E2A20",
        "edge": "rgba(0,255,160,0.25)", "neon": "#00FFB0", "neon_dim": "rgba(0,255,160,0.20)",
        "fg": "#B8F8D0", "alt": "rgba(0,255,120,0.10)", "sel":"rgba(0,255,120,0.30)"
    },
    "amber": {
        "bg": "#120C03", "panel": "#1B1306", "panel_hi": "#241909",
        "edge": "rgba(255,190,90,0.25)", "neon": "#FFC266", "neon_dim":"rgba(255,190,90,0.18)",
        "fg": "#FFE7BF", "alt":"rgba(255,180,60,0.10)", "sel":"rgba(255,190,90,0.30)"
    },
    "cyan": {
        "bg": "#051018", "panel": "#0B1E2A", "panel_hi": "#0E2836",
        "edge": "rgba(90,210,255,0.28)", "neon": "#6BD8FF", "neon_dim":"rgba(90,210,255,0.18)",
        "fg": "#CFEFFF", "alt":"rgba(90,210,255,0.10)", "sel":"rgba(90,210,255,0.30)"
    },
    "mag": {
        "bg": "#100515", "panel": "#1E0B2A", "panel_hi": "#260D36",
        "edge": "rgba(220,100,255,0.28)", "neon": "#D07CFF", "neon_dim":"rgba(220,100,255,0.18)",
        "fg": "#F1DBFF", "alt":"rgba(220,100,255,0.10)", "sel":"rgba(220,100,255,0.30)"
    },
    "mono": {
        "bg": "#0A0F0C", "panel": "#0F1713", "panel_hi": "#132019",
        "edge": "rgba(120,220,160,0.25)", "neon": "#9BE2B8", "neon_dim":"rgba(120,220,160,0.18)",
        "fg": "#DDEFE5", "alt":"rgba(120,220,160,0.10)", "sel":"rgba(120,220,160,0.25)"
    },
}

_THEME_STORE = os.path.join(os.path.expanduser("~"), ".kaya_theme.txt")

def available() -> list[str]:
    return list(THEMES.keys())

def apply_theme(app: QtWidgets.QApplication, name: str) -> str:
    theme = THEMES.get(name) or THEMES["matrix"]
    app.setStyleSheet(_QSS.format(**theme))
    return "matrix" if name not in THEMES else name

def save_current(name: str):
    try:
        with open(_THEME_STORE, "w", encoding="utf-8") as f:
            f.write(name.strip())
    except Exception:
        pass

def load_and_apply(app: QtWidgets.QApplication) -> str:
    name = "matrix"
    try:
        if os.path.exists(_THEME_STORE):
            name = open(_THEME_STORE, "r", encoding="utf-8").read().strip() or "matrix"
    except Exception:
        name = "matrix"
    return apply_theme(app, name)
