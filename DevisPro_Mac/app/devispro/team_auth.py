"""Lokale Team- & Rollen-Verwaltung (KMU-Mehrbenutzer, kein Cloud-Zwang).

Ein KMU legt Mitarbeiterkonten an:
  - admin     : voller Zugriff inkl. Fachkraft-Freigabe (Review-Blocker aufheben)
  - buero     : Offerten/Rechnungen erstellen, Devis freigeben
  - aussendienst : nur Devis erfassen/bepreisen, KEINE Freigabe

Authentifizierung: PBKDF2-HMAC-SHA256 (reine Stdlib, kein bcrypt noetig).
Session: signierter Cookie (Rolle im Payload), gueltig 8h.

Reine Stdlib; Speicherung in data/team.json.
"""

import os
import json
import hmac
import hashlib
import secrets
import datetime as dt

DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
PFAD = os.path.join(DATA, "team.json")
SEK = secrets.token_hex(32)            # fluechtig pro Prozessstart; ausreichend fuer lokal
DAUER_H = 8

ROLLEN = {
    "admin": "Administrator (voller Zugriff, Freigabe)",
    "buero": "Büro (Offerten, Rechnungen, Freigabe)",
    "aussendienst": "Aussendienst (nur erfassen/bepreisen)",
}
# Welche Rollen duerfen den Review-Blocker (Fachkraft-Freigabe) aufheben?
FREIGABE_ROLLEN = {"admin", "buero"}


def _laden():
    if os.path.exists(PFAD):
        try:
            with open(PFAD, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"mitglieder": {}, "next_id": 1}


def _speichern(d):
    os.makedirs(DATA, exist_ok=True)
    tmp = PFAD + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=1)
    os.replace(tmp, PFAD)


def _pbkdf2(passwort: str, salt: bytes) -> str:
    return hashlib.pbkdf2_hmac("sha256", passwort.encode("utf-8"), salt, 100_000).hex()


def anlegen(benutzer, passwort, rolle="aussendienst", angelegt_von="admin"):
    benutzer = (benutzer or "").strip()
    rolle = (rolle or "aussendienst").strip().lower()
    if not benutzer:
        raise ValueError("Benutzername erforderlich")
    if rolle not in ROLLEN:
        raise ValueError("Unbekannte Rolle")
    if len(passwort or "") < 6:
        raise ValueError("Passwort mindestens 6 Zeichen")
    d = _laden()
    for m in d["mitglieder"].values():
        if m["benutzer"].lower() == benutzer.lower():
            raise ValueError("Benutzer existiert bereits")
    salt = secrets.token_bytes(16)
    d["mitglieder"][str(d["next_id"])] = {
        "id": str(d["next_id"]),
        "benutzer": benutzer,
        "salt": salt.hex(),
        "hash": _pbkdf2(passwort, salt),
        "rolle": rolle,
        "angelegt": dt.date.today().isoformat(),
        "angelegt_von": angelegt_von,
        "aktiv": True,
    }
    d["next_id"] += 1
    _speichern(d)
    return d["next_id"] - 1


def loeschen(benutzer):
    d = _laden()
    for kid, m in list(d["mitglieder"].items()):
        if m["benutzer"].lower() == (benutzer or "").lower():
            del d["mitglieder"][kid]
            _speichern(d)
            return True
    return False


def pruefen(benutzer, passwort):
    d = _laden()
    for m in d["mitglieder"].values():
        if m["benutzer"].lower() == (benutzer or "").lower() and m.get("aktiv", True):
            erwartet = _pbkdf2(passwort, bytes.fromhex(m["salt"]))
            return hmac.compare_digest(erwartet, m["hash"])
    return False


def rolle_von(benutzer):
    d = _laden()
    for m in d["mitglieder"].values():
        if m["benutzer"].lower() == (benutzer or "").lower():
            return m["rolle"]
    return None


def liste():
    d = _laden()
    return [{"id": m["id"], "benutzer": m["benutzer"], "rolle": m["rolle"],
             "aktiv": m.get("aktiv", True), "angelegt": m.get("angelegt", "")}
            for m in d["mitglieder"].values()]


def login_token(benutzer):
    now = dt.datetime.now().isoformat()
    payload = f"{benutzer}|{now}"
    sig = hmac.new(SEK.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return f"{payload}|{sig}"


def token_gueltig(token):
    if not token or "|" not in token:
        return None
    payload, sig = token.rsplit("|", 1)
    erwartet = hmac.new(SEK.encode(), payload.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(erwartet, sig):
        return None
    try:
        benutzer, ts = payload.split("|", 1)
        ts = dt.datetime.fromisoformat(ts)
    except Exception:
        return None
    if (dt.datetime.now() - ts) > dt.timedelta(hours=DAUER_H):
        return None
    return benutzer


def darf_freigeben(token):
    """True, wenn der eingeloggte Benutzer den Review-Blocker aufheben darf."""
    benutzer = token_gueltig(token)
    if not benutzer:
        return False
    return rolle_von(benutzer) in FREIGABE_ROLLEN
