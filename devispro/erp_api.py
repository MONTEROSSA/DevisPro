"""Echte ERP-Connector-API (Abacus/Proffix/andere) – Spezifikation + Push.

Die bisherigen Connectoren exportieren eine CSV zum manuellen Import. Für
wiederkehrende Nutzer braucht es einen echten, automatisierten Push. Dieses
Modul definiert eine generische REST-API (HMAC-signiert) und liefert einen
Beispiel-Client, der Offerten/Rechnungen direkt an ein ERP uebertraegt.

Reine Stdlib (urllib). Kein Flask, kein Requests. Der KMU hostet den
Connector-Endpunkt im Buero; DevisPro pusht via HTTPS (oder LAN).
"""

import json
import hmac
import hashlib
import time
import urllib.request
import urllib.error


SPEZIFIKATION = {
    "endpoint": "POST /api/v1/belege",
    "auth": "HMAC-SHA256 im Header 'X-DevisPro-Sig' (sha256=<hex>) ueber Body+Timestamp",
    "headers": ["Content-Type: application/json", "X-DevisPro-Sig", "X-DevisPro-Ts"],
    "payload": {
        "beleg_typ": "ANGEBOT|RECHNUNG",
        "beleg_nr": "D-0001",
        "datum": "2026-08-12",
        "konto": "3200",
        "positionen": [
            {"pos": 1, "text": "...", "menge": 10, "einheit": "m3",
             "ep": 180.0, "betrag": 1800.0}
        ],
        "netto": 1800.0, "mwst_pct": 8.1, "brutto": 1945.8,
    },
    "erp_beispiele": {
        "abacus": "Abacus API / FiBu-Import (Belegimport über JSON-Adapter)",
        "proffix": "Proffix PX-REST oder PX-Datei (Offerten/Rechnungen)",
        "generic": "Jeder Endpunkt, der obiges JSON akzeptiert",
    },
}


def sign(body_json: str, secret: str, ts=None):
    ts = ts or int(time.time())
    raw = (str(ts) + body_json).encode("utf-8")
    sig = hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()
    return {"X-DevisPro-Sig": "sha256=" + sig, "X-DevisPro-Ts": str(ts)}


def beleg_payload(devis, profil, beleg_nr, typ="ANGEBOT", konto="3200"):
    netto = sum((p.betrag or 0) for p in devis.positions)
    mwst_pct = float(profil.get("mwst_pct", 8.1) or 8.1)
    mwst = netto * mwst_pct / 100.0
    return {
        "beleg_typ": typ,
        "beleg_nr": beleg_nr,
        "datum": str(devis.meta.get("date", "") or ""),
        "konto": konto,
        "positionen": [
            {"pos": i + 1, "text": p.text, "menge": p.menge,
             "einheit": p.einheit, "ep": p.ep, "betrag": p.betrag}
            for i, p in enumerate(devis.positions)
        ],
        "netto": round(netto, 2),
        "mwst_pct": mwst_pct,
        "brutto": round(netto + mwst, 2),
    }


def push(erp_url, payload, secret, timeout=20):
    """Sendet das Beleg-JSON HMAC-signiert an den ERP-Endpunkt.

    Gibt (ok, status_or_error) zurueck.
    """
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    hdrs = sign(body.decode("utf-8"), secret)
    hdrs["Content-Type"] = "application/json"
    req = urllib.request.Request(erp_url, data=body, headers=hdrs, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return True, r.status
    except urllib.error.HTTPError as e:
        return False, f"HTTP {e.code}"
    except Exception as e:
        return False, str(e)


def spezifikation():
    return SPEZIFIKATION
