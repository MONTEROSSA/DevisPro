"""Mahnwesen: 1./2./3. Mahnung aus einer Rechnung.

Erzeugt Mahnungen mit Verzugszins (OR 104) und Gebuehr, als HTML + PDF.
Reine Stdlib. Die Rechnung wird ueber devispro.rechnung geladen.
"""
import html
from dataclasses import dataclass, field
from typing import List

from . import rechnung as rmod


def _chf(v) -> str:
    try:
        return f"{float(v or 0.0):,.2f}".replace(",", "'")
    except (TypeError, ValueError):
        return "0.00"


def _r2(v):
    try:
        return round(float(v) * 100) / 100.0
    except (TypeError, ValueError):
        return 0.0


# OR 104: Verzugszins 5% ab Faelligkeit (Default, kann im Profil ueberschrieben)
DEFAULT_ZINS_PCT = 5.0
MAHNGEBUEHR = 30.0  # pauschal je Mahnung (OR 106/107 kulanzweise)


@dataclass
class Mahnung:
    stufe: int                 # 1, 2, 3
    rechnungs_nr: str
    datum: str
    faellig: str
    betrieb: str = ""
    kunde: str = ""
    objekt: str = ""
    offen_brutto: float = 0.0
    zins_pct: float = DEFAULT_ZINS_PCT
    zins_betrag: float = 0.0
    gebuehr: float = MAHNGEBUEHR
    notiz: str = ""

    def total(self) -> float:
        return _r2(self.offen_brutto + self.zins_betrag + self.gebuehr)


def berechnen(r: "rmod.Rechnung", stufe: int, datum: str,
              zins_pct: float = DEFAULT_ZINS_PCT, tage_ueberfaellig: int = 30,
              gebuehr: float = MAHNGEBUEHR) -> Mahnung:
    stufe = max(1, min(3, int(stufe)))
    zins_betrag = _r2(r.brutto() * zins_pct / 100.0 * (tage_ueberfaellig / 365.0)) if stufe >= 2 else 0.0
    return Mahnung(
        stufe=stufe,
        rechnungs_nr=r.rechnungs_nr,
        datum=datum,
        faellig=r.faellig,
        betrieb=r.betrieb,
        kunde=r.kunde,
        objekt=r.objekt,
        offen_brutto=r.brutto(),
        zins_pct=zins_pct,
        zins_betrag=zins_betrag,
        gebuehr=gebuehr if stufe >= 2 else 0.0,  # 1. Mahnung ohne Gebuehr
    )


_T = {
    "de": {"mahnung": "Mahnung", "stufe": "Mahnstufe", "rn": "Rechnung Nr.",
           "datum": "Datum", "faellig": "Ursprünglich fällig", "empfaenger": "Empfänger",
           "objekt": "Objekt", "offen": "Offener Betrag (brutto)", "zins": "Verzugszins",
           "gebuehr": "Mahngebühr", "total": "Total einzuzahlen", "notiz": "Hinweis",
           "text1": "Wir bitten höflich, die offene Rechnung zu begleichen.",
           "text2": "Zweite Mahnung: Bitte begleichen Sie umgehend.",
           "text3": "Letzte Mahnung vor Inkasso. Betrag ist sofort fällig."},
    "fr": {"mahnung": "Rappel", "stufe": "Niveau", "rn": "Facture N°",
           "datum": "Date", "faellig": "Échéance initiale", "empfaenger": "Destinataire",
           "objekt": "Objet", "offen": "Montant ouvert (brut)", "zins": "Intérêts moratoires",
           "gebuehr": "Frais de rappel", "total": "Total à payer", "notiz": "Note",
           "text1": "Nous vous prions de régler la facture ouverte.",
           "text2": "Second rappel : veuillez régler d'urgence.",
           "text3": "Dernier rappel avant encaissement. Montant dû immédiatement."},
    "it": {"mahnung": "Sollecito", "stufe": "Livello", "rn": "Fattura N°",
           "datum": "Data", "faellig": "Scadenza iniziale", "empfaenger": "Destinatario",
           "objekt": "Oggetto", "offen": "Importo aperto (lordo)", "zins": "Interessi di mora",
           "gebuehr": "Spese di sollecito", "total": "Totale da pagare", "notiz": "Nota",
           "text1": "La preghiamo di saldare la fattura aperta.",
           "text2": "Secondo sollecito: La preghiamo di saldare urgentemente.",
           "text3": "Ultimo sollecito prima dell'incasso. Importo esigibile subito."},
}


def build_html(m: Mahnung, lang: str = "de") -> str:
    t = _T.get(lang, {})
    texte = [t.get("text1", ""), t.get("text2", ""), t.get("text3", "")]
    hinweis = texte[m.stufe - 1] if 1 <= m.stufe <= 3 else ""
    return f"""<!doctype html>
<html lang="{lang}"><head><meta charset="utf-8">
<title>{t['mahnung']} {m.stufe} – {html.escape(m.betrieb)}</title>
<style>
 @page {{ size: A4; margin: 16mm; }}
 body {{ font-family: -apple-system, system-ui, Arial, sans-serif; color:#1a1a1a; font-size:11px; }}
 header {{ display:flex; justify-content:space-between; border-bottom:3px solid #b91c1c; padding-bottom:10px; margin-bottom:14px; }}
 .logo {{ font-size:20px; font-weight:800; color:#b91c1c; }}
 h1 {{ font-size:16px; margin:0 0 10px; }}
 table {{ width:100%; border-collapse:collapse; margin-top:10px; }}
 td {{ border-bottom:1px solid #ddd; padding:5px 6px; }}
 td.k {{ background:#f7f7f7; width:36%; font-weight:600; }}
 .sum {{ margin-left:auto; width:300px; margin-top:14px; }}
 .sum table {{ width:100%; }}
 .sum .total {{ font-size:14px; font-weight:800; color:#b91c1c; border-top:2px solid #b91c1c; }}
 .note {{ background:#fef2f2; border:1px solid #fca5a5; color:#7f1d1d; padding:8px 10px; border-radius:6px; margin-top:12px; }}
 footer {{ margin-top:24px; font-size:9px; color:#888; border-top:1px solid #eee; padding-top:8px; }}
</style></head>
<body>
<header><div><div class="logo">{html.escape(m.betrieb)}</div></div>
 <div class="meta"><div><b>{t['mahnung']} {m.stufe}</b></div>
 <div>{t['rn']}: {html.escape(m.rechnungs_nr)}</div>
 <div>{t['datum']}: {html.escape(m.datum)}</div></div></header>
<h1>{t['mahnung']} {m.stufe}</h1>
<table>
 <tr><td class="k">{t['empfaenger']}</td><td>{html.escape(m.kunde)}</td></tr>
 <tr><td class="k">{t['objekt']}</td><td>{html.escape(m.objekt)}</td></tr>
 <tr><td class="k">{t['faellig']}</td><td>{html.escape(m.faellig)}</td></tr>
</table>
<div class="sum"><table>
 <tr><td>{t['offen']}</td><td class="r">{_chf(m.offen_brutto)}</td></tr>
 <tr><td>{t['zins']} {_chf(m.zins_pct)}%</td><td class="r">{_chf(m.zins_betrag)}</td></tr>
 <tr><td>{t['gebuehr']}</td><td class="r">{_chf(m.gebuehr)}</td></tr>
 <tr class="total"><td>{t['total']}</td><td class="r">{_chf(m.total())}</td></tr>
</table></div>
<div class="note">{html.escape(hinweis)}</div>
<footer>Erstellt mit DevisPro – {html.escape(m.betrieb)}</footer>
</body></html>"""


def build_pdf(m: Mahnung, lang: str = "de") -> bytes:
    from . import pdf_native as PN
    from . import qr_rechnung as qr_mod
    t = _T.get(lang, {})
    pdf = PN.PDF()
    pdf.heading(f"{t.get('mahnung', 'Mahnung')} {m.stufe}")
    pdf.footer(f"Erstellt mit DevisPro – {m.betrieb}")
    pdf.kv([
        (t.get("rn", "Rechnung"), f"{m.rechnungs_nr}\n{t.get('datum','')}: {m.datum}"),
        (t.get("empfaenger", "Empfänger"), m.kunde),
        (t.get("objekt", "Objekt"), m.objekt),
    ])
    pdf.summary([
        (t.get("offen", "Offen"), _chf(m.offen_brutto), False),
        (f"{t.get('zins','Zins')} {_chf(m.zins_pct)}%", _chf(m.zins_betrag), False),
        (t.get("gebuehr", "Gebühr"), _chf(m.gebuehr), False),
        (t.get("total", "Total"), _chf(m.total()), True),
    ])
    pdf.note(([t.get("text1", ""), t.get("text2", ""), t.get("text3", "")][m.stufe - 1]))
    # Swiss QR-Code einbetten (reine Stdlib, scannbar)
    try:
        from . import rechnung as rmod
        r = rmod.Rechnung(rechnungs_nr=m.rechnungs_nr, datum=m.datum, faellig=m.faellig,
                          betrieb=m.betrieb, kunde=m.kunde, objekt=m.objekt,
                          positionen=[], mwst_pct=8.1)
        # Betrag der Mahnung als offener Posten setzen
        r._offen_override = m.total()
        matrix, _ = qr_mod.qr_matrix_aus_rechnung(r)
        pdf.image(matrix, PN.PAGE_W - PN.MARGIN_R - 130, PN.MARGIN_B - 4, 130)
    except Exception:
        pass
    return pdf.build()
