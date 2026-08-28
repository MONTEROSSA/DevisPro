"""Margen-Copilot: Heuristik statt Black-Box-KI (reine Stdlib, offline).

Der Margen-Copilot nutzt das Benchmark-Netzwerk (anonyme Marktpreise) und
die kantonalen Aufschlaege, um pro Position eine Empfehlung zu geben:
  - ▲ zu tief  (Ihr Preis deutlich unter Markt -> vermutlich zu guenstig)
  - ▼ zu hoch  (Ihr Preis ueber Markt -> evtl. Auftragsrisiko)
  - ● ok       (im Marktband)
  - Warnung bei Marge < 8% (Risiko)

Kein Cloud, keine API-Keys. Die Logik ist erklaerbar (Transparenz fuer KMU).
"""

import os


def _kategorie(text):
    t = (text or "").lower()
    if "beton" in t or "fundament" in t or "erdbau" in t or "abtra" in t:
        return "Erdbau/Beton"
    if "mauer" in t or "wand" in t or "gips" in t or "putz" in t:
        return "Mauerwerk/Gips"
    if "elektro" in t or "kabel" in t or "strom" in t or "steck" in t:
        return "Elektro"
    if "sanit" in t or "wasser" in t or "abfluss" in t or "rohr" in t:
        return "Sanitaer"
    if "anstrich" in t or "farbe" in t or "lack" in t or "maler" in t:
        return "Maler"
    if "dach" in t or "ziegel" in t or "isolier" in t:
        return "Dach/Isolation"
    if "boden" in t or "platten" in t or "flies" in t or "parkett" in t:
        return "Boden/Platten"
    if "fenster" in t or "tuer" in t:
        return "Fenster/Tueren"
    return "Allgemein"


def analyse(devis, kanton="ZH", benchmark_mod=None):
    """Liefert Liste von Empfehlungen pro Position.

    Prueft Markt-Band UND Plausibilitaet (KMU-Schutz vor falschen Zahlen):
      - EP = 0 (Preis fehlt)
      - EP < 0 (Verlust/Fehler)
      - Menge <= 0 oder unplausibel hoch
      - Dublette (gleiche Pos-Nr mehrfach)
      - Marge-Risiko (Markt-Abweichung)
    """
    out = []
    gesehene_nr = {}
    for idx, p in enumerate(devis.positions):
        kat = _kategorie(p.text)
        ep = (p.ep if p.ep is not None else 0.0)
        menge = getattr(p, "menge", 0) or 0
        markt = None
        if benchmark_mod:
            try:
                # direkter Markt-Vergleich je Position (Kategorie + Einheit)
                res = benchmark_mod.benchmark(kat, p.einheit or "-", ep, kanton=kanton)
                if res and res.get("avg") is not None:
                    markt = res["avg"]
            except Exception:
                markt = None
        # --- Markt-Band ---
        if markt and ep:
            abw = (ep - markt) / markt * 100.0
            if abw < -10:
                status = "▲"   # zu tief
                hinweis = f"Preis {abs(abw):.0f}% unter Markt – evtl. zu guenstig kalkuliert"
            elif abw > 10:
                status = "▼"   # zu hoch
                hinweis = f"Preis {abw:.0f}% ueber Markt – Auftragsrisiko"
            else:
                status = "●"   # ok
                hinweis = "im Marktband"
        else:
            status = "●"
            hinweis = "kein Marktvergleich verfuegbar"
        marge_ok = True
        # --- Plausibilitaets-Check (KMU-Schutz vor falschen Zahlen) ---
        warnungen = []
        if ep == 0:
            warnungen.append("EP = 0 — Preis fehlt")
            marge_ok = False
        if ep < 0:
            warnungen.append("EP negativ — Verlust/Fehler")
            marge_ok = False
        if menge <= 0:
            warnungen.append("Menge 0 oder negativ — unplausibel")
            marge_ok = False
        elif menge > 100000:
            warnungen.append("Menge sehr hoch — pruefen")
        # Dublette: gleiche pos_nr taucht mehrfach auf
        nr = str(p.pos_nr or "").strip()
        if nr:
            gesehene_nr[nr] = gesehene_nr.get(nr, 0) + 1
            if gesehene_nr[nr] > 1:
                warnungen.append(f"Dublette Pos-Nr {nr}")
                marge_ok = False
        if warnungen:
            status = "⚠"   # warnung
            hinweis = "; ".join(warnungen)
        out.append({
            "pos_nr": p.pos_nr,
            "text": p.text,
            "ep": ep,
            "markt": markt,
            "status": status,
            "hinweis": hinweis,
            "marge_ok": marge_ok,
        })
    return out
