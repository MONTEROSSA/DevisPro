import csv
from dataclasses import dataclass


@dataclass
class PriceItem:
    artikel_id: str
    bezeichnung: str
    npk: str
    einheit: str
    ep_chf: float
    kategorie: str


def _parse_rows(raw_rows):
    """Roh-Zeilen (Listen) -> Liste[PriceItem]. Teilt Kopfzeilen-Erkennung."""
    items = []
    rows = [r for r in raw_rows if r and any(c.strip() for c in r)]
    if not rows:
        return items
    header = [c.strip().lower() for c in rows[0]]
    has_header = any(k in ("ep_chf", "preis_chf", "preis", "einheitspreis") for k in header) or \
                 ("artikel_id" in header)
    data_rows = rows[1:] if has_header else rows
    for i, vals in enumerate(data_rows):
        if len(vals) < 2:
            continue
        if has_header:
            d = {header[j]: vals[j] for j in range(min(len(header), len(vals)))}
            aid = d.get("artikel_id", "").strip()
            bez = d.get("bezeichnung", "").strip()
            raw_ep = d.get("ep_chf") or d.get("preis_chf") or ""
            npk = d.get("npk", "").strip()
            einheit = d.get("einheit", "").strip()
            kat = d.get("kategorie", "").strip()
        else:
            aid = vals[0].strip()
            bez = vals[1].strip() if len(vals) > 1 else aid
            npk = vals[2].strip() if len(vals) > 2 else ""
            einheit = vals[3].strip() if len(vals) > 3 else ""
            raw_ep = vals[4].strip() if len(vals) > 4 else ""
            kat = vals[5].strip() if len(vals) > 5 else ""
        try:
            ep = float(str(raw_ep).replace(",", "."))
        except (ValueError, TypeError):
            continue
        if not aid:
            aid = f"ART-{i+1:04d}"
        if not bez:
            bez = aid
        items.append(PriceItem(
            artikel_id=aid, bezeichnung=bez, npk=npk,
            einheit=einheit, ep_chf=ep, kategorie=kat,
        ))
    return items


def load(path: str) -> list:
    """Liest eine Richtpreis-CSV (UTF-8, Komma-getrennt).

    Erwartete Spalten (alle ausser artikel_id/bezeichnung/ep_chf optional):
      artikel_id, bezeichnung, npk, einheit, ep_chf, kategorie
    Eine Zeile ohne gueltigen Preis wird uebersprungen.
    """
    with open(path, encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)
        return _parse_rows(list(reader))


def load_xlsx(path: str) -> list:
    """Liest eine Excel-Richtpreisliste (.xlsx). Benoetigt openpyxl.
    Erwartet dieselben Spalten wie die CSV (ohne Formel-Zellen)."""
    try:
        import openpyxl
    except ImportError:
        raise RuntimeError(
            "Excel-Import benoetigt 'openpyxl'. Bitte via 'pip install openpyxl' "
            "nachruesten oder die Liste als CSV speichern.")
    wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
    ws = wb.active
    rows = []
    for r in ws.iter_rows(values_only=True):
        row = ["" if c is None else str(c) for c in r]
        # erste Spalte leer + Rest leer -> ignorieren
        if not any(row):
            continue
        rows.append(row)
    return _parse_rows(rows)
