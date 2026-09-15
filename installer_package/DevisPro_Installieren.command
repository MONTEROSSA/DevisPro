#!/bin/bash
# DevisPro - Installieren & Starten (fuer Kunden-Mac, keine Abhaengigkeiten zu diesem Rechner)
cd "$(dirname "$0")"
APP="./DevisPro.app"

echo "=== DevisPro wird vorbereitet ==="
if [ ! -d "$APP" ]; then
  echo "FEHLER: DevisPro.app nicht im selben Ordner gefunden."
  echo "Bitte dieses Script im selben Ordner wie DevisPro.app ausfuehren."
  read -n 1 -s -r -p "Taste druecken zum Schliessen..."
  exit 1
fi

echo "[1/2] Sicherheits-Kennzeichnung von Apple entfernen (einmalig notwendig, da die App"
echo "       ausserhalb des App Stores signiert ist - ganz normal fuer KMU-Software)..."
xattr -cr "$APP"

echo "[2/2] DevisPro wird gestartet..."
open "$APP"

sleep 2
echo ""
echo "=== Fertig! DevisPro sollte sich jetzt oeffnen. ==="
echo "Tipp: Fuer den naechsten Start reicht ein Doppelklick auf DevisPro.app."
echo ""
read -n 1 -s -r -p "Dieses Fenster kann jetzt geschlossen werden..."
