"""Ausschreibungs-Monitor für den Kanton Zürich.

Ehrliche Einordnung der Portale (keine erfundenen Live-Treffer):
  Öffentlich (gesetzlich ab Schwellenwert):
    - simap.ch        offizielle Schweizer Beschaffungsplattform (Kanton + Gemeinden)
    - Amtsblatt Kt. Zürich (Submissionsanzeigen)
  Privat / Gewerbe (Architekten, GU/TU, Bauherren):
    - devisio.ch      Devis-Anfragen Hoch-/Tiefbau
    - olmero.ch       weitverbreitete Ausschreibungsplattform
    - baublatt.ch     Baubewilligungen ZH (frühzeitig Kontakt)
    - infobau.ch      Projektübersichten
"""
import urllib.request
import urllib.parse
import re
import webbrowser

SIMAP_BASE = "https://www.simap.ch"

PORTALS = {
    "simap": "https://www.simap.ch",
    "devisio": "https://www.devisio.ch",
    "olmero": "https://www.olmero.ch",
    "baublatt": "https://www.baublatt.ch",
    "infobau": "https://www.infobau.ch",
}


def build_simap_url(kanton: str = "Zürich", stichwort: str = "") -> str:
    q = urllib.parse.urlencode({"cn": kanton, "kw": stichwort})
    return f"{SIMAP_BASE}/shtml/{q}"


def list_portals() -> None:
    print("Ausschreibungs-Portale Kanton Zürich:")
    print("-" * 50)
    for name, url in PORTALS.items():
        print(f"  {name:<10} {url}")
    print()
    print("Empfehlung:")
    print("  Öffentlich: simap.ch -> Kanton 'Zürich' + CPV/Branche filtern,")
    print("              Unterlagen (Devis) dort direkt herunterladen.")
    print("  Privat:    devisio.ch / olmero.ch Account + E-Mail-Alarm anlegen.")
    print("  Frühzeitig: baublatt.ch Baubewilligungen beobachten.")


def open_portal(name: str = "simap", kanton: str = "Zürich") -> str:
    url = build_simap_url(kanton) if name == "simap" else PORTALS.get(name, SIMAP_BASE)
    try:
        webbrowser.open(url)
    except Exception:  # noqa: BLE001
        pass
    return url


def _best_effort_titles(url: str, timeout: int = 20) -> list:
    """Best-effort Titel-Extraktion. Gibt Hinweis zurück statt erfundener Treffer."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "devispro/0.1"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
        titles = re.findall(r"<a[^>]+class=\"[^\"]*tender[^\"]*\"[^>]*>(.*?)</a>", html, re.I | re.S)
        titles = [re.sub(r"<[^>]+>", "", t).strip() for t in titles]
        return [t for t in titles if t][:20]
    except Exception as e:  # noqa: BLE001
        return [f"ABRUF FEHLGESCHLAGEN: {e} (simap.ch ist JS/Login-basiert – manuell prüfen)"]


if __name__ == "__main__":
    list_portals()
