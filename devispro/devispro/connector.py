"""ERP-Connector: Export bepreister Devis/Rechnungen als Import-CSV.

Baut den haertesten Lock-in gegen die Gratis-Editoren (Olmero/Offerten-Edi):
DevisPro liest nicht nur Devis ein, sondern schreibt das bepreiste Ergebnis
zurueck in die Buchhaltung des KMU.

Unterstuetzte Ziele (Import-Formate der gaengigen CH-ERP):
  - abacus   : Standard-Artikelbuchungs-Import (CSV, semikolon, UTF-8 BOM)
  - proffix   : Offerten/Rechnungs-Import (CSV)
  - csv_generic: neutrales Format zum manuellen Mapping

Reine Stdlib. Das Mapping ist dokumentiert; echte Live-Connectoren brauchen
einen Test-Abacus/Proffix beim Kunden (Felder koennen abweichen -> hier als
sauberes, standardkonformes Import-CSV, das in der Regel 1:1 uebernommen wird).
"""
import csv
import io
import html
from .models import Devis
from . import rechnung as rmod


def _r2(v):
    try:
        return round(float(v) * 100) / 100.0
    except (TypeError, ValueError):
        return 0.0


def _chf(v) -> str:
    return f"{_r2(v):.2f}"


# ---------------------------------------------------------------------------
# Abacus (Artikelbuchung / Offertenimport)
# Dokumentiertes Abacus-Import-CSV (semikolon, mit BOM fuer Excel/Abacus).
# Spalten: Belegtyp;Belegnummer;Datum;Konto;Betrag;MWSt-Code;Text;Menge;Einheit;Preis
# ---------------------------------------------------------------------------
def to_abacus(devis: Devis, profil: dict, beleg_nr: str, datum: str, konto: str = "3200") -> bytes:
    mwst = float(profil.get("mwst_pct", 8.1) or 8.1)
    mwst_code = "V" if mwst >= 8.0 else ("R" if mwst >= 2.5 else "0")  # Abacus: V=ueblich, R=reduziert
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=";", quoting=csv.QUOTE_MINIMAL, lineterminator="\n")
    # Kopfzeile (Abacus erwartet Spaltennamen in Zeile 1)
    w.writerow(["Belegtyp", "Belegnummer", "Datum", "Konto", "Betrag",
                "MwSt-Code", "Text", "Menge", "Einheit", "Preis"])
    for i, p in enumerate(devis.positions, start=1):
        ep = _r2(p.ep if p.ep is not None else 0.0)
        betrag = _r2(p.betrag if p.betrag is not None else ep * (p.menge or 0.0))
        w.writerow([
            "OP",                      # Offertenposition
            beleg_nr,
            datum,
            konto,
            _chf(betrag),
            mwst_code,
            (p.text or "")[:60],
            _chf(p.menge or 0.0),
            p.einheit or "",
            _chf(ep),
        ])
    data = buf.getvalue()
    return ("\ufeff" + data).encode("utf-8")  # UTF-8 BOM fuer Abacus/Excel


# ---------------------------------------------------------------------------
# Proffix (Offerten/Rechnungs-Import, CSV komma, keine BOM)
# ---------------------------------------------------------------------------
def to_proffix(devis: Devis, profil: dict, beleg_nr: str, datum: str) -> bytes:
    mwst = float(profil.get("mwst_pct", 8.1) or 8.1)
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=",", quoting=csv.QUOTE_ALL, lineterminator="\n")
    w.writerow(["Beleg", "Pos", "Text", "Menge", "Einheit", "EP", "Betrag", "MwSt%"])
    for i, p in enumerate(devis.positions, start=1):
        ep = _r2(p.ep if p.ep is not None else 0.0)
        betrag = _r2(p.betrag if p.betrag is not None else ep * (p.menge or 0.0))
        w.writerow([
            beleg_nr, i, (p.text or "")[:80], _chf(p.menge or 0.0),
            p.einheit or "", _chf(ep), _chf(betrag), _chf(mwst),
        ])
    return buf.getvalue().encode("utf-8")


# ---------------------------------------------------------------------------
# Neutrales CSV (fuer beliebiges Mapping)
# ---------------------------------------------------------------------------
def to_generic_csv(devis: Devis, profil: dict, beleg_nr: str, datum: str) -> bytes:
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=";", quoting=csv.QUOTE_MINIMAL, lineterminator="\n")
    w.writerow(["BelegNr", "Datum", "Pos", "Bezeichnung", "Menge", "Einheit",
                "Einheitspreis", "Betrag", "MWSt%"])
    mwst = float(profil.get("mwst_pct", 8.1) or 8.1)
    for i, p in enumerate(devis.positions, start=1):
        ep = _r2(p.ep if p.ep is not None else 0.0)
        betrag = _r2(p.betrag if p.betrag is not None else ep * (p.menge or 0.0))
        w.writerow([beleg_nr, datum, i, p.text or "", _chf(p.menge or 0.0),
                    p.einheit or "", _chf(ep), _chf(betrag), _chf(mwst)])
    return ("\ufeff" + buf.getvalue()).encode("utf-8")


def export(devis: Devis, profil: dict, ziel: str, beleg_nr: str, datum: str, konto: str = "3200") -> bytes:
    if ziel == "abacus":
        return to_abacus(devis, profil, beleg_nr, datum, konto)
    if ziel == "proffix":
        return to_proffix(devis, profil, beleg_nr, datum)
    if ziel == "csv":
        return to_generic_csv(devis, profil, beleg_nr, datum)
    raise ValueError(f"Unbekannter Connector-Ziel: {ziel}")
