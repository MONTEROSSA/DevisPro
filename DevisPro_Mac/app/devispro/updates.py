"""Update-Pruefung fuer DevisPro (KMU-lokal, kein Cloud-Zwang).

Beim Oeffnen der Web-Oberflaeche fragt die App asynchron die zentrale
version.json auf devispro.de ab. Ist eine neuere Version verfuegbar,
erscheint sofort ein Banner mit Changelog (Fehlerbehebungen/Erweiterungen).

Design-Prinzipien:
  - reiner Stdlib (urllib) – keine Fremdpakete
  - offline-sicher: bei Netzfehler/Timeout wird still beendet (kein Crash)
  - gecacht: hoechstens alle CHECK_INTERVAL Sekunden eine echte Anfrage
  - respektiert, dass KMU die App lokal ohne Internet betreiben koennen
"""
import json
import os
import threading
import time
import urllib.request

from .version import VERSION, CHANNEL, parse, newer

# Zentrale Versionsdatei (vom Anbieter auf devispro.de hochgeladen)
DEFAULT_URL = os.environ.get(
    "DEVISPRO_UPDATE_URL",
    "https://devispro.de/version.json",
)
CHECK_INTERVAL = 6 * 3600          # max. alle 6h live pruefen
CACHE_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "update_cache.json")
CACHE_FILE = os.environ.get("DEVISPRO_UPDATE_CACHE", CACHE_FILE)
TIMEOUT = 5                        # sekunden

_lock = threading.Lock()
_cache = {"checked": 0, "latest": None}


def _load_cache():
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"checked": 0, "latest": None}


def _save_cache(c):
    try:
        os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(c, f)
    except Exception:
        pass


def fetch_remote(url: str = DEFAULT_URL) -> dict:
    """Laedt version.json; bei Fehler -> {} (offline-sicher)."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "DevisPro-Updater/1.0"})
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            data = resp.read().decode("utf-8")
        return json.loads(data)
    except Exception:
        return {}


def check(force: bool = False, url: str = DEFAULT_URL) -> dict:
    """Liefert Dict: {available, local, latest, channel, notes:{de,fr,it}, url, checked}.

    Ergebnis ist immer gueltig (auch offline). 'available'=True nur wenn
    zentrale Version > lokale Version.
    """
    now = time.time()
    with _lock:
        cached = _load_cache()
        if not force and cached.get("checked") and (now - cached["checked"]) < CHECK_INTERVAL:
            latest = cached.get("latest") or {}
        else:
            latest = fetch_remote(url)
            cached = {"checked": now, "latest": latest}
            _save_cache(cached)
    remote_ver = latest.get("version", "")
    avail = bool(remote_ver) and newer(remote_ver, VERSION)
    return {
        "available": avail,
        "local": VERSION,
        "latest": remote_ver or VERSION,
        "channel": latest.get("channel", CHANNEL),
        "notes": latest.get("notes", {}),
        "url": latest.get("download_url", "https://devispro.de"),
        "checked": bool(remote_ver),
    }


def render_banner(check_result: dict, lang: str = "de") -> str:
    """Liefert HTML-Banner (oder '' wenn kein Update da)."""
    if not check_result.get("available"):
        return ""
    notes = check_result.get("notes", {}) or {}
    lines = notes.get(lang) or notes.get("de") or []
    items = "".join(f"<li>{_esc(n)}</li>" for n in lines)
    latest = check_result.get("latest", "")
    url = check_result.get("url", "https://devispro.de")
    return f"""
<div id="update-banner" class="update-banner" role="status">
  <div class="ub-inner">
    <strong>Update verfügbar: Version {_esc(latest)}</strong>
    <span class="ub-sub">Fehlerbehebungen &amp; Erweiterungen</span>
    {f'<ul class="ub-notes">{items}</ul>' if items else ''}
    <a class="ub-btn" href="{_esc(url)}" target="_blank" rel="noopener">Jetzt aktualisieren</a>
  </div>
  <button class="ub-close" onclick="document.getElementById('update-banner').remove()">×</button>
</div>"""


def _esc(s):
    from html import escape
    return escape(str(s))
