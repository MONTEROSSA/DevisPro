#!/bin/bash
# DevisPro Backup zu VPS - sicher (SSH-Key, kein Passwort)
# Laeuft lokal auf deinem Mac, schiebt automatisch verschluesselte Backups auf den VPS

set -e
VPS="root@187.77.79.26"
KEY="$HOME/devis-auto/_vps_key"
REMOTE_DIR="/var/www/devispro/backups_userdata"
LOCAL_BACKUP_DIR="$HOME/Library/Application Support/DevisPro/backups"
LOG="$HOME/devispro_backup.log"

# Datums-Berechnung
DATE=$(date +%Y%m%d_%H%M%S)
DAY_OF_WEEK=$(date +%u)  # 1=Montag ... 7=Sonntag
DAY_OF_MONTH=$(date +%d)
WEEKLY_FLAG=""
MONTHLY_FLAG=""

if [ "$DAY_OF_WEEK" = "7" ]; then
    WEEKLY_FLAG="yes"
fi
if [ "$DAY_OF_MONTH" = "01" ]; then
    MONTHLY_FLAG="yes"
fi

echo "[$(date)] === DevisPro Backup gestartet ===" | tee -a "$LOG"

# 1) Lokal verschluesseltes Backup erstellen
if [ ! -d "$HOME/Library/Application Support/DevisPro/devis" ]; then
  echo "[$(date)] WARN: Keine Devis-Daten in USER_DATA - ueberspringe" | tee -a "$LOG"
  exit 0
fi

# Backup mit existierender backup.py Logik (Datum in Python als int)
# WICHTIG: cd in das INNERE Package-Verzeichnis damit die M27-Version geladen wird
cd "$HOME/devis-auto/devispro"
python3 -c "
import sys
# Pfad auf INNERE devispro zeigen (das echte Package)
sys.path.insert(0, '.')
from devispro.backup import create
print(f'Geladene Version: {create.__code__.co_filename}')

# Tages-Backup (verschluesselt)
backup_path, manifest = create(label='daily', password='auto-backup-2026')
print(f'  Daily: {backup_path}')

# Woechentliches Backup (Sonntag)
if '$WEEKLY_FLAG' == 'yes':
    backup_path, _ = create(label='weekly', password='auto-backup-2026')
    print(f'  Weekly: {backup_path}')

# Monatliches Backup (am 1.)
if '$MONTHLY_FLAG' == 'yes':
    backup_path, _ = create(label='monthly', password='auto-backup-2026')
    print(f'  Monthly: {backup_path}')
" 2>&1 | tee -a "$LOG"

# 2) Auf VPS hochladen
echo "[$(date)] === Uploads zu VPS ===" | tee -a "$LOG"
LATEST=$(ls -t "$LOCAL_BACKUP_DIR"/devispro_backup_*.dpbk 2>/dev/null | head -1)
if [ -z "$LATEST" ]; then
  echo "[$(date)] WARN: Keine .dpbk-Backups gefunden" | tee -a "$LOG"
  exit 0
fi

FILENAME=$(basename "$LATEST")
scp -i "$KEY" -o StrictHostKeyChecking=no "$LATEST" "$VPS:$REMOTE_DIR/${FILENAME}.${DATE}"
echo "[$(date)] Hochgeladen: ${FILENAME}.${DATE}" | tee -a "$LOG"

# 3) Alte Backups auf VPS aufraeumen (max 30 behalten)
ssh -i "$KEY" -o StrictHostKeyChecking=no "$VPS" "
  cd $REMOTE_DIR
  ls -t *.dpbk.* 2>/dev/null | tail -n +31 | xargs -r rm -f
  echo '  Backups auf VPS:'
  ls -lh *.dpbk.* 2>/dev/null | tail -10
  echo '  Anzahl:' \$(ls *.dpbk.* 2>/dev/null | wc -l)
" 2>&1 | tee -a "$LOG"

# 4) Lokale Backups aufraeumen (max 7 behalten)
ls -t "$LOCAL_BACKUP_DIR"/devispro_backup_*.dpbk 2>/dev/null | tail -n +8 | while read old; do
  rm -f "$old" && echo "  [local] geloescht: $old" | tee -a "$LOG"
done

echo "[$(date)] === Backup fertig ===" | tee -a "$LOG"