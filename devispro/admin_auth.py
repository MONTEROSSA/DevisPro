"""Einfache Admin-Authentifizierung (lokal, ausreichend fuer KMU-Anbieter-Tool).

Kein Hochsicherheits-System, aber verhindert, dass jemand ohne Passwort
Kunden freischaltet / Codes erzeugt. Passwort wird einmalig gesetzt
(admin_pass.json), Default bei Erststart.

Session: ein signierter Cookie (HMAC ueber kunde_id=admin|zeit), gueltig 8h.
"""
import os
import json
import hashlib
import hmac
import secrets
import datetime as dt

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(HERE, "data")
PASS_PFAD = os.path.join(DATA, "admin_pass.json")
SESSION_SEK = secrets.token_hex(32)  # fluechtig pro Prozessstart; ausreichend fuer lokal
SESSION_DAUER_H = 8

# Default-Passwort nur fuer Erststart; sofort aendern!
DEFAULT_PASS = "devispro-admin-2026"


def _lade_hash():
    if os.path.exists(PASS_PFAD):
        with open(PASS_PFAD, encoding="utf-8") as f:
            return json.load(f)["hash"]
    h = hashlib.sha256(DEFAULT_PASS.encode()).hexdigest()
    with open(PASS_PFAD, "w", encoding="utf-8") as f:
        json.dump({"hash": h, "changed": False}, f, indent=2)
    return h


def passwort_setzen(neues: str):
    h = hashlib.sha256(neues.encode()).hexdigest()
    with open(PASS_PFAD, "w", encoding="utf-8") as f:
        json.dump({"hash": h, "changed": True}, f, indent=2)


def passwort_aendern_noetig() -> bool:
    if os.path.exists(PASS_PFAD):
        with open(PASS_PFAD, encoding="utf-8") as f:
            return not json.load(f).get("changed", False)
    return True


def pruefen(passwort: str) -> bool:
    h = _lade_hash()
    return hmac.compare_digest(h, hashlib.sha256(passwort.encode()).hexdigest())


def session_token() -> str:
    now = dt.datetime.now().isoformat()
    payload = f"admin|{now}"
    sig = hmac.new(SESSION_SEK.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return f"{payload}|{sig}"


def session_gueltig(token: str) -> bool:
    if not token or "|" not in token:
        return False
    payload, sig = token.rsplit("|", 1)
    erwartet = hmac.new(SESSION_SEK.encode(), payload.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(erwartet, sig):
        return False
    try:
        ts = dt.datetime.fromisoformat(payload.split("|", 1)[1])
    except Exception:
        return False
    return (dt.datetime.now() - ts) < dt.timedelta(hours=SESSION_DAUER_H)
