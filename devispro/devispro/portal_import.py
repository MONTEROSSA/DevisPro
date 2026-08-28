"""Portal-Import: Ausschreibungen von Simap / Olmero / Devisio.

Diese Portale sind JS-lastig; ein direkter Import ist nicht immer moeglich.
Wir versuchen:
  1) URL direkt laden (urllib) -> HTML parsen nach Positionsmustern
  2) Falls JS-geschützt: klarer Hinweis, Ordner-Import zu nutzen

Reine Stdlib. Gibt ein Devis zurueck (oder None wenn nichts erkannt).
"""

import re
import urllib.request
import ssl
from .models import Devis, Position


def _norm(text):
    return re.sub(r"\s+", " ", (text or "").strip())


def _parse_positionen_aus_html(html_text):
    """Heuristik: findet 'Nr Text Menge Einheit [Betrag]' in HTML-Texten."""
    pos = []
    # entferne tags
    plain = re.sub(r"<[^>]+>", " ", html_text)
    plain = _norm(plain)
    # muster 1: nr text menge einheit betrag
    for m in re.finditer(
            r"(\d{1,3}(?:\.\d{1,2})?)\s+([A-Za-zÄÖÜäöü][\wÄÖÜäöü\-\/\s]{4,60}?)\s+"
            r"(\d+[.,]?\d*)\s*(m2|m3|Stk|h|kg|t|m|l|pauschal)\s*(\d+[.,]?\d*)?",
            plain):
        nr, text, menge, einheit, betrag = m.groups()
        pos.append({
            "pos_nr": nr,
            "text": _norm(text),
            "menge": float(menge.replace(",", ".")),
            "einheit": einheit,
            "ep": (float(betrag.replace(",", ".")) if betrag else None),
        })
    if pos:
        return pos
    # muster 2 (lockerer): nr text betrag  -> menge=1
    for m in re.finditer(
            r"(\d{1,3}(?:\.\d{1,2})?)\s+([A-Za-zÄÖÜäöü][\wÄÖÜäöü\-\/\s]{4,60}?)\s+"
            r"(\d+[.,]?\d*)\s*(CHF|Fr\.?)?",
            plain):
        nr, text, betrag, _ = m.groups()
        pos.append({
            "pos_nr": nr,
            "text": _norm(text),
            "menge": 1.0,
            "einheit": "",
            "ep": float(betrag.replace(",", ".")),
        })
    return pos


def import_url(url):
    """Laedt eine Portalseite und extrahiert Positionen."""
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 DevisPro"})
    try:
        with urllib.request.urlopen(req, timeout=25, context=ctx) as resp:
            data = resp.read(2_000_000)
        try:
            html_text = data.decode("utf-8", errors="ignore")
        except Exception:
            html_text = data.decode("latin-1", errors="ignore")
    except Exception:
        return None
    pos = _parse_positionen_aus_html(html_text)
    if not pos:
        return None
    positions = [Position(pos_nr=p["pos_nr"], text=p["text"],
                           menge=p["menge"], einheit=p["einheit"],
                           ep=p["ep"]) for p in pos]
    return Devis(meta={"projekt": "Portal-Import", "quelle": url},
                 addresses=[], chapters=[], positions=positions)
