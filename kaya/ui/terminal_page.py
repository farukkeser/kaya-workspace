# kaya/ui/terminal_page.py
from PySide6 import QtWidgets, QtGui, QtCore
from ..terminal import parser as tparser

# __version__ güvenli import (yoksa "dev")
try:
    from .. import __version__ as KAYA_VERSION
except Exception:
    KAYA_VERSION = "dev"

# --- Saat tabanlı selamlama (gömülü, dış bağımlılık yok) ---
from datetime import datetime
try:
    import zoneinfo  # Python 3.9+
    _ZONEINFO_OK = True
except Exception:
    zoneinfo = None
    _ZONEINFO_OK = False

def time_based_greeting(name: str | None = None, tz: str = "Europe/Istanbul") -> str:
    """05-12: Günaydın | 12-17: Tünaydın | 17-22: İyi akşamlar | 22-05: İyi geceler"""
    if _ZONEINFO_OK:
        try:
            now = datetime.now(zoneinfo.ZoneInfo(tz))
        except Exception:
            now = datetime.now()
    else:
        now = datetime.now()

    h = now.hour
    if 5 <= h < 12: g = "Günaydın"
    elif 12 <= h < 17: g = "Tünaydın"
    elif 17 <= h < 22: g = "İyi akşamlar"
    else: g = "İyi geceler"
    return f"{g}{', ' + name if name else ''}."

WELCOME = f"""╔══════════════════════════════════════════════════════╗
║  K.A.Y.A  —  Kişisel Akıllı Yardımcı Asistan {KAYA_VERSION:<8}║
╚══════════════════════════════════════════════════════╝

"""

# --- Typewriter: QPlainTextEdit'e harf harf yazan mini sınıf ---
class Typewriter(QtCore.QObject):
    finished = QtCore.Signal()
    def __init__(self, target: QtWidgets.QPlainTextEdit, ms_per_char: int = 14, chunk: int = 2, parent=None):
        super().__init__(parent)
        self.target = target
        self.ms = max(1, ms_per_char)
        self.chunk = max(1, chunk)
        self._timer = QtCore.QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._queue: list[str] = []
        self._cur: str = ""
        self._i = 0
        self._running = False

    def queue(self, text: str):
        """Sıraya metin ekle. Çalışmıyorsa otomatik başlar."""
        self._queue.append(text)
        if not self._running:
            self._start_next()

    def skip(self):
        """Kalan her şeyi anında yaz ve bitir."""
        if self._running:
            self._timer.stop()
            remaining = self._cur[self._i:]
            if remaining:
                self._insert(remaining)
        while self._queue:
            self._insert(self._queue.pop(0))
        self._running = False
        self.finished.emit()

    def _start_next(self):
        if not self._queue:
            self._running = False
            self.finished.emit()
            return
        self._running = True
        self._cur = self._queue.pop(0)
        self._i = 0
        self._timer.start(self.ms)

    def _tick(self):
        if self._i >= len(self._cur):
            self._timer.stop()
            self._start_next()
            return
        nxt = min(len(self._cur), self._i + self.chunk)
        piece = self._cur[self._i:nxt]
        self._insert(piece)
        self._i = nxt

    def _insert(self, s: str):
        self.target.moveCursor(QtGui.QTextCursor.End)
        self.target.insertPlainText(s)
        self.target.ensureCursorVisible()


class TerminalPage(QtWidgets.QWidget):
    def __init__(self, bus, parent=None):
        super().__init__(parent)
        self.bus = bus
        self._exec_busy = False   # reentrancy kilidi
        self._needs_gap = False   # bir sonraki komuttan önce küçük boşluk

        v = QtWidgets.QVBoxLayout(self)

        # ÇIKTI
        self.out = QtWidgets.QPlainTextEdit(readOnly=True)
        self.out.setPlainText(WELCOME)

        # GİRİŞ
        self.inp = QtWidgets.QLineEdit(
            placeholderText='kaya> Komut...  örn: new note "ideas/todo" body="..." | mkdir "projects/ego"'
        )
        self.inp.setMinimumHeight(44)
        v.addWidget(self.out)
        v.addWidget(self.inp)

        # Kısayollar (tek bağ)
        try:
            self.inp.returnPressed.disconnect()
        except Exception:
            pass
        self.inp.returnPressed.connect(self.execute)
        # Ctrl+Return sadece input’a bağlı olsun
        QtGui.QShortcut(QtGui.QKeySequence("Ctrl+Return"), self.inp, self.execute)

        # Typewriter
        self.tw = Typewriter(self.out, ms_per_char=14, chunk=2, parent=self)
        QtGui.QShortcut(QtGui.QKeySequence("Esc"), self, self.tw.skip)

        # Açılış sekansı
        greet = time_based_greeting(name=None, tz="Europe/Istanbul")
        for s in (
            greet + "\n",
            "Sistem başlatılıyor…\n",
            "[OK] Çekirdek modüller yüklendi\n",
            "[OK] Dosya sistemi çevrimiçi\n",
            "[OK] Arayüz teması etkin\n",
            "Hizmete hazırım patron.\n\n",
        ):
            self.tw.queue(s)

        self.inp.setFocus()

    def log(self, t: str):
        if not t.endswith("\n"):
            t += "\n"
        self.tw.queue(t)

    def execute(self):
        if self._exec_busy:
            return
        self._exec_busy = True
        try:
            line = self.inp.text().strip()
            if not line:
                return

            # Önceki komut/cevaptan sonraki komut biraz aşağıdan başlasın
            if self._needs_gap:
                self.tw.queue("\n")
                self._needs_gap = False

            # Kullanıcı satırını göster
            self.tw.queue(f"> {line}\n")

            # Parse et
            cmd, p = tparser.parse(line)

            # "theme ..." komutları için argümanları garanti et
            if cmd == "theme":
                parts = line.split()
                if len(parts) > 1:
                    p = p or {}
                    p.setdefault("args",   parts[1:])
                    p.setdefault("argv",   parts[1:])
                    p.setdefault("tokens", parts[1:])
                    p.setdefault("rest",   " ".join(parts[1:]))

            # Çalıştır
            res = self.bus.dispatch(cmd, p or {})
            if res:
                self.log(str(res))

        except Exception as e:
            self.log(f"Error: {e}")
        finally:
            self.inp.clear()
            self._needs_gap = True
            self._exec_busy = False
