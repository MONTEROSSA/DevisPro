"""Buchhaltungs-Integrationen (Import + Export) fuer viele Systeme.

DevisPro haertet den Lock-in gegen Editoren: es schreibt das bepreiste
Ergebnis zurueck in die Buchhaltung des KMU (Export) UND kann Offerten/
Rechnungen aus dem Buchhaltungs-Export zuruecklesen (Import).

Unterstuetzte Ziele (Import-CSV der gaengigen CH/DE/EU-ERP & Buchhaltung):
  CH:  Abacus, Proffix, BMD, Banana, WinOffice, RamCO, Mobit, Kleinvieh
  DE:  DATEV, SAP (CSV), Lexoffice, SevDesk
  EU:  XRechnung (Exportseite via Rechnung), generisches CSV

Jedes System ist ein Eintrag in SYSTEME mit einer Export-Spezifikation
(Spalten, Trennzeichen, BOM, Quoting) und optionalem Reverse-Import.
Reine Stdlib.
"""

import csv
import io
import os

from .models import Devis, Position
from . import connector as conn_mod


def _r2(v):
    try:
        return round(float(v) * 100) / 100.0
    except (TypeError, ValueError):
        return 0.0


def _chf(v) -> str:
    return f"{_r2(v):.2f}"


def _mwst_code(pct: float) -> str:
    if pct >= 8.0:
        return "V"   # ueblich (Schweiz 8.1%)
    if pct >= 2.5:
        return "R"   # reduziert (2.6%)
    return "0"      # befreit


def _produce(delimiter, quoting, columns, rows, bom):
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=delimiter, quoting=quoting, lineterminator="\n")
    w.writerow(columns)
    for r in rows:
        w.writerow(r)
    out = buf.getvalue()
    return ("\ufeff" + out).encode("utf-8") if bom else out.encode("utf-8")


def _rows(devis, profil, beleg, datum, konto, system):
    mwst = float(profil.get("mwst_pct", 8.1) or 8.1)
    code = _mwst_code(mwst)
    rows = []
    for i, p in enumerate(devis.positions, start=1):
        ep = _r2(p.ep if p.ep is not None else 0.0)
        betrag = _r2(p.betrag if p.betrag is not None else ep * (p.menge or 0.0))
        menge = _r2(p.menge or 0.0)
        text = (p.text or "").strip()
        if system == "abacus":
            rows.append(["OP", beleg, datum, konto, _chf(betrag), code, text[:60], _chf(menge), p.einheit or "", _chf(ep)])
        elif system == "proffix":
            rows.append([beleg, i, text[:80], _chf(menge), p.einheit or "", _chf(ep), _chf(betrag), _chf(mwst)])
        elif system == "bmd":
            rows.append([beleg, i, text[:40], text[:80], _chf(menge), p.einheit or "", _chf(ep), _chf(betrag), _chf(mwst)])
        elif system == "datev":
            rows.append([datum, beleg, konto, "3200", text[:30], _chf(betrag), _chf(menge), p.einheit or ""])
        elif system == "banana":
            rows.append([datum, beleg, konto, text[:40], _chf(betrag)])
        elif system == "sap":
            rows.append([beleg, i, text[:40], _chf(menge), p.einheit or "", _chf(betrag), "CHF"])
        elif system == "lexoffice":
            rows.append([beleg, datum, i, text[:80], _chf(menge), p.einheit or "", _chf(ep), _chf(betrag), _chf(mwst)])
        elif system == "sevdesk":
            rows.append([beleg, datum, i, text[:80], _chf(menge), p.einheit or "", _chf(ep), _chf(betrag), _chf(mwst)])
        elif system == "winoffice":
            rows.append([beleg, i, text[:80], _chf(menge), p.einheit or "", _chf(ep), _chf(betrag)])
        elif system == "ramco":
            rows.append([beleg, i, text[:60], _chf(menge), p.einheit or "", _chf(ep), _chf(betrag)])
        elif system == "mobit":
            rows.append([beleg, i, text[:80], _chf(menge), p.einheit or "", _chf(ep), _chf(betrag)])
        elif system == "kleinvieh":
            rows.append([beleg, text[:80], _chf(menge), p.einheit or "", _chf(ep), _chf(betrag)])
        else:  # generic
            rows.append([beleg, datum, i, text, _chf(menge), p.einheit or "", _chf(ep), _chf(betrag), _chf(mwst)])
    return rows


# (id, Name, Land, Beschreibung, [Spalten], Trennzeichen, quoting, BOM)
_SYSTEM_SPECS = [
    ("abacus", "Abacus", "CH", "Artikelbuchungs-Import (semikolon, BOM)",
     ["Belegtyp", "Belegnummer", "Datum", "Konto", "Betrag", "MwSt-Code", "Text", "Menge", "Einheit", "Preis"],
     ";", csv.QUOTE_MINIMAL, True),
    ("proffix", "Proffix", "CH", "Offerten/Rechnungs-Import (Komma, quotiert)",
     ["Beleg", "Pos", "Text", "Menge", "Einheit", "EP", "Betrag", "MwSt%"],
     ",", csv.QUOTE_ALL, False),
    ("bmd", "BMD", "AT/CH", "BMD Fibu-Import (semikolon, BOM)",
     ["Beleg", "Pos", "ArtNr", "Text", "Menge", "Einheit", "EP", "Betrag", "MwSt%"],
     ";", csv.QUOTE_MINIMAL, True),
    ("datev", "DATEV", "DE", "DATEV-Buchungsstapel (semikolon, BOM)",
     ["Belegdatum", "Belegnummer", "Kontonummer", "Gegenkonto", "Buchungstext", "Umsatz", "Menge", "Einheit"],
     ";", csv.QUOTE_MINIMAL, True),
    ("banana", "Banana Accounting", "CH", "Banana Buchungen (semikolon, BOM)",
     ["Date", "Doc", "Account", "Description", "Amount"],
     ";", csv.QUOTE_MINIMAL, True),
    ("sap", "SAP (CSV)", "DE/EU", "SAP-Mehrseiten-CSV (Komma)",
     ["BELNR", "POS", "MAKTX", "MENGE", "MEINS", "NETWR", "WAERS"],
     ",", csv.QUOTE_MINIMAL, False),
    ("lexoffice", "Lexoffice", "DE", "Lexoffice Rechnungs-CSV (Komma)",
     ["Rechnungsnummer", "Datum", "Pos", "Beschreibung", "Menge", "Einheit", "Einzelpreis", "Gesamtpreis", "MwSt%"],
     ",", csv.QUOTE_MINIMAL, False),
    ("sevdesk", "SevDesk", "DE", "SevDesk Rechnungs-CSV (Komma)",
     ["Rechnungsnummer", "Datum", "Pos", "Beschreibung", "Menge", "Einheit", "Einzelpreis", "Gesamtpreis", "MwSt%"],
     ",", csv.QUOTE_MINIMAL, False),
    ("winoffice", "WinOffice", "CH", "WinOffice Offerten-Import (semikolon)",
     ["Beleg", "Pos", "Text", "Menge", "Einheit", "EP", "Betrag"],
     ";", csv.QUOTE_MINIMAL, True),
    ("ramco", "RamCO", "CH", "RamCO Offerten-Import (semikolon)",
     ["Auftrag", "Pos", "Artikel", "Menge", "Einheit", "EP", "Betrag"],
     ";", csv.QUOTE_MINIMAL, True),
    ("mobit", "Mobit", "CH", "Mobit Offerten-Import (Komma)",
     ["Beleg", "Pos", "Text", "Menge", "Einheit", "EP", "Betrag"],
     ",", csv.QUOTE_MINIMAL, False),
    ("kleinvieh", "Kleinvieh", "CH", "Kleinvieh Offerten-Import (semikolon)",
     ["Beleg", "Text", "Menge", "Einheit", "EP", "Betrag"],
     ";", csv.QUOTE_MINIMAL, True),
    ("csv", "Generisches CSV", "–", "Neutrales Format zum manuellen Mapping (semikolon, BOM)",
     ["BelegNr", "Datum", "Pos", "Bezeichnung", "Menge", "Einheit", "Einheitspreis", "Betrag", "MWSt%"],
     ";", csv.QUOTE_MINIMAL, True),
]


def liste():
    """Liste aller Systeme als dicts."""
    out = []
    for sid, name, land, desc, cols, delim, quoting, bom in _SYSTEM_SPECS:
        out.append({"id": sid, "name": name, "land": land, "beschreibung": desc,
                    "columns": cols, "reverse": sid in ("abacus", "proffix", "csv")})
    return out


def export(system_id, devis, profil, beleg, datum, konto="3200") -> bytes:
    if system_id == "abacus":
        return conn_mod.to_abacus(devis, profil, beleg, datum, konto)
    if system_id == "proffix":
        return conn_mod.to_proffix(devis, profil, beleg, datum)
    if system_id == "csv":
        return conn_mod.to_generic_csv(devis, profil, beleg, datum)
    spec = next((s for s in _SYSTEM_SPECS if s[0] == system_id), None)
    if spec is None:
        raise ValueError(f"Unbekanntes Buchhaltungs-System: {system_id}")
    _, name, land, desc, columns, delim, quoting, bom = spec
    rows = _rows(devis, profil, beleg, datum, konto, system_id)
    return _produce(delim, quoting, columns, rows, bom)


def dateiname(system_id, beleg) -> str:
    return f"{beleg}_{system_id}.csv"


# ---------------------------------------------------------------------------
# Reverse-Import: Offerten/Rechnungen aus dem Buchhaltungs-Export zuruecklesen
# ---------------------------------------------------------------------------
def from_accounting(system_id, path) -> Devis:
    """Liest eine Export-CSV des Buchhaltungssystems zurueck in ein Devis.

    Unterstuetzt die Hauptsysteme (abacus, proffix, csv). Andere werden
    ueber das generische CSV gelesen (Text/Menge/Einheit/EP-Spalten).
    """
    with open(path, encoding="utf-8-sig", errors="ignore") as f:
        text = f.read()
    try:
        dialect = csv.Sniffer().sniff(text[:4096], delimiters=";,|\t")
        delim = dialect.delimiter
    except Exception:
        delim = ";"
    reader = csv.reader(io.StringIO(text), delimiter=delim)
    rows = list(reader)
    if not rows:
        raise ValueError("Leere Datei")
    header = [h.strip().lower() for h in rows[0]]
    # Spalten-Indizes bestimmen (tolerant)
    def idx(*names):
        for n in names:
            for j, h in enumerate(header):
                if n in h:
                    return j
        return None
    i_text = idx("text", "beschreibung", "artikel", "bezeichnung", "maktx")
    i_menge = idx("menge", "meng", "quantity")
    i_einheit = idx("einheit", "meins", "unit")
    i_ep = idx("ep", "einzelpreis", "netwr", "preis", "price")
    i_betrag = idx("betrag", "umsatz", "gesamt", "amount", "netto")
    positions = []
    for r in rows[1:]:
        if len(r) < 2:
            continue
        text_v = r[i_text].strip() if i_text is not None and i_text < len(r) else ""
        if not text_v:
            continue
        menge = r[i_menge].replace("'", "").replace(",", ".") if i_menge is not None and i_menge < len(r) and r[i_menge] else "0"
        einheit = r[i_einheit].strip() if i_einheit is not None and i_einheit < len(r) else ""
        ep = r[i_ep].replace("'", "").replace(",", ".") if i_ep is not None and i_ep < len(r) and r[i_ep] else ""
        betrag = r[i_betrag].replace("'", "").replace(",", ".") if i_betrag is not None and i_betrag < len(r) and r[i_betrag] else ""
        p = Position(
            pos_nr=str(len(positions) + 1),
            text=text_v,
            menge=float(menge or 0),
            einheit=einheit,
            ep=(float(ep) if ep else None),
            betrag=(float(betrag) if betrag else None),
        )
        p.fill()
        positions.append(p)
    return Devis(meta={"projekt": f"Import {system_id}"}, addresses=[], chapters=[], positions=positions)
