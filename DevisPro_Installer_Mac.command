#!/bin/bash
# ============================================================
#  DevisPro - Installer & Starter (macOS)
#  Ein Produkt der Monterossa AG
#  Doppelklick -> prueft Python, startet DevisPro, oeffnet Browser.
# ============================================================
set -e

# Ort dieser Datei = Installationsordner
DIR="$(cd "$(dirname "$0")" && pwd)"
# App-Ordner: entweder beigelegt (app/) oder devis-auto-Wurzel
if   [ -f "$DIR/app/webui.py" ]; then APP="$DIR/app"
elif [ -f "$DIR/webui.py" ];      then APP="$DIR"
else
  echo "FEHLER: webui.py nicht gefunden (weder app/ noch Wurzel)."
  exit 1
fi
PORT=5070

echo ""
echo "========================================"
echo "  DevisPro Installer (macOS)"
echo "========================================"
echo ""

# --- 1) Python 3 vorhanden? ---
if ! command -v python3 &> /dev/null; then
  echo "[..] Python 3 wird installiert (brew)..."
  if command -v brew &> /dev/null; then
    brew install python
  else
    echo "[FEHLER] Bitte installieren Sie Python 3 von https://python.org"
    echo "          (brew ist nicht verfuegbar)."
    exit 1
  fi
fi
echo "[OK] Python: $(python3 --version 2>&1)"

# --- 2) openpyxl optional (nur fuer Excel-Upload) ---
python3 -c "import openpyxl" 2>/dev/null && echo "[OK] openpyxl vorhanden" \
  || echo "[Hinweis] openpyxl fehlt - Excel-Upload deaktiviert (sonst voll funktionsfaehig)."

# --- 3) Server starten (falls noch nicht laeuft) ---
if lsof -ti :$PORT >/dev/null 2>&1; then
  echo "[OK] DevisPro laeuft bereits auf Port $PORT."
else
  echo "[..] DevisPro wird gestartet..."
  cd "$APP"
  nohup python3 webui.py >/tmp/devispro.log 2>&1 &
  sleep 3
  if lsof -ti :$PORT >/dev/null 2>&1; then
    echo "[OK] DevisPro gestartet."
  else
    echo "[FEHLER] Start fehlgeschlagen - siehe /tmp/devispro.log"
    cat /tmp/devispro.log
    exit 1
  fi
fi

# --- 4) Browser oeffnen ---
echo ""
echo "    Oeffne http://localhost:$PORT"
echo ""
open "http://localhost:$PORT"
