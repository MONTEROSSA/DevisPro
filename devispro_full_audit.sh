#!/bin/bash
# DevisPro Komplett-Pruefung — KEIN LLM, KEIN Provider
# Prueft: Landing-Page, App-Signatur, M1-M4, Cronjobs, alles automatisch

DEVAUTO="/Users/ferdinandrothlisberger/devis-auto"
DESK="/Users/ferdinandrothlisberger/Desktop"
BUNDLE="$DESK/DevisPro.app"
LOG="/tmp/devispro_audit_$(date +%Y%m%d_%H%M%S).log"

echo "========================================" | tee -a "$LOG"
echo "DEVISPRO KOMPLETT-PRUEFUNG" | tee -a "$LOG"
echo "Gestartet: $(date)" | tee -a "$LOG"
echo "========================================" | tee -a "$LOG"

PASSED=0
FAILED=0
WARNINGS=0

check() {
    local name="$1"
    local cmd="$2"
    local result=$(eval "$cmd" 2>&1)
    if [ $? -eq 0 ] && [ -n "$result" ]; then
        echo "  ✓ $name" | tee -a "$LOG"
        PASSED=$((PASSED + 1))
    else
        echo "  ✗ $name — $result" | tee -a "$LOG"
        FAILED=$((FAILED + 1))
    fi
}

warn() {
    local name="$1"
    local detail="$2"
    echo "  ⚠ WARN: $name — $detail" | tee -a "$LOG"
    WARNINGS=$((WARNINGS + 1))
}

# 1. App-Signatur
echo "" | tee -a "$LOG"
echo "[1/8] App-Signatur & Notarisierung" | tee -a "$LOG"
check "spctl: Notarized Developer ID" "spctl --assess --type execute -vv '$BUNDLE' 2>&1 | grep -q 'Notarized Developer ID'"
check "codesign: valid" "codesign --verify --deep --strict '$BUNDLE'"
check "codesign: Authority erkannt" "codesign -dvv '$BUNDLE' 2>&1 | grep -q 'Developer ID Application: Ferdinand'"
check "Notary-Ticket gestempelt" "codesign -dvv '$BUNDLE' 2>&1 | grep -q 'Notarization Ticket=stapled'"

# 2. App-Prozess
echo "" | tee -a "$LOG"
echo "[2/8] App-Prozess" | tee -a "$LOG"
check "App laeuft" "pgrep -f 'DevisPro.app/Contents/MacOS/python-runtime' | head -1"
APP_PID=$(pgrep -f "DevisPro.app/Contents/MacOS/python-runtime" | head -1)
if [ -n "$APP_PID" ]; then
    check "App-Speicher < 500MB" "[ \$(ps -o rss= -p $APP_PID) -lt 512000 ]"
    check "App-CPU stabil" "ps -p $APP_PID -o %cpu= | head -1 | awk '{exit (\$1 < 50)?0:1}'"
fi

# 3. Module im Bundle
echo "" | tee -a "$LOG"
echo "[3/8] Module im Bundle" | tee -a "$LOG"
MODULE_COUNT=$(ls "$BUNDLE/Contents/Resources/devispro/"*.py 2>/dev/null | wc -l | tr -d ' ')
echo "  Module im Bundle: $MODULE_COUNT" | tee -a "$LOG"
[ "$MODULE_COUNT" -ge 70 ] && PASSED=$((PASSED + 1)) || FAILED=$((FAILED + 1))

# Pruefe ob kritische Module da sind
for mod in agent marketplace cloud_sync erp_ecosystem verbaende_kataloge app_gui stammdaten data_store; do
    if [ -f "$BUNDLE/Contents/Resources/devispro/${mod}.py" ]; then
        echo "  ✓ $mod.py vorhanden" | tee -a "$LOG"
        PASSED=$((PASSED + 1))
    else
        echo "  ✗ $mod.py FEHLT" | tee -a "$LOG"
        FAILED=$((FAILED + 1))
    fi
done

# 4. M1-M4 Smoke-Test
echo "" | tee -a "$LOG"
echo "[4/8] M1-M4 Moats (headless)" | tee -a "$LOG"
PYBIN="$BUNDLE/Contents/MacOS/python-runtime/bin/python3.11"
if [ -f "$PYBIN" ] && [ -f /tmp/moat_FINAL.py ]; then
    rm -f "$BUNDLE/Contents/Resources/devispro/__pycache__"/data_store.cpython-311.pyc
    rm -f "$BUNDLE/Contents/Resources/devispro/__pycache__"/stammdaten.cpython-311.pyc
    RESULT=$("$PYBIN" /tmp/moat_FINAL.py 2>&1)
    if echo "$RESULT" | grep -q "FUNKTIONSFÄHIG"; then
        echo "  ✓ M1-M4 ENDE-ZU-ENDE" | tee -a "$LOG"
        PASSED=$((PASSED + 1))
    else
        echo "  ✗ M1-M4 FEHLGESCHLAGEN" | tee -a "$LOG"
        echo "$RESULT" | tail -10 | tee -a "$LOG"
        FAILED=$((FAILED + 1))
    fi
else
    echo "  ⚠ Pybin oder /tmp/moat_FINAL.py fehlt" | tee -a "$LOG"
    WARNINGS=$((WARNINGS + 1))
fi

# 5. KI-Agent (manuell headless)
echo "" | tee -a "$LOG"
echo "[5/8] KI-Agent" | tee -a "$LOG"
if [ -f "$BUNDLE/Contents/Resources/devispro/agent.py" ]; then
    AGENT_TEST=$("$PYBIN" -c "
import sys, types
preise_stub = types.ModuleType('devispro.preise')
preise_stub.PREISE = {'lizenz_jahr': 990, 'einmalig': 2400, 'support_jahr': 990, 'einmal_chf': 2400}
sys.modules['devispro.preise'] = preise_stub
pricing_stub = types.ModuleType('devispro.pricing')
pricing_stub.preis = lambda k: preise_stub.PREISE
sys.modules['devispro.pricing'] = pricing_stub
import importlib.util
spec = importlib.util.spec_from_file_location('devispro.data_store', '$BUNDLE/Contents/Resources/devispro/data_store.py')
m = importlib.util.module_from_spec(spec); sys.modules['devispro.data_store'] = m; spec.loader.exec_module(m)
spec = importlib.util.spec_from_file_location('devispro.crypto_rsa', '$BUNDLE/Contents/Resources/devispro/crypto_rsa.py')
m = importlib.util.module_from_spec(spec); sys.modules['devispro.crypto_rsa'] = m; spec.loader.exec_module(m)
spec = importlib.util.spec_from_file_location('devispro', '$BUNDLE/Contents/Resources/devispro/__init__.py', submodule_search_locations=['$BUNDLE/Contents/Resources/devispro'])
pkg = importlib.util.module_from_spec(spec); sys.modules['devispro'] = pkg; spec.loader.exec_module(pkg)
from devispro.agent import FAQ
print(f'OK: {len(FAQ)} Themen')
" 2>&1)
    if echo "$AGENT_TEST" | grep -q "OK:"; then
        THEMES=$(echo "$AGENT_TEST" | grep "OK:" | awk '{print $2}')
        echo "  ✓ Agent geladen: $THEMES FAQ-Themen" | tee -a "$LOG"
        PASSED=$((PASSED + 1))
    else
        echo "  ✗ Agent-Fehler: $AGENT_TEST" | tee -a "$LOG"
        FAILED=$((FAILED + 1))
    fi
fi

# 6. Cronjobs
echo "" | tee -a "$LOG"
echo "[6/8] Cronjobs" | tee -a "$LOG"
CRON_COUNT=$(hermes cron list 2>&1 | grep -E "^\s+[a-f0-9]{12}" | wc -l | tr -d ' ')
echo "  Aktive Cronjobs: $CRON_COUNT" | tee -a "$LOG"
[ "$CRON_COUNT" -ge 15 ] && PASSED=$((PASSED + 1)) || warn "Cronjobs" "Nur $CRON_COUNT aktiv"
# 429-fail check
HTTP429_FAILS=$(hermes cron list 2>&1 | grep -c "HTTP 429")
[ "$HTTP429_FAILS" -eq 0 ] && echo "  ✓ Keine 429-Fehler in Cronjobs" | tee -a "$LOG" || warn "HTTP 429 Fehler" "$HTTP429_FAILS Cronjobs fehlerhaft"

# 7. Landing-Page
echo "" | tee -a "$LOG"
echo "[7/8] Landing-Page (dev / prod)" | tee -a "$LOG"
LP_LOCAL="$DEVAUTO/devispro_neue_startseite.html"
if [ -f "$LP_LOCAL" ]; then
    SIZE=$(wc -c < "$LP_LOCAL")
    echo "  ✓ Landing-Page lokal: $SIZE bytes" | tee -a "$LOG"
    PASSED=$((PASSED + 1))
    # Pruefe auf Standard-Elemente
    for element in '<button' 'href=' '<form' '<input' '<a '; do
        if grep -q "$element" "$LP_LOCAL"; then
            echo "  ✓ Enthält $element" | tee -a "$LOG"
            PASSED=$((PASSED + 1))
        else
            echo "  ✗ FEHLT: $element" | tee -a "$LOG"
            FAILED=$((FAILED + 1))
        fi
    done
else
    warn "Landing-Page" "$LP_LOCAL nicht gefunden"
fi
# Pruefe ob online
PROD_URL="https://www.devispro.de"
if curl -s --max-time 5 -o /dev/null -w "%{http_code}" "$PROD_URL" 2>/dev/null | grep -q "200"; then
    echo "  ✓ devispro.de online (HTTP 200)" | tee -a "$LOG"
    PASSED=$((PASSED + 1))
    # Lade und teste Buttons
    HTML=$(curl -s --max-time 10 "$PROD_URL" 2>/dev/null)
    echo "$HTML" > /tmp/landing_prod.html
    if echo "$HTML" | grep -q "DevisPro"; then
        echo "  ✓ Enthält 'DevisPro' Text" | tee -a "$LOG"
        PASSED=$((PASSED + 1))
    fi
    if echo "$HTML" | grep -qE "(Download|download|App|.zip|.dmg)"; then
        echo "  ✓ Enthält Download-Link" | tee -a "$LOG"
        PASSED=$((PASSED + 1))
    fi
    if echo "$HTML" | grep -qE "(Preis|price|chf|CHF|kosten)"; then
        echo "  ✓ Enthält Preis-Info" | tee -a "$LOG"
        PASSED=$((PASSED + 1))
    fi
else
    warn "devipro.de" "konnte nicht erreicht werden"
fi

# 8. Distribution-Files
echo "" | tee -a "$LOG"
echo "[8/8] Distribution-Files" | tee -a "$LOG"
for f in "DevisPro_Mac_notarized.zip" "DevisPro_Mac_signed.zip" "DevisPro_Installer_Mac.command" "ANLEITUNG_KMU.md"; do
    if [ -f "$DEVAUTO/$f" ]; then
        SIZE=$(ls -la "$DEVAUTO/$f" | awk '{print $5}')
        echo "  ✓ $f ($SIZE bytes)" | tee -a "$LOG"
        PASSED=$((PASSED + 1))
    else
        warn "$f" "Datei fehlt"
    fi
done

# Zusammenfassung
echo "" | tee -a "$LOG"
echo "========================================" | tee -a "$LOG"
echo "ZUSAMMENFASSUNG" | tee -a "$LOG"
echo "========================================" | tee -a "$LOG"
echo "  ✓ Bestanden: $PASSED" | tee -a "$LOG"
echo "  ✗ Fehlgeschlagen: $FAILED" | tee -a "$LOG"
echo "  ⚠ Warnungen: $WARNINGS" | tee -a "$LOG"
echo "  Log: $LOG" | tee -a "$LOG"
echo "  Beendet: $(date)" | tee -a "$LOG"
echo "========================================" | tee -a "$LOG"
