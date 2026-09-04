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


def _to_rappen(value: float, width: int) -> str:
    """Konvertiert einen CHF-Wert zu Rappen-String mit fixer Breite."""
    from decimal import Decimal, ROUND_HALF_UP
    rappen = int((Decimal(str(value or 0)) * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    return f"{rappen:0{width}d}"


def _fmt_posnr(nr: str) -> str:
    """Formatiert pos_nr als 13-stelligen String (ohne Prefix).

    DevisPro-Format: 1-stelliger Prefix ('1' oder '3') + 13 Stellen Code.
    Wir schreiben den Prefix (z.B. '1') separat, also muss diese Funktion
    13 Zeichen liefern, damit Pos-Zeile insgesamt 68 Zeichen hat.
    """
    s = (nr or "").replace(".", "").replace(" ", "")[:13]
    return s.ljust(13, "0")


def _fmt_text(text: str) -> str:
    """Formatiert Text als 40-Zeichen-String (mit trailing spaces aufgefuellt)."""
    return (text or "").ljust(40)[:40]


def _fmt_einheit(unit: str) -> str:
    """Formatiert Einheit als 4-Zeichen-String (mit trailing spaces aufgefuellt)."""
    return (unit or "").ljust(4)[:4]


def _fmt_date(date_str: str) -> str:
    """Formatiert Datum als YYYYMMDD 8-Zeichen-String.

    Akzeptiert: 'YYYY-MM-DD', 'YYYY-MM-DD HH:MM', 'YYYYMMDD' oder leer.
    """
    s = (date_str or "").replace("-", "").replace(" ", "").replace(":", "")[:8]
    return s.ljust(8, "0")[:8]


def export(devis: Devis, path: str) -> None:
    """Schreibt ein Devis im DevisPro-Format (kompatibel zu bestehenden Dateien).

    Layout: Header, dann pro Position zwei Zeilen ('1' = Original, '3' = Preis), Footer.
    Werte werden in Rappen x 100 konvertiert.
    """
    lines = []
    m = devis.meta

    # Header (58 Zeichen)
    header = (
        "01"
        + (m.get("project_id", "") or "").ljust(9)[:9]
        + (m.get("project_name", "") or "").ljust(28)[:28]
        + (m.get("devis_nr", "") or "").ljust(8)[:8]
        + _fmt_date(m.get("date", "") or "")
        + (m.get("currency", "CHF") or "CHF").ljust(3)[:3]
    )
    lines.append(header)

    # Positionen
    for p in devis.positions:
        # Original-Position (68 Zeichen)
        lines.append(
            "1"
            + _fmt_posnr(p.pos_nr or "")
            + _fmt_text(p.text or "")
            + _to_rappen(p.menge or 0.0, 10)
            + _fmt_einheit(p.einheit or "")
        )
        # Preis-Zeile (36 Zeichen)
        ep = p.ep if p.ep is not None else 0.0
        betrag = p.betrag if p.betrag is not None else (ep * (p.menge or 0.0))
        lines.append(
            "3"
            + _fmt_posnr(p.pos_nr or "")
            + _to_rappen(ep, 10)
            + _to_rappen(betrag, 12)
        )

    # Footer
    lines.append("99" + f"{len(devis.positions):06d}")

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


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
PARSER_VERSION = "1.1.0"