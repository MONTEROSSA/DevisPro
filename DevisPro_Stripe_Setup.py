"""Stripe-Setup fuer DevisPro - fuehrt 3 Produkte + Webhook ein.

BENUTZUNG:
  1. Stripe-Account einloggen: https://dashboard.stripe.com
  2. Developers -> API keys -> Restricted key erstellen
     (Berechtigungen: customers:write, subscriptions:write, checkout:write)
  3. STRIPE_API_KEY=sk_test_... (oder sk_live_...) als ENV-Variable setzen
  4. Dieses Script ausfuehren: python3 DevisPro_Stripe_Setup.py
  5. Output: 3 Price-IDs + Webhook-Secret ausgeben
"""
import os
import sys
import json
import stripe
from pathlib import Path


def setup_stripe_products():
    """Erstellt die 3 DevisPro-Produkte in Stripe und gibt die IDs aus."""

    api_key = os.environ.get("STRIPE_API_KEY")
    if not api_key:
        print("FEHLER: STRIPE_API_KEY nicht gesetzt!")
        print("")
        print("So geht's:")
        print("  1. https://dashboard.stripe.com -> Login")
        print("  2. Developers -> API keys -> 'Create restricted key'")
        print("  3. Berechtigungen: customers:write, subscriptions:write, checkout:write")
        print("  4. Key kopieren (z.B. sk_test_51N...)")
        print("  5. Setzen: export STRIPE_API_KEY='sk_test_...'")
        print("  6. Erneut ausfuehren: python3 DevisPro_Stripe_Setup.py")
        return False

    stripe.api_key = api_key

    # Pruefe Key-Typ
    is_live = api_key.startswith("sk_live_")
    mode = "LIVE" if is_live else "TEST"
    print(f"=== DevisPro Stripe-Setup ({mode}-Modus) ===\n")

    # Preise aus billing.py
    PREISE = {
        "solo": {"name": "DevisPro Solo", "price_chf": 79,
                  "description": "Solo plan - 5 Devis pro Monat"},
        "team": {"name": "DevisPro Team", "price_chf": 249,
                  "description": "Team plan - 25 Devis + 3 User + KI-Agent"},
        "business": {"name": "DevisPro Business", "price_chf": 599,
                      "description": "Business plan - Unlimited + 5 User + API"},
    }

    results = {}
    for plan_id, plan in PREISE.items():
        print(f"Erstelle Produkt: {plan['name']} (CHF {plan['price_chf']}/Monat)...")

        try:
            # 1) Produkt erstellen
            product = stripe.Product.create(
                name=plan["name"],
                description=plan["description"],
                metadata={"plan_id": plan_id, "app": "devispro"},
            )

            # 2) Preis erstellen (wiederkehrend, monatlich)
            price = stripe.Price.create(
                product=product.id,
                unit_amount=plan["price_chf"] * 100,  # in Rappen
                currency="chf",
                recurring={"interval": "month"},
                metadata={"plan_id": plan_id},
            )

            results[plan_id] = {
                "product_id": product.id,
                "price_id": price.id,
                "name": plan["name"],
                "price_chf": plan["price_chf"],
            }
            print(f"  OK: Product {product.id}, Price {price.id}")

        except stripe.error.StripeError as e:
            print(f"  FEHLER: {e}")
            return False

    # 3) ENV-Datei schreiben
    env_content = "# DevisPro Stripe-Konfiguration (automatisch generiert)\n"
    env_content += f"STRIPE_API_KEY={api_key}\n"
    for plan_id, data in results.items():
        env_content += f"STRIPE_PRICE_{plan_id.upper()}={data['price_id']}\n"
    env_content += "\n# Webhook-Secret manuell setzen (siehe Setup-Anleitung):\n"
    env_content += "# STRIPE_WEBHOOK_SECRET=whsec_...\n"

    env_path = Path.home() / ".devispro_stripe.env"
    env_path.write_text(env_content, encoding="utf-8")
    print(f"\n=== Konfiguration gespeichert: {env_path} ===\n")

    print("=== Naechste Schritte ===")
    print("1. Webhook erstellen:")
    print("   Dashboard -> Developers -> Webhooks -> 'Add endpoint'")
    print("   URL: https://api.devispro.de/stripe/webhook")
    print("   Events: checkout.session.completed, customer.subscription.*, invoice.payment_*")
    print("2. Webhook-Secret kopieren (whsec_...)")
    print("3. Setzen: export STRIPE_WEBHOOK_SECRET='whsec_...'")
    print(f"4. Zur .env-Datei hinzufuegen: cat >> {env_path}")
    print("5. Test-Modus: sk_test_... verwenden (keine echten Zahlungen)")
    print("6. Live-Schaltung: sk_live_... verwenden + 'Activate' in Dashboard")

    return True


if __name__ == "__main__":
    success = setup_stripe_products()
    sys.exit(0 if success else 1)