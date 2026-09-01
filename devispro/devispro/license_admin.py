"""Lizenz-Admin (Anbieter-Seite) - vollautomatisch.

Ablauf:
  1. Kunde bestellt/pilottet -> lizenz_ausstellen(kunde) erzeugt Erstlizenz + Rechnung.
  2. Naher Ablauf -> erinnerung_pruefen() erkennt fällige Erinnerungen (30/14/7 Tage)
     und bereitet Mail-Texte vor (automatischer Versand via SMTP optional).
  3. Du bestaetigst Zahlungseingang -> freigeben_nach_zahlung(kunde) erzeugt den
     Jahres-Code und (optional) versendet ihn automatisch an den Kunden.

Du musst NUR den Zahlungseingang bestaetigen. Alles andere läuft automatisch:
Rechnung, Erinnerungen, Code-Generierung, Code-Versand.
"""
import os
import json
import smtplib
import datetime as dt
from email.message import EmailMessage

from devispro import crypto_rsa as rsa
from devispro import stammdaten as stammdaten_mod

# --- Hersteller / Kontakt (Monterossa AG) ---------------------------------
HERSTELLER = "Monterossa AG"
KONTAKT_MAIL = "info@monterossa.ch"          # Anfragen + Trial-Benachrichtigung
WEB = "devispro.de"

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(HERE, "data")
KUNDEN_PFAD = os.path.join(DATA, "kunden.json")
ADMIN_KEYS_PFAD = os.path.join(DATA, "admin_keys.json")

PREIS_JAHR = 990.0
PREIS_EINRICHTUNG = 2400.0
ABO_START = dt.date(2026, 1, 1).isoformat()  # Demo-Referenz

# Tarif-Preise aus zentraler Preis-Quelle (DevisPro vs DevisPro+ERP).
# Alte Keys "lizenz_jahr" / "einrichtung" gibt's im neuen pricing.py nicht mehr —
# jetzt heißen sie "support_jahr" (Professional) und "einmal_chf" (Einrichtung).
# Wir holen beide Keys mit Legacy-Fallback, damit alte Aufrufer weiter laufen.
from devispro import pricing as _pricing

def _preise_keys(tarif: str = "professional") -> tuple:
    """Liefert (jahres_preis, einrichtungs_preis) — robust gegen Key-Umbenennungen."""
    p = _pricing.preis(tarif)
    # Neuer Tarif-Schema: support_jahr + einmal_chf
    jahres = p.get("support_jahr", p.get("lizenz_jahr", 990.0))
    einmal = p.get("einmal_chf", p.get("einrichtung", 2400.0))
    return float(jahres), float(einmal)

PREIS_JAHR, PREIS_EINRICHTUNG = _preise_keys("professional")

# PRIVATE Key nur hier (Anbieter). Wird NICHT an KMU ausgeliefert.
_PRIVATE_KEY = None
def _lade_private_key():
    global _PRIVATE_KEY
    if _PRIVATE_KEY is not None:
        return _PRIVATE_KEY
    if os.path.exists(ADMIN_KEYS_PFAD):
        with open(ADMIN_KEYS_PFAD, encoding="utf-8") as f:
            _PRIVATE_KEY = rsa.key_from_str(json.load(f)["private"])
    else:
        # Fallback: Demo-Key erzeugen (nur fuer lokale Entwicklung)
        pub, priv = rsa.generate_keypair(1024)
        _PRIVATE_KEY = priv
    return _PRIVATE_KEY


# --- Kundenverwaltung -------------------------------------------------------
def _laden():
    if not os.path.exists(KUNDEN_PFAD):
        return {}
    with open(KUNDEN_PFAD, encoding="utf-8") as f:
        return json.load(f)


def _speichern(db):
    with open(KUNDEN_PFAD, "w", encoding="utf-8") as f:
        json.dump(db, f, indent=2, ensure_ascii=False)


def kunde_anlegen(kunde_id, firma, email, pilot=False, tarif="devis"):
    db = _laden()
    heute = dt.date.today()
    tarif = str(tarif).lower()
    if tarif not in _pricing.TARIFE:
        tarif = "devis"
    p = _pricing.preis(tarif)
    if pilot:
        bis = heute + dt.timedelta(days=90)  # 3 Monate Pilot
        betrag = 0.0
    else:
        bis = heute + dt.timedelta(days=365)
        betrag = p["einrichtung"] + p["lizenz_jahr"]
    db[kunde_id] = {
        "firma": firma, "email": email, "pilot": pilot,
        "tarif": tarif,
        "gueltig_bis": bis.isoformat(),
        "letzte_rechnung": None, "bezahlt": bool(pilot),  # Trial gilt als freigeschaltet
        "erinnerungen_gesendet": [],
        "quelle": "pilot" if pilot else "verkauf",
    }
    _speichern(db)
    if not pilot:
        rechnung_erstellen(kunde_id, betrag, "Erstlizenz", tarif=tarif)
        db = _laden()  # frisch laden, damit letzte_rechnung sichtbar ist
    # Lokale KMU-Lizenzdatei direkt mit Erstcode befüllen (volle Automation)
    import devispro.license as liz
    erst_code, erst_bis = jahres_code_erzeugen(kunde_id)
    # Bei Pilot das 90-Tage-Bis schreiben, sonst das Jahres-Bis
    liz_bis = bis.isoformat() if pilot else erst_bis
    liz._schreibe_lizenz(kunde_id, liz_bis, erst_code, tarif=tarif)
    return db[kunde_id]


def _lead_loggen(eintrag: dict) -> None:
    """Lokaler Fallback fuer Trial-Leads: immer nach data/trial_leads.log (JSON-Lines),
    auch wenn kein SMTP konfiguriert ist. So geht keine Anfrage verloren."""
    try:
        pfad = os.path.join(DATA, "trial_leads.log")
        with open(pfad, "a", encoding="utf-8") as f:
            f.write(json.dumps(eintrag, ensure_ascii=False) + "\n")
    except Exception:
        pass


def trial_anmelden(daten: dict) -> dict:
    """Self-Service 3-Monats-Test: Kunde gibt Daten ein -> 90-Tage-Lizenz.

    daten: {firma, email, name, kanton, gewerk, sprache}
    Gibt dict: {ok, kunde_id, gueltig_bis, fehler}.
    """
    firma = (daten.get("firma") or "").strip()
    email = (daten.get("email") or "").strip()
    if not firma or not email:
        return {"ok": False, "fehler": "Firma und E-Mail sind erforderlich."}
    if "@" not in email or "." not in email:
        return {"ok": False, "fehler": "Bitte eine gültige E-Mail-Adresse angeben."}
    # Stabile Kunden-ID aus Firma+Email
    kunde_id = "TRIAL-" + _id_aus(firma, email)
    db = _laden()
    tarif = str(daten.get("tarif") or "devis").lower()
    if tarif not in _pricing.TARIFE:
        tarif = "devis"
    if kunde_id in db and db[kunde_id].get("bezahlt"):
        # schon als Trial/Volllizenz vorhanden -> bestehende freischalten
        bis = db[kunde_id]["gueltig_bis"]
    else:
        k = kunde_anlegen(kunde_id, firma, email, pilot=True, tarif=tarif)
        bis = k["gueltig_bis"]
        # Profil (Kanton/Gewerk/Sprache) direkt mit den Trial-Daten vorbelegen
        _profil_vorbelegen(daten)
        # 1) Bestaetigung an den Kunden
        _mail_senden(
            email, "Ihr DevisPro 3-Monate-Test ist freigeschaltet",
            f"Hallo {firma},\n\nIhr 3-monatiger DevisPro-Test ist aktiv.\n"
            f"Gültig bis: {bis}\n\nSie können die Software sofort nutzen. "
            f"DevisPro importiert Devis aus ALLEN gängigen Formaten "
            f"(SIA-451/Sorba, Bauweb, CSV/Excel, GAEB D84, ÖNORM, XRechnung) "
            f"und erstellt pro Devis automatisch eine Swiss QR-Rechnung.\n\n"
            f"Nach Ablauf erhalten Sie ein unverbindliches Angebot.\n\n"
            f"{HERSTELLER} · {KONTAKT_MAIL}")
        # 2) Benachrichtigung an den Hersteller (Monterossa AG)
        _mail_senden(
            KONTAKT_MAIL, "Neue DevisPro-Probekunde",
            f"Neuer 3-Monate-Test angemeldet:\n\n"
            f"Firma:        {firma}\n"
            f"Ansprechpartner: {daten.get('name') or '-'}\n"
            f"E-Mail:       {email}\n"
            f"Kanton:       {daten.get('kanton') or '-'}\n"
            f"Gewerk:       {daten.get('gewerk') or '-'}\n"
            f"Gültig bis:   {bis}\n\n"
            f"Kunde-ID: {kunde_id}\n\n"
            f"DevisPro importiert Devis aus ALLEN gängigen Formaten "
            f"(SIA-451/Sorba, Bauweb, CSV/Excel, GAEB D84, ÖNORM, XRechnung) "
            f"und erstellt pro Devis automatisch eine Swiss QR-Rechnung.\n\n"
            f"{HERSTELLER}")
        # 3) Lokaler Fallback-Log (immer, auch ohne SMTP konfiguriert)
        _lead_loggen({
            "zeit": dt.datetime.now().isoformat(timespec="seconds"),
            "firma": firma, "ansprechpartner": daten.get("name") or "",
            "email": daten.get("email") or "", "kanton": daten.get("kanton") or "",
            "gewerk": daten.get("gewerk") or "", "gueltig_bis": bis,
            "kunde_id": kunde_id,
        })
    return {"ok": True, "kunde_id": kunde_id, "gueltig_bis": bis}


def _id_aus(firma, email):
    import re
    base = re.sub(r"[^a-zA-Z0-9]", "", firma)[:8].upper() or "KMU"
    suffix = re.sub(r"[^a-zA-Z0-9]", "", email.split("@")[0])[:6].upper()
    return f"{base}{suffix}"


def _profil_vorbelegen(daten):
    try:
        profil = stammdaten_mod.load_profile()
        if daten.get("kanton"):
            profil["kanton"] = daten["kanton"].upper()
        if daten.get("gewerk"):
            profil["gewerk"] = daten["gewerk"]
        if daten.get("name"):
            profil["ansprechpartner"] = daten["name"]
        profil["betrieb"] = (daten.get("firma") or profil.get("betrieb", "")).strip()
        stammdaten_mod.save_profile(profil)
    except Exception:
        pass


# --- Rechnung (HTML, druckbar) ---------------------------------------------
def rechnung_erstellen(kunde_id, betrag, typ="Jahresverlaengerung", tarif=None):
    db = _laden()
    k = db.get(kunde_id)
    if not k:
        raise ValueError("Unbekannter Kunde")
    nr = f"R-{kunde_id}-{dt.date.today().strftime('%Y%m%d')}"
    k["letzte_rechnung"] = {"nr": nr, "betrag": betrag, "typ": typ,
                            "datum": dt.date.today().isoformat()}
    _speichern(db)
    produkt = _pricing.preis(tarif or k.get("tarif", "devis"))["bezeichnung"]
    html = f"""<html><body style="font-family:sans-serif;max-width:600px;margin:2rem auto">
<h2>Rechnung {nr}</h2>
<p>{k['firma']}<br>{k['email']}</p>
<p>Datum: {dt.date.today().isoformat()}</p>
<table border="1" cellpadding="6" style="border-collapse:collapse;width:100%">
<tr><td>{typ} {produkt}</td><td style="text-align:right">{betrag:,.2f} CHF</td></tr>
</table>
<p><b>Gesamt: {betrag:,.2f} CHF</b></p>
<p>Zahlbar innert 30 Tagen. Nach Zahlungseingang erhalten Sie automatisch den
Jahres-Freischaltcode per E-Mail.</p>
<p>DevisPro · {HERSTELLER} · {KONTAKT_MAIL}</p>
</body></html>"""
    pfad = os.path.join(DATA, f"rechnung_{nr}.html")
    with open(pfad, "w", encoding="utf-8") as f:
        f.write(html)
    return {"nr": nr, "pfad": pfad, "betrag": betrag}


# --- Jahres-Code generieren (nur nach Zahlung, RSA-signiert) --------------
def kunden_code_export(kunde_id):
    """Erzeugt den Erst-Freischaltcode fuer einen Verkaufskunden.

    Dieser Code ist RSA-signiert (Private Key) und gueltig fuer +1 Jahr
    ab heute. Der Kunde gibt ihn beim ersten Start in DevisPro unter
    'Lizenz' ein - kein lokaler Zugriff auf den Anbieter-Rechner noetig.
    """
    db = _laden()
    if kunde_id not in db:
        return None
    heute = dt.date.today()
    neu_bis = (heute + dt.timedelta(days=365)).isoformat()
    priv = _lade_private_key()
    sig = rsa.sign(priv, f"{kunde_id}|{neu_bis}")
    code = f"{kunde_id}|{neu_bis}|{sig}"
    # lokale Lizenzdatei des Anbieters aktualisieren (Demo/Referenz)
    import devispro.license as liz
    liz._schreibe_lizenz(kunde_id, neu_bis, code)
    return {"code": code, "gueltig_bis": neu_bis, "firma": db[kunde_id].get("firma", "")}


def jahres_code_erzeugen(kunde_id):
    """Erzeugt den gueltigen Code fuer +1 Jahr (RSA-signiert mit PRIVATE Key).

    Rueckgabe: (code_string, neu_bis)
    code_string = "kunde_id|gueltig_bis|SIGNATUR"
    """
    db = _laden()
    k = db[kunde_id]
    heute = dt.date.today()
    alt = dt.date.fromisoformat(k["gueltig_bis"])
    basis = alt if alt > heute else heute
    neu_bis = (basis + dt.timedelta(days=365)).isoformat()
    priv = _lade_private_key()
    sig = rsa.sign(priv, f"{kunde_id}|{neu_bis}")
    return f"{kunde_id}|{neu_bis}|{sig}", neu_bis


def freigeben_nach_zahlung(kunde_id, auto_versenden=True):
    """DU BESTAETIGST NUR HIER: Zahlung da -> Code wird erzeugt + versendet.

    Gibt dict zurueck: {code, gueltig_bis, mail_gesendet}.
    """
    db = _laden()
    k = db[kunde_id]
    code, neu_bis = jahres_code_erzeugen(kunde_id)
    k["gueltig_bis"] = neu_bis
    k["bezahlt"] = True
    k["erinnerungen_gesendet"] = []
    _speichern(db)
    # Rechnung fuer die Verlaengerung (Tarif-Preis)
    tarif = k.get("tarif", "devis")
    rechnung_erstellen(kunde_id, _pricing.preis(tarif)["lizenz_jahr"], "Jahresverlaengerung", tarif=tarif)
    mail_ok = False
    if auto_versenden:
        mail_ok = _mail_senden(
            k["email"], "Ihr DevisPro Jahres-Code",
            f"Hallo {k['firma']},\n\nIhre Zahlung ist eingegangen. "
            f"Ihr Jahres-Freischaltcode lautet:\n\n  {code}\n\n"
            f"Gueltig bis: {neu_bis}\n\nEinfach in DevisPro unter "
            f"'Lizenz' eingeben. Danke!\n\nDevisPro · {HERSTELLER} · {KONTAKT_MAIL}")
    return {"code": code, "gueltig_bis": neu_bis, "mail_gesendet": mail_ok}


# --- Automatische Erinnerungen --------------------------------------------
def erinnerung_pruefen():
    """Prueft alle Kunden auf fällige Erinnerungen (30/14/7 Tage vor Ablauf).

    Gibt Liste von (kunde_id, tage, bereits_gesendet) zurueck.
    Automatischer Versand via _mail_senden (SMTP optional).
    """
    db = _laden()
    heute = dt.date.today()
    faellig = []
    for kid, k in db.items():
        bis = dt.date.fromisoformat(k["gueltig_bis"])
        tage = (bis - heute).days
        if 0 <= tage <= 30:
            for schwelle in (30, 14, 7):
                if tage <= schwelle and schwelle not in k["erinnerungen_gesendet"]:
                    faellig.append((kid, tage))
                    k["erinnerungen_gesendet"].append(schwelle)
                    _mail_senden(
                        k["email"], "DevisPro – Lizenz läuft bald ab",
                        f"Hallo {k['firma']},\n\nIhre DevisPro-Lizenz läuft in "
                        f"{tage} Tagen ab ({bis.isoformat()}).\n\nSie erhalten "
                        f"automatisch die Rechnung und nach Zahlung den neuen "
                        f"Freischaltcode.\n\nDevisPro · {HERSTELLER} · {KONTAKT_MAIL}")
                    break
    _speichern(db)
    return faellig


# --- SMTP (optional, einmal konfigurieren) --------------------------------
SMTP = {"host": "", "user": "", "pass": "", "von": KONTAKT_MAIL,
        "port": 587, "tls": "starttls"}
SMTP_PFAD = os.path.join(DATA, "smtp.json")

# Vordefinierte Anbieter-Profile (Host/Port/TLS). Passwort + Mailbox bleiben lokal.
SMTP_PRESETS = {
    "hostinger": {"host": "smtp.hostinger.com", "port": 465, "tls": "ssl", "hint": "info@ihre-domain"},
    "nnx": {"host": "ic4.nnx.ch", "port": 587, "tls": "starttls", "hint": "info@monterossa.ch"},
    "mailgun": {"host": "smtp.mailgun.org", "port": 587, "tls": "starttls", "hint": "postmaster@"},
}


def smtp_preset(name, mailbox, pwd, von=None):
    """Konfiguriert SMTP ueber ein Anbieter-Profil (z.B. 'hostinger')."""
    p = SMTP_PRESETS.get(name)
    if not p:
        return False
    smtp_konfigurieren(p["host"], mailbox, pwd, von=von or mailbox,
                       port=p["port"], tls=p["tls"])
    return True


# --- Autorisierte Absender-Domains (keine Secrets, nur Konfiguration) -------
EMAIL_DOMAINS_PFAD = os.path.join(DATA, "email_domains.json")
DEFAULT_DOMAINS = {
    "default_sender": "info@devispro.de",   # info@devispro.de gehoert dem Kunden (Hostinger)
    "aktiv": ["devispro.de", "monterossa.ch"],
    "hinweis": "info@devispro.de ist Haupt-Mailadresse (Hostinger); info@monterossa.ch ist Firmenmail Monterossa AG. devispro.ch gehoert dem Kunden NICHT.",
}


def lade_email_domains():
    if os.path.exists(EMAIL_DOMAINS_PFAD):
        try:
            with open(EMAIL_DOMAINS_PFAD, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return dict(DEFAULT_DOMAINS)


def speichere_email_domains(cfg):
    try:
        with open(EMAIL_DOMAINS_PFAD, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)
        return True
    except Exception:
        return False


def _smtp_laden():
    """Laedt gespeicherte SMTP-Daten aus data/smtp.json (nur lokal, kein Code-Commit)."""
    global SMTP
    if os.path.exists(SMTP_PFAD):
        try:
            with open(SMTP_PFAD, encoding="utf-8") as f:
                g = json.load(f)
            SMTP["host"] = g.get("host", "")
            SMTP["user"] = g.get("user", "")
            SMTP["pass"] = g.get("pass", "")
            SMTP["von"] = g.get("von", KONTAKT_MAIL)
            # Port + Verschluesselung (Default: 587 + STARTTLS)
            try:
                SMTP["port"] = int(g.get("port", 587))
            except Exception:
                SMTP["port"] = 587
            SMTP["tls"] = g.get("tls", "starttls")
        except Exception:
            pass
    return SMTP


def smtp_konfigurieren(host, user, pwd, von=KONTAKT_MAIL, port=587, tls="starttls"):
    try:
        port = int(port)
    except Exception:
        port = 587
    if tls not in ("starttls", "ssl", "none"):
        tls = "starttls"
    SMTP["host"] = host; SMTP["user"] = user; SMTP["pass"] = pwd
    SMTP["von"] = von; SMTP["port"] = port; SMTP["tls"] = tls
    # persistent speichern
    try:
        with open(SMTP_PFAD, "w", encoding="utf-8") as f:
            json.dump({"host": host, "user": user, "pass": pwd, "von": von,
                       "port": port, "tls": tls}, f, indent=2, ensure_ascii=False)
    except Exception:
        pass


# Beim Modul-Laden: gespeicherte SMTP-Daten uebernehmen (falls vorhanden)
_smtp_laden()


def _mail_senden(an, betreff, text):
    if not SMTP["host"]:
        return False  # kein SMTP konfiguriert -> nur lokal vorbereitet
    try:
        m = EmailMessage()
        m["From"] = SMTP["von"]; m["To"] = an; m["Subject"] = betreff
        m.set_content(text)
        host, port, tls = SMTP["host"], SMTP["port"], SMTP["tls"]
        if tls == "ssl":
            with smtplib.SMTP_SSL(host, port, timeout=20) as s:
                s.login(SMTP["user"], SMTP["pass"]); s.send_message(m)
        else:
            with smtplib.SMTP(host, port, timeout=20) as s:
                if tls == "starttls":
                    s.starttls()
                s.login(SMTP["user"], SMTP["pass"]); s.send_message(m)
        return True
    except Exception:
        return False


def mail_mit_pdf(an, betreff, text, pdf_pfad, pdf_name=None):
    """Sendet eine Kunden-Mail mit PDF-Anhang (z.B. Offerte/Rechnung).
    Nutzt dieselbe Hostinger-SMTP-Config. Liefert True bei Erfolg."""
    if not SMTP["host"]:
        return False
    try:
        with open(pdf_pfad, "rb") as fh:
            pdata = fh.read()
        m = EmailMessage()
        m["From"] = SMTP["von"]; m["To"] = an; m["Subject"] = betreff
        m.set_content(text)
        m.add_attachment(pdata, maintype="application", subtype="pdf",
                         filename=pdf_name or os.path.basename(pdf_pfad))
        host, port, tls = SMTP["host"], SMTP["port"], SMTP["tls"]
        if tls == "ssl":
            with smtplib.SMTP_SSL(host, port, timeout=30) as s:
                s.login(SMTP["user"], SMTP["pass"]); s.send_message(m)
        else:
            with smtplib.SMTP(host, port, timeout=30) as s:
                if tls == "starttls":
                    s.starttls()
                s.login(SMTP["user"], SMTP["pass"]); s.send_message(m)
        return True
    except Exception as e:
        return False


def mail_html(an, betreff, text, html):
    """Sendet eine Kunden-Mail als HTML (multipart/alternative: Text + HTML).
    Kein Anhang -> Kunden muessen nichts oeffnen (Phishing-Angst minimiert).
    'text' ist der reine Text-Fallback, 'html' der gestaltete Inhalt.
    Liefert True bei Erfolg."""
    if not SMTP["host"]:
        return False
    try:
        m = EmailMessage()
        m["From"] = SMTP["von"]; m["To"] = an; m["Subject"] = betreff
        m.set_content(text)                       # Plain-Text-Fallback
        m.add_alternative(html, subtype="html")   # gestaltete HTML-Version
        host, port, tls = SMTP["host"], SMTP["port"], SMTP["tls"]
        if tls == "ssl":
            with smtplib.SMTP_SSL(host, port, timeout=30) as s:
                s.login(SMTP["user"], SMTP["pass"]); s.send_message(m)
        else:
            with smtplib.SMTP(host, port, timeout=30) as s:
                if tls == "starttls":
                    s.starttls()
                s.login(SMTP["user"], SMTP["pass"]); s.send_message(m)
        return True
    except Exception:
        return False


# --- Anbieter-Konsole: Passwort-Check (Standard bei Erststart) ------------
ANBIETER_STANDARD_PASSWORT = "devispro-admin-2026"


def check_password(pw):
    """Prueft das Anbieter-Konsole-Passwort (Standard oder gesetzt in admin_keys)."""
    try:
        if os.path.exists(ADMIN_KEYS_PFAD):
            with open(ADMIN_KEYS_PFAD, encoding="utf-8") as f:
                d = json.load(f)
            return pw == d.get("anbieter_passwort", ANBIETER_STANDARD_PASSWORT)
    except Exception:
        pass
    return pw == ANBIETER_STANDARD_PASSWORT
