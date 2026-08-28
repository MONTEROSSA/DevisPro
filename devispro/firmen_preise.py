"""Firmen-eigene Richtpreise fuer echte Offerten.

Das Unternehmen laedt eine CSV/Excel mit seinen eigenen Preisen hoch:
  Bezeichnung;Einheit;EP_CHF
  Fenster aus Holz-Metall;m2;950
  Montage;h;145
  ...

Beim CRBX-Import wird jede Position gegen diese Preise gematcht (statt der
CH-Durchschnitts-Simulation). Fallback auf Simulation, wenn kein Treffer.

CSV-Spalten (tolerant, deutsch/englisch):
  Bezeichnung / Text / Artikel / Positionsbezeichnung
  Einheit / ME
  EP / EPreis / Einheitspreis / CHF
Optionale Spalte: BKP / Kapitel (fuer genaueres Matching)
"""
import os
import csv
import re

DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
PATH = os.path.join(DATA, "meine_preise.csv")


def _norm(s):
    return (s or "").strip().lower()


def laden():
    """Liest die eigene Preisliste. Gibt Liste von dicts zurueck."""
    if not os.path.exists(PATH):
        return []
    out = []
    with open(PATH, encoding="utf-8-sig", newline="") as f:
        # trenner erraten
        sample = f.read(4096)
        f.seek(0)
        delim = ";" if sample.count(";") >= sample.count(",") else ","
        reader = csv.DictReader(f, delimiter=delim)
        for row in reader:
            # spalten normalisieren
            d = {_norm(k): v for k, v in row.items() if k}
            bez = (d.get("bezeichnung") or d.get("text") or d.get("artikel")
                   or d.get("positionsbezeichnung") or d.get("pos") or "").strip()
            einh = (d.get("einheit") or d.get("me") or "").strip()
            ep_raw = (d.get("ep") or d.get("epreis") or d.get("einheitspreis")
                      or d.get("ep_chf") or d.get("chf") or d.get("preis") or "").strip()
            bkp = (d.get("bkp") or d.get("kapitel") or "").strip()
            if not bez:
                continue
            try:
                ep = float(str(ep_raw).replace("'", "").replace(" ", "").replace(",", "."))
            except ValueError:
                ep = None
            if ep is None:
                continue
            out.append({"bez": bez.lower(), "einheit": einh, "ep": ep, "bkp": bkp})
    return out


def preis_fuer(text, bkp=None):
    """Liefert (einheit, ep) aus der eigenen Liste oder None.

    Match: laengster gemeinsamer Begriff in Bezeichnung, oder BKP-Gleichheit.
    """
    preise = laden()
    if not preise:
        return None
    tl = (text or "").lower()
    # 1) exakte enthaltensein-Teilwort-Match (speziellster zuerst)
    best = None
    for p in preise:
        if p["bez"] in tl or tl in p["bez"]:
            # laengeres bez = spezifischer -> bevorzugen
            if best is None or len(p["bez"]) > len(best["bez"]):
                best = p
    if best:
        return best["einheit"], best["ep"]
    # 2) BKP-match
    if bkp:
        for p in preise:
            if p["bkp"] and bkp.startswith(p["bkp"].replace(".", "")):
                return p["einheit"], p["ep"]
    return None


def exists():
    return os.path.exists(PATH) and len(laden()) > 0


def speichern_aus_upload(fp):
    """Kopiert hochgeladene CSV nach data/meine_preise.csv. Gibt Anzahl Preise zurueck."""
    os.makedirs(DATA, exist_ok=True)
    with open(fp, "rb") as src, open(PATH, "wb") as dst:
        dst.write(src.read())
    return len(laden())
