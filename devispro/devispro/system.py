"""System-Modul: Backup, Restore, Audit-Log (Zuverlaessigkeit).

- Auto-Backup der Stammdaten vor jeder Aenderung (rotierend, 10 Versionen)
- Audit-Log aller wichtigen Aktionen (wer/wann/was) -> Nachvollziehbarkeit
- Gesundheitscheck (Plausibilitaet der Daten)
"""
import os
import json
import shutil
import datetime as dt

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(HERE, "data")
BACKUP_DIR = os.path.join(DATA, "backups")
LOG_PFAD = os.path.join(DATA, "audit.log")
MAX_BACKUPS = 10

# Dateien, die NIEMALS in ein Backup gehoeren (Geheimnisse/Passwoerter).
# smtp.json enthaelt das SMTP-Passwort und darf nicht in Backups wandern.
BACKUP_EXCLUDE = {"smtp.json"}


def _log(msg: str):
    ts = dt.datetime.now().isoformat(timespec="seconds")
    try:
        with open(LOG_PFAD, "a", encoding="utf-8") as f:
            f.write(f"{ts}  {msg}\n")
    except Exception:
        pass


def audit(event: str, detail=""):
    """Schreibt eine Audit-Zeile."""
    _log(f"[{event}] {detail}")


def backup(name="auto"):
    """Erstellt ein rotierendes Backup der wichtigsten Dateien.

    Dateien in BACKUP_EXCLUDE (z.B. smtp.json mit dem SMTP-Passwort) werden
    bewusst NICHT gesichert, damit keine Geheimnisse in Backups wandern.
    """
    os.makedirs(BACKUP_DIR, exist_ok=True)
    ts = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = os.path.join(BACKUP_DIR, f"{name}_{ts}")
    os.makedirs(dest, exist_ok=True)
    for fn in ["profil.json", "meine_preise.csv", "kunden.json", "lizenz.json"]:
        if fn in BACKUP_EXCLUDE:
            continue  # Geheimnis -> nie sichern
        src = os.path.join(DATA, fn)
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(dest, fn))
    # Rotation
    subs = sorted([d for d in os.listdir(BACKUP_DIR) if d.startswith(name + "_")])
    while len(subs) > MAX_BACKUPS:
        old = subs.pop(0)
        shutil.rmtree(os.path.join(BACKUP_DIR, old), ignore_errors=True)
    _log(f"[BACKUP] {name} -> {dest} (ausgeschlossen: {sorted(BACKUP_EXCLUDE)})")
    return dest


def gesundheitscheck():
    """Prueft Plausibilitaet der Daten; gibt (ok, meldungen) zurueck."""
    msgs = []
    ok = True
    profil = None
    try:
        with open(os.path.join(DATA, "profil.json"), encoding="utf-8") as f:
            profil = json.load(f)
    except Exception:
        msgs.append("Profil nicht lesbar"); ok = False
    if profil:
        for k in ["betrieb", "gewerk", "mwst_pct"]:
            if not profil.get(k):
                msgs.append(f"Profil-Feld '{k}' fehlt"); ok = False
    preise = os.path.join(DATA, "meine_preise.csv")
    if not os.path.exists(preise) or os.path.getsize(preise) < 10:
        msgs.append("Richtpreisliste leer"); ok = False
    return ok, msgs


def letzte_backups(n=5):
    if not os.path.isdir(BACKUP_DIR):
        return []
    return sorted(os.listdir(BACKUP_DIR))[-n:]
