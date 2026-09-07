#!/bin/bash
# DevisPro Stripe Self-Service Setup
# Fuehre das einmalig aus. Das Skript macht alles automatisch.

set -e
cd ~/devis-auto

echo "=== DevisPro Stripe Setup ==="
echo ""

# Pruefe ob bereits eingeloggt
if ! stripe products list --limit 1 2>&1 | grep -q "object"; then
  echo "Stripe CLI ist nicht eingeloggt. Bitte fuehre zuerst aus:"
  echo ""
  echo "  stripe login"
  echo ""
  echo "Es oeffnet sich ein Browser. Klicke 'Allow access'."
  echo "Dann fuehre dieses Script NOCHMAL aus."
  exit 1
fi

echo "Stripe CLI eingeloggt. Erstelle Produkte..."
echo ""

# Solo
echo "1/3 DevisPro Solo (79 CHF)..."
SOLO_ID=$(stripe products create --name="DevisPro Solo" --description="Solo Plan - 5 Devis pro Monat, PDF + QR-Rechnung, E-Mail-Support" 2>/dev/null | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
SOLO_PRICE_ID=$(stripe prices create --product=$SOLO_ID --unit-amount=7900 --currency=chf --recurring.interval=month 2>/dev/null | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
echo "    Product: $SOLO_ID, Price: $SOLO_PRICE_ID"

# Team
echo "2/3 DevisPro Team (249 CHF)..."
TEAM_ID=$(stripe products create --name="DevisPro Team" --description="Team Plan - 25 Devis + 3 User + KI-Agent + Cloud-Sync + Priority-Support" 2>/dev/null | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
TEAM_PRICE_ID=$(stripe prices create --product=$TEAM_ID --unit-amount=24900 --currency=chf --recurring.interval=month 2>/dev/null | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
echo "    Product: $TEAM_ID, Price: $TEAM_PRICE_ID"

# Business
echo "3/3 DevisPro Business (599 CHF)..."
BUS_ID=$(stripe products create --name="DevisPro Business" --description="Business Plan - Unlimited Devis + 5 User + 10 ERP-Anbindungen + API-Zugang + Account-Manager" 2>/dev/null | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
BUS_PRICE_ID=$(stripe prices create --product=$BUS_ID --unit-amount=59900 --currency=chf --recurring.interval=month 2>/dev/null | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
echo "    Product: $BUS_ID, Price: $BUS_PRICE_ID"

# Speichere in ENV-Datei
cat >> ~/.devispro_stripe.env <<EOF
STRIPE_PRICE_SOLO=$SOLO_PRICE_ID
STRIPE_PRICE_TEAM=$TEAM_PRICE_ID
STRIPE_PRICE_BUSINESS=$BUS_PRICE_ID
EOF

echo ""
echo "=== FERTIG ==="
echo ""
echo "Konfiguration gespeichert: ~/.devispro_stripe.env"
echo ""
echo "Naechste Schritte:"
echo "1. Stripe Dashboard -> Webhooks -> + Add endpoint"
echo "   URL: https://api.devispro.de/stripe/webhook"
echo "2. Webhook-Secret zu ENV-Datei hinzufuegen:"
echo "   echo 'STRIPE_WEBHOOK_SECRET=whsec_...x' >> ~/.devispro_stripe.env"
echo "3. Teste mit:"
echo "   python3 ~/devis-auto/devispro/tests/test_billing_stripe.py"