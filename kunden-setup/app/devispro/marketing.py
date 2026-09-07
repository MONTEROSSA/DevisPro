"""Marketing-Landingpage für DevisPro (CH-Bau-KMU). Rein stdlib-Render.

Eigenständige Verkaufsseite, die das Profil gegenüber Abacus/Manuallösungen
abhebt: automatische SIA-451 Bepreisung, kantonale Preise, 3-Monate-Pilot.
"""
import html


def render_landing(lang: str = "de") -> str:
    t = {
        "de": {
            "title": "DevisPro – Devis in 3 Minuten bepreist",
            "sub": "Automatische Bepreisung für Schweizer Bau-KMU – aus ALLEN gängigen "
                   "Formaten: SIA-451/Sorba, Bauweb, generisches CSV/Excel, GAEB (DE), "
                   "ÖNORM (AT) und XRechnung (EU). Inkl. Swiss QR-Rechnung.",
            "cta": "Jetzt 3 Monate gratis testen",
            "feat1_h": "Automatisch bepreist",
            "feat1": "NPK-Matching gegen Ihre Richtpreisliste. Unsichere Treffer "
                     "werden klar markiert – Sie prüfen nur, was nötig ist.",
            "feat2_h": "Ganze Schweiz",
            "feat2": "26 Kantone mit eigenem Preisfaktor. Ein Devis, korrekt "
                     "kalkuliert für Zürich, Genf oder Tessin.",
            "feat3_h": "Zusatzpositionen",
            "feat3": "Was erst vor Ort klar wird, ergänzen Sie mit einem Klick – "
                     "die Gesamtofferte inkl. MWSt ist sofort da.",
            "feat4_h": "Alle Formate",
            "feat4": "SIA-451/Sorba, Bauweb, CSV/Excel, GAEB (DE), ÖNORM (AT), "
                     "XRechnung (EU) – automatisch erkannt. Plus Swiss QR-Rechnung "
                     "pro Devis, direkt versendbar.",
            "preis_h": "Preis",
            "preis": "CHF 2'400.— Einmalig + CHF 990.—/Jahr. Pilot 3 Monate gratis, "
                     "danach CHF 500.— Rabatt auf das erste Jahr.",
            "vs": "Warum DevisPro statt Abacus?",
            "vs1": "Abacus ist eine riesige ERP-Lösung – DevisPro macht GENAU eine "
                   "Sache, aber besser: Devis in Sekunden bepreisen.",
            "vs2": "Kein Jahresvertrag über zehntausende Franken. Einmalig 2'400 "
                   "plus kleines Abo.",
            "vs3": "Läuft lokal auf Ihrem Computer (Mac oder Windows) – keine "
                   "Cloud-Zwischenstation für Kundendaten.",
        },
        "fr": {
            "title": "DevisPro – Devis tarifé en 3 minutes",
            "sub": "Tarification automatique pour les PME suisses – dans TOUS les formats : "
                   "SIA-451/Sorba, Bauweb, CSV/Excel generique, GAEB (DE), OENORM (AT) et "
                   "XRechnung (UE). Avec QR-facture suisse.",
            "cta": "Tester 3 mois gratuitement",
            "feat1_h": "Tarife automatiquement",
            "feat1": "Appariement NPK avec votre liste de prix. Les correspondances "
                     "incertaines sont clairement marquees.",
            "feat2_h": "Toute la Suisse",
            "feat2": "26 cantons avec leur propre facteur de prix. Un devis, correct "
                     "pour Zurich, Geneve ou le Tessin.",
            "feat3_h": "Positions supplementaires",
            "feat3": "Ce qui ne se clarifie que sur place, vous le completez en un "
                     "clic – l'offre totale TVA comprise est immediate.",
            "feat4_h": "Tous les formats",
            "feat4": "SIA-451/Sorba, Bauweb, CSV/Excel, GAEB (DE), OENORM (AT), "
                     "XRechnung (UE) – reconnus automatiquement. Plus QR-facture suisse par devis.",
            "preis_h": "Prix",
            "preis": "CHF 2'400.— unique + CHF 990.—/an. Pilote 3 mois gratuits, "
                     "puis CHF 500.— de reduction la 1re annee.",
            "vs": "Pourquoi DevisPro plutot qu'Abacus ?",
            "vs1": "Abacus est un immense ERP – DevisPro fait UNE seule chose, mais "
                   "mieux : tarifer le devis en secondes.",
            "vs2": "Pas de contrat annuel de dizaines de milliers. 2'400 une fois "
                   "plus un petit abonnement.",
            "vs3": "Fonctionne localement sur votre ordinateur (Mac ou Windows) – "
                   "aucune etape cloud pour les donnees clients.",
        },
        "it": {
            "title": "DevisPro – Devis prezzato in 3 minuti",
            "sub": "Tariffazione automatica per le PMI svizzere – in TUTTI i formati: "
                   "SIA-451/Sorba, Bauweb, CSV/Excel generico, GAEB (DE), OENORM (AT) e "
                   "XRechnung (UE). Con QR-fattura svizzera.",
            "cta": "Prova 3 mesi gratis",
            "feat1_h": "Tariffato automaticamente",
            "feat1": "Matching NPK con la vostra lista prezzi. Le corrispondenze "
                     "incerte sono chiaramente evidenziate.",
            "feat2_h": "Tutta la Svizzera",
            "feat2": "26 cantoni con proprio fattore di prezzo. Un devis, corretto "
                     "per Zurigo, Ginevra o il Ticino.",
            "feat3_h": "Posizioni supplementari",
            "feat3": "Cio che si chiarisce solo in loco, lo completate con un clic – "
                     "l'offerta totale IVA inclusa e immediata.",
            "feat4_h": "Tutti i formati",
            "feat4": "SIA-451/Sorba, Bauweb, CSV/Excel, GAEB (DE), OENORM (AT), "
                     "XRechnung (UE) – riconosciuti automaticamente. Più QR-fattura svizzera per devis.",
            "preis_h": "Prezzo",
            "preis": "CHF 2'400.— una tantum + CHF 990.—/anno. Piloto 3 mesi gratis, "
                     "poi CHF 500.— di sconto sul primo anno.",
            "vs": "Perche DevisPro invece di Abacus ?",
            "vs1": "Abacus e un enorme ERP – DevisPro fa UNA sola cosa, ma meglio: "
                   "tariffa il devis in secondi.",
            "vs2": "Nessun contratto annuale di decine di migliaia. 2'400 una volta "
                   "piu un piccolo abbonamento.",
            "vs3": "Funziona localmente sul vostro computer (Mac o Windows) – "
                   "nessuna tappa cloud per i dati clienti.",
        },
    }

    d = t.get(lang, t["de"])

    def esc(s):
        return html.escape(str(s))

    return f"""<!doctype html><html lang="{esc(lang)}"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(d['title'])}</title>
<style>
 body {{ font-family:-apple-system,system-ui,Segoe UI,Arial,sans-serif;
        margin:0; color:#1a1a1a; line-height:1.5; }}
 .hero {{ background:linear-gradient(135deg,#14532d,#166534); color:#fff;
         padding:64px 24px; text-align:center; }}
 .hero h1 {{ font-size:34px; margin:0 0 12px; }}
 .hero p {{ max-width:680px; margin:0 auto 24px; opacity:.95; }}
 .btn {{ display:inline-block; background:#f59e0b; color:#1a1a1a; font-weight:700;
        padding:14px 28px; border-radius:8px; text-decoration:none; font-size:16px; }}
 .wrap {{ max-width:920px; margin:0 auto; padding:48px 24px; }}
 .feat {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(240px,1fr));
         gap:20px; margin:32px 0; }}
 .card {{ border:1px solid #e5e7eb; border-radius:12px; padding:20px; }}
 .card h3 {{ margin:0 0 8px; color:#14532d; }}
 .vs {{ background:#f0fdf4; border:1px solid #bbf7d0; border-radius:12px;
       padding:24px; margin-top:32px; }}
 .vs li {{ margin-bottom:10px; }}
 .preis {{ text-align:center; font-size:18px; margin:24px 0; padding:20px;
          background:#fffbeb; border-radius:12px; }}
 footer {{ text-align:center; padding:24px; color:#888; font-size:13px; }}
</style></head>
<body>
<section class="hero">
  <h1>{esc(d['title'])}</h1>
  <p>{esc(d['sub'])}</p>
  <a class="btn" href="/bepreisen">▶ {esc(d['cta'])}</a>
</section>
<div class="wrap">
  <div class="feat">
    <div class="card"><h3>{esc(d['feat1_h'])}</h3><p>{esc(d['feat1'])}</p></div>
    <div class="card"><h3>{esc(d['feat2_h'])}</h3><p>{esc(d['feat2'])}</p></div>
    <div class="card"><h3>{esc(d['feat3_h'])}</h3><p>{esc(d['feat3'])}</p></div>
    <div class="card"><h3>{esc(d['feat4_h'])}</h3><p>{esc(d['feat4'])}</p></div>
  </div>
  <div class="preis"><b>{esc(d['preis_h'])}:</b> {esc(d['preis'])}</div>
  <div class="vs"><h2>{esc(d['vs'])}</h2><ul>
    <li>{esc(d['vs1'])}</li><li>{esc(d['vs2'])}</li><li>{esc(d['vs3'])}</li>
  </ul></div>
</div>
<footer>DevisPro · ein Produkt der Monterossa AG · info@monterossa.ch · devispro.ch</footer>
</body></html>"""
