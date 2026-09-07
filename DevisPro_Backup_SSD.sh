#!/bin/bash
# DevisPro Backup auf Samsung SSD
# - Verschlüsselt (.dpbk, AES-256-CTR + HMAC-SHA256)
# - Tägliche + Wöchentliche + Monatliche Backups
# - Auto-Rotation (max 30 behalten)
# - Kein Netzwerk, lokal auf SSD = schnell + sicher

set -e
SSD="/Volumes/Extern Samsung SSD 990 Pro 2TB Media"
BACKUP_DIR="$SSD/DevisPro_Backups"
LOCAL_USER_DATA="$HOME/Library/Application Support/DevisPro"
LOG="$HOME/devispro_ssd_backup.log"

echo "[$(date)] === DevisPro SSD-Backup gestartet ===" | tee -a "$LOG"

# Prüfen ob SSD gemountet ist
if [ ! -d "$SSD" ]; then
  echo "[$(date)] FEHLER: Samsung SSD nicht gemountet unter $SSD" | tee -a "$LOG"
  exit 1
fi

# Backup-Ordner auf SSD erstellen
mkdir -p "$BACKUP_DIR/daily" "$BACKUP_DIR/weekly" "$BACKUP_DIR/monthly"

# Prüfen ob Devis-Daten existieren
if [ ! -d "$LOCAL_USER_DATA/devis" ]; then
  echo "[$(date)] WARN: Keine Devis-Daten in $LOCAL_USER_DATA" | tee -a "$LOG"
  exit 0
fi

cd "$HOME/devis-auto/devispro"
DATE=$(date +%Y%m%d_%H%M%S)
DAY_OF_WEEK=$(date +%u)
DAY_OF_MONTH=$(date +%d)
WEEKLY_FLAG=""
MONTHLY_FLAG=""

if [ "$DAY_OF_WEEK" = "7" ]; then WEEKLY_FLAG="yes"; fi
if [ "$DAY_OF_MONTH" = "01" ]; then MONTHLY_FLAG="yes"; fi

# Backup erstellen (M27-AES-256 verschlüsselt)
python3 -c "
import sys
sys.path.insert(0, '.')
from devispro.backup import create

# Tages-Backup
backup_path, _ = create(label='daily', password='auto-backup-2026')
print(f'  Daily: {backup_path}')

# Wöchentliches Backup (Sonntag)
if '$WEEKLY_FLAG' == 'yes':
    backup_path, _ = create(label='weekly', password='auto-backup-2026')
    print(f'  Weekly: {backup_path}')

# Monatliches Backup (am 1.)
if '$MONTHLY_FLAG' == 'yes':
    backup_path, _ = create(label='monthly', password='auto-backup-2026')
    print(f'  Monthly: {backup_path}')
" 2>&1 | tee -a "$LOG"

# Auf Samsung SSD kopieren
echo "[$(date)] === Kopiere auf Samsung SSD ===" | tee -a "$LOG"
LATEST=$(ls -t "$LOCAL_USER_DATA/backups"/devispro_backup_*.dpbk 2>/dev/null | head -1)
if [ -z "$LATEST" ]; then
  echo "[$(date)] FEHLER: Keine .dpbk-Backups gefunden" | tee -a "$LOG"
  exit 1
fi

FILENAME=$(basename "$LATEST")
cp -v "$LATEST" "$BACKUP_DIR/daily/$FILENAME.$DATE" 2>&1 | tee -a "$LOG"

# Rotation (max 30 pro Kategorie)
for CATEGORY in daily weekly monthly; do
  ls -t "$BACKUP_DIR/$CATEGORY"/devispro_backup_*.dpbk.* 2>/dev/null | tail -n +31 | while read old; do
    rm -f "$old" && echo "  [rotiert] $old" | tee -a "$LOG"
  done
done

echo "[$(date)] === SSD-Backup fertig ===" | tee -a "$LOG"
echo "  Verfuegbare Backups auf SSD:"
du -sh "$BACKUP_DIR"/* 2>/dev/null | tee -a "$LOG"