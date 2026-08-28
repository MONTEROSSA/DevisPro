"""Lizenz-Modul (lokal im KMU).

Sperrt die App, wenn keine gueltige Lizenz vorliegt oder sie abgelaufen ist.
Ein Jahres-Code (vom Anbieter mit dem PRIVATEN Schluessel signiert)
verlaengert die Lizenz um 1 Jahr.

Sicherheitsmodell (asymmetrisch, reiner Python, keine C-Bindings):
  - Anbieter signiert  "kunde_id|gueltig_bis"  mit PRIVATE Key  -> Signatur
  - Code-Format:        "kunde_id|gueltig_bis|SIGNATUR"  (| getrennt)
  - KMU verifiziert mit dem PBULIC Key (hier einkompiliert).
  - Der PRIVATE Key verlaesst NIE den Anbieter (liegt in data/admin_keys.json,
    wird NICHT an KMU ausgeliefert). Ein KMU kann daher keine gueltigen
    Codes faelschen.

Der einkompilierte PUBLIC Key unten wurde einmalig mit crypto_rsa generiert.
"""
import os
import json
import datetime as dt

from devispro import crypto_rsa as rsa

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(HERE, "data")
LIZENZ_PFAD = os.path.join(DATA, "lizenz.json")

# --- PUBLIC KEY (einkompiliert; nur zur Verifikation) --------------------
PUBLIC_KEY = rsa.key_from_str(
    "786384224379318110360856249497529226727116363957243417842276"
    "536270069534315056275833162703364510833722572439778862205964"
    "177497392112761359005688733177110464685513028044489201801331"
    "294193585966379129381955298948101587142442990207499327607697"
    "955525665478238156761313923135912918917872746265508262026715"
    "37589423:65537"
)


def _sign_string(kunde_id: str, gueltig_bis: str) -> str:
    """Code-String bauen: kunde_id|gueltig_bis|signatur (vom Anbieter signiert)."""
    msg = f"{kunde_id}|{gueltig_bis}"
    # Signatur wird hier NICHT erzeugt (kein Private Key) -> nur Verifikation.
    return msg  # Platzhalter; echte Signatur kommt vom Admin-Modul


def lizenz_laden() -> "dict or None":
    if not os.path.exists(LIZENZ_PFAD):
        return None
    try:
        with open(LIZENZ_PFAD, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def modus() -> str:
    """Aktiver Modus aus der Lizenz: 'voll' | 'ppd' | 'trial' | 'starter' | 'professional' | 'enterprise'.

    PREISMODELL v3 FINAL (3-Tarif-Modell):
    - Starter (PPD): modus = 'starter', guthaben_devis für Prepaid
    - Professional: modus = 'professional' (subscription), gueltig_bis für Ablauf
    - Enterprise: modus = 'enterprise' (custom), gueltig_bis für Ablauf
    - Legacy: 'voll' (einmal), 'ppd' (altes PPD), 'trial' (Test)
    """
    lz = lizenz_laden() or {}
    # Neu: direkter Modus aus 3-Tarif-Modell
    if lz.get("modus") in ("starter", "professional", "enterprise"):
        return lz["modus"]
    # Legacy-Rückwärtskompatibilität
    if (lz.get("modus") or "").lower() == "ppd":
        return "starter"  # PPD -> Starter
    return "trial" if not lz.get("gueltig_bis") else "voll"


def _ppd_status(lz: dict) -> dict:
    """PPD-spezifischer Zustand: aktiv oder ueberzogen.

    Gilt fuer Starter (PPD) und Legacy-PPD.
    ENTSCHEIDUNG (pragmatisch): 'ueberzogen' = Ehrenwort-Rechnung offen
    bzw. Prepaid-Guthaben negativ -> Soft-Sperre/Watermark statt harter
    Blockade (Konzept B.4). Die App bleibt lesend/nutzend erreichbar.

    PROFESSOR-FIX (2026-08-26): Die Pruefung hing zuvor am Flag
    'ppd_bezahlt' — das setzt NIE jemand auf False (_ehrenwort_aktivieren()'s
    schreibt ppd_bezahlt=True, es gibt keinen Zahlungs-Eingang im Code).
    Folge: negativer Zaehler blieb fuer immer 'ppd_aktiv', Watermark und
    Warnleiste wären nie erschienen. Konzept Entscheidung 4 sagt aber:
    Watermark bei offener Rechnung ODER ueberzogenem Guthaben -> massgebend
    ist ausschliesslich guthaben_devis < 0.
    """
    g = lz.get("guthaben_devis")
    if g is not None and int(g) < 0:
        return {"zustand": "ppd_ueberzogen"}
    return {"zustand": "starter_aktiv",
            "guthaben_devis": None if g is None else int(g)}


def status() -> dict:
    lz = lizenz_laden()
    if not lz:
        return {"zustand": "keine_lizenz", "tage_bis_ablauf": None,
                "kunde_id": None, "gueltig_bis": None, "modus": None}

    # 3-Tarif-Modell: Starter (PPD), Professional, Enterprise
    m = lz.get("modus")
    if m in ("starter", "professional", "enterprise"):
        if m == "starter":
            s = _ppd_status(lz)
            return {"zustand": s["zustand"], "tage_bis_ablauf": None,
                    "kunde_id": lz.get("kunde_id"), "gueltig_bis": None,
                    "guthaben_devis": s.get("guthaben_devis"),
                    "modus": "starter"}
        # Professional/Enterprise: Zeit-basiert (Subscription)
        bis = lz.get("gueltig_bis")
        if not bis:
            return {"zustand": "keine_lizenz", "tage_bis_ablauf": None,
                    "kunde_id": lz.get("kunde_id"), "gueltig_bis": None,
                    "modus": m}
        try:
            bis_date = dt.date.fromisoformat(bis)
        except Exception:
            return {"zustand": "keine_lizenz", "tage_bis_ablauf": None,
                    "kunde_id": lz.get("kunde_id"), "gueltig_bis": None,
                    "modus": m}
        heute = dt.date.today()
        tage = (bis_date - heute).days
        if tage < 0:
            return {"zustand": "abgelaufen", "tage_bis_ablauf": tage,
                    "kunde_id": lz["kunde_id"], "gueltig_bis": lz["gueltig_bis"],
                    "modus": m}
        if tage <= 30:
            return {"zustand": "erinnert", "tage_bis_ablauf": tage,
                    "kunde_id": lz["kunde_id"], "gueltig_bis": lz["gueltig_bis"],
                    "modus": m}
        return {"zustand": "aktiv", "tage_bis_ablauf": tage,
                "kunde_id": lz["kunde_id"], "gueltig_bis": lz["gueltig_bis"],
                "modus": m}

    # Legacy: PPD (alt) -> als Starter behandeln
    if (m or "").lower() == "ppd":
        s = _ppd_status(lz)
        return {"zustand": s["zustand"], "tage_bis_ablauf": None,
                "kunde_id": lz.get("kunde_id"), "gueltig_bis": None,
                "guthaben_devis": s.get("guthaben_devis"),
                "modus": "starter"}

    # Legacy: Einmal / Trial (zeitbasiert)
    bis = lz.get("gueltig_bis")
    if not bis:
        return {"zustand": "keine_lizenz", "tage_bis_ablauf": None,
                "kunde_id": lz.get("kunde_id"), "gueltig_bis": None,
                "modus": "trial"}
    try:
        bis_date = dt.date.fromisoformat(bis)
    except Exception:
        return {"zustand": "keine_lizenz", "tage_bis_ablauf": None,
                "kunde_id": lz.get("kunde_id"), "gueltig_bis": None,
                "modus": "trial"}
    heute = dt.date.today()
    tage = (bis_date - heute).days
    if tage < 0:
        return {"zustand": "abgelaufen", "tage_bis_ablauf": tage,
                "kunde_id": lz["kunde_id"], "gueltig_bis": lz["gueltig_bis"],
                "modus": "voll"}
    if tage <= 30:
        return {"zustand": "erinnert", "tage_bis_ablauf": tage,
                "kunde_id": lz["kunde_id"], "gueltig_bis": lz["gueltig_bis"],
                "modus": "voll"}
    return {"zustand": "aktiv", "tage_bis_ablauf": tage,
            "kunde_id": lz["kunde_id"], "gueltig_bis": lz["gueltig_bis"],
            "modus": "voll"}


def _schreibe_lizenz(kunde_id: str, gueltig_bis: str, code_str: str, tarif: str = "devis"):
    heute = dt.date.today()
    neu = {
        "kunde_id": kunde_id,
        "gueltig_bis": gueltig_bis,
        "code": code_str,
        "tarif": (tarif or "devis").lower(),
        "ausgestellt_am": heute.isoformat(),
    }
    with open(LIZENZ_PFAD, "w", encoding="utf-8") as f:
        json.dump(neu, f, indent=2, ensure_ascii=False)
    return neu


def tarif() -> str:
    """Liest den Tarif aus der lokalen Lizenz (Default 'devis')."""
    from devispro import pricing as _pz
    return _pz.tarif_aus_lizenz(lizenz_laden())


def code_anwenden(kunde_id: str, code: str) -> dict:
    """Verlaengert Lizenz um 1 Jahr, wenn Code gueltig signiert ist.

    code-Format:  kunde_id|gueltig_bis|SIGNATUR
    Gibt dict: {ok, gueltig_bis, fehler}.
    """
    code = (code or "").strip()
    if not code:
        return {"ok": False, "fehler": "Kein Code eingegeben."}
    teile = code.split("|")
    if len(teile) != 3:
        return {"ok": False, "fehler": "Ungültiges Code-Format."}
    c_kid, c_bis, c_sig = teile
    if c_kid != kunde_id:
        return {"ok": False, "fehler": "Code gehört zu einer anderen Kunden-ID."}
    msg = f"{c_kid}|{c_bis}"
    if not rsa.verify(PUBLIC_KEY, msg, c_sig):
        return {"ok": False, "fehler": "Ungültiger (nicht signierter) Code."}
    # Ablaufdatum aus Code uebernehmen (vom Anbieter festgelegt)
    try:
        neu_bis = dt.date.fromisoformat(c_bis)
    except Exception:
        return {"ok": False, "fehler": "Ungültiges Ablaufdatum im Code."}
    heute = dt.date.today()
    if neu_bis < heute:
        return {"ok": False, "fehler": "Code ist bereits abgelaufen."}
    _schreibe_lizenz(kunde_id, c_bis, code)
    return {"ok": True, "gueltig_bis": c_bis}


def ppd_code_anwenden(kunde_id: str, code: str) -> dict:
    """Wendet einen PPD-Code an: "kunde_id|PPD:<anzahl>|SIGNATUR".

    PREISMODELL v3 (3-Tarif-Modell): derselbe RSA-Mechanismus wie bei den
    Jahres-Codes. Setzt modus=starter und guthaben_devis=<anzahl> (Prepaid)
    bzw. addiert zu bestehendem Guthaben.
    """
    code = (code or "").strip()
    teile = code.split("|")
    if len(teile) != 3:
        return {"ok": False, "fehler": "Ungültiges Code-Format."}
    c_kid, c_payload, c_sig = teile
    if c_kid != kunde_id:
        return {"ok": False, "fehler": "Code gehört zu einer anderen Kunden-ID."}
    if not c_payload.upper().startswith("PPD:"):
        return {"ok": False, "fehler": "Kein Pay-per-Devis-Code (PPD:<n> erwartet)."}
    try:
        anzahl = int(c_payload.split(":", 1)[1])
        if anzahl < 1 or anzahl > 1000:
            raise ValueError
    except ValueError:
        return {"ok": False, "fehler": "Ungültige Devis-Anzahl im Code."}
    if not rsa.verify(PUBLIC_KEY, f"{c_kid}|{c_payload}", c_sig):
        return {"ok": False, "fehler": "Ungültiger (nicht signierter) Code."}
    lz = lizenz_laden() or {}
    alt = int(lz.get("guthaben_devis") or 0) if lz.get("modus") in ("starter", "ppd") else 0
    neu = {
        "kunde_id": kunde_id,
        "modus": "starter",
        "guthaben_devis": alt + anzahl,
        "ppd_bezahlt": True,
        "code": code,
        "gueltig_bis": lz.get("gueltig_bis", ""),
        "ausgestellt_am": dt.date.today().isoformat(),
    }
    with open(LIZENZ_PFAD, "w", encoding="utf-8") as f:
        json.dump(neu, f, indent=2, ensure_ascii=False)
    return {"ok": True, "modus": "starter", "guthaben_devis": neu["guthaben_devis"]}


def ppd_devis_verbrauchen(n: int = 1) -> dict:
    """Zieht n Devis vom Prepaid-Guthaben ab (Ehrenwort: Zähler läuft ins
    Negative -> status() meldet ppd_ueberzogen). Gibt neuen Stand zurück."""
    lz = lizenz_laden()
    if not lz or lz.get("modus") != "ppd":
        return {"ok": False, "fehler": "Kein PPD-Modus aktiv."}
    lz["guthaben_devis"] = int(lz.get("guthaben_devis") or 0) - n
    with open(LIZENZ_PFAD, "w", encoding="utf-8") as f:
        json.dump(lz, f, indent=2, ensure_ascii=False)
    return {"ok": True, "guthaben_devis": lz["guthaben_devis"]}


def darf_nutzen() -> bool:
    """True = ein Devis darf finalisiert/bepreist werden.

    PREISMODELL v3 (3-Tarif-Modell):
      - professional / enterprise (aktiv/erinnert)    -> True (unbegrenzt)
      - starter (starter_aktiv / ppd_ueberzogen)     -> True (Soft-Sperre bei ueberzogen;
                                                        Ehrenwort-Kunde bleibt nutzbar,
                                                        Watermark + Warnleiste)
      - starter (keine_lizenz = Trial)               -> True solange Gratis-Kontingent
                                                        (5 finalisierte Devis) nicht leer
      - voll (aktiv/erinnert)                        -> True
      - abgelaufen                                   -> False
    """
    s = status()
    z = s["zustand"]
    m = s.get("modus")

    # 3-Tarif-Modell: Professional/Enterprise = unbegrenzt
    if m in ("professional", "enterprise") and z in ("aktiv", "erinnert"):
        return True

    # Starter (PPD): immer erlaubt (Soft-Sperre bei ueberzogen)
    if m == "starter" and z in ("starter_aktiv", "ppd_ueberzogen"):
        return True

    # Starter Trial: 5 Gratis-Devis
    if m == "starter" and z == "keine_lizenz":
        from devispro import trial_counter as tc
        return tc.gratis_erlaubt()

    # Legacy: Voll-Lizenz
    if m == "voll" and z in ("aktiv", "erinnert"):
        return True

    # Legacy PPD (wird als starter behandelt)
    if m == "starter" and z in ("starter_aktiv", "ppd_ueberzogen"):
        return True

    return False
