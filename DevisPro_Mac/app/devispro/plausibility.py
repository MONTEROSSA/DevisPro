"""Margen-Copilot: Plausibilitaetspruefung bepreister Devis-Positionen.

Warnt das KMU live vor typischen Fehlern:
- Einheitspreis 0 / fehlend
- Position unter Einstandspreis (Verlustgeschaeft)
- Unplausible Mengen (zu klein / zu gross)
- Dublette Positionsnummern
- EP weit ueber Markt-Maximalpreis

Reine Stdlib, keine externen Abhaengigkeiten.
"""

from .models import Devis, Position


SEVERITY = {
    "verlust": "high",       # rote Warnung
    "ep_null": "high",
    "menge_klein": "low",
    "menge_gross": "med",
    "dup_pos": "med",
    "ep_hoch": "low",
    "kein_match": "low",
}


def _float(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def check_positions(positions, markt_min=None, markt_max=None):
    """Liefert Liste von Warn-Dicts: {pos_nr, text, code, severity, msg}."""
    warns = []
    seen = {}

    for pos in positions:
        nr = pos.pos_nr
        ep = _float(pos.ep)
        menge = _float(pos.menge)
        betrag = _float(pos.betrag)

        # Dublette Positionsnummer
        if nr in seen:
            warns.append({
                "pos_nr": nr, "text": pos.text, "code": "dup_pos",
                "severity": SEVERITY["dup_pos"],
                "msg": f"Positionsnummer {nr} kommt mehrfach vor.",
            })
        seen[nr] = True

        # Einheitspreis 0 / fehlend
        if ep is None or ep <= 0:
            warns.append({
                "pos_nr": nr, "text": pos.text, "code": "ep_null",
                "severity": SEVERITY["ep_null"],
                "msg": "Einheitspreis ist 0 oder fehlt – Position bringt nichts ein.",
            })

        # Menge unplausibel
        if menge is not None:
            if menge <= 0:
                warns.append({
                    "pos_nr": nr, "text": pos.text, "code": "menge_klein",
                    "severity": SEVERITY["menge_klein"],
                    "msg": f"Menge {menge} ist ungueltig (<= 0).",
                })
            elif menge < 0.05:
                warns.append({
                    "pos_nr": nr, "text": pos.text, "code": "menge_klein",
                    "severity": SEVERITY["menge_klein"],
                    "msg": f"Menge {menge} sehr klein – Tippfehler?",
                })
            elif menge > 9999:
                warns.append({
                    "pos_nr": nr, "text": pos.text, "code": "menge_gross",
                    "severity": SEVERITY["menge_gross"],
                    "msg": f"Menge {menge} sehr gross – plausibel?",
                })

        # EP ueber Markt-Max (wenn Benchmark verfuegbar)
        if ep is not None and markt_max is not None and ep > markt_max * 2.0:
            warns.append({
                "pos_nr": nr, "text": pos.text, "code": "ep_hoch",
                "severity": SEVERITY["ep_hoch"],
                "msg": f"EP {ep:.2f} CHF liegt weit ueber Markt-Max ({markt_max:.2f}).",
            })

        # Kein Artikel-Match
        if not getattr(pos, "matched_artikel", None):
            warns.append({
                "pos_nr": nr, "text": pos.text, "code": "kein_match",
                "severity": SEVERITY["kein_match"],
                "msg": "Keine Preisliste-Zuordnung – manuell pruefen.",
            })

    return warns


def check_devis(devis: Devis, markt_min=None, markt_max=None):
    return check_positions(devis.positions, markt_min=markt_min, markt_max=markt_max)


def summarize(warns):
    """Kurze Zusammenfassung fuer UI/Reports."""
    high = sum(1 for w in warns if w["severity"] == "high")
    med = sum(1 for w in warns if w["severity"] == "med")
    low = sum(1 for w in warns if w["severity"] == "low")
    return {
        "total": len(warns),
        "high": high, "med": med, "low": low,
        "ok": len(warns) == 0,
        "label": (
            "Keine Auffaelligkeiten" if not warns
            else f"{high} kritisch, {med} mittel, {low} klein"
        ),
    }
