"""M28: Stripe-Integration fuer DevisPro Pay-per-Devis.

Ermoeglicht echte Online-Zahlungen fuer Devis-Lizenzen:
- 5-Devis Trial: kostenlos
- Solo: 79 CHF/Mt
- Team: 249 CHF/Mt
- Business: 599 CHF/Mt
- Enterprise: Custom

Stripe-Webhook validiert Zahlungen, aktualisiert User-Lizenz.
"""
import os
import json
import hmac
import hashlib
import time
from typing import Dict, Optional
from datetime import datetime, timedelta
from pathlib import Path

# Stripe-Library optional (nur falls Payment aktiviert)
try:
    import stripe
    STRIPE_AVAILABLE = True
except ImportError:
    STRIPE_AVAILABLE = False


# ==========================================================
# KONFIGURATION
# ==========================================================

STRIPE_API_KEY = os.environ.get("STRIPE_API_KEY", "")  # sk_live_...
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")  # whsec_...

PREISE = {
    "solo": {
        "name": "DevisPro Solo",
        "price_chf": 79,
        "interval": "month",
        "stripe_price_id": "price_solo_xxx",  # In Stripe erstellen
        "features": ["5 Devis/Mt inklusive", "Sorba-Import", "PDF + QR-Rechnung", "E-Mail-Support"],
    },
    "team": {
        "name": "DevisPro Team",
        "price_chf": 249,
        "interval": "month",
        "stripe_price_id": "price_team_xxx",
        "features": ["25 Devis/Mt inklusive", "3 User", "KI-Agent", "Cloud-Sync", "Priority-Support"],
    },
    "business": {
        "name": "DevisPro Business",
        "price_chf": 599,
        "interval": "month",
        "stripe_price_id": "price_business_xxx",
        "features": ["Unlimited Devis", "5 User", "10 ERP-Anbindungen", "API-Zugang", "Account-Manager"],
    },
}


# ==========================================================
# CHECKOUT-SESSION
# ==========================================================

def create_checkout_session(plan: str, customer_email: str, success_url: str, cancel_url: str) -> Dict:
    """Erstellt eine Stripe-Checkout-Session fuer die Lizenz-Bezahlung.

    Args:
        plan: 'solo', 'team', 'business'
        customer_email: User-Email (fuer Rechnung)
        success_url: URL nach erfolgreicher Zahlung
        cancel_url: URL bei Abbruch

    Returns: Dict mit checkout_url und session_id
    """
    if not STRIPE_AVAILABLE:
        return {"error": "Stripe-Library nicht installiert. pip install stripe"}

    if plan not in PREISE:
        return {"error": f"Unbekannter Plan: {plan}"}

    if not STRIPE_API_KEY:
        return {"error": "STRIPE_API_KEY nicht konfiguriert"}

    try:
        stripe.api_key = STRIPE_API_KEY
        price = PREISE[plan]
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[{
                "price_data": {
                    "currency": "chf",
                    "product_data": {
                        "name": price["name"],
                        "description": f"DevisPro {plan.upper()} - {price['interval']}ly subscription",
                    },
                    "unit_amount": price["price_chf"] * 100,  # in Rappen
                    "recurring": {"interval": price["interval"]},
                },
                "quantity": 1,
            }],
            mode="subscription",
            customer_email=customer_email,
            success_url=success_url + "?session_id={CHECKOUT_SESSION_ID}",
            cancel_url=cancel_url,
            metadata={"plan": plan, "product": "devispro"},
        )
        return {
            "checkout_url": session.url,
            "session_id": session.id,
            "plan": plan,
        }
    except Exception as e:
        return {"error": str(e)}


# ==========================================================
# WEBHOOK
# ==========================================================

def verify_webhook(payload: bytes, signature: str) -> Optional[Dict]:
    """Verifiziert und parsed ein Stripe-Webhook.

    Args:
        payload: Raw Request-Body (bytes)
        signature: Stripe-Signature Header (z.B. 't=...,v1=...')

    Returns: Event-Dict wenn gueltig, None sonst.
    """
    if not STRIPE_WEBHOOK_SECRET:
        return None

    try:
        # Stripe-Standard: HMAC-SHA256 mit Timestamp
        elements = dict(item.split("=", 1) for item in signature.split(","))
        timestamp = elements.get("t")
        sig = elements.get("v1")
        if not timestamp or not sig:
            return None

        # Signed payload: timestamp + "." + payload
        signed_payload = f"{timestamp}.".encode() + payload
        expected = hmac.new(
            STRIPE_WEBHOOK_SECRET.encode(),
            signed_payload,
            hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(expected, sig):
            return None

        # Erfolg - Event parsen
        return json.loads(payload.decode())
    except Exception:
        return None


def handle_webhook_event(event: Dict) -> Dict:
    """Verarbeitet ein verifiziertes Stripe-Event.

    Wichtigste Events:
    - checkout.session.completed: Zahlung erfolgreich
    - customer.subscription.created: Subscription gestartet
    - customer.subscription.updated: Aenderung
    - customer.subscription.deleted: Kuendigung
    - invoice.payment_succeeded: Monatliche Zahlung erfolgreich
    - invoice.payment_failed: Zahlung fehlgeschlagen
    """
    event_type = event.get("type")
    data = event.get("data", {}).get("object", {})

    if event_type == "checkout.session.completed":
        return _handle_checkout_completed(data)
    elif event_type == "customer.subscription.created":
        return _handle_subscription_created(data)
    elif event_type == "customer.subscription.updated":
        return _handle_subscription_updated(data)
    elif event_type == "customer.subscription.deleted":
        return _handle_subscription_cancelled(data)
    elif event_type == "invoice.payment_succeeded":
        return _handle_payment_succeeded(data)
    elif event_type == "invoice.payment_failed":
        return _handle_payment_failed(data)
    else:
        return {"handled": False, "event_type": event_type}


def _handle_checkout_completed(session: Dict) -> Dict:
    """Zahlung erfolgreich: User bekommt Lizenz."""
    customer_email = session.get("customer_email")
    plan = session.get("metadata", {}).get("plan")
    customer_id = session.get("customer")
    subscription_id = session.get("subscription")

    if not all([customer_email, plan]):
        return {"handled": False, "error": "missing fields"}

    # Lizenz aktivieren
    license_data = {
        "email": customer_email,
        "plan": plan,
        "customer_id": customer_id,
        "subscription_id": subscription_id,
        "activated_at": datetime.now().isoformat(),
        "expires_at": (datetime.now() + timedelta(days=30)).isoformat(),
        "status": "active",
    }

    _save_license(customer_email, license_data)

    return {
        "handled": True,
        "action": "license_activated",
        "plan": plan,
        "email": customer_email,
    }


def _handle_subscription_created(subscription: Dict) -> Dict:
    """Subscription erstellt."""
    return _handle_checkout_completed({
        "customer_email": subscription.get("customer_email"),
        "customer": subscription.get("customer"),
        "subscription": subscription.get("id"),
        "metadata": subscription.get("metadata", {}),
    })


def _handle_subscription_updated(subscription: Dict) -> Dict:
    """Subscription geaendert (z.B. Plan-Upgrade)."""
    customer_id = subscription.get("customer")
    new_plan = subscription.get("metadata", {}).get("plan")

    # Update existierende Lizenz
    _update_license_by_customer(customer_id, {"plan": new_plan})
    return {"handled": True, "action": "plan_updated", "new_plan": new_plan}


def _handle_subscription_cancelled(subscription: Dict) -> Dict:
    """Subscription gekuendigt."""
    customer_id = subscription.get("customer")
    _update_license_by_customer(customer_id, {"status": "cancelled", "expires_at": datetime.now().isoformat()})
    return {"handled": True, "action": "subscription_cancelled"}


def _handle_payment_succeeded(invoice: Dict) -> Dict:
    """Monatliche Zahlung erfolgreich — Lizenz verlaengert."""
    customer_id = invoice.get("customer")
    new_expiry = (datetime.now() + timedelta(days=30)).isoformat()
    _update_license_by_customer(customer_id, {"expires_at": new_expiry, "status": "active"})
    return {"handled": True, "action": "license_extended"}


def _handle_payment_failed(invoice: Dict) -> Dict:
    """Zahlung fehlgeschlagen — User bekommt Warnung."""
    customer_id = invoice.get("customer")
    _update_license_by_customer(customer_id, {"status": "payment_failed"})
    return {"handled": True, "action": "payment_failed_notice_sent"}


# ==========================================================
# LICENSE-SPEICHER
# ==========================================================

def _save_license(email: str, license_data: Dict) -> None:
    """Speichert eine Lizenz im lokalen Store."""
    from . import data_store as ds
    try:
        from .compliance import audit_log
    except ImportError:
        def audit_log(*args, **kwargs):
            pass  # Fallback wenn compliance nicht verfuegbar

    USER_DATA = Path(ds.app_support_dir())
    licenses_path = USER_DATA / "licenses.json"
    USER_DATA.mkdir(parents=True, exist_ok=True)

    licenses = {}
    if licenses_path.exists():
        try:
            licenses = json.loads(licenses_path.read_text(encoding="utf-8"))
        except Exception:
            pass

    licenses[email] = license_data
    licenses_path.write_text(json.dumps(licenses, indent=2, ensure_ascii=False), encoding="utf-8")
    try:
        audit_log("license_activated", {"email": email, "plan": license_data.get("plan")})
    except Exception:
        pass


def _update_license_by_customer(customer_id: str, updates: Dict) -> None:
    """Updated eine Lizenz anhand der Stripe-Customer-ID."""
    from . import data_store as ds

    USER_DATA = Path(ds.app_support_dir())
    licenses_path = USER_DATA / "licenses.json"
    if not licenses_path.exists():
        return
    try:
        licenses = json.loads(licenses_path.read_text(encoding="utf-8"))
        for email, lic in licenses.items():
            if lic.get("customer_id") == customer_id:
                lic.update(updates)
                licenses[email] = lic
        licenses_path.write_text(json.dumps(licenses, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass


def get_user_license(email: str) -> Optional[Dict]:
    """Gibt die Lizenz eines Users zurueck."""
    from . import data_store as ds
    USER_DATA = Path(ds.app_support_dir())
    licenses_path = USER_DATA / "licenses.json"
    if not licenses_path.exists():
        return None
    try:
        licenses = json.loads(licenses_path.read_text(encoding="utf-8"))
        return licenses.get(email)
    except Exception:
        return None


# ==========================================================
# DASHBOARD-DATEN
# ==========================================================

def get_pricing_table() -> Dict:
    """Gibt die aktuelle Pricing-Tabelle fuer die Anzeige zurueck."""
    return PREISE


def is_payment_enabled() -> bool:
    """Prueft ob Stripe-Zahlungen aktiviert sind."""
    return STRIPE_AVAILABLE and bool(STRIPE_API_KEY)