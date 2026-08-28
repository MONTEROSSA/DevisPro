"""Mehrwaehrung fuer grenzueberschreitende Bauprojekte (CH/DE/AT/FR/IT).

DevisPro rechnet das Devis in CHF; KMU mit Auslandgeschaften (z.B.
Tessin -> Italien, Genf -> Frankreich, Grenzgaenger zu DE/AT) brauchen
Angebote in EUR/USD. Reine Stdlib: Kurse via SNB- und EZB-XML mit
pessimistischem Fallback (eingebaute Referenzkurse), damit das Tool auch
offline korrekt bleibt.

Wichtig: DevisPro speist die Kalkulation IMMER in CHF; die Fremdwaehrung
ist nur eine Anzeige/Export-Umrechnung. Das verhindert Margenverluste
durch Waehrungsrisiko.
"""

import urllib.request
import xml.etree.ElementTree as ET

# Referenzkurse (1 CHF -> X), pessimistisch gerundet fuer sichere Offline-Fallback
FALLBACK = {
    "CHF": 1.0,
    "EUR": 1.06,   # 1 CHF ~ 1.06 EUR
    "USD": 1.14,
    "GBP": 0.92,
}

CUR_SYM = {"CHF": "CHF", "EUR": "€", "USD": "$", "GBP": "£"}

# SNB: 1 CHF in Fremdwaehrung (XML enthaelt 'devisenkurs' je Einheit)
_SNB_URL = "https://www.snb.ch/api/secure/asset/classifier/download?id=iesis&lang=de&format=xml"
# EZB Referenzkurse: 1 EUR -> X (wir drehen um)
_EZB_URL = "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml"


def kurs_chf_nach(ziel):
    """Liefert Faktor: 1 CHF = ? ziel. Holt live, sonst Fallback."""
    if ziel == "CHF":
        return 1.0
    try:
        with urllib.request.urlopen(_SNB_URL, timeout=6) as r:
            root = ET.fromstring(r.read())
        # SNB-XML Struktur: observaList/observa mit 'symbol' und 'devisenkurs'
        for obs in root.iter():
            sym = obs.get("symbol") or ""
            if sym.upper() == ziel.upper():
                val = obs.findtext("devisenkurs") or obs.findtext("value")
                if val:
                    return float(val)
    except Exception:
        pass
    # EZB als zweite Quelle (EUR-basiert)
    try:
        with urllib.request.urlopen(_EZB_URL, timeout=6) as r:
            root = ET.fromstring(r.read())
        ns = {"e": "http://www.ecb.int/vocabulary/2002-08-01/eurofxref"}
        for c in root.iter("{http://www.ecb.int/vocabulary/2002-08-01/eurofxref}Cube"):
            if c.get("currency") == ziel:
                eur_in_ziel = float(c.get("rate"))   # 1 EUR = ? ziel
                return eur_in_ziel / FALLBACK["EUR"]   # 1 CHF = (eur/1.06)
    except Exception:
        pass
    return FALLBACK.get(ziel, 1.0)


def umrechnen(betrag_chf, ziel):
    return round(betrag_chf * kurs_chf_nach(ziel), 2)


def format(ziel, betrag):
    sym = CUR_SYM.get(ziel, ziel)
    if ziel == "CHF":
        return f"{betrag:,.2f} {sym}".replace(",", "'")
    return f"{sym} {betrag:,.2f}"


def verfuegbare():
    return list(CUR_SYM.keys())
