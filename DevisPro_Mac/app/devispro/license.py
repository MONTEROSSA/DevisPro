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


def status() -> dict:
    lz = lizenz_laden()
    if not lz:
        return {"zustand": "keine_lizenz", "tage_bis_ablauf": None,
                "kunde_id": None, "gueltig_bis": None}
    bis = dt.date.fromisoformat(lz["gueltig_bis"])
    heute = dt.date.today()
    tage = (bis - heute).days
    if tage < 0:
        return {"zustand": "abgelaufen", "tage_bis_ablauf": tage,
                "kunde_id": lz["kunde_id"], "gueltig_bis": lz["gueltig_bis"]}
    if tage <= 30:
        return {"zustand": "erinnert", "tage_bis_ablauf": tage,
                "kunde_id": lz["kunde_id"], "gueltig_bis": lz["gueltig_bis"]}
    return {"zustand": "aktiv", "tage_bis_ablauf": tage,
            "kunde_id": lz["kunde_id"], "gueltig_bis": lz["gueltig_bis"]}


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


def darf_nutzen() -> bool:
    s = status()
    return s["zustand"] in ("aktiv", "erinnert")
