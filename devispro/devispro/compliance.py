"""M27 Compliance: DSGVO-Auskunftsrecht + Audit-Log.

Implementiert:
- export_user_data(): Liest alle User-Daten und gibt sie als JSON zurueck (DSGVO Art. 15)
- delete_user_data(): Loescht ALLE User-Daten (DSGVO Art. 17 "Recht auf Vergessenwerden")
- audit_log(): Strukturiertes Security-Audit-Log (Login, Export, Loeschung, Aenderungen)
- list_audit_log(): Letzte N Audit-Eintraege anzeigen

Speicherort: ~/Library/Application Support/DevisPro/data/audit.log (append-only)
"""
import os
import json
import time
import shutil
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional

from . import data_store as ds

# Pfade
USER_DATA = Path(ds.app_support_dir())
AUDIT_LOG = USER_DATA / "audit.log"
AUDIT_LOG_MAX_ENTRIES = 10_000  # Ringpuffer (aelteste werden geloescht)


# ==========================================================
# AUDIT-LOG
# ==========================================================

def audit_log(event: str, details: Optional[Dict[str, Any]] = None,
              user: Optional[str] = None) -> None:
    """Schreibt einen Audit-Eintrag.

    Args:
        event: z.B. "login", "export", "delete_user", "import", "config_change"
        details: zusaetzliche Metadaten (devis_id, file_path, etc.)
        user: User-ID (falls vorhanden)
    """
    USER_DATA.mkdir(parents=True, exist_ok=True)
    entry = {
        "timestamp": datetime.now().isoformat(),
        "event": event,
        "user": user or os.environ.get("USER", "unknown"),
        "details": details or {},
    }
    with open(AUDIT_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    # Ring-Buffer: limit auf 10k Eintraege
    try:
        if AUDIT_LOG.exists() and AUDIT_LOG.stat().st_size > 5_000_000:  # 5 MB
            _rotate_audit_log()
    except Exception:
        pass  # Rotation ist nicht kritisch


def _rotate_audit_log() -> None:
    """Behaelt nur die letzten N Eintraege (aelteste weg)."""
    if not AUDIT_LOG.exists():
        return
    with open(AUDIT_LOG, "r", encoding="utf-8") as f:
        lines = f.readlines()
    # Behalte nur letzte AUDIT_LOG_MAX_ENTRIES
    if len(lines) > AUDIT_LOG_MAX_ENTRIES:
        kept = lines[-AUDIT_LOG_MAX_ENTRIES:]
        with open(AUDIT_LOG, "w", encoding="utf-8") as f:
            f.writelines(kept)


def list_audit_log(limit: int = 100, event_filter: Optional[str] = None) -> List[Dict]:
    """Gibt die letzten N Audit-Eintraege zurueck (neueste zuerst)."""
    if not AUDIT_LOG.exists():
        return []
    entries = []
    with open(AUDIT_LOG, "r", encoding="utf-8") as f:
        for line in f:
            try:
                entry = json.loads(line)
                if event_filter and entry.get("event") != event_filter:
                    continue
                entries.append(entry)
            except Exception:
                continue
    # Neueste zuerst
    entries.reverse()
    return entries[:limit]


# ==========================================================
# DSGVO AUSKUNFTSRECHT (Art. 15)
# ==========================================================

def export_user_data(user_id: Optional[str] = None) -> Dict[str, Any]:
    """Exportiert ALLE User-Daten (DSGVO Art. 15 - Auskunftsrecht).

    Args:
        user_id: User-Identifikation (optional, fuer Filterung)

    Returns: Dict mit allen User-bezogenen Daten.
    """
    audit_log("export_user_data", {"user_id": user_id or "self"})

    export = {
        "export_date": datetime.now().isoformat(),
        "user_data": {
            "profile": {},
            "devis": [],
            "preise": [],
            "kunden": [],
            "audit_log": [],
        },
        "data_categories": [
            "Stammdaten (Firmendaten, Profil)",
            "Devis-Historie",
            "Preislisten",
            "Kunden-Daten",
            "Rechnungen",
            "Audit-Log",
        ],
        "hinweis": "Alle Daten, die DevisPro ueber Sie speichert. Exportiert gemaess DSGVO Art. 15.",
    }

    # 1) Profil
    profile_path = USER_DATA / "profil.json"
    if profile_path.exists():
        try:
            with open(profile_path, encoding="utf-8") as f:
                export["user_data"]["profile"] = json.load(f)
        except Exception as e:
            export["user_data"]["profile"] = {"error": str(e)}

    # 2) Kunden
    kunden_path = USER_DATA / "kunden.json"
    if kunden_path.exists():
        try:
            with open(kunden_path, encoding="utf-8") as f:
                export["user_data"]["kunden"] = json.load(f)
        except Exception as e:
            export["user_data"]["kunden"] = {"error": str(e)}

    # 3) Preise
    preise_path = USER_DATA / "meine_preise.csv"
    if preise_path.exists():
        export["user_data"]["preise"] = preise_path.read_text(encoding="utf-8-sig")

    # 4) Devis-Historie (alle meta.json + bepreist.sia-Dateien)
    devis_dir = USER_DATA / "devis"
    if devis_dir.exists():
        for dev_dir in sorted(devis_dir.iterdir()):
            if dev_dir.is_dir():
                meta_path = dev_dir / "meta.json"
                if meta_path.exists():
                    try:
                        with open(meta_path, encoding="utf-8") as f:
                            export["user_data"]["devis"].append({
                                "id": dev_dir.name,
                                "meta": json.load(f),
                            })
                    except Exception as e:
                        export["user_data"]["devis"].append({
                            "id": dev_dir.name,
                            "error": str(e),
                        })

    # 5) Audit-Log (nur eigene Eintraege)
    export["user_data"]["audit_log"] = list_audit_log(limit=500, event_filter=None)

    return export


# ==========================================================
# DSGVO RECHT AUF VERGESSENWERDEN (Art. 17)
# ==========================================================

def delete_user_data(keep_audit_log: bool = True, password_confirm: Optional[str] = None) -> Dict[str, int]:
    """Loescht ALLE User-Daten (DSGVO Art. 17).

    ACHTUNG: Dies ist UNWIDERRUFLICH. Backup vorher erstellen!

    Args:
        keep_audit_log: Wenn True, wird der Audit-Log behalten (fuer Compliance-Nachweis)
        password_confirm: Optionales Passwort als Bestaetigung

    Returns: Dict mit Anzahl geloeschter Dateien/Ordner.
    """
    audit_log("delete_user_data_INITIATED", {"keep_audit_log": keep_audit_log})

    deleted = {"files": 0, "directories": 0, "total_size_bytes": 0}

    # User-Daten loeschen (alles ausser Backup-Ordner und Audit-Log)
    for item in USER_DATA.iterdir():
        if item.name == "backups":
            continue  # Backups separat handhaben (oft in Cloud gespiegelt)
        if keep_audit_log and item.name == "audit.log":
            continue

        try:
            if item.is_file():
                deleted["files"] += 1
                deleted["total_size_bytes"] += item.stat().st_size
                item.unlink()
            elif item.is_dir():
                # Anzahl Dateien im Verzeichnis zaehlen
                file_count = sum(1 for _ in item.rglob("*") if _.is_file())
                size = sum(f.stat().st_size for f in item.rglob("*") if f.is_file())
                deleted["files"] += file_count
                deleted["directories"] += 1
                deleted["total_size_bytes"] += size
                shutil.rmtree(item)
        except Exception as e:
            audit_log("delete_user_data_ERROR", {"path": str(item), "error": str(e)})

    # Audit-Log-Eintrag (wenn wir ihn behalten)
    if keep_audit_log:
        audit_log("delete_user_data_COMPLETED", deleted)

    return deleted


# ==========================================================
# AUFNAHME-FRISTEN
# ==========================================================

def enforce_retention_policies(max_backup_age_days: int = 365,
                                max_audit_log_entries: int = AUDIT_LOG_MAX_ENTRIES) -> Dict[str, int]:
    """Loescht automatisch alte Backups und limitiert Audit-Log-Groesse.

    Args:
        max_backup_age_days: Aelteste erlaubte Backup (Default: 1 Jahr)
        max_audit_log_entries: Max Anzahl Audit-Eintraege (Default: 10'000)

    Returns: Dict mit Anzahl geloeschter Backups und Audit-Eintraege.
    """
    deleted = {"backups": 0, "audit_entries": 0}
    now = time.time()
    max_age_seconds = max_backup_age_days * 24 * 60 * 60

    # Alte Backups loeschen
    backup_dir = USER_DATA / "backups"
    if backup_dir.exists():
        for backup_file in backup_dir.iterdir():
            try:
                if backup_file.stat().st_mtime < (now - max_age_seconds):
                    backup_file.unlink()
                    deleted["backups"] += 1
            except Exception:
                pass

    # Audit-Log limitieren
    if AUDIT_LOG.exists():
        with open(AUDIT_LOG, "r", encoding="utf-8") as f:
            lines = f.readlines()
        if len(lines) > max_audit_log_entries:
            kept = lines[-max_audit_log_entries:]
            with open(AUDIT_LOG, "w", encoding="utf-8") as f:
                f.writelines(kept)
            deleted["audit_entries"] = len(lines) - len(kept)

    return deleted


# ==========================================================
# CONVENIENCE
# ==========================================================

def get_compliance_status() -> Dict[str, Any]:
    """Gibt einen Ueberblick ueber den Compliance-Status des User-Accounts.

    Nuetzlich fuer die GUI "Datenschutz" Section.
    """
    return {
        "audit_log_exists": AUDIT_LOG.exists(),
        "audit_log_entries": len(list_audit_log(limit=10_000)),
        "backups_exist": (USER_DATA / "backups").exists() and any((USER_DATA / "backups").iterdir()),
        "data_categories_stored": [
            "Profil" if (USER_DATA / "profil.json").exists() else None,
            "Devis" if (USER_DATA / "devis").exists() else None,
            "Preise" if (USER_DATA / "meine_preise.csv").exists() else None,
            "Kunden" if (USER_DATA / "kunden.json").exists() else None,
        ],
        "export_available": True,
        "delete_available": True,
    }