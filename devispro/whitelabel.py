"""White-Label & Verbands-Lizenz (Bulk-Lizenzen).

Ermoeglicht Verbaende / Haendler, DevisPro markengerecht zu verteilen:
- Branding (Firmenname, Logo-Pfad, Akzentfarbe) konfigurierbar
- Bulk-Lizenzcodes: ein Verband bekommt N Codes, die er an Mitglieder
  weitergeben kann (jeder Code schoepft eine Vollversion/Pro-Lizenz).

Reine Stdlib. Codes sind HMAC-signiert (crypto_rsa nicht noetig, hier
reicht ein secreter Key aus data/abo.json bzw. admin_keys).
"""
import os
import json
import hmac
import hashlib
import secrets

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(HERE, "data")
WL_PFAD = os.path.join(DATA, "whitelabel.json")
CODES_PFAD = os.path.join(DATA, "lizenz_codes.json")


def _secret() -> bytes:
    # stabiler Key aus admin_keys (public reicht als deterministischer Salt)
    try:
        k = json.load(open(os.path.join(DATA, "admin_keys.json"), encoding="utf-8"))
        mat = (k.get("public", "") or k.get("private", "") or "devispro-wl")
        return hashlib.sha256(mat.encode("utf-8")).digest()
    except Exception:
        return b"devispro-whitelabel-secret"


def branding_laden() -> dict:
    if os.path.exists(WL_PFAD):
        try:
            return json.load(open(WL_PFAD, encoding="utf-8"))
        except Exception:
            pass
    return {"firma": "DevisPro", "logo": "", "farbe": "#15803d"}


def branding_setzen(firma: str, logo: str = "", farbe: str = "#15803d") -> dict:
    neu = {"firma": firma, "logo": logo, "farbe": farbe}
    with open(WL_PFAD, "w", encoding="utf-8") as f:
        json.dump(neu, f, indent=2, ensure_ascii=False)
    return neu


def code_erzeugen(tarif: str = "pro", verband: str = "", anzahl: int = 1) -> list:
    """Erzeugt `anzahl` signierte Lizenzcodes fuer einen Tarif/Verband."""
    codes = []
    bestehend = []
    if os.path.exists(CODES_PFAD):
        try:
            bestehend = json.load(open(CODES_PFAD, encoding="utf-8"))
        except Exception:
            bestehend = []
    for _ in range(anzahl):
        raw = secrets.token_hex(8).upper()
        sig = hmac.new(_secret(), (raw + "|" + tarif).encode("utf-8"), hashlib.sha256).hexdigest()[:8].upper()
        code = f"DP-{tarif[:1].upper()}-{raw}-{sig}"
        eintrag = {"code": code, "tarif": tarif, "verband": verband, "eingeloest": False}
        bestehend.append(eintrag)
        codes.append(code)
    with open(CODES_PFAD, "w", encoding="utf-8") as f:
        json.dump(bestehend, f, indent=2, ensure_ascii=False)
    return codes


def code_pruefen(code: str) -> dict:
    """Prueft einen Code und gibt Tarif / Gueltigkeit zurueck."""
    if os.path.exists(CODES_PFAD):
        try:
            bestehend = json.load(open(CODES_PFAD, encoding="utf-8"))
        except Exception:
            bestehend = []
        for e in bestehend:
            if e.get("code") == code:
                return {"gueltig": True, "tarif": e["tarif"], "verband": e.get("verband", ""),
                        "eingeloest": e.get("eingeloest", False)}
    return {"gueltig": False}


def code_einloesen(code: str) -> dict:
    """Loest einen Code ein -> setzt abo.json auf den Tarif."""
    pr = code_pruefen(code)
    if not pr.get("gueltig") or pr.get("eingeloest"):
        return {"ok": False, "fehler": "Code ungueltig oder bereits eingeloest"}
    from . import abo as abo_mod
    res = abo_mod.setze_tarif(kunde_id=code, tarif=pr["tarif"])
    # als eingeloest markieren
    bestehend = json.load(open(CODES_PFAD, encoding="utf-8"))
    for e in bestehend:
        if e.get("code") == code:
            e["eingeloest"] = True
    with open(CODES_PFAD, "w", encoding="utf-8") as f:
        json.dump(bestehend, f, indent=2, ensure_ascii=False)
    return {"ok": True, "tarif": pr["tarif"], **res}


def codes_liste() -> list:
    if os.path.exists(CODES_PFAD):
        try:
            return json.load(open(CODES_PFAD, encoding="utf-8"))
        except Exception:
            pass
    return []
