"""Devis-Vorlagen: wiederkehrende Standard-Devis schnell wiederverwenden.

Ein KMU speichert ein bepreistes Devis als benannte Vorlage (z.B.
"Badrenovation Standard", "Fassadenanstrich 2026"). Beim naechsten aehnlichen
Projekt wird die Vorlage geladen – Positionen inkl. EP sind sofort gefuellt,
nur Menge/Text anpassen. Reine Stdlib, lokal in data/devis_vorlagen.json.
"""

import os
import json
from datetime import date

DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
PFAD = os.path.join(DATA, "devis_vorlagen.json")


def _laden():
    if os.path.exists(PFAD):
        try:
            with open(PFAD, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _speichern(d):
    os.makedirs(DATA, exist_ok=True)
    tmp = PFAD + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=1)
    os.replace(tmp, PFAD)


def speichern(name, devis, profil=None):
    """Speichert ein Devis als Vorlage.

    name: Vorlagenname. devis: devispro.models.Devis (bereits bepreist).
    Gibt dict zurueck: {name, n_pos, gesamt, datum}.
    """
    name = (name or "").strip()
    if not name:
        raise ValueError("Vorlagenname erforderlich")
    positionen = []
    for p in devis.positions:
        p.fill()  # Betrag aus EP x Menge sicherstellen
        positionen.append({
            "pos_nr": p.pos_nr,
            "text": p.text,
            "menge": p.menge,
            "einheit": p.einheit,
            "ep": p.ep,
            "kategorie": getattr(p, "matched_artikel", None) or "",
        })
    gesamt = round(sum((p.betrag or 0) for p in devis.positions), 2)
    d = _laden()
    d[name] = {
        "name": name,
        "datum": date.today().isoformat(),
        "projekt": devis.meta.get("projekt", ""),
        "kanton": (profil or {}).get("kanton", ""),
        "gewerk": (profil or {}).get("gewerk", ""),
        "n_pos": len(positionen),
        "gesamt": gesamt,
        "positionen": positionen,
    }
    _speichern(d)
    return {"name": name, "n_pos": len(positionen), "gesamt": gesamt, "datum": d[name]["datum"]}


def liste():
    """Alle Vorlagen als Liste (neuste zuerst)."""
    d = _laden()
    out = []
    for v in d.values():
        out.append({
            "name": v.get("name", ""),
            "datum": v.get("datum", ""),
            "projekt": v.get("projekt", ""),
            "n_pos": v.get("n_pos", 0),
            "gesamt": v.get("gesamt", 0),
            "gewerk": v.get("gewerk", ""),
        })
    out.sort(key=lambda x: x.get("datum", ""), reverse=True)
    return out


def laden(name):
    """Vorlage nach Name. Gibt das dict oder None zurueck."""
    d = _laden()
    return d.get(name)


def loeschen(name):
    d = _laden()
    if name in d:
        del d[name]
        _speichern(d)
        return True
    return False


def erstellen(name):
    """Neues Devis aus Vorlage -> speichert es im Verlauf, gibt did zurueck.

    Setzt Positionen inkl. EP vor; Menge/Text koennen danach im Devis editiert werden.
    """
    v = laden(name)
    if not v:
        raise ValueError("Vorlage nicht gefunden")
    from devispro.models import Devis, Position
    from devispro import history as history_mod
    from devispro import stammdaten
    positionen = []
    for pt in v.get("positionen", []):
        pos = Position(
            pos_nr=pt.get("pos_nr", ""),
            text=pt.get("text", ""),
            menge=float(pt.get("menge") or 0),
            einheit=pt.get("einheit", "m2"),
            ep=(float(pt["ep"]) if pt.get("ep") else None),
        )
        pos.matched_artikel = pt.get("kategorie") or None
        pos.requires_review = False
        pos.confidence = 1.0
        pos.fill()
        positionen.append(pos)
    devis = Devis(meta={"projekt": v.get("projekt", name) + " (Vorlage)"},
                  addresses=[], chapters=[], positions=positionen)
    netto = sum((p.betrag or 0) for p in positionen)
    profil = stammdaten.load_profile() or {}
    did = history_mod.save(devis, netto, name=v.get("projekt", name) + " (Vorlage)",
                           method="vorlage", kanton=profil.get("kanton", "ZH"))
    return did
