"""Druckfertige Offerte (Angebot) als HTML/A4 und optional PDF.

Reine Stdlib + optionalem wkhtmltopdf (falls installiert). Liefert immer
ein druckbares HTML zurueck; wenn wkhtmltopdf vorhanden ist, zusaetzlich
eine echte PDF-Datei. Kein externes Paket noetig.
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
    """Auf Rappen runden (wie SIA-Export), damit Summen konsistent sind."""
    try:
        return round(float(v) * 100) / 100.0
    except (TypeError, ValueError):
        return 0.0


def build_offerte_html(devis: Devis, profil: dict, extras=None, lang: str = "de") -> str:
    """Erzeugt druckfertiges HTML-Angebot (A4)."""
    extras = extras or []
    meta = devis.meta or {}
    betrieb = html.escape(str(profil.get("betrieb", "Ihr Betrieb") or "Ihr Betrieb"))
    gewerk = html.escape(str(profil.get("gewerk", "") or ""))
    kanton = html.escape(str(profil.get("kanton", "") or ""))
    mwst_pct = float(profil.get("mwst_pct", 8.1) or 8.1)

    # Summen mit Rappen-Rundung, damit sie exakt zur SIA-Datei passen
    pos_rows = []
    netto_sum = 0.0
    for p in devis.positions:
        ep = _round_rappen(p.ep if p.ep is not None else 0.0)
        menge = p.menge or 0.0
        betrag = _round_rappen(ep * menge)
        netto_sum += betrag
        pos_rows.append(
            "<tr>"
            f"<td class='nr'>{html.escape(p.pos_nr or '')}</td>"
            f"<td>{html.escape(p.text or '')}</td>"
            f"<td class='c'>{html.escape(p.einheit or '')}</td>"
            f"<td class='r'>{_chf(menge)}</td>"
            f"<td class='r'>{_chf(ep)}</td>"
            f"<td class='r'>{_chf(betrag)}</td>"
            f"<td class='c'>{'✓' if not getattr(p, 'requires_review', False) else '⚠'}</td>"
            "</tr>"
        )

    extra_rows = []
    extra_sum = 0.0
    for i, ex in enumerate(extras, start=1):
        ep = _round_rappen(float(ex.get("ep") or 0.0))
        menge = float(ex.get("menge") or 0.0)
        betrag = _round_rappen(float(ex.get("betrag") or (ep * menge)))
        extra_sum += betrag
        extra_rows.append(
            "<tr class='zusatz'>"
            f"<td class='nr'>Z{i:03d}</td>"
            f"<td>{html.escape('[Zusatz] ' + str(ex.get('text') or 'Ergänzung'))}</td>"
            f"<td class='c'>{html.escape(str(ex.get('einheit') or ''))}</td>"
            f"<td class='r'>{_chf(menge)}</td>"
            f"<td class='r'>{_chf(ep)}</td>"
            f"<td class='r'>{_chf(betrag)}</td>"
            "<td class='c'>✓</td></tr>"
        )

    zwischen = _round_rappen(netto_sum + extra_sum)
    mwst = _round_rappen(zwischen * mwst_pct / 100.0)
    brutto = _round_rappen(zwischen + mwst)

    titel = {
        "de": "Offerte / Devis",
        "fr": "Offre / Devis",
        "it": "Offerta / Devis",
    }.get(lang, "Offerte / Devis")

    reviewed = sum(1 for p in devis.positions if getattr(p, "requires_review", False))

    hinweis = ""
    if reviewed:
        hinweis = (
            "<p class='warn'>⚠ {0} Position(en) mit unsicherem Match – vor Versand "
            "durch Fachkraft prüfen.</p>"
        ).format(reviewed)

    rows_html = "\n".join(pos_rows + extra_rows)
    today = meta.get("date") or ""

    return f"""<!doctype html>
<html lang="{html.escape(lang)}"><head><meta charset="utf-8">
<title>{titel} – {betrieb}</title>
<style>
 @page {{ size: A4; margin: 16mm; }}
 * {{ box-sizing: border-box; }}
 body {{ font-family: -apple-system, system-ui, "Helvetica Neue", Arial, sans-serif;
        color:#1a1a1a; font-size: 11px; margin:0; }}
 .kop f {{ }}
 header {{ display:flex; justify-content:space-between; align-items:flex-start;
          border-bottom:3px solid #14532d; padding-bottom:10px; margin-bottom:14px; }}
 .logo {{ font-size:20px; font-weight:800; color:#14532d; }}
 .meta {{ text-align:right; font-size:10px; color:#555; }}
 h1 {{ font-size:15px; margin:0 0 4px; }}
 table {{ width:100%; border-collapse:collapse; margin-top:8px; }}
 th,td {{ border-bottom:1px solid #ddd; padding:5px 6px; vertical-align:top; }}
 th {{ background:#f0f4f1; text-align:left; font-size:10px; }}
 td.nr {{ font-family:ui-monospace,Menlo,monospace; color:#666; width:70px; }}
 td.c {{ text-align:center; width:24px; }}
 td.r {{ text-align:right; white-space:nowrap; }}
 tr.zusatz td {{ background:#fffbeb; }}
 .sum {{ margin-top:14px; margin-left:auto; width:280px; }}
 .sum table {{ width:100%; }}
 .sum td {{ border:none; padding:3px 6px; }}
 .sum .total {{ font-size:14px; font-weight:800; color:#14532d; border-top:2px solid #14532d; }}
 .warn {{ background:#fff7ed; border:1px solid #f59e0b; color:#9a3412;
         padding:8px 10px; border-radius:6px; margin-top:12px; }}
 footer {{ margin-top:24px; font-size:9px; color:#888; border-top:1px solid #eee; padding-top:8px; }}
</style></head>
<body>
<header>
  <div><div class="logo">{betrieb}</div>
       <div style="font-size:10px;color:#555">{gewerk} · {kanton}</div></div>
  <div class="meta">
    <div><b>{titel}</b></div>
    <div>Projekt: {html.escape(str(meta.get('project_name','') or ''))}</div>
    <div>Devis-Nr: {html.escape(str(meta.get('devis_nr','') or ''))}</div>
    <div>Datum: {html.escape(str(today))}</div>
  </div>
</header>
<h1>{titel}</h1>
{hinweis}
<table>
  <thead><tr><th>Nr</th><th>Bezeichnung</th><th class='c'>Einheit</th>
  <th class='r'>Menge</th><th class='r'>EP (CHF)</th><th class='r'>Betrag (CHF)</th>
  <th class='c'>✓</th></tr></thead>
  <tbody>
  {rows_html}
  </tbody>
</table>
<div class="sum"><table>
  <tr><td>Zwischensumme (Netto)</td><td class='r'>{_chf(zwischen)}</td></tr>
  <tr><td>MWSt {_chf(mwst_pct)}%</td><td class='r'>{_chf(mwst)}</td></tr>
  <tr class='total'><td>Total (brutto)</td><td class='r'>{_chf(brutto)}</td></tr>
</table></div>
<footer>
  Erstellt mit DevisPro · Automatische SIA-451 Bepreisung · {betrieb}
</footer>
</body></html>"""


def export_pdf(devis: Devis, profil: dict, out_path: str, extras=None, lang: str = "de") -> bool:
    """Versucht echtes PDF via wkhtmltopdf; True wenn gelungen, sonst False
    (dann liegt unter out_path eine .html-Fallback-Datei)."""
    html_doc = build_offerte_html(devis, profil, extras=extras, lang=lang)
    wk = shutil.which("wkhtmltopdf")
    if wk:
        try:
            subprocess.run([wk, "--quiet", "-", out_path],
                           input=html_doc.encode("utf-8"), timeout=30, check=True)
            return True
        except Exception:
            pass
    # Fallback: HTML speichern (relaxte Endung)
    html_path = out_path
    if not html_path.endswith(".html"):
        html_path = out_path + ".html"
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_doc)
    return False
