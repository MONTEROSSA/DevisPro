"""Tests fuer M28 Stripe-Integration."""
import sys
import os
import json
import hmac
import hashlib
import tempfile
from pathlib import Path

# Test-Mode aktivieren BEVOR wir billing importieren
os.environ["STRIPE_API_KEY"] = ""  # nicht echt
os.environ["STRIPE_WEBHOOK_SECRET"] = "whsec_test_secret"

sys.path.insert(0, '/Users/ferdinandrothlisberger/devis-auto/devispro')

# Patch USER_DATA
import devispro.data_store as ds
TEST_DIR = tempfile.mkdtemp(prefix="devispro_billing_test_")
ds.app_support_dir = lambda: TEST_DIR

from devispro.billing import (
    create_checkout_session, verify_webhook, handle_webhook_event,
    get_pricing_table, is_payment_enabled, get_user_license, PREISE,
)


def test_pricing_table_complete():
    """Pricing-Tabelle enthaelt alle 3 Plaene."""
    table = get_pricing_table()
    assert "solo" in table
    assert "team" in table
    assert "business" in table
    # Preise korrekt nach Empfehlung (Modell C)
    assert table["solo"]["price_chf"] == 79
    assert table["team"]["price_chf"] == 249
    assert table["business"]["price_chf"] == 599
    print(f"OK: Pricing-Tabelle mit {len(table)} Plaenen (Solo 79, Team 249, Business 599 CHF)")


def test_checkout_session_without_api_key():
    """Ohne Stripe-Key wird Fehler zurueckgegeben."""
    os.environ.pop("STRIPE_API_KEY", None)
    result = create_checkout_session("solo", "test@example.com", "https://ok", "https://cancel")
    assert "error" in result
    print(f"OK: Ohne API-Key wird Fehler zurueckgegeben: {result.get('error', '')[:50]}")


def test_checkout_session_unknown_plan():
    """Unbekannter Plan wird abgelehnt."""
    os.environ["STRIPE_API_KEY"] = "sk_test_xxx"
    # Force STRIPE_AVAILABLE=True durch monkeypatching
    import devispro.billing as billing
    original_available = billing.STRIPE_AVAILABLE
    billing.STRIPE_AVAILABLE = True
    try:
        result = create_checkout_session("unknown", "test@example.com", "https://ok", "https://cancel")
        assert "error" in result
        assert "Unbekannter Plan" in result.get("error", "")
    finally:
        billing.STRIPE_AVAILABLE = original_available
    print("OK: Unbekannter Plan wird abgelehnt")


def test_webhook_signature_verification_valid():
    """Webhook mit korrekter Signatur wird akzeptiert."""
    secret = "whsec_test_secret"
    os.environ["STRIPE_WEBHOOK_SECRET"] = secret
    payload = b'{"type":"checkout.session.completed","data":{"object":{}}}'
    timestamp = str(int(1234567890))
    signed_payload = f"{timestamp}.".encode() + payload
    signature = hmac.new(secret.encode(), signed_payload, hashlib.sha256).hexdigest()
    sig_header = f"t={timestamp},v1={signature}"

    result = verify_webhook(payload, sig_header)
    assert result is not None
    assert result["type"] == "checkout.session.completed"
    print("OK: Webhook mit gueltiger Signatur wird verifiziert")


def test_webhook_signature_verification_invalid():
    """Webhook mit falscher Signatur wird abgelehnt."""
    secret = "whsec_test_secret"
    os.environ["STRIPE_WEBHOOK_SECRET"] = secret
    payload = b'{"type":"test"}'
    # Falscher HMAC
    sig_header = "t=1234567890,v1=0000000000000000000000000000000000000000000000000000000000000000"

    result = verify_webhook(payload, sig_header)
    assert result is None
    print("OK: Webhook mit falscher Signatur wird abgelehnt")


def test_handle_checkout_completed():
    """Checkout-Completed-Event aktiviert eine Lizenz."""
    event = {
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "customer_email": "kunde@example.com",
                "customer": "cus_ABC123",
                "subscription": "sub_XYZ789",
                "metadata": {"plan": "team"},
            }
        }
    }
    result = handle_webhook_event(event)
    assert result["handled"] is True
    assert result["action"] == "license_activated"
    assert result["plan"] == "team"
    assert result["email"] == "kunde@example.com"

    # Pruefe ob Lizenz gespeichert wurde
    lic = get_user_license("kunde@example.com")
    assert lic is not None
    assert lic["plan"] == "team"
    assert lic["status"] == "active"
    print(f"OK: License-Activation: {result['email']} -> {result['plan']}")


def test_handle_payment_failed():
    """Payment-Failed markiert Lizenz als fehlerhaft."""
    # Erst aktivieren
    handle_webhook_event({
        "type": "checkout.session.completed",
        "data": {"object": {"customer_email": "fail@example.com", "customer": "cus_FAIL", "metadata": {"plan": "solo"}}}
    })
    # Dann fehlschlagen
    result = handle_webhook_event({
        "type": "invoice.payment_failed",
        "data": {"object": {"customer": "cus_FAIL"}}
    })
    assert result["handled"] is True
    assert result["action"] == "payment_failed_notice_sent"
    lic = get_user_license("fail@example.com")
    assert lic["status"] == "payment_failed"
    print("OK: Payment-Failure-Handling")


def test_handle_subscription_cancelled():
    """Subscription-Cancelled deaktiviert Lizenz."""
    handle_webhook_event({
        "type": "checkout.session.completed",
        "data": {"object": {"customer_email": "cancel@example.com", "customer": "cus_CANCEL", "metadata": {"plan": "business"}}}
    })
    result = handle_webhook_event({
        "type": "customer.subscription.deleted",
        "data": {"object": {"customer": "cus_CANCEL"}}
    })
    assert result["handled"] is True
    lic = get_user_license("cancel@example.com")
    assert lic["status"] == "cancelled"
    print("OK: Subscription-Cancel-Handling")


def test_handle_payment_succeeded_extends_license():
    """Erfolgreiche monatliche Zahlung verlaengert die Lizenz."""
    # Aktivieren
    handle_webhook_event({
        "type": "checkout.session.completed",
        "data": {"object": {"customer_email": "renew@example.com", "customer": "cus_RENEW", "metadata": {"plan": "team"}}}
    })
    old_lic = get_user_license("renew@example.com")

    # Kurz warten
    import time
    time.sleep(0.1)

    # Monatliche Zahlung
    result = handle_webhook_event({
        "type": "invoice.payment_succeeded",
        "data": {"object": {"customer": "cus_RENEW"}}
    })
    assert result["action"] == "license_extended"
    new_lic = get_user_license("renew@example.com")
    # Neues expiry sollte spaeter sein
    assert new_lic["expires_at"] > old_lic["expires_at"]
    print(f"OK: License-Extension von {old_lic['expires_at']} bis {new_lic['expires_at']}")


def test_is_payment_enabled_without_keys():
    """Ohne Stripe-Keys ist Payment deaktiviert."""
    os.environ.pop("STRIPE_API_KEY", None)
    assert is_payment_enabled() is False
    print("OK: Payment deaktiviert ohne API-Key")


if __name__ == "__main__":
    import shutil
    try:
        print("=" * 60)
        print("M28 Stripe-Integration Tests")
        print("=" * 60)
        test_pricing_table_complete()
        test_checkout_session_without_api_key()
        test_checkout_session_unknown_plan()
        test_webhook_signature_verification_valid()
        test_webhook_signature_verification_invalid()
        test_handle_checkout_completed()
        test_handle_payment_failed()
        test_handle_subscription_cancelled()
        test_handle_payment_succeeded_extends_license()
        test_is_payment_enabled_without_keys()
        print("=" * 60)
        print("ALLE TESTS BESTANDEN - Stripe-Integration einsatzbereit")
        print("=" * 60)
    finally:
        if Path(TEST_DIR).exists():
            shutil.rmtree(TEST_DIR, ignore_errors=True)