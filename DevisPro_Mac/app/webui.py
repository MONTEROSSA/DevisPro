"""Web-UI fuer devispro (reine Python-Stdlib, kein Flask noetig).

Features:
  - Profil + Richtpreise EINMAL eingeben -> bleiben persistent (data/)
  - Devis hochladen -> automatisch mit gespeicherten Preisen bepreisen
  - Review-Blocker (Download gesperrt bis Fachkraft-Freigabe)
  - ROI-Kalkulator (Zeit/Geld-Ersparnis, Break-even, 12-Monats-Cashflow)

Start: python3 webui.py   ->  http://localhost:5070
"""
import os
import sys
import cgi
import html
import json
import time
import shutil
import re
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, urlencode, parse_qs, quote

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from devispro.parsers import crb
from devispro.models import Devis
from devispro.pricelist import load as load_prices
from devispro.matcher import Matcher
from devispro import stammdaten
from devispro import roi as roi_mod
from devispro import kantone as kant_mod
from devispro import license as liz
from devispro import admin_auth as auth
from devispro import i18n as i18n_mod
from devispro import pdf as pdf_mod
from devispro import marketing as marketing_mod
from devispro import history as history_mod
from devispro import documents as documents_mod
from devispro import rechnung as rechnung_mod
from devispro import updates as updates_mod
from devispro import connector as connector_mod
from devispro import accounting as accounting_mod
from devispro import ordner_import as ordner_mod
from devispro import multicurrency as mc_mod
from devispro import whatsapp_bot as wa_mod
from devispro import subunternehmer as sub_mod
from devispro import margen_copilot as margen_mod
from devispro import marketing as marketing_mod
from devispro import erp_api as erp_mod
from devispro import agent as agent_mod
from devispro import backup as backup_mod
from devispro import diagnostics as diag_mod
from devispro import mahnung as mahnung_mod
from devispro import abo as abo_mod
from devispro import lifecycle as lifecycle_mod
from devispro import whitelabel as whitelabel_mod
from devispro import license_admin as lizadm
from devispro.documents import export_pdf as doc_export_pdf
from devispro.i18n import t as _t, LANGS
from devispro import plausibility as plausib_mod
from devispro import benchmark as bench_mod
from devispro import vision as vision_mod
from devispro import templates as templates_mod
from devispro import recurring as recurring_mod
from devispro import team_auth as team_mod
from devispro import team_sync as sync_mod


def _read_raw_post(self):
    """Rohdaten des POST-Bodys (fuer eigene Multipart-Parser)."""
    length = int(self.headers.get("Content-Length", 0) or 0)
    return self.rfile.read(length) if length else b""


def _parse_multipart_file(self, field_name):
    """Liest eine Datei aus einem multipart/form-data POST roh ein.

    Umgeht cgi.FieldStorage (das in Py3.9 Bilder im Text-Mode parst und
    bei PNG-Bytes mit UnicodeDecodeError abstuerzt). Liefert (filename, bytes)
    oder (None, None).
    """
    ctype = self.headers.get("Content-Type", "")
    if "multipart/form-data" not in ctype:
        return None, None
    boundary = None
    for part in ctype.split(";"):
        part = part.strip()
        if part.startswith("boundary="):
            boundary = part[len("boundary="):].strip().strip('"')
    if not boundary:
        return None, None
    raw = _read_raw_post(self)
    delim = b"--" + boundary.encode()
    # Teile zwischen den Trennern
    parts = raw.split(delim)
    for part in parts:
        if b"Content-Disposition" not in part:
            continue
        # part beginnt mit \r\n\r\n (Header/Body-Grenze)
        head, sep, body = part.partition(b"\r\n\r\n")
        if not sep:
            continue
        head = head.decode("utf-8", "ignore")
        if "name=\"%s\"" % field_name not in head:
            continue
        # Dateiname extrahieren
        fn = None
        for tok in head.split(";"):
            tok = tok.strip()
            if tok.startswith("filename="):
                fn = tok[len("filename="):].strip().strip('"')
        body = body.rstrip(b"\r\n")  # trailing CRLF des Parts entfernen
        return fn, body
    return None, None


HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
os.makedirs(DATA, exist_ok=True)
PORT = int(os.environ.get("PORT", "5070"))


PAGE = """<!doctype html>
<html lang="{HTML_LANG}"><head><meta charset="utf-8">
<title>devispro – SIA-451 Bepreisung</title>
<style>
 body{{font-family:-apple-system,system-ui,sans-serif;max-width:1000px;margin:2rem auto;padding:0 1rem;color:#1a1a1a}}
 h1{{font-size:1.5rem}} h2{{font-size:1.15rem;margin-top:1.5rem;border-bottom:2px solid #1d4ed8;padding-bottom:.3rem}}
 .card{{border:1px solid #ddd;border-radius:10px;padding:1.2rem;margin:1rem 0;background:#fafafa}}
 .nav a{{margin-right:1rem;color:#1d4ed8;text-decoration:none;font-weight:600}}
 .topbar{{display:flex;align-items:center;gap:1rem;flex-wrap:wrap;padding:.7rem 0;border-bottom:2px solid #1d4ed8;margin-bottom:1rem}}
 .topbar .brand{{font-weight:800;font-size:1.2rem;color:#14532d}}
 .topbar .nav{{flex:1;display:flex;gap:.3rem;flex-wrap:wrap}}
 .topbar .nav a{{margin:0;padding:.25rem .5rem;border-radius:6px}}
 .topbar .nav a:hover{{background:#eef2ff}}
 .topbar .actions{{display:flex;gap:.5rem}}
 .btn-sm{{display:inline-block;background:#1d4ed8;color:#fff;padding:.5rem .9rem;border-radius:8px;text-decoration:none;font-weight:600;font-size:.9rem;white-space:nowrap}}
 .btn-sm.alt{{background:#15803d}}
 .btn-sm:hover{{opacity:.9}}
 .lang a{{color:#666;text-decoration:none;font-weight:700;padding:.15rem .35rem;border-radius:5px;font-size:.85rem}}
 .lang a.on{{color:#1d4ed8;background:#eef2ff}}
 .lang a:hover{{background:#f1f5f9}}
 label{{display:block;margin:.5rem 0 .2rem;font-weight:600}}
 input[type=file],input[type=text],input[type=number],select{{width:100%;padding:.5rem;border:1px solid #ccc;border-radius:6px;box-sizing:border-box}}
 .grid{{display:grid;grid-template-columns:1fr 1fr;gap:.6rem 1.2rem}}
 button{{margin-top:1rem;background:#1d4ed8;color:#fff;border:0;padding:.7rem 1.4rem;border-radius:8px;font-size:1rem;cursor:pointer}}
 table{{border-collapse:collapse;width:100%;margin-top:1rem;font-size:.85rem}}
 th,td{{border:1px solid #e2e2e2;padding:.35rem .55rem;text-align:left}} th{{background:#f0f4ff}}
 .rev{{color:#b91c1c;font-weight:700}} .ok{{color:#15803d}} .meta{{color:#555;font-size:.9rem}}
 code{{background:#eee;padding:.1rem .35rem;border-radius:4px}}
 a.btn{{display:inline-block;margin-top:1rem;background:#15803d;color:#fff;padding:.7rem 1.4rem;border-radius:8px;text-decoration:none}}
 .warn{{background:#fff7ed;border:1px solid #fdba74;border-radius:8px;padding:.8rem;margin:.6rem 0;font-size:.88rem;line-height:1.5}}
 .blocker{{background:#fef2f2;border:1px solid #fca5a5;border-radius:8px;padding:.8rem 1rem;margin:.6rem 0;font-size:.9rem;line-height:1.5}}
 .blocker ul{{margin:.4rem 0 .2rem 1.1rem}} .blocker li{{margin:.2rem 0}}
 .okbox{{background:#f0fdf4;border:1px solid #86efac;border-radius:8px;padding:.7rem;margin:.6rem 0;color:#166534}}
 .kpi{{display:grid;grid-template-columns:repeat(3,1fr);gap:1rem;margin-top:1rem}}
 .kpi div{{background:#1d4ed8;color:#fff;border-radius:10px;padding:1rem;text-align:center}}
 .kpi .v{{font-size:1.5rem;font-weight:700}} .kpi .l{{font-size:.8rem;opacity:.9}}
 .chart{{width:100%;height:220px;margin-top:1rem}}
 .save{{background:#d1fae5;border:1px solid #86efac;border-radius:8px;padding:.6rem;margin-top:.6rem;color:#065f46}}
 .warn-box{{background:#fff7ed;border:1px solid #fdba74;border-radius:8px;padding:.8rem 1rem;margin-top:1rem;font-size:.88rem;line-height:1.5}}
 .warn-list{{margin:.4rem 0 0 1.1rem;padding:0}}
 .warn-list li{{margin:.2rem 0}}
 .warn-list .w-high{{color:#b91c1c;font-weight:600}}
 .warn-list .w-med{{color:#b45309}}
 .warn-list .w-low{{color:#92400e}}
 .bm{{font-size:.75rem;font-weight:700;padding:.1rem .35rem;border-radius:4px;white-space:nowrap}}
 .bm.low{{background:#fee2e2;color:#b91c1c}}
 .bm.high{{background:#fef3c7;color:#92400e}}
 .bm.ok{{background:#dcfce7;color:#166534}}
 .bm{{background:#f1f5f9;color:#64748b}}
 .update-banner{{position:sticky;top:0;z-index:50;background:#14532d;color:#fff;
  display:flex;align-items:flex-start;gap:1rem;padding:.7rem 1rem;box-shadow:0 2px 8px rgba(0,0,0,.18)}}
 .update-banner .ub-inner{{flex:1}}
 .update-banner strong{{display:block;font-size:.95rem}}
 .update-banner .ub-sub{{font-size:.8rem;opacity:.85}}
 .update-banner ul.ub-notes{{margin:.3rem 0 0 1.1rem;font-size:.8rem}}
 .update-banner .ub-btn{{display:inline-block;margin-top:.4rem;background:#fff;color:#14532d;
  padding:.3rem .8rem;border-radius:6px;font-weight:700;text-decoration:none;font-size:.8rem}}
 .update-banner .ub-close{{background:none;border:none;color:#fff;font-size:1.4rem;cursor:pointer;line-height:1}}
 @media print {{
  .nav,.lang,.btn,.update-banner{{display:none !important}}
  body{{background:#fff}} .card{{box-shadow:none;border:none}}
 }}
 .stages{{display:flex;flex-wrap:wrap;gap:1rem;margin:1.2rem 0}}
 .stage{{flex:1 1 160px;border:2px solid #d6d3d3;border-radius:10px;padding:1rem;background:#fff;opacity:.85}}
 .stage.done{{border-color:#15803d;background:#f0fdf4;opacity:1}}
 .stagenum{{font-weight:800;color:#14532d;margin-bottom:.3rem}}
 .stagedesc{{font-size:.85rem;color:#444;margin-bottom:.6rem}}
 .muted{{color:#999;font-size:.85rem}}</style></head><body>
<script>
// Update-Hinweis: sofort beim Oeffnen pruefen (offline-sicher).
(function(){{
 try{{
  fetch('/api/version').then(function(r){{return r.json();}}).then(function(d){{
   if(d && d.available){{
    var b=document.createElement('div'); b.innerHTML=d.banner;
    document.body.insertBefore(b.firstChild, document.body.firstChild);
   }}
  }}).catch(function(){{}});
 }}catch(e){{}}
}})();
</script>
{NAV}
{RESULT}
<footer style="margin-top:2.5rem;padding:1.2rem 0;border-top:2px solid #e2e2e2;text-align:center;font-size:.85rem;color:#666">
  DevisPro ist ein Produkt der <a href="https://www.monterossa.ch" style="color:#1d4ed8;text-decoration:none;font-weight:600">www.monterossa.ch</a>
  &middot; <a href="mailto:info@devispro.de" style="color:#1d4ed8;text-decoration:none">info@devispro.de</a> &middot; devispro.de
</footer>
</body></html>"""


def lang_from_request(self):
    """Sprache aus Query (?lang=) oder Cookie (lang=) lesen, Default 'de'."""
    from urllib.parse import urlparse
    parsed = urlparse(self.path)
    q = parse_qs(parsed.query)
    if "lang" in q and q["lang"][0] in LANGS:
        return q["lang"][0]
    cookie = self.headers.get("Cookie", "")
    for part in cookie.split(";"):
        part = part.strip()
        if part.startswith("lang=") and part[5:] in LANGS:
            return part[5:]
    return "de"


def render_nav(lang):
    """Oberer Navigationsbalken mit Aktionen + Sprachumschaltung (persistent via Cookie)."""
    def L(k):
        return _t(k, lang)
    links = [
        ("/", L("bepreisen")),
        ("/profil", L("stammdaten")),
        ("/roi", L("roi")),
        ("/dashboard", L("dashboard")),
        ("/benchmark", "Benchmark"),
        ("/vorlagen", "Vorlagen"),
        ("/wiederkehrend", "Wdh-Rechn."),
        ("/sync", "Sync"),
        ("/ordner_import", "Ordner"),
        ("/waehrung", "Währung"),
        ("/whatsapp", "WhatsApp"),
        ("/subunternehmer", "Sub"),
        ("/margen", "Marge"),
        ("/marketing", "Marketing"),
        ("/erp_api", "ERP-API"),
        ("/agent", "KI-Agent"),
        ("/backup", "Backup"),
        ("/abo", "Abo"),
        ("/setup", "Setup"),
        ("/diagnose", "Diagnose"),
        ("/lizenz", L("lizenz")),
    ]
    nav_links = "".join(f'<a href="{u}">{html.escape(t)}</a>' for u, t in links)
    lang_sw = " · ".join(
        f'<a href="/lang/{c}" class="{"on" if c==lang else ""}">{c.upper()}</a>'
        for c in LANGS)
    return f"""<div class="topbar">
 <div class="brand">devispro</div>
 <div class="nav">{nav_links}</div>
 <div class="actions">
   <a class="btn-sm" href="/bepreisen">{L('neues_devis')}</a>
   <a class="btn-sm alt" href="/meine_devis">{L('meine_devis')}</a>
   <a class="btn-sm" href="/team_login">👥 Team</a>
 </div>
 <div class="lang" title="{L('sprache')}">{lang_sw}</div>
</div>"""


def render_page(body_html, lang="de"):
    """PAGE mit Nav + Sprache fuellen."""
    return PAGE.format(NAV=render_nav(lang), HTML_LANG=lang, RESULT=body_html)


def redirect(path, cookie_lang=None):
    hdrs = [("Location", path)]
    if cookie_lang:
        hdrs.append(("Set-Cookie", f"lang={cookie_lang}; Path=/"))
    return hdrs


def render_meine_devis(lang):
    def L(k):
        return _t(k, lang)
    items = history_mod.list_all()
    if not items:
        body = (f"<div class='card'><h2>{L('historie_titel')}</h2>"
                f"<p class='meta'>{L('historie_info')}</p>"
                f"<div class='warn'>{L('keine_devis')}</div>"
                f"<a class='btn' href='/bepreisen'>{L('neues_devis')}</a></div>")
        return render_page(body, lang)
    rows = []
    for m in items:
        did = m["id"]
        status = m.get("status", "offen")
        status_txt = L("freigegeben") if status == "freigegeben" else L("offen")
        rows.append(
            "<tr>"
            f"<td>{html.escape(m.get('datum',''))}</td>"
            f"<td>{html.escape(str(m.get('name','')))}</td>"
            f"<td style='text-align:right'>{m.get('netto',0):,.2f} CHF</td>"
            f"<td>{html.escape(m.get('kanton',''))}</td>"
            f"<td class='{'ok' if status=='freigegeben' else 'rev'}'>{status_txt}</td>"
            f"<td><a class='btn-sm' href='/devis_view?id={did}'>{L('ansehen')}</a> "
            f"<a class='btn-sm alt' href='/devis_offerte?id={did}'>{L('offerte')}</a> "
            f"<a class='btn-sm' href='/devis_download?id={did}'>⬇</a> "
            f"<form method='post' action='/devis_freigeben' style='display:inline'>"
            f"<input type='hidden' name='id' value='{did}'>"
            f"<button type='submit' class='btn-sm' style='background:#15803d' "
            f"title='{L('freigegeben')}'>✓</button></form> "
            f"<form method='post' action='/devis_delete' style='display:inline'>"
            f"<input type='hidden' name='id' value='{did}'>"
            f"<button type='submit' class='btn-sm' style='background:#b91c1c' "
            f"onclick=\"return confirm('{L('loeschen')}?')\" title='{L('loeschen')}'>🗑</button></form></td>"
            "</tr>"
        )
    body = (f"<div class='card'><h2>{L('historie_titel')}</h2>"
            f"<p class='meta'>{L('historie_info')}</p>"
            f"<h3 style='margin-top:1rem'>{L('devis_import_titel')}</h3>"
            f"<p class='meta'>{L('devis_import_info')}</p>"
            f"<form method='post' action='/import_devis' enctype='multipart/form-data' "
            f"style='display:flex;flex-wrap:wrap;gap:.5rem;align-items:flex-end'>"
            f"<input type='file' name='file' accept='.sia,.crb,.csv,.txt,.xlsx,.xls,.xml' "
            f"style='max-width:22rem'>"
            f"<button type='submit' class='btn-sm'>{L('import_starten')}</button></form>"
            f"<a class='btn' href='/bepreisen' style='margin-left:.6rem'>{L('neues_devis')}</a>"
            f"<table style='margin-top:1rem'><thead><tr>"
            f"<th>{L('datum')}</th><th>{L('name')}</th><th>{L('betrag')}</th>"
            f"<th>Kanton</th><th>{L('status')}</th><th>Aktion</th></tr></thead>"
            f"<tbody>{''.join(rows)}</tbody></table></div>")
    return render_page(body, lang)


def render_devis_view(did, lang):
    def L(k):
        return _t(k, lang)
    m = None
    for x in history_mod.list_all():
        if x["id"] == did:
            m = x
            break
    if not m:
        return render_page("<div class='blocker'>✗ Devis nicht gefunden.</div>", lang)
    devis = crb.parse(history_mod.path_of(did, "bepreist.sia"))
    rows = []
    for p in devis.positions:
        bet = f"{p.betrag:,.2f}" if p.betrag is not None else "–"
        ep = f"{p.ep:,.2f}" if p.ep is not None else "0.00"
        # Benchmark-Vergleich (anonym, Netzwerkeffekt, kanton-spezifisch)
        bm = bench_mod.benchmark(
            kategorie=(p.matched_artikel or (p.text[:20] if p.matched_artikel else None)),
            einheit=p.einheit, ep=(p.ep or 0), kanton=m.get("kanton"))
        if bm["urteil"] == "tief":
            bm_html = f"<span class='bm low' title='Markt-Durchschnitt {bm['avg']} CHF (n={bm['n']})'>▼ {bm['delta_pct']}%</span>"
        elif bm["urteil"] == "hoch":
            bm_html = f"<span class='bm high' title='Markt-Durchschnitt {bm['avg']} CHF (n={bm['n']})'>▲ {bm['delta_pct']}%</span>"
        elif bm["urteil"] == "ok":
            bm_html = f"<span class='bm ok' title='Markt-Durchschnitt {bm['avg']} CHF (n={bm['n']})'>● Markt</span>"
        else:
            bm_html = "<span class='bm' title='Noch keine Marktdaten'>–</span>"
        rows.append(
            f"<tr><td><code>{html.escape(str(p.pos_nr))}</code></td>"
            f"<td>{html.escape(str(p.text))}</td>"
            f"<td style='text-align:right'>{ep}</td>"
            f"<td>{html.escape(str(p.menge))} {html.escape(str(p.einheit))}</td>"
            f"<td style='text-align:right'>{bet}</td>"
            f"<td class='{'ok' if not p.requires_review else 'rev'}'>"
            f"{'✓' if not p.requires_review else '!'}</td>"
            f"<td style='text-align:center'>{bm_html}</td>"
        )
    # Margen-Copilot: Plausibilitaetspruefung
    warns = plausib_mod.check_positions(devis.positions)
    summ = plausib_mod.summarize(warns)
    if summ["ok"]:
        warn_box = f"<div class='save' style='margin-top:1rem'>✓ Margen-Copilot: keine Auffaelligkeiten ({summ['label']}).</div>"
    else:
        items = "".join(
            f"<li class='w-{w['severity']}'><b>Pos {html.escape(str(w['pos_nr']))}:</b> "
            f"{html.escape(w['msg'])}</li>" for w in warns)
        warn_box = (f"<div class='warn-box' style='margin-top:1rem'>"
                    f"<b>⚠ Margen-Copilot – {summ['label']}</b>"
                    f"<ul class='warn-list'>{items}</ul></div>")
    # Margen-Copilot: Markt-Beratung (Benchmark-Moat, kanton-spezifisch)
    try:
        br = bench_mod.berate(devis.positions, kanton=m.get("kanton"))
        def _row(r):
            d = r["delta_pct"]
            return (f"<li><b>Pos {html.escape(str(r['pos_nr']))}:</b> "
                    f"{html.escape(str(r['text'])[:60])} "
                    f"<span class='bm {'low' if d < 0 else 'high'}'>{'▼' if d < 0 else '▲'} {abs(d)}%</span> "
                    f"(Markt {r['avg']} CHF)</li>")
        if br["bewertet"] == 0:
            markt_box = ""
        else:
            u = "".join(_row(r) for r in br["top_unter"]) or "<li class='ok'>– keine</li>"
            o = "".join(_row(r) for r in br["top_ueber"]) or "<li class='ok'>– keine</li>"
            markt_box = (
                f"<div class='warn-box' style='margin-top:1rem; border-color:#2e7d32'>"
                f"<b>📊 Margen-Copilot – Markt-Benchmark ({html.escape(str(br['kanton']))})</b><br>"
                f"<span class='bm low'>▼ {len(br['unter_markt'])} Pos. unter Markt</span> "
                f"→ Marge-Risiko ~<b>{br['margen_risiko_chf']:,.0f} CHF</b> &nbsp; "
                f"<span class='bm high'>▲ {len(br['ueber_markt'])} Pos. ueber Markt</span> "
                f"→ Auftrags-Risiko ~<b>{br['auftrags_risiko_chf']:,.0f} CHF</b>"
                f"<details style='margin-top:.5rem'><summary>Top-Positionen</summary>"
                f"<p class='meta'>Zu guenstig (Marge verschenkt):</p><ul class='warn-list'>{u}</ul>"
                f"<p class='meta'>Zu teuer (Zuschlag gefaehrdet):</p><ul class='warn-list'>{o}</ul></details>"
                f"</div>")
    except Exception:
        markt_box = ""
    warn_box = warn_box + markt_box
    total = sum((p.betrag or 0.0) for p in devis.positions)
    body = (f"<div class='card'><h2>{L('historie_titel')} – {html.escape(str(m.get('name','')))}</h2>"
            f"<p class='meta'>{L('datum')}: {html.escape(m.get('datum',''))} · "
            f"Kanton: {html.escape(m.get('kanton',''))} · "
            f"{L('gesamt')}: <b>{total:,.2f} CHF</b></p>"
            f"<a class='btn-sm' href='/devis_offerte?id={did}'>{L('offerte')} / PDF</a> "
            f"<a class='btn-sm alt' href='/devis_download?id={did}'>⬇ Sorba</a> "
            f"<a class='btn-sm' href='/devis_connector?id={did}&ziel=abacus'>⇩ Abacus</a> "
            f"<a class='btn-sm' href='/devis_connector?id={did}&ziel=proffix'>⇩ Proffix</a> "
            f"<a class='btn-sm alt' href='/devis_mahnung?id={did}&stufe=1'>⚠ Mahnung</a> "
            f"<a class='btn-sm alt' href='/devis_lifecycle?id={did}'>🔄 Lebenszyklus</a> "
            f"<a class='btn-sm alt' href='/devis_vorlage_form?id={did}'>📋 Als Vorlage</a> "
            f"<a class='btn-sm' href='/meine_devis'>← {L('meine_devis')}</a>"
            f"<h3 style='margin-top:1.4rem'>{L('dokumente')}</h3>"
            f"<form method='get' action='/devis_doc' style='display:flex;flex-wrap:wrap;gap:.5rem;align-items:flex-end'>"
            f"<input type='hidden' name='id' value='{did}'>"
            f"<label style='font-size:.8rem'>{L('werkvertrag')}<br>"
            f"<button class='btn-sm' type='submit' name='typ' value='werkvertrag'>{L('dok_erstellen')}</button></label>"
            f"<label style='font-size:.8rem'>{L('devis_muster')}<br>"
            f"<button class='btn-sm' type='submit' name='typ' value='devis_muster'>{L('dok_erstellen')}</button></label>"
            f"<label style='font-size:.8rem'>{L('abnahme')}<br>"
            f"<button class='btn-sm' type='submit' name='typ' value='abnahme'>{L('dok_erstellen')}</button></label>"
            f"<label style='font-size:.8rem'>{L('bindend_bis')}<br>"
            f"<input type='date' name='bindend_bis' style='padding:.25rem'></label>"
            f"<label style='font-size:.8rem'>{L('maengel')}<br>"
            f"<textarea name='maengel' rows='1' placeholder='…' style='width:14rem;padding:.25rem'></textarea></label>"
            f"<label style='font-size:.8rem'>{L('bedingt')}<br>"
            f"<input type='checkbox' name='bedingt' value='1'></label>"
            f"</form>"
            f"<h3 style='margin-top:1.4rem'>{L('rechnung')}</h3>"
            f"<form method='get' action='/devis_rechnung' style='display:flex;flex-wrap:wrap;gap:.5rem;align-items:flex-end'>"
            f"<input type='hidden' name='id' value='{did}'>"
            f"<label style='font-size:.8rem'>{L('rabatt')}<br><input type='number' step='0.1' name='rabatt_pct' value='0' style='width:5rem;padding:.25rem'></label>"
            f"<label style='font-size:.8rem'>{L('skonto')}<br><input type='number' step='0.1' name='skonto_pct' value='0' style='width:5rem;padding:.25rem'></label>"
            f"<label style='font-size:.8rem'>{L('skonto_bis')}<br><input type='date' name='skonto_bis' style='padding:.25rem'></label>"
            f"<button class='btn-sm' type='submit'>{L('rechnung_erstellen')}</button></form>"
            f"<p style='margin-top:.6rem'><a class='btn-sm' href='/qr_rechnung?id={did}'>⚡ Swiss QR-Rechnung</a></p>"
            f"<h3 style='margin-top:1.4rem'>{L('gespeicherte_docs')}</h3>"
            f"{_render_saved_docs(did, lang)}"
            f"<table style='margin-top:1rem'><thead><tr><th>Pos</th><th>Artikel</th>"
            f"<th>EP CHF</th><th>Menge</th><th>Betrag</th><th>✓</th><th>Markt</th></tr></thead>"
            f"<tbody>{''.join(rows)}</tbody></table>"
            f"{warn_box}"
            f"</div>")
    return render_page(body, lang)


def _render_devis_check(self, lang="de"):
    from devispro import lead_magnet as lead_mod
    q = dict(x.split("=", 1) for x in (self.path.split("?", 1)[-1].split("&") if "?" in self.path else []))
    res = None
    if q.get("r") == "1" and q.get("f"):
        try:
            import json as _json
            res = _json.load(open(os.path.join(DATA, os.path.basename(q["f"])), encoding="utf-8"))
        except Exception:
            res = None
    return lead_mod.render_result(res, lang) if res else lead_mod.render_form(lang)


def _render_saved_docs(did, lang):
    docs = history_mod.list_docs(did)
    if not docs:
        return "<p class='meta'>Noch keine Dokumente erzeugt.</p>"
    items = ""
    for typ, _ in docs:
        label = typ.replace("doc_", "")
        items += (f"<li><a class='btn-sm' href='/devis_doc_file?id={did}&amp;typ={typ}'>"
                  f"{_t(label, lang) if _t(label, lang) != label else label}</a></li>")
    return f"<ul style='list-style:none;padding:0;display:flex;flex-wrap:wrap;gap:.5rem'>{items}</ul>"


def render_index(self=None, lang=None):
    if lang is None:
        lang = lang_from_request(self) if self is not None else "de"
    preise_ok = stammdaten.prices_exist()
    profil = stammdaten.load_profile()
    hint = "" if preise_ok else (
        "<div class='warn'>⚠ Noch keine Richtpreisliste gespeichert. "
        "Gehe zu <a href='/profil'>Stammdaten</a> und gib einmalig deine Preise ein – "
        "danach brauchst du sie bei jedem neuen Devis nicht mehr.</div>")
    body = f"""
 <p class="meta">Betrieb: <b>{html.escape(profil.get('betrieb','–'))}</b> · Gewerk: {html.escape(profil.get('gewerk','–'))}
 · Stundenlohn: {profiler_or(profil)} CHF/h</p>
 {hint}
 <div class="card">
  <form method="post" enctype="multipart/form-data" action="/import_devis">
   <label>Devis-Datei (alle Formate)</label>
   <input type="file" name="file" accept=".sia,.crb,.txt,.csv,.xlsx,.xml" required>
   <p class="meta">Unterstützte Formate: <b>SIA-451/Sorba</b> (.sia), <b>Bauweb/Daedalus</b> (.csv),
   <b>generisches CSV/Excel</b> (.csv/.xlsx), <b>GAEB D84</b> (DE, .xml), <b>ÖNORM B 2063</b> (AT, .csv),
   <b>XRechnung</b> (EU, .xml). Das Format wird automatisch erkannt.</p>
   <button type="submit">Importieren &amp; automatisch bepreisen</button>
   </form>
   <p class="meta">Richtpreisliste wird automatisch aus deinen gespeicherten Stammdaten verwendet.
   Pro Devis wird eine <b>Swiss QR-Rechnung</b> erzeugt.</p>
   </div>
   <div class="card">
   <form method="post" enctype="multipart/form-data" action="/import_foto">
    <label>📷 Oder: Devis abfotografieren</label>
    <input type="file" name="foto" accept="image/*" required>
    <p class="meta">Foto eines Devis hochladen – devispro extrahiert die Positionen (OCR) oder
    zeigt ein geführtes Formular zur Bestätigung. Kein Tippen nötig.</p>
    <button type="submit">Aus Foto importieren</button>
   </form>
   </div>
   <div class="card" style="background:#f0fdf4;border:1px solid #bbf7d0">
    <h3 style="margin:0 0 .4rem;color:#14532d">🚀 Das macht devispro zum Verkaufshit</h3>
    <ul style="margin:.3rem 0 0 1.1rem;padding:0;line-height:1.6">
      <li><b>Margen-Copilot:</b> devispro warnt bei jedem Devis vor EP=0, Verlust, Dublette und unplausibler Menge.</li>
      <li><b>Marktpreis-Benchmark:</b> anonyme Vergleichspreise pro Position – sehen Sie sofort, wo Ihre Kalkulation unter Markt liegt.</li>
      <li><b>Gratis Devis-Check:</b> Kunden prüfen ein Devis in 30 Sek. anonym, ohne Login – und testen 3 Monate gratis.</li>
      <li><b>Alle Formate:</b> SIA-451/Sorba, Bauweb, CSV/Excel, GAEB (DE), ÖNORM (AT), XRechnung (EU) + Swiss QR-Rechnung.</li>
    </ul>
    <p style="margin:.6rem 0 0"><a class="btn-sm" href="/check">🔍 Jetzt gratis Devis-Check starten</a></p>
   <div class="card">
   <form method="post" enctype="multipart/form-data" action="/portal_import">
    <label>📡 Oder: Heruntergeladene Ausschreibung (Simap/Olmero/Devisio)</label>
    <input type="file" name="file" accept=".sia,.crb,.txt,.csv,.xlsx,.xml,.pdf" required>
    <input type="text" name="stichwort" placeholder="Projektname (optional)" style="margin-top:.5rem">
    <p class="meta">Laden Sie die vom Portal heruntergeladene Ausschreibungs-Datei hoch – devispro
    importiert, bepreist und speist anonym den Marktpreis-Benchmark (Netzwerkeffekt).</p>
    <button type="submit">Aus Portal importieren &amp; bepreisen</button>
   </form>
   <div class="card">
   <form method="post" enctype="multipart/form-data" action="/learn_prices">
    <label>🧠 Oder: Preise automatisch lernen (Zero-Typing-Onboarding)</label>
    <input type="file" name="file" accept=".sia,.crb,.txt,.csv,.xlsx,.xml,.pdf" required>
    <p class="meta">Laden Sie einfach <b>3 Ihrer echten, bereits bepreisten Devis</b> hoch (nacheinander). DevisPro
    extrahiert Ihre Einheitspreise und baut die Stammdaten automatisch – kein einziges Feld tippen.</p>
    <button type="submit">Preise lernen &amp; Stammdaten füllen</button>
   </form>
   </div>
   """
    if preise_ok:
        body += "<div class='save'>✓ Deine Richtpreisliste ist gespeichert und wird für jedes neue Devis automatisch verwendet.</div>"
    return render_page(body, lang)


def profiler_or(profil):
    return profil.get("stundenlohn_chf", "–")


KANTON_CHOICES = [(k, v[1]) for k, v in kant_mod.KANTONE.items()]


def render_preis_tabelle() -> str:
    """Editierbare Uebersicht der gespeicherten Richtpreise.
    Jede Zeile hat editierbare Felder (EP/Kategorie) + Speichern/Loeschen."""
    csv_text = stammdaten.load_prices_csv()
    if not csv_text.strip():
        return "<p class='meta'>Noch keine Richtpreise gespeichert. Lade oben eine CSV/Excel hoch.</p>"
    try:
        from devispro import pricelist as pl_mod
        items = pl_mod.load(os.path.join(DATA, "meine_preise.csv"))
    except Exception:
        return "<p class='meta'>Richtpreisliste vorhanden, aber nicht lesbar.</p>"
    if not items:
        return "<p class='meta'>Richtpreisliste ist leer.</p>"
    rows = []
    for idx, it in enumerate(items):
        ep_disp = f"{it.ep_chf:.2f}"
        rows.append(
            "<tr>"
            f"<td><code>{html.escape(it.artikel_id)}</code></td>"
            f"<td>{html.escape(it.bezeichnung)}</td>"
            f"<td>{html.escape(it.npk)}</td>"
            f"<td>{html.escape(it.einheit)}</td>"
            f"<td><form method='post' action='/preise_edit' style='display:inline'>"
            f"<input type='hidden' name='idx' value='{idx}'>"
            f"<input type='number' step='0.01' name='ep' value='{ep_disp}' style='width:90px'></form></td>"
            f"<td><form method='post' action='/preise_edit' style='display:inline'>"
            f"<input type='hidden' name='idx' value='{idx}'>"
            f"<input type='text' name='kategorie' value='{html.escape(it.kategorie)}' style='width:90px'></form></td>"
            f"<td><form method='post' action='/preise_edit' style='display:inline'>"
            f"<input type='hidden' name='idx' value='{idx}'>"
            f"<button type='submit' title='diese Zeile speichern'>✓</button></form>"
            f"<form method='post' action='/preise_del' style='display:inline'>"
            f"<input type='hidden' name='idx' value='{idx}'>"
            f"<button type='submit' title='Zeile loeschen' onclick=\"return confirm('Zeile loeschen?')\">🗑</button></form></td>"
            "</tr>"
        )
    return (
        "<p class='meta'>Unter <b>EP</b> und <b>Kategorie</b> direkt aendern, dann "
        "✓ klicken – nur diese Zeile wird gespeichert. 🗑 entfernt die Zeile.</p>"
        "<table><thead><tr><th>Artikel</th><th>Bezeichnung</th><th>NPK</th>"
        "<th>Einheit</th><th>EP CHF</th><th>Kategorie</th><th>Aktion</th></tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table>"
    )


def render_profil(lang="de"):
    profil = stammdaten.load_profile()
    kanton_opts = "".join(
        f'<option value="{k}"{" selected" if profil.get("kanton", "ZH") == k else ""}>{k} – {lbl}</option>'
        for k, lbl in KANTON_CHOICES)
    preise = stammdaten.load_prices_csv()
    body = f"""
 <div class="card">
  <h2>1 · Betrieb &amp; Kalkulationssätze (einmal eingeben)</h2>
  <form method="post" action="/profil_save">
   <div class="grid">
    <div><label>Betrieb</label><input type="text" name="betrieb" value="{html.escape(str(profil.get('betrieb','')))}"></div>
    <div><label>Gewerk</label><input type="text" name="gewerk" value="{html.escape(str(profil.get('gewerk','')))}"></div>
    <div><label>Kanton</label><select name="kanton" data-kver="2">{kanton_opts}</select></div>
    <div><label>Stundenlohn CHF/h</label><input type="number" step="0.5" name="stundenlohn_chf" value="{profil.get('stundenlohn_chf',82)}"></div>
    <div><label>Material-Aufschlag %</label><input type="number" step="0.5" name="material_aufschlag_pct" value="{profil.get('material_aufschlag_pct',12)}"></div>
    <div><label>Gemeinkosten %</label><input type="number" step="0.5" name="gemeinkosten_pct" value="{profil.get('gemeinkosten_pct',10)}"></div>
    <div><label>Gewinn %</label><input type="number" step="0.5" name="gewinn_pct" value="{profil.get('gewinn_pct',8)}"></div>
    <div><label>MwSt %</label><input type="number" step="0.1" name="mwst_pct" value="{profil.get('mwst_pct',8.1)}"></div>
    <div><label>IBAN (für QR-Rechnung)</label><input type="text" name="iban" value="{html.escape(str(profil.get('iban','')))}" placeholder="CH..."></div>
    <div><label>Strasse</label><input type="text" name="strasse" value="{html.escape(str(profil.get('strasse','')))}"></div>
    <div><label>PLZ / Ort</label><input type="text" name="plz_ort" value="{html.escape(str(profil.get('plz_ort','')))}"></div>
   </div>
   <button type="submit">Betriebsdaten speichern</button>
  </form>
 </div>
 <div class="card">
  <h2>2 · Richtpreisliste (einmal eingeben, bleibt gespeichert)</h2>
  <p class="meta">Format (kommagetrennt, mit oder ohne Kopfzeile): <code>artikel_id,bezeichnung,npk,einheit,ep_chf,kategorie</code>
  – die Spalten <code>npk</code> und <code>kategorie</code> sind optional, <code>ep_chf</code> ist der Einheitspreis. Eine Zeile pro Artikel.</p>
  <form method="post" action="/preise_save" enctype="multipart/form-data">
   <textarea name="paste" rows="10" style="width:100%;font-family:monospace">{{PREISE}}</textarea>
   <p class="meta">…oder Datei hochladen:</p>
   <input type="file" name="prices" accept=".csv,.xlsx">
   <button type="submit">Richtpreisliste speichern</button>
  </form>
 </div>
 <div class="card">
  <h2>2b · Gespeicherte Richtpreise kontrollieren &amp; anpassen</h2>
  {{PREISTABELLE}}
 </div>
 <div class="save">✓ Alles, was du hier speicherst, bleibt in <code>data/</code> und wird für jedes neue Devis automatisch verwendet – kein erneutes Eintippen.</div>
 <div class="card">
  <h2>3 · Lizenzierte NPK-Daten importieren (optional)</h2>
  <p class="meta">DevisPro nutzt SIA-451 + deine Richtpreise. Für volle NPK-Positionen (Artikelnummern + Texte)
  importierst du deine eigene, lizenzierte NPK-Liste (CSV: <code>npk,text,einheit,preis_chf</code>).
  DevisPro ordnet sie automatisch den Gewerken zu und gewichtet nach Kanton.</p>
  <form method="post" action="/npk_import" enctype="multipart/form-data">
   <input type="file" name="npkfile" accept=".csv">
   <button type="submit">NPK-Liste importieren</button>
  </form>
 </div>
"""
    body = body.replace("{PREISE}", html.escape(preise))
    body = body.replace("{PREISTABELLE}", render_preis_tabelle())
    return render_page(body, lang)


def render_roi(lang="de"):
    profil = stammdaten.load_profile()
    r = roi_mod.calculate_from_profile(profil)
    cf = r["cashflow"]
    be = r["break_even_monat"] or 12
    be_text = f"Monat {be}" if be <= 12 else "> 12 Monate"
    body = f"""
 <div class="card">
  <h2>ROI-Kalkulator – was die App dir spart</h2>
  <p class="meta">Basierend auf deinem Stundenlohn von {r['stundenlohn']:.0f} CHF/h und typischen KMU-Werten.
  Werte unten anpassbar.</p>
  <form method="post" action="/roi">
   <div class="grid">
    <div><label>Aufwand von Hand (h/Devis)</label><input type="number" step="0.1" name="zeit_manuell_h" value="2.0"></div>
    <div><label>Aufwand mit App (h/Devis)</label><input type="number" step="0.1" name="zeit_app_h" value="0.2"></div>
    <div><label>Devis pro Monat</label><input type="number" step="1" name="devis_pro_monat" value="20"></div>
    <div><label>Fehler-Ersparnis (CHF/Devis)</label><input type="number" step="5" name="fehler_ersparnis_chf" value="40"></div>
    <div><label>App-Anschaffung CHF</label><input type="number" step="100" name="app_preis" value="2400"></div>
    <div><label>Jahresgebühr CHF</label><input type="number" step="50" name="app_jahr" value="900"></div>
   </div>
   <button type="submit">Berechnen</button>
  </form>
 </div>
 <div class="kpi">
  <div><div class="v">{r['zeit_erspart_pro_devis']:.1f} h</div><div class="l">gespart pro Devis</div></div>
  <div><div class="v">{r['monat_ersparnis']:,.0f}</div><div class="l">CHF gespart / Monat</div></div>
  <div><div class="v">{r['jahr_ersparnis']:,.0f}</div><div class="l">CHF gespart / Jahr</div></div>
 </div>
 <div class="kpi">
  <div><div class="v">{be_text}</div><div class="l">Break-even (App bezahlt)</div></div>
  <div><div class="v">{r['roi_jahr1']:,.0f}</div><div class="l">Netto-Gewinn nach 12 Mon.</div></div>
  <div><div class="v">{r['roi_pct']:.0f}%</div><div class="l">ROI Jahr 1</div></div>
 </div>
 <p class="meta">Zeit gespart im Jahr: <b>{r['zeit_erspart_jahr_h']:.0f} Stunden</b>
 (= {(r['zeit_erspart_jahr_h']/8):.0f} Arbeitstage à 8h).</p>
 <svg class="chart" viewBox="0 0 600 220" preserveAspectRatio="none">
  {chart_svg(cf)}
 </svg>
 <p class="meta">Kumulierter Cashflow (Ersparnis abzüglich App-Kosten) über 12 Monate, in CHF.</p>
"""
    return render_page(body, lang)


def chart_svg(cf):
    w, h = 600, 220
    n = len(cf)
    maxv = max(max(cf), 1)
    minv = min(min(cf), 0)
    span = maxv - minv or 1
    pts = []
    for i, v in enumerate(cf):
        x = 30 + (550 * i / max(n - 1, 1))
        y = h - 20 - ((v - minv) / span) * (h - 40)
        pts.append((x, y))
    line = " ".join(f"{x:.0f},{y:.0f}" for x, y in pts)
    zero_y = h - 20 - ((0 - minv) / span) * (h - 40)
    dots = "".join(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="3" fill="#1d4ed8"/>' for x, y in pts)
    return (f'<line x1="30" y1="{zero_y:.0f}" x2="580" y2="{zero_y:.0f}" stroke="#bbb"/>'
            f'<polyline points="{line}" fill="none" stroke="#1d4ed8" stroke-width="2.5"/>{dots}')


def render_result(rows, total, currency, review, count, file, review_positions, devis_id=None, lang="de"):
    warn = ("<div class='warn'>⚠ <b>Hinweis zur Verlässlichkeit:</b> Diese Bepreisung basiert auf der "
            "hochgeladenen Richtpreisliste. Sie ist nur so verlässlich wie diese Liste selbst. "
            "Die Preise sind ein Vorschlag zur Vorabprüfung – <b>keine</b> rechtsverbindliche Kalkulation. "
            "Vor Offertabgabe muss eine berechtigte Fachkraft (Human-in-the-Loop) gegenrechnen.</div>")
    if review > 0:
        rev_list = "".join(
            f"<li><code>{html.escape(p['pos_nr'])}</code> {html.escape(str(p['text']))} "
            f"(Conf {p['conf']:.2f}) – <b>kein eindeutiger Treffer</b></li>"
            for p in review_positions)
        block = (f"<div class='blocker'>🔒 <b>Download gesperrt:</b> {review} Position(en) mit unsicherem "
                 f"Match müssen zuerst manuell bepreist werden.<ul>{rev_list}</ul>"
                 f"<p>Erst nach manueller Korrektur (oder bewusster Freigabe) darf die Datei für Sorba exportiert werden.</p>"
                 f"<form method='post' action='/override'><button type='submit' name='file' value='{file}'>"
                 f"Trotz offener Review-Positionen exportieren (Fachkraft bestätigt)</button></form></div>")
        dl = ""
    else:
        block = "<div class='okbox'>✓ Alle Positionen eindeutig zugeordnet (Conf ≥ Schwelle). " \
                "Vor Abgabe dennoch Fachkraft-Freigabe einholen.</div>"
        dl = f"<a class=\"btn\" href=\"/download?f={file}\">⬇ Sorba-Datei herunterladen ({file})</a>"
    saved_note = ""
    if devis_id:
        saved_note = (f"<div class='save'>✓ Dieses Devis wurde im Verlauf gespeichert "
                      f"(<code>{html.escape(devis_id)}</code>). Du findest es unter "
                      f"<a href='/meine_devis'>📁 Meine Devis</a> – auch später wieder ansehbar.</div>")
    body = f"""<div class="card">
 {warn}
 <p><b>Ergebnis:</b> {count} Positionen · Gesamtbetrag (Netto) <b>{total:,.2f} {currency}</b> ·
    Manuelle Prüfung nötig: <span class="{'rev' if review>0 else 'ok'}">{review}</span></p>
 {block}
 {dl}
 {saved_note}
 <table><thead><tr><th>Pos</th><th>Artikel</th><th>EP CHF</th><th>Menge</th><th>Betrag</th><th>Conf</th><th>Review</th></tr></thead><tbody>"""
    for p in rows:
        ep = f"{p['ep']:,.2f}" if p["ep"] is not None else "0.00"
        bet = f"{p['betrag']:,.2f}" if p["betrag"] is not None else "–"
        conf = f"{p['conf']:,.2f}" if p["conf"] is not None else "–"
        flag = "rev" if p["review"] else "ok"
        mark = "!" if p["review"] else "ok"
        art = html.escape(str(p["artikel"] or "–"))
        body += (f"<tr><td><code>{html.escape(p['pos_nr'])}</code></td>"
                 f"<td>{art}</td>"
                 f"<td><form method='post' action='/edit_position' style='display:inline'>"
                 f"<input type='hidden' name='pos_nr' value='{html.escape(p['pos_nr'])}'>"
                 f"<input type='number' step='0.01' name='ep' value='{ep}' style='width:90px'>"
                 f"<button type='submit' title='EP speichern'>✓</button></form></td>"
                 f"<td style='white-space:nowrap'>{p['menge']:,.2f} {html.escape(p['einheit'])} "
                 f"<form method='post' action='/edit_menge' style='display:inline'>"
                 f"<input type='hidden' name='pos_nr' value='{html.escape(p['pos_nr'])}'>"
                 f"<input type='number' step='0.01' name='menge' value='{p['menge']:.2f}' style='width:90px'>"
                 f"<button type='submit' title='Menge speichern'>✓</button></form></td>"
                 f"<td>{bet}</td><td>{conf}</td><td class='{flag}'>{mark}</td></tr>")
    body += "</tbody></table></div>"
    # --- Zusatzpositionen (Fachbetrieb ergaenzt VOR-ORT-Erkenntnisse) ---
    try:
        from devispro import extras as ex
        gewerk = (stammdaten.load_profile() or {}).get("gewerk", "") or "GU"
        sugg = ex.vorschlaege_fuer(gewerk)
        opt_rows = "".join(
            f"<tr><td><input type='checkbox' name='ex_id' value='{html.escape(s['id'])}'></td>"
            f"<td><input type='hidden' name='ex_bez_{html.escape(s['id'])}' value='{html.escape(s['bezeichnung'])}'>"
            f"<input type='hidden' name='ex_eh_{html.escape(s['id'])}' value='{html.escape(s['einheit'])}'>"
            f"{html.escape(s['bezeichnung'])}</td>"
            f"<td>{html.escape(s['einheit'])}</td>"
            f"<td><input type='number' step='0.01' name='ex_ep_{html.escape(s['id'])}' value='{s['ep_chf'] if s['ep_chf'] else ''}' "
            f"placeholder='Preis CHF' style='width:110px'>{' (selbst setzen)' if not s['ep_chf'] else ''}</td>"
            f"<td><input type='number' step='0.01' name='ex_mg_{html.escape(s['id'])}' value='1' style='width:80px'></td></tr>"
            for s in sugg)
        extras_block = f"""
 <div class="card" style="margin-top:1.5rem">
  <h2>Zusätzliche Positionen ergänzen <span class="meta">(Vor-Ort erkannt – Mensch entscheidet)</span></h2>
  <p class="warn">⚠ Der Devis-Entwurf deckt nur die <b>geplanten</b> Arbeiten. Was erst vor Ort
  klar wird (Untergrund ausgleichen, spachteln, aufstemmen, entsorgen …) müssen Sie hier
  ergänzen – sonst rechnen Sie sich arm.</p>
  <form method="post" action="/process_extras">
   <input type="hidden" name="basis_total" value="{total:.2f}">
   <table><thead><tr><th>✓</th><th>Vorgeschlagene Zusatzposition ({html.escape(gewerk)})</th>
   <th>Einheit</th><th>EP CHF</th><th>Menge</th></tr></thead>
   <tbody>{opt_rows}</tbody></table>
   <h3 style="font-size:1rem;margin-top:1rem">Eigene Position frei ergänzen</h3>
   <input type="text" name="own_bez" placeholder="Bezeichnung (z.B. Spezialanstrich)" style="width:280px">
   <input type="text" name="own_eh" placeholder="Einheit" style="width:90px">
   <input type="number" step="0.01" name="own_ep" placeholder="EP CHF" style="width:100px">
   <input type="number" step="0.01" name="own_mg" placeholder="Menge" value="1" style="width:80px">
   <button type="submit">Zusatzpositionen übernehmen &amp; Gesamtofferte berechnen</button>
  </form>
 </div>"""
    except Exception:
        extras_block = ""
    body += extras_block
    return render_page(body, lang)


def _recompute_and_render(devis_path, edit_pos_nr=None, ep=None, menge=None):
    """Aendert eine Position in der hochgeladenen SIA (inline edit), markiert sie als
    manuell geprueft (Conf 1.0, review=False) und rendert das Ergebnis neu.
    Bereits manuell gepruefte Positionen (samt editierter Werte) bleiben erhalten
    (persistent via _reviewed.json + bepreist.sia)."""
    from devispro.parsers import crb
    from devispro.pricelist import load as load_prices
    from devispro.matcher import Matcher
    reviewed_path = os.path.join(DATA, "_reviewed.json")
    reviewed = set()
    if os.path.exists(reviewed_path):
        try:
            reviewed = set(json.load(open(reviewed_path)))
        except Exception:
            reviewed = set()
    if edit_pos_nr:
        reviewed.add(edit_pos_nr)
        json.dump(sorted(reviewed), open(reviewed_path, "w"))
    # Basis-SIA: bepreist.sia (bereits editierte Werte) falls vorhanden, sonst Original
    edited_path = os.path.join(DATA, "bepreist.sia")
    base_path = edited_path if (os.path.exists(edited_path) and edit_pos_nr) else devis_path
    devis = crb.parse(base_path)
    preise_csv = stammdaten.load_prices_csv() or ""
    prices_path = os.path.join(DATA, "_meine_preise.csv")
    with open(prices_path, "w", encoding="utf-8") as f:
        f.write(preise_csv)
    prices = load_prices(prices_path)
    matcher = Matcher(method="mock", threshold=0.6)
    profil = stammdaten.load_profile() or {}
    kf = float(profil.get("kanton_faktor", 1.0) or 1.0)
    rows = []; review = 0; review_positions = []
    for p in devis.positions:
        if p.pos_nr == edit_pos_nr and (ep is not None or menge is not None):
            if menge is not None:
                p.menge = float(menge)
            if ep is not None:
                p.ep = float(ep)
            else:
                p.ep = (p.ep or 0.0) * kf  # falls nur menge editiert: kanton anwenden
            p.requires_review = False
            p.confidence = 1.0
            p.matched_artikel = p.matched_artikel or "manuell"
            p.begruendung = "Manuell vom Fachbetrieb korrigiert"
            p.fill()
        elif p.pos_nr in reviewed:
            # bereits manuell geprueft: editierte Werte aus SIA behalten, kanton anwenden
            p.ep = (p.ep or 0.0) * kf
            p.requires_review = False
            p.confidence = 1.0
            p.fill()
        else:
            r = matcher.match(p, prices)
            p.ep = (r.einheitspreis_chf or 0.0) * kf
            p.matched_artikel = r.matched_artikel_id
            p.confidence = r.confidence
            p.requires_review = r.requires_review
            p.begruendung = r.begruendung
            p.fill()
        if p.requires_review:
            review += 1
            review_positions.append({"pos_nr": p.pos_nr, "text": p.text, "conf": p.confidence})
        rows.append({"pos_nr": p.pos_nr, "artikel": p.matched_artikel, "ep": p.ep,
                     "menge": p.menge, "einheit": p.einheit, "betrag": p.betrag,
                     "conf": p.confidence, "review": p.requires_review})
    out_name = "bepreist.sia"
    crb.export(devis, os.path.join(DATA, out_name))
    total = sum((p.betrag or 0.0) for p in devis.positions)
    return render_result(rows, total, devis.meta.get("currency", "CHF"),
                         review, len(devis.positions), out_name, review_positions)


def render_override(file, lang="de"):
    body = f"""<div class="card">
 <div class='warn'>⚠ Sie haben den Export mit offenen Review-Positionen bewusst freigegeben.
 Die betroffenen Positionen enthalten geschätzte (nicht verifizierte) Preise.</div>
 <a class="btn" href="/download?f={file}">⬇ Sorba-Datei herunterladen ({file})</a>
 <p class="meta">Datei: {file}</p>
</div>"""
    return render_page(body, lang)


def render_lizenz(lang="de"):
    s = liz.status()
    if s["zustand"] == "abgelaufen":
        return render_gesperrt(s)
    z = s["zustand"]
    farbe = {"aktiv": "#15803d", "erinnert": "#b45309", "keine_lizenz": "#b91c1c"}.get(z, "#333")
    info = {
        "aktiv": "Lizenz aktiv.",
        "erinnert": f"Achtung: Lizenz läuft in {s['tage_bis_ablauf']} Tagen ab. "
                    f"Sie erhalten automatisch Rechnung + Code.",
        "keine_lizenz": "Keine Lizenz erkannt. Bitte Freischaltcode eingeben.",
    }[z]
    body = f"""
 <div class="card">
  <h2>Lizenzstatus</h2>
  <p><span style="color:{farbe};font-weight:700">{info}</span></p>
  <p class="meta">Kunde: {html.escape(str(s.get('kunde_id') or '–'))} ·
     Gültig bis: {html.escape(str(s.get('gueltig_bis') or '–'))}</p>
  <form method="post" action="/lizenz_code">
   <label>Freischaltcode eingeben (Jahrescode)</label>
   <input type="text" name="code" placeholder="24-stelliger Code" style="max-width:420px">
   <label style="margin-top:.6rem">Kunde-ID</label>
   <input type="text" name="kunde_id" value="KMU-001" style="max-width:200px">
   <button type="submit">Code anwenden &amp; um 1 Jahr verlängern</button>
  </form>
 </div>
"""
    return render_page(body, lang)


def render_gesperrt(s, lang="de"):
    body = f"""
 <div class="blocker" style="max-width:560px;margin:3rem auto">
  <h2 style="color:#b91c1c">🔒 DevisPro gesperrt</h2>
  <p>Ihre Lizenz ist abgelaufen (seit {html.escape(str(s.get('gueltig_bis') or '–'))}).
  Die Software ist ohne gültigen Jahres-Code nicht nutzbar.</p>
  <p class="meta">Sie erhalten nach Zahlungseingang automatisch den neuen Code per E-Mail.
  Falls Sie ihn schon haben, geben Sie ihn hier ein:</p>
  <form method="post" action="/lizenz_code" style="margin-top:1rem">
   <input type="text" name="code" placeholder="24-stelliger Jahrescode" style="width:100%;padding:.6rem">
   <input type="hidden" name="kunde_id" value="{html.escape(str(s.get('kunde_id') or 'KMU-001'))}">
   <button type="submit" style="margin-top:.8rem">Code anwenden</button>
  </form>
 </div>
"""
    return render_page(body, lang)


def render_trial(lang="de", fehler="", erfolg_bis="", email="", projekt=""):
    from devispro import kantone as kant_mod
    from devispro.extras import gewerke_liste
    kantone_opts = "".join(
        f'<option value="{k}">{k} – {html.escape(kant_mod.label(k))}</option>'
        for k in sorted(kant_mod.KANTONE.keys()))
    gewerk_opts = "".join(
        f'<option value="{html.escape(g)}">{html.escape(g)}</option>'
        for g in gewerke_liste())
    from devispro import pricing as _pz
    def _ff(x): return f"{x:,.0f}".replace(",", "'")
    preis_d_ein, preis_d_jahr = _ff(_pz.preis("devis")["einrichtung"]), _ff(_pz.preis("devis")["lizenz_jahr"])
    preis_e_ein, preis_e_jahr = _ff(_pz.preis("erp")["einrichtung"]), _ff(_pz.preis("erp")["lizenz_jahr"])
    warn = f"<div class='blocker'>{html.escape(fehler)}</div>" if fehler else ""
    erfolg = (f"<div class='okbox'>✓ {_t('trial_erfolg', lang)} "
              f"(<b>{html.escape(erfolg_bis)}</b>)</div>") if erfolg_bis else ""
    prelit = f' value="{html.escape(email)}"' if email else ""
    projpre = f' value="{html.escape(projekt)}"' if projekt else ""
    body = f"""
 <div class="card" style="max-width:560px;margin:2.5rem auto">
  <h2>{_t('trial_titel', lang)}</h2>
  <p class="meta">{_t('trial_info', lang)}</p>
  {warn}{erfolg}
  <form method="post" action="/trial_anmelden" style="margin-top:1rem">
   <label>{_t('trial_firma', lang)} *</label>
   <input type="text" name="firma" required style="width:100%;padding:.6rem">
   <label style="margin-top:.6rem">{_t('trial_name', lang)}</label>
   <input type="text" name="name" style="width:100%;padding:.6rem">
   <label style="margin-top:.6rem">{_t('trial_email', lang)} *</label>
   <input type="email" name="email" required style="width:100%;padding:.6rem"{prelit}>
   <label style="margin-top:.6rem">Projekt / Devis-Name</label>
   <input type="text" name="projekt" style="width:100%;padding:.6rem"{projpre}>
   <label style="margin-top:.6rem">{_t('trial_kanton', lang)}</label>
   <select name="kanton" style="width:100%;padding:.6rem">{kantone_opts}</select>
   <label style="margin-top:.6rem">{_t('trial_gewerk', lang)}</label>
   <select name="gewerk" style="width:100%;padding:.6rem">{gewerk_opts}</select>
   <label style="margin-top:.6rem">Tarif</label>
   <select name="tarif" style="width:100%;padding:.6rem">
     <option value="devis">DevisPro – {preis_d_ein} CHF + {preis_d_jahr} CHF/Jahr</option>
     <option value="erp">DevisPro + ERP – {preis_e_ein} CHF + {preis_e_jahr} CHF/Jahr</option>
   </select>
   <button type="submit" style="margin-top:1rem">{_t('trial_start', lang)}</button>
  </form>
 </div>
"""
    return render_page(body, lang)


def render_admin_login(fehler="", lang="de"):
    warn = f"<div class='blocker'>{html.escape(fehler)}</div>" if fehler else ""
    body = f"""
 <div class="card" style="max-width:420px;margin:3rem auto">
  <h2>Anbieter-Login</h2>
  {warn}
  <form method="post" action="/admin_login">
   <label>Passwort</label>
   <input type="password" name="pw" style="width:100%" autofocus>
   <button type="submit">Einloggen</button>
  </form>
  <p class="meta">Standardpasswort bei Erststart: <code>devispro-admin-2026</code><br>
  Bitte nach dem ersten Login ändern (Passwort-Reset über CLI).</p>
 </div>
"""
    return render_page(body, lang)


def render_admin(lang="de"):
    # Anbieter-Sicht: Kundenliste + Zahlungsbestätigung
    try:
        import json
        with open(os.path.join(DATA, "kunden.json"), encoding="utf-8") as f:
            db = json.load(f)
        if isinstance(db, list):
            db = {k.get("kunde_id", f"K{i:03d}"): k for i, k in enumerate(db) if isinstance(k, dict)}
    except Exception:
        db = {}
    zeilen = ""
    for kid, k in db.items():
        bez = "✅ bezahlt" if k.get("bezahlt") else "⏳ offen"
        zeilen += (f"<tr><td><code>{html.escape(kid)}</code></td><td>{html.escape(k.get('firma',''))}</td>"
                   f"<td>{html.escape(k.get('gueltig_bis',''))}</td><td>{bez}</td>"
                   f"<td><form method='post' action='/admin_freigeben'>"
                   f"<input type='hidden' name='kunde_id' value='{html.escape(kid)}'>"
                   f"<button type='submit'>Zahlung da → Code</button></form></td></tr>")
    body = f"""
 <div class="card">
  <h2>Anbieter-Konsole – nur Zahlungseingang bestätigen
   <a href="/admin_logout" style="float:right;font-size:.8rem">Logout</a></h2>
  <p class="meta">Nach Klick auf „Zahlung da" läuft alles automatisch: Rechnung,
  Jahres-Code-Erzeugung, Code-Versand an Kunden.</p>
  <p class="meta"><b>Format-Unterstützung:</b> DevisPro importiert SIA-451/Sorba, Bauweb/Daedalus,
  generisches CSV/Excel, GAEB D84 (DE), ÖNORM (AT) und XRechnung (EU) – und erzeugt pro Devis
  eine Swiss QR-Rechnung.</p>
  <table><thead><tr><th>Kunde</th><th>Firma</th><th>Gültig bis</th><th>Status</th><th>Aktion</th></tr></thead>
  <tbody>{zeilen or "<tr><td colspan=5>Keine Kunden</td></tr>"}</tbody></table>
  <form method="post" action="/admin_neu" style="margin-top:1rem">
   <h3 style="font-size:1rem">Neuer Kunde</h3>
   <input type="text" name="kunde_id" placeholder="KMU-001" style="max-width:160px">
   <input type="text" name="firma" placeholder="Firma" style="max-width:200px">
   <input type="email" name="email" placeholder="email@firma.ch" style="max-width:240px">
   <select name="pilot"><option value="0">Volllizenz</option><option value="1">Pilot (3 Mon)</option></select>
   <button type="submit">Anlegen</button>
  </form>
  <form method="post" action="/admin_code" style="margin-top:.8rem">
   <h3 style="font-size:1rem">Freischaltcode erzeugen (für Verkaufskunden)</h3>
   <p class="meta">Erzeugt einen signierten Code, den der Kunde beim ersten Start unter „Lizenz" eingibt.</p>
   <input type="text" name="kunde_id" placeholder="KMU-001" style="max-width:160px">
   <button type="submit">Code erzeugen</button>
  </form>
  <form method="post" action="/admin_erinnerung" style="margin-top:.8rem">
   <button type="submit">Erinnerungen jetzt prüfen/versenden</button>
  </form>
  <form method="post" action="/admin_smtp" style="margin-top:1.2rem">
   <h3 style="font-size:1rem">E-Mail-Versand (SMTP) – einmalig einrichten</h3>
   <p class="meta">Damit Bestätigungs- und Lead-Mails an <code>info@monterossa.ch</code> sowie
   an Kunden automatisch rausgehen. Die Zugangsdaten bleiben lokal in <code>data/</code>.</p>
   <p class="meta"><b>Hostinger (devispro.de):</b> Mailbox + Passwort eingeben, Rest ist voreingestellt (smtp.hostinger.com, SSL 465).</p>
   <input type="hidden" name="preset" value="hostinger">
   <input type="text" name="user" placeholder="info@devispro.de" style="max-width:240px">
   <input type="password" name="pass" placeholder="Mailbox-Passwort (Hostinger)" style="max-width:240px">
   <div style="display:flex;gap:.6rem;align-items:center;flex-wrap:wrap">
    <label>Absender:<input type="text" name="von" value="info@devispro.de" style="max-width:200px"></label>
    <label>Port: <input type="number" name="port" value="465" style="width:80px"></label>
    <label>Verschlüsselung:
     <select name="tls">
      <option value="ssl" selected>SSL (465)</option>
      <option value="starttls">STARTTLS (587)</option>
      <option value="none">Ohne</option>
     </select>
    </label>
   </div>
   <button type="submit">Hostinger speichern</button>
  </form>
  <form method="post" action="/admin_smtp" style="margin-top:1rem">
   <h3 style="font-size:1rem">E-Mail-Versand (anderer Anbieter)</h3>
   <input type="text" name="host" placeholder="smtp.monterossa.ch" style="max-width:240px">
   <input type="text" name="user" placeholder="info@monterossa.ch" style="max-width:240px">
   <input type="password" name="pass" placeholder="SMTP-Passwort" style="max-width:240px">
   <div style="display:flex;gap:.6rem;align-items:center;flex-wrap:wrap">
    <label>Port: <input type="number" name="port" value="587" style="width:80px"></label>
    <label>Verschlüsselung:
     <select name="tls">
      <option value="starttls" selected>STARTTLS (587)</option>
      <option value="ssl">SSL (465)</option>
      <option value="none">Ohne</option>
     </select>
    </label>
   </div>
   <button type="submit">SMTP speichern</button>
  </form>
  <form method="post" action="/admin_smtp_test" style="margin-top:1rem">
   <h3 style="font-size:1rem">Test-Mail senden</h3>
   <input type="email" name="test_to" placeholder="ihre@email.ch" style="max-width:240px">
   <button type="submit">Test senden</button>
  </form>
  <form method="post" action="/admin_werbe_mail" style="margin-top:1rem">
   <h3 style="font-size:1rem">Werbe-Mail (HTML, ohne Anhang)</h3>
   <p class="meta">Phishing-sichere HTML-Mail – Kunden öffnen keinen Anhang. Empfänger mit Komma trennen.</p>
   <input type="text" name="empfaenger" placeholder="kunde@beispiel.ch, info@monterossa.ch" style="max-width:320px">
   <button type="submit">Werbe-Mail senden</button>
  </form>
  <p style="margin-top:1rem"><a class="btn" href="/admin_white_label">⚙ White-Label &amp; Verbands-Lizenzen</a> <a class="btn" href="/admin_funnel">📈 Funnel &amp; Leads</a></p>
  </div>
"""
    return render_page(body, lang)

def render_dashboard(lang="de"):
    from devispro import system as sys_mod
    import glob, json, os as _os
    ok, msgs = sys_mod.gesundheitscheck()
    backups = sys_mod.letzte_backups(5)
    # Letzte Devis-Werte aus bepreit-Maps
    werte = []
    for f in glob.glob(os.path.join(DATA, "*.sia")):
        try:
            from devispro.parsers import crb
            d = crb.parse(f)
            tot = sum((p.betrag or 0) for p in d.positions)
            werte.append((_os.path.basename(f), tot))
        except Exception:
            pass
    werte.sort(key=lambda x: x[1], reverse=True)
    rowsh = "".join(f"<tr><td>{html.escape(n)}</td><td>{v:,.2f} CHF</td></tr>" for n, v in werte[:8]) or "<tr><td colspan=2>Keine Devis verarbeitet</td></tr>"
    bk = "".join(f"<li>{html.escape(b)}</li>" for b in backups) or "<li>Keine Backups</li>"
    health = "✓ Alle Systeme OK" if ok else "⚠ " + "; ".join(msgs)
    body = f"""
 <div class="card">
  <h2>Dashboard – System &amp; Statistik</h2>
  <p class="{'okbox' if ok else 'warn'}">{health}</p>
  <div style="display:flex;gap:2rem;flex-wrap:wrap">
   <div><h3>Verarbeitete Devis (Werte)</h3>
    <table><thead><tr><th>Datei</th><th>Netto</th></tr></thead><tbody>{rowsh}</tbody></table></div>
   <div><h3>Backups (letzte 5)</h3><ul>{bk}</ul>
    <form method="post" action="/backup_now"><button type="submit">Jetzt Backup erstellen</button></form></div>
  </div>
  <p class="meta">Alle Aktionen werden im Audit-Log (data/audit.log) protokolliert.</p>
 </div>
"""
    return render_page(body, lang)


class Handler(BaseHTTPRequestHandler):
    def _send(self, body: bytes, ctype="text/html; charset=utf-8"):
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _fieldstorage(self):
        length = int(self.headers.get("Content-Length", 0))
        return cgi.FieldStorage(fp=self.rfile, headers=self.headers,
                                environ={"REQUEST_METHOD": "POST",
                                         "CONTENT_TYPE": self.headers.get("Content-Type", ""),
                                         "CONTENT_LENGTH": str(length)})

    def do_GET(self):
        lang = lang_from_request(self)
        parsed = urlparse(self.path)
        # --- Trial-Gate: ohne gueltige Lizenz nur Trial-Anmeldung zugreifen ---
        if not liz.darf_nutzen():
            frei_exact = {"/", "/start", "/trial", "/lizenz", "/admin",
                          "/api/version", "/favicon.ico"}
            frei_prefix = ("/lang/", "/devis_doc_file")
            if not (parsed.path in frei_exact
                    or any(parsed.path.startswith(p) for p in frei_prefix)):
                self.send_response(303)
                self.send_header("Location", f"/lizenz?lang={lang}")
                self.end_headers()
                return
        if parsed.path == "/qr_rechnung":
            q = parse_qs(parsed.query)
            did = q.get("id", [None])[0]
            if not did or not history_mod.exists(did):
                self._send(render_page("<div class='blocker'>✗ Devis nicht gefunden.</div>", lang).encode("utf-8"))
                return
            try:
                devis = crb.parse(history_mod.path_of(did, "bepreist.sia"))
                profil = stammdaten.load_profile() or {}
                kreditor = {
                    "name": profil.get("betrieb") or "Monterossa AG",
                    "strasse": profil.get("strasse") or "Hauptstrasse 1",
                    "plz_ort": profil.get("plz_ort") or "8000 Zuerich",
                    "land": "CH",
                    "iban": profil.get("iban") or "CH3908704016075473007",
                }
                from devispro import qr_rechnung as qr_mod
                qr = qr_mod.rechnung_aus_devis(devis, kreditor=kreditor, ref_nr=did)
                body = (f"<div class='card'><h3>Swiss QR-Rechnung – {html.escape(did)}</h3>"
                        f"<pre style='white-space:pre-wrap;background:#fff;padding:1rem;border:1px solid #ddd'>{html.escape(qr.als_text())}</pre>"
                        f"<p class='meta'>QR-Code-Verfuegbar: {qr_mod.qr_verfuegbar()}</p>"
                        f"<a class='btn' href='/devis/{did}'>← Zurück</a></div>")
                self._send(render_page(body, lang).encode("utf-8"))
            except Exception as e:
                self._send(render_page(f"<div class='blocker'>✗ Fehler: {html.escape(str(e))}</div>", lang).encode("utf-8"))
            return
        if parsed.path == "/check" and self.command == "GET":
            # Gratis Devis-Check (Lead-Magnet, OHNE Login)
            q = parse_qs(parsed.query)
            if q.get("embed", ["0"])[0] == "1":
                # Eigenstaendiges, einbettbares Widget (fuer devispro.de Landing)
                from devispro import lead_magnet as lead_mod
                html = lead_mod.render_form(lang)
                self._send(html.encode("utf-8"), "text/html; charset=utf-8")
                return
            body = _render_devis_check(self, lang)
            self._send(render_page(body, lang).encode("utf-8"))
            return
        if parsed.path == "/erp":
            from devispro import license as _liz
            from devispro import erp_ui as _eu
            meld = ""
            q = parse_qs(parsed.query)
            if q.get("m"):
                meld = q["m"][0]
            body = _eu.render_erp(_liz.tarif(), meldung=meld)
            self._send(render_page(body, lang).encode("utf-8"))
            return

        if parsed.path == "/download":
            path = os.path.join(DATA, os.path.basename(fname))
            if os.path.exists(path):
                with open(path, "rb") as f:
                    data = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.send_header("Content-Disposition", f'attachment; filename="{os.path.basename(fname)}"')
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
                return
            self._send(b"Datei nicht gefunden", "text/plain; charset=utf-8")
            return
        elif parsed.path == "/dashboard":
            self._send(render_dashboard().encode("utf-8"))
        elif parsed.path == "/lizenz":
            self._send(render_lizenz().encode("utf-8"))
        elif parsed.path == "/trial":
            q = parse_qs(parsed.query)
            em = (q.get("email", [""])[0] or "").strip()
            pj = (q.get("projekt", [""])[0] or "").strip()
            self._send(render_trial(lang, email=em, projekt=pj).encode("utf-8"))
        elif parsed.path == "/admin":
            tok = self.headers.get("Cookie", "").split("adminsess=")[-1].split(";")[0]
            if auth.session_gueltig(tok):
                self._send(render_admin().encode("utf-8"))
            else:
                self._send(render_admin_login().encode("utf-8"))
        elif parsed.path == "/profil":
            self._send(render_profil().encode("utf-8"))
        elif parsed.path in ("/", "/start"):
            qlang = lang_from_request(self)
            # ?lang= setzt Cookie, damit die Sprache im ganzen App bleibt
            if "lang=" in parsed.query:
                self.send_response(303)
                self.send_header("Location", "/")
                self.send_header("Set-Cookie", f"lang={qlang}; Path=/")
                self.end_headers()
                return
            self._send(marketing_mod.render_landing(qlang).encode("utf-8"),
                       "text/html; charset=utf-8")
        elif parsed.path == "/api/version":
            lang = lang_from_request(self)
            res = updates_mod.check()
            res["banner"] = updates_mod.render_banner(res, lang)
            payload = json.dumps(res, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return
        elif parsed.path == "/bepreisen":
            self._send(render_index(self).encode("utf-8"))
        elif parsed.path == "/offerte":
            # Angebot (HTML/A4; PDF falls wkhtmltopdf vorhanden) aus bepreister SIA
            # Optional ?id=devis_XXXX -> aus Verlauf laden
            q = parse_qs(parsed.query)
            did = q.get("id", [None])[0]
            if did and history_mod.exists(did):
                bex = history_mod.path_of(did, "bepreist.sia")
            else:
                bex = os.path.join(DATA, "bepreist.sia")
            if not os.path.exists(bex):
                self._send(render_page("<div class='blocker'>✗ Bitte zuerst ein Devis bepreisen.</div>", lang).encode("utf-8"))
                return
            try:
                devis = crb.parse(bex)
                profil = stammdaten.load_profile() or {}
                olang = q.get("lang", [lang])[0]
                if olang not in LANGS:
                    olang = lang
                html_doc = pdf_mod.build_offerte_html(devis, profil, extras=[], lang=olang)
                self._send(html_doc.encode("utf-8"), "text/html; charset=utf-8")
            except Exception as e:
                self._send(render_page(f"<div class='blocker'>✗ Fehler: {html.escape(str(e))}</div>", lang).encode("utf-8"))
        elif parsed.path == "/meine_devis":
            self._send(render_meine_devis(lang).encode("utf-8"))
        elif parsed.path.startswith("/devis/"):
            did = parsed.path[len("/devis/"):].split("?")[0]
            if not did or not history_mod.exists(did):
                self._send(render_page("<div class='blocker'>✗ Devis nicht gefunden.</div>", lang).encode("utf-8"))
                return
            self._send(render_devis_view(did, lang).encode("utf-8"))
        elif parsed.path == "/devis_view":
            q = parse_qs(parsed.query)
            did = q.get("id", [None])[0]
            if not did or not history_mod.exists(did):
                self._send(render_page("<div class='blocker'>✗ Devis nicht gefunden.</div>", lang).encode("utf-8"))
                return
            self._send(render_devis_view(did, lang).encode("utf-8"))
        elif parsed.path == "/devis_offerte":
            q = parse_qs(parsed.query)
            did = q.get("id", [None])[0]
            if not did or not history_mod.exists(did):
                self._send(render_page("<div class='blocker'>✗ Devis nicht gefunden.</div>", lang).encode("utf-8"))
                return
            try:
                devis = crb.parse(history_mod.path_of(did, "bepreist.sia"))
                profil = stammdaten.load_profile() or {}
                olang = q.get("lang", [lang])[0]
                if olang not in LANGS:
                    olang = lang
                as_pdf = q.get("pdf", ["0"])[0] in ("1", "on", "true")
                if as_pdf:
                    # echtes PDF via dependency-freiem Generator (immer verfuegbar)
                    data = documents_mod.build_pdf("devis_muster", devis, profil, olang, qr=True)
                    history_mod.save_doc(did, "offerte", data, "pdf")
                    self.send_response(200)
                    self.send_header("Content-Type", "application/pdf")
                    self.send_header("Content-Disposition", f'attachment; filename="{did}_offerte.pdf"')
                    self.send_header("Content-Length", str(len(data)))
                    self.end_headers()
                    self.wfile.write(data)
                    return
                html_doc = pdf_mod.build_offerte_html(devis, profil, extras=[], lang=olang)
                self._send(html_doc.encode("utf-8"), "text/html; charset=utf-8")
            except Exception as e:
                self._send(render_page(f"<div class='blocker'>✗ Fehler: {html.escape(str(e))}</div>", lang).encode("utf-8"))
        elif parsed.path == "/devis_download":
            q = parse_qs(parsed.query)
            did = q.get("id", [None])[0]
            if not did or not history_mod.exists(did):
                self._send(b"Datei nicht gefunden", "text/plain; charset=utf-8")
                return
            fname = did + ".sia"
            path = history_mod.path_of(did, "bepreist.sia")
            with open(path, "rb") as f:
                data = f.read()
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Disposition", f'attachment; filename="{fname}"')
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return
        elif parsed.path == "/devis_doc":
            q = parse_qs(parsed.query)
            did = q.get("id", [None])[0]
            typ = q.get("typ", ["devis_muster"])[0]
            dlang = q.get("lang", [lang])[0]
            if dlang not in LANGS:
                dlang = lang
            if not did or not history_mod.exists(did):
                self._send(render_page("<div class='blocker'>✗ Devis nicht gefunden.</div>", lang).encode("utf-8"))
                return
            try:
                devis = crb.parse(history_mod.path_of(did, "bepreist.sia"))
                profil = stammdaten.load_profile() or {}
                bindend_bis = q.get("bindend_bis", [""])[0]
                maengel = q.get("maengel", [])
                if isinstance(maengel, str):
                    maengel = [m for m in maengel.split("|") if m.strip()] or None
                bedingt = q.get("bedingt", ["0"])[0] in ("1", "on", "true")
                as_pdf = q.get("pdf", ["0"])[0] in ("1", "on", "true")
                if as_pdf:
                    # echtes PDF via dependency-freiem Generator (immer verfuegbar)
                    data = documents_mod.build_pdf(
                        typ, devis, profil, dlang,
                        bindend_bis=bindend_bis, maengel=maengel, bedingt=bedingt,
                    )
                    history_mod.save_doc(did, f"doc_{typ}", data, "pdf")
                    self.send_response(200)
                    self.send_header("Content-Type", "application/pdf")
                    self.send_header("Content-Disposition", f'attachment; filename="{did}_{typ}.pdf"')
                    self.send_header("Content-Length", str(len(data)))
                    self.end_headers()
                    self.wfile.write(data)
                    return
                html_doc = documents_mod.build(
                    typ, devis, profil, dlang,
                    bindend_bis=bindend_bis, maengel=maengel, bedingt=bedingt,
                )
                history_mod.save_doc(did, f"doc_{typ}", html_doc.encode("utf-8"), "html")
                self._send(html_doc.encode("utf-8"), "text/html; charset=utf-8")
            except Exception as e:
                self._send(render_page(f"<div class='blocker'>✗ Fehler: {html.escape(str(e))}</div>", lang).encode("utf-8"))
            return
        elif parsed.path == "/devis_rechnung":
            q = parse_qs(parsed.query)
            did = q.get("id", [None])[0]
            if not did or not history_mod.exists(did):
                self._send(render_page("<div class='blocker'>✗ Devis nicht gefunden.</div>", lang).encode("utf-8"))
                return
            try:
                devis = crb.parse(history_mod.path_of(did, "bepreist.sia"))
                profil = stammdaten.load_profile() or {}
                rlang = q.get("lang", [lang])[0]
                if rlang not in LANGS:
                    rlang = lang
                rnr = q.get("rnr", [f"R-{did[-4:]}"])[0] or f"R-{did[-4:]}"
                datum = q.get("datum", [""])[0] or devis.meta.get("date", "")
                faellig = q.get("faellig", [""])[0] or ""
                rabatt = q.get("rabatt_pct", ["0"])[0] or "0"
                skonto = q.get("skonto_pct", ["0"])[0] or "0"
                skonto_bis = q.get("skonto_bis", [""])[0] or ""
                as_pdf = q.get("pdf", ["0"])[0] in ("1", "on", "true")
                r = rechnung_mod.from_devis(
                    devis, profil, rnr, datum, faellig,
                    rabatt_pct=float(rabatt or 0), skonto_pct=float(skonto or 0),
                    skonto_bis=skonto_bis,
                )
                # Zahlungsplan: 1/3 / 2/3 bei Bauleistung als Vorschlag
                if not faellig:
                    r.zahlungsplan = [
                        rechnung_mod.Teilzahlung(faellig="bei Auftragserteilung", betrag=round(r.brutto()*0.3*100)/100, grund="1. Rate (30%)"),
                        rechnung_mod.Teilzahlung(faellig="bei Bezug", betrag=round(r.brutto()*0.4*100)/100, grund="2. Rate (40%)"),
                        rechnung_mod.Teilzahlung(faellig="30 Tage nach Schluss", betrag=round(r.brutto()*0.3*100)/100, grund="Schlussrechnung (30%)"),
                    ]
                if as_pdf:
                    data = rechnung_mod.build_pdf(r, rlang)
                    history_mod.save_doc(did, "rechnung", data, "pdf")
                    self.send_response(200)
                    self.send_header("Content-Type", "application/pdf")
                    self.send_header("Content-Disposition", f'attachment; filename="{did}_rechnung.pdf"')
                    self.send_header("Content-Length", str(len(data)))
                    self.end_headers()
                    self.wfile.write(data)
                    return
                html_doc = rechnung_mod.build_html(r, rlang)
                history_mod.save_doc(did, "rechnung", html_doc.encode("utf-8"), "html")
                self._send(html_doc.encode("utf-8"), "text/html; charset=utf-8")
            except Exception as e:
                self._send(render_page(f"<div class='blocker'>✗ Fehler: {html.escape(str(e))}</div>", lang).encode("utf-8"))
            return
        elif parsed.path == "/ordner_import":
            body = (
                "<div class='card'><h2>📁 Ordner-Import (komplettes Devis aus vielen Unterlagen)</h2>"
                "<p class='meta'>Bei grösseren Bauten enthält eine Ausschreibung viele Unterlagen: "
                "Leistungsverzeichnis (.sia/.crb), Zusatzblätter (CSV/XLSX), GAEB (.xml), XRechnung (.xml), "
                "Pläne als Foto/PDF. Laden Sie den <b>ganzen Ordner</b> hoch – DevisPro analysiert jede Datei "
                "und füllt das Devis <b>vollständig</b> aus (Positionen werden zusammengeführt, doppelte entfernt).</p>"
                "<form method='post' action='/ordner_import' enctype='multipart/form-data'>"
                "<p class='meta'><b>Mehrere Dateien auswählen</b> (oder einen ganzen Ordner per ⌘/Strg+A):</p>"
                "<input type='file' name='files' multiple accept='.sia,.crb,.csv,.xlsx,.xls,.xml,.txt,.png,.jpg,.jpeg,.webp,.pdf' style='max-width:40rem'>"
                "<p style='margin-top:.6rem'><label><input type='checkbox' name='bepreisen' value='1' checked> "
                "automatisch gegen meine Richtpreise bepreisen</label></p>"
                "<button type='submit' class='btn' style='margin-top:.6rem'>Analysieren &amp; Devis erstellen</button></form>"
                "<p class='meta' style='margin-top:1rem'>Unterstützte Formate: SIA-451/Sorba, Bauweb/Daedalus, "
                "generisches CSV/Excel, GAEB (DE), ÖNORM (AT), XRechnung (EU). Bilder/PDF werden als «manuell» "
                "markiert (OCR auf diesem System nicht verfügbar).</p></div>"
            )
            self._send(render_page(body, lang).encode("utf-8"))
            return
        elif parsed.path == "/waehrung":
            q = parse_qs(parsed.query)
            did = q.get("id", [None])[0]
            ziel = q.get("ziel", ["EUR"])[0]
            profil = stammdaten.load_profile() or {}
            betrag_chf = 0.0
            if did and history_mod.exists(did):
                try:
                    devis = crb.parse(history_mod.path_of(did, "bepreist.sia"))
                    betrag_chf = sum((p.betrag or 0) for p in devis.positions)
                except Exception:
                    pass
            kurs = mc_mod.kurs_chf_nach(ziel)
            umg = mc_mod.umrechnen(betrag_chf, ziel)
            opts = "".join(f"<option value='{c}' {'selected' if c==ziel else ''}>{c}</option>" for c in mc_mod.verfuegbare())
            body = (
                "<div class='card'><h2>💱 Mehrwährung (CH/DE/AT/FR/IT)</h2>"
                "<p class='meta'>DevisPro rechnet IMMER in CHF (kein Währungsrisiko). Die Fremdwährung ist eine "
                "Anzeige/Export-Umrechnung für Grenzprojekte (Tessin→IT, Genf→FR, Grenzgänger DE/AT).</p>"
                f"<form method='get'><label>Devis: <select name='id'>{''.join(f'<option value={d}>{d}</option>' for d in history_mod.list_all()[:50])}</select></label> "
                f"<label>Zielwährung: <select name='ziel'>{opts}</select></label> "
                "<button type='submit' class='btn-sm'>Umrechnen</button></form>"
                f"<div class='save'>💡 1 CHF = {kurs:.4f} {ziel} · "
                f"Devis-Total: CHF {betrag_chf:,.2f} = <b>{mc_mod.format(ziel, umg)}</b></div>"
                "<p class='meta'>Kurse via SNB/EZB (Live) mit sicheren Offline-Referenzkursen als Fallback.</p></div>"
            )
            self._send(render_page(body, lang).encode("utf-8"))
            return
        elif parsed.path == "/whatsapp":
            did = parse_qs(parsed.query).get("id", [None])[0]
            profil = stammdaten.load_profile() or {}
            body = (
                "<div class='card'><h2>📱 WhatsApp-Bot (Angebot in 10 Sek.)</h2>"
                "<p class='meta'>Erzeugen Sie einen Klick-freien Angebotstext + Deep-Link für WhatsApp. "
                "Ideal für Bauherren, die schnell ein Angebot aufs Handy wollen.</p>"
                "<form method='get'><label>Devis: <select name='id'>" +
                "".join(f"<option value='{d}'>{d}</option>" for d in history_mod.list_all()[:50]) +
                "</select></label> <button type='submit' class='btn-sm'>Vorschau</button></form>"
            )
            if did and history_mod.exists(did):
                devis = crb.parse(history_mod.path_of(did, "bepreist.sia"))
                txt = wa_mod.angebot_text(devis, profil, did, lang)
                link = wa_mod.deep_link(did, txt)
                body += (
                    f"<h3 style='margin-top:1rem'>Angebotstext</h3><pre style='white-space:pre-wrap;background:#f8faf8;border:1px solid #ddd;padding:.8rem;border-radius:6px'>{html.escape(txt)}</pre>"
                    f"<p><a class='btn' href='{html.escape(link)}' target='_blank'>↗ In WhatsApp öffnen</a></p>"
                )
            body += "</div>"
            self._send(render_page(body, lang).encode("utf-8"))
            return
        elif parsed.path == "/subunternehmer":
            q = parse_qs(parsed.query)
            did = q.get("id", [None])[0]
            profil = stammdaten.load_profile() or {}
            body = (
                "<div class='card'><h2>🤝 Subunternehmer-Marge</h2>"
                "<p class='meta'>Erfassen Sie die Offerten Ihrer Subunternehmer pro Position – DevisPro rechnet "
                "Ihre Marge (Verkaufspreis − Sub-Kosten) aus und zeigt sie sofort.</p>"
                "<form method='get'><label>Devis: <select name='id'>" +
                "".join(f"<option value='{d}'>{d}</option>" for d in history_mod.list_all()[:50]) +
                "</select></label> <button type='submit' class='btn-sm'>Anzeigen</button></form>"
            )
            if did and history_mod.exists(did):
                devis = crb.parse(history_mod.path_of(did, "bepreist.sia"))
                zeilen = sub_mod.marge_berechnen(devis, did)
                rows = "".join(
                    f"<tr><td>{html.escape(str(z['pos_nr']))}</td><td>{html.escape(str(z['text']))}</td>"
                    f"<td style='text-align:right'>{z['verkauf']:,.2f}</td>"
                    f"<td>{html.escape(str(z['sub_firma']))}</td>"
                    f"<td style='text-align:right'>{z['sub_betrag']:,.2f}</td>"
                    f"<td style='text-align:right;color:{'#15803d' if z['marge']>=0 else '#b91c1c'}'>{z['marge']:,.2f} ({z['marge_pct']:.0f}%)</td></tr>"
                    for z in zeilen)
                body += (
                    "<table style='margin-top:.6rem'><thead><tr><th>Pos</th><th>Text</th><th>Verkauf CHF</th>"
                    "<th>Sub-Firma</th><th>Sub CHF</th><th>Marge</th></tr></thead>"
                    f"<tbody>{rows}</tbody></table>"
                    "<form method='post' action='/sub_setze' style='margin-top:1rem'>"
                    f"<input type='hidden' name='id' value='{html.escape(str(did))}'>"
                    "<input name='pos' placeholder='Pos-Nr' style='width:80px'> "
                    "<input name='firma' placeholder='Sub-Firma' style='width:160px'> "
                    "<input name='betrag' type='number' step='0.01' placeholder='Sub-Betrag CHF' style='width:140px'> "
                    "<button type='submit' class='btn-sm'>Offerte speichern</button></form>"
                )
            body += "</div>"
            self._send(render_page(body, lang).encode("utf-8"))
            return
        elif parsed.path == "/margen":
            did = parse_qs(parsed.query).get("id", [None])[0]
            profil = stammdaten.load_profile() or {}
            kt = profil.get("kanton", "ZH")
            body = (
                "<div class='card'><h2>🧠 Margen-Copilot</h2>"
                "<p class='meta'>Heuristik statt Black Box: DevisPro vergleicht Ihre Preise mit dem anonymen "
                "Marktpreis-Netzwerk und flaggt zu tiefe/hoche Kalkulationen. Erklärbar, offline, keine API-Keys.</p>"
                "<form method='get'><label>Devis: <select name='id'>" +
                "".join(f"<option value='{d}'>{d}</option>" for d in history_mod.list_all()[:50]) +
                "</select></label> <button type='submit' class='btn-sm'>Analysieren</button></form>"
            )
            if did and history_mod.exists(did):
                devis = crb.parse(history_mod.path_of(did, "bepreist.sia"))
                from devispro import benchmark as bench_mod
                res = margen_mod.analyse(devis, kanton=kt, benchmark_mod=bench_mod)
                rows = "".join(
                    f"<tr><td>{html.escape(str(r['pos_nr']))}</td><td>{html.escape(str(r['text']))}</td>"
                    f"<td style='text-align:center;font-size:1.1rem'>{r['status']}</td>"
                    f"<td class='meta'>{html.escape(str(r['hinweis']))}</td></tr>"
                    for r in res)
                body += (
                    "<table style='margin-top:.6rem'><thead><tr><th>Pos</th><th>Text</th><th>Status</th>"
                    "<th>Empfehlung</th></tr></thead>"
                    f"<tbody>{rows}</tbody></table>"
                )
            body += "</div>"
            self._send(render_page(body, lang).encode("utf-8"))
            return
        elif parsed.path == "/marketing":
            profil = stammdaten.load_profile() or {}
            devis_liste = []
            for did in history_mod.list_all()[:10]:
                try:
                    d = crb.parse(history_mod.path_of(did, "bepreist.sia"))
                    devis_liste.append((d, d.meta.get("project_name") or did))
                except Exception:
                    pass
            sample = devis_liste[0][0] if devis_liste else Devis(meta={"project_name": "Musterprojekt"}, addresses=[], chapters=[], positions=[])
            posts = "".join(
                f"<h3 style='margin-top:1rem'>{p.title()}</h3>"
                f"<pre style='white-space:pre-wrap;background:#f8faf8;border:1px solid #ddd;padding:.8rem;border-radius:6px'>{html.escape(marketing_mod.social_post(profil, sample, p, lang))}</pre>"
                for p in ("linkedin", "facebook", "instagram"))
            body = (
                "<div class='card'><h2>📣 Marketing-Assistent</h2>"
                "<p class='meta'>Aus dem Devis wird Vertriebs-Material: Social Posts, Ausschreibungs-Anschreiben, "
                "Referenz-Blatt (PDF). DevisPro = Rechen-Tool + Vertriebs-Assistent.</p>"
                f"<h3>Ausschreibungs-Anschreiben (Muster)</h3>"
                f"<pre style='white-space:pre-wrap;background:#f8faf8;border:1px solid #ddd;padding:.8rem;border-radius:6px'>{html.escape(marketing_mod.ausschreibungs_anschreiben(profil, sample, lang))}</pre>"
                f"{posts}"
                "<p class='meta' style='margin-top:1rem'>Referenz-PDF: <a class='btn-sm' href='/marketing_referenz'>⬇ Herunterladen</a></p>"
                "</div>"
            )
            self._send(render_page(body, lang).encode("utf-8"))
            return
        elif parsed.path == "/erp_api":
            profil = stammdaten.load_profile() or {}
            spec = erp_mod.spezifikation()
            body = (
                "<div class='card'><h2>🔌 Echte ERP-Connector-API</h2>"
                "<p class='meta'>Statt nur CSV-Export: automatisierter Push von Offerten/Rechnungen an Abacus/Proffix "
                "via HMAC-signierter REST-API. Sie hosten den Endpunkt im Büro; DevisPro pusht (LAN/HTTPS).</p>"
                f"<p class='meta'><b>Endpoint:</b> {html.escape(spec['endpoint'])} · <b>Auth:</b> {html.escape(spec['auth'])}</p>"
                "<form method='post' action='/erp_push' style='display:flex;flex-wrap:wrap;gap:.5rem;margin-top:.6rem'>"
                "<label>ERP-URL<input name='url' placeholder='https://buero.local/api/v1/belege' style='width:280px'></label> "
                "<label>Secret<input name='secret' type='password' style='width:180px'></label> "
                "<label>Devis<select name='id'>" +
                "".join(f"<option value='{d}'>{d}</option>" for d in history_mod.list_all()[:50]) +
                "</select></label> "
                "<button type='submit' class='btn'>Push testen</button></form>"
                "<p class='meta' style='margin-top:1rem'>ERP-Beispiele: " +
                " · ".join(f"<b>{k}</b>: {html.escape(v)}" for k, v in spec['erp_beispiele'].items()) + "</p>"
                "</div>"
            )
            self._send(render_page(body, lang).encode("utf-8"))
            return
        elif parsed.path == "/marketing_referenz":
            profil = stammdaten.load_profile() or {}
            devis_liste = []
            for did in history_mod.list_all()[:10]:
                try:
                    d = crb.parse(history_mod.path_of(did["id"] if isinstance(did, dict) else did, "bepreist.sia"))
                    devis_liste.append((d, d.meta.get("project_name") or (did["id"] if isinstance(did, dict) else did)))
                except Exception:
                    pass
            if not devis_liste:
                devis_liste = [(Devis(meta={"project_name": "Musterprojekt"}, addresses=[], chapters=[], positions=[]), "Musterprojekt")]
            data = marketing_mod.referenz_blatt_pdf(profil, devis_liste, lang)
            self.send_response(200)
            self.send_header("Content-Type", "application/pdf")
            self.send_header("Content-Disposition", 'attachment; filename="referenzen.pdf"')
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return
        elif parsed.path == "/agent":
            q = parse_qs(parsed.query)
            did = q.get("did", [None])[0]
            profil = stammdaten.load_profile() or {}
            devis_opts = "".join(
                f"<option value='{d['id']}' {'selected' if did==d['id'] else ''}>{d['id']} – {html.escape(str(d.get('name','')))}</option>"
                for d in history_mod.list_all()[:50])
            body = (
                "<div class='card'><h2>🤖 DevisPro KI-Agent</h2>"
                "<p class='meta'>Ihr lokaler, offline Assistent (keine Cloud, keine API-Keys). Er beantwortet Fragen "
                "und fuehrt echte Aktionen aus: MWST/Kanton aendern, Export in Buchhaltung, Waehrung umrechnen, "
                "Marketing-Texte, Devis oeffnen.</p>"
                "<form method='get' style='margin-bottom:.6rem'><label>Betreff Devis: <select name='did'>" +
                "<option value=''>– keines –</option>" + devis_opts + "</select></label> "
                "<button type='submit' class='btn-sm'>Laden</button></form>"
                "<div id='agentlog' style='background:#f8faf8;border:1px solid #ddd;border-radius:6px;padding:.8rem;max-height:320px;overflow:auto;white-space:pre-wrap;font-size:.95rem'>"
                "🤖 Hallo! Ich bin der DevisPro-KI-Agent. Was moechten Sie tun?\n"
                "Beispiele: «setze MWST auf 7.7», «exportiere nach Abacus», «rechne 5000 CHF in EUR um», «öffne devis_0007».\n"
                f"Aktueller Betrieb: {html.escape(str(profil.get('betrieb','')))} · Kanton: {html.escape(str(profil.get('kanton','ZH')))} · MWST: {profil.get('mwst_pct',8.1)}%</div>"
                "<form method='post' action='/agent_chat' id='agentform' style='display:flex;gap:.5rem;margin-top:.6rem'>"
                f"<input type='hidden' name='did' value='{html.escape(str(did or ''))}'>"
                "<input name='msg' placeholder='Ihre Frage oder Aktion…' style='flex:1' autofocus>"
                "<button type='submit' class='btn'>Senden</button></form>"
                "<script>document.getElementById('agentform').addEventListener('submit',function(e){e.preventDefault();"
                "var f=this,m=f.msg.value;if(!m)return;var log=document.getElementById('agentlog');"
                "log.innerHTML+='\\n\\n👤 '+m;f.msg.value='';"
                "var fd=new FormData(f);fetch('/agent_chat',{method:'post',body:new URLSearchParams(fd)}).then(r=>r.text()).then(t=>{log.innerHTML+='\\n🤖 '+t;log.scrollTop=log.scrollHeight;});});</script>"
                "</div>"
            )
            self._send(render_page(body, lang).encode("utf-8"))
            return
        elif parsed.path == "/backup":
            backups = backup_mod.list_backups()
            rows = "".join(
                f"<tr><td>{html.escape(b['name'])}</td><td>{b['size']//1024} KB</td>"
                f"<td>{html.escape(time.strftime('%Y-%m-%d %H:%M', time.localtime(b['time'])))}</td>"
                f"<td><a class='btn-sm' href='/backup_download?name={quote(b['name'])}'>⬇</a></td>"
                f"<td><a class='btn-sm' href='/backup_restore?name={quote(b['name'])}' onclick=\"return confirm('Wirklich wiederherstellen? Aktuelle Daten werden ueberschrieben.')\">↺</a></td></tr>"
                for b in backups) or "<tr><td colspan='5' class='meta'>Noch keine Backups vorhanden.</td></tr>"
            body = (
                "<div class='card'><h2>💾 Backup &amp; Wiederherstellung</h2>"
                "<p class='meta'>Schützt Ihre Kundendaten (Devis, Preisliste, Stammdaten, Abo, Lizenz). "
                "Ein Backup ist ein integritätsgesichertes ZIP (Manifest + SHA-256).</p>"
                "<form method='post' action='/backup_create' style='margin-bottom:1rem'>"
                "<input name='label' placeholder='Label (optional)' style='width:200px'> "
                "<input name='note' placeholder='Notiz (optional)' style='width:240px'> "
                "<button type='submit' class='btn'>Jetzt Backup erstellen</button></form>"
                "<table><thead><tr><th>Datei</th><th>Grösse</th><th>Zeit</th><th>Download</th><th>Restore</th></tr></thead>"
                f"<tbody>{rows}</tbody></table></div>"
            )
            self._send(render_page(body, lang).encode("utf-8"))
            return
        elif parsed.path == "/backup_download":
            q = parse_qs(parsed.query)
            name = q.get("name", [""])[0]
            bdir = backup_mod.BACKUP_DIR
            zpath = os.path.join(bdir, os.path.basename(name))
            if name and os.path.isfile(zpath):
                with open(zpath, "rb") as f:
                    data = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "application/zip")
                self.send_header("Content-Disposition", f'attachment; filename="{os.path.basename(zpath)}"')
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
            else:
                self._send(render_page("<div class='blocker'>✗ Backup nicht gefunden.</div>", lang).encode("utf-8"))
            return
        elif parsed.path == "/backup_restore":
            q = parse_qs(parsed.query)
            name = q.get("name", [""])[0]
            zpath = os.path.join(backup_mod.BACKUP_DIR, os.path.basename(name))
            if name and os.path.isfile(zpath):
                try:
                    n = backup_mod.restore(zpath)
                    ok, info = backup_mod.verify(zpath)
                    body = f"<div class='okbox'>✓ Wiederhergestellt: {n} Dateien. Integrität: {info}.</div>"
                except Exception as e:
                    body = f"<div class='blocker'>✗ Restore fehlgeschlagen: {html.escape(str(e))}</div>"
                self._send(render_page(body, lang).encode("utf-8"))
            else:
                self._send(render_page("<div class='blocker'>✗ Backup nicht gefunden.</div>", lang).encode("utf-8"))
            return
        elif parsed.path == "/setup":
            profil = stammdaten.load_profile() or {}
            kantone = ["AG","AI","AR","BE","BL","BS","FR","GE","GL","GR","JU","LU","NE","NW","OW","SG","SH","SO","SZ","TG","TI","UR","VD","VS","ZG","ZH"]
            opts = "".join(f"<option value='{k}' {'selected' if profil.get('kanton')==k else ''}>{k}</option>" for k in kantone)
            gewerke = ["Baumeister","Gipser","Maler","Plattenleger","Elektro","Sanitaer","Fenster/Tueren","Schreiner","Heizung/Lueftung","Sonstiges"]
            gopts = "".join(f"<option value='{g}' {'selected' if profil.get('gewerk')==g else ''}>{g}</option>" for g in gewerke)
            cur_betrieb = html.escape(str(profil.get("betrieb","") or ""))
            cur_mwst = profil.get("mwst_pct", 8.1)
            body = (
                "<div class='card' style='max-width:680px;margin:2rem auto'><h2>🚀 Ersteinrichtung (2 Minuten)</h2>"
                "<p class='meta'>DevisPro ist in 3 Schritten startklar. Alle Angaben bleiben lokal auf Ihrem Rechner.</p>"
                "<form method='post' action='/setup_save'>"
                "<h3>1 · Betrieb</h3>"
                "<label>Betriebsname<input name='betrieb' value='"+cur_betrieb+"' style='width:100%'></label><br>"
                "<label style='margin-top:.6rem;display:inline-block'>Gewerk<select name='gewerk'>"+gopts+"</select></label> "
                "<label style='margin-top:.6rem;display:inline-block'>Kanton<select name='kanton'>"+opts+"</select></label> "
                "<label style='margin-top:.6rem;display:inline-block'>MWST %<input name='mwst' value='"+str(cur_mwst)+"' style='width:80px'></label>"
                "<h3 style='margin-top:1rem'>2 · Richtpreise</h3>"
                "<p class='meta'>Laden Sie Ihre Richtpreis-CSV hoch (Spalten: artikel_id;bezeichnung;einheit;ep_chf;kategorie) – optional, kann später ergänzt werden.</p>"
                "<input type='file' name='preise' accept='.csv' style='margin:.4rem 0'>"
                "<h3 style='margin-top:1rem'>3 · Loslegen</h3>"
                "<button type='submit' class='btn'>Einrichtung abschliessen</button>"
                "</form></div>"
            )
            self._send(render_page(body, lang).encode("utf-8"))
            return
        elif parsed.path == "/diagnose":
            report = diag_mod.selfcheck()
            body = diag_mod.to_html(report)
            self._send(render_page(body, lang).encode("utf-8"))
            return
        elif parsed.path == "/devis_connector":
            q = parse_qs(parsed.query)
            did = q.get("id", [None])[0]
            ziel = q.get("ziel", [None])[0]
            if not did or not history_mod.exists(did):
                self._send(render_page("<div class='blocker'>✗ Devis nicht gefunden.</div>", lang).encode("utf-8"))
                return
            if not (abo_mod.darf("connector_abacus") or abo_mod.darf("connector_proffix") or abo_mod.darf("alle_formate")):
                self._send(render_page(f"<div class='blocker'>✗ Connector nur im Tarif Premium / Vollversion.</div>", lang).encode("utf-8"))
                return
            # System-Auswahl anzeigen, wenn kein ziel gewaehlt
            if not ziel:
                sys_rows = ""
                for s in accounting_mod.liste():
                    sys_rows += (
                        f"<tr><td><b>{html.escape(s['name'])}</b></td>"
                        f"<td class='meta'>{html.escape(s['land'])}</td>"
                        f"<td class='meta'>{html.escape(s['beschreibung'])}</td>"
                        f"<td style='display:flex;gap:.3rem'>"
                        f"<a class='btn-sm' href='/devis_connector?id={html.escape(str(did))}&ziel={s['id']}'>⇩ Export</a>"
                        + ("<span class='meta'>↺ Rück-Import</span>" if s["reverse"] else "")
                        + "</td></tr>"
                    )
                body = (
                    "<div class='card'><h2>🔌 Buchhaltungs-Integrationen</h2>"
                    f"<p class='meta'>Devis <b>{html.escape(str(did))}</b> in das Buchhaltungssystem des KMU "
                    "übertragen (Export) – oder Offerten/Rechnungen aus dem System zurücklesen (Rück-Import). "
                    "DevisPro bricht Lock-in: Ihre Daten gehören Ihnen.</p>"
                    "<table style='margin-top:.6rem'><thead><tr><th>System</th><th>Land</th>"
                    "<th>Format</th><th>Aktion</th></tr></thead>"
                    f"<tbody>{sys_rows}</tbody></table>"
                    "<p class='meta' style='margin-top:1rem'>Unterstützt: Abacus, Proffix, BMD, DATEV, Banana, "
                    "SAP, Lexoffice, SevDesk, WinOffice, RamCO, Mobit, Kleinvieh, generisches CSV. "
                    "Rück-Import (Offerte/Rechnung aus Buchhaltung → Devis) für Abacus/Proffix/CSV.</p></div>"
                )
                self._send(render_page(body, lang).encode("utf-8"))
                return
            try:
                devis = crb.parse(history_mod.path_of(did, "bepreist.sia"))
                profil = stammdaten.load_profile() or {}
                beleg = q.get("beleg", [f"D-{did[-4:]}"])[0] or f"D-{did[-4:]}"
                datum = q.get("datum", [devis.meta.get("date", "")] [0]) or devis.meta.get("date", "")
                konto = q.get("konto", ["3200"])[0] or "3200"
                data = accounting_mod.export(ziel, devis, profil, beleg, datum, konto)
                fn = accounting_mod.dateiname(ziel, beleg)
                self.send_response(200)
                self.send_header("Content-Type", "text/csv; charset=utf-8")
                self.send_header("Content-Disposition", f'attachment; filename="{fn}"')
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
                return
            except Exception as e:
                self._send(render_page(f"<div class='blocker'>✗ Fehler: {html.escape(str(e))}</div>", lang).encode("utf-8"))
            return
        elif parsed.path == "/devis_mahnung":
            q = parse_qs(parsed.query)
            did = q.get("id", [None])[0]
            stufe = int(q.get("stufe", ["1"])[0] or "1")
            if not did or not history_mod.exists(did):
                self._send(render_page("<div class='blocker'>✗ Devis nicht gefunden.</div>", lang).encode("utf-8"))
                return
            if not abo_mod.darf("mahnung"):
                self._send(render_page("<div class='blocker'>✗ Mahnwesen nur im Tarif Premium / Vollversion.</div>", lang).encode("utf-8"))
                return
            try:
                devis = crb.parse(history_mod.path_of(did, "bepreist.sia"))
                profil = stammdaten.load_profile() or {}
                rnr = q.get("rnr", [f"R-{did[-4:]}"])[0] or f"R-{did[-4:]}"
                datum = q.get("datum", [devis.meta.get("date", "")] [0]) or devis.meta.get("date", "")
                faellig = q.get("faellig", [""])[0] or ""
                r = rechnung_mod.from_devis(devis, profil, rnr, datum, faellig)
                m = mahnung_mod.berechnen(r, stufe, datum, zins_pct=float(profil.get("zins_pct", 5.0) or 5.0))
                as_pdf = q.get("pdf", ["0"])[0] in ("1", "on", "true")
                if as_pdf:
                    data = mahnung_mod.build_pdf(m, lang)
                    history_mod.save_doc(did, f"mahnung_{stufe}", data, "pdf")
                    self.send_response(200)
                    self.send_header("Content-Type", "application/pdf")
                    self.send_header("Content-Disposition", f'attachment; filename="{did}_mahnung_{stufe}.pdf"')
                    self.send_header("Content-Length", str(len(data)))
                    self.end_headers()
                    self.wfile.write(data)
                    return
                html_doc = mahnung_mod.build_html(m, lang)
                self._send(html_doc.encode("utf-8"), "text/html; charset=utf-8")
            except Exception as e:
                self._send(render_page(f"<div class='blocker'>✗ Fehler: {html.escape(str(e))}</div>", lang).encode("utf-8"))
            return
        elif parsed.path == "/abo":
            info = abo_mod.info()
            feats = "".join(f"<li>✓ {html.escape(str(f))}</li>" for f in info["features"])
            blocks = "".join(
                f"<div class='tarif'><h3>{t['name']}</h3><div class='preis'>{t['preis_chf']} CHF / {t['intervall']}</div></div>"
                for t in abo_mod.TARIFE.values()
            )
            body = (f"<h1>Abo &amp; Tarife</h1>"
                    f"<div class='warn'>Aktiver Tarif: <b>{html.escape(str(info['name']))}</b> "
                    f"({info['preis_chf']} CHF / {info['intervall']})</div>"
                    f"<h2>Verfügbare Features</h2><ul>{feats}</ul>"
                    f"<h2>Tarifstufen</h2><div class='tarife'>{blocks}</div>")
            self._send(render_page(body, lang).encode("utf-8"))
            return
        elif parsed.path == "/admin_white_label":
            # nur fuer Admins sichtbar (gleicher Guard wie andere Admin-Routen)
            tok = self.headers.get("Cookie", "").split("adminsess=")[-1].split(";")[0]
            if not auth.session_gueltig(tok):
                self._send(render_admin_login(fehler="Bitte zuerst einloggen.", lang=lang).encode("utf-8"))
                return
            try:
                branding = whitelabel_mod.branding_laden()
                codes = whitelabel_mod.codes_liste()
                crows = ""
                for e in codes:
                    status = "eingeloest" if e.get("eingeloest") else "frei"
                    crows += (f"<tr><td><code>{html.escape(e['code'])}</code></td>"
                              f"<td>{html.escape(e.get('tarif',''))}</td>"
                              f"<td>{html.escape(e.get('verband',''))}</td><td>{status}</td></tr>")
                body = (f"<h1>White-Label &amp; Verbands-Lizenzen</h1>"
                        f"<form method='post' action='/admin_white_label' style='margin-bottom:1.4rem'>"
                        f"<h3 style='font-size:1rem'>Branding</h3>"
                        f"<input type='text' name='firma' value='{html.escape(branding.get('firma',''))}' placeholder='Verbandsname'>"
                        f"<input type='text' name='farbe' value='{html.escape(branding.get('farbe','#15803d'))}' placeholder='#15803d' style='width:110px'>"
                        f"<input type='text' name='logo' value='{html.escape(branding.get('logo',''))}' placeholder='Logo-Pfad (optional)'>"
                        f"<button type='submit' name='aktion' value='branding'>Branding speichern</button>"
                        f"<h3 style='font-size:1rem;margin-top:1rem'>Bulk-Lizenzcodes erzeugen</h3>"
                        f"<input type='text' name='verband' placeholder='Verband'>"
                        f"<label>Tarif: <select name='tarif'><option value='pro'>Pro</option><option value='premium'>Premium</option><option value='starter'>Starter</option></select></label>"
                        f"<label>Anzahl: <input type='number' name='anzahl' value='5' style='width:80px' min='1' max='200'></label>"
                        f"<button type='submit' name='aktion' value='codes'>Codes erzeugen</button>"
                        f"</form>"
                        f"<h2>Erzeugte Codes ({len(codes)})</h2>"
                        f"<table class='t'><tr><th>Code</th><th>Tarif</th><th>Verband</th><th>Status</th></tr>{crows}</table>"
                        f"<p class='meta'>Codes sind HMAC-signiert. Einloesen via abo.setze_tarif() – "
                        f" Mitglieder erhalten Pro/Premium-Features (inkl. ERP-Connector, Mahnung, QR).</p>")
                self._send(render_page(body, lang).encode("utf-8"))
            except Exception as e:
                self._send(render_page(f"<div class='blocker'>✗ Fehler: {html.escape(str(e))}</div>", lang).encode("utf-8"))
            return
        elif parsed.path == "/benchmark":
            # Premium-Netzwerk: Marktpreis-Benchmark Uebersicht
            from devispro import benchmark as bench_mod
            try:
                ns = bench_mod.network_stats(kanton=(stammdaten.load_profile() or {}).get("kanton"))
            except Exception:
                ns = {"gesamt_positionen": 0, "kategorien": 0, "kantone": 0, "top_beispiele": []}
            profil = stammdaten.load_profile() or {}
            kt = profil.get("kanton", "CH")
            ex_rows = "".join(
                f"<tr><td>{html.escape(str(b['kanton']))}</td><td>{html.escape(str(b['kategorie']))}</td>"
                f"<td>{html.escape(str(b['einheit']))}</td><td style='text-align:right'>{b['avg']:,.2f}</td>"
                f"<td style='text-align:right'>{b['n']}</td></tr>"
                for b in ns["top_beispiele"]) or "<tr><td colspan=5>Keine Daten</td></tr>"
            body = (
                "<div class='card'><h2>📊 Marktpreis-Benchmark-Netzwerk</h2>"
                "<p class='meta'>Anonyme, aggregierte Marktpreise aus dem DevisPro-Netzwerk. "
                "Jeder Devis speist seine bepreisten Positionen anonym ein – so sehen Sie sofort, "
                "ob Ihre Kalkulation unter oder ueber Markt liegt. Keine Kundennamen, keine Projekte.</p>"
                "<div class='kpi'>"
                f"<div><div class='v'>{ns['gesamt_positionen']:,}</div><div class='l'>eingespeiste Positionen</div></div>"
                f"<div><div class='v'>{ns['kategorien']}</div><div class='l'>Gewerke/Kategorien</div></div>"
                f"<div><div class='v'>{ns['kantone']}</div><div class='l'>Kantone abgedeckt</div></div>"
                "</div>"
                "<h3 style='margin-top:1.4rem'>Beispiel-Marktpreise (Kanton Ihrer Wahl)</h3>"
                "<table style='margin-top:.6rem'><thead><tr><th>Kanton</th><th>Kategorie</th>"
                "<th>Einheit</th><th>Ø Markt CHF</th><th>n</th></tr></thead>"
                f"<tbody>{ex_rows}</tbody></table>"
                "<p class='meta' style='margin-top:1rem'>Ihr Kanton: <b>"
                f"{html.escape(str(kt))}</b>. Beim naechsten Devis sehen Sie ▼/●/▲ pro Position im Vergleich "
                "zu diesen Marktpreisen. Premium-Kunden sehen kanton-spezifische Benchmarks.</p>"
                "<div class='save'>✓ Das Netzwerk waechst mit jedem Devis – Ihr Vorteil gegenueber starren Editoren.</div>"
                "</div>"
            )
            self._send(render_page(body, lang).encode("utf-8"))
            return
        elif parsed.path == "/vorlagen":
            # Devis-Vorlagen verwalten (wiederverwendbare Standard-Devis)
            vorl = templates_mod.liste()
            rows = ""
            if vorl:
                for v in vorl:
                    rows += (
                        "<tr>"
                        f"<td><b>{html.escape(str(v['name']))}</b></td>"
                        f"<td class='meta'>{html.escape(str(v.get('projekt') or ''))}</td>"
                        f"<td style='text-align:right'>{v.get('n_pos', 0)}</td>"
                        f"<td style='text-align:right'>{v.get('gesamt', 0):,.2f}</td>"
                        f"<td class='meta'>{html.escape(str(v.get('datum') or ''))}</td>"
                        "<td style='display:flex;gap:.3rem'>"
                        f"<form method='post' action='/vorlage_laden' style='display:inline'>"
                        f"<input type='hidden' name='name' value='{html.escape(str(v['name']))}'>"
                        f"<button type='submit' class='btn-sm'>⬇ Laden</button></form>"
                        f"<form method='post' action='/vorlage_del' style='display:inline'>"
                        f"<input type='hidden' name='name' value='{html.escape(str(v['name']))}'>"
                        f"<button type='submit' class='btn-sm alt' onclick=\"return confirm('Vorlage löschen?')\">🗑</button></form>"
                        "</td></tr>"
                    )
            else:
                rows = "<tr><td colspan=6 class='meta'>Noch keine Vorlagen gespeichert. Öffnen Sie ein Devis und klicken Sie «Als Vorlage speichern».</td></tr>"
            body = (
                "<div class='card'><h2>📋 Devis-Vorlagen</h2>"
                "<p class='meta'>Speichern Sie wiederkehrende Standard-Devis (z.B. «Badrenovation Standard», "
                "«Fassadenanstrich 2026»). Beim nächsten ähnlichen Projekt laden Sie die Vorlage – alle Positionen "
                "inkl. EP sind sofort gefüllt, nur Menge/Text anpassen.</p>"
                "<table style='margin-top:.6rem'><thead><tr><th>Name</th><th>Projekt</th>"
                "<th>Pos</th><th>Gesamt CHF</th><th>Datum</th><th>Aktion</th></tr></thead>"
                f"<tbody>{rows}</tbody></table>"
                "<p class='meta' style='margin-top:1rem'>Tipp: Eine Vorlage wird aus einem bestehenden, bepreisten "
                "Devis erstellt – öffnen Sie es und nutzen Sie «Als Vorlage speichern».</p>"
                "</div>"
            )
            self._send(render_page(body, lang).encode("utf-8"))
            return
        elif parsed.path == "/devis_vorlage_form":
            # Form: Devis als Vorlage speichern (Name eingeben)
            q = parse_qs(parsed.query)
            did = q.get("id", [None])[0]
            body = (
                "<div class='card'><h2>📋 Devis als Vorlage speichern</h2>"
                f"<p class='meta'>Devis <b>{html.escape(str(did))}</b> als wiederverwendbare Standard-Vorlage sichern.</p>"
                "<form method='post' action='/vorlage_speichern'>"
                f"<input type='hidden' name='id' value='{html.escape(str(did))}'>"
                "<label>Vorlagenname<br><input type='text' name='name' placeholder='z.B. Badrenovation Standard' "
                "required style='width:280px;padding:.4rem'></label><br>"
                "<button type='submit' class='btn' style='margin-top:.6rem'>Speichern</button>"
                "</form></div>"
            )
            self._send(render_page(body, lang).encode("utf-8"))
            return
        elif parsed.path == "/wiederkehrend":
            # Wiederkehrende Rechnungen (Vertraege / Service-Abo)
            vertraege = recurring_mod.liste()
            faellig = recurring_mod.faellige_heute()
            faellig_hinw = ""
            if faellig:
                faellig_hinw = ("<div class='save'>⏰ <b>%d Rechnung(en) faellig</b> – unten mit «Rechnung erzeugen» "
                                "erstellen (Swiss-QR inklusive).</div>" % len(faellig))
            rows = ""
            if vertraege:
                for v in vertraege:
                    status = "aktiv" if v.get("aktiv", True) else "beendet"
                    bemerk = " (beendet)" if not v.get("aktiv", True) else ""
                    rows += (
                        "<tr>"
                        f"<td><b>{html.escape(str(v['name']))}</b>{bemerk}</td>"
                        f"<td>{html.escape(str(v.get('kunde') or ''))}</td>"
                        f"<td style='text-align:right'>{v.get('betrag', 0):,.2f}</td>"
                        f"<td>{html.escape(str(v.get('intervall') or ''))}</td>"
                        f"<td style='text-align:right'>{v.get('naechste', '')}</td>"
                        f"<td style='display:flex;gap:.3rem'>"
                        f"<form method='post' action='/wr_rechnung' style='display:inline'>"
                        f"<input type='hidden' name='name' value='{html.escape(str(v['name']))}'>"
                        f"<button type='submit' class='btn-sm'>🧾 Rechnung</button></form>"
                        f"<form method='post' action='/wr_del' style='display:inline'>"
                        f"<input type='hidden' name='name' value='{html.escape(str(v['name']))}'>"
                        f"<button type='submit' class='btn-sm alt' onclick=\"return confirm('Vertrag löschen?')\">🗑</button></form>"
                        "</td></tr>"
                    )
            else:
                rows = "<tr><td colspan=6 class='meta'>Noch keine Verträge. Legen Sie unten den ersten an.</td></tr>"
            body = (
                "<div class='card'><h2>🔁 Wiederkehrende Rechnungen</h2>"
                "<p class='meta'>Service-, Wartungs- oder Mietverträge zentral verwalten. DevisPro erinnert an "
                "fällige Zyklen und erzeugt die Rechnung (mit Swiss-QR) auf Knopfdruck – vollständig lokal, "
                "ohne Cloud-Zwang.</p>"
                f"{faellig_hinw}"
                "<table style='margin-top:.6rem'><thead><tr><th>Vertrag</th><th>Kunde</th>"
                "<th>Betrag CHF</th><th>Intervall</th><th>Nächste</th><th>Aktion</th></tr></thead>"
                f"<tbody>{rows}</tbody></table></div>"
                "<div class='card' style='margin-top:1.2rem'><h3>➕ Neuen Vertrag anlegen</h3>"
                "<form method='post' action='/wr_anlegen' style='display:flex;flex-wrap:wrap;gap:.5rem;align-items:flex-end'>"
                "<label>Name<br><input name='name' placeholder='z.B. Wartung Müller' required style='width:180px'></label>"
                "<label>Kunde<br><input name='kunde' placeholder='Firma/Person' style='width:180px'></label>"
                "<label>Betrag (CHF)<br><input name='betrag' type='number' step='0.01' min='0' placeholder='390.00' required style='width:110px'></label>"
                "<label>Intervall<br><select name='intervall'>"
                "<option value='monatlich'>monatlich</option>"
                "<option value='quartalsweise'>quartalsweise</option>"
                "<option value='halbjaehrlich'>halbjährlich</option>"
                "<option value='jaehrlich'>jährlich</option></select></label>"
                "<label>Start (JJJJ-MM-TT)<br><input name='start' type='date' style='width:150px'></label>"
                "<label>Ende (optional)<br><input name='ende' type='date' style='width:150px'></label>"
                "<label>Bemerkung<br><input name='notiz' placeholder='Leistung' style='width:200px'></label>"
                "<button type='submit' class='btn'>Anlegen</button>"
                "</form></div>"
            )
            self._send(render_page(body, lang).encode("utf-8"))
            return
        elif parsed.path == "/wr_datei":
            q = parse_qs(parsed.query)
            fn = (q.get("f", [None])[0] or "").strip()
            fn = os.path.basename(fn)
            base = os.path.join(DATA, "wiederkehrend_rechnungen")
            p = os.path.join(base, fn)
            if not fn or not os.path.exists(p):
                self._send(b"Datei nicht gefunden", "text/plain; charset=utf-8")
                return
            with open(p, "rb") as f:
                data = f.read()
            ctype = "application/pdf" if fn.endswith(".pdf") else "text/html; charset=utf-8"
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return
        elif parsed.path == "/team":
            # Team-Verwaltung: nur Rolle admin
            tok = self.headers.get("Cookie", "").split("teamsess=")[-1].split(";")[0]
            ben = team_mod.token_gueltig(tok)
            if team_mod.rolle_von(ben) != "admin":
                self._send(render_page(
                    "<div class='blocker'>🔒 <b>Zugriff nur für Admin.</b> Bitte als Team-Admin anmelden.</div>",
                    lang).encode("utf-8"))
                return
            mitgl = team_mod.liste()
            rows = ""
            if mitgl:
                for m in mitgl:
                    rows += (
                        "<tr>"
                        f"<td><b>{html.escape(str(m['benutzer']))}</b></td>"
                        f"<td>{html.escape(str(m['rolle']))}</td>"
                        f"<td>{'aktiv' if m.get('aktiv', True) else 'inaktiv'}</td>"
                        f"<td style='display:flex;gap:.3rem'>"
                        f"<form method='post' action='/team_del' style='display:inline'>"
                        f"<input type='hidden' name='benutzer' value='{html.escape(str(m['benutzer']))}'>"
                        f"<button type='submit' class='btn-sm alt' onclick=\"return confirm('Löschen?')\">🗑</button></form>"
                        "</td></tr>"
                    )
            else:
                rows = "<tr><td colspan=4 class='meta'>Noch keine Mitarbeiter angelegt.</td></tr>"
            body = (
                "<div class='card'><h2>👥 Team &amp; Rollen</h2>"
                f"<p class='meta'>Angemeldet als <b>{html.escape(str(ben))}</b> (Admin). "
                "Rollen: <b>admin</b> (voller Zugriff + Freigabe), <b>büro</b> (Offerten/Rechnungen/Freigabe), "
                "<b>aussendienst</b> (nur erfassen/bepreisen, keine Freigabe).</p>"
                "<table style='margin-top:.6rem'><thead><tr><th>Benutzer</th><th>Rolle</th>"
                "<th>Status</th><th>Aktion</th></tr></thead>"
                f"<tbody>{rows}</tbody></table>"
                "<div class='card' style='margin-top:1.2rem'><h3>➕ Mitarbeiter anlegen</h3>"
                "<form method='post' action='/team_anlegen' style='display:flex;flex-wrap:wrap;gap:.5rem;align-items:flex-end'>"
                "<label>Benutzer<br><input name='benutzer' required style='width:160px'></label>"
                "<label>Passwort (≥6)<br><input name='pw' type='password' required style='width:140px'></label>"
                "<label>Rolle<br><select name='rolle'>"
                "<option value='aussendienst'>Aussendienst</option>"
                "<option value='buero'>Büro</option>"
                "<option value='admin'>Admin</option></select></label>"
                "<button type='submit' class='btn'>Anlegen</button></form></div>"
                "<p class='meta' style='margin-top:1rem'>Hinweis: Die Fachkraft-Freigabe (Review-Blocker) "
                "ist auf Admin/Büro beschränkt – Aussendienst kann Devis erfassen, aber nicht freigeben.</p>"
                "</div>"
            )
            self._send(render_page(body, lang).encode("utf-8"))
            return
        elif parsed.path == "/team_login":
            body = (
                "<div class='card' style='max-width:420px;margin:3rem auto'><h2>👥 Team-Anmeldung</h2>"
                "<form method='post' action='/team_login'>"
                "<label>Benutzer</label><input name='benutzer' style='width:100%' autofocus>"
                "<label style='margin-top:.6rem'>Passwort</label><input name='pw' type='password' style='width:100%'>"
                "<button type='submit' style='margin-top:1rem'>Anmelden</button></form>"
                "<p class='meta'><a href='/'>← Zurück</a></p></div>"
            )
            self._send(render_page(body, lang).encode("utf-8"))
            return
        elif parsed.path == "/sync":
            # Team-Sync: Rolle admin/buero
            tok = self.headers.get("Cookie", "").split("teamsess=")[-1].split(";")[0]
            ben = team_mod.token_gueltig(tok)
            if team_mod.rolle_von(ben) not in ("admin", "buero"):
                self._send(render_page(
                    "<div class='blocker'>🔒 <b>Zugriff nur für Admin/Büro.</b> Bitte als berechtigter Benutzer anmelden.</div>",
                    lang).encode("utf-8"))
                return
            last = sync_mod.last_sync()
            last_txt = last["at"] if last else "noch kein Sync"
            body = (
                "<div class='card'><h2>🔄 Team-Sync (offline-first)</h2>"
                f"<p class='meta'>Angemeldet als <b>{html.escape(str(ben))}</b>. "
                "Letzter Sync: <b>{html.escape(str(last_txt))}</b></p>"
                "<p class='meta'>DevisPro ist bewusst <b>KMU-lokal</b> – kein Cloud-Zwang. Der Sync "
                "gleicht Daten zwischen Geräten ab (Preise, Vorlagen, wiederkehrende Rechnungen, "
                "Devis-Verlauf, Team). Strategie: <b>Last-Write-Wins</b> pro Datei/Devis.</p>"
                "<div style='display:flex;flex-wrap:wrap;gap:1rem;margin-top:1rem'>"
                "<div class='card' style='flex:1;min-width:240px'>"
                "<h3>📦 Export auf Datenträger</h3>"
                "<p class='meta'>Erzeugt <code>devispro_sync.zip</code> (mit Manifest). Auf USB-Stick / "
                "geteilten Ordner kopieren und am Ziel-PC importieren.</p>"
                "<form method='post' action='/sync_export'><button type='submit' class='btn'>Bundle erzeugen</button></form>"
                "</div>"
                "<div class='card' style='flex:1;min-width:240px'>"
                "<h3>📥 Import vom Datenträger</h3>"
                "<p class='meta'>Bundle auswählen (vom Buero-PC exportiert). Überschreibt nur ältere Stände.</p>"
                "<form method='post' action='/sync_import' enctype='multipart/form-data'>"
                "<input type='file' name='bundle' accept='.zip' required><br>"
                "<button type='submit' class='btn' style='margin-top:.5rem'>Importieren</button></form>"
                "</div></div>"
                "<div class='card' style='margin-top:1rem'>"
                "<h3>🌐 LAN-Sync (optional)</h3>"
                "<p class='meta'>Im Buero einmal ein Token erzeugen; Aussendienst-PCs holen den Stand per Token "
                "vom Buero-PC (solange dieser läuft).</p>"
                "<form method='post' action='/sync_token' style='display:inline'><button type='submit' class='btn-sm'>Token erzeugen</button></form> "
                "<form method='post' action='/sync_pull' style='display:inline;margin-left:.5rem'>"
                "<input name='token' placeholder='Token' style='width:200px'> "
                "<button type='submit' class='btn-sm'>Vom Buero holen</button></form>"
                "</div>"
                "</div>"
            )
            self._send(render_page(body, lang).encode("utf-8"))
            return
        elif parsed.path == "/sync_export":
            tok = self.headers.get("Cookie", "").split("teamsess=")[-1].split(";")[0]
            ben = team_mod.token_gueltig(tok)
            if team_mod.rolle_von(ben) not in ("admin", "buero"):
                self._send(render_page("<div class='blocker'>🔒 Nur Admin/Büro dürfen exportieren.</div>", lang).encode("utf-8"))
                return
            try:
                zp = sync_mod.build_bundle(DATA)
                with open(zp, "rb") as f:
                    data = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "application/zip")
                self.send_header("Content-Disposition", 'attachment; filename="devispro_sync.zip"')
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
            except Exception as e:
                self._send(render_page(f"<div class='blocker'>✗ Export fehlgeschlagen: {html.escape(str(e))}</div>", lang).encode("utf-8"))
            return
        elif parsed.path == "/sync_bundle":
            q = parse_qs(parsed.query)
            token = (q.get("token", [""])[0] or "").strip()
            if not sync_mod.sync_token_gueltig(token, DATA):
                self._send(b"forbidden", "text/plain; charset=utf-8")
                return
            try:
                zp = sync_mod.build_bundle(DATA)
                with open(zp, "rb") as f:
                    data = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "application/zip")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
            except Exception:
                self._send(b"error", "text/plain; charset=utf-8")
            return
        elif parsed.path == "/admin_funnel":
            tok = self.headers.get("Cookie", "").split("adminsess=")[-1].split(";")[0]
            if not auth.session_gueltig(tok):
                self._send(render_admin_login("Bitte zuerst einloggen.").encode("utf-8"))
                return
            from devispro import lead_magnet as lead_mod
            fs = lead_mod.funnel_stats()
            krows = "".join(f"<tr><td>{html.escape(str(k))}</td><td style='text-align:right'>{n}</td></tr>"
                            for k, n in fs["kantone"]) or "<tr><td colspan=2>keine Daten</td></tr>"
            body = (
                "<div class='card'><h2>📈 Funnel &amp; Leads</h2>"
                "<div class='kpi'>"
                f"<div><div class='v'>{fs['checks']}</div><div class='l'>Devis-Checks</div></div>"
                f"<div><div class='v'>{fs['trials']}</div><div class='l'>Probe-Kunden</div></div>"
                "</div>"
                "<h3 style='margin-top:1.2rem'>Top-Kantone (Leads)</h3>"
                "<table style='margin-top:.4rem'><thead><tr><th>Kanton</th><th>Leads</th></tr></thead>"
                f"<tbody>{krows}</tbody></table>"
                "<p class='meta' style='margin-top:1rem'>Quelle: data/trial_leads.log (JSON-Lines). "
                "Jeder Devis-Check ohne Login wird protokolliert – so ist der Funnel messbar.</p>"
                "</div>"
            )
            self._send(render_page(body, lang).encode("utf-8"))
            return
        elif parsed.path == "/devis_qr":
            q = parse_qs(parsed.query)
            did = q.get("id", [None])[0]
            if not did or not history_mod.exists(did):
                self._send(b"Devis nicht gefunden", "text/plain; charset=utf-8")
                return
            try:
                devis = crb.parse(history_mod.path_of(did, "bepreist.sia"))
                profil = stammdaten.load_profile() or {}
                rnr = q.get("rnr", [f"R-{did[-4:]}"])[0] or f"R-{did[-4:]}"
                datum = q.get("datum", [devis.meta.get("date", "")] [0]) or devis.meta.get("date", "")
                faellig = q.get("faellig", [""])[0] or ""
                r = rechnung_mod.from_devis(devis, profil, rnr, datum, faellig)
                from devispro import qr_rechnung as qr_mod
                from devispro import qr_render as QR
                matrix, _ = qr_mod.qr_matrix_aus_rechnung(r)
                png = QR.to_png_bytes(matrix, scale=6)
                self.send_response(200)
                self.send_header("Content-Type", "image/png")
                self.send_header("Content-Length", str(len(png)))
                self.end_headers()
                self.wfile.write(png)
                return
            except Exception as e:
                self._send(render_page(f"<div class='blocker'>✗ Fehler: {html.escape(str(e))}</div>", lang).encode("utf-8"))
            return
        elif parsed.path == "/devis_doc_file":
            q = parse_qs(parsed.query)
            did = q.get("id", [None])[0]
            typ = q.get("typ", [None])[0]
            if not did or not typ or not history_mod.exists(did):
                self._send(b"Datei nicht gefunden", "text/plain; charset=utf-8")
                return
            p = history_mod.path_of(did, f"{typ}.pdf")
            is_pdf = os.path.exists(p)
            if not is_pdf:
                p = history_mod.path_of(did, f"{typ}.html")
            if not os.path.exists(p):
                self._send(b"Datei nicht gefunden", "text/plain; charset=utf-8")
                return
            with open(p, "rb") as f:
                data = f.read()
            ctype = "application/pdf" if is_pdf else "text/html; charset=utf-8"
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Disposition", f'inline; filename="{did}_{typ}.{"pdf" if is_pdf else "html"}"')
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return
        elif parsed.path == "/devis_lifecycle":
            q = parse_qs(parsed.query)
            did = q.get("id", [None])[0]
            if not did or not history_mod.exists(did):
                self._send(render_page("<div class='blocker'>Devis nicht gefunden</div>", lang).encode("utf-8"))
                return
            try:
                ov = lifecycle_mod.overview(did)
                cards = ""
                for st in ov["stages"]:
                    cls = "stage done" if st["present"] else "stage"
                    link = f"<a class='btn-sm' href='{st['link']}'>Ansehen</a>" if st["present"] else "<span class='muted'>offen</span>"
                    cards += (f"<div class='{cls}'><div class='stagenum'>{st['label']}</div>"
                              f"<div class='stagedesc'>{st['desc']}</div><div>{link}</div></div>")
                ges = f"{ov['gesamtbetrag']:.2f} CHF" if ov.get("gesamtbetrag") else "–"
                body = (f"<h1>Lebenszyklus &middot; {html.escape(str(ov['projekt']))}</h1>"
                        f"<div class='warn'>Projekt-ID: <b>{html.escape(did)}</b> &nbsp;|&nbsp; "
                        f"Gesamtvolumen: <b>{ges}</b></div>"
                        f"<div class='stages'>{cards}</div>"
                        f"<p><a class='btn' href='/devis_offerte?id={did}'>Offerte/PDF</a> "
                        f"<a class='btn' href='/devis_rechnung?id={did}'>Rechnung + QR</a> "
                        f"<a class='btn' href='/devis_connector?id={did}&ziel=abacus'>ERP-Export</a></p>")
                self._send(render_page(body, lang).encode("utf-8"))
            except Exception as e:
                self._send(render_page(f"<div class='blocker'>✗ Fehler: {html.escape(str(e))}</div>", lang).encode("utf-8"))
            return
        elif parsed.path.startswith("/lang/"):
            new_lang = parsed.path.split("/lang/", 1)[-1].split("/")[0]
            if new_lang not in LANGS:
                new_lang = "de"
            # zurueck zur vorherigen Seite (Referer) oder Start
            ref = self.headers.get("Referer", "/")
            self.send_response(303)
            self.send_header("Location", ref)
            self.send_header("Set-Cookie", f"lang={new_lang}; Path=/")
            self.end_headers()
            return
        elif parsed.path == "/favicon.ico":
            self._send(b"", "text/plain")
        else:
            self._send(render_index(self).encode("utf-8"))

    def do_POST(self):
        parsed = urlparse(self.path)
        lang = lang_from_request(self)
        if parsed.path == "/check":
            fn, raw = _parse_multipart_file(self, "devis")
            if not raw:
                self._send(render_page("<div class='blocker'>✗ Keine Datei empfangen.</div>", lang).encode("utf-8"))
                return
            fn = os.path.basename(fn or "devis.sia")
            tmp = os.path.join(DATA, "_check_" + fn.replace("/", "_"))
            open(tmp, "wb").write(raw)
            try:
                from devispro import lead_magnet as lead_mod
                res = lead_mod.analyze(tmp)
                import json as _json
                res_name = "_checkres_" + fn.replace("/", "_") + ".json"
                _json.dump(res, open(os.path.join(DATA, res_name), "w"), default=str)
                os.remove(tmp)
                loc = f"/check?r=1&f={quote(res_name)}"
                self.send_response(303)
                self.send_header("Location", loc)
                self.end_headers()
                return
            except Exception as e:
                self._send(render_page(f"<div class='blocker'>✗ Check fehlgeschlagen: {html.escape(str(e))}</div>", lang).encode("utf-8"))
                return
        if parsed.path == "/check_lead":
            # Lead aus dem Devis-Check (Funnel-Messung) + Weiterleitung zu /trial
            form = self._fieldstorage()
            email = (form.getvalue("email") or "").strip()
            projekt = (form.getvalue("projekt") or "").strip()
            try:
                from devispro import lead_magnet as lead_mod
                lead_mod.log_check_lead(email, projekt=projekt)
            except Exception:
                pass
            # 1-Klick: E-Mail + Projekt ins Trial-Formular vorausfuellen
            q = urlencode({"email": email, "projekt": projekt})
            self.send_response(303)
            self.send_header("Location", f"/trial?{q}")
            self.end_headers()
            return
        if parsed.path == "/admin_white_label":
            form = self._fieldstorage()
            aktion = form.getvalue("aktion", "")
            try:
                if aktion == "branding":
                    firma = form.getvalue("firma", "") or "DevisPro"
                    farbe = form.getvalue("farbe", "") or "#15803d"
                    logo = form.getvalue("logo", "") or ""
                    whitelabel_mod.branding_setzen(firma, logo, farbe)
                elif aktion == "codes":
                    verband = form.getvalue("verband", "") or ""
                    tarif = form.getvalue("tarif", "pro") or "pro"
                    try:
                        anzahl = int(form.getvalue("anzahl", "5") or "5")
                    except Exception:
                        anzahl = 5
                    anzahl = max(1, min(200, anzahl))
                    wl = whitelabel_mod.code_erzeugen(tarif, verband, anzahl)
                    self.send_response(200)
                    self.send_header("Content-Type", "text/plain; charset=utf-8")
                    self.end_headers()
                    self.wfile.write(("\n".join(wl)).encode("utf-8"))
                    return
            except Exception as e:
                self._send(render_page(f"<div class='blocker'>✗ Fehler: {html.escape(str(e))}</div>", lang).encode("utf-8"))
                return
            self.send_response(303)
            self.send_header("Location", "/admin_white_label")
            self.end_headers()
            return
        if parsed.path == "/import_devis":
            form = self._fieldstorage()
            up = form["file"] if "file" in form else None
            if up is None or not getattr(up, "filename", ""):
                self._send(render_page("<div class='blocker'>✗ Keine Datei empfangen.</div>", lang).encode("utf-8"))
                return
            fn = os.path.basename(up.filename)
            raw = up.file.read() if hasattr(up, "file") else getattr(up, "value", b"")
            tmp = os.path.join(DATA, "_import_" + fn.replace("/", "_"))
            open(tmp, "wb").write(raw)
            try:
                from devispro import importers
                devis = importers.import_devis(tmp)
                # bepreisen via Mock-Matcher gegen gespeicherte Preise
                from devispro import pricelist as pl_mod, matcher as mat_mod
                preise = pl_mod.load(os.path.join(DATA, "meine_preise.csv"))
                m = mat_mod.Matcher(method="mock", threshold=0.6)
                preisliste = {p.artikel_id: p for p in preise}
                for pos in devis.positions:
                    r = m.match(pos, list(preisliste.values()))
                    pos.matched_artikel = r.matched_artikel_id
                    pos.confidence = r.confidence
                    pos.requires_review = r.requires_review
                    if r.matched_artikel_id and preisliste.get(r.matched_artikel_id):
                        pos.ep = preisliste[r.matched_artikel_id].ep_chf
                        pos.fill()
                netto = sum((pos.betrag or 0) for pos in devis.positions)
                profil = stammdaten.load_profile() or {}
                did = history_mod.save(devis, netto,
                                       name=devis.meta.get("projekt", "Import"),
                                       method="mock",
                                       kanton=profil.get("kanton", "ZH"))
                # Anonymen Benchmark speisen (Netzwerkeffekt, kanton-spezifisch)
                try:
                    from devispro import benchmark as bench_mod
                    kton = (profil.get("kanton") or meta.get("kanton") or "CH")
                    bench_mod.contribute([
                        {"kategorie": (pos.matched_artikel or pos.text[:20]),
                         "einheit": pos.einheit, "ep": pos.ep}
                        for pos in devis.positions
                    ], kanton=kton)
                except Exception:
                    pass
                os.remove(tmp)
                self.send_response(303)
                self.send_header("Location", f"/devis/{did}?importiert=1")
                self.end_headers()
                return
            except Exception as e:
                self._send(render_page(f"<div class='blocker'>✗ Import fehlgeschlagen: {html.escape(str(e))}</div>", lang).encode("utf-8"))
                return
        if parsed.path == "/portal_import":
            form = self._fieldstorage()
            up = form["file"] if "file" in form else None
            if up is None or not getattr(up, "filename", ""):
                self._send(render_page("<div class='blocker'>✗ Keine Ausschreibungs-Datei empfangen.</div>", lang).encode("utf-8"))
                return
            fn = os.path.basename(up.filename)
            raw = up.file.read() if hasattr(up, "file") else getattr(up, "value", b"")
            tmp = os.path.join(DATA, "_portal_" + fn.replace("/", "_"))
            open(tmp, "wb").write(raw)
            try:
                from devispro import monitor as mon_mod
                from devispro import stammdaten as _sd
                profil = _sd.load_profile() or {}
                kton = profil.get("kanton", "ZH")
                stichwort = (form.getvalue("stichwort") or "").strip()
                devis, did = mon_mod.import_ausschreibung(tmp, kanton=kton, stichwort=stichwort)
                os.remove(tmp)
                self.send_response(303)
                self.send_header("Location", f"/devis/{did}?importiert=1&quelle=portal")
                self.end_headers()
                return
            except Exception as e:
                try:
                    os.remove(tmp)
                except Exception:
                    pass
                self._send(render_page(f"<div class='blocker'>✗ Portal-Import fehlgeschlagen: {html.escape(str(e))}</div>", lang).encode("utf-8"))
                return
        if parsed.path == "/learn_prices":
            form = self._fieldstorage()
            up = form["file"] if "file" in form else None
            if up is None or not getattr(up, "filename", ""):
                self._send(render_page("<div class='blocker'>✗ Keine Devis-Datei empfangen.</div>", lang).encode("utf-8"))
                return
            fn = os.path.basename(up.filename)
            raw = up.file.read() if hasattr(up, "file") else getattr(up, "value", b"")
            tmpf = os.path.join(DATA, "_learn_" + fn.replace("/", "_"))
            open(tmpf, "wb").write(raw)
            try:
                from devispro import importers, pricelist as pl_mod
                dev = importers.import_devis(tmpf)
                added = pl_mod.learn_from_devis(dev)
                os.remove(tmpf)
                body = (f"<div class='okbox'>✓ {added} Positionen aus Ihrem Devis übernommen. "
                        f"Ihre Richtpreisliste ist jetzt gefüllt – künftige Devis werden automatisch "
                        f"damit bepreist.</div>"
                        f"<p class='meta'><a class='btn-sm' href='/bepreisen'>Jetzt ein Devis bepreisen</a></p>")
                self.send_response(303)
                self.send_header("Location", f"/bepreisen?gelernt={added}")
                self.end_headers()
                return
            except Exception as e:
                try:
                    os.remove(tmpf)
                except Exception:
                    pass
                self._send(render_page(f"<div class='blocker'>✗ Lernen fehlgeschlagen: {html.escape(str(e))}</div>", lang).encode("utf-8"))
                return
        if parsed.path == "/import_foto":
            fn, raw = _parse_multipart_file(self, "foto")
            if not raw:
                self._send(render_page("<div class='blocker'>✗ Kein Foto empfangen.</div>", lang).encode("utf-8"))
                return
            fn = os.path.basename(fn or "foto.png")
            tmp = os.path.join(DATA, "_foto_" + fn.replace("/", "_"))
            open(tmp, "wb").write(raw)
            try:
                positions, meta = vision_mod.extract(tmp)
                if meta.get("ocr"):
                    from devispro import pricelist as pl_mod, matcher as mat_mod
                    preise = pl_mod.load(os.path.join(DATA, "meine_preise.csv"))
                    preisliste = {p.artikel_id: p for p in preise}
                    m = mat_mod.Matcher(method="mock", threshold=0.6)
                    devis = vision_mod.to_devis(positions)
                    for pos in devis.positions:
                        r = m.match(pos, list(preisliste.values()))
                        pos.matched_artikel = r.matched_artikel_id
                        pos.confidence = r.confidence
                        pos.requires_review = r.requires_review
                        if r.matched_artikel_id and preisliste.get(r.matched_artikel_id):
                            pos.ep = preisliste[r.matched_artikel_id].ep_chf
                            pos.fill()
                    netto = sum((pos.betrag or 0) for pos in devis.positions)
                    profil = stammdaten.load_profile() or {}
                    did = history_mod.save(devis, netto,
                                           name="Foto-Devis", method="mock",
                                           kanton=profil.get("kanton", "ZH"))
                    os.remove(tmp)
                    self.send_response(303)
                    self.send_header("Location", f"/devis/{did}?importiert=1&foto=1")
                    self.end_headers()
                    return
                else:
                    img_uri = vision_mod.image_data_uri(tmp)
                    form_html = (
                        "<div class='card'><h2>📷 Devis aus Foto – Positionen bestätigen</h2>"
                        "<p class='meta'>OCR ist auf diesem System nicht verfügbar. Bestätigen Sie die "
                        "Positionen manuell – das Devis wird sofort bepreist.</p>"
                        + (f"<img src='{img_uri}' style='max-width:100%;border:1px solid #ddd;border-radius:8px;margin:.6rem 0'>" if img_uri else "")
                        + "<form method='post' action='/import_foto_positions'>"
                    )
                    for i in range(1, 6):
                        form_html += (
                            f"<div style='display:flex;gap:.4rem;margin:.3rem 0;flex-wrap:wrap'>"
                            f"<input name='nr{i}' placeholder='Pos' style='width:3rem'>"
                            f"<input name='txt{i}' placeholder='Bezeichnung' style='flex:1;min-width:12rem'>"
                            f"<input name='mng{i}' placeholder='Menge' style='width:5rem'>"
                            f"<input name='eh{i}' placeholder='Einheit' style='width:4rem'>"
                            f"<input name='ep{i}' placeholder='EP' style='width:6rem'></div>"
                        )
                    form_html += "<button type='submit' class='btn'>Bepreisen</button></form></div>"
                    self._send(render_page(form_html, lang).encode("utf-8"))
                    return
            except Exception as e:
                self._send(render_page(f"<div class='blocker'>✗ Foto-Import fehlgeschlagen: {html.escape(str(e))}</div>", lang).encode("utf-8"))
                return
        if parsed.path == "/import_foto_positions":
            form = self._fieldstorage()
            try:
                from devispro.models import Devis, Position
                positions = []
                for i in range(1, 6):
                    nr = form.getvalue(f"nr{i}", "").strip()
                    txt = form.getvalue(f"txt{i}", "").strip()
                    if not txt:
                        continue
                    mng = form.getvalue(f"mng{i}", "1").strip()
                    eh = form.getvalue(f"eh{i}", "m2").strip()
                    ep = form.getvalue(f"ep{i}", "").strip()
                    positions.append(Position(
                        pos_nr=nr or str(i),
                        text=txt,
                        menge=float(mng) if mng else 1.0,
                        einheit=eh or "m2",
                        ep=(float(ep) if ep else None),
                    ))
                if not positions:
                    self._send(render_page("<div class='blocker'>✗ Bitte mindestens eine Position eingeben.</div>", lang).encode("utf-8"))
                    return
                from devispro import pricelist as pl_mod, matcher as mat_mod
                preise = pl_mod.load(os.path.join(DATA, "meine_preise.csv"))
                preisliste = {p.artikel_id: p for p in preise}
                m = mat_mod.Matcher(method="mock", threshold=0.6)
                for pos in positions:
                    r = m.match(pos, list(preisliste.values()))
                    pos.matched_artikel = r.matched_artikel_id
                    pos.confidence = r.confidence
                    pos.requires_review = r.requires_review
                    if r.matched_artikel_id and preisliste.get(r.matched_artikel_id):
                        pos.ep = preisliste[r.matched_artikel_id].ep_chf
                        pos.fill()
                devis = Devis(meta={"projekt": "Foto-Devis"}, addresses=[], chapters=[], positions=positions)
                netto = sum((pos.betrag or 0) for pos in positions)
                profil = stammdaten.load_profile() or {}
                did = history_mod.save(devis, netto, name="Foto-Devis", method="mock",
                                       kanton=profil.get("kanton", "ZH"))
                self.send_response(303)
                self.send_header("Location", f"/devis/{did}?importiert=1&foto=1")
                self.end_headers()
                return
            except Exception as e:
                self._send(render_page(f"<div class='blocker'>✗ Fehler: {html.escape(str(e))}</div>", lang).encode("utf-8"))
                return
        if self.path == "/ordner_import":
            form = self._fieldstorage()
            files = form["files"] if "files" in form else None
            if not isinstance(files, list):
                files = [files] if files else []
            files = [f for f in files if getattr(f, "filename", "")]
            if not files:
                self._send(render_page("<div class='blocker'>✗ Bitte mindestens eine Datei auswählen.</div>", lang).encode("utf-8"))
                return
            bepreisen = form.getvalue("bepreisen") == "1"
            tmpdir = os.path.join(DATA, "_ordner_" + str(int(time.time())))
            os.makedirs(tmpdir, exist_ok=True)
            try:
                for f in files:
                    raw = f.file.read() if hasattr(f, "file") else getattr(f, "value", b"")
                    fn = os.path.basename(f.filename or "datei")
                    open(os.path.join(tmpdir, fn), "wb").write(raw)
                devis, report = ordner_mod.analyse_ordner(tmpdir)
                if bepreisen:
                    ordner_mod.passe_an(devis)
                # bepreistes Devis speichern (wie import_devis)
                preise_csv = stammdaten.load_prices_csv()
                if preise_csv:
                    prices_path = os.path.join(DATA, "_meine_preise.csv")
                    with open(prices_path, "w", encoding="utf-8") as pf:
                        pf.write(preise_csv)
                    try:
                        prices = load_prices(prices_path)
                        matcher_m = Matcher(method="mock", threshold=0.6)
                        for p in devis.positions:
                            r = matcher_m.match(p, prices)
                            p.matched_artikel = r.matched_artikel_id
                            p.confidence = r.confidence
                            p.requires_review = r.requires_review
                            if r.matched_artikel_id and prices.get(r.matched_artikel_id):
                                p.ep = prices[r.matched_artikel_id].ep_chf
                                p.fill()
                    except Exception:
                        pass
                crb.export(devis, os.path.join(DATA, "bepreist.sia"))
                netto = sum((p.betrag or 0) for p in devis.positions)
                profil = stammdaten.load_profile() or {}
                did = history_mod.save(devis, netto, name="Ordner-Import",
                                       method="ordner", kanton=profil.get("kanton", "ZH"))
                shutil.rmtree(tmpdir, ignore_errors=True)
                self.send_response(303)
                self.send_header("Location", f"/devis/{did}?importiert=1&ordner=1")
                self.end_headers()
            except Exception as e:
                shutil.rmtree(tmpdir, ignore_errors=True)
                self._send(render_page(f"<div class='blocker'>✗ Ordner-Import fehlgeschlagen: {html.escape(str(e))}</div>", lang).encode("utf-8"))
            return
        if self.path == "/sub_setze":
            form = self._fieldstorage()
            did = (form.getvalue("id") or "").strip()
            pos = (form.getvalue("pos") or "").strip()
            firma = (form.getvalue("firma") or "").strip()
            try:
                betrag = float(form.getvalue("betrag") or 0)
            except (TypeError, ValueError):
                betrag = 0.0
            if did and pos and history_mod.exists(did):
                sub_mod.setze_offerte(did, pos, firma, betrag)
                self.send_response(303)
                self.send_header("Location", f"/subunternehmer?id={quote(did)}")
                self.end_headers()
            else:
                self._send(render_page("<div class='blocker'>✗ Fehlende Angaben.</div>", lang).encode("utf-8"))
            return
        if self.path == "/marketing_referenz":
            profil = stammdaten.load_profile() or {}
            devis_liste = []
            for did in history_mod.list_all()[:10]:
                try:
                    d = crb.parse(history_mod.path_of(did, "bepreist.sia"))
                    devis_liste.append((d, d.meta.get("project_name") or did))
                except Exception:
                    pass
            if not devis_liste:
                devis_liste = [(Devis(meta={"project_name": "Musterprojekt"}, addresses=[], chapters=[], positions=[]), "Musterprojekt")]
            data = marketing_mod.referenz_blatt_pdf(profil, devis_liste, lang)
            self.send_response(200)
            self.send_header("Content-Type", "application/pdf")
            self.send_header("Content-Disposition", 'attachment; filename="referenzen.pdf"')
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return
        if self.path == "/erp_push":
            form = self._fieldstorage()
            url = (form.getvalue("url") or "").strip()
            secret = (form.getvalue("secret") or "").strip()
            did = (form.getvalue("id") or "").strip()
            profil = stammdaten.load_profile() or {}
            if not url or not did or not history_mod.exists(did):
                self._send(render_page("<div class='blocker'>✗ ERP-URL und Devis erforderlich.</div>", lang).encode("utf-8"))
                return
            try:
                devis = crb.parse(history_mod.path_of(did, "bepreist.sia"))
                payload = erp_mod.beleg_payload(devis, profil, did, typ="ANGEBOT", konto="3200")
                ok, info = erp_mod.push(url, payload, secret)
                if ok:
                    body = f"<div class='okbox'>✓ Push an ERP erfolgreich (HTTP {info}). Beleg {html.escape(did)} übertragen.</div>"
                else:
                    body = f"<div class='blocker'>✗ Push fehlgeschlagen: {html.escape(str(info))}</div>"
                self._send(render_page(body, lang).encode("utf-8"))
            except Exception as e:
                self._send(render_page(f"<div class='blocker'>✗ Fehler: {html.escape(str(e))}</div>", lang).encode("utf-8"))
            return
        if self.path == "/agent_chat":
            form = self._fieldstorage()
            msg = (form.getvalue("msg") or "").strip()
            did = (form.getvalue("did") or "").strip()
            if not msg:
                self._send(b"Bitte eine Nachricht eingeben.")
                return
            res = agent_mod.chat(msg, {"lang": lang, "did": did or None, "data_dir": DATA})
            # bei Navigation: Location-Header als Text-Hinweis einbetten
            ans = res.get("answer", "")
            if res.get("navigate"):
                ans += f"\n\n→ {res['navigate']}"
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(ans.encode("utf-8"))
            return
        if self.path == "/backup_create":
            form = self._fieldstorage()
            label = (form.getvalue("label") or "").strip()
            note = (form.getvalue("note") or "").strip()
            try:
                zpath, man = backup_mod.create(label=label, note=note)
                self.send_response(303)
                self.send_header("Location", "/backup?created=" + quote(os.path.basename(zpath)))
                self.end_headers()
            except Exception as e:
                self._send(render_page(f"<div class='blocker'>✗ Backup fehlgeschlagen: {html.escape(str(e))}</div>", lang).encode("utf-8"))
            return
        if self.path == "/setup_save":
            form = self._fieldstorage()
            profil = stammdaten.load_profile() or {}
            profil["betrieb"] = (form.getvalue("betrieb") or "").strip()
            profil["gewerk"] = (form.getvalue("gewerk") or "").strip()
            profil["kanton"] = (form.getvalue("kanton") or "ZH").strip().upper()
            try:
                profil["mwst_pct"] = float((form.getvalue("mwst") or 8.1))
            except (TypeError, ValueError):
                profil["mwst_pct"] = 8.1
            profil["setup_done"] = True
            stammdaten.save_profile(profil)
            # Richtpreise hochladen (optional)
            up = form["preise"] if "preise" in form else None
            saved = False
            if up is not None and getattr(up, "filename", ""):
                data = up.file.read()
                if data:
                    open(os.path.join(DATA, "meine_preise.csv"), "wb").write(data)
                    saved = True
            self.send_response(303)
            self.send_header("Location", "/?setup=ok" + ("&preise=1" if saved else ""))
            self.end_headers()
            return
        if self.path == "/trial_anmelden":
            form = self._fieldstorage()
            res = lizadm.trial_anmelden({
                "firma": form.getvalue("firma", ""),
                "name": form.getvalue("name", ""),
                "email": form.getvalue("email", ""),
                "kanton": form.getvalue("kanton", ""),
                "gewerk": form.getvalue("gewerk", ""),
                "projekt": form.getvalue("projekt", ""),
                "tarif": form.getvalue("tarif", "devis"),
                "sprache": lang,
            })
            if res["ok"]:
                # Nach Anmeldung direkt in die App (Lizenz ist jetzt 90 Tage gueltig)
                self.send_response(303)
                self.send_header("Location", f"/bepreisen?lang={lang}")
                self.end_headers()
                return
            self._send(render_trial(lang, fehler=res.get("fehler", "Fehler")).encode("utf-8"))
            return
        if self.path == "/lizenz_code":
            form = self._fieldstorage()
            kid = form.getvalue("kunde_id", "KMU-001")
            code = form.getvalue("code", "")
            res = liz.code_anwenden(kid, code)
            if res["ok"]:
                body = f"<div class='okbox'>✓ Lizenz verlängert bis {res['gueltig_bis']}. "
                body += "DevisPro ist wieder freigeschaltet.</div>"
            else:
                body = f"<div class='blocker'>✗ {html.escape(res['fehler'])}</div>"
            self._send(render_page(body, lang).encode("utf-8"))
            return
        if self.path in ("/admin_freigeben", "/admin_neu", "/admin_erinnerung"):
            tok = self.headers.get("Cookie", "").split("adminsess=")[-1].split(";")[0]
            if not auth.session_gueltig(tok):
                self._send(render_admin_login("Bitte zuerst einloggen.").encode("utf-8"))
                return
        if self.path == "/admin_freigeben":
            form = self._fieldstorage()
            kid = form.getvalue("kunde_id", "")
            from devispro import license_admin as adm
            out = adm.freigeben_nach_zahlung(kid)
            body = (f"<div class='okbox'>✓ Zahlung bestätigt. Code erzeugt + "
                    f"automatisch versendet.<br>Code: <code>{out['code']}</code><br>"
                    f"Gültig bis: {out['gueltig_bis']}<br>Mail gesendet: {out['mail_gesendet']}</div>")
            self._send(render_page(body, lang).encode("utf-8"))
            return
        if self.path == "/admin_neu":
            form = self._fieldstorage()
            from devispro import license_admin as adm
            adm.kunde_anlegen(form.getvalue("kunde_id"), form.getvalue("firma"),
                              form.getvalue("email"), pilot=(form.getvalue("pilot") == "1"))
            self._send(render_admin().encode("utf-8"))
            return
        if self.path == "/admin_code":
            tok = self.headers.get("Cookie", "").split("adminsess=")[-1].split(";")[0]
            if not auth.session_gueltig(tok):
                self._send(render_admin_login("Bitte zuerst einloggen.").encode("utf-8"))
                return
            form = self._fieldstorage()
            from devispro import license_admin as adm
            kid = (form.getvalue("kunde_id") or "").strip()
            res = adm.kunden_code_export(kid)
            if res:
                body = (f"<div class='okbox'>✓ Freischaltcode für <b>{res['firma']}</b> erzeugt "
                        f"(gültig bis {res['gueltig_bis']}).<br><br>"
                        f"<code style='font-size:1.05rem;background:#fff;padding:.5rem;border:1px solid #ddd;display:block;word-break:break-all'>{res['code']}</code>"
                        f"<br><br>Diesen Code dem Kunden per E-Mail senden – er gibt ihn beim ersten "
                        f"Start unter 'Lizenz' ein.</div>")
            else:
                body = "<div class='blocker'>Kunde nicht gefunden.</div>"
            self._send(render_page(body + "\n" + render_admin(lang).split("<div class=\"card\">", 1)[-1], lang).encode("utf-8"))
            return
        if self.path == "/admin_erinnerung":
            from devispro import license_admin as adm
            faellig = adm.erinnerung_pruefen()
            body = f"<div class='okbox'>✓ Erinnerungsprüfung läuft. {len(faellig)} Kunde(n) erinnert.</div>"
            self._send(render_page(body, lang).encode("utf-8"))
            return
        if self.path == "/admin_smtp":
            tok = self.headers.get("Cookie", "").split("adminsess=")[-1].split(";")[0]
            if not auth.session_gueltig(tok):
                self._send(render_admin_login("Bitte zuerst einloggen.").encode("utf-8"))
                return
            form = self._fieldstorage()
            preset = (form.getvalue("preset") or "").strip()
            host = (form.getvalue("host") or "").strip()
            user = (form.getvalue("user") or "").strip()
            pwd = (form.getvalue("pass") or "").strip()
            port = (form.getvalue("port") or "587").strip()
            tls = (form.getvalue("tls") or "starttls").strip()
            von = (form.getvalue("von") or "").strip() or None
            try:
                port = int(port)
            except Exception:
                port = 587
            if tls not in ("starttls", "ssl", "none"):
                tls = "starttls"
            from devispro import license_admin as adm
            if preset == "hostinger":
                ok = adm.smtp_preset("hostinger", user, pwd, von=von)
                body = ("<div class='okbox'>✓ Hostinger (devispro.de) gespeichert. "
                        "Mails werden jetzt ueber smtp.hostinger.com versendet.</div>" if ok
                        else "<div class='blocker'>Hostinger-Profil unbekannt.</div>")
            elif host and user:
                adm.smtp_konfigurieren(host, user, pwd, von=von, port=port, tls=tls)
                body = "<div class='okbox'>✓ SMTP gespeichert. Mails werden jetzt automatisch versendet.</div>"
            else:
                body = "<div class='blocker'>Host und Benutzer sind erforderlich.</div>"
            msg = body + "\n"
            self._send(render_page(
                "<div class='card'>" + msg + render_admin(lang).split("<div class=\"card\">", 1)[-1],
                lang).encode("utf-8"))
            return
        if self.path == "/admin_smtp_test":
            tok = self.headers.get("Cookie", "").split("adminsess=")[-1].split(";")[0]
            if not auth.session_gueltig(tok):
                self._send(render_admin_login("Bitte zuerst einloggen.").encode("utf-8"))
                return
            form = self._fieldstorage()
            to = (form.getvalue("test_to") or "").strip()
            from devispro import license_admin as adm
            if not to:
                body = "<div class='blocker'>Test-Empfänger fehlt.</div>"
            elif not adm.SMTP["host"]:
                body = "<div class='blocker'>Kein SMTP konfiguriert. Zuerst Hostinger/SMTP speichern.</div>"
            else:
                ok = adm._mail_senden(to, "DevisPro Test-Mail",
                                      "Dies ist eine Test-Mail von DevisPro.\n\n"
                                      "Absender: %s\nHost: %s\n\nDevisPro · Monterossa AG" %
                                      (adm.SMTP["von"], adm.SMTP["host"]))
                body = ("<div class='okbox'>✓ Test-Mail an %s gesendet.</div>" % to if ok
                        else "<div class='blocker'>Versand fehlgeschlagen – Host/Passwort prüfen.</div>")
            self._send(render_page(
                "<div class='card'>" + body + render_admin(lang).split("<div class=\"card\">", 1)[-1],
                lang).encode("utf-8"))
            return
        if self.path == "/admin_werbe_mail":
            tok = self.headers.get("Cookie", "").split("adminsess=")[-1].split(";")[0]
            if not auth.session_gueltig(tok):
                self._send(render_admin_login("Bitte zuerst einloggen.").encode("utf-8"))
                return
            form = self._fieldstorage()
            empf = (form.getvalue("empfaenger") or "").strip()
            from devispro import license_admin as adm
            if not adm.SMTP["host"]:
                body = "<div class='blocker'>Kein SMTP konfiguriert. Zuerst Hostinger/SMTP speichern.</div>"
            elif not empf:
                body = "<div class='blocker'>Empfänger fehlt (Komma-getrennt).</div>"
            else:
                empfaenger = [e.strip() for e in empf.split(",") if e.strip() and "@" in e]
                if not empfaenger:
                    body = "<div class='blocker'>Kein gültiger Empfänger (enthält @).</div>"
                else:
                    text, html = marketing_mod.werbe_mail_html(lang)
                    fehler = []
                    for e in empfaenger:
                        ok = adm.mail_html(e, "DevisPro – Ihr SIA-451-Devis automatisch bepreisen", text, html)
                        if not ok:
                            fehler.append(e)
                    if fehler:
                        body = ("<div class='blocker'>Versand an %s fehlgeschlagen – SMTP prüfen.</div>"
                                % ", ".join(fehler))
                    else:
                        body = ("<div class='okbox'>✓ Werbe-Mail (HTML, ohne Anhang) an %d Empfänger gesendet: %s</div>"
                                % (len(empfaenger), ", ".join(empfaenger)))
            self._send(render_page(
                "<div class='card'>" + body + render_admin(lang).split("<div class=\"card\">", 1)[-1],
                lang).encode("utf-8"))
            return
        if self.path == "/admin_login":
            form = self._fieldstorage()
            pw = form.getvalue("pw", "")
            if auth.pruefen(pw):
                tok = auth.session_token()
                self.send_response(303)
                self.send_header("Set-Cookie", f"adminsess={tok}; Path=/; HttpOnly; Max-Age=28800")
                self.send_header("Location", "/admin")
                self.end_headers()
                return
            self._send(render_admin_login("Falsches Passwort.").encode("utf-8"))
            return
        if self.path == "/admin_logout":
            self.send_response(303)
            self.send_header("Set-Cookie", "adminsess=; Path=/; Max-Age=0")
            self.send_header("Location", "/admin")
            self.end_headers()
            return
        if self.path == "/devis_delete":
            form = self._fieldstorage()
            did = form.getvalue("id", "")
            if did and history_mod.exists(did):
                history_mod.delete(did)
            self._send(render_meine_devis(lang).encode("utf-8"))
            return
        if self.path == "/devis_freigeben":
            form = self._fieldstorage()
            did = form.getvalue("id", "")
            if did and history_mod.exists(did):
                history_mod.set_status(did, "freigegeben")
            self._send(render_meine_devis(lang).encode("utf-8"))
            return
        if self.path == "/team_login":
            form = self._fieldstorage()
            ben = (form.getvalue("benutzer") or "").strip()
            pw = form.getvalue("pw", "")
            if team_mod.pruefen(ben, pw):
                tok = team_mod.login_token(ben)
                self.send_response(303)
                self.send_header("Set-Cookie", f"teamsess={tok}; Path=/; HttpOnly; Max-Age=28800")
                self.send_header("Location", "/team")
                self.end_headers()
            else:
                self._send(render_page("<div class='blocker'>✗ Falscher Benutzer oder Passwort.</div>", lang).encode("utf-8"))
            return
        if self.path == "/team_logout":
            self.send_response(303)
            self.send_header("Set-Cookie", "teamsess=; Path=/; Max-Age=0")
            self.send_header("Location", "/team_login")
            self.end_headers()
            return
        if self.path == "/team_anlegen":
            tok = self.headers.get("Cookie", "").split("teamsess=")[-1].split(";")[0]
            ben = team_mod.token_gueltig(tok)
            if team_mod.rolle_von(ben) != "admin":
                self._send(render_page("<div class='blocker'>🔒 Nur Admin darf Benutzer anlegen.</div>", lang).encode("utf-8"))
                return
            form = self._fieldstorage()
            nb = (form.getvalue("benutzer") or "").strip()
            npw = form.getvalue("pw", "")
            rol = (form.getvalue("rolle") or "aussendienst").strip()
            try:
                team_mod.anlegen(nb, npw, rol, angelegt_von=ben)
                self.send_response(303); self.send_header("Location", "/team"); self.end_headers()
            except Exception as e:
                self._send(render_page(f"<div class='blocker'>✗ {html.escape(str(e))}</div>", lang).encode("utf-8"))
            return
        if self.path == "/team_del":
            tok = self.headers.get("Cookie", "").split("teamsess=")[-1].split(";")[0]
            ben = team_mod.token_gueltig(tok)
            if team_mod.rolle_von(ben) != "admin":
                self._send(render_page("<div class='blocker'>🔒 Nur Admin darf Benutzer löschen.</div>", lang).encode("utf-8"))
                return
            form = self._fieldstorage()
            tb = (form.getvalue("benutzer") or "").strip()
            team_mod.loeschen(tb)
            self.send_response(303); self.send_header("Location", "/team"); self.end_headers()
            return
        if self.path == "/sync_import":
            tok = self.headers.get("Cookie", "").split("teamsess=")[-1].split(";")[0]
            ben = team_mod.token_gueltig(tok)
            if team_mod.rolle_von(ben) not in ("admin", "buero"):
                self._send(render_page("<div class='blocker'>🔒 Nur Admin/Büro dürfen importieren.</div>", lang).encode("utf-8"))
                return
            form = self._fieldstorage()
            up = form["bundle"] if "bundle" in form else None
            if up is None or not getattr(up, "filename", ""):
                self._send(render_page("<div class='blocker'>✗ Kein Bundle empfangen.</div>", lang).encode("utf-8"))
                return
            tmpz = os.path.join(DATA, "_sync_import.zip")
            open(tmpz, "wb").write(up.file.read() if hasattr(up, "file") else getattr(up, "value", b""))
            try:
                rep = sync_mod.apply_bundle(tmpz, DATA)
                os.remove(tmpz)
                detail = (f"Aktualisiert: {len(rep['updated'])} · Neu: {len(rep['added'])} · "
                          f"Beibehalten (neueste): {len(rep['skipped'])}")
                body = (f"<div class='okbox'>✓ Sync angewendet. {html.escape(detail)}</div>"
                        f"<a class='btn' href='/sync'>← Zurück zu Team-Sync</a>")
                self._send(render_page(body, lang).encode("utf-8"))
            except Exception as e:
                if os.path.exists(tmpz): os.remove(tmpz)
                self._send(render_page(f"<div class='blocker'>✗ Import fehlgeschlagen: {html.escape(str(e))}</div>", lang).encode("utf-8"))
            return
        if self.path == "/sync_token":
            tok = self.headers.get("Cookie", "").split("teamsess=")[-1].split(";")[0]
            ben = team_mod.token_gueltig(tok)
            if team_mod.rolle_von(ben) not in ("admin", "buero"):
                self._send(render_page("<div class='blocker'>🔒 Nur Admin/Büro dürfen ein Token erzeugen.</div>", lang).encode("utf-8"))
                return
            t = sync_mod.sync_token_erzeugen(DATA)
            body = (f"<div class='okbox'>✓ LAN-Token erzeugt: <code>{html.escape(t)}</code><br>"
                    "Diesen Token an die Aussendienst-PCs weitergeben (gültig, solange die Datei "
                    "<code>sync_token.json</code> im Buero besteht).</div>"
                    f"<a class='btn' href='/sync'>← Zurück zu Team-Sync</a>")
            self._send(render_page(body, lang).encode("utf-8"))
            return
        if self.path == "/sync_pull":
            form = self._fieldstorage()
            url = (form.getvalue("url") or "http://127.0.0.1:5070").strip()
            token = (form.getvalue("token") or "").strip()
            try:
                from urllib.request import urlopen, Request
                req = Request(url.rstrip("/") + "/sync_bundle?token=" + token)
                data = urlopen(req, timeout=20).read()
                tmpz = os.path.join(DATA, "_sync_pull.zip")
                open(tmpz, "wb").write(data)
                rep = sync_mod.apply_bundle(tmpz, DATA)
                os.remove(tmpz)
                detail = f"Aktualisiert: {len(rep['updated'])} · Neu: {len(rep['added'])} · Beibehalten: {len(rep['skipped'])}"
                body = (f"<div class='okbox'>✓ Vom Buero geholt & angewendet. {html.escape(detail)}</div>"
                        f"<a class='btn' href='/sync'>← Zurück zu Team-Sync</a>")
                self._send(render_page(body, lang).encode("utf-8"))
            except Exception as e:
                self._send(render_page(f"<div class='blocker'>✗ Pull fehlgeschlagen: {html.escape(str(e))}</div>", lang).encode("utf-8"))
            return
        if self.path == "/vorlage_speichern":
            form = self._fieldstorage()
            did = form.getvalue("id", "")
            name = (form.getvalue("name") or "").strip()
            if did and name and history_mod.exists(did):
                try:
                    devis = crb.parse(history_mod.path_of(did, "bepreist.sia"))
                    profil = stammdaten.load_profile() or {}
                    res = templates_mod.speichern(name, devis, profil)
                    body = (f"<div class='okbox'>✓ Vorlage «{html.escape(name)}» gespeichert "
                            f"({res['n_pos']} Positionen, {res['gesamt']:,.2f} CHF). "
                            f"<a class='btn-sm' href='/vorlagen'>Vorlagen ansehen</a></div>"
                            f"{render_meine_devis(lang)}")
                    self._send(render_page(body, lang).encode("utf-8"))
                except Exception as e:
                    self._send(render_page(f"<div class='blocker'>✗ Fehler: {html.escape(str(e))}</div>", lang).encode("utf-8"))
                return
            self._send(render_page("<div class='blocker'>✗ Vorlage benötigt Namen und ein gespeichertes Devis.</div>", lang).encode("utf-8"))
            return
        if self.path == "/vorlage_laden":
            form = self._fieldstorage()
            name = (form.getvalue("name") or "").strip()
            try:
                did = templates_mod.erstellen(name)
                self.send_response(303)
                self.send_header("Location", f"/devis/{did}?importiert=1&vorlage=1")
                self.end_headers()
            except Exception as e:
                self._send(render_page(f"<div class='blocker'>✗ Fehler: {html.escape(str(e))}</div>", lang).encode("utf-8"))
            return
        if self.path == "/vorlage_del":
            form = self._fieldstorage()
            name = (form.getvalue("name") or "").strip()
            templates_mod.loeschen(name)
            self.send_response(303)
            self.send_header("Location", "/vorlagen")
            self.end_headers()
            return
        if self.path == "/wr_anlegen":
            form = self._fieldstorage()
            try:
                name = (form.getvalue("name") or "").strip()
                kunde = (form.getvalue("kunde") or "").strip()
                betrag = float(form.getvalue("betrag") or 0)
                intervall = (form.getvalue("intervall") or "monatlich").strip()
                start = (form.getvalue("start") or "").strip()
                ende = (form.getvalue("ende") or "").strip()
                notiz = (form.getvalue("notiz") or "").strip()
                v = recurring_mod.anlegen(name, kunde, betrag, intervall, start=start,
                                          ende=ende, notiz=notiz)
                body = (f"<div class='okbox'>✓ Vertrag «{html.escape(name)}» angelegt. "
                        f"Nächste Rechnung fällig: <b>{html.escape(str(v['naechste']))}</b>. "
                        f"<a class='btn-sm' href='/wiederkehrend'>Zurück</a></div>")
                self._send(render_page(body, lang).encode("utf-8"))
            except Exception as e:
                self._send(render_page(f"<div class='blocker'>✗ Fehler: {html.escape(str(e))}</div>", lang).encode("utf-8"))
            return
        if self.path == "/wr_rechnung":
            form = self._fieldstorage()
            name = (form.getvalue("name") or "").strip()
            try:
                profil = stammdaten.load_profile() or {}
                res = recurring_mod.erzeuge_rechnung(name, profil)
                # Rechnung + QR als Datei zum Ansehen speichern
                out_dir = os.path.join(DATA, "wiederkehrend_rechnungen")
                os.makedirs(out_dir, exist_ok=True)
                fn = res["nr"].replace("/", "_")
                open(os.path.join(out_dir, fn + ".html"), "w", encoding="utf-8").write(res["html"])
                open(os.path.join(out_dir, fn + ".pdf"), "wb").write(res["pdf"])
                body = (
                    "<div class='card'><h2>🧾 Rechnung erzeugt</h2>"
                    f"<p class='meta'>Vertrag <b>{html.escape(name)}</b> · Rechnung <b>{html.escape(res['nr'])}</b> "
                    f"· Fällig: {html.escape(res['faellig'])} · Nächste: {html.escape(res['naechste'])}</p>"
                    f"<div class='save'>✓ Swiss-QR eingebettet. Download:</div>"
                    f"<p><a class='btn' href='/wr_datei?f={quote(fn)}.html'>📄 HTML ansehen</a> "
                    f"<a class='btn' href='/wr_datei?f={quote(fn)}.pdf'>📄 PDF (QR)</a> "
                    f"<a class='btn' href='/wiederkehrend'>← Zurück</a></p>"
                    "<div class='note' style='margin-top:1rem'>Vorschau:</div>"
                    f"<iframe src='/wr_datei?f={quote(fn)}.html' style='width:100%;height:520px;border:1px solid #ddd;border-radius:8px'></iframe>"
                    "</div>"
                )
                self._send(render_page(body, lang).encode("utf-8"))
            except Exception as e:
                self._send(render_page(f"<div class='blocker'>✗ Fehler: {html.escape(str(e))}</div>", lang).encode("utf-8"))
            return
        if self.path == "/wr_del":
            form = self._fieldstorage()
            name = (form.getvalue("name") or "").strip()
            recurring_mod.loeschen(name)
            self.send_response(303)
            self.send_header("Location", "/wiederkehrend")
            self.end_headers()
            return
        if self.path == "/override":
            # Fachkraft-Freigabe: nur Rollen admin/buero duerfen den Review-Blocker aufheben
            tok = self.headers.get("Cookie", "").split("teamsess=")[-1].split(";")[0]
            if not team_mod.darf_freigeben(tok):
                self._send(render_page(
                    "<div class='blocker'>🔒 <b>Keine Berechtigung:</b> Nur Admin/Büro dürfen "
                    "den Review-Blocker (Fachkraft-Freigabe) aufheben. Melden Sie sich als "
                    "berechtigter Benutzer an.</div>", lang).encode("utf-8"))
                return
            form = self._fieldstorage()
            fname = form.getvalue("file", "bepreist.sia")
            self._send(render_override(fname).encode("utf-8"))
            return
        if self.path == "/profil_save":
            from devispro import system as sys_mod
            sys_mod.backup("vor_profil")
            form = self._fieldstorage()
            profil = {
                "betrieb": form.getvalue("betrieb", ""),
                "gewerk": form.getvalue("gewerk", ""),
                "kanton": form.getvalue("kanton", "ZH"),
                "stundenlohn_chf": float(form.getvalue("stundenlohn_chf", 82)),
                "material_aufschlag_pct": float(form.getvalue("material_aufschlag_pct", 12)),
                "gemeinkosten_pct": float(form.getvalue("gemeinkosten_pct", 10)),
                "gewinn_pct": float(form.getvalue("gewinn_pct", 8)),
                "mwst_pct": float(form.getvalue("mwst_pct", 8.1)),
                "iban": form.getvalue("iban", ""),
                "strasse": form.getvalue("strasse", ""),
                "plz_ort": form.getvalue("plz_ort", ""),
            }
            from devispro import kantone as kant_mod
            profil = kant_mod.waehle_kanton_profil(profil)
            stammdaten.save_profile(profil)
            self._send(render_profil().encode("utf-8"))
            return
        if self.path == "/preise_save":
            form = self._fieldstorage()
            content = form.getvalue("paste") or ""
            if "prices" in form and getattr(form["prices"], "file", None):
                raw = form["prices"].file.read()
                fname = (getattr(form["prices"], "filename", "") or "").lower()
                if fname.endswith(".xlsx"):
                    tmp = os.path.join(DATA, "_xlsx_upload.xlsx")
                    open(tmp, "wb").write(raw)
                    try:
                        from devispro import pricelist as pl_mod
                        items = pl_mod.load_xlsx(tmp)
                        import io, csv as _csv
                        buf = io.StringIO()
                        w = _csv.writer(buf)
                        w.writerow(["artikel_id","bezeichnung","npk","einheit","ep_chf","kategorie"])
                        for it in items:
                            w.writerow([it.artikel_id, it.bezeichnung, it.npk,
                                        it.einheit, f"{it.ep_chf:.2f}", it.kategorie])
                        content = buf.getvalue()
                        msg = f"✓ Excel importiert: {len(items)} Positionen."
                    except Exception as e:
                        msg = f"Fehler beim Excel-Import: {e}"
                        content = ""
                    finally:
                        if os.path.exists(tmp):
                            os.remove(tmp)
                else:
                    content = raw.decode("utf-8", "ignore")
            if content:
                stammdaten.save_prices_csv(content)
                if "msg" not in dir():
                    msg = "✓ Richtpreisliste gespeichert."
            else:
                if "msg" not in dir():
                    msg = "Keine Daten empfangen."
            # msg evtl. nicht gesetzt
            try:
                msg
            except NameError:
                msg = "✓ Richtpreisliste gespeichert."
            self._send(render_page((
                f"<div class='card'><div class='okbox'>{html.escape(msg)}</div>"
                f"<a class='btn' href='/profil'>← Zurück zu Stammdaten</a></div>"
            ), lang).encode("utf-8"))
            return
        if self.path in ("/preise_edit", "/preise_del"):
            from devispro import pricelist as pl_mod
            form = self._fieldstorage()
            try:
                idx = int(form.getvalue("idx", "-1"))
            except (TypeError, ValueError):
                idx = -1
            path_csv = os.path.join(DATA, "meine_preise.csv")
            items = pl_mod.load(path_csv)
            if 0 <= idx < len(items):
                if self.path == "/preise_edit":
                    if form.getvalue("ep") not in (None, ""):
                        try:
                            items[idx].ep_chf = float(str(form.getvalue("ep")).replace(",", "."))
                        except (ValueError, TypeError):
                            pass
                    if form.getvalue("kategorie") is not None:
                        items[idx].kategorie = form.getvalue("kategorie").strip()
                else:  # preise_del
                    items.pop(idx)
                # zurueckschreiben
                import io, csv as _csv
                buf = io.StringIO()
                w = _csv.writer(buf)
                w.writerow(["artikel_id","bezeichnung","npk","einheit","ep_chf","kategorie"])
                for it in items:
                    w.writerow([it.artikel_id, it.bezeichnung, it.npk,
                                it.einheit, f"{it.ep_chf:.2f}", it.kategorie])
                stammdaten.save_prices_csv(buf.getvalue())
            self._send(render_profil().encode("utf-8"))
            return
        if self.path == "/npk_import":
            from devispro import npk as npk_mod
            from devispro import system as sys_mod
            form = self._fieldstorage()
            msg = "Keine Datei erhalten"
            if "npkfile" in form and getattr(form["npkfile"], "file", None):
                tmp = os.path.join(DATA, "_npk_upload.csv")
                open(tmp, "wb").write(form["npkfile"].file.read())
                try:
                    neu, skip = npk_mod.import_npk_csv(tmp, os.path.join(DATA, "meine_preise.csv"))
                    sys_mod.audit("NPK_IMPORT", f"{neu} Positionen")
                    msg = f"✓ {neu} NPK-Positionen importiert ({skip} übersprungen)."
                except Exception as e:
                    msg = f"Fehler beim Import: {e}"
                os.remove(tmp)
            self._send(render_page(f"<div class='card'><div class='okbox'>{html.escape(msg)}</div><a class='btn' href='/profil'>← Zurück zu Stammdaten</a></div>", lang).encode("utf-8"))
            return
        if self.path == "/roi":
            form = self._fieldstorage()
            kw = {k: float(form.getvalue(k)) for k in
                  ["zeit_manuell_h", "zeit_app_h", "devis_pro_monat",
                   "fehler_ersparnis_chf", "app_preis", "app_jahr"] if form.getvalue(k)}
            r = roi_mod.calculate_from_profile(stammdaten.load_profile(), **kw)
            self._send(render_roi_with(r).encode("utf-8"))
            return
        if self.path == "/backup_now":
            from devispro import system as sys_mod
            sys_mod.backup("manuell")
            sys_mod.audit("BACKUP_MANUELL", "")
            self._send(render_dashboard().encode("utf-8"))
            return
        if self.path == "/process_extras":
            from devispro import system as sys_mod
            sys_mod.audit("EXTRAS_ANGWANDT", "")
            form = self._fieldstorage()
            try:
                basis = float(form.getvalue("basis_total", "0") or "0")
            except Exception:
                basis = 0.0
            extras_rows = []
            extra_sum = 0.0
            for ex_id in (form.getlist("ex_id") or []):
                try:
                    ep = float(form.getvalue("ex_ep_" + ex_id) or "0")
                    mg = float(form.getvalue("ex_mg_" + ex_id) or "0")
                except Exception:
                    continue
                bez = form.getvalue("ex_bez_" + ex_id, ex_id)
                eh = form.getvalue("ex_eh_" + ex_id, "")
                bet = ep * mg
                extra_sum += bet
                extras_rows.append((bez, eh, ep, mg, bet))
            # Eigene Position
            own_bez = form.getvalue("own_bez", "").strip()
            if own_bez:
                try:
                    oep = float(form.getvalue("own_ep") or "0")
                    omg = float(form.getvalue("own_mg") or "0")
                except Exception:
                    oep = omg = 0.0
                obet = oep * omg
                extra_sum += obet
                extras_rows.append((own_bez, form.getvalue("own_eh", ""), oep, omg, obet))
            gesamt = basis + extra_sum
            profil = (stammdaten.load_profile() or {})
            mwst = profil.get("mwst_pct", 8.1) or 8.1
            mwst_betrag = gesamt * mwst / 100.0
            brutt = gesamt + mwst_betrag
            er = "".join(
                f"<tr><td>{html.escape(str(b))}</td><td>{html.escape(str(e))}</td>"
                f"<td>{ep:,.2f}</td><td>{mg:,.2f}</td><td>{bet:,.2f}</td></tr>"
                for (b, e, ep, mg, bet) in extras_rows) or "<tr><td colspan=5>Keine Zusatzpositionen</td></tr>"
            # Zusatzpositionen als dicts fuer SIA-Export aufbereiten
            extras_dicts = []
            for i, (b, e, ep, mg, bet) in enumerate(extras_rows, start=1):
                extras_dicts.append({"pos_nr": f"Z{i:03d}", "text": str(b),
                                     "menge": mg, "einheit": str(e), "ep": ep, "betrag": bet})
            # Erweiterte SIA-Datei schreiben (falls Devis noch da)
            dl_link = ""
            up = os.path.join(DATA, "_up_devis.sia")
            if os.path.exists(up):
                try:
                    devis = crb.parse(up)
                    out_ext = os.path.join(DATA, "bepreist_mit_zusatz.sia")
                    crb.export(devis, out_ext, extras=extras_dicts)
                    dl_link = (f"<a class=\"btn\" href=\"/download?f=bepreist_mit_zusatz.sia\">"
                               f"⬇ Erweiterte Sorba-Datei herunterladen (inkl. Zusatzpositionen)</a>")
                except Exception:
                    dl_link = ""
            body = f"""
 <div class="card">
  <h2>Gesamtofferte (Devis + ergänzte Positionen)</h2>
  <table><thead><tr><th>Devis-Positionen (automatisch)</th><th></th><th></th><th></th><th>Betrag</th></tr></thead>
  <tbody><tr><td colspan=4>Automatisch bepreiste Devis-Positionen</td><td><b>{basis:,.2f} CHF</b></td></tr></tbody></table>
  <table style="margin-top:1rem"><thead><tr><th>Zusätzliche Position (Fachbetrieb)</th><th>Einheit</th>
  <th>EP CHF</th><th>Menge</th><th>Betrag</th></tr></thead><tbody>{er}</tbody></table>
  <table style="margin-top:1rem"><tbody>
   <tr><td colspan=4><b>Automatisch bepreiste Devis-Positionen</b></td><td><b>{basis:,.2f} CHF</b></td></tr>
   <tr><td colspan=4><b>Zusätzlich vom Fachbetrieb ergänzt ({len(extras_rows)})</b></td><td><b>{extra_sum:,.2f} CHF</b></td></tr>
   <tr><td colspan=4><b>Zwischensumme (Netto)</b></td><td><b>{gesamt:,.2f} CHF</b></td></tr>
   <tr><td colspan=4>MwSt {mwst:g}%</td><td>{mwst_betrag:,.2f} CHF</td></tr>
   <tr><td colspan=4><b>Gesamt (Brutto)</b></td><td><b>{brutt:,.2f} CHF</b></td></tr>
  </tbody></table>
  <div class='okbox' style="margin-top:1rem">✓ Inkl. {len(extras_rows)} vom Fachbetrieb ergänzter Position(en).</div>
  {dl_link}
  <button type="button" onclick="window.print()" class="btn" style="margin-left:1rem">🖨 Drucken / Als PDF speichern</button>
  <a class="btn" href="/" style="margin-left:1rem">⬅ Neues Devis</a>
 </div>"""
            self._send(render_page(body, lang).encode("utf-8"))
            return

        if self.path in ("/edit_position", "/edit_menge"):
            form = self._fieldstorage()
            pos_nr = form.getvalue("pos_nr", "")
            devis_path = os.path.join(DATA, "_up_devis.sia")
            if not os.path.exists(devis_path):
                self._send(render_index(self).encode("utf-8"))
                return
            ep = float(form.getvalue("ep") or 0) if self.path == "/edit_position" else None
            menge = float(form.getvalue("menge") or 0) if self.path == "/edit_menge" else None
            try:
                html_out = _recompute_and_render(devis_path, edit_pos_nr=pos_nr,
                                                 ep=ep, menge=menge)
                self._send(html_out.encode("utf-8"))
            except Exception as e:
                self._send(render_index(self).encode("utf-8"))
            return

        if self.path == "/erp_aktion":
            from devispro import license as _liz
            from devispro import erp as _erp
            if _liz.tarif() != "erp":
                self.send_response(303); self.send_header("Location", "/erp"); self.end_headers(); return
            form = self._fieldstorage()
            aktion = form.getvalue("aktion", "")
            nr = (form.getvalue("nr") or "").strip()
            wert = form.getvalue("wert", "")
            meld = ""
            try:
                if aktion == "wareneingang" and nr:
                    _erp.artikel_wareneingang(nr, float(wert or 0))
                    meld = f"Wareneingang {wert} fuer {nr} erfasst."
                elif aktion == "zahlung" and nr:
                    _erp.beleg_zahlung(nr, float(wert or 0))
                    meld = f"Zahlung {wert} CHF auf {nr} erfasst."
                elif aktion == "neuer_artikel":
                    a_nr = (form.getvalue("nr") or "").strip()
                    if a_nr:
                        _erp.artikel_ergaenzen(
                            a_nr, form.getvalue("bez") or a_nr,
                            form.getvalue("einheit") or "Stk",
                            ek=float(form.getvalue("ek") or 0),
                            vk=float(form.getvalue("vk") or 0),
                            bestand=float(form.getvalue("bestand") or 0),
                            mindest=float(form.getvalue("mindest") or 0))
                        meld = f"Artikel {a_nr} angelegt."
                elif aktion == "neuer_partner":
                    p_nr = (form.getvalue("nr") or "").strip()
                    if p_nr:
                        _erp.partner_ergaenzen(
                            p_nr, form.getvalue("name") or p_nr,
                            form.getvalue("typ") or "kunde",
                            strasse=form.getvalue("strasse") or "",
                            plz_ort=form.getvalue("plz_ort") or "",
                            mwst_nr=form.getvalue("mwst") or "",
                            mail=form.getvalue("mail") or "")
                        meld = f"Partner {p_nr} angelegt."
                elif aktion == "neuer_beleg":
                    btyp = form.getvalue("typ") or "rechnung"
                    pnr = (form.getvalue("partner_nr") or "").strip()
                    pname = form.getvalue("partner_name") or pnr
                    raw = form.getvalue("positionen") or ""
                    positionen = []
                    for line in raw.splitlines():
                        line = line.strip()
                        if not line:
                            continue
                        teile = [t.strip() for t in line.split("|")]
                        if len(teile) >= 5:
                            try:
                                positionen.append({
                                    "artikel_nr": teile[0], "bezeichnung": teile[1],
                                    "menge": float(teile[2]), "einheit": teile[3],
                                    "ep": float(teile[4])})
                            except ValueError:
                                pass
                    if pnr and positionen:
                        _erp.beleg_erstellen(btyp, pnr, pname, positionen)
                        meld = f"Beleg ({btyp}) fuer {pnr} erstellt."
                    else:
                        meld = "Fehler: Partner-Nr und mind. 1 Position noetig."
            except Exception as e:
                meld = f"Fehler: {e}"
            self.send_response(303)
            self.send_header("Location", f"/erp?m={quote(meld)}")
            self.end_headers()
            return

        if self.path != "/process":
            self._send(b"not found", "text/plain")
            return
        form = self._fieldstorage()
        devis_f = form["devis"] if "devis" in form else None
        method = form.getvalue("method", "mock")
        if devis_f is None or not getattr(devis_f, "file", None):
            self._send(render_index(self).encode("utf-8"))
            return
        devis_path = os.path.join(DATA, "_up_devis.sia")
        with open(devis_path, "wb") as f:
            f.write(devis_f.file.read())
        # Richtpreise automatisch aus gespeicherter Liste
        preise_csv = stammdaten.load_prices_csv()
        if not preise_csv:
            self._send(render_index(self).encode("utf-8"))
            return
        prices_path = os.path.join(DATA, "_meine_preise.csv")
        with open(prices_path, "w", encoding="utf-8") as f:
            f.write(preise_csv)
        try:
            devis = crb.parse(devis_path)
            prices = load_prices(prices_path)
            matcher = Matcher(method=method, threshold=0.6)
            profil = stammdaten.load_profile() or {}
            kf = float(profil.get("kanton_faktor", 1.0) or 1.0)
        except Exception:
            self._send(render_index(self).encode("utf-8"))
            return
        rows = []
        review = 0
        review_positions = []
        for p in devis.positions:
            r = matcher.match(p, prices)
            p.ep = (r.einheitspreis_chf or 0.0) * kf
            p.matched_artikel = r.matched_artikel_id
            p.confidence = r.confidence
            p.requires_review = r.requires_review
            p.begruendung = r.begruendung
            p.fill()
            if p.requires_review:
                review += 1
                review_positions.append({"pos_nr": p.pos_nr, "text": p.text, "conf": p.confidence})
            rows.append({"pos_nr": p.pos_nr, "artikel": p.matched_artikel, "ep": p.ep,
                         "menge": p.menge, "einheit": p.einheit, "betrag": p.betrag,
                         "conf": p.confidence, "review": p.requires_review})
        out_name = "bepreist.sia"
        crb.export(devis, os.path.join(DATA, out_name))
        total = sum((p.betrag or 0.0) for p in devis.positions)
        # Verlauf speichern (jedes Devis bleibt spaeter ansehbar)
        try:
            from devispro import history as hist_mod
            did = hist_mod.save(devis, total, name=None, method=method,
                                kanton=profil.get("kanton", "ZH"), status="offen")
            audit_msg = f"DEVIS_BEPREIST id={did} netto={total:.2f}"
            try:
                from devispro import system as sys_mod
                sys_mod.audit("DEVIS_BEPREIST", audit_msg)
            except Exception:
                pass
        except Exception:
            did = None
        self._send(render_result(rows, total, devis.meta.get("currency", "CHF"),
                                 review, len(devis.positions), out_name,
                                 review_positions, devis_id=did).encode("utf-8"))

    def log_message(self, *args):
        pass


def render_roi_with(r, lang="de"):
    cf = r["cashflow"]
    be = r["break_even_monat"] or 12
    be_text = f"Monat {be}" if be <= 12 else "> 12 Monate"
    body = f"""
 <div class="card">
  <h2>ROI-Kalkulator – was die App dir spart</h2>
  <form method="post" action="/roi">
   <div class="grid">
    <div><label>Aufwand von Hand (h/Devis)</label><input type="number" step="0.1" name="zeit_manuell_h" value="2.0"></div>
    <div><label>Aufwand mit App (h/Devis)</label><input type="number" step="0.1" name="zeit_app_h" value="0.2"></div>
    <div><label>Devis pro Monat</label><input type="number" step="1" name="devis_pro_monat" value="20"></div>
    <div><label>Fehler-Ersparnis (CHF/Devis)</label><input type="number" step="5" name="fehler_ersparnis_chf" value="40"></div>
    <div><label>App-Anschaffung CHF</label><input type="number" step="100" name="app_preis" value="2400"></div>
    <div><label>Jahresgebühr CHF</label><input type="number" step="50" name="app_jahr" value="900"></div>
   </div>
   <button type="submit">Berechnen</button>
  </form>
 </div>
 <div class="kpi">
  <div><div class="v">{r['zeit_erspart_pro_devis']:.1f} h</div><div class="l">gespart pro Devis</div></div>
  <div><div class="v">{r['monat_ersparnis']:,.0f}</div><div class="l">CHF gespart / Monat</div></div>
  <div><div class="v">{r['jahr_ersparnis']:,.0f}</div><div class="l">CHF gespart / Jahr</div></div>
 </div>
 <div class="kpi">
  <div><div class="v">{be_text}</div><div class="l">Break-even (App bezahlt)</div></div>
  <div><div class="v">{r['roi_jahr1']:,.0f}</div><div class="l">Netto-Gewinn nach 12 Mon.</div></div>
  <div><div class="v">{r['roi_pct']:.0f}%</div><div class="l">ROI Jahr 1</div></div>
 </div>
 <p class="meta">Zeit gespart im Jahr: <b>{r['zeit_erspart_jahr_h']:.0f} Stunden</b>
 (= {(r['zeit_erspart_jahr_h']/8):.0f} Arbeitstage à 8h).</p>
 <svg class="chart" viewBox="0 0 600 220" preserveAspectRatio="none">
  {chart_svg(cf)}
 </svg>
 <p class="meta">Kumulierter Cashflow (Ersparnis abzüglich App-Kosten) über 12 Monate, in CHF.</p>
"""
    return render_page(body, lang)


if __name__ == "__main__":
    # Markt-Benchmark beim ersten Start mit realistischen CH-Werten befuellen
    try:
        from devispro import benchmark as _bench
        import os as _os
        if not _os.path.exists(_bench.STORE_PATH):
            _bench.seed_market(silent=True)
    except Exception:
        pass
    print(f"devispro UI laeuft auf http://localhost:{PORT}")
    HTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
