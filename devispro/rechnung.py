"""Rechnungs-Modul (Abacus-Niveau): Angebot -> Rechnung mit Zahlungsplan.

Erzeugt:
  - reine Datenstruktur Rechnung (Positionen, Zwischensumme, MWSt, Skonto,
    Rabatt, Teilzahlungen/Zahlungsplan)
  - HTML-Ansicht (A4, druckbar) und echtes PDF via pdf_native
  - kann aus einem bepreisten Devis abgeleitet werden

Ohne Fremdpakete; PDF dependency-frei.
"""
import html
from dataclasses import dataclass, field
from typing import List, Optional

from .models import Devis


def _chf(value) -> str:
    try:
        v = float(value or 0.0)
    except (TypeError, ValueError):
        v = 0.0
    return f"{v:,.2f}".replace(",", "'")


def _r2(v: float) -> float:
    try:
        return round(float(v) * 100) / 100.0
    except (TypeError, ValueError):
        return 0.0


@dataclass
class RechnungsPosition:
    nr: str
    text: str
    menge: float = 0.0
    einheit: str = ""
    ep: float = 0.0
    betrag: float = 0.0


@dataclass
class Teilzahlung:
    faellig: str          # Datum/Text
    betrag: float
    grund: str = ""       # z.B. "1. Rate / Schlussrechnung"


@dataclass
class Rechnung:
    rechnungs_nr: str
    datum: str
    faellig: str
    betrieb: str = ""
    kunde: str = ""
    objekt: str = ""
    positionen: List[RechnungsPosition] = field(default_factory=list)
    mwst_pct: float = 8.1
    rabatt_pct: float = 0.0       # optionaler Gesamtrabatt
    skonto_pct: float = 0.0       # optionaler Skonto bei Fruehzahlung
    skonto_bis: str = ""
    zahlungsplan: List[Teilzahlung] = field(default_factory=list)
    notiz: str = ""

    # -- abgeleitete Summen --
    def netto(self) -> float:
        return _r2(sum(p.betrag for p in self.positionen))

    def rabatt_betrag(self) -> float:
        return _r2(self.netto() * self.rabatt_pct / 100.0)

    def netto_nach_rabatt(self) -> float:
        return _r2(self.netto() - self.rabatt_betrag())

    def mwst(self) -> float:
        return _r2(self.netto_nach_rabatt() * self.mwst_pct / 100.0)

    def brutto(self) -> float:
        return _r2(self.netto_nach_rabatt() + self.mwst())

    def skonto_betrag(self) -> float:
        return _r2(self.brutto() * self.skonto_pct / 100.0)

    def brutto_mit_skonto(self) -> float:
        return _r2(self.brutto() - self.skonto_betrag())


def from_devis(devis: Devis, profil: dict, rechnungs_nr: str, datum: str,
               faellig: str, **kw) -> "Rechnung":
    pos = []
    for i, p in enumerate(devis.positions, start=1):
        ep = _r2(p.ep if p.ep is not None else 0.0)
        betrag = _r2(p.betrag if p.betrag is not None else 0.0)
        if betrag == 0.0 and ep != 0.0 and (p.menge or 0.0):
            betrag = _r2(ep * (p.menge or 0.0))
        if ep == 0.0 and betrag != 0.0 and (p.menge or 0.0):
            ep = _r2(betrag / (p.menge or 1.0))
        pos.append(RechnungsPosition(
            nr=str(p.pos_nr or i),
            text=str(p.text or ""),
            menge=p.menge or 0.0,
            einheit=str(p.einheit or ""),
            ep=ep, betrag=betrag,
        ))
    addr = {}
    for a in (devis.addresses or []):
        role = (a.get("role") or "").lower()
        if "auftraggeber" in role or "besteller" in role or "maitre" in role or "committ" in role:
            addr["besteller"] = a
    best = addr.get("besteller", {})
    return Rechnung(
        rechnungs_nr=rechnungs_nr, datum=datum, faellig=faellig,
        betrieb=str(profil.get("betrieb", "") or ""),
        kunde=str(best.get("name", "") or ""),
        objekt=str(devis.meta.get("project_name", "") or best.get("name", "") or ""),
        positionen=pos,
        mwst_pct=float(profil.get("mwst_pct", 8.1) or 8.1),
        rabatt_pct=float(kw.get("rabatt_pct", 0.0) or 0.0),
        skonto_pct=float(kw.get("skonto_pct", 0.0) or 0.0),
        skonto_bis=str(kw.get("skonto_bis", "") or ""),
        notiz=str(kw.get("notiz", "") or ""),
    )


# ----------------------------------------------------------------------------
# HTML
# ----------------------------------------------------------------------------
def build_html(r: Rechnung, lang: str = "de") -> str:
    T = {
        "de": {"rechnung": "Rechnung", "nr": "Rechnung Nr.", "datum": "Datum", "faellig": "Fällig bis",
               "empfaenger": "Empfänger", "objekt": "Objekt", "pos": "Positionen",
               "nr2": "Nr", "bez": "Bezeichnung", "einh": "Einh.", "menge": "Menge",
               "ep": "EP (CHF)", "betrag": "Betrag", "zwischen": "Zwischensumme (Netto)",
               "rabatt": "Rabatt", "mwst": "MWSt", "total": "Total (brutto)",
               "skonto": "Skonto", "zahlung": "Zahlungsplan", "faellig": "Fällig",
               "grund": "Grund", "notiz": "Notiz", "betrag2": "Betrag (CHF)"},
        "fr": {"rechnung": "Facture", "nr": "Facture N°", "datum": "Date", "faellig": "Échéance",
               "empfaenger": "Destinataire", "objekt": "Objet", "pos": "Positions",
               "nr2": "Nr", "bez": "Désignation", "einh": "Unité", "menge": "Qté",
               "ep": "PU (CHF)", "betrag": "Montant", "zwischen": "Sous-total (net)",
               "rabatt": "Remise", "mwst": "TVA", "total": "Total (brut)",
               "skonto": "Escompte", "zahlung": "Plan de paiement", "faellig": "Échéance",
               "grund": "Motif", "notiz": "Note", "betrag2": "Montant (CHF)"},
        "it": {"rechnung": "Fattura", "nr": "Fattura N°", "datum": "Data", "faellig": "Scadenza",
               "empfaenger": "Destinatario", "objekt": "Oggetto", "pos": "Posizioni",
               "nr2": "Nr", "bez": "Descrizione", "einh": "Unità", "menge": "Qtà",
               "ep": "PU (CHF)", "betrag": "Importo", "zwischen": "Subtotale (netto)",
               "rabatt": "Sconto", "mwst": "IVA", "total": "Totale (lordo)",
               "skonto": "Sconto cassa", "zahlung": "Piano di pagamento", "faellig": "Scadenza",
               "grund": "Motivo", "notiz": "Nota", "betrag2": "Importo (CHF)"},
    }.get(lang, {})
    rows = "".join(
        f"<tr><td>{html.escape(p.nr)}</td><td>{html.escape(p.text)}</td>"
        f"<td>{html.escape(p.einheit)}</td><td class='r'>{_chf(p.menge)}</td>"
        f"<td class='r'>{_chf(p.ep)}</td><td class='r'>{_chf(p.betrag)}</td></tr>"
        for p in r.positionen
    )
    zplan = ""
    if r.zahlungsplan:
        zr = "".join(
            f"<tr><td>{html.escape(z.faellig)}</td><td>{html.escape(z.grund)}</td>"
            f"<td class='r'>{_chf(z.betrag)}</td></tr>"
            for z in r.zahlungsplan
        )
        zplan = (f"<h2>{T['zahlung']}</h2><table class='pos'>"
                 f"<thead><tr><th>{T['faellig']}</th><th>{T['grund']}</th>"
                 f"<th class='r'>{T['betrag2']}</th></tr></thead><tbody>{zr}</tbody></table>")
    rab = (f"<tr><td>{T['rabatt']} {_chf(r.rabatt_pct)}%</td><td class='r'>-{_chf(r.rabatt_betrag())}</td></tr>"
           ) if r.rabatt_pct else ""
    sk = (f"<tr class='total'><td>{T['skonto']} {_chf(r.skonto_pct)}% (bis {html.escape(r.skonto_bis)})</td>"
          f"<td class='r'>-{_chf(r.skonto_betrag())}</td></tr>"
          ) if r.skonto_pct else ""
    notiz = f"<p class='note'>{html.escape(r.notiz)}</p>" if r.notiz else ""
    qr_uri = qr_data_uri(r)
    return f"""<!doctype html>
<html lang="{lang}"><head><meta charset="utf-8">
<title>{T['rechnung']} {html.escape(r.rechnungs_nr)}</title>
<style>
 @page {{ size: A4; margin: 16mm; }}
 * {{ box-sizing: border-box; }}
 body {{ font-family: -apple-system, system-ui, "Helvetica Neue", Arial, sans-serif;
        color:#1a1a1a; font-size: 11px; margin:0; }}
 header {{ display:flex; justify-content:space-between; align-items:flex-start;
          border-bottom:3px solid #14532d; padding-bottom:10px; margin-bottom:14px; }}
 .logo {{ font-size:20px; font-weight:800; color:#14532d; }}
 .meta {{ text-align:right; font-size:10px; color:#555; }}
 h1 {{ font-size:16px; margin:0 0 4px; }}
 h2 {{ font-size:12px; margin:16px 0 5px; border-bottom:1px solid #ddd; padding-bottom:3px; }}
 table {{ width:100%; border-collapse:collapse; margin-top:8px; }}
 th,td {{ border-bottom:1px solid #ddd; padding:5px 6px; vertical-align:top; }}
 th {{ background:#f0f4f1; text-align:left; font-size:10px; }}
 td.r {{ text-align:right; white-space:nowrap; }}
 .sum {{ margin-top:14px; margin-left:auto; width:300px; }}
 .sum table {{ width:100%; }}
 .sum td {{ border:none; padding:3px 6px; }}
 .sum .total {{ font-size:14px; font-weight:800; color:#14532d; border-top:2px solid #14532d; }}
 .note {{ background:#fff7ed; border:1px solid #f59e0b; color:#9a3412;
         padding:8px 10px; border-radius:6px; margin-top:12px; font-size:10px; }}
 footer {{ margin-top:24px; font-size:9px; color:#888; border-top:1px solid #eee; padding-top:8px; }}
</style></head>
<body>
<header><div><div class="logo">{html.escape(r.betrieb)}</div></div>
  <div class="meta"><div><b>{T['rechnung']}</b></div>
  <div>{T['nr']}: {html.escape(r.rechnungs_nr)}</div>
  <div>{T['datum']}: {html.escape(r.datum)}</div>
  <div>{T['faellig']}: {html.escape(r.faellig)}</div></div></header>
<h1>{T['rechnung']} {html.escape(r.rechnungs_nr)}</h1>
<table class="kv"><tr><td class="k">{T['empfaenger']}</td><td>{html.escape(r.kunde)}</td></tr>
<tr><td class="k">{T['objekt']}</td><td>{html.escape(r.objekt)}</td></tr></table>
<h2>{T['pos']}</h2>
<table class="pos"><thead><tr><th>{T['nr2']}</th><th>{T['bez']}</th><th>{T['einh']}</th>
<th class="r">{T['menge']}</th><th class="r">{T['ep']}</th><th class="r">{T['betrag']}</th></tr></thead>
<tbody>{rows}</tbody></table>
<div class="sum"><table>
  <tr><td>{T['zwischen']}</td><td class="r">{_chf(r.netto())}</td></tr>
  {rab}
  <tr><td>{T['mwst']} {_chf(r.mwst_pct)}%</td><td class="r">{_chf(r.mwst())}</td></tr>
  <tr class="total"><td>{T['total']}</td><td class="r">{_chf(r.brutto())}</td></tr>
  {sk}
</table></div>
{zplan}
{notiz}
<div style="margin-top:18px;display:flex;gap:14px;align-items:flex-start">
  <div><div style="font-size:10px;font-weight:700;color:#14532d">Swiss QR-Rechnung</div>
  <img src="{qr_uri}" alt="Swiss QR" style="width:140px;height:140px;border:1px solid #ccc;background:#fff"/>
  <div style="font-size:8px;color:#666;max-width:150px">Scannen mit Banking-App zur Zahlung</div></div>
</div>
<footer>Erstellt mit DevisPro - {html.escape(r.betrieb)}</footer>
</body></html>"""


def qr_data_uri(r: "Rechnung") -> str:
    """Liefert das Swiss-QR als base64 PNG-Data-URI fuer HTML-Einbettung."""
    try:
        from . import qr_rechnung as qr_mod
        import base64
        matrix, _ = qr_mod.qr_matrix_aus_rechnung(r)
        png = qr_mod.QR.to_png_bytes(matrix, scale=4) if hasattr(qr_mod, "QR") else None
        # qr_rechnung hat qr_render nicht direkt; ueber qr_render importieren
        from . import qr_render as QR
        png = QR.to_png_bytes(matrix, scale=4)
        return "data:image/png;base64," + base64.b64encode(png).decode("ascii")
    except Exception:
        return ""


# ----------------------------------------------------------------------------\
# PDF (dependency-frei)
# ----------------------------------------------------------------------------
def build_pdf(r: Rechnung, lang: str = "de") -> bytes:
    from . import pdf_native as PN
    from . import qr_rechnung as qr_mod
    T = {
        "de": {"rechnung": "Rechnung", "nr": "Rechnung Nr.", "datum": "Datum", "faellig": "Faellig bis",
               "empfaenger": "Empfaenger", "objekt": "Objekt", "pos": "Positionen",
               "zwischen": "Zwischensumme (Netto)", "rabatt": "Rabatt", "mwst": "MWSt",
               "total": "Total (brutto)", "skonto": "Skonto", "zahlung": "Zahlungsplan",
               "faellig": "Faellig", "grund": "Grund", "notiz": "Notiz", "betrag": "Betrag"},
        "fr": {"rechnung": "Facture", "nr": "Facture N°", "datum": "Date", "faellig": "Echeance",
               "empfaenger": "Destinataire", "objekt": "Objet", "pos": "Positions",
               "zwischen": "Sous-total (net)", "rabatt": "Remise", "mwst": "TVA",
               "total": "Total (brut)", "skonto": "Escompte", "zahlung": "Plan de paiement",
               "faellig": "Echeance", "grund": "Motif", "notiz": "Note", "betrag": "Montant"},
        "it": {"rechnung": "Fattura", "nr": "Fattura N°", "datum": "Data", "faellig": "Scadenza",
               "empfaenger": "Destinatario", "objekt": "Oggetto", "pos": "Posizioni",
               "zwischen": "Subtotale (netto)", "rabatt": "Sconto", "mwst": "IVA",
               "total": "Totale (lordo)", "skonto": "Sconto cassa", "zahlung": "Piano di pagamento",
               "faellig": "Scadenza", "grund": "Motivo", "notiz": "Nota", "betrag": "Importo"},
    }.get(lang, {})
    pdf = PN.PDF()
    pdf.heading(f"{T['rechnung']} {r.rechnungs_nr}")
    pdf.footer(f"Erstellt mit DevisPro - {r.betrieb}")
    pdf.kv([
        (T["nr"], f"{r.rechnungs_nr}\n{r.datum}\n{T['faellig']}: {r.faellig}"),
        (T["empfaenger"], r.kunde),
        (T["objekt"], r.objekt),
    ])
    pdf.subtitle(T["pos"])
    rows = [[p.nr, p.text, p.einheit, _chf(p.menge), _chf(p.ep), _chf(p.betrag)] for p in r.positionen]
    pdf.table(["Nr", "Bezeichnung", "Einh.", "Menge", "EP", "Betrag"], rows,
              widths=[40, 250, 45, 55, 60, 60], size=9)
    summ = [[T["zwischen"], _chf(r.netto())]]
    if r.rabatt_pct:
        summ.append([f"{T['rabatt']} {_chf(r.rabatt_pct)}%", "-" + _chf(r.rabatt_betrag())])
    summ.append([f"{T['mwst']} {_chf(r.mwst_pct)}%", _chf(r.mwst())])
    pdf.summary([(k, v, False) for k, v in summ] + [(T["total"], _chf(r.brutto()), True)])
    if r.zahlungsplan:
        pdf.subtitle(T["zahlung"])
        zr = [[z.faellig, z.grund, _chf(z.betrag)] for z in r.zahlungsplan]
        pdf.table([T["faellig"], T["grund"], T["betrag"]], zr, widths=[120, 260, 100], size=9)
    if r.notiz:
        pdf.note(r.notiz)
    # Swiss QR-Code einbetten (reine Stdlib, scannbar)
    try:
        matrix, _ = qr_mod.qr_matrix_aus_rechnung(r)
        # unten rechts, 46mm ~ 130pt
        pdf.image(matrix, PN.PAGE_W - PN.MARGIN_R - 130, PN.MARGIN_B - 4, 130)
    except Exception:
        pass
    return pdf.build()
