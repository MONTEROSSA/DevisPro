"""WhatsApp-Bot fuers KMU (Angebot in 10 Sekunden per Chat).

Szenario: Kunde schreibt «Preis fuer Badrenovation?» -> KMU antwortet mit
einem DevisPro-Link (oder kurzem Angebotstext). DevisPro stellt dazu:
  - einen Deep-Link-Generator (wa.me/?text=...) fuer bestehende Devis
  - eine Webhook-Signatur-Pruefung (HMAC) fuer self-hosted Bot-Server
  - einen vorgefertigten Angebotstext (ohne Klick-Friktion)

Reine Stdlib. Kein externer Dienst noetig.
"""

import hmac
import hashlib
import json
import urllib.parse


def deep_link(deeplink_token, nachricht=None):
    """Erzeugt eine wa.me-URL, die in WhatsApp eine vorbefuellte Nachricht
    mit dem DevisPro-Link oeffnet."""
    base = "https://wa.me/"
    text = nachricht or f"Hier Ihr Angebot von DevisPro: https://devispro.de/d/{deeplink_token}"
    return base + "?" + urllib.parse.urlencode({"text": text})


def angebot_text(devis, profil, did, lang="de"):
    """Kurzer, klickfreier Angebotstext fuer WhatsApp (max ~1000 Zeichen)."""
    betrieb = profil.get("betrieb", "Ihr Betrieb")
    netto = sum((p.betrag or 0) for p in devis.positions)
    mwst = netto * float(profil.get("mwst_pct", 8.1) or 8.1) / 100.0
    brutto = netto + mwst
    lines = [
        f"📋 Angebot {betrieb}",
        f"Projekt: {devis.meta.get('project_name', '') or 'Ihr Bauvorhaben'}",
        f"Positionen: {len(devis.positions)}",
        f"Total: CHF {brutto:,.2f}".replace(",", "'"),
        f"Link: https://devispro.de/d/{did}",
        "Fragen? Antworten Sie einfach auf diese Nachricht.",
    ]
    return "\n".join(lines)


def verify_webhook(raw_body: bytes, signature_header: str, secret: str) -> bool:
    """Prueft X-Hub-Signature v1 (HMAC-SHA256, 'sha256=' Prefix)."""
    if not signature_header or not secret:
        return False
    if not signature_header.startswith("sha256="):
        return False
    expected = hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature_header[len("sha256="):])


def sign_payload(payload: dict, secret: str) -> str:
    raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    return "sha256=" + hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()
