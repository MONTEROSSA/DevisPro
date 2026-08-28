"""SIA-118-basierte Baustellen-Dokumente (Werkvertrag, Abnahme, Devis-Muster).

Reine Stdlib + optionales wkhtmltopdf (Fallback: druckfertiges HTML).
Hinweis: SIA 118 ist eine Privatnorm und gilt nur, wenn vertraglich einbezogen.
Die Vorlagen sind Orientierungshilfen, KEINE Rechtsberatung – vor Einsatz
einen Fachanwalt Bau- und Werkvertragsrecht konsultieren.
"""
import html
import os
import shutil
import subprocess

from .models import Devis


def _chf(value) -> str:
    try:
        v = float(value or 0.0)
    except (TypeError, ValueError):
        v = 0.0
    return f"{v:,.2f}".replace(",", "'")


def _round_rappen(v: float) -> float:
    try:
        return round(float(v) * 100) / 100.0
    except (TypeError, ValueError):
        return 0.0


# ----------------------------------------------------------------------------
# Texte (DE/FR/IT) – nur die dokumentrelevanten Begriffe
# ----------------------------------------------------------------------------
T = {
    "werkvertrag":   {"de": "Werkvertrag (gemäss SIA 118)", "fr": "Contrat d'entreprise (selon SIA 118)", "it": "Contratto d'opera (secondo SIA 118)"},
    "abnahme":       {"de": "Abnahmeprotokoll", "fr": "Procès-verbal de réception", "it": "Verbale di collaudo"},
    "devis_muster":  {"de": "Devis / Kostenvoranschlag", "fr": "Devis / Devis estimatif", "it": "Devis / Preventivo"},
    "unternehmer":   {"de": "Unternehmer (KMU)", "fr": "Entrepreneur (PME)", "it": "Imprenditore (PMI)"},
    "besteller":     {"de": "Besteller (Bauherr)", "fr": "Maître de l'ouvrage", "it": "Committente"},
    "objekt":        {"de": "Objekt / Baustelle", "fr": "Objet / Chantier", "it": "Oggetto / Cantiere"},
    "leistung":      {"de": "Leistungsumfang", "fr": "Étendue des prestations", "it": "Estensione delle prestazioni"},
    "preis":         {"de": "Preis / Vergütung", "fr": "Prix / Rémunération", "it": "Prezzo / Corrispettivo"},
    "ausfuehrung":   {"de": "Ausführungsfrist", "fr": "Délai d'exécution", "it": "Termine di esecuzione"},
    "zahlung":       {"de": "Zahlungsbedingungen", "fr": "Conditions de paiement", "it": "Condizioni di pagamento"},
    "haftung":       {"de": "Mängelhaftung / Verjährung", "fr": "Garantie des défauts / Prescription", "it": "Garanzia / Prescrizione"},
    "unterzeichnung":{"de": "Unterzeichnung", "fr": "Signature", "it": "Firma"},
    "ort_datum":     {"de": "Ort, Datum", "fr": "Lieu, date", "it": "Luogo, data"},
    "name":          {"de": "Name", "fr": "Nom", "it": "Nome"},
    "unterschrift":  {"de": "Unterschrift", "fr": "Signature", "it": "Firma"},
    "festgestellt":  {"de": "Es werden folgende Mängel festgestellt", "fr": "Les défauts suivants sont constatés", "it": "Sono constatati i seguenti difetti"},
    "kein_mangel":   {"de": "Keine Mängel festgestellt – das Werk wird abgenommen.", "fr": "Aucun défaut constaté – l'ouvrage est réceptionné.", "it": "Nessun difetto constatato – l'opera è collaudata."},
    "bedingt":       {"de": "Abnahme unter Vorbehalt (siehe Mängelliste).", "fr": "Réception sous réserve (voir liste des défauts).", "it": "Collaudo con riserva (vedi elenco difetti)."},
    "verbindlich":   {"de": "Dieser Devis ist unverbindlich, sofern nicht anders vermerkt.", "fr": "Ce devis n'est pas engageant, sauf mention contraire.", "it": "Questo devis non è vincolante, salvo diversa indicazione."},
    "verbindlich_bis":{"de": "Verbindlich bis", "fr": "Engageant jusqu'au", "it": "Vincolante fino al"},
    "hinweis":       {"de": "Hinweis", "fr": "Remarque", "it": "Nota"},
    "haftung_text":  {"de": "Mängel an Bauten verjähren 5 Jahre (OR 371). Bei Abnahme gelten offene Mängel als gerügt.", "fr": "Les défauts aux constructions se prescrivent par 5 ans (CO 371). Lors de la réception, les défauts ouverts sont réputés signalés.", "it": "I difetti alle costruzioni si prescrivono in 5 anni (CO 371). Alla collaudo, i difetti aperti si considerano segnalati."},
}


def _t(key, lang):
    return T.get(key, {}).get(lang, T.get(key, {}).get("de", key))


COMMON_CSS = """
 @page { size: A4; margin: 16mm; }
 * { box-sizing: border-box; }
 body { font-family: -apple-system, system-ui, "Helvetica Neue", Arial, sans-serif;
        color:#1a1a1a; font-size: 11px; margin:0; line-height:1.45; }
 header { display:flex; justify-content:space-between; align-items:flex-start;
          border-bottom:3px solid #14532d; padding-bottom:10px; margin-bottom:14px; }
 .logo { font-size:20px; font-weight:800; color:#14532d; }
 .meta { text-align:right; font-size:10px; color:#555; }
 h1 { font-size:16px; margin:0 0 12px; color:#14532d; }
 h2 { font-size:12px; margin:16px 0 5px; border-bottom:1px solid #ddd; padding-bottom:3px; }
 table.kv { width:100%; border-collapse:collapse; margin:6px 0; }
 table.kv td { border:1px solid #ddd; padding:5px 7px; vertical-align:top; }
 table.kv td.k { background:#f0f4f1; width:34%; font-weight:600; }
 .pos { width:100%; border-collapse:collapse; margin-top:8px; }
 .pos th, .pos td { border-bottom:1px solid #ddd; padding:4px 6px; }
 .pos th { background:#f0f4f1; text-align:left; font-size:10px; }
 .pos td.r { text-align:right; white-space:nowrap; }
 .sum { margin-top:12px; margin-left:auto; width:300px; }
 .sum table { width:100%; }
 .sum td { border:none; padding:3px 6px; }
 .sum .total { font-size:14px; font-weight:800; color:#14532d; border-top:2px solid #14532d; }
 .warn { background:#fff7ed; border:1px solid #f59e0b; color:#9a3412;
         padding:8px 10px; border-radius:6px; margin-top:12px; font-size:10px; }
 .sign { margin-top:34px; display:flex; justify-content:space-between; gap:40px; }
 .sign > div { flex:1; border-top:1px solid #333; padding-top:5px; font-size:10px; }
 footer { margin-top:24px; font-size:9px; color:#888; border-top:1px solid #eee; padding-top:8px; }
"""


def _addresses(devis):
    out = {}
    for a in (devis.addresses or []):
        role = (a.get("role") or "").lower()
        if "auftraggeber" in role or "besteller" in role or "maitre" in role or "committ" in role:
            out["besteller"] = a
        elif "auftragnehmer" in role or "unternehmer" in role or "entrepreneur" in role or "imprend" in role:
            out["unternehmer"] = a
    return out


def _summen(devis, profil, extras=None):
    extras = extras or []
    netto = 0.0
    for p in devis.positions:
        ep = _round_rappen(p.ep if p.ep is not None else 0.0)
        netto += _round_rappen(ep * (p.menge or 0.0))
    for ex in extras:
        ep = _round_rappen(float(ex.get("ep") or 0.0))
        netto += _round_rappen(ep * float(ex.get("menge") or 0.0))
    mwst_pct = float(profil.get("mwst_pct", 8.1) or 8.1)
    mwst = _round_rappen(netto * mwst_pct / 100.0)
    return netto, mwst, _round_rappen(netto + mwst), mwst_pct


def _positions_html(devis):
    rows = []
    for p in devis.positions:
        ep = _round_rappen(p.ep if p.ep is not None else 0.0)
        betrag = _round_rappen(ep * (p.menge or 0.0))
        rows.append(
            "<tr>"
            f"<td>{html.escape(p.pos_nr or '')}</td>"
            f"<td>{html.escape(p.text or '')}</td>"
            f"<td>{html.escape(p.einheit or '')}</td>"
            f"<td class='r'>{_chf(p.menge or 0.0)}</td>"
            f"<td class='r'>{_chf(ep)}</td>"
            f"<td class='r'>{_chf(betrag)}</td>"
            "</tr>"
        )
    return "\n".join(rows)


# ----------------------------------------------------------------------------
# Werkvertrag
# ----------------------------------------------------------------------------
def build_werkvertrag_html(devis: Devis, profil: dict, lang: str = "de",
                           bindend_bis: str = "", extras=None) -> str:
    betrieb = html.escape(str(profil.get("betrieb", "Ihr Betrieb") or "Ihr Betrieb"))
    meta = devis.meta or {}
    addr = _addresses(devis)
    best = addr.get("besteller", {})
    netto, mwst, brutto, mwst_pct = _summen(devis, profil, extras)
    projekt = html.escape(str(meta.get("project_name", "") or best.get("name", "") or ""))
    ort = html.escape(str(best.get("city", "") or meta.get("city", "") or ""))
    tr = _t

    besteller_html = (
        f"<td class='k'>{tr('besteller', lang)}</td>"
        f"<td>{html.escape(str(best.get('name','') or ''))}<br>"
        f"{html.escape(str(best.get('street','') or ''))}<br>"
        f"{html.escape(str(best.get('city','') or ''))}</td>"
    )
    unternehmer_html = (
        f"<td class='k'>{tr('unternehmer', lang)}</td>"
        f"<td>{betrieb}<br>{html.escape(str(profil.get('strasse','') or ''))}"
        f"<br>{html.escape(str(profil.get('ort','') or ''))}</td>"
    )

    bindend = (f"{tr('verbindlich_bis', lang)}: <b>{html.escape(bindend_bis)}</b>" if bindend_bis
               else f"<i>{tr('verbindlich', lang)}</i>")

    preis_block = (
        f"<table class='kv'><tr>{unternehmer_html}</tr><tr>{besteller_html}</tr>"
        f"<tr><td class='k'>{tr('objekt', lang)}</td><td>{projekt} ({ort})</td></tr>"
        f"<tr><td class='k'>{tr('preis', lang)}</td>"
        f"<td>Netto CHF {_chf(netto)} · MWSt {_chf(mwst_pct)}% = CHF {_chf(mwst)} · "
        f"<b>Brutto CHF {_chf(brutto)}</b></td></tr>"
        f"<tr><td class='k'>{tr('ausfuehrung', lang)}</td><td>____________________</td></tr>"
        f"<tr><td class='k'>{tr('zahlung', lang)}</td>"
        f"<td>30 Tage netto · Teilrechnungen nach Baufortschritt</td></tr>"
        f"<tr><td class='k'>{tr('haftung', lang)}</td><td>{tr('haftung_text', lang)}</td></tr>"
        f"</table>"
    )

    return f"""<!doctype html>
<html lang="{html.escape(lang)}"><head><meta charset="utf-8">
<title>{tr('werkvertrag', lang)} – {betrieb}</title>
<style>{COMMON_CSS}</style></head>
<body>
<header><div><div class="logo">{betrieb}</div>
  <div style="font-size:10px;color:#555">{html.escape(str(profil.get('gewerk','') or ''))}</div></div>
  <div class="meta"><div><b>{tr('werkvertrag', lang)}</b></div>
  <div>Devis-Nr: {html.escape(str(meta.get('devis_nr','') or ''))}</div>
  <div>Datum: {html.escape(str(meta.get('date','') or ''))}</div></div></header>
<h1>{tr('werkvertrag', lang)}</h1>
<div class="warn">{tr('hinweis', lang)}: SIA 118 gilt nur bei vertraglicher Einbeziehung.
Dieses Dokument ist eine Orientierungshilfe, keine Rechtsberatung.</div>
{preis_block}
<h2>{tr('leistung', lang)}</h2>
<table class="pos"><thead><tr><th>Nr</th><th>Bezeichnung</th><th>Einh.</th>
<th class="r">Menge</th><th class="r">EP (CHF)</th><th class="r">Betrag (CHF)</th></tr></thead>
<tbody>{_positions_html(devis)}</tbody></table>
<p style="margin-top:10px">{bindend}</p>
<div class="sign"><div>{tr('ort_datum', lang)}:<br><br><br>{tr('unterschrift', lang)} {tr('unternehmer', lang)}</div>
<div>{tr('ort_datum', lang)}:<br><br><br>{tr('unterschrift', lang)} {tr('besteller', lang)}</div></div>
<footer>Erstellt mit DevisPro · {betrieb}</footer>
</body></html>"""


# ----------------------------------------------------------------------------
# Abnahmeprotokoll
# ----------------------------------------------------------------------------
def build_abnahme_html(devis: Devis, profil: dict, lang: str = "de",
                       maengel=None, bedingt: bool = False) -> str:
    betrieb = html.escape(str(profil.get("betrieb", "Ihr Betrieb") or "Ihr Betrieb"))
    meta = devis.meta or {}
    addr = _addresses(devis)
    best = addr.get("besteller", {})
    projekt = html.escape(str(meta.get("project_name", "") or best.get("name", "") or ""))

    if maengel:
        ml = "".join(f"<li>{html.escape(str(m))}</li>" for m in maengel)
        maengel_block = f"<ul>{ml}</ul><p><b>{_t('bedingt', lang)}</b></p>"
    else:
        maengel_block = f"<p>{_t('kein_mangel', lang)}</p>"

    return f"""<!doctype html>
<html lang="{html.escape(lang)}"><head><meta charset="utf-8">
<title>{_t('abnahme', lang)} – {betrieb}</title>
<style>{COMMON_CSS}</style></head>
<body>
<header><div><div class="logo">{betrieb}</div></div>
  <div class="meta"><div><b>{_t('abnahme', lang)}</b></div>
  <div>Devis-Nr: {html.escape(str(meta.get('devis_nr','') or ''))}</div>
  <div>Datum: {html.escape(str(meta.get('date','') or ''))}</div></div></header>
<h1>{_t('abnahme', lang)}</h1>
<table class="kv">
 <tr><td class="k">{_t('objekt', lang)}</td><td>{projekt}</td></tr>
 <tr><td class="k">{_t('unternehmer', lang)}</td><td>{betrieb}</td></tr>
 <tr><td class="k">{_t('besteller', lang)}</td><td>{html.escape(str(best.get('name','') or ''))}</td></tr>
</table>
<h2>{_t('festgestellt', lang)}</h2>
{maengel_block}
<div class="sign"><div>{_t('ort_datum', lang)}:<br><br><br>{_t('unterschrift', lang)} {_t('unternehmer', lang)}</div>
<div>{_t('ort_datum', lang)}:<br><br><br>{_t('unterschrift', lang)} {_t('besteller', lang)}</div></div>
<footer>Erstellt mit DevisPro · {betrieb}</footer>
</body></html>"""


# ----------------------------------------------------------------------------
# Devis-/Offerten-Muster
# ----------------------------------------------------------------------------
def build_devis_muster_html(devis: Devis, profil: dict, lang: str = "de",
                            bindend_bis: str = "", extras=None) -> str:
    betrieb = html.escape(str(profil.get("betrieb", "Ihr Betrieb") or "Ihr Betrieb"))
    meta = devis.meta or {}
    addr = _addresses(devis)
    best = addr.get("besteller", {})
    netto, mwst, brutto, mwst_pct = _summen(devis, profil, extras)

    bindend = (f"{_t('verbindlich_bis', lang)}: <b>{html.escape(bindend_bis)}</b>" if bindend_bis
               else f"<i>{_t('verbindlich', lang)}</i>")

    return f"""<!doctype html>
<html lang="{html.escape(lang)}"><head><meta charset="utf-8">
<title>{_t('devis_muster', lang)} – {betrieb}</title>
<style>{COMMON_CSS}</style></head>
<body>
<header><div><div class="logo">{betrieb}</div>
  <div style="font-size:10px;color:#555">{html.escape(str(profil.get('gewerk','') or ''))}</div></div>
  <div class="meta"><div><b>{_t('devis_muster', lang)}</b></div>
  <div>Projekt: {html.escape(str(meta.get('project_name','') or best.get('name','') or ''))}</div>
  <div>Devis-Nr: {html.escape(str(meta.get('devis_nr','') or ''))}</div>
  <div>Datum: {html.escape(str(meta.get('date','') or ''))}</div></div></header>
<h1>{_t('devis_muster', lang)}</h1>
<div class="warn">{bindend}</div>
<table class="pos"><thead><tr><th>Nr</th><th>Bezeichnung</th><th>Einh.</th>
<th class="r">Menge</th><th class="r">EP (CHF)</th><th class="r">Betrag (CHF)</th></tr></thead>
<tbody>{_positions_html(devis)}</tbody></table>
<div class="sum"><table>
  <tr><td>Netto (CHF)</td><td class="r">{_chf(netto)}</td></tr>
  <tr><td>MWSt {_chf(mwst_pct)}% (CHF)</td><td class="r">{_chf(mwst)}</td></tr>
  <tr class="total"><td>Total (CHF)</td><td class="r">{_chf(brutto)}</td></tr>
</table></div>
<footer>Erstellt mit DevisPro · {betrieb}</footer>
</body></html>"""


# ----------------------------------------------------------------------------
# PDF-Export (Fallback: HTML)
# ----------------------------------------------------------------------------
def export_pdf(html_doc: str, out_path: str) -> bool:
    wk = shutil.which("wkhtmltopdf")
    if wk:
        try:
            subprocess.run([wk, "--quiet", "-", out_path],
                           input=html_doc.encode("utf-8"), timeout=30, check=True)
            return True
        except Exception:
            pass
    html_path = out_path
    if not html_path.endswith(".html"):
        html_path = out_path + ".html"
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_doc)
    return False


def build(typ: str, devis: Devis, profil: dict, lang: str = "de", **kw) -> str:
    if typ == "werkvertrag":
        return build_werkvertrag_html(devis, profil, lang, bindend_bis=kw.get("bindend_bis", ""), extras=kw.get("extras"))
    if typ == "abnahme":
        return build_abnahme_html(devis, profil, lang, maengel=kw.get("maengel"), bedingt=kw.get("bedingt", False))
    if typ == "devis_muster":
        return build_devis_muster_html(devis, profil, lang, bindend_bis=kw.get("bindend_bis", ""), extras=kw.get("extras"))
    raise ValueError(f"Unbekannter Dokumenttyp: {typ}")


# ----------------------------------------------------------------------------
# Echtes PDF via dependency-freiem Generator (pdf_native) – kein wkhtmltopdf noetig
# ----------------------------------------------------------------------------
def build_pdf(typ: str, devis: Devis, profil: dict, lang: str = "de", **kw) -> bytes:
    from . import pdf_native as PN
    betrieb = str(profil.get("betrieb", "Ihr Betrieb") or "Ihr Betrieb")
    meta = devis.meta or {}
    addr = _addresses(devis)
    best = addr.get("besteller", {})
    netto, mwst, brutto, mwst_pct = _summen(devis, profil, kw.get("extras"))
    gewerk = _t("unternehmer", lang)  # wird unten ueberschrieben
    L = {k: _t(k, lang) for k in _t.__globals__ if False}  # noop
    TITEL = {
        "werkvertrag": _t("werkvertrag", lang),
        "devis_muster": _t("devis_muster", lang),
        "abnahme": _t("abnahme", lang),
    }.get(typ, "")
    projekt = str(meta.get("project_name", "") or best.get("name", "") or "")

    pdf = PN.PDF()
    pdf.heading(TITEL)
    pdf.footer(f"Erstellt mit DevisPro - {betrieb}")

    if typ in ("werkvertrag", "devis_muster"):
        pdf.kv([
            (_t("unternehmer", lang), f"{betrieb}\n{profil.get('strasse','')}\n{profil.get('ort','')}"),
            (_t("besteller", lang), f"{best.get('name','')}\n{best.get('street','')}\n{best.get('city','')}"),
            (_t("objekt", lang), projekt),
        ])
        pdf.subtitle(_t("leistung", lang))
        rows = []
        for p in devis.positions:
            ep = _round_rappen(p.ep if p.ep is not None else 0.0)
            bet = _round_rappen(ep * (p.menge or 0.0))
            rows.append([str(p.pos_nr or ""), str(p.text or ""), str(p.einheit or ""),
                         _chf(p.menge or 0.0), _chf(ep), _chf(bet)])
        pdf.table(["Nr", "Bezeichnung", "Einh.", "Menge", "EP (CHF)", "Betrag"],
                  rows, widths=[40, 250, 45, 55, 60, 60], size=9)
        pdf.summary([
            ("Netto (CHF)", _chf(netto), False),
            (f"MWSt {_chf(mwst_pct)}% (CHF)", _chf(mwst), False),
            ("Total (CHF)", _chf(brutto), True),
        ])
        if kw.get("bindend_bis"):
            pdf.text(f"{_t('verbindlich_bis', lang)}: {kw['bindend_bis']}")
        else:
            pdf.note(_t("verbindlich", lang))
        pdf.spacer(8)
        pdf.sign([_t("unternehmer", lang), _t("besteller", lang)])
        # Swiss QR-Code einbetten (reine Stdlib, scannbar) - Option "qr=1"
        if kw.get("qr"):
            try:
                from . import qr_rechnung as qr_mod
                from . import qr_render as QR
                from . import rechnung as rmod
                r = rmod.from_devis(devis, profil, kw.get("rnr", f"O-{meta.get('project_name','')}"),
                                    str(meta.get("date", "")), kw.get("faellig", ""))
                matrix, _ = qr_mod.qr_matrix_aus_rechnung(r)
                pdf.image(matrix, PN.PAGE_W - PN.MARGIN_R - 130, PN.MARGIN_B - 4, 130)
            except Exception:
                pass

    elif typ == "abnahme":
        pdf.kv([
            (_t("objekt", lang), projekt),
            (_t("unternehmer", lang), betrieb),
            (_t("besteller", lang), str(best.get("name", "") or "")),
        ])
        pdf.subtitle(_t("festgestellt", lang))
        maengel = kw.get("maengel")
        if maengel:
            for m in maengel:
                pdf.text(f"- {m}")
            if kw.get("bedingt"):
                pdf.note(_t("bedingt", lang))
        else:
            pdf.text(_t("kein_mangel", lang))
        pdf.spacer(8)
        pdf.sign([_t("unternehmer", lang), _t("besteller", lang)])

    return pdf.build()

