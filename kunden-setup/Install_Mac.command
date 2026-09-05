#!/bin/bash
# ============================================================
#  DevisPro - Automatische Installation (macOS)
#  Doppelklick auf diese Datei -> alles laeuft von alleine.
# ============================================================
set -e
APP_DIR="$(dirname "$0")/app"
PORT=5070

echo ""
echo "========================================"
echo "  DevisPro Installation (macOS)"
echo "========================================"
echo ""

# --- 1) Python vorhanden? (macOS hat Python 3 meist bereits) ---
if ! command -v python3 &> /dev/null; then
    echo "[..] Python wird installiert (brew)..."
    if command -v brew &> /dev/null; then
        brew install python
    else
        echo "[FEHLER] Bitte installieren Sie Python 3 von https://python.org (brew nicht gefunden)."
        exit 1
    fi
fi
echo "[OK] Python bereit: $(python3 --version)"

# --- 2) openpyxl nur falls Excel-Upload gewuenscht (optional, nicht noetig zum Start) ---
echo "[OK] DevisPro startet ohne weitere Abhaengigkeiten."

echo ""
echo "[..] DevisPro wird gestartet..."
echo "     Oeffnen Sie danach im Browser:  http://localhost:$PORT"
echo ""

cd "$APP_DIR"
PORT=$PORT exec python3 webui.py
