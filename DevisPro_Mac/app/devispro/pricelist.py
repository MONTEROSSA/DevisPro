import csv
import os
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


def from_devis_positions(positions, min_ep=1.0):
    """Lernt eine Richtpreisliste aus den Positionen bepreister Devis.

    positions: Liste von devispro.models.Position (oder dicts mit
    text/einheit/ep/kategorie). Pro eindeutigem Bezeichnungstext wird ein
    PriceItem erzeugt (EP = Einheitspreis aus dem Devis). Das ist das
    Zero-Typing-Onboarding: Kunde laedt seine echten Devis hoch, DevisPro
    baut die Stammdaten automatisch.

    Rueckgabe: Liste[PriceItem] (nur Positionen mit gueltigem EP >= min_ep).
    """
    gelernt = {}
    for p in positions:
        if hasattr(p, "ep"):
            txt = (getattr(p, "text", "") or "").strip()
            eh = (getattr(p, "einheit", "") or "").strip() or "-"
            ep = getattr(p, "ep", None)
            kat = (getattr(p, "kategorie", "") or "").strip()
        else:
            txt = (p.get("text") or p.get("bezeichnung") or "").strip()
            eh = (p.get("einheit") or "").strip() or "-"
            ep = p.get("ep")
            kat = (p.get("kategorie") or "").strip()
        if not txt:
            continue
        try:
            epf = float(ep)
        except (TypeError, ValueError):
            continue
        if epf < min_ep:
            continue
        # mehrfache Treffer desselben Textes: EP mitteln
        if txt in gelernt:
            alt = gelernt[txt]
            alt["sum"] += epf
            alt["n"] += 1
            alt["ep"] = round(alt["sum"] / alt["n"], 2)
        else:
            gelernt[txt] = {"einheit": eh, "ep": round(epf, 2), "kat": kat, "sum": epf, "n": 1}
    items = []
    for i, (txt, d) in enumerate(gelernt.items(), 1):
        items.append(PriceItem(
            artikel_id=f"GEL-{i:04d}",
            bezeichnung=txt,
            npk="",
            einheit=d["einheit"],
            ep_chf=d["ep"],
            kategorie=d["kat"] or "allgemein",
        ))
    return items


def to_csv(items) -> str:
    """Schreibt PriceItems als Richtpreis-CSV-String (Spalten wie load erwartet)."""
    import io
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["artikel_id", "bezeichnung", "npk", "einheit", "ep_chf", "kategorie"])
    for it in items:
        w.writerow([it.artikel_id, it.bezeichnung, it.npk, it.einheit,
                    f"{it.ep_chf:.2f}", it.kategorie])
    return buf.getvalue()


def learn_from_devis(devis, data_dir=None) -> int:
    """Extrahiert Preise aus einem Devis und haengt sie an die gespeicherte
    Richtpreisliste an (data/meine_preise.csv). Rueckgabe: Anzahl neu gelernter Positionen.

    Ist noch keine Liste vorhanden, wird sie komplett erstellt.
    data_dir: optionaler Ueberschreibungsordner; default = Paket-Datenverzeichnis.
    """
    if data_dir is None:
        data_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    path = os.path.join(data_dir, "data", "meine_preise.csv")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    existing = load(path) if os.path.exists(path) else []
    seen = {(it.bezeichnung.strip().lower(), it.einheit.strip().lower()) for it in existing}
    new_items = from_devis_positions(devis.positions if hasattr(devis, "positions") else devis)
    added = 0
    for it in new_items:
        key = (it.bezeichnung.strip().lower(), it.einheit.strip().lower())
        if key not in seen:
            existing.append(it)
            seen.add(key)
            added += 1
    content = to_csv(existing)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return added
