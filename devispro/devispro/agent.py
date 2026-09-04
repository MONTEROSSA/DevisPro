"""DevisPro KI-Agent (offline, reine Stdlib) – Ihr Assistent im Produkt.

Der Agent ist ein lokaler, datenschutzfreundlicher Helfer (kein Cloud, keine
API-Keys). Er beantwortet Fragen zur Software und fuehrt echte Aktionen aus:
  - Devis oeffnen / wechseln
  - MWST, Kanton, Betrieb aendern
  - Export in Buchhaltungssysteme (Abacus, Proffix, DATEV, ...)
  - Mehrwaehrung umrechnen
  - Margen-Copilot / Benchmark erklaeren
  - Marketing-Texte erzeugen
  - FAQ zu Preisen, Trial, Lizenz, Formaten

Architektur:
  - Wissensbasis (FAQ + Feature-Beschreibungen) fuer Antworten
  - Intent-Erkennung ueber Schluesselwort-Score (deterministisch, erklaerbar)
  - Aktions-Funktionen rufen bestehende Module auf (kein Duplikat-Code)
"""

import os
import re
import json

from . import stammdaten
from . import history as history_mod
from .parsers import crb
from . import accounting as accounting_mod
from . import multicurrency as mc_mod
from . import margen_copilot as margen_mod
from . import marketing as marketing_mod
from . import subunternehmer as sub_mod
from . import erp_api as erp_mod


# ---------------------------------------------------------------------------
# Wissensbasis
# ---------------------------------------------------------------------------

FAQ = {
    "trial": (
        "DevisPro bietet einen 3-monatigen Pilot (Trial) – erst NACH Eingabe von "
        "Firma und E-Mail. Danach 500 CHF Rabatt auf die Jahreslizenz. "
        "Preismodell: 2'400 CHF + 990 CHF/Jahr. Lizenz ist lokal beim KMU, "
        "Freischalt-Code jaehrlich vom Anbieter."
    ),
    "preis": (
        "DevisPro kostet 2'400 CHF einmalig plus 990 CHF pro Jahr (Wartung, "
        "Updates, Benchmark-Netzwerk). Der 3-Monats-Pilot ist gratis, danach "
        "500 CHF Rabatt. Anbieter: Monterossa AG, info@monterossa.ch."
    ),
    "formate": (
        "DevisPro liest: SIA-451/Sorba, Bauweb/Daedalus, generisches CSV/Excel, "
        "GAEB (DE), OENORM (AT), XRechnung (EU). Es schreibt: SIA-451 (bepreist), "
        "Angebot/Offerte, Rechnung, Swiss-QR, sowie Export fuer Abacus, Proffix, "
        "BMD, DATEV, Banana, SAP, Lexoffice, SevDesk, WinOffice, RamCO, Mobit, "
        "Kleinvieh und generisches CSV."
    ),
    "lizenz": (
        "Die Lizenz ist lokal beim KMU installiert und ohne jaehrlichen "
        "Freischalt-Code unbrauchbar (RSA-signiert). Nach Zahlung bestaetigt der "
        "Anbieter und der Code wird automatisch ausgestellt."
    ),
    "kanton": (
        "DevisPro deckt alle 26 Kantone mit kantonalen Aufschlaegen (Baukosten-Index "
        "NPK). Das Kanton wird im Stammdaten-Profil gesetzt und beeinflusst die "
        "Benchmark-Vergleiche und Regionale Aufschlaege."
    ),
    "ordner": (
        "Sie koennen ganze ORDNER hochladen (nicht nur einzelne Dateien). DevisPro "
        "analysiert alle Unterlagen (SIA, CSV, XLSX, GAEB, OENORM, XRechnung, Bilder) "
        "und fuellt das komplette Devis automatisch aus. Bilder/PDF werden als "
        "«manuell» markiert (OCR auf diesem System nicht verfuegbar)."
    ),
    "ki": (
        "Der DevisPro-KI-Agent (ich) ist offline und lokal – keine Cloud, keine "
        "API-Keys. Ich beantworte Fragen und fuehre Aktionen aus: Devis oeffnen, "
        "MWST/Kanton aendern, Export in Buchhaltungssysteme, Waehrung umrechnen, "
        "Marketing-Texte erzeugen."
    ),
    "sicherheit": (
        "Alles laeuft lokal auf Ihrem Mac/Windows. Keine Daten verlassen das Geraet. "
        "Die Benchmark-Daten sind anonymisiert. SMTP-Zugangsdaten liegen nur in "
        "data/smtp.json (nicht im Code)."
    ),
    "support": (
        "Support: info@monterossa.ch (Monterossa AG). Die Dokumentation liegt im "
        "Paket (README.txt, LIZENZ_MONTEROSSA.txt). Der KI-Agent hilft sofort zu "
        "jeder Frage."
    ),
    "erp": (
        "DevisPro + ERP ist die integrierte Erweiterung: Lager & Stuecklisten, "
        "Einkauf/Bestellung, Verkauf (Offerte->Auftrag->Rechnung), Buchhaltung "
        "(Journal, KMU-Kontenrahmen, MWST-Abrechnung) und ein Live-Dashboard "
        "(Umsatz, offene Posten, Lagerwert). 13 Schnittstellen zu Abacus, Proffix, "
        "BMD, DATEV, Banana, SAP. Preis: 8'900 CHF + 3'490 CHF/Jahr."
    ),
}

FEATURES = {
    "margen-copilot": "Vergleicht Ihre Preise mit dem anonymen Marktpreis-Netzwerk und flaggt zu tiefe/hoche Kalkulationen (Heuristik, erklaerbar).",
    "benchmark": "Anonymes Marktpreis-Netzwerk ueber alle Kantone – fuer realistische Aufschlaege und Preis-Checks.",
    "whatsapp": "Erzeugt klick-freie Angebotstexte + Deep-Links fuer WhatsApp.",
    "subunternehmer": "Erfasst Sub-Offerten pro Position und rechnet Ihre Marge (Verkaufspreis − Sub-Kosten) aus.",
    "marketing": "Social Posts, Ausschreibungs-Anschreiben und Referenz-Blatt (PDF) aus dem Devis.",
    "mehrwaehrung": "Rechnet Devis in EUR/USD/GBP um (SNB/EZB-Kurse, sicherer Offline-Fallback). Kalkulation bleibt in CHF.",
    "wiederkehrend": "Automatische Perioden-Rechnungen (Wartung, Abos, Servicevertraege).",
    "mahnwesen": "Erinnerungen und Mahnungen fuer offene Posten.",
    "team": "Rollen & Rechte (Admin, Kalkulator, Lesen) plus offline Sync via USB/LAN.",
    "qr": "Swiss-QR-Rechnungen (einzahlen.bar, PostFinance, Banken).",
    "white-label": "Eigenes Branding (Firma, Logo, Farben) fuer Dienstleister.",
    "erp-api": "HMAC-signierter REST-Push von Belegen an Abacus/Proffix/andere ERP.",
    "erp": "Integriertes ERP (Tarif DevisPro + ERP): Lager, Einkauf, Verkauf, Buchhaltung, Live-Dashboard.",
    "dashboard": "Kennzahlen: Umsatz, Auslastung, offene Posten, Pipeline.",
}

# ---------------------------------------------------------------------------
# Intent-Erkennung
# ---------------------------------------------------------------------------

INTENTS = [
    ("set_mwst", ["mwst", "mehrwertsteuer", "steuer", "satz"], r"mwst\s*(auf)?\s*(\d+[.,]?\d*)"),
    ("set_kanton", ["kanton", "region", "ort"], r"kanton\s*(auf)?\s*([a-z]{2})", True),
    ("set_betrieb", ["betrieb", "firma", "firmenname"], None),
    ("export_accounting", ["export", "buchhaltung", "abacus", "proffix", "datev", "bmd", "banan", "sap", "lexoffice", "sevdesk"], None),
    ("waehrung", ["waehrung", "euro", "eur", "usd", "umrechn", "chf"], None),
    ("open_devis", ["oeffne", "zeige", "zeig", "devis", "offert", "angebot"], None),
    ("margen", ["marge", "copilot", "benchmark", "marktpreis", "zu teuer", "zu guenstig"], None),
    ("sub", ["subunternehmer", "sub ", "subunternehm", "fremd"], None),
    ("marketing", ["marketing", "social", "linkedin", "facebook", "instagram", "werbung", "ausschreib"], None),
    ("help_features", ["funktion", "feature", "kann", "was bietet", "uebersicht", "hilfe"], None),
    ("erp", ["erp", "lager", "buchhaltung", "artikel", "stuecklist", "einkauf", "verkauf", "dashboard", "mwst-abrechn"], None),
    ("faq", ["trial", "preis", "kosten", "lizenz", "format", "support", "sicher", "ki agent"], None),
]


def _detect_lang(q):
    ql = q.lower()
    if re.search(r"\b(le|la|les|pour|comment|est|suis|votre)\b", ql) or "comment" in ql:
        return "fr"
    if re.search(r"\b(il|la|le|per|come|sono|vostro|offerta)\b", ql) or "prezzo" in ql:
        return "it"
    return "de"


def _find_devis(token):
    """Sucht Devis nach id-Praefix oder Projektname."""
    for d in history_mod.list_all():
        did = d["id"] if isinstance(d, dict) else d
        name = (d.get("name", "") if isinstance(d, dict) else "")
        if token and (did.startswith(token) or token in did or token.lower() in name.lower()):
            return did
    return None


# ---------------------------------------------------------------------------
# Aktionen
# ---------------------------------------------------------------------------

def _set_mwst(value, profil, data_dir):
    try:
        val = float(value.replace(",", "."))
    except Exception:
        return None, "Bitte eine gueltige MWST-Zahl angeben (z.B. 7.7 oder 8.1)."
    profil["mwst_pct"] = val
    stammdaten.save_profile(profil)
    return val, f"MWST auf {val:.1f}% gesetzt."


def _set_kanton(kanton, profil, data_dir):
    from devispro import kantone as kantone_mod
    code = kantone_mod.normiere_kanton(kanton)
    if not code:
        return kanton.upper(), f"Unbekannter Kanton «{kanton}». Verfuegbare: z.B. ZH, BE, AG, BS, GE …"
    profil["kanton"] = code
    profil = kantone_mod.waehle_kanton_profil(profil)  # setzt auch kanton_label + kanton_faktor
    stammdaten.save_profile(profil)
    return code, f"Kanton auf {code} ({profil.get('kanton_label','')}) gesetzt (beeinflusst Benchmark & Aufschlaege)."


def _set_betrieb(name, profil, data_dir):
    profil["betrieb"] = name
    stammdaten.save_profile(profil)
    return name, f"Betriebsname auf «{name}» gesetzt."


def _export(devis, system, profil, data_dir, lang="de"):
    valid = {s["id"]: s["name"] for s in accounting_mod.liste()}
    if system not in valid:
        return None, "Unbekanntes Buchhaltungssystem. Verfuegbar: " + ", ".join(valid.keys())
    if devis is None:
        return None, "Kein Devis geladen. Bitte zuerst ein Devis oeffnen (z.B. «öffne devis_0007»)."
    from devispro.models import Devis
    beleg = devis.meta.get("project_name") or "Offerte"
    datum = str(devis.meta.get("date", "") or "")
    out = accounting_mod.export(system, devis, profil, beleg, datum)
    return out, f"Export fuer {valid[system]} erstellt ({len(out.splitlines())} Zeilen)."


# ---------------------------------------------------------------------------
# Haupt-Chat
# ---------------------------------------------------------------------------

def chat(message, context=None):
    """Verarbeitet eine Nutzer-Nachricht und liefert ein Antwort-Dict.

    context: dict mit 'lang', 'did' (aktuelles Devis), 'data_dir'
    Rueckgabe: {answer, action, navigate, lang}
    """
    context = context or {}
    lang = context.get("lang") or _detect_lang(message)
    data_dir = context.get("data_dir")
    did = context.get("did")
    profil = stammdaten.load_profile() or {}
    q = message.strip()
    ql = q.lower()

    # 1) MWST aendern
    m = re.search(r"mwst\s*(auf)?\s*(\d+[.,]?\d*)", ql)
    if ("mwst" in ql or "mehrwertsteuer" in ql) and m:
        val, info = _set_mwst(m.group(2), profil, data_dir)
        return {"answer": f"✅ {info} Betroffene Offerten/Rechnungen werden beim naechsten Speichern neu berechnet.", "action": "mwst", "lang": lang}

    # 2) Kanton aendern (robust: alle formulierungen) — ABER nur wenn nicht "währung" oder "export" erwähnt
    is_currency = any(w in ql for w in ("waehrung", "euro", "umrechn", "franken", "chf", "eur", "usd", "gbp"))
    is_export = any(w in ql for w in ("export", "buchhalt", "abacus", "proffix", "datev", "bmd", "banana", "sap", "lexoffice", "sevdesk", "winoffice", "ramco", "mobit", "kleinvieh", "csv"))
    from devispro import kantone as kantone_mod
    if (("kanton" in ql or "kt." in ql or "kt " in ql) and not is_currency and not is_export):
        kt_erkannt = None
        ql2 = ql.replace(".", " ")
        # a) "kanton/kt" + code oder name
        m = re.search(r"(kanton|kt\.?|kant\.?)\s*(auf|in|nach|zu|an|auf den)?\s*([a-zäöü]{2,20})", ql2)
        if m:
            kt_erkannt = m.group(3)
        # b) "schalte/wechsle/setze/stelle/umschalte/ander auf|zu|in X um"
        if not kt_erkannt:
            m2 = re.search(r"(schalt|wechsel|setz|stell|umschalt|ändere?|aendere?|umstell)\w*\s+(auf|zu|in|nach|an)\s+([a-zäöü]{2,20})", ql2)
            if m2:
                kt_erkannt = m2.group(3)
        # c) "auf|zu|in|nach X (um|wechseln|schalten)"
        if not kt_erkannt:
            m3 = re.search(r"(auf|zu|in|nach)\s+([a-zäöü]{2,20})\s*(um|wechsel|schalt|ändere?|aendere?)?", ql2)
            if m3:
                kt_erkannt = m3.group(2)
        # d) direkter Kantonsname irgendwo im text
        if not kt_erkannt:
            for kn in kantone_mod.KANTON_NAMEN:
                if kn in ql:
                    kt_erkannt = kn
                    break
        # e) nur der code (AG, ZH, ...)
        if not kt_erkannt:
            for code in kantone_mod.KANTONE:
                if code.lower() in ql.split():
                    kt_erkannt = code
                    break
        if kt_erkannt:
            code = kantone_mod.normiere_kanton(kt_erkannt)
            if code:
                kt, info = _set_kanton(code, profil, data_dir)
                return {"answer": f"✅ {info}", "action": "kanton", "lang": lang}
            return {"answer": f"⚠️ Kanton «{kt_erkannt}» ist mir nicht bekannt. Beispiele: «Wechsle auf Kanton Aargau», «setze Kanton auf ZH».", "action": "kanton", "lang": lang}

    # 3) Betrieb aendern
    m = re.search(r"(betrieb|firma)\s*(auf|ist)?\s*[:\"]?\s*([A-Za-z0-9\s\.]+)", ql)
    if ("betrieb" in ql or "firma" in ql) and m and ("auf" in ql or "ist" in ql):
        name = m.group(3).strip().title()
        name, info = _set_betrieb(name, profil, data_dir)
        return {"answer": f"✅ {info}", "action": "betrieb", "lang": lang}

    # 4) Export in Buchhaltung
    valid_ids = {s["id"] for s in accounting_mod.liste()}
    for key in valid_ids:
        if key in ql and ("export" in ql or "buchhalt" in ql):
            devis = _load_devis(did, data_dir)
            out, info = _export(devis, key, profil, data_dir, lang)
            if out is None:
                return {"answer": f"⚠️ {info}", "action": "export", "lang": lang}
            return {"answer": f"✅ {info}\n\nVorschau:\n{out[:800]}", "action": "export", "lang": lang}

    # 5) Waehrung umrechnen
    if "waehrung" in ql or "euro" in ql or "umrechn" in ql or "chf" in ql:
        betrag = re.search(r"(\d+[.,]?\d*)", ql)
        ziel = "EUR"
        for c in ("eur", "euro", "usd", "gbp", "dollar", "pfund"):
            if c in ql:
                ziel = {"eur": "EUR", "euro": "EUR", "usd": "USD", "dollar": "USD", "gbp": "GBP", "pfund": "GBP"}[c]
        if betrag:
            b = float(betrag.group(1).replace(",", "."))
            umg = mc_mod.umrechnen(b, ziel)
            return {"answer": f"💱 {b:,.2f} CHF = {mc_mod.format(ziel, umg)} (Kurs 1 CHF = {mc_mod.kurs_chf_nach(ziel):.4f} {ziel}).", "action": "waehrung", "lang": lang}
        return {"answer": "💱 Geben Sie einen Betrag an, z.B. «rechne 5000 CHF in EUR um». Verfuegbare Zielwaehrungen: " + ", ".join(mc_mod.verfuegbare()), "action": "waehrung", "lang": lang}

    # 6) Margen / Copilot
    if any(w in ql for w in ("marge", "copilot", "benchmark", "marktpreis", "zu teuer", "zu guenstig", "aufpreis")):
        devis = _load_devis(did, data_dir)
        if devis is None:
            return {"answer": "🧠 Der Margen-Copilot vergleicht Ihre Preise mit dem Marktpreis-Netzwerk. Bitte zuerst ein Devis oeffnen.", "action": "margen", "lang": lang}
        from devispro import benchmark as bench_mod
        res = margen_mod.analyse(devis, kanton=profil.get("kanton", "ZH"), benchmark_mod=bench_mod)
        lines = "\n".join(f"  {r['status']} {r['pos_nr']} {r['text'][:40]} – {r['hinweis']}" for r in res[:8])
        return {"answer": f"🧠 Margen-Copilot (Kanton {profil.get('kanton','ZH')}):\n{lines}\n\nÖffnen Sie «Marge» fuer die volle Analyse.", "action": "margen", "lang": lang}

    # 7) Subunternehmer
    if "subunternehmer" in ql or "sub " in ql or "fremd" in ql:
        return {"answer": "🤝 Subunternehmer-Marge: Erfassen Sie die Offerten Ihrer Subs pro Position – DevisPro rechnet Ihre Marge (Verkaufspreis − Sub-Kosten) aus. Oeffnen Sie «Sub».", "action": "sub", "lang": lang}

    # 8) Marketing
    if any(w in ql for w in ("marketing", "social", "linkedin", "facebook", "instagram", "werbung", "ausschreib")):
        devis = _load_devis(did, data_dir)
        if devis is None:
            return {"answer": "📣 Marketing-Assistent: Social Posts, Ausschreibungs-Anschreiben und Referenz-Blatt (PDF). Bitte zuerst ein Devis oeffnen, damit ich einen Text dazu erzeuge.", "action": "marketing", "lang": lang}
        post = marketing_mod.social_post(profil, devis, "linkedin", lang)
        return {"answer": f"📣 LinkedIn-Post fuer Ihr Devis:\n\n{post}\n\n(Oeffnen Sie «Marketing» fuer alle Kanaele + PDF)", "action": "marketing", "lang": lang}

    # 8b) ERP
    if any(w in ql for w in ("erp", "lager", "buchhaltung", "artikel", "stuecklist", "einkauf", "verkauf", "dashboard", "mwst-abrechn")):
        return {"answer": (
            "📊 DevisPro + ERP (Tarif 'DevisPro + ERP'):\n"
            "  • Lager & Stücklisten: Bestand, Mindestbestand, Nachbestelllisten\n"
            "  • Einkauf: Lieferanten, Bestellungen, Disposition\n"
            "  • Verkauf: Offerten → Auftrag → Rechnung, Teilzahlungen, Mahnwesen\n"
            "  • Buchhaltung: Journal, KMU-Kontenrahmen, MWST-Abrechnung\n"
            "  • Dashboard: Umsatz, offene Posten, Lagerwert – live\n"
            "Öffnen Sie «ERP-API» in der Navigation für die 13 Schnittstellen "
            "(Abacus, Proffix, BMD, DATEV, Banana, SAP …)."), "action": "erp", "lang": lang}

    # 9) Devis oeffnen
    m = re.search(r"(oeffne|zeige|zeig|offert|angebot|devis)\s*([a-z0-9_]+)", ql)
    if any(w in ql for w in ("oeffne", "zeige", "zeig", "offert", "angebot")) and m:
        token = m.group(2)
        found = _find_devis(token)
        if found:
            return {"answer": f"📂 Devis {found} geoeffnet.", "action": "open", "navigate": f"/devis/{found}", "lang": lang}
        return {"answer": f"🔍 Kein Devis gefunden fuer «{token}». Verfuegbare: " + ", ".join(d["id"] for d in history_mod.list_all()[:10]), "action": "open", "lang": lang}

    # 10) Feature-Uebersicht
    if any(w in ql for w in ("funktion", "feature", "kann", "was bietet", "uebersicht", "hilfe", "hilf")):
        feats = "\n".join(f"  • {k}: {v}" for k, v in FEATURES.items())
        return {"answer": f"🔧 DevisPro Funktionen:\n{feats}\n\nFragen Sie mich etwas wie «setze MWST auf 7.7» oder «exportiere nach Abacus».", "action": "help", "lang": lang}

    # 11) FAQ (mit Synonymen)
    FAQ_KEYWORDS = {
        "trial": ["trial", "pilot", "testen", "gratis", "kostenlos", "demo"],
        "preis": ["preis", "kosten", "kostet", "gebühr", "gebuehr", "teuer", "tarif", "abo", "jahres", "chf", "franken"],
        "formate": ["format", "sia", "sorba", "gaeb", "oenorm", "xrechnung", "csv", "excel", "import", "datev"],
        "lizenz": ["lizenz", "freischalt", "code", "schluessel", "rsa", "gesperrt"],
        "kanton": ["kanton", "region", "aufpreis", "npk", "baukosten"],
        "ordner": ["ordner", "ganze", "mehrere dateien", "upload"],
        "ki": ["ki", "agent", "assistent", "chatbot", "künstlich", "kuenstlich"],
        "sicherheit": ["sicher", "datenschutz", "cloud", "privat", "dsgvo", "offline"],
        "support": ["support", "hilfe", "kontakt", "monterossa", "email", "e-mail"],
    }
    for key, kws in FAQ_KEYWORDS.items():
        if any(w in ql for w in kws):
            return {"answer": "ℹ️ " + FAQ[key], "action": "faq", "lang": lang}

    # 12) Fallback
    return {"answer": (
        "🤖 Ich bin der DevisPro-KI-Agent (lokal, offline). Ich helfe zu:\n"
        "  • «setze MWST auf 7.7»\n"
        "  • «setze Kanton auf BE»\n"
        "  • «exportiere nach Abacus»\n"
        "  • «rechne 5000 CHF in EUR um»\n"
        "  • «öffne devis_0007»\n"
        "  • «was kostet DevisPro?» / «welche Formate?»\n"
        "  • «mach einen LinkedIn-Post»\n"
        "Falls ich eine Frage nicht verstehe, formulieren Sie sie kurz mit einem der Schluesselwoerter."
    ), "action": "fallback", "lang": lang}


def _load_devis(did, data_dir):
    """Lädt ein Devis — versucht zuerst den DevisPro-Parser, dann CRB-SIA als Fallback."""
    if not did:
        return None
    sia_path = history_mod.path_of(did, "bepreist.sia")
    # Primär: DevisPro-Format (M16)
    try:
        from .parsers.devispro_sia import parse as devispro_parse
        dev = devispro_parse(sia_path)
        if dev and dev.positions:
            return dev
    except Exception:
        pass
    # Fallback: CRB-SIA-Standard-Format
    try:
        return crb.parse(sia_path)
    except Exception:
        return None
