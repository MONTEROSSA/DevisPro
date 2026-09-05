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
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, urlencode, parse_qs

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from devispro.parsers import crb
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
from devispro import license_admin as lizadm
from devispro.documents import export_pdf as doc_export_pdf
from devispro.i18n import t as _t, LANGS

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
</style></head><body>
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
        rows.append(
            f"<tr><td><code>{html.escape(str(p.pos_nr))}</code></td>"
            f"<td>{html.escape(str(p.text))}</td>"
            f"<td style='text-align:right'>{ep}</td>"
            f"<td>{html.escape(str(p.menge))} {html.escape(str(p.einheit))}</td>"
            f"<td style='text-align:right'>{bet}</td>"
            f"<td class='{'ok' if not p.requires_review else 'rev'}'>"
            f"{'✓' if not p.requires_review else '!'}</td></tr>"
        )
    total = sum((p.betrag or 0.0) for p in devis.positions)
    body = (f"<div class='card'><h2>{L('historie_titel')} – {html.escape(str(m.get('name','')))}</h2>"
            f"<p class='meta'>{L('datum')}: {html.escape(m.get('datum',''))} · "
            f"Kanton: {html.escape(m.get('kanton',''))} · "
            f"{L('gesamt')}: <b>{total:,.2f} CHF</b></p>"
            f"<a class='btn-sm' href='/devis_offerte?id={did}'>{L('offerte')} / PDF</a> "
            f"<a class='btn-sm alt' href='/devis_download?id={did}'>⬇ Sorba</a> "
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
            f"<th>EP CHF</th><th>Menge</th><th>Betrag</th><th>✓</th></tr></thead>"
            f"<tbody>{''.join(rows)}</tbody></table></div>")
    return render_page(body, lang)


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


def render_trial(lang="de", fehler="", erfolg_bis=""):
    from devispro import kantone as kant_mod
    from devispro.extras import gewerke_liste
    kantone_opts = "".join(
        f'<option value="{k}">{k} – {html.escape(kant_mod.label(k))}</option>'
        for k in sorted(kant_mod.KANTONE.keys()))
    gewerk_opts = "".join(
        f'<option value="{html.escape(g)}">{html.escape(g)}</option>'
        for g in gewerke_liste())
    warn = f"<div class='blocker'>{html.escape(fehler)}</div>" if fehler else ""
    erfolg = (f"<div class='okbox'>✓ {_t('trial_erfolg', lang)} "
              f"(<b>{html.escape(erfolg_bis)}</b>)</div>") if erfolg_bis else ""
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
   <input type="email" name="email" required style="width:100%;padding:.6rem">
   <label style="margin-top:.6rem">{_t('trial_kanton', lang)}</label>
   <select name="kanton" style="width:100%;padding:.6rem">{kantone_opts}</select>
   <label style="margin-top:.6rem">{_t('trial_gewerk', lang)}</label>
   <select name="gewerk" style="width:100%;padding:.6rem">{gewerk_opts}</select>
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
        if parsed.path == "/download":
            fname = parsed.query.split("f=", 1)[-1]
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
            self._send(render_trial(lang).encode("utf-8"))
        elif parsed.path == "/admin":
            tok = self.headers.get("Cookie", "").split("adminsess=")[-1].split(";")[0]
            if auth.session_gueltig(tok):
                self._send(render_admin().encode("utf-8"))
            else:
                self._send(render_admin_login().encode("utf-8"))
        elif parsed.path == "/profil":
            self._send(render_profil().encode("utf-8"))
        elif parsed.path in ("/", "/start"):
            qlang = parsed.query.split("lang=", 1)[-1].split("&")[0] or "de"
            if qlang not in LANGS:
                qlang = "de"
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
                os.remove(tmp)
                self.send_response(303)
                self.send_header("Location", f"/devis/{did}?importiert=1")
                self.end_headers()
                return
            except Exception as e:
                self._send(render_page(f"<div class='blocker'>✗ Import fehlgeschlagen: {html.escape(str(e))}</div>", lang).encode("utf-8"))
                return
        if self.path == "/trial_anmelden":
            form = self._fieldstorage()
            res = lizadm.trial_anmelden({
                "firma": form.getvalue("firma", ""),
                "name": form.getvalue("name", ""),
                "email": form.getvalue("email", ""),
                "kanton": form.getvalue("kanton", ""),
                "gewerk": form.getvalue("gewerk", ""),
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
            host = (form.getvalue("host") or "").strip()
            user = (form.getvalue("user") or "").strip()
            pwd = (form.getvalue("pass") or "").strip()
            port = (form.getvalue("port") or "587").strip()
            tls = (form.getvalue("tls") or "starttls").strip()
            try:
                port = int(port)
            except Exception:
                port = 587
            if tls not in ("starttls", "ssl", "none"):
                tls = "starttls"
            from devispro import license_admin as adm
            if host and user:
                adm.smtp_konfigurieren(host, user, pwd, port=port, tls=tls)
                body = "<div class='okbox'>✓ SMTP gespeichert. Mails werden jetzt automatisch versendet.</div>"
            else:
                body = "<div class='blocker'>Host und Benutzer sind erforderlich.</div>"
            msg = body + "\n"
            self._send(render_page(
                "<div class='card'>" + msg + render_admin(lang).split("<div class=\"card\">", 1)[-1],
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
        if self.path == "/override":
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
    print(f"devispro UI laeuft auf http://localhost:{PORT}")
    HTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
