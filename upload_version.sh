#!/bin/bash
# Upload von version.json auf devispro.ch (Anbieter führt das einmal aus).
# Voraussetzung: SSH-Zugang zum Webhost von devispro.ch ist eingerichtet.
# Ersetze USER@HOST und /pfad/zu/webroot durch die echten Werte deines Hosters.
set -e
SRC="/Users/ferdinandrothlisberger/devis-auto/version.json"
# ---- HIER ANPASSEN (deine Hosting-Daten) ----
HOST_USER="USER"          # z.B. devispro
HOST_NAME="devispro.ch"   # oder IP
REMOTE_DIR="/var/www/devispro.ch"   # Web-Root auf dem Host
# ---------------------------------------------
echo "Lade version.json auf $HOST_USER@$HOST_NAME:$REMOTE_DIR ..."
scp "$SRC" "$HOST_USER@$HOST_NAME:$REMOTE_DIR/version.json"
echo "Fertig. Kunde sieht Update beim naechsten Oeffnen von DevisPro."
