#!/bin/bash
# DevisPro – Installer/Starter für macOS
# Doppelklick startet die DevisPro-Web-UI lokal (http://localhost:5070).
# Keine Python-Installation nötig – macOS hat Python 3 bereits an Bord.

DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

# Python 3 ermitteln
PY=$(command -v python3 || command -v python || true)
if [ -z "$PY" ]; then
  osascript -e 'display dialog "Python 3 wurde nicht gefunden. Bitte installieren Sie Python 3 von python.org" buttons {"OK"} default button "OK"'
  exit 1
fi

# Port freimachen, falls noch belegt
pkill -f "webui.py" 2>/dev/null
sleep 1

# Server starten (im Hintergrund)
"$PY" webui.py >/dev/null 2>&1 &
sleep 3

# Browser öffnen
open "http://localhost:5070/"

# Hinweis
osascript -e 'display dialog "DevisPro ist gestartet.\n\nÖffne im Browser: http://localhost:5070\n\nZum Beenden: Terminal schliessen oder diesen Dialog ignorieren." buttons {"OK"} default button "OK"' 2>/dev/null &
exit 0
