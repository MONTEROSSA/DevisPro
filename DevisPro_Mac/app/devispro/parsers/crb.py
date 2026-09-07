"""SIA 451 / CRB Positional Standard (Fixed-Width) -- echtes Sorba-Format.

Laut realem Sorba-Export (Beispiel):
  Zeile 01: Kopfdaten  (line_type[2], project_id[9], project_name, date[YYYYMMDD][8], currency[3])
  Zeile 11: Position   (line_type[2], pos_nr[12], text[40], qty[10 Rappen], unit[4])
  Zeile 31: Preiszeile (line_type[2], pos_nr[12], unit_price[10 Rappen], total_price[12 Rappen])
  Zeile 99: Abschluss  (line_type[2], count[6])

Zahlen (Menge, EP, Betrag) liegen in RAPPEN (Wert x 100, rechtsbuendig,
fuehrende Nullen). Beim Parsen /100 -> CHF; beim Export x100 -> Rappen.
pos_nr: 12 Stellen, NPK ohne Punkt linksbuendig, rest mit 0 aufgefuellt.
"""
from ..models import Devis, Position

WIDTHS = {
    "11": [("line_type", 2), ("pos_nr", 12), ("text", 40), ("qty", 10), ("unit", 4)],
    "31": [("line_type", 2), ("pos_nr", 12), ("unit_price", 10), ("total_price", 12)],
    "99": [("line_type", 2), ("count", 6)],
}


def _split(line: str):
    typ = line[:2]
    if typ == "11":
        return typ, {
            "line_type": "11",
            "pos_nr": line[2:14].strip(),
            "text": line[14:54].strip(),
            "qty": line[54:64].strip(),
            "unit": line[64:68].strip(),
        }
    if typ == "31":
        return typ, {
            "line_type": "31",
            "pos_nr": line[2:14].strip(),
            "unit_price": line[14:24].strip(),
            "total_price": line[24:36].strip(),
        }
    if typ == "99":
        return typ, {"line_type": "99", "count": line[2:8].strip()}
    # unbekannter Typ
    return typ, {"line_type": typ}


def _to_rappen(s: str) -> int:
    s = (s or "").strip()
    if s == "":
        return 0
    # robust gegen nicht-numerische Reste (z.B. Einheit klebend)
    digits = "".join(c for c in s if c.isdigit())
    if not digits:
        return 0
    return int(digits)


def _to_chf(s: str) -> float:
    return _to_rappen(s) / 100.0


def _fmt_rappen(value, width: int) -> str:
    # exaktes kaufmaennisches Runden via Decimal (kein Float-Rauschen, kein Banker's)
    from decimal import Decimal, ROUND_HALF_UP
    rappen = int((Decimal(str(value or 0)) * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    return f"{rappen:0{width}d}"


def _fmt_posnr(nr: str, width: int = 12) -> str:
    s = (nr or "").replace(".", "").replace(" ", "")
    return (s + "0" * width)[:width]


def parse(path: str) -> Devis:
    meta = {"version": "SIA451", "currency": "CHF", "date": "",
            "project_id": "", "project_name": ""}
    addresses = []
    chapters = []
    positions = []
    pending = {}
    current_chapter = None

    with open(path, encoding="utf-8") as f:
        for raw in f:
            line = raw.rstrip("\n")
            if not line.strip():
                continue
            typ = line[:2]

            if typ == "01":
                # Robust fuer variables Layout: Datum(8)+Waehrung(3) stehen am Ende,
                # project_id(9) am Anfang. Dazwischen: project_name (optional devis_nr).
                meta["project_id"] = line[2:11].strip()
                rest = line[11:]
                meta["currency"] = (rest[-3:].strip() or "CHF")
                meta["date"] = rest[-11:-3].strip()
                name_field = rest[:-11].strip()
                # devis_nr nur wenn Breite passt (>=58 Zeichen: name[28]+devis_nr[8])
                if len(line) >= 58:
                    meta["project_name"] = line[11:39].strip()
                    meta["devis_nr"] = line[39:47].strip()
                else:
                    # variables Layout: devis_nr nach '|' falls vorhanden, sonst leer
                    if "|" in name_field:
                        meta["project_name"] = name_field.split("|")[0].strip()
                        meta["devis_nr"] = name_field.split("|")[1].strip()
                    else:
                        meta["project_name"] = name_field
                        meta["devis_nr"] = ""
            elif typ == "11":
                _, fld = _split(line)
                pending[fld["pos_nr"]] = {
                    "text": fld["text"],
                    "menge": _to_chf(fld["qty"]),
                    "einheit": fld["unit"],
                }
            elif typ == "31":
                _, fld = _split(line)
                pos_nr = fld["pos_nr"]
                p = pending.pop(pos_nr, {"text": "", "menge": 0.0, "einheit": ""})
                pos = Position(
                    pos_nr=pos_nr,
                    text=p["text"],
                    menge=p["menge"],
                    einheit=p["einheit"],
                    ep=_to_chf(fld["unit_price"]),
                    betrag=_to_chf(fld["total_price"]),
                )
                pos.chapter = current_chapter
                positions.append(pos)
            elif typ == "99":
                pass
    return Devis(meta=meta, addresses=addresses, chapters=chapters, positions=positions)


def export(devis: Devis, path: str, extras=None) -> None:
    """Exportiert Devis als SIA-451. `extras` (optional) = Liste von dicts
    mit den Zusatzpositionen des Fachbetriebs:
        {pos_nr, text, menge, einheit, ep, betrag}
    Diese werden als zusaetzliche 11/31-Zeilen (mit Kennung 'Z') angehaengt.
    """
    extras = extras or []
    lines = []
    m = devis.meta
    lines.append(
        "01"
        + (m.get("project_id", "") or "").ljust(9)[:9]
        + (m.get("project_name", "") or "").ljust(28)[:28]
        + (m.get("devis_nr", "") or "").ljust(8)[:8]
        + (m.get("date", "") or "").ljust(8)[:8]
        + (m.get("currency", "CHF") or "CHF").ljust(3)[:3]
    )
    total = len(devis.positions)
    for p in devis.positions:
        lines.append(
            "11"
            + _fmt_posnr(p.pos_nr).ljust(12)[:12]
            + (p.text or "").ljust(40)[:40]
            + _fmt_rappen(p.menge, 10)
            + (p.einheit or "").ljust(4)[:4]
        )
        ep = p.ep if p.ep is not None else 0.0
        betrag = p.betrag if p.betrag is not None else (ep * p.menge)
        lines.append(
            "31"
            + _fmt_posnr(p.pos_nr).ljust(12)[:12]
            + _fmt_rappen(ep, 10)
            + _fmt_rappen(betrag, 12)
        )
    # Zusatzpositionen (Fachbetrieb)
    for i, ex in enumerate(extras, start=1):
        pos_nr = ex.get("pos_nr") or f"Z{i:03d}"
        text = "[Zusatz] " + (ex.get("text") or "Ergänzung")
        menge = float(ex.get("menge") or 0.0)
        einheit = (ex.get("einheit") or "").ljust(4)[:4]
        ep = float(ex.get("ep") or 0.0)
        betrag = float(ex.get("betrag") or (ep * menge))
        lines.append("11" + _fmt_posnr(pos_nr).ljust(12)[:12]
                     + text.ljust(40)[:40] + _fmt_rappen(menge, 10) + einheit)
        lines.append("31" + _fmt_posnr(pos_nr).ljust(12)[:12]
                     + _fmt_rappen(ep, 10) + _fmt_rappen(betrag, 12))
        total += 1
    lines.append("99" + f"{total:06d}")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
