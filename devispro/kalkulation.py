"""Kalkulations-Engine fuer DevisPro.

Rechnet einen EP (Einheitspreis) aus:
  - EK-Preis (Beschaffung)  [optional, sonst = 0]
  - + Materialaufschlag %
  - + Gemeinkosten %
  + Gewinn %
  = netto Verkaufspreis

Das ist der Unterschied zu einer reinen "Richtpreisliste": der Fachbetrieb
sieht seinen effektiven Deckungsbeitrag und kann Marge bewusst steuern.
"""
import datetime as dt


def berechne_ep(einkauf_chf, material_pct=12.0, gemeinkosten_pct=10.0, gewinn_pct=8.0):
    """Gibt (netto_ep, aufschlaege) zurueck.

    netto_ep = einkauf * (1 + mat/100) * (1 + gk/100) * (1 + gew/100)
    aufschlaege = dict mit Einzelbetraegen (auf EK-Basis).
    """
    mat = einkauf_chf * material_pct / 100.0
    nach_mat = einkauf_chf + mat
    gk = nach_mat * gemeinkosten_pct / 100.0
    nach_gk = nach_mat + gk
    gew = nach_gk * gewinn_pct / 100.0
    netto = nach_gk + gew
    return netto, {
        "einkauf": einkauf_chf,
        "material": mat,
        "gemeinkosten": gk,
        "gewinn": gew,
        "netto": netto,
    }


def kalkuliere_positionen(rows, profil):
    """rows: Liste von dicts mit 'ep' (aktueller Richtpreis) und 'menge'.
    Nutzt den Richtpreis als Verkaufspreis-Basis und zerlegt ihn rueckwaerts
    in EK + Aufschlaege, damit der Fachbetrieb die Marge sieht.

    Vereinfachung: EP aus Richtpreis = netto Verkaufspreis. Wir rechnen
    EK rueckwaerts aus (netto / Faktoren), um Aufschlaege sichtbar zu machen.
    """
    mat = profil.get("material_aufschlag_pct", 12.0)
    gk = profil.get("gemeinkosten_pct", 10.0)
    gew = profil.get("gewinn_pct", 8.0)
    faktor = (1 + mat / 100.0) * (1 + gk / 100.0) * (1 + gew / 100.0)
    out = []
    for r in rows:
        ep = r.get("ep") or 0.0
        menge = r.get("menge") or 0.0
        einkauf = ep / faktor if faktor > 0 else ep
        _, auf = berechne_ep(einkauf, mat, gk, gew)
        auf["verkauf_ep"] = ep
        auf["menge"] = menge
        auf["betrag"] = ep * menge
        out.append(auf)
    return out


def deckungsbeitrag(kalkuliert):
    """Summe Gewinn ueber alle Positionen = Deckungsbeitrag (bevor Steuer)."""
    return sum(k.get("gewinn", 0.0) * k.get("menge", 0.0) for k in kalkuliert)
