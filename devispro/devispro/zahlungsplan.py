"""Zahlungsplan-Generator & Risiko-Cockpit für Baurechnungen (Profi-Umfang).

Baut aus wenigen Vorgaben den kompletten, SIA-konformen Zahlungsplan:
    Anzahlung (Akonto) -> Abschlagsrechnungen (waehrend Bau) ->
    Schlussrechnung (abzgl. Anzahlung + Garantierueckbehalt) ->
    Garantiefreigabe nach Frist.

Plus das Risiko-Cockpit: zeigt live, wie viel offen, gebunden (Garantie)
und bereits ausbezahlt ist - die KPI, die Mitbewerber so nicht bieten.
"""

from .rechnung import Rechnung, Teilzahlung, _r2


def erstelle_plan(r: Rechnung, abschlaege: int = 2) -> list:
    """Erzeugt den kompletten Zahlungsplan aus der Rechnung.

    Bei einer SCHLUSSrechnung sind Anzahlung bereits geflossen -> wird
    im Schluss-Schritt abgezogen (nicht doppelt als eigener Schritt gezaehlt).
    Bei einer reinen ANZAHLUNGSrechnung steht nur die Anzahlung im Plan.

    abschlaege: Anzahl Abschlagsrechnungen zwischen Anzahlung und Schluss.
    """
    plan = []
    brutto = r.brutto()
    anz = r.anzahlung_betrag()
    garantie = r.garantie_betrag()

    # 1) Anzahlung nur als eigener Schritt, wenn nicht bereits als schluss-abzug gemeint
    if r.typ == "anzahlung":
        plan.append({
            "nr": len(plan) + 1,
            "typ": "Anzahlung (Akonto)",
            "grund": f"{r.anzahlung_pct:.0f}% bei Auftragserteilung",
            "betrag": anz,
            "faellig": "bei Auftragserteilung",
        })
        return plan

    # 1b) Bei Schlussrechnung: Anzahlung als erster (bereits geflossener) Schritt
    if r.typ == "schluss" and anz > 0:
        plan.append({
            "nr": len(plan) + 1,
            "typ": "Anzahlung (Akonto, bezahlt)",
            "grund": f"{r.anzahlung_pct:.0f}% bei Auftragserteilung (bereits geflossen)",
            "betrag": anz,
            "faellig": "bei Auftragserteilung",
        })

    # 2) Abschlaege + Schluss teilen sich den Rest (brutto - anzahlung - garantie - bereits bezahlt)
    rest = _r2(brutto - anz - garantie - r.bereits_bezahlt) if r.typ == "schluss" else _r2(brutto - garantie - r.bereits_bezahlt)
    if r.typ == "schluss" and rest > 0:
        teil = _r2(rest / (abschlaege + 1))
        for i in range(abschlaege):
            plan.append({
                "nr": len(plan) + 1,
                "typ": f"Abschlag {i+1}",
                "grund": f"Bauabschnitt {i+1} ({100*teil/brutto:.0f}% des Bruttos)",
                "betrag": teil,
                "faellig": f"nach Leistungsnachweis {i+1}",
            })
        # Schluss = letzter Teil (bereits bezahlt ist bereits im rest abgezogen)
        schluss = _r2(teil)
        if schluss > 0:
            plan.append({
                "nr": len(plan) + 1,
                "typ": "Schlussrechnung",
                "grund": (f"letzter Bauabschnitt abzgl. Anzahlung ({_chf(anz)}) "
                          f"und Garantie ({r.garantie_pct:.0f}%)"),
                "betrag": schluss,
                "faellig": r.faelliges_datum(),
            })
    elif r.typ != "schluss" and rest > 0:
        # reine abschlagsrechnung ohne trennung
        pro = _r2(rest / abschlaege)
        for i in range(abschlaege):
            plan.append({
                "nr": len(plan) + 1,
                "typ": f"Abschlag {i+1}",
                "grund": f"Zwischenabrechnung ({100*pro/brutto:.0f}% des Bruttos)",
                "betrag": pro,
                "faellig": f"nach Leistungsnachweis {i+1}",
            })
    # 4) Garantiefreigabe
    if r.garantie_pct > 0:
        plan.append({
            "nr": len(plan) + 1,
            "typ": "Garantiefreigabe",
            "grund": f"nach {r.garantie_monate} Monaten (Rueckbehalt {r.garantie_pct:.0f}%)",
            "betrag": garantie,
            "faellig": f"nach {r.garantie_monate} Monaten",
        })
    return plan


def cockpit(r: Rechnung) -> dict:
    """Risiko-Cockpit: alle relevanten KPIs einer Baurechnung.

    Liefert Ampel-Status (gruen/gelb/rot) fuer sofortige Beurteilung.
    Das ist das Alleinstellungsmerkmal gegenueber Mitbewerbern.
    """
    brutto = r.brutto()
    garantie = r.garantie_betrag()
    anz = r.anzahlung_betrag()
    offen = _r2(brutto - r.bereits_bezahlt - garantie)
    bereits = _r2(r.bereits_bezahlt + anz)
    return {
        "brutto": brutto,
        "garantie_gebunden": garantie,
        "anzahlung": anz,
        "bereits_ausbezahlt": bereits,
        "offen_nach_garantie": offen,
        "waehrung": r.waehrung,
        # Ampeln
        "ampel_garantie": "gruen" if garantie > 0 else "rot",
        "ampel_anzahlung": "gruen" if r.anzahlung_pct > 0 else "gelb",
        "ampel_liquiditaet": "gruen" if offen >= 0 else "rot",
    }


def _chf(value) -> str:
    try:
        v = float(value or 0.0)
    except (TypeError, ValueError):
        v = 0.0
    return f"{v:,.2f}".replace(",", "'")
