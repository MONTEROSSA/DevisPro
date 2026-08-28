"""Marketing-Materialien für das KMU (offline, reine Stdlib).

DevisPro hilft dem KMU nicht nur intern, sondern auch beim Vertrieb:
  - Social-Media-Posts (LinkedIn/Facebook/Instagram) für abgeschlossene Devis
  - Ausschreibungs-Anschreiben (Profi-Mail an Bauherren)
  - Referenz-Blatt (PDF) aus den letzten Projekten

So wird aus dem Rechen-Tool ein Vertriebs-Assistent.
"""

import os
import html

from . import pdf_native as PN
from .models import Devis


def social_post(profil, devis, plattform="linkedin", lang="de"):
    betrieb = profil.get("betrieb", "Ihr Betrieb")
    gewerk = profil.get("gewerk", "Bauleistungen")
    projekt = (devis.meta.get("project_name") or "ein spannendes Bauprojekt")
    netto = sum((p.betrag or 0) for p in devis.positions)
    if plattform == "linkedin":
        return (
            f"{betrieb} hat {projekt} abgeschlossen.\n\n"
            f"💡 {gewerk} – sauber kalkuliert mit DevisPro in CHF {netto:,.0f}".replace(",", "'") + "\n"
            f"📐 Vom Leistungsverzeichnis zum fertigen Angebot in Minuten.\n\n"
            f"#baunebenwerbung #schweiz #devispro"
        )
    if plattform == "facebook":
        return (
            f"🏗️ {betrieb} – Ihr Partner für {gewerk}!\n\n"
            f"Wir haben {projekt} realisiert. Saubere Offerten, faire Preise.\n"
            f"Jetzt unverbindlich anfragen: info@devispro.de"
        )
    if plattform == "instagram":
        return (
            f"{betrieb} ✨\n{gewerk} | {projekt}\n"
            f"Angebot in CHF {netto:,.0f}".replace(",", "'") + " 💸\n"
            f"#bau #schweiz #devispro #angebot"
        )
    return f"{betrieb}: {projekt}"


def ausschreibungs_anschreiben(profil, devis, lang="de"):
    betrieb = profil.get("betrieb", "Ihr Betrieb")
    addr = {}
    for a in (devis.addresses or []):
        role = (a.get("role") or "").lower()
        if "auftraggeber" in role or "besteller" in role or "maitre" in role or "committ" in role:
            addr = a
    name = addr.get("name", "Sehr geehrte Damen und Herren")
    projekt = devis.meta.get("project_name", "Ihr Bauprojekt")
    return (
        f"Sehr geehrte(r) {name},\n\n"
        f"vielen Dank für die Ausschreibung zu «{projekt}». Anbei finden Sie unser "
        f"vollständiges, geprüftes Angebot, erstellt mit DevisPro.\n\n"
        f"Wir übernehmen die Leistungen als General- bzw. Fachunternehmer und "
        f"stehen für Rückfragen gerne zur Verfügung.\n\n"
        f"Freundliche Grüsse\n{betrieb}\ninfo@devispro.de"
    )


def render_landing(lang="de"):
    """Professionelle Startseite (Landing Page) – vollständiges HTML-Dokument.

    Ersatz für die durch einen Sibling-Ueberschreib-Verlust verlorene Funktion.
    Bewusst self-contained (kein render_page-Wrapper), da webui.py es direkt
    mit Content-Type text/html ausliefert.
    """
    from devispro import pricing as _pz
    def _ff(x): return f"{x:,.0f}".replace(",", "'")
    d = _pz.preis("devis"); e = _pz.preis("erp")
    _lz_preis_str = (f"DevisPro {_ff(d['einrichtung'])} CHF + {_ff(d['lizenz_jahr'])} CHF/Jahr &middot; "
                     f"DevisPro + ERP {_ff(e['einrichtung'])} CHF + {_ff(e['lizenz_jahr'])} CHF/Jahr &middot; "
                     f"3 Monate Pilot gratis")
    t = {
        "de": {
            "title": "DevisPro – SIA-451 Devis automatisch bepreisen",
            "claim": "Vom Leistungsverzeichnis zum fertigen Angebot in Minuten. Korrekt, kantonal, compliant.",
            "sub": "DevisPro ist die schweizerische Komplettlösung für Bauleistungs-Devis: Import (SIA-451/Sorba, Bauweb, CSV/Excel, GÄB, ÖNORM, XRechnung), automatische Bepreisung, Offerte/Rechnung, Swiss-QR, Buchhaltungs-Export, KI-Agent – alles lokal auf Ihrem Mac/PC, ohne Cloud.",
            "cta": "Beispiel-Devis erstellen",
            "sec_features": "Alle Funktionen",
            "sec_why": "Warum DevisPro",
            "f1": "Ordner-Import", "f1d": "Laden Sie ganze Projektordner hoch – alle Unterlagen werden analysiert und das komplette Devis automatisch ausgefüllt.",
            "f2": "26 Kantone", "f2d": "Kantonale Aufschläge (NPK) und Marktpreis-Benchmark für realistische, rechtssichere Kalkulation.",
            "f3": "Buchhaltung", "f3d": "Export in Abacus, Proffix, BMD, DATEV, Banana, SAP, Lexoffice, SevDesk u.v.m. – Lock-in gebrochen.",
            "f4": "KI-Agent", "f4d": "Lokaler, offline Assistent: beantwortet Fragen und führt Aktionen aus (MWST, Kanton, Export, Währung).",
            "f5": "Margen-Copilot", "f5d": "Zeigt sofort, wo Marge verloren geht – vor Versand des Angebots.",
            "f6": "Swiss-QR", "f6d": "Rechnungen mit einzahlen.bar / PostFinance / Bank-QR – gesetzeskonform.",
            "w1": "Lokal & sicher – keine Daten verlassen Ihr Gerät",
            "w2": "Kein Abo-Zwang – einmalige Lizenz, jährlicher Freischalt-Code",
            "w3": "Schweizer Support durch Monterossa AG",
            "price": _lz_preis_str,
            "foot": 'DevisPro ist ein Produkt der <a href="https://www.monterossa.ch">www.monterossa.ch</a> &middot; <a href="mailto:info@devispro.de">info@devispro.de</a> &middot; devispro.de',
        }
    }
    T = t.get(lang, t["de"])
    features = [
        (T["f1"], T["f1d"]), (T["f2"], T["f2d"]), (T["f3"], T["f3d"]),
        (T["f4"], T["f4d"]), (T["f5"], T["f5d"]), (T["f6"], T["f6d"]),
    ]
    feat_html = "".join(
        f'<div class="card" style="flex:1 1 280px;min-width:260px">'
        f'<h3 style="margin:0 0 .4rem">🔧 {h}</h3><p class="meta" style="margin:0">{d}</p></div>'
        for h, d in features)
    why_html = "".join(f"<li>{w}</li>" for w in (T["w1"], T["w2"], T["w3"]))
    return f"""<!doctype html>
<html lang="{lang}"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{T['title']}</title>
<style>
 body{{font-family:-apple-system,Segö UI,Roboto,sans-serif;margin:0;background:#f4f7f5;color:#1b2a26}}
 .wrap{{max-width:1040px;margin:0 auto;padding:2.5rem 1.2rem}}
 header{{text-align:center;padding:2.5rem 1rem;background:linear-gradient(135deg,#0f5132,#198754);color:#fff;border-radius:0 0 18px 18px}}
 header h1{{margin:0 0 .6rem;font-size:2.1rem}}
 header p.claim{{margin:0 auto;max-width:720px;font-size:1.05rem;opacity:.95}}
 .cta{{display:inline-block;margin-top:1.4rem;background:#fff;color:#0f5132;padding:.8rem 1.6rem;border-radius:10px;font-weight:700;text-decoration:none}}
 .sub{{max-width:760px;margin:1.6rem auto;line-height:1.6}}
 h2.sec{{text-align:center;margin:2.4rem 0 1rem;color:#0f5132}}
 .grid{{display:flex;flex-wrap:wrap;gap:1rem;margin-top:1rem}}
 .card{{background:#fff;border:1px solid #e3e9e6;border-radius:12px;padding:1.1rem 1.2rem;box-shadow:0 1px 3px rgba(0,0,0,.04)}}
 ul.why{{max-width:680px;margin:1rem auto;line-height:1.9}}
 .price{{text-align:center;font-size:1.15rem;font-weight:700;color:#0f5132;margin:1.5rem 0}}
 footer{{text-align:center;color:#6b7c76;margin:3rem 0 1rem;font-size:.9rem}}
 .branchen{{display:flex;flex-wrap:wrap;gap:10px;justify-content:center;margin:1.4rem 0 .4rem}}
 .br{{background:#e8f5ec;border:1px solid #0f5132;color:#0f5132;padding:8px 14px;border-radius:20px;font-size:.95rem;font-weight:600}}
</style></head>
<body>
<header><h1>{T['title']}</h1><p class="claim">{T['claim']}</p>
<div class="cta-wrap" style="display:flex;gap:.8rem;justify-content:center;flex-wrap:wrap;margin-top:1.2rem">
<a class="cta" href="/DevisPro_Mac.zip" style="background:#ffd54a;color:#0f5132">&#11015; Jetzt herunterladen &amp; 3 Monate testen</a>
<a class="cta" href="/anleitung.html" style="background:#fff;color:#0f5132">📖 {T['cta']}</a>
</div></header>
<div class="wrap">
<p class="sub">{T['sub']}</p>
<h2 class="sec">{T['sec_features']}</h2>
<div class="grid">{feat_html}</div>
<h2 class="sec">{T['sec_why']}</h2>
<ul class="why">{why_html}</ul>
<h2 class="sec">Für welche Branchen</h2>
<p class="sub" style="text-align:center">DevisPro deckt die gesamte Schweizer Bauwirtschaft ab &ndash; vom Hoch- und Tiefbau über die Gebäudetechnik bis zum Ausbau, Holzbau und Nebengewerk. NPK-orientiert, kantonal korrekt.</p>
<div class="branchen">
 <span class="br">Maler</span><span class="br">Gipser</span><span class="br">Sanit&auml;rinstallation</span><span class="br">Heizung</span>
 <span class="br">L&uuml;ftung</span><span class="br">Elektro</span><span class="br">Spengler</span><span class="br">Glaser</span>
 <span class="br">Baumeister</span><span class="br">Maurer</span><span class="br">Bodenleger</span><span class="br">Schreiner</span>
 <span class="br">Fensterbau</span><span class="br">T&uuml;ren</span><span class="br">Holzbau / Zimmer</span><span class="br">Dachdecker</span>
 <span class="br">Plattenleger / Pflaster</span><span class="br">Schlosser / Metallbau</span><span class="br">Gartenbau / Landschaft</span><span class="br">Strassenbau</span>
 <span class="br">Abbruch</span><span class="br">Geb&auml;udereinigung</span><span class="br">Solar / Photovoltaik</span><span class="br">Aufzug / Fahrstuhl</span>
 <span class="br">W&auml;rmed&auml;mmung</span><span class="br">Fassadenbau</span><span class="br">Rollladen / Jalousien</span><span class="br">Bodenbel&auml;ge / Teppich</span>
 <span class="br">Brandschutz</span><span class="br">Pool / Schwimmbad</span><span class="br">Vermessung / Geomatik</span><span class="br">Planer / Architektur</span>
 <span class="br">Treuhand / Immobilien</span><span class="br">GU / Totalunternehmer</span>
</div>
<div class="card" style="max-width:720px;margin:2rem auto;text-align:center">
 <h2 style="margin-top:0">Integriertes ERP (Tarif DevisPro + ERP)</h2>
 <p class="meta">Lager, Einkauf, Verkauf, Buchhaltung und ein Live-Dashboard – direkt eingebaut.
 Sehen Sie sich das ERP unverbindlich als Beispiel an, bevor Sie entscheiden.</p>
 <a class="cta" href="/erp_vorschau" style="background:#0f5132;color:#fff">📊 ERP-Vorschau ansehen (Beispiel)</a>
 <a class="cta" href="/anleitung.html" download style="background:#1c4a8a;color:#fff">📖 Bedienungsanleitung herunterladen</a>
</div>
<p class="price">{T['price']}</p>
</div>
<footer>{T['foot']}</footer>
</body></html>"""


def referenz_blatt_pdf(profil, devis_liste, lang="de"):
    """devis_liste: Liste von (devis, projektname) Tupeln."""
    betrieb = str(profil.get("betrieb", "Ihr Betrieb") or "Ihr Betrieb")
    pdf = PN.PDF()
    pdf.heading(f"Referenzen – {betrieb}")
    pdf.footer("Erstellt mit DevisPro")
    pdf.subtitle("Ausgewählte Projekte")
    rows = []
    for devis, name in devis_liste:
        netto = sum((p.betrag or 0) for p in devis.positions)
        rows.append([name, str(len(devis.positions)), f"CHF {netto:,.0f}".replace(",", "'")])
    pdf.table(["Projekt", "Positionen", "Volumen"], rows, widths=[260, 100, 120], size=9)
    pdf.note("Referenzen sind anonymisierte Beispiele. Alle Kundennamen auf Wunsch.")


# ---- HTML-Werbemail (kein Anhang -> Kunden müssen nichts öffnen) ----
_WERBE_GRAD = "#0f7a3d"
_WERBE_DUNKEL = "#0b5e2f"
_WERBE_HELL = "#f3f8f4"


def _werbe_html_block(nutzen, preise):
    """Baut den HTML-Inhalt der Werbe-Mail. nutzen: Liste str, preise: Liste (label,wert)."""
    def zeile(t):
        return f'<li style="margin:0 0 8px 0;line-height:1.5">{html.escape(t)}</li>'
    nutzen_html = "".join(zeile(n) for n in nutzen)
    preise_html = "".join(
        f'<tr><td style="padding:8px 0;border-bottom:1px solid #e3e9e5">{html.escape(l)}</td>'
        f'<td style="padding:8px 0;border-bottom:1px solid #e3e9e5;text-align:right;font-weight:bold">'
        f'{html.escape(v)}</td></tr>'
        for l, v in preise
    )
    return f"""<!DOCTYPE html>
<html lang="de">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:{_WERBE_HELL};font-family:Helvetica,Arial,sans-serif;color:#1a1a1a">
<div style="max-width:620px;margin:0 auto;background:#ffffff">
  <div style="background:{_WERBE_GRAD};padding:28px 32px">
    <h1 style="margin:0;color:#fff;font-size:24px;line-height:1.25">DevisPro</h1>
    <p style="margin:6px 0 0 0;color:#dff3e7;font-size:14px">SIA-451-Devis automatisch bepreisen</p>
  </div>
  <div style="padding:28px 32px">
    <p style="margin:0 0 16px 0;font-size:15px;line-height:1.6">
      Baün Sie Offerte in <b>Minuten statt Stunden</b>. DevisPro liest Ihr SIA-451-Devis und
      bepreist jede Position automatisch mit Ihren Stammdaten &ndash; inkl. Kantonsfaktoren und MWST.
    </p>
    <h2 style="margin:24px 0 10px 0;color:{_WERBE_DUNKEL};font-size:18px">Ihr Nutzen</h2>
    <ul style="margin:0;padding-left:20px;font-size:14px">{nutzen_html}</ul>
    <h2 style="margin:24px 0 10px 0;color:{_WERBE_DUNKEL};font-size:18px">Preismodell</h2>
    <table style="width:100%%;border-collapse:collapse;font-size:14px">{preise_html}</table>
    <div style="margin:24px 0 8px 0;background:{_WERBE_HELL};border-left:4px solid {_WERBE_GRAD};padding:16px 18px;font-size:14px;line-height:1.6">
      <b>Jetzt Pilot sichern:</b> Testen Sie DevisPro <b>3 Monate kostenlos</b> &ndash; einfach
      herunterladen und mit <b>IHREN</b> echten Devis starten. Kein Risiko, keine Karte nötig.
    </div>
    <p style="margin:24px 0 0 0;font-size:14px;line-height:1.6">
      <a href="https://devispro.de/DevisPro_Mac.zip" style="background:{_WERBE_GRAD};color:#fff;text-decoration:none;padding:12px 22px;border-radius:6px;display:inline-block;font-weight:bold">⬇ Jetzt 3 Monate testen &ndash; Download</a>
      &nbsp;
      <a href="mailto:info@devispro.de" style="background:#fff;color:{_WERBE_DUNKEL};text-decoration:none;padding:12px 22px;border-radius:6px;display:inline-block;font-weight:bold;border:1px solid {_WERBE_GRAD}">Fragen? Antworten</a>
    </p>
  </div>
  <div style="background:#f0f3f1;padding:16px 32px;font-size:12px;color:#5a5a5a">
    DevisPro &middot; Monterossa AG &middot; <a href="mailto:info@devispro.de" style="color:{_WERBE_DUNKEL}">info@devispro.de</a> &middot; devispro.de
  </div>
</div>
</body></html>"""


def werbe_mail_html(lang="de"):
    """Liefert (text, html) für die HTML-Werbemail. Ohne Anhang -> phishing-sicher.
    Kann von Web-UI und CLI genutzt werden."""
    from devispro import pricing as _pz
    def _fmt(x):
        return f"{x:,.0f}".replace(",", "'")
    nutzen = [
        "Automatische Bepreisung aller Positionen (Sorba, Bauweb, CSV/Excel, GÄB, ÖNORM, XRechnung) – Fehlerquoten gegen Null",
        "Schweizweite Abdeckung: NPK, 7 Gewerke, 26 Kantone",
        "Margen-Copilot & Marktpreis-Benchmark für sichere Angebote",
        "Komplett lokal & sicher – keine Daten verlassen Ihr Gerät",
        "Foto-Import, Gratis-Devis-Check und PDF-Offerte mit Swiss-QR",
        "Einmalige Lizenz, jährlicher Freischalt-Code – kein Abomodell",
        "Optional DevisPro + ERP: Lager & Stücklisten, Einkauf/Bestellung, Verkauf (Offerte→Auftrag→Rechnung), Buchhaltung mit MWST-Abrechnung",
        "Mahnwesen, Debitoren-Kreditlimit, Inventur und 13 Buchhaltungs-Exporte (Abacus, Proffix, BMD, DATEV, Banana, SAP …)",
    ]
    d = _pz.preis("devis")
    e = _pz.preis("erp")
    preise = [
        ("DevisPro – Einrichtung", f"{_fmt(d['einrichtung'])} CHF (einmalig)"),
        ("DevisPro – Lizenz pro Jahr", f"{_fmt(d['lizenz_jahr'])} CHF"),
        ("DevisPro + ERP – Einrichtung", f"{_fmt(e['einrichtung'])} CHF (einmalig)"),
        ("DevisPro + ERP – Lizenz pro Jahr", f"{_fmt(e['lizenz_jahr'])} CHF"),
        ("Pilot", "3 Monate gratis (beide Tarife)"),
        ("Support", "Monterossa AG"),
    ]
    html = _werbe_html_block(nutzen, preise)
    text = (
        "Guten Tag\n\n"
        "Baün Sie Offerte in Minuten statt Stunden. DevisPro liest Ihr SIA-451-Devis und bepreist "
        "jede Position automatisch.\n\n"
        "Zwei Tarife:\n"
        f"  DevisPro:        {_fmt(d['einrichtung'])} CHF Einrichtung + {_fmt(d['lizenz_jahr'])} CHF/Jahr\n"
        f"  DevisPro + ERP:  {_fmt(e['einrichtung'])} CHF Einrichtung + {_fmt(e['lizenz_jahr'])} CHF/Jahr\n"
        "    Das integrierte ERP bietet: Lager & Stücklisten, Einkauf/Bestellung,\n"
        "    Verkauf (Offerte->Auftrag->Rechnung), Buchhaltung mit MWST-Abrechnung,\n"
        "    Mahnwesen, Debitoren-Kreditlimit, Inventur und 13 Buchhaltungs-Exporte\n"
        "    (Abacus, Proffix, BMD, DATEV, Banana, SAP ...).\n"
        "  Pilot: 3 Monate gratis, danach 500 CHF Rabatt.\n\n"
        "Jetzt 3 Monate kostenlos testen: Laden Sie DevisPro einfach herunter und starten Sie mit "
        "IHREN echten Devis – kein Risiko, keine Karte nötig.\n"
        "Download: https://devispro.de/DevisPro_Mac.zip\n\n"
        "Fragen? Antworten Sie auf diese Mail oder schreiben Sie an info@devispro.de.\n\n"
        "Freundliche Grüsse\nMonterossa AG\ninfo@devispro.de · devispro.de\n"
    )
    return text, html


def homepage_html(lang="de"):
    """Moderne, informative, lukrative öffentliche Homepage (devispro.de)."""
    from devispro import pricing as _pz
    d = _pz.preis("devis")
    e = _pz.preis("erp")
    def f(x): return f"{x:,.0f}".replace(",", "'")
    DEV_EIN, DEV_J, ERP_EIN, ERP_J = f(d["einrichtung"]), f(d["lizenz_jahr"]), f(e["einrichtung"]), f(e["lizenz_jahr"])
    return ("""<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>DevisPro – SIA-451-Devis automatisch bepreisen + integriertes ERP</title>
<style>
  *{box-sizing:border-box;margin:0;padding:0}
  body{font-family:Helvetica,Arial,sans-serif;color:#1a1a1a;background:#f3f8f4;line-height:1.6}
  .hero{background:linear-gradient(135deg,#0b5e2f 0%%,#0f7a3d 100%%);color:#fff;padding:90px 24px 70px;text-align:center}
  .hero h1{font-size:3rem;margin-bottom:16px;letter-spacing:-.5px}
  .hero p{font-size:1.25rem;max-width:760px;margin:0 auto;color:#dff3e7}
  .badge{display:inline-block;background:rgba(255,255,255,.15);border:1px solid rgba(255,255,255,.4);padding:6px 14px;border-radius:20px;font-size:.85rem;margin-bottom:18px}
  .cta{margin-top:34px}
  .btn{display:inline-block;background:#fff;color:#0b5e2f;text-decoration:none;padding:15px 30px;border-radius:8px;font-weight:bold;margin:8px}
  .btn.alt{background:#0b5e2f;color:#fff;border:1px solid #fff}
  .wrap{max-width:1040px;margin:0 auto;padding:60px 24px}
  h2{color:#0b5e2f;font-size:2rem;margin:48px 0 8px;text-align:center}
  .sub{text-align:center;color:#5a6b62;max-width:680px;margin:0 auto 8px}
  .grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:18px;margin-top:28px}
  .card{background:#fff;border:1px solid #e3e9e5;border-radius:10px;padding:24px}
  .card h3{color:#0b5e2f;margin-bottom:10px;font-size:1.15rem}
  .card p{font-size:.95rem;color:#444}
  .steps{counter-reset:s;display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:18px;margin-top:28px}
  .step{background:#fff;border:1px solid #e3e9e5;border-radius:10px;padding:24px;position:relative}
  .step:before{counter-increment:s;content:"0" counter(s);display:block;font-size:1.6rem;font-weight:bold;color:#0f7a3d;margin-bottom:8px}
  table{width:100%%;border-collapse:collapse;margin:18px 0}
  td{padding:13px 0;border-bottom:1px solid #e3e9e5}
  td:last-child{text-align:right;font-weight:bold}
  .tier{background:#fff;border:1px solid #e3e9e5;border-radius:12px;padding:30px;margin-top:22px}
  .tier.empf{border:2px solid #0f7a3d;box-shadow:0 8px 24px rgba(15,122,61,.14)}
  .tier h3{color:#0b5e2f;font-size:1.5rem}
  .tier .preis{font-size:1.7rem;font-weight:bold;margin:12px 0;color:#0b5e2f}
  .tier ul{margin:10px 0 0 18px;font-size:.95rem}
  .tier ul li{margin:5px 0}
  .quote{background:#fff;border-left:4px solid #0f7a3d;padding:22px 26px;border-radius:8px;margin:24px 0;font-style:italic}
  .box{background:#0f7a3d;color:#fff;padding:34px 24px;border-radius:10px;text-align:center;margin:36px 0}
  .box a{background:#fff;color:#0b5e2f}
  .faq{margin-top:24px}
  .faq dt{font-weight:bold;color:#0b5e2f;margin-top:16px}
  .faq dd{color:#444;margin:4px 0 0 0}
  footer{background:#1a1a1a;color:#cfcfcf;font-size:.88rem;padding:36px 24px;text-align:center;line-height:1.9}
  footer a{color:#6fe0a0;text-decoration:none}
  ul.feat{margin:0 0 0 18px}
  ul.feat li{margin:6px 0}
  .branchen{display:flex;flex-wrap:wrap;gap:10px;margin:18px 0 8px}
  .br{background:#e8f5ec;border:1px solid #0f7a3d;color:#0b5e2f;padding:8px 14px;border-radius:20px;font-size:.95rem;font-weight:600}
</style>
</head>
<body>
<div class="hero">
  <div class="badge">Schweizer KMU-Lösung · lokal · DSGVO-konform</div>
  <h1>DevisPro</h1>
  <p>SIA-451-Devis in Minuten statt Stunden automatisch bepreisen – und optional ein
     komplettes ERP für Ihren Bau-Betrieb, direkt integriert. Alles auf Ihrem Mac, keine Cloud-Zwang.</p>
  <div class="cta">
    <a class="btn" href="/DevisPro_Mac.zip">&#11015; Jetzt 3 Monate testen – Download</a>
    <a class="btn alt" href="mailto:info@devispro.de">Fragen? Antworten</a>
  </div>
</div>
<div class="wrap">

  <h2>Das spart Ihnen echte Zeit</h2>
  <p class="sub">Von der Import-Datei bis zur versandfertigen Offerte mit Swiss-QR – in wenigen Klicks, ohne Copy-Paste-Fehler.</p>
  <div class="grid">
    <div class="card"><h3>Automatische Bepreisung</h3><p>Import von Sorba, Bauweb, CSV/Excel, GÄB, ÖNORM, XRechnung. Artikel werden automatisch mit Schweizer Marktpreisen bepreist – Fehlerquoten gegen Null.</p></div>
    <div class="card"><h3>Schweizweite Abdeckung</h3><p>NPK, 7 Gewerke, alle 26 Kantone mit kantonalen Faktoren. Regional korrekt kalkuliert, vom Tessin bis Graubünden.</p></div>
    <div class="card"><h3>Marge im Griff</h3><p>Margen-Copilot, Marktpreis-Benchmark und Subunternehmer-Marge. Sie sehen sofort, ob das Geschäft rentabel ist.</p></div>
    <div class="card"><h3>Sicher &amp; lokal</h3><p>Keine Daten verlassen Ihr Gerät. PDF-Offerte mit Swiss-QR, Foto-Import und ein kostenloser Devis-Check als Lead-Magnet.</p></div>
    <div class="card"><h3>Integriertes ERP (optional)</h3><p>Lager, Einkauf, Verkauf, Buchhaltung und ein Live-Dashboard – im Tarif DevisPro + ERP direkt eingebaut.</p></div>
    <div class="card"><h3>13 Buchhaltungs-Exporte</h3><p>Abacus, Proffix, BMD, DATEV, Banana, SAP, Excel und mehr – Ihre Daten wandern nahtlos an die Treuhand.</p></div>
  </div>

  <h2>So funktioniert's</h2>
  <div class="steps">
    <div class="step"><h3>Importieren</h3><p>Devis als SIA-451, Sorba, Bauweb, GÄB, CSV/Excel oder Foto hochladen.</p></div>
    <div class="step"><h3>Bepreisen</h3><p>DevisPro schlägt Einheitspreise vor, prüft Kanton/Gewerk und gleicht Marge ab.</p></div>
    <div class="step"><h3>Offerte erstellen</h3><p>PDF-Offerte mit Swiss-QR, oder direkt ins integrierte ERP übernehmen.</p></div>
  </div>

  <h2>Für welche Branchen</h2>
  <p class="sub">DevisPro deckt die gesamte Schweizer Bauwirtschaft ab &ndash; vom Hoch- und Tiefbau über die Gebäudetechnik bis zum Ausbau, Holzbau und Nebengewerk. NPK-orientiert, kantonal korrekt.</p>
  <div class="branchen">
    <span class="br">Maler</span><span class="br">Gipser</span><span class="br">Sanit&auml;rinstallation</span><span class="br">Heizung</span>
    <span class="br">L&uuml;ftung</span><span class="br">Elektro</span><span class="br">Spengler</span><span class="br">Glaser</span>
    <span class="br">Baumeister</span><span class="br">Maurer</span><span class="br">Bodenleger</span><span class="br">Schreiner</span>
    <span class="br">Fensterbau</span><span class="br">T&uuml;ren</span><span class="br">Holzbau / Zimmer</span><span class="br">Dachdecker</span>
    <span class="br">Plattenleger / Pflaster</span><span class="br">Schlosser / Metallbau</span><span class="br">Gartenbau / Landschaft</span><span class="br">Strassenbau</span>
    <span class="br">Abbruch</span><span class="br">Geb&auml;udereinigung</span><span class="br">Solar / Photovoltaik</span><span class="br">Aufzug / Fahrstuhl</span>
    <span class="br">W&auml;rmed&auml;mmung</span><span class="br">Fassadenbau</span><span class="br">Rollladen / Jalousien</span><span class="br">Bodenbel&auml;ge / Teppich</span>
    <span class="br">Brandschutz</span><span class="br">Pool / Schwimmbad</span><span class="br">Vermessung / Geomatik</span><span class="br">Planer / Architektur</span>
    <span class="br">Treuhand / Immobilien</span><span class="br">GU / Totalunternehmer</span>
  </div>
  <p class="meta">Planer, Architekturbüros und Treuhand, die Devis Ihrer Bau-Partner prüfen, nutzen den <a href="/check">gratis Devis-Check</a> ebenfalls.</p>

  <h2>Zwei Tarife &ndash; wählen Sie Ihren</h2>
  <p class="sub">Beide Tarife enthalten die automatische SIA-451-Bepreisung. Das ERP ist die optionale Erweiterung für Betriebe, die mehr brauchen.</p>
  <div class="tier">
    <h3>DevisPro</h3>
    <div class="preis">%s CHF Einrichtung + %s CHF/Jahr</div>
    <p>SIA-451-Devis automatisch bepreisen, schweizweit, mit Margen-Copilot und Swiss-QR. 3 Monate gratis testen.</p>
  </div>
  <div class="tier empf">
    <h3>DevisPro + ERP</h3>
    <div class="preis">%s CHF Einrichtung + %s CHF/Jahr</div>
    <p>Alles aus DevisPro plus ein vollwertiges ERP:</p>
    <ul>
      <li><b>Artikel &amp; Lager:</b> Bestand, Mindestbestand, Stücklisten, Wareneingang, Nachbestelllisten</li>
      <li><b>Einkauf:</b> Lieferanten, Bestellungen, Disposition, MWST-Abzug</li>
      <li><b>Verkauf:</b> Offerten &#8594; Auftrag &#8594; Rechnung, Teilzahlungen, Mahnwesen (3 Stufen)</li>
      <li><b>Buchhaltung:</b> Journal, Kontenrahmen KMU, Debitoren/Kreditoren, MWST-Abrechnung</li>
      <li><b>Dashboard:</b> Umsatz, offene Posten, Lagerwert, Marge – live</li>
    </ul>
  </div>
  <p style="text-align:center;margin-top:1rem"><a class="cta" href="/erp_vorschau" style="background:#0f5132;color:#fff">📊 ERP-Vorschau ansehen (Beispiel)</a></p>

  <h2>Preisübersicht</h2>
  <table>
    <tr><td>DevisPro – Einrichtung</td><td>%s CHF (einmalig)</td></tr>
    <tr><td>DevisPro – Lizenz pro Jahr</td><td>%s CHF</td></tr>
    <tr><td>DevisPro + ERP – Einrichtung</td><td>%s CHF (einmalig)</td></tr>
    <tr><td>DevisPro + ERP – Lizenz pro Jahr</td><td>%s CHF</td></tr>
    <tr><td>Pilot</td><td>3 Monate gratis (beide Tarife)</td></tr>
    <tr><td>Support</td><td>Monterossa AG</td></tr>
  </table>

  <div class="quote">"Wir offerieren in Minuten statt Stunden – und mit dem ERP sehe ich Umsatz, offene Devis und Lagerwert auf einen Blick. Ein Gamechanger für unser Baugeschäft."<br>– Schweizer KMU, Sanitär &amp; Heizung</div>

  <h2>Gratis Devis-Check &ndash; in 30 Sekunden</h2>
  <div class="tier">
    <p>Laden Sie ein Devis hoch (SIA-451/Sorba, Bauweb, CSV/Excel, GÄB, &Ouml;NORM, XRechnung) &ndash;
    devispro zeigt Ihnen <b>anonym 3 Positionen, wo Sie vermutlich Marge verlieren</b>. Kein Login, keine Installation.</p>
    <div class="cta"><a class="btn" href="/check">&#128269; Jetzt gratis Devis-Check starten</a></div>
  </div>

  <h2>Null Tippen am Tag 1 &ndash; Preise lernt sich von alleine</h2>
  <div class="tier">
    <p>Laden Sie einfach <b>3 Ihrer echten, bereits bepreisten Devis</b> hoch. devispro extrahiert Ihre
    Einheitspreise und baut die komplette Stammdatenliste automatisch &ndash; ohne ein einziges Feld von Hand zu f&uuml;llen.
    Das ist der gr&ouml;sste Vorteil gegen&uuml;ber Abacus und Proffix, wo die Preisliste Woche 1 komplett leer ist.</p>
    <div class="cta"><a class="btn" href="/bepreisen">&#129504; Preise automatisch lernen</a></div>
  </div>

  <h2>Häufige Fragen</h2>
  <dl class="faq">
    <dt>Wie funktioniert die Lizenz?</dt><dd>Einmalige Einrichtung plus jährlicher Freischalt-Code vom Anbieter. Ohne Code ist die Software nicht nutzbar – Schutz vor Raubkopie.</dd>
    <dt>Kann ich erst testen?</dt><dd>Ja. 3 Monate Pilot gratis, mit IHREN echten Devis. Keine Karte, kein Risiko.</dd>
    <dt>Laufen meine Daten in die Cloud?</dt><dd>Nein. Alles bleibt lokal auf Ihrem Mac. Keine Server-Zwang, DSGVO-konform.</dd>
    <dt>Welche Formate werden unterstützt?</dt><dd>SIA-451/Sorba, Bauweb, CSV/Excel, GÄB, ÖNORM, XRechnung, Swiss QR – plus Foto-Import.</dd>
    <dt>Bekomme ich das ERP auch später?</dt><dd>Ja. Upgrade jederzeit über Monterossa AG (info@devispro.de).</dd>
  </dl>

  <div class="box">
    <b>Jetzt Pilot sichern:</b> 3 Monate kostenlos testen – einfach herunterladen und mit IHREN echten Devis starten. Kein Risiko, keine Karte nötig.
    <div class="cta"><a class="btn" href="/DevisPro_Mac.zip">&#11015; Download starten</a></div>
  </div>
</div>
<footer>
  DevisPro ist ein Produkt der <a href="https://www.monterossa.ch">www.monterossa.ch</a> &middot;
  <a href="mailto:info@devispro.de">info@devispro.de</a> &middot; devispro.de
</footer>
</body>
</html>""" % (DEV_EIN, DEV_J, ERP_EIN, ERP_J, DEV_EIN, DEV_J, ERP_EIN, ERP_J))
