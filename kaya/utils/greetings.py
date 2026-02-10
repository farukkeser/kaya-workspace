# kaya/utils/greeting.py
from datetime import datetime

try:
    import zoneinfo  # Python 3.9+
    _ZONEINFO_OK = True
except Exception:
    zoneinfo = None
    _ZONEINFO_OK = False

def time_based_greeting(name: str | None = None, tz: str = "Europe/Istanbul") -> str:
    """
    Sistem saatine göre Türkçe selamlama döndürür.
    05-12:  Günaydın   | 12-17: Tünaydın | 17-22: İyi akşamlar | 22-05: İyi geceler
    """
    if _ZONEINFO_OK:
        try:
            now = datetime.now(zoneinfo.ZoneInfo(tz))
        except Exception:
            now = datetime.now()
    else:
        now = datetime.now()

    h = now.hour
    if 5 <= h < 12:
        g = "Günaydın"
    elif 12 <= h < 17:
        g = "Tünaydın"
    elif 17 <= h < 22:
        g = "İyi akşamlar"
    else:
        g = "İyi geceler"
    return f"{g}{', ' + name if name else ''}."
