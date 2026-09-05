"""Ordner-Import: ganzer Projektordner -> ein komplettes Devis.

Bei groesseren Bauten enthaelt eine Ausschreibung viele Unterlagen
(Leistungsverzeichnis .sia, Zusatzblaetter .csv/.xlsx, GAEB .xml, Plaene
als Foto/PDF mit Positionslisten, XRechnung .xml usw.). Das KMU laedt den
ganzen Ordner hoch; DevisPro analysiert jede Datei und fuellt das Devis
vollstaendig aus.

Strategie beim Zusammenfuehren:
  - Alle Positionen aus allen lesbaren Dateien werden gesammelt.
  - Nach (Text, Einheit) dedupliziert; bei Konflikt gewinnt der reichere
    Datensatz (EP/Betrag vorhanden, danach groessere Menge).
  - Nicht-parsbare Dateien (z.B. reine Bilder ohne OCR) werden als
    "manuell" markiert und im Report aufgefuehrt.

Reine Stdlib; wiederverwendet devispro.importers fuer die Formate.
"""

import os
import re
import shutil
import subprocess
from .models import Devis, Position


def _norm_key(text, einheit):
    return (re.sub(r"\s+", " ", (text or "").strip().lower())[:80],
            (einheit or "").strip().lower())


def _richer(a, b):
    """True wenn a reicher als b (beide Position-aehnliche dicts)."""
    def score(p):
        s = 0
        if p.get("ep"): s += 2
        if p.get("betrag"): s += 2
        if p.get("menge"): s += 1
        s += float(p.get("menge") or 0) * 0.01
        return s
    return score(a) >= score(b)


def _ocr_verfuegbar():
    """True wenn das System-Binary tesseract installiert ist."""
    return shutil.which("tesseract") is not None


def _ocr_bild(pfad):
    """Versucht, Positionen aus einem Bild/PDF via tesseract zu extrahieren.
    Gibt eine Liste von Position-dicts zurueck (leer wenn nichts erkennbar)."""
    if not _ocr_verfuegbar():
        return None  # nicht verfuegbar -> Aufrufer markiert 'manuell'
    try:
        out = subprocess.run(
            ["tesseract", pfad, "stdout", "-l", "deu+eng+fra+ita", "--psm", "6"],
            capture_output=True, text=True, timeout=60)
        text = out.stdout
    except Exception:
        return None
    return _ocr_zu_positionen(text)


def _ocr_zu_positionen(text):
    """Heuristik: extrahiert 'Pos  Text  Menge  Einheit  Betrag' aus OCR-Text."""
    pos = []
    for line in text.splitlines():
        # Muster: Zahl am Anfang, dann Text, dann Menge + Einheit + Betrag
        m = re.search(r"(\d+)\s+([A-Za-z].+?)\s+(\d+[.,]?\d*)\s*([a-zA-Z]+)?\s*(\d+[.,]?\d*)?", line)
        if m:
            pos.append({
                "pos_nr": m.group(1),
                "text": m.group(2).strip(),
                "menge": float(m.group(3).replace(",", ".")),
                "einheit": m.group(4) or "",
                "ep": None,
                "betrag": (float(m.group(5).replace(",", ".")) if m.group(5) else None),
            })
    return pos


def analyse_ordner(ordner_pfad):
    """Analysiert alle Dateien in ordner_pfad.

    Gibt (devis, report) zurueck. report enthaelt 'dateien' (Liste mit
    Status pro Datei) und 'statistik'.
    """
    from . import importers
    dateien = []
    merged = {}        # key -> position-dict
    order = []
    nicht_lesbar = []

    for name in sorted(os.listdir(ordner_pfad)):
        pf = os.path.join(ordner_pfad, name)
        if not os.path.isfile(pf):
            continue
        ext = os.path.splitext(name)[1].lower()
        if ext in (".pdf", ".png", ".jpg", ".jpeg", ".webp", ".tif", ".tiff"):
            # Bild/PDF: OCR versuchen, sonst manuell markieren
            ocr = _ocr_bild(pf)
            if ocr:
                for d in ocr:
                    key = _norm_key(d.get("text"), d.get("einheit"))
                    if key in merged:
                        if _richer(d, merged[key]):
                            merged[key] = d
                    else:
                        merged[key] = d
                        order.append(key)
                dateien.append({"datei": name, "status": "ok", "info": f"{len(ocr)} Position(en) via OCR erkannt"})
            else:
                nicht_lesbar.append(name)
                dateien.append({"datei": name, "status": "manuell",
                                "info": "Bild/PDF – OCR nicht verfügbar; bitte Positionen manuell ergänzen"})
            continue
        try:
            devis = importers.import_devis(pf)
            count = len(devis.positions)
            for p in devis.positions:
                d = {
                    "pos_nr": p.pos_nr, "text": p.text,
                    "menge": p.menge, "einheit": p.einheit,
                    "ep": p.ep, "betrag": p.betrag,
                }
                key = _norm_key(p.text, p.einheit)
                if key in merged:
                    if _richer(d, merged[key]):
                        merged[key] = d
                else:
                    merged[key] = d
                    order.append(key)
            dateien.append({"datei": name, "status": "ok", "info": f"{count} Position(en) erkannt"})
        except Exception as e:
            nicht_lesbar.append(name)
            dateien.append({"datei": name, "status": "fehler",
                            "info": f"nicht lesbar: {type(e).__name__}: {e}"})

    positions = []
    for key in order:
        d = merged[key]
        p = Position(
            pos_nr=str(len(positions) + 1),
            text=d.get("text", ""),
            menge=float(d.get("menge") or 0),
            einheit=d.get("einheit") or "",
            ep=(float(d["ep"]) if d.get("ep") is not None else None),
            betrag=(float(d["betrag"]) if d.get("betrag") is not None else None),
        )
        p.fill()
        positions.append(p)

    devis = Devis(meta={"projekt": "Ordner-Import"}, addresses=[], chapters=[],
                  positions=positions)
    report = {
        "dateien": dateien,
        "n_lesbar": sum(1 for d in dateien if d["status"] == "ok"),
        "n_manuell": len(nicht_lesbar),
        "n_positionen": len(positions),
        "nicht_lesbar": nicht_lesbar,
    }
    return devis, report


def passe_an(devis, profil=None):
    """devis gegen gespeicherte Richtpreise bepreisen (Mock-Matcher)."""
    import tempfile as _tf
    from . import stammdaten, pricelist, matcher
    preise = stammdaten.load_prices_csv()
    if not preise:
        return devis
    tmp = os.path.join(_tf.gettempdir(), "hermes_ordner_preise.csv")
    open(tmp, "w", encoding="utf-8").write(preise)
    items = pricelist.load(tmp)
    m = matcher.Matcher(method="mock", threshold=0.6)
    preisliste = {it.artikel_id: it for it in items}
    for p in devis.positions:
        r = m.match(p, list(preisliste.values()))
        p.matched_artikel = r.matched_artikel_id
        p.confidence = r.confidence
        p.requires_review = r.requires_review
        if r.matched_artikel_id and preisliste.get(r.matched_artikel_id):
            p.ep = preisliste[r.matched_artikel_id].ep_chf
            p.fill()
    return devis
