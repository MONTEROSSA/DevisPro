"""Gratis Devis-Check: Lead-Magnet ohne Login.

Der KMU laedt ein Devis (Sorba, Bauweb, CSV, GAEB, OENORM, XRechnung) hoch.
devispro matched es anonym gegen eine neutrale Demo-Preisliste und zeigt:
- 3 Positionen, wo das KMU vermutlich Marge verliert (EP < Markt)
- Eine grobe Gesamt-Marge-Schaetzung
- CTA: "3 Monate kostenlos testen" (-> /trial)

Kein Login, keine Datenspeicherung des hochgeladenen Devis. Reine Stdlib.
"""

import os
import html
import json
from . import importers
from .matcher import Matcher
from . import stammdaten
from . import plausibility as plausib_mod
from . import benchmark as bench_mod


def demo_pricelist():
    """Neutrale Demo-Preisliste (Groessenordnung CH-Markt, nicht kundenspezifisch)."""
    return {
        "MAL-001": {"artikel_id": "MAL-001", "bezeichnung": "Innenanstrich Wand", "npk": "MAL", "einheit": "m2", "ep_chf": 35.0, "kategorie": "Maler"},
        "MAL-002": {"artikel_id": "MAL-002", "bezeichnung": "Decke streichen", "npk": "MAL", "einheit": "m2", "ep_chf": 32.0, "kategorie": "Maler"},
        "MAL-003": {"artikel_id": "MAL-003", "bezeichnung": "Spachteln", "npk": "MAL", "einheit": "m2", "ep_chf": 28.0, "kategorie": "Maler"},
        "SAN-001": {"artikel_id": "SAN-001", "bezeichnung": "Wasserentlüfter", "npk": "SAN", "einheit": "stk", "ep_chf": 95.0, "kategorie": "Sanitaer"},
        "SAN-002": {"artikel_id": "SAN-002", "bezeichnung": "Rohr verlegen", "npk": "SAN", "einheit": "m", "ep_chf": 120.0, "kategorie": "Sanitaer"},
        "BAU-001": {"artikel_id": "BAU-001", "bezeichnung": "Putz", "npk": "BAU", "einheit": "m2", "ep_chf": 48.0, "kategorie": "Bau"},
        "BAU-002": {"artikel_id": "BAU-002", "bezeichnung": "Estrich", "npk": "BAU", "einheit": "m2", "ep_chf": 65.0, "kategorie": "Bau"},
        "ELE-001": {"artikel_id": "ELE-001", "bezeichnung": "Steckdose", "npk": "ELE", "einheit": "stk", "ep_chf": 85.0, "kategorie": "Elektro"},
    }


def analyze(path):
    """Liefert Dict mit Check-Ergebnis (positionen, margen_verlust, gesamt)."""
    devis = importers.import_devis(path)
    pl = demo_pricelist()
    m = Matcher(pl)
    for pos in devis.positions:
        r = m.match(pos, list(pl.values()))
        pos.matched_artikel = r.matched_artikel_id
        pos.ep = r.einheitspreis_chf
        pos.confidence = r.confidence
        pos.requires_review = r.requires_review
        pos.fill()

    # Margen-Verlust: Positionen wo EP < Markt-Durchschnitt (Benchmark)
    verlust = []
    for pos in devis.positions:
        bm = bench_mod.benchmark(kategorie=(pos.matched_artikel or pos.text[:20]),
                                 einheit=pos.einheit, ep=(pos.ep or 0))
        if bm["urteil"] == "tief" and bm["delta_pct"] is not None:
            verlust.append({
                "pos_nr": pos.pos_nr, "text": pos.text,
                "ep": pos.ep or 0, "avg": bm["avg"], "delta_pct": bm["delta_pct"],
            })
    verlust.sort(key=lambda x: x["delta_pct"])
    warns = plausib_mod.check_positions(devis.positions)
    netto = sum((p.betrag or 0) for p in devis.positions)
    return {
        "projekt": devis.meta.get("projekt", "Devis"),
        "n_positionen": len(devis.positions),
        "netto": round(netto, 2),
        "verlust": verlust[:3],  # Top 3
        "n_verlust": len(verlust),
        "warns": warns,
    }


def render_form(lang="de"):
    return f"""
 <div class="card">
  <h2>🔍 Gratis Devis-Check – in 30 Sekunden</h2>
  <p class="meta">Laden Sie ein Devis hoch (SIA-451/Sorba, Bauweb, CSV/Excel, GAEB, ÖNORM, XRechnung).
  devispro zeigt Ihnen anonym <b>3 Positionen, wo Sie vermutlich Marge verlieren</b> – ohne Login, ohne Installieren.</p>
  <form method="post" enctype="multipart/form-data" action="/check">
   <input type="file" name="devis" accept=".sia,.crb,.txt,.csv,.xlsx,.xml" required>
   <button type="submit" class="btn">Jetzt kostenlos prüfen</button>
  </form>
  <p class="meta">Ihr Devis wird <b>nicht gespeichert</b> und nicht an Dritte weitergegeben.</p>
 </div>
"""


def log_check_lead(email, firma="", kanton="", gewerk="", projekt=""):
    """Lead aus dem gratis Devis-Check protokollieren (Funnel-Messung).

    Schreibt eine JSON-Zeile nach data/trial_leads.log mit quelle='check'.
    So ist der Funnel Check -> Trial -> Kunde messbar.
    """
    try:
        from datetime import datetime
        pfad = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "trial_leads.log")
        eintrag = {
            "zeit": datetime.now().isoformat(timespec="seconds"),
            "quelle": "check",
            "email": (email or "").strip(),
            "firma": (firma or "").strip(),
            "kanton": (kanton or "").strip(),
            "gewerk": (gewerk or "").strip(),
            "projekt": (projekt or "").strip(),
        }
        with open(pfad, "a", encoding="utf-8") as f:
            f.write(json.dumps(eintrag, ensure_ascii=False) + "\n")
        return True
    except Exception:
        return False


def log_download_lead(email, firma="", kanton="", gewerk="", tarif="devis"):
    """Lead aus dem Software-Download protokollieren (Funnel-Messung).

    Schreibt eine JSON-Zeile nach data/trial_leads.log mit quelle='download'.
    So ist der Funnel Download -> Trial -> Kunde messbar.
    tarif: 'devis' oder 'erp' – welche Test-Variante der Kunde gewaehlt hat.
    """
    try:
        from datetime import datetime
        pfad = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "trial_leads.log")
        if tarif not in ("devis", "erp"):
            tarif = "devis"
        eintrag = {
            "zeit": datetime.now().isoformat(timespec="seconds"),
            "quelle": "download",
            "email": (email or "").strip(),
            "firma": (firma or "").strip(),
            "kanton": (kanton or "").strip(),
            "gewerk": (gewerk or "").strip(),
            "tarif": tarif,
            "projekt": "",
        }
        with open(pfad, "a", encoding="utf-8") as f:
            f.write(json.dumps(eintrag, ensure_ascii=False) + "\n")
        return True
    except Exception:
        return False


def funnel_stats():
    """Funnel-Kennzahlen aus data/trial_leads.log (JSON-Lines).

    Liefert dict: {checks, trials, kunden_bezahlt, top_kantone}
    quelle='check' zaehlt Devis-Checks; quelle='trial' zaehlt angemeldete Tests.
    """
    try:
        pfad = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "trial_leads.log")
        checks = 0
        trials = 0
        kantone = {}
        with open(pfad, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    e = json.loads(line)
                except Exception:
                    continue
                q = e.get("quelle", "")
                if q == "check":
                    checks += 1
                elif q == "trial":
                    trials += 1
                kt = (e.get("kanton") or "").upper()
                if kt:
                    kantone[kt] = kantone.get(kt, 0) + 1
        top = sorted(kantone.items(), key=lambda kv: kv[1], reverse=True)[:5]
        return {"checks": checks, "trials": trials, "kantone": top}
    except FileNotFoundError:
        return {"checks": 0, "trials": 0, "kantone": []}
    except Exception:
        return {"checks": 0, "trials": 0, "kantone": []}


def render_result(res, lang="de"):
    if res is None:
        return render_form(lang)
    lines = ""
    if res["verlust"]:
        for v in res["verlust"]:
            lines += (f"<li><b>Pos {html.escape(str(v['pos_nr']))} – {html.escape(str(v['text']))}</b><br>"
                      f"Ihr EP: <b>{v['ep']:.2f} CHF</b> · Markt-Durchschnitt: {v['avg']:.2f} CHF "
                      f"<span class='bm low'>▼ {v['delta_pct']}%</span> "
                      f"→ potentielle Marge unter Markt</li>")
    else:
        lines = "<li>✓ In diesem Devis fallen keine offensichtlichen Margen-Verluste auf.</li>"
    return f"""
 <div class="card">
  <h2>🔍 Ihr Devis-Check: {html.escape(str(res['projekt']))}</h2>
  <p class="meta">{res['n_positionen']} Positionen · Netto {res['netto']:,.2f} CHF</p>
  <h3 style="margin-top:1rem">Positionen mit Margen-Risiko</h3>
  <ul class="warn-list">{lines}</ul>
  <div class="save" style="margin-top:1rem">Mit devispro sehen Sie diese Warnungen <b>automatisch bei jedem Devis</b> –
   inkl. Swiss QR-Rechnung und allen Formaten. KMU-Kunden sparen im Schnitt 2–3 Stunden pro Devis
   und verhindern Margen-Verluste von 5–15 %.</div>
  <div class="card" style="margin-top:1.2rem;background:#f0fdf4;border:1px solid #bbf7d0">
   <h3 style="margin:0 0 .4rem;color:#14532d">📩 Ihr Devis-Check als PDF + 3 Monate gratis</h3>
   <p class="meta">Hinterlassen Sie Ihre E-Mail – wir senden Ihnen den Check und schalten
   3 Monate kostenlos frei (keine Kreditkarte).</p>
   <form method="post" action="/check_lead">
    <input type="hidden" name="projekt" value="{html.escape(str(res['projekt']))}">
    <input type="email" name="email" placeholder="name@firma.ch" required style="width:260px;padding:.4rem">
    <button type="submit" class="btn">Zusenden &amp; 3 Monate testen</button>
   </form>
  </div>
  <p style="margin-top:1rem"><a class="btn-sm alt" href="/check">Weiteres Devis prüfen</a>
   <a class="btn-sm alt" href="/bepreisen">Eigenes Devis bepreisen</a></p>
 </div>
"""
