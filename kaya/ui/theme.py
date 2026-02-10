# kaya/ui/theme.py
# (Retro QSS + Accent switch — dynamic gradients)
from __future__ import annotations
from PySide6 import QtWidgets

# kaya/ui/theme.py içindeki ACCENTS = {...} bloðunu bununla deðiþtir
ACCENTS = {
    # mevcutlar
    'green':  {'ACC':'#39FF14','ACCM':'#A4FFB2','BD':'#145c2f'},
    'blue':   {'ACC':'#00D1FF','ACCM':'#9CEBFF','BD':'#0b4d63'},
    'red':    {'ACC':'#FF3B3B','ACCM':'#FFB3B3','BD':'#5a1111'},

    # yeni paletler
    'amber':     {'ACC':'#FFC247','ACCM':'#FFE1A3','BD':'#6B4A0F'},   # CRT/amber
    'cyan':      {'ACC':'#44DDF0','ACCM':'#B5F3FA','BD':'#0D3E49'},   # tron-vari cyan
    'magenta':   {'ACC':'#FF66CC','ACCM':'#FFB3E6','BD':'#5A1A42'},
    'purple':    {'ACC':'#B38BFA','ACCM':'#E0D1FF','BD':'#3C2E67'},
    'teal':      {'ACC':'#2AB39A','ACCM':'#AEE8DB','BD':'#154C43'},
    'orange':    {'ACC':'#FF7A29','ACCM':'#FFC4A3','BD':'#6A2A07'},
    'lime':      {'ACC':'#C6FF00','ACCM':'#E9FF9D','BD':'#3D5C00'},
    'ice':       {'ACC':'#9AE0FF','ACCM':'#D7F2FF','BD':'#264C5C'},   # buz mavisi
    'mono':      {'ACC':'#9BE2B8','ACCM':'#E6FFF3','BD':'#1F5B45'},   # düþük doygunluk
    'graphite':  {'ACC':'#C0C0C0','ACCM':'#E6E6E6','BD':'#3A3A3A'},   # gri neon
    'cyberpunk': {'ACC':'#FCEE09','ACCM':'#FFF68A','BD':'#625400'},   # neon sarý
}
_cur = 'green'

def _hex_to_rgb(hexstr: str) -> tuple[int,int,int]:
    h = hexstr.strip().lstrip('#')
    if len(h) == 3:
        h = ''.join(ch*2 for ch in h)
    r = int(h[0:2], 16); g = int(h[2:4], 16); b = int(h[4:6], 16)
    return r, g, b

def qss(ac: str = 'green') -> str:
    a = ACCENTS.get(ac, ACCENTS['green'])
    ACC, ACCM, BD = a['ACC'], a['ACCM'], a['BD']
    r, g, b = _hex_to_rgb(ACC)

    # Accent’e göre CRT parýltýsý ve scanline rengi
    radial_rgba   = f"rgba({r},{g},{b},.06)"
    scanline_rgba = f"rgba({r},{g},{b},.025)"
    listgrad_top  = f"rgba({r},{g},{b},.09)"
    listgrad_bot  = f"rgba({r},{g},{b},.02)"
    listscan_rgba = f"rgba({r},{g},{b},.04)"
    sel_grad_l    = f"rgba({r//4},{g//4},{b//4},.7)"   # koyu ton
    sel_grad_r    = f"rgba({r//3},{g//3},{b//3},.85)"  # biraz daha parlak

    return f"""
*{{font-family:'Cascadia Mono','JetBrains Mono','Consolas','Courier New',monospace;font-size:12pt;letter-spacing:.2px;}}
QMainWindow,QWidget{{
  background:#000; color:#E9FFE9;
  background-image:
    radial-gradient(circle at 50% -20%, {radial_rgba}, rgba(0,0,0,0) 40%),
    repeating-linear-gradient(to bottom, {scanline_rgba} 0, {scanline_rgba} 1px, rgba(0,0,0,0) 1px, rgba(0,0,0,0) 3px);
}}
QFrame,QListWidget,QTreeView,QTextEdit,QPlainTextEdit,QLineEdit,QCalendarWidget,QTextBrowser,QGroupBox,QMenu{{
  background:#000; color:#DFFFE0; border:1px solid {BD}; border-radius:3px;
}}
QPushButton,QToolButton{{
  background:qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #010, stop:1 #000);
  color:{ACCM}; border:1px solid {BD}; padding:6px 10px; border-radius:3px;
}}
QPushButton:hover,QToolButton:hover{{ border-color:{ACC}; color:#F2FFF2; }}
QPushButton:checked,QToolButton:checked{{ background:#031; border-color:{ACC}; }}
.navbtn{{ min-height:52px; max-width:80px; font-weight:800; color:{ACCM}; }}
.navbtn:hover{{ color:#D8FFE0; }}
.navbtn:checked{{ background:#031; color:#fff; border-color:{ACC}; }}
QLabel#accent{{ color:{ACC}; letter-spacing:.6px; font-weight:900; }}
QSlider::groove:horizontal{{ height:3px; background:{BD}; border:0; }}
QSlider::handle:horizontal{{ width:10px; background:{ACC}; border:1px solid {ACCM}; margin:-5px 0; }}
QSlider#pos::groove:horizontal{{ height:2px; background:{BD}; }}
QSlider#pos::handle:horizontal{{ width:8px; background:{ACC}; border:1px solid {ACCM}; margin:-6px 0; }}
QCalendarWidget QToolButton{{ background:#000; color:{ACCM}; border:1px solid {BD}; padding:0 4px; border-radius:3px; min-height:16px; }}
QCalendarWidget QToolButton:hover{{ border-color:{ACC}; }}
QCalendarWidget QAbstractItemView:enabled{{ selection-background-color:#052; selection-color:#fff; font-size:9pt; outline:none; }}
QListWidget#tracklist{{
  outline:none; background:#000; border:1px solid {BD};
  background-image:
    linear-gradient(to bottom, {listgrad_top}, {listgrad_bot}),
    repeating-linear-gradient(to bottom, {listscan_rgba} 0, {listscan_rgba} 1px, rgba(0,0,0,0) 1px, rgba(0,0,0,0) 5px);
}}
QListWidget#tracklist::item{{ padding:4px 8px; border-bottom:1px dashed {BD}; }}
QListWidget#tracklist::item:selected{{
  background:qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 {sel_grad_l}, stop:1 {sel_grad_r});
  color:#EAFFEA; border-bottom:1px solid {ACC};
}}
#toast{{ background:rgba(0,0,0,.88); border:1px solid {ACC}; color:#E7FFE7; padding:6px 10px; border-radius:3px; }}
"""

def apply(win: QtWidgets.QWidget, accent: str = 'green'):
    """Uygulamaya QSS uygula (global) ve top-level pencereleri yenile."""
    global _cur
    _cur = accent if accent in ACCENTS else 'green'
    css = qss(_cur)
    app = QtWidgets.QApplication.instance()
    if app is not None:
        app.setStyleSheet(css)
        # mevcut pencereleri yeniden cilala (anýnda etkisi için)
        for w in app.topLevelWidgets():
            try:
                w.style().unpolish(w)
                w.style().polish(w)
                w.update()
            except Exception:
                pass
    else:
        # fallback
        win.setStyleSheet(css)

def current():
    return ACCENTS.get(_cur, ACCENTS['green'])
