"""Foto-Import: Devis aus einem Foto/Scan extrahieren.

DevisPro bettet tesseract fest im .app-Bundle ein (kein Cloud, keine
Installation durch das KMU noetig). Suchreihenfolge fuer die Engine:
  1) eingebautes Binary im Bundle  (Contents/Resources/tesseract/)
  2) sonst System-PATH (falls vorhanden)
  3) sonst Fallback: Bild als Ursprung, manuell erfassen.

OCR-Sprachdaten (deu/eng/fra/ita) liegen ebenfalls im Bundle.

Reine Stdlib + optional PIL/pytesseract.
"""

import os
import re
import base64
import shutil
import subprocess
from .models import Devis, Position

# Moegliche Orte fuer das eingebaute tesseract (relativ zum devispro-Modul).
# devispro liegt meist in Contents/Resources/devispro/ -> tesseract in
# Contents/Resources/tesseract/. Wir pruefen mehrere Kaendaten, damit der
# Build nicht vom exakten Layout abhaengt.
_RES = os.path.dirname(os.path.abspath(__file__))


def _kandidaten():
    """Alle denkbaren Pfade zum eingebauten tesseract-Binary."""
    cands = []
    # 1) Contents/Resources/tesseract/tesseract  (Standard)
    cands.append(os.path.normpath(os.path.join(_RES, "..", "tesseract", "tesseract")))
    # 2) Contents/Resources/devispro/tesseract/tesseract (falls verschachtelt)
    cands.append(os.path.normpath(os.path.join(_RES, "tesseract", "tesseract")))
    # 3) Contents/MacOS/tesseract/tesseract
    cands.append(os.path.normpath(os.path.join(_RES, "..", "..", "MacOS", "tesseract", "tesseract")))
    # 4) neben dem .app-Bundle: gleicher Ordner wie devispro/
    cands.append(os.path.normpath(os.path.join(_RES, "tesseract", "tesseract")))
    return cands


def eingebautes_tesseract():
    """Pfad zum eingebauten tesseract-Binary (oder None)."""
    for p in _kandidaten():
        if os.path.isfile(p) and os.access(p, os.X_OK):
            return p
    return None


def ocr_verfuegbar_info():
    """Liefert (verfuegbar, details) — details ist eine Liste der geprueften Pfade."""
    eing = eingebautes_tesseract()
    if eing:
        return True, [f"eingebaut: {eing}"]
    sys = shutil.which("tesseract")
    if sys:
        return True, [f"system: {sys}"]
    return False, _kandidaten()


def ocr_available():
    """True wenn eine tesseract-Engine verfuegbar ist (eingebaut oder System)."""
    return eingebautes_tesseract() is not None or shutil.which("tesseract") is not None


def _engine_path():
    return eingebautes_tesseract() or shutil.which("tesseract")


def _tessdata_dir():
    eng = _engine_path()
    if not eng:
        return None
    # tessdata liegt neben dem binary im Ordner 'tessdata'
    d = os.path.join(os.path.dirname(eng), "tessdata")
    return d if os.path.isdir(d) else None


def _ocr_text(img_path):
    """OCR ueber eingebautes Binary (kein pytesseract noetig)."""
    eng = _engine_path()
    if not eng:
        verf, details = ocr_verfuegbar_info()
        raise RuntimeError(
            "tesseract nicht gefunden. Gepruefte Pfade:\n" + "\n".join(details))
    env = dict(os.environ)
    td = _tessdata_dir()
    if td:
        # tesseract erwartet TESSDATA_PREFIX = Ordner MIT den .traineddata
        env["TESSDATA_PREFIX"] = td
    last_err = ""
    for langs in ("deu+eng+fra+ita", "deu+eng", "deu", "eng"):
        try:
            out = subprocess.run([eng, img_path, "stdout", "-l", langs],
                                 capture_output=True, text=True, timeout=60, env=env)
            if out.returncode == 0:
                return out.stdout
            last_err = (out.stderr or out.stdout)[:200]
        except Exception as e:
            last_err = str(e)
    raise RuntimeError("tesseract Fehler: " + last_err)


# Robustes Parsing: unterstuetzt
#   "12  Innenanstrich Wand  40  m2  35.00"   (Menge + Einheit + EP)
#   "1.1 Innenanstrich Wand 2 Anstriche  m2  42'50"  (Einheit vor Preis, ' als Dezimal)
#   "2  Gerueststellung  Pauschal  820'00"
# Eine ZEILE wird NUR als Position gewertet, wenn sie eine echte
# Beschreibung (Woerter) hat. Reine Zahlen/Zusammenfassungen (Brutto,
# Netto, MWSt, Datum) werden verworfen -> kein Muell in der Tabelle.
_UNITS = ["m2", "m3", "lfm", "kg", "t", "std", "stk", "m", "h", "pauschal"]
_UNIT_RE = re.compile(r"(?<!\w)(" + "|".join(_UNITS) + r")(?!\w)", re.I)
_NUM = r"\d{1,4}(?:['.,]\d{1,3})?"
_SKIP = re.compile(
    r"\b(brutto|netto|mwst|rabatt|skonto|summe|total|abzug|kondition|zwischen|"
    r"versicherung|baustrom|baureinigung|reklame|bemerk|subtotal|eingabe|"
    r"offerteingabe|termin|datum|seite|massen|teil|zuzueglich)\b", re.I)


def _parse_lines(text):
    pos = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        # Datum zeilen (06.06.2022 / 2022-12-31) ausschliessen
        if re.search(r"\d{1,2}[./-]\d{1,2}[./-]\d{2,4}", line):
            continue
        m = re.match(r"^(\d{1,4}(?:\.\d+)*)\b[\s.\-]*\s*(.*)$", line)
        if not m:
            continue
        nr = m.group(1)
        rest = m.group(2).strip()
        # Beschreibung braucht Woerter (mind. 3 Buchstaben)
        words = re.findall(r"[A-Za-zÄÖÜäöüß]{3,}", rest)
        if not words:
            continue
        # Zusammenfassungs-Zeilen ausschliessen
        if _SKIP.search(rest):
            continue
        nums = re.findall(_NUM, rest)
        ep = None
        if nums:
            ep = float(nums[-1].replace("'", ".").replace(",", "."))
        um = _UNIT_RE.search(rest)
        einheit = um.group(1).lower() if um else "m2"
        txt = rest
        if nums:
            p = nums[-1]
            i = txt.rfind(p)
            if i >= 0:
                txt = txt[:i] + txt[i + len(p):]
        if um:
            txt = txt[:um.start()] + txt[um.end():]
        txt = re.sub(r"\s+", " ", txt).strip()
        if len(txt) < 3:
            continue
        pos.append({
            "pos_nr": nr,
            "text": txt,
            "menge": 1.0,
            "einheit": einheit,
            "ep": ep,
        })
    return pos


def _pdf_text(pdf_path):
    """Text aus einem PDF mit Textschicht ziehen (sauberer als OCR)."""
    try:
        from pypdf import PdfReader
    except Exception:
        try:
            from PyPDF2 import PdfReader
        except Exception:
            return None
    try:
        r = PdfReader(pdf_path)
        parts = []
        for pg in r.pages:
            t = pg.extract_text() or ""
            parts.append(t)
        return "\n".join(parts).strip()
    except Exception:
        return None


def extract(img_path, diagnose=False):
    """Liefert (positions, meta) – meta['ocr'] = True/False.

    Bei diagnose=True wird ein OCR-Fehler (z.B. tesseract fehlt) als
    Exception weitergereicht statt still in den Fallback zu gehen.
    """
    # PDF: zuerst echten Text extrahieren (sauberer als OCR)
    if img_path.lower().endswith(".pdf"):
        txt = _pdf_text(img_path)
        if txt:
            rows = _parse_lines(txt)
            if rows:
                positions = [
                    Position(pos_nr=r["pos_nr"], text=r["text"], menge=r["menge"],
                             einheit=r["einheit"], ep=r["ep"])
                    for r in rows
                ]
                return positions, {"ocr": True, "quelle": "pdf", "anzahl": len(positions)}
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
            if diagnose:
                raise
            # sonst: leise in Fallback
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
