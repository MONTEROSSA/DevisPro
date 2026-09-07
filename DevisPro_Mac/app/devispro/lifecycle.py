"""Lebenszyklus-Ansicht: Devis -> Offerte -> Rechnung -> Teilrechnung -> Mahnung.

Bietet pro Projekt (Devis) eine uebersichtliche Kette aller erzeugten Dokumente
mit Status, Betrag und direkten Links. Die glue zwischen Bepreisung, QR-Rechnung,
Connector-Export und Mahnwesen.
"""
from . import history as hist_mod
from . import models as mdl

STAGES = [
    ("bepreist", "1. Bepreist", "Devis bepreist"),
    ("offerte", "2. Offerte", "Angebot/Offerte erstellt"),
    ("rechnung", "3. Rechnung", "Rechnung gestellt"),
    ("teil", "4. Teilzahlung", "Teilrechnung/Recall"),
    ("mahnung", "5. Mahnung", "Mahnung versendet"),
]


def overview(did: str) -> dict:
    """Liefert die Lebenszyklus-Uebersicht eines Devis als dict."""
    if not hist_mod.exists(did):
        return {"did": did, "exists": False, "stages": []}
    docs = {typ: path for typ, path in hist_mod.list_docs(did)}
    # meta laden (Projektname etc.)
    projekt = did
    mp = hist_mod.path_of(did, "meta.json")
    if mp and os_path_exists(mp):
        try:
            meta = json_load(mp)
            projekt = meta.get("project_name") or meta.get("project") or did
        except Exception:
            pass
    stages = []
    total = None
    betrag = _sum_betraege(did)
    for key, label, desc in STAGES:
        present = key in docs
        stages.append({
            "key": key,
            "label": label,
            "desc": desc,
            "present": present,
            "path": docs.get(key),
            "link": f"/devis_doc_file?id={did}&typ={key}" if present else None,
        })
    return {
        "did": did,
        "exists": True,
        "projekt": projekt,
        "stages": stages,
        "gesamtbetrag": betrag,
        "dokumente": list(docs.keys()),
    }


def _sum_betraege(did: str):
    """Versucht den Gesamtbetrag aus dem bepreisten Devis zu ermitteln."""
    try:
        from . import crb as crb_mod
        p = hist_mod.path_of(did, "bepreist.sia")
        if not p:
            return None
        devis = crb_mod.parse(p)
        total = 0.0
        for pos in devis.positions:
            if pos.betrag:
                total += float(pos.betrag)
        return round(total, 2)
    except Exception:
        return None


# --- kleine lokale Helfer (os/json imports vermeiden Top-Level-Reihenfolge) ---
import os as _os
import json as _json


def os_path_exists(p):
    return _os.path.exists(p)


def json_load(p):
    with open(p, encoding="utf-8") as f:
        return _json.load(f)
