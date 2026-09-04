"""DevisPro-Format Parser (SIA-451-kompatibel aber mit 1-stelligen Prefixen).

Format-Layout (aus echten DevisPro-Dateien abgeleitet):
  Original-Position: 68 Zeichen
    [0]      '1' (Line-Type)
    [1:14]   pos_nr (13 Stellen, linksbuendig, mit 0 aufgefuellt)
    [14:54]  text (40 Zeichen, mit trailing spaces auf 40 aufgefuellt)
    [54:64]  menge (10 Stellen, Rappen / 100 = CHF z.B. 000006500 = 65.00)
    [64:68]  einheit (1-4 Zeichen + trailing spaces)

  Preis-Zeile: 36 Zeichen
    [0]      '3' (Line-Type)
    [1:14]   pos_nr (13 Stellen)
    [14:24]  unit_price (10 Stellen, Rappen / 100)
    [24:36]  total_price (12 Stellen, Rappen / 100)

  Header: 58 Zeichen
    [0:2]    '01' (Line-Type)
    [2:11]   project_id (9 Zeichen)
    [11:39]  project_name (28 Zeichen)
    [39:47]  devis_nr (8 Zeichen)
    [47:55]  date (8 Zeichen YYYYMMDD)
    [55:58]  currency (3 Zeichen, z.B. CHF)

  Footer: 8 Zeichen
    [0:2]    '99' (Line-Type)
    [2:8]    count (6 Stellen)
"""
import re
from typing import Dict, Any
from ..models import Devis, Position


def _to_chf(s: str) -> float:
    """Konvertiert Rappen-String zu CHF (Wert / 100)."""
    s = (s or "").strip()
    if not s:
        return 0.0
    digits = "".join(c for c in s if c.isdigit())
    if not digits:
        return 0.0
    return int(digits) / 100.0


def parse(path: str) -> Devis:
    """Parst eine DevisPro-formatierte bepreist.sia Datei.

    Fixed-Width Parser mit praezisen Spalten-Offsets (siehe Modul-Docstring).
    """
    meta = {
        "version": "SIA451-DevisPro",
        "currency": "CHF",
        "date": "",
        "project_id": "",
        "project_name": "",
        "devis_nr": "",
    }
    addresses = []
    chapters = []
    positions = []
    pending: Dict[str, Dict[str, Any]] = {}
    current_chapter = None

    with open(path, encoding="utf-8") as f:
        for raw in f:
            line = raw.rstrip("\n")
            if not line:
                continue

            # Header: 58 Zeichen, [0:2]='01', [2:11] project_id, [11:39] name, [39:47] devis_nr,
            # [47:55] date (YYYYMMDD), [55:58] currency
            if len(line) >= 58 and line[:2] == "01":
                meta["project_id"] = line[2:11].strip()
                meta["project_name"] = line[11:39].strip()
                meta["devis_nr"] = line[39:47].strip()
                meta["date"] = line[47:55].strip()
                meta["currency"] = line[55:58].strip() or "CHF"
                continue

            # Footer: [0:2]='99', [2:8] count
            if len(line) >= 8 and line[:2] == "99":
                continue

            # Original-Position: 68 Zeichen, [0]='1', [1:14] code, [14:54] text,
            # [54:64] menge (10 stellig), [64:68] einheit
            if len(line) >= 64 and line[0] == "1":
                pos_nr = line[1:14].strip()
                text = line[14:54].strip()
                menge = _to_chf(line[54:64])
                einheit = line[64:].strip() if len(line) > 64 else ""
                pending[pos_nr] = {
                    "text": text,
                    "menge": menge,
                    "einheit": einheit,
                }
                continue

            # Preis-Zeile: 36 Zeichen, [0]='3', [1:14] code, [14:24] EP, [24:36] total
            if len(line) >= 36 and line[0] == "3":
                pos_nr = line[1:14].strip()
                ep = _to_chf(line[14:24])
                betrag = _to_chf(line[24:36])
                p = pending.pop(pos_nr, {"text": "", "menge": 0.0, "einheit": ""})
                pos = Position(
                    pos_nr=pos_nr,
                    text=p["text"],
                    menge=p["menge"],
                    einheit=p["einheit"],
                    ep=ep,
                    betrag=betrag,
                )
                pos.chapter = current_chapter
                positions.append(pos)
                continue

            # Unbekannte Zeile: ignorieren

    return Devis(meta=meta, addresses=addresses, chapters=chapters, positions=positions)


# Konstante für die Parser-Erkennung
PARSER_ID = "devispro_sia"
PARSER_VERSION = "1.0.0"