"""Subunternehmer-Management: Marge zwischen KMU-Preis und Sub-Offerte.

Bei groesseren Bauten vergibt das KMU Teilleistungen an Subunternehmer.
DevisPro haelt pro Position die Sub-Offerte fest und rechnet die Marge
(KMU-Verkaufspreis - Sub-Kosten) aus. So sieht das KMU sofort, wo die
Marge sitzt und wo die Sub-Offerte zu teuer ist.

Reine Stdlib.
"""

import json
import os

DATA = None  # wird in webui gesetzt

SUB_FILE = "subunternehmer.json"


def _pfad():
    if DATA:
        return os.path.join(DATA, SUB_FILE)
    return SUB_FILE


def laden():
    p = _pfad()
    if not os.path.exists(p):
        return {}
    try:
        return json.load(open(p, encoding="utf-8"))
    except Exception:
        return {}


def speichern(daten):
    with open(_pfad(), "w", encoding="utf-8") as f:
        json.dump(daten, f, ensure_ascii=False, indent=2)


def setze_offerte(devis_id, pos_nr, sub_firma, sub_betrag):
    """Speichert eine Sub-Offerte fuer eine Position eines Devis."""
    d = laden()
    d.setdefault(devis_id, {})
    d[devis_id][pos_nr] = {
        "firma": sub_firma,
        "betrag": float(sub_betrag),
    }
    speichern(d)
    return d[devis_id][pos_nr]


def marge_berechnen(devis, devis_id):
    """Liefert pro Position (sub_firma, sub_betrag, verkauf, marge, marge_pct)."""
    subs = laden().get(devis_id, {})
    out = []
    for p in devis.positions:
        verkauf = (p.betrag if p.betrag is not None else 0.0)
        sub = subs.get(p.pos_nr, {})
        sub_betrag = sub.get("betrag", 0.0)
        marge = round(verkauf - sub_betrag, 2)
        pct = round(marge / verkauf * 100.0, 1) if verkauf else 0.0
        out.append({
            "pos_nr": p.pos_nr,
            "text": p.text,
            "verkauf": verkauf,
            "sub_firma": sub.get("firma", ""),
            "sub_betrag": sub_betrag,
            "marge": marge,
            "marge_pct": pct,
        })
    return out
