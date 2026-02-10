# kaya/services/theme_service.py
from __future__ import annotations
from pathlib import Path
from PySide6 import QtWidgets
from ..ui import theme as ui_theme

_THEMESTORE = Path.home() / ".kaya_theme.txt"

def _read_saved() -> str | None:
    try:
        if _THEMESTORE.exists():
            t = _THEMESTORE.read_text(encoding="utf-8").strip()
            return t or None
    except Exception:
        pass
    return None

def _save(name: str):
    try:
        _THEMESTORE.write_text(name.strip(), encoding="utf-8")
    except Exception:
        pass

def _normalize(params) -> tuple[str|None, str|None]:
    # Her şey olabilir: None, dict, string, list...
    if params is None:
        return None, None
    # Tek satır string geldiyse ("set blue" vb.)
    if isinstance(params, str):
        toks = params.strip().split()
        if not toks: return None, None
        sub = toks[0].lower()
        name = toks[1].lower() if len(toks) > 1 else None
        return sub, name
    # Dizi geldiyse
    if isinstance(params, (list, tuple)):
        toks = [str(x) for x in params]
        if not toks: return None, None
        sub = toks[0].lower()
        name = toks[1].lower() if len(toks) > 1 else None
        return sub, name

    # Dict ise
    p = dict(params)
    # doğrudan alanlar
    sub  = (p.get("sub") or p.get("action") or p.get("verb") or p.get("cmd") or p.get("0") or "")
    name = (p.get("name") or p.get("accent") or p.get("value") or p.get("1") or "")
    # args/argv/tokens/rest
    tokens = None
    for key in ("args", "argv", "tokens"):
        if key in p:
            v = p[key]
            tokens = v if isinstance(v, (list, tuple)) else str(v).split()
            break
    if tokens is None and isinstance(p.get("rest"), str):
        tokens = p["rest"].split()
    if tokens:
        if not sub and len(tokens) > 0: sub = tokens[0]
        if not name and len(tokens) > 1: name = tokens[1]

    sub  = sub.strip().lower()  if isinstance(sub, str)  and sub  else None
    name = name.strip().lower() if isinstance(name, str) and name else None
    return sub, name

class ThemeService:
    """
    Komutlar:
      theme list
      theme set <name>
      theme reset
    Ayrıca şu kısa yollar da desteklenir:
      theme.list | theme.set | theme.reset
    """
    def __init__(self, main_window: QtWidgets.QMainWindow):
        self.win = main_window

    def apply_saved_or_default(self):
        name = _read_saved() or "green"
        ui_theme.apply(self.win, name)
        return name

    def handle(self, params=None):
        sub, name = _normalize(params)

        if sub == "list":
            return "Themes: " + ", ".join(ui_theme.ACCENTS.keys())

        if sub == "set":
            if not name:
                return "Usage: theme set <name>\nThemes: " + ", ".join(ui_theme.ACCENTS.keys())
            if name not in ui_theme.ACCENTS:
                return f"Unknown theme '{name}'. Available: " + ", ".join(ui_theme.ACCENTS.keys())
            ui_theme.apply(self.win, name)
            _save(name)
            return f"Theme set to: {name}"

        if sub == "reset":
            ui_theme.apply(self.win, "green")
            _save("green")
            return "Theme reset to: green"

        return "theme commands: list | set <name> | reset"
