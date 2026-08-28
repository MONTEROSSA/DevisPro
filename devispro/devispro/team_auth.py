"""Lokale Team- & Rollen-Verwaltung (KMU-Mehrbenutzer, kein Cloud-Zwang).
Erweitert: projektleiter Rolle, Berechtigungs-Checks, UI-Integration.
"""
from __future__ import annotations
import os
import json
import hmac
import hashlib
import secrets
import datetime as dt
from typing import Dict, List, Optional, Set
from pathlib import Path

DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
PFAD = os.path.join(DATA, "team.json")
SEK = secrets.token_hex(32)
DAUER_H = 8

# Rollen-Hierarchie (höher = mehr Rechte)
ROLLEN = {
    "admin": {"label": "Administrator", "level": 100, "desc": "Voller Zugriff, User-Verwaltung, Freigabe"},
    "projektleiter": {"label": "Projektleiter", "level": 75, "desc": "Projekte verwalten, Freigabe, Reports, Team-Sync"},
    "buero": {"label": "Büro", "level": 50, "desc": "Offerten/Rechnungen erstellen, Devis freigeben"},
    "aussendienst": {"label": "Aussendienst", "level": 25, "desc": "Nur Devis erfassen/bepreisen, KEINE Freigabe"},
    "viewer": {"label": "Viewer", "level": 10, "desc": "Nur Lesen, Export, keine Änderungen"},
}

# Permission Matrix
PERMISSIONS: Dict[str, Set[str]] = {
    "admin": {
        "devis:create", "devis:read", "devis:update", "devis:delete", "devis:finalize",
        "offerte:create", "rechnung:create", "freigabe:erteilen",
        "team:manage", "sync:manage", "settings:manage",
        "preise:manage", "analysen:manage", "export:all",
    },
    "projektleiter": {
        "devis:create", "devis:read", "devis:update", "devis:finalize",
        "offerte:create", "rechnung:create", "freigabe:erteilen",
        "sync:manage", "preise:read", "analysen:manage", "export:all",
    },
    "buero": {
        "devis:create", "devis:read", "devis:update", "devis:finalize",
        "offerte:create", "rechnung:create", "freigabe:erteilen",
        "preise:read", "export:angebot",
    },
    "aussendienst": {
        "devis:create", "devis:read", "devis:update",
        "preise:read",
    },
    "viewer": {
        "devis:read", "export:pdf",
    },
}

FREIGABE_ROLLEN = {"admin", "projektleiter", "buero"}


def _laden() -> Dict:
    if os.path.exists(PFAD):
        try:
            with open(PFAD, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"mitglieder": {}, "next_id": 1}


def _speichern(d: Dict):
    os.makedirs(DATA, exist_ok=True)
    tmp = PFAD + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=1)
    os.replace(tmp, PFAD)


def _pbkdf2(passwort: str, salt: bytes) -> str:
    return hashlib.pbkdf2_hmac("sha256", passwort.encode("utf-8"), salt, 100_000).hex()


def anlegen(benutzer: str, passwort: str, rolle: str = "aussendienst", angelegt_von: str = "admin") -> int:
    benutzer = (benutzer or "").strip()
    rolle = (rolle or "aussendienst").strip().lower()
    if not benutzer:
        raise ValueError("Benutzername erforderlich")
    if rolle not in ROLLEN:
        raise ValueError(f"Unbekannte Rolle: {rolle}. Verfügbar: {list(ROLLEN.keys())}")
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


def loeschen(benutzer: str) -> bool:
    d = _laden()
    for kid, m in list(d["mitglieder"].items()):
        if m["benutzer"].lower() == (benutzer or "").lower():
            del d["mitglieder"][kid]
            _speichern(d)
            return True
    return False


def pruefen(benutzer: str, passwort: str) -> bool:
    d = _laden()
    for m in d["mitglieder"].values():
        if m["benutzer"].lower() == (benutzer or "").lower() and m.get("aktiv", True):
            erwartet = _pbkdf2(passwort, bytes.fromhex(m["salt"]))
            return hmac.compare_digest(erwartet, m["hash"])
    return False


def rolle_von(benutzer: str) -> Optional[str]:
    d = _laden()
    for m in d["mitglieder"].values():
        if m["benutzer"].lower() == (benutzer or "").lower():
            return m["rolle"]
    return None


def rolle_aendern(benutzer: str, neue_rolle: str, geaendert_von: str) -> bool:
    """Ändert Rolle (nur admin/projektleiter dürfen)."""
    if neue_rolle not in ROLLEN:
        raise ValueError("Unbekannte Rolle")
    # Berechtigung prüfen
    changer_role = rolle_von(geaendert_von)
    if changer_role not in ("admin", "projektleiter"):
        raise PermissionError("Keine Berechtigung für Rollen-Änderung")
    # Admin kann nicht degradiert werden (Schutz)
    if rolle_von(benutzer) == "admin" and neue_rolle != "admin":
        raise PermissionError("Admin-Rolle kann nicht geändert werden")
    
    d = _laden()
    for m in d["mitglieder"].values():
        if m["benutzer"].lower() == (benutzer or "").lower():
            m["rolle"] = neue_rolle
            _speichern(d)
            return True
    return False


def aktiv_setzen(benutzer: str, aktiv: bool) -> bool:
    d = _laden()
    for m in d["mitglieder"].values():
        if m["benutzer"].lower() == (benutzer or "").lower():
            m["aktiv"] = aktiv
            _speichern(d)
            return True
    return False


def liste() -> List[Dict]:
    d = _laden()
    result = []
    for m in d["mitglieder"].values():
        role_info = ROLLEN.get(m["rolle"], {})
        result.append({
            "id": m["id"],
            "benutzer": m["benutzer"],
            "rolle": m["rolle"],
            "rolle_label": role_info.get("label", m["rolle"]),
            "rolle_level": role_info.get("level", 0),
            "aktiv": m.get("aktiv", True),
            "angelegt": m.get("angelegt", ""),
            "angelegt_von": m.get("angelegt_von", ""),
        })
    # Sort by level desc, then name
    result.sort(key=lambda x: (-x["rolle_level"], x["benutzer"]))
    return result


def login_token(benutzer: str) -> str:
    now = dt.datetime.now().isoformat()
    payload = f"{benutzer}|{now}"
    sig = hmac.new(SEK.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return f"{payload}|{sig}"


def token_gueltig(token: str) -> Optional[str]:
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


def rolle_von_token(token: str) -> Optional[str]:
    benutzer = token_gueltig(token)
    if not benutzer:
        return None
    return rolle_von(benutzer)


def hat_berechtigung(token: str, permission: str) -> bool:
    """Prüft ob Token eine bestimmte Permission hat."""
    rolle = rolle_von_token(token)
    if not rolle:
        return False
    return permission in PERMISSIONS.get(rolle, set())


def hat_rolle_mindestens(token: str, min_rolle: str) -> bool:
    """Prüft ob Token mindestens min_rolle Level hat."""
    rolle = rolle_von_token(token)
    if not rolle or min_rolle not in ROLLEN:
        return False
    return ROLLEN[rolle]["level"] >= ROLLEN[min_rolle]["level"]


def darf_freigeben(token: str) -> bool:
    """True, wenn der eingeloggte Benutzer den Review-Blocker aufheben darf."""
    benutzer = token_gueltig(token)
    if not benutzer:
        return False
    return rolle_von(benutzer) in FREIGABE_ROLLEN


def darf_devis_loeschen(token: str) -> bool:
    return hat_berechtigung(token, "devis:delete")


def darf_team_verwalten(token: str) -> bool:
    return hat_berechtigung(token, "team:manage")


def darf_sync_verwalten(token: str) -> bool:
    return hat_berechtigung(token, "sync:manage")


def get_rolle_info(rolle: str) -> Dict:
    return ROLLEN.get(rolle, {})


def get_alle_rollen() -> Dict:
    return ROLLEN.copy()


# Test
if __name__ == "__main__":
    # Clean test
    if os.path.exists(PFAD):
        os.remove(PFAD)
    
    anlegen("admin", "admin123", "admin")
    anlegen("hans", "hans123", "projektleiter")
    anlegen("peter", "peter123", "buero")
    anlegen("thomas", "thomas123", "aussendienst")
    anlegen("gast", "gast123", "viewer")
    
    print("Team:")
    for m in liste():
        print(f"  {m['benutzer']}: {m['rolle_label']} (Level {m['rolle_level']})")
    
    token = login_token("hans")
    print(f"\nHans Token: {token[:30]}...")
    print(f"Hans Rolle: {rolle_von_token(token)}")
    print(f"Hans darf freigeben: {darf_freigeben(token)}")
    print(f"Hans hat 'team:manage': {hat_berechtigung(token, 'team:manage')}")
    print(f"Hans hat 'devis:delete': {hat_berechtigung(token, 'devis:delete')}")
    print(f"Hans mind. projektleiter: {hat_rolle_mindestens(token, 'projektleiter')}")
    
    token2 = login_token("thomas")
    print(f"\nThomas (aussendienst) darf freigeben: {darf_freigeben(token2)}")
    print(f"Thomas hat 'freigabe:erteilen': {hat_berechtigung(token2, 'freigabe:erteilen')}")