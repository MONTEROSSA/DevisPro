"""ERP-Web-UI (stdlib, keine Flask). Voll bedienbares ERP-Dashboard: Dashboard,
Listen (Artikel, Partner, Belege, Mahnwesen, MWST) sowie Formulare zum Anlegen
von Artikeln, Partnern und Belegen. Wird nur bei Tarif 'erp' voll angezeigt.
"""

import html
from devispro import erp as E


def _tabelle(spalten, zeilen, leer="–"):
    rows = "".join(
        "<tr>" + "".join(f"<td>{html.escape(str(c))}</td>" for c in r) + "</tr>"
        for r in zeilen) or f"<tr><td colspan='{len(spalten)}' style='color:#999'>{leer}</td></tr>"
    return ("<table class='tbl'><thead><tr>"
            + "".join(f"<th>{html.escape(s)}</th>" for s in spalten) + "</tr></thead><tbody>"
            + rows + "</tbody></table>")


def _fmt(x):
    try:
        return f"{float(x):,.2f}".replace(",", "'")
    except Exception:
        return str(x)


def _artikel_form():
    return """
<form method="post" action="/erp_aktion" class="card" style="margin-top:1rem">
  <h3>Neuer Artikel</h3>
  <div class="grid">
    <input name="nr" placeholder="Artikel-Nr (A-001)" required>
    <input name="bez" placeholder="Bezeichnung">
    <input name="einheit" placeholder="Einheit (m3)" value="m3">
    <input name="ek" placeholder="EK Preis" type="number" step="0.01">
    <input name="vk" placeholder="VK Preis" type="number" step="0.01">
    <input name="bestand" placeholder="Bestand" type="number" step="0.001" value="0">
    <input name="mindest" placeholder="Mindestbestand" type="number" step="0.001" value="0">
  </div>
  <input type="hidden" name="aktion" value="neuer_artikel">
  <button type="submit">Artikel speichern</button>
</form>"""


def _partner_form():
    return """
<form method="post" action="/erp_aktion" class="card" style="margin-top:1rem">
  <h3>Neuer Partner</h3>
  <div class="grid">
    <input name="nr" placeholder="Partner-Nr (K-001)" required>
    <select name="typ"><option value="kunde">Kunde</option><option value="lieferant">Lieferant</option></select>
    <input name="name" placeholder="Name / Firma">
    <input name="strasse" placeholder="Strasse">
    <input name="plz_ort" placeholder="PLZ Ort">
    <input name="mail" placeholder="E-Mail">
    <input name="mwst" placeholder="MWST-Nr (CHE-...)">
  </div>
  <input type="hidden" name="aktion" value="neuer_partner">
  <button type="submit">Partner speichern</button>
</form>"""


def _beleg_form():
    return """
<form method="post" action="/erp_aktion" class="card" style="margin-top:1rem">
  <h3>Neue Rechnung / Bestellung</h3>
  <div class="grid">
    <select name="typ"><option value="rechnung">Verkaufsrechnung</option><option value="bestellung">Bestellung (Lieferant)</option><option value="angebot">Angebot</option><option value="auftrag">Auftrag</option></select>
    <input name="partner_nr" placeholder="Partner-Nr" required>
    <input name="partner_name" placeholder="Partner-Name">
  </div>
  <p class="meta">Positionen (eine pro Zeile: Artikel-Nr | Bezeichnung | Menge | Einheit | EP):</p>
  <textarea name="positionen" rows="4" placeholder="A-001|Beton|4|m3|180"></textarea>
  <input type="hidden" name="aktion" value="neuer_beleg">
  <button type="submit">Beleg erstellen</button>
</form>"""


def render_erp(tarif="devis", meldung="", sektion="dashboard"):
    if tarif != "erp":
        return ("<div class='card'><h2>DevisPro ERP</h2>"
                "<p class='meta'>Das integrierte ERP ist im Tarif <b>DevisPro + ERP</b> "
                "enthalten. Aktueller Tarif: <b>%s</b>.</p>"
                "<p>Upgrade ueber Monterossa AG (info@devispro.de).</p></div>" % tarif)
    m = f"<div class='okbox'>{html.escape(meldung)}</div>" if meldung else ""
    d = E.dashboard()
    kennz = _tabelle(
        ["Kennzahl", "Wert"],
        [["Umsatz (Jahr)", f"{_fmt(d['umsatz_jahr'])} CHF"],
         ["Offene Posten", f"{_fmt(d['offene_posten'])} CHF"],
         ["Lagerwert", f"{_fmt(d['lagerwert'])} CHF"],
         ["Artikel", d["artikel"]], ["Kunden", d["kunden"]],
         ["Lieferanten", d["lieferanten"]],
         ["Offene Rechnungen", d["rechnungen_offen"]],
         ["Max. Mahnstufe", d["mahnstufe_max"]],
         ["Nachbestellen", ", ".join(d["nachbestellung"]) or "–"]])
    art = _tabelle(["Nr", "Bezeichnung", "Bestand", "EK", "VK", "Min"],
                   [[a.nr, a.bezeichnung, a.bestand, _fmt(a.ek_preis), _fmt(a.vk_preis), a.mindestbestand]
                    for a in E.artikel_liste()])
    part = _tabelle(["Nr", "Name", "Typ", "Offen", "Kreditlimit"],
                    [[p.nr, p.name, p.typ, _fmt(p.offen), _fmt(getattr(p, "kreditlimit", 0.0))]
                     for p in E.partner_liste()])
    bez = _tabelle(["Nr", "Typ", "Partner", "Netto", "Brutto", "Status"],
                   [[b.nr, b.typ, b.partner_name, _fmt(b.netto()), _fmt(b.brutto()),
                     b.status or ("bezahlt" if b.bezahlt else "offen")]
                    for b in E.beleg_liste()])
    offen = _tabelle(["Rechnung", "Kunde", "Fällig", "Offen", "Stufe"],
                     [[o["nr"], o["partner"], o["faellig"], _fmt(o["offen"]), o["stufe"]]
                      for o in E.offene_posten_liste()])
    mw = d["mwst"]
    mwtxt = (f"MWST geschuldet: {_fmt(mw['mwst_geschuldet'])} CHF"
             + f" · Vorsteuer: {_fmt(mw['vorsteuer'])} CHF"
             + f" · Saldo zahlbar: {_fmt(mw['saldo_zahlbar'])} CHF")
    warn = E.debitoren_warnungen()
    warntxt = _tabelle(["Kunde", "Offen", "Limit"],
                      [[w["name"], _fmt(w["offen"]), _fmt(w["limit"])] for w in warn]) if warn else \
              "<p class='meta'>Keine Kreditlimit-Ueberschreitungen.</p>"
    body = f"""
<div class="card">
  <h2>DevisPro ERP – Dashboard</h2>
  {m}
  {kennz}
  <h3 style="margin-top:1.5rem">Debitoren-Warnungen (Kreditlimit)</h3>
  {warntxt}
  <h3 style="margin-top:1.5rem">Artikel & Lager</h3>
  {art}
  {_artikel_form()}
  <h3 style="margin-top:1.5rem">Partner (Kunden & Lieferanten)</h3>
  {part}
  {_partner_form()}
  <h3 style="margin-top:1.5rem">Belege (Verkauf & Einkauf)</h3>
  {bez}
  {_beleg_form()}
  <h3 style="margin-top:1.5rem">Offene Posten & Mahnwesen</h3>
  {offen}
  <h3 style="margin-top:1.5rem">MWST-Abrechnung ({mw['jahr']})</h3>
  <p class="meta">{mwtxt}</p>
  <p class="meta">Export an Buchhaltung (Abacus, Proffix, BMD, DATEV, Banana, SAP …) "
     "ueber die 13 integrierten Schnittstellen.</p>
</div>"""
    return body


def render_erp_vorschau():
    """Anonyme, oeffentliche ERP-Vorschau mit festen Beispieldaten eines
    Muster-KMU. Zeigt das Dashboard genau so, wie es der Kunde nach dem
    Download im Tarif 'erp' sehen wuerde – klar als Beispiel markiert.
    Kein Tarif-Check, keine echten Kundendaten."""
    d = {
        "umsatz_jahr": 482350.0, "offene_posten": 73420.0, "lagerwert": 58210.0,
        "artikel": 142, "kunden": 38, "lieferanten": 11,
        "rechnungen_offen": 9, "mahnstufe_max": 2,
        "nachbestellung": ["A-118 (Daemmung)", "A-204 (Putz)"],
        "mwst": {"jahr": 2026, "mwst_geschuldet": 28410.0, "vorsteuer": 9120.0, "saldo_zahlbar": 19290.0},
    }
    kennz = _tabelle(
        ["Kennzahl", "Wert"],
        [["Umsatz (Jahr)", f"{_fmt(d['umsatz_jahr'])} CHF"],
         ["Offene Posten", f"{_fmt(d['offene_posten'])} CHF"],
         ["Lagerwert", f"{_fmt(d['lagerwert'])} CHF"],
         ["Artikel", d["artikel"]], ["Kunden", d["kunden"]],
         ["Lieferanten", d["lieferanten"]],
         ["Offene Rechnungen", d["rechnungen_offen"]],
         ["Max. Mahnstufe", d["mahnstufe_max"]],
         ["Nachbestellen", ", ".join(d["nachbestellung"]) or "–"]])
    art = _tabelle(["Nr", "Bezeichnung", "Bestand", "EK", "VK", "Min"],
                   [["A-001", "Sanitärarmatur Typ X", 24, _fmt(82.0), _fmt(149.0), 8],
                    ["A-118", "Dämmplatte 60mm", 6, _fmt(12.4), _fmt(21.9), 10],
                    ["A-204", "Innenputz 25kg", 3, _fmt(9.1), _fmt(16.5), 12],
                    ["A-330", "Heizungspumpe Eco", 11, _fmt(140.0), _fmt(239.0), 4]])
    part = _tabelle(["Nr", "Name", "Typ", "Offen", "Kreditlimit"],
                    [["K-014", "Bauprojekt GmbH", "kunde", _fmt(18400.0), _fmt(50000.0)],
                     ["K-022", "Wohnbau AG", "kunde", _fmt(28900.0), _fmt(40000.0)],
                     ["L-003", "Baumarkt AG", "lieferant", "0.00", "–"]])
    bez = _tabelle(["Nr", "Typ", "Partner", "Netto", "Brutto", "Status"],
                   [["R-2026-014", "rechnung", "Bauprojekt GmbH", _fmt(16230.0), _fmt(17528.0), "offen"],
                    ["R-2026-015", "rechnung", "Wohnbau AG", _fmt(26750.0), _fmt(28890.0), "offen"],
                    ["A-2026-009", "auftrag", "Renovation Müller", _fmt(9400.0), _fmt(10152.0), "bezahlt"]])
    offen = _tabelle(["Rechnung", "Kunde", "Fällig", "Offen", "Stufe"],
                    [["R-2026-014", "Bauprojekt GmbH", "2026-09-15", _fmt(17528.0), "1"],
                     ["R-2026-015", "Wohnbau AG", "2026-09-22", _fmt(28890.0), "2"]])
    mw = d["mwst"]
    mwtxt = (f"MWST geschuldet: {_fmt(mw['mwst_geschuldet'])} CHF"
             + f" · Vorsteuer: {_fmt(mw['vorsteuer'])} CHF"
             + f" · Saldo zahlbar: {_fmt(mw['saldo_zahlbar'])} CHF")
    warntxt = _tabelle([ "Kunde", "Offen", "Limit"],
                       [["Wohnbau AG", _fmt(28900.0), _fmt(40000.0)]])
    body = f"""
<div class="card">
  <h2>📊 DevisPro ERP – <span style="color:#b91c1c">Beispiel-Vorschau</span></h2>
  <div class="okbox" style="background:#e8f5ec;color:#0b5e2f">So sieht das ERP-Dashboard im Tarif <b>DevisPro + ERP</b> aus.
  Gezeigte Zahlen sind ein Musterbetrieb (Sanitär Meier AG) – nach dem Download sehen Sie Ihre eigenen, echten Daten.</div>
  {kennz}
  <h3 style="margin-top:1.5rem">Debitoren-Warnungen (Kreditlimit)</h3>
  {warntxt}
  <h3 style="margin-top:1.5rem">Artikel & Lager</h3>
  {art}
  <h3 style="margin-top:1.5rem">Partner (Kunden & Lieferanten)</h3>
  {part}
  <h3 style="margin-top:1.5rem">Belege (Verkauf & Einkauf)</h3>
  {bez}
  <h3 style="margin-top:1.5rem">Offene Posten & Mahnwesen</h3>
  {offen}
  <h3 style="margin-top:1.5rem">MWST-Abrechnung ({mw['jahr']})</h3>
  <p class="meta">{mwtxt}</p>
  <p class="meta">Export an Buchhaltung (Abacus, Proffix, BMD, DATEV, Banana, SAP …) über die 13 integrierten Schnittstellen.</p>
  <p style="margin-top:1.2rem"><a class="btn" href="/download_gate" style="background:#ffd54a;color:#0f5132">⬇ Jetzt herunterladen &amp; 3 Monate testen</a>
  <a class="btn" href="/trial">🚀 Pilot anmelden</a></p>
</div>
"""
    return body
