"""Foto-Import: Devis aus einem Foto/Scan extrahieren.

Strategie (graceful degradation, reine Stdlib-faehig):
1. Wenn PIL + pytesseract verfuegbar: OCR ueber das Bild, dann
   Zeilen-Parsing in Positionen (Pos-Nr, Text, Menge, Einheit, EP).
2. Sonst: strukturierter Fallback – das Bild wird als Devis-Ursprung
   gespeichert, und der Nutzer bestaetigt/korrigiert die extrahierten
   Positionen in einem gefuehrten Formular.

KEIN Cloud-Zwang, KEINE externen API-Keys noetig. Funktioniert lokal.
Die OCR ist ein Hebel, der den Demo-Wow-Effekt liefert, sobald
pytesseract installiert ist – ohne es ist das Feature ein sauberer
"Foto hochladen + bestaetigen"-Flow.
"""

import os
import re
import base64
from .models import Devis, Position


def ocr_available():
    try:
        import PIL  # noqa: F401
        import pytesseract  # noqa: F401
        return True
    except Exception:
        return False


def _ocr_text(img_path):
    from PIL import Image
    import pytesseract
    img = Image.open(img_path)
    return pytesseract.image_to_string(img, lang="deu+eng+fra+ita")


# Typische Zeilen:  "12  Innenanstrich Wand  40  m2  35.00"
_LINE = re.compile(
    r"^\s*(\d{1,4})[\.\s-]*\s+(.+?)\s+(\d{1,4}[.,]?\d{0,3})\s*"
    r"(stk|stück|st|m2|m3|m|lfm|kg|t|h|std|menge)?\s*"
    r"(\d{0,4}[.,]?\d{1,2})?\s*$",
    re.IGNORECASE,
)


def _parse_lines(text):
    pos = []
    for line in text.splitlines():
        m = _LINE.match(line.strip())
        if not m:
            continue
        nr, txt, menge, einheit, ep = m.groups()
        pos.append({
            "pos_nr": nr,
            "text": txt.strip(),
            "menge": float(menge.replace(",", ".")) if menge else 1.0,
            "einheit": (einheit or "m2").lower().replace("stück", "stk").replace("stueck", "stk"),
            "ep": float(ep.replace(",", ".")) if ep else None,
        })
    return pos


def extract(img_path):
    """Liefert (positions, meta) – meta['ocr'] = True/False."""
    if ocr_available():
        try:
            text = _ocr_text(img_path)
            rows = _parse_lines(text)
            if rows:
                positions = [
                    Position(pos_nr=r["pos_nr"], text=r["text"], menge=r["menge"],
                             einheit=r["einheit"], ep=r["ep"])
                    for r in rows
                ]
                return positions, {"ocr": True, "anzahl": len(positions)}
        except Exception:
            pass
    # Fallback: kein OCR – leere Positionen, Bild als Ursprung markiert
    return [], {"ocr": False, "anzahl": 0, "image": os.path.basename(img_path)}


def to_devis(positions, projekt="Devis aus Foto"):
    return Devis(meta={"projekt": projekt, "quelle": "foto"},
                 addresses=[], chapters=[], positions=positions)


def image_data_uri(img_path, max_kb=800):
    """Base64-Preview fuer die Web-UI (Limit, damit die Seite schlank bleibt)."""
    try:
        with open(img_path, "rb") as f:
            data = f.read()
        if len(data) > max_kb * 1024:
            return None
        ext = os.path.splitext(img_path)[1].lower().lstrip(".") or "png"
        mime = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg",
                "webp": "image/webp"}.get(ext, "image/png")
        b64 = base64.b64encode(data).decode("ascii")
        return f"data:{mime};base64,{b64}"
    except Exception:
        return None
