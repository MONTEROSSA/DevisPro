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
import os
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


def import_ausschreibung(pfad: str, kanton: str = "ZH", stichwort: str = ""):
    """Laedt eine heruntergeladene Ausschreibung (Datei) und gibt ein
    bepreites Devis zurueck.

    Ablauf:
      1. Datei ueber die bestehenden Importer (SIA-451, Bauweb/CSV, GAEB,
         OENORM, XRechnung, PDF/Foto-OCR) einlesen.
      2. Positionen automatisch bepreisen (Matcher + Preisliste).
      3. Anonym ins Benchmark-Netzwerk einspeisen (Moat).
      4. Im Verlauf speichern.

    Rueckgabe: (devis, did) – did ist die Verlaufs-ID fuer Download/Offerte.
    Wirft bei nicht lesbarer Datei einen ValueError mit ehrlichem Hinweis.

    Hinweis: Portale (simap/olmero/devisio) erlauben den Download der
    Ausschreibungs-Unterlagen als Datei – diese Datei hier uebergeben.
    Ein automatischer Login-Scrape ist bewusst NICHT implementiert (rechtlich
    und technisch instabil); der Import erfolgt ueber die vom Kunden
    heruntergeladene Datei.
    """
    from devispro import importers as _imp
    from devispro import pricelist as _pl
    from devispro import matcher as _m
    from devispro import history as _hist
    from devispro import benchmark as _bm

    devis = _imp.import_devis(pfad)
    rows = _pl.load(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "meine_preise.csv"))
    if not rows:
        # ohne eigene Preisliste: LEER lassen (KMU soll eigene Preise eingeben)
        rows = []
    # normalisiere zu PriceItem-aehnlichen Objekten fuer den Matcher
    norm = []
    for it in rows:
        if hasattr(it, "artikel_id"):
            norm.append(it)
        elif isinstance(it, dict):
            norm.append(type("P", (), {
                "artikel_id": it.get("artikel_id", ""),
                "bezeichnung": it.get("bezeichnung", ""),
                "npk": it.get("npk", ""),
                "einheit": it.get("einheit", ""),
                "ep_chf": it.get("ep_chf") or it.get("ep") or 0.0,
                "kategorie": it.get("kategorie", ""),
            })())
    preisliste = {p.artikel_id: p for p in norm}
    m = _m.Matcher(method="mock", threshold=0.6)
    for pos in devis.positions:
        r = m.match(pos, list(preisliste.values()))
        pos.matched_artikel = r.matched_artikel_id
        pos.ep = r.einheitspreis_chf
        pos.confidence = r.confidence
        pos.requires_review = r.requires_review
        pos.fill()
    if _bm.stats()["entries"] == 0:
        _bm.seed_market(silent=True)
    _bm.contribute_devis(devis.positions, kanton=kanton)
    netto = sum((p.betrag or 0) for p in devis.positions)
    did = _hist.save(devis, netto, name=stichwort or devis.meta.get("projekt", "Ausschreibung"),
                     method="portal", kanton=kanton, status="offen")
    return devis, did


if __name__ == "__main__":
    list_portals()
