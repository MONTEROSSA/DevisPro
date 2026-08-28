"""Team-Sync (offline-first) - Daten zwischen Geraeten abgleichen.
CRDT-basiert: file_lock, sync_watch, merge_positions, presence.json, Konflikt-Marker.
Reine Stdlib + Watchdog (optional).
"""
from __future__ import annotations
import os
import json
import zipfile
import shutil
import tempfile
import threading
import time
import fcntl
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False

DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")

SYNC_ITEMS = [
    ("meine_preise.csv", "file"),
    ("profil.json", "file"),
    ("devis_vorlagen.json", "file"),
    ("wiederkehrend.json", "file"),
    ("kunden.json", "file"),
    ("team.json", "file"),
    ("analysen.json", "file"),
    ("devis", "dir"),
]

def _mtime(p):
    try:
        return float(os.path.getmtime(p))
    except Exception:
        return 0.0


# ============================================================
# File Locking (pro Devis-Ordner)
# ============================================================

LOCK_DIR = Path(DATA) / "locks"
LOCK_DIR.mkdir(parents=True, exist_ok=True)

def file_lock(devis_id: str, user_id: str, user_name: str = "") -> bool:
    """Erwirbt exklusiven Lock für einen Devis-Ordner.
    Returns True wenn Lock erworben, False wenn schon gelockt.
    """
    lock_file = LOCK_DIR / f"{devis_id}.lock"
    lock_file.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        # Atomic create with O_EXCL
        fd = os.open(lock_file, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
        with os.fdopen(fd, "w") as f:
            json.dump({
                "devis_id": devis_id,
                "user_id": user_id,
                "user_name": user_name,
                "locked_at": datetime.now().isoformat(),
                "pid": os.getpid(),
            }, f)
        return True
    except FileExistsError:
        # Prüfen ob Lock veraltet (PID nicht mehr existent)
        try:
            with open(lock_file, "r") as f:
                lock_data = json.load(f)
            pid = lock_data.get("pid", 0)
            if pid and not _pid_exists(pid):
                # Stale lock -> übernehmen
                return file_lock(devis_id, user_id, user_name)
        except Exception:
            pass
        return False
    except Exception:
        return False


def file_unlock(devis_id: str, user_id: str) -> bool:
    """Gibt Lock frei (nur Owner darf entsperren)."""
    lock_file = LOCK_DIR / f"{devis_id}.lock"
    try:
        with open(lock_file, "r") as f:
            lock_data = json.load(f)
        if lock_data.get("user_id") == user_id:
            os.remove(lock_file)
            return True
        return False
    except Exception:
        return False


def file_lock_status(devis_id: str) -> Optional[Dict[str, Any]]:
    """Gibt Lock-Status zurück: None=frei, Dict=gelockt."""
    lock_file = LOCK_DIR / f"{devis_id}.lock"
    try:
        with open(lock_file, "r") as f:
            data = json.load(f)
        # Prüfen ob PID noch lebt
        pid = data.get("pid", 0)
        if pid and not _pid_exists(pid):
            # Stale -> aufräumen
            os.remove(lock_file)
            return None
        return data
    except Exception:
        return None


def _pid_exists(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


# ============================================================
# Presence (wer ist online im Shared Folder)
# ============================================================

PRESENCE_FILE = Path(DATA) / "presence.json"
PRESENCE_TTL = 30  # Sekunden

def presence_update(user_id: str, user_name: str, current_devis: str = "") -> None:
    """Aktualisiert Presence-Eintrag für User."""
    PRESENCE_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    # Lade bestehende
    presence = {}
    if PRESENCE_FILE.exists():
        try:
            with open(PRESENCE_FILE, "r") as f:
                presence = json.load(f)
        except Exception:
            presence = {}
    
    presence[user_id] = {
        "user_id": user_id,
        "user_name": user_name,
        "current_devis": current_devis,
        "last_seen": datetime.now().isoformat(),
    }
    
    # Cleanup alte Einträge
    now = datetime.now()
    for uid, data in list(presence.items()):
        try:
            last = datetime.fromisoformat(data.get("last_seen", ""))
            if (now - last).total_seconds() > PRESENCE_TTL * 3:
                del presence[uid]
        except Exception:
            del presence[uid]
    
    # Atomic write
    tmp = PRESENCE_FILE.with_suffix(".tmp")
    with open(tmp, "w") as f:
        json.dump(presence, f, ensure_ascii=False, indent=1)
    os.replace(tmp, PRESENCE_FILE)


def presence_get() -> Dict[str, Dict[str, Any]]:
    """Gibt alle aktiven User zurück."""
    if not PRESENCE_FILE.exists():
        return {}
    try:
        with open(PRESENCE_FILE, "r") as f:
            data = json.load(f)
        # Filter expired
        now = datetime.now()
        result = {}
        for uid, d in data.items():
            try:
                last = datetime.fromisoformat(d.get("last_seen", ""))
                if (now - last).total_seconds() <= PRESENCE_TTL:
                    result[uid] = d
            except Exception:
                pass
        return result
    except Exception:
        return {}


def presence_heartbeat(user_id: str, user_name: str, current_devis: str = "", interval: int = 10):
    """Startet Heartbeat-Thread für Presence (daemon)."""
    def _beat():
        while True:
            presence_update(user_id, user_name, current_devis)
            time.sleep(interval)
    t = threading.Thread(target=_beat, daemon=True)
    t.start()
    return t


# ============================================================
# Sync Watch (polling / Watchdog auf Shared Folder)
# ============================================================

class SyncEventHandler(FileSystemEventHandler):
    def __init__(self, callback: Callable[[str], None]):
        self.callback = callback
        self._last_event = 0
    
    def on_any_event(self, event):
        if event.is_directory:
            return
        now = time.time()
        if now - self._last_event < 1.0:  # Debounce
            return
        self._last_event = now
        self.callback(event.src_path)


def sync_watch(shared_folder: str, callback: Callable[[str], None], poll_interval: float = 5.0) -> threading.Thread:
    """Überwacht Shared Folder auf Änderungen.
    Nutzt Watchdog wenn verfügbar, sonst Polling.
    Callback erhält geänderten Pfad.
    Returns Thread (daemon).
    """
    shared_path = Path(shared_folder)
    shared_path.mkdir(parents=True, exist_ok=True)
    
    stop_event = threading.Event()
    
    def _poll():
        last_mtimes = {}
        while not stop_event.is_set():
            try:
                for item in shared_path.rglob("*"):
                    if item.is_file():
                        mt = item.stat().st_mtime
                        key = str(item.relative_to(shared_path))
                        if key not in last_mtimes or last_mtimes[key] != mt:
                            last_mtimes[key] = mt
                            callback(str(item))
            except Exception:
                pass
            stop_event.wait(poll_interval)
    
    if WATCHDOG_AVAILABLE:
        observer = Observer()
        handler = SyncEventHandler(callback)
        observer.schedule(handler, str(shared_path), recursive=True)
        observer.start()
        
        def _stop():
            observer.stop()
            observer.join()
        stop_event._observer = observer  # type: ignore
        stop_event._stop_hook = _stop  # type: ignore
    else:
        # Polling fallback
        pass
    
    t = threading.Thread(target=_poll, daemon=True)
    t.start()
    return t


def sync_watch_stop(watch_thread: threading.Thread):
    """Stoppt sync_watch Thread."""
    if hasattr(watch_thread, '_stop_hook'):
        watch_thread._stop_hook()
    # Daemon threads stop automatically on exit


# ============================================================
# Merge mit Konflikt-Markern (CRDT-style LWW + Konflikte)
# ============================================================

def merge_positions(local: List[Dict], remote: List[Dict], 
                    key_field: str = "pos_nr") -> Tuple[List[Dict], List[Dict]]:
    """Merged zwei Positions-Listen (LWW + Konflikt-Erkennung).
    Returns: (merged_list, conflicts_list)
    """
    merged = {}
    conflicts = []
    
    # Remote first (basis)
    for item in remote:
        key = item.get(key_field)
        if key:
            merged[key] = {"data": item, "source": "remote", "mtime": item.get("_mtime", 0)}
    
    # Local overlay
    for item in local:
        key = item.get(key_field)
        if key:
            local_mtime = item.get("_mtime", 0)
            if key in merged:
                remote_mtime = merged[key]["mtime"]
                if abs(local_mtime - remote_mtime) < 1.0:
                    # Gleichzeitige Änderung -> Konflikt
                    conflicts.append({
                        "key": key,
                        "local": item,
                        "remote": merged[key]["data"],
                        "field": key_field,
                    })
                    # LWW: neuerer gewinnt
                    if local_mtime > remote_mtime:
                        merged[key] = {"data": item, "source": "local", "mtime": local_mtime}
                elif local_mtime > remote_mtime:
                    merged[key] = {"data": item, "source": "local", "mtime": local_mtime}
            else:
                merged[key] = {"data": item, "source": "local", "mtime": local_mtime}
    
    return [v["data"] for v in merged.values()], conflicts


def write_conflict_marker(devis_id: str, conflicts: List[Dict]) -> str:
    """Schreibt Konflikt-Datei für manuelle Auflösung."""
    conflict_file = Path(DATA) / "devis" / devis_id / "conflicts.json"
    conflict_file.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "devis_id": devis_id,
        "created": datetime.now().isoformat(),
        "conflicts": conflicts,
    }
    with open(conflict_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    return str(conflict_file)


def read_conflict_marker(devis_id: str) -> Optional[List[Dict]]:
    """Liest ungelöste Konflikte."""
    conflict_file = Path(DATA) / "devis" / devis_id / "conflicts.json"
    try:
        with open(conflict_file, "r") as f:
            return json.load(f).get("conflicts", [])
    except Exception:
        return None


def resolve_conflict(devis_id: str, key: str, resolution: str, resolved_data: Dict) -> bool:
    """Markiert Konflikt als gelöst (resolution: 'local'|'remote'|'manual')."""
    conflicts = read_conflict_marker(devis_id)
    if not conflicts:
        return False
    
    remaining = [c for c in conflicts if c["key"] != key]
    if len(remaining) == len(conflicts):
        return False
    
    conflict_file = Path(DATA) / "devis" / devis_id / "conflicts.json"
    if remaining:
        with open(conflict_file, "w", encoding="utf-8") as f:
            json.dump({"devis_id": devis_id, "conflicts": remaining}, f, ensure_ascii=False, indent=1)
    else:
        conflict_file.unlink(missing_ok=True)
    return True


# ============================================================
# Bundle Functions (erweitert)
# ============================================================

def build_bundle(data_dir=DATA, out_zip=None):
    if out_zip is None:
        os.makedirs(data_dir, exist_ok=True)
        out_zip = os.path.join(data_dir, "devispro_sync.zip")
    manifest = {"generated": datetime.now().isoformat(), "items": {}}
    with zipfile.ZipFile(out_zip, "w", zipfile.ZIP_DEFLATED) as z:
        for name, kind in SYNC_ITEMS:
            src = os.path.join(data_dir, name)
            if not os.path.exists(src):
                continue
            if kind == "file":
                arc = os.path.join("sync", name)
                z.write(src, arc)
                manifest["items"][name] = {"kind": "file", "mtime": _mtime(src)}
            else:
                for entry in sorted(os.listdir(src)):
                    full = os.path.join(src, entry)
                    if not os.path.isdir(full):
                        continue
                    mt = max((_mtime(os.path.join(full, f)) for f in os.listdir(full)),
                             default=_mtime(full))
                    for root, _, files in os.walk(full):
                        for f in files:
                            fp = os.path.join(root, f)
                            arc = os.path.join("sync", name, os.path.relpath(fp, src))
                            z.write(fp, arc)
                    manifest["items"][os.path.join(name, entry)] = {"kind": "dir", "mtime": mt}
    with zipfile.ZipFile(out_zip, "a", zipfile.ZIP_DEFLATED) as z:
        z.writestr("sync_manifest.json", json.dumps(manifest, ensure_ascii=False, indent=1))
    return out_zip


def apply_bundle(zip_path, data_dir=DATA):
    report = {"updated": [], "added": [], "skipped": [], "conflicts": []}
    if not os.path.exists(zip_path):
        raise FileNotFoundError("Bundle nicht gefunden: " + zip_path)
    tmp = tempfile.mkdtemp(prefix="hermes_sync_")
    try:
        with zipfile.ZipFile(zip_path) as z:
            manifest = json.loads(z.read("sync_manifest.json"))
            z.extractall(tmp)
        for key, info in manifest["items"].items():
            local = os.path.join(data_dir, key)
            remote_path = os.path.join(tmp, "sync", key)
            if not os.path.exists(remote_path):
                continue
            remote_mt = float(info.get("mtime", 0))
            local_mt = _mtime(local)
            if remote_mt <= local_mt + 0.5:
                report["skipped"].append(key)
                continue
            if info["kind"] == "file":
                os.makedirs(os.path.dirname(local) or ".", exist_ok=True)
                shutil.copy2(remote_path, local)
                if not os.path.exists(local) or local_mt == 0:
                    report["added"].append(key)
                else:
                    report["updated"].append(key)
            else:
                if os.path.exists(local):
                    shutil.rmtree(local)
                shutil.copytree(remote_path, local)
                os.utime(local, (remote_mt, remote_mt))
                report["updated" if local_mt > 0 else "added"].append(key)
        try:
            with open(os.path.join(data_dir, "sync_last.json"), "w", encoding="utf-8") as f:
                json.dump({"at": datetime.now().isoformat(),
                           "bundles": len(manifest["items"])}, f)
        except Exception:
            pass
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return report


def last_sync(data_dir=DATA):
    p = os.path.join(data_dir, "sync_last.json")
    if os.path.exists(p):
        try:
            return json.load(open(p, encoding="utf-8"))
        except Exception:
            return None
    return None


def sync_token_erzeugen(data_dir=DATA, gueltig_tage=30):
    import hmac, hashlib, secrets
    seed = secrets.token_hex(16)
    tok = hmac.new(b"devispro-sync", seed.encode(), hashlib.sha256).hexdigest()[:24]
    pfad = os.path.join(data_dir, "sync_token.json")
    with open(pfad, "w", encoding="utf-8") as f:
        json.dump({"token": tok, "created": datetime.now().isoformat()}, f)
    return tok


def sync_token_gueltig(token, data_dir=DATA):
    pfad = os.path.join(data_dir, "sync_token.json")
    if not token or not os.path.exists(pfad):
        return False
    try:
        d = json.load(open(pfad, encoding="utf-8"))
        return d.get("token") == token
    except Exception:
        return False


# ============================================================
# Sync Status für UI
# ============================================================

def sync_status(data_dir=DATA) -> Dict[str, Any]:
    """Gibt Sync-Status für UI zurück: 'synced' | 'pending' | 'conflict' | 'offline'."""
    last = last_sync(data_dir)
    conflicts_exist = any(
        (Path(DATA) / "devis" / d / "conflicts.json").exists()
        for d in os.listdir(Path(DATA) / "devis")
        if (Path(DATA) / "devis" / d).is_dir()
    ) if (Path(DATA) / "devis").exists() else False
    
    if conflicts_exist:
        return {"status": "conflict", "message": "Konflikte vorhanden", "last_sync": last}
    
    if last:
        try:
            last_dt = datetime.fromisoformat(last["at"])
            age = (datetime.now() - last_dt).total_seconds()
            if age < 300:  # 5 Min
                return {"status": "synced", "message": "Synchronisiert", "last_sync": last}
            elif age < 3600:
                return {"status": "pending", "message": f"Letzter Sync vor {int(age/60)} Min", "last_sync": last}
            else:
                return {"status": "offline", "message": f"Letzter Sync vor {int(age/3600)} Std", "last_sync": last}
        except Exception:
            pass
    
    return {"status": "offline", "message": "Nie synchronisiert", "last_sync": None}


# Test
if __name__ == "__main__":
    print("Testing locks...")
    print(file_lock("devis_001", "user1", "Hans"))
    print(file_lock("devis_001", "user2", "Peter"))  # False
    print(file_lock_status("devis_001"))
    print(file_unlock("devis_001", "user1"))
    print(file_lock("devis_001", "user2", "Peter"))  # True now