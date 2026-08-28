"""Wiederkehrende Rechnungen (Recurring Invoicing) - Abo/Service/Vertrags-Rechnungen.

Ein KMU legt Vertraege an (z.B. "Wartung Mueller", "Mietgarage Berg",
"Service-Abc monatlich") mit Intervall (monatlich/quartalsweise/halbjaehrlich/
jaehrlich) und Betrag. DevisPro erinnert an faellige Rechnungen und erzeugt die
Rechnung (mit Swiss-QR) auf Knopfdruck - vollstaendig lokal, ohne Cloud/Zwang.

Reine Stdlib; Speicherung in data/wiederkehrend.json.
"""

import os
import json
from datetime import date, timedelta

from . import rechnung as rmod
from .rechnung import RechnungsPosition

DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
PFAD = os.path.join(DATA, "wiederkehrend.json")

INTERVALLE = {
    "monatlich": 1,
    "quartalsweise": 3,
    "halbjaehrlich": 6,
    "jaehrlich": 12,
}


def _heute():
    return date.today()


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


def _add_monate(d, monate):
    """d + monate Monate (Tag wird beibehalten, auf Monatsende gekappt)."""
    m = d.month - 1 + monate
    y = d.year + m // 12
    m = m % 12 + 1
    # Tage des Zielmonats
    if m in (1, 3, 5, 7, 8, 10, 12):
        max_t = 31
    elif m in (4, 6, 9, 11):
        max_t = 30
    else:
        max_t = 29 if (y % 4 == 0 and (y % 100 != 0 or y % 400 == 0)) else 28
    t = min(d.day, max_t)
    return date(y, m, t)


def _naechste_faellig(start_iso, intervall):
    if intervall not in INTERVALLE:
        intervall = "monatlich"
    monate = INTERVALLE[intervall]
    try:
        d = date.fromisoformat(start_iso)
    except Exception:
        d = _heute()
    heute = _heute()
    # solange in der Vergangenheit: Intervall addieren
    while d < heute:
        d = _add_monate(d, monate)
    return d.isoformat()


def liste():
    d = _laden()
    out = []
    for v in d.values():
        out.append({
            "name": v.get("name", ""),
            "kunde": v.get("kunde", ""),
            "betrag": v.get("betrag", 0),
            "intervall": v.get("intervall", "monatlich"),
            "start": v.get("start", ""),
            "naechste": v.get("naechste", ""),
            "ende": v.get("ende", ""),
            "mwst_pct": v.get("mwst_pct", 8.1),
            "notiz": v.get("notiz", ""),
            "aktiv": v.get("aktiv", True),
        })
    out.sort(key=lambda x: (x.get("naechste") or "9999"))
    return out


def anlegen(name, kunde, betrag, intervall="monatlich", start=None,
            positionen=None, ende="", mwst_pct=8.1, notiz="", profil=None):
    name = (name or "").strip()
    if not name:
        raise ValueError("Vertragsname erforderlich")
    betrag = float(betrag or 0)
    if betrag <= 0:
        raise ValueError("Betrag muss > 0 sein")
    if intervall not in INTERVALLE:
        raise ValueError("Ungueltiges Intervall")
    if not start:
        start = _heute().isoformat()
    naechste = _naechste_faellig(start, intervall)
    if not positionen:
        positionen = [{"text": f"Leistung gemäss Vertrag «{name}»", "betrag": round(betrag, 2)}]
    d = _laden()
    d[name] = {
        "name": name,
        "kunde": kunde or "",
        "betrag": round(betrag, 2),
        "intervall": intervall,
        "start": start,
        "naechste": naechste,
        "ende": ende or "",
        "mwst_pct": float(mwst_pct or 8.1),
        "notiz": notiz or "",
        "positionen": positionen,
        "aktiv": True,
    }
    _speichern(d)
    return d[name]


def loeschen(name):
    d = _laden()
    if name in d:
        del d[name]
        _speichern(d)
        return True
    return False


def faellige_heute():
    heute = _heute().isoformat()
    out = []
    for v in liste():
        if v.get("aktiv", True) and v.get("naechste", "") <= heute:
            out.append(v)
    return out


def erzeuge_rechnung(name, profil=None):
    """Erzeugt die naechste Rechnung fuer einen Vertrag.

    Liefert dict: {rechnung, html, pdf, faellig, nr}. Setzt naechste_faellig
    auf den naechsten Zyklus (Intervall vorruecken).
    """
    d = _laden()
    v = d.get(name)
    if not v:
        raise ValueError("Vertrag nicht gefunden")
    heute = _heute()
    rnr = f"WR-{name[:6].upper().replace(' ', '')}-{heute.strftime('%y%m')}"
    faellig = (heute + timedelta(days=30)).isoformat()
    betrieb = (profil or {}).get("betrieb", "") or "Ihr Betrieb"
    pos = []
    for i, p in enumerate(v.get("positionen", []), start=1):
        betrag = float(p.get("betrag", 0))
        pos.append(RechnungsPosition(
            nr=str(i),
            text=str(p.get("text", "")),
            menge=1.0,
            einheit="Pauschal",
            ep=round(betrag, 2),
            betrag=round(betrag, 2),
        ))
    r = rmod.Rechnung(
        rechnungs_nr=rnr,
        datum=heute.isoformat(),
        faellig=faellig,
        betrieb=str(betrieb),
        kunde=str(v.get("kunde", "")),
        objekt=str(name),
        positionen=pos,
        mwst_pct=float(v.get("mwst_pct", 8.1)),
        notiz=str(v.get("notiz", "")),
    )
    html = rmod.build_html(r, "de")
    pdf = rmod.build_pdf(r, "de")
    # naechste Faelligkeit vorruecken: eine Zyklusbreite ab der gerade verrechneten
    # Faelligkeit (v["naechste"]) – nicht ab "heute" (sonst wird bei bereits
    # zukuenftigem naechste nichts vorgerueckt).
    try:
        basis = date.fromisoformat(v["naechste"])
    except Exception:
        basis = heute
    naechste_d = _add_monate(basis, INTERVALLE.get(v["intervall"], 1))
    if naechste_d < heute:
        naechste_d = date.fromisoformat(_naechste_faellig(naechste_d.isoformat(), v["intervall"]))
    naechste = naechste_d.isoformat()
    # falls Vertrag befristet und ueberschritten -> inaktiv
    ende = v.get("ende", "")
    aktiv = True
    if ende and naechste > ende:
        aktiv = False
    v["naechste"] = naechste
    v["aktiv"] = aktiv
    d[name] = v
    _speichern(d)
    return {"rechnung": r, "html": html, "pdf": pdf, "faellig": faellig, "nr": rnr, "naechste": naechste}
