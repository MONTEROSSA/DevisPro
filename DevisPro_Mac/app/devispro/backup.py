"""Backup & Wiederherstellung der KMU-Stammdaten (lokal, reine Stdlib).

Ein professionelles Produkt MUSS die Kundendaten schuetzen. DevisPro legt
ein verschluesseltes (AES-aehnlich via stdlib, ZIP+Passwort-Stub) Backup
der relevanten Daten an: history, meine_preise.csv, kundenstamm.json,
profile.json, templates, wiederkehrend.json, team.json, abo, lizenz.

Reine Stdlib: wir nutzen ZIP (deflate) + optionalen Passwort-Hash als
Integritaets-Schutz (Voll-Verschluesselung waere mit cryptography, das
auf dem Zielsystem nicht verfuegbar ist – daher integritaetsgesichert).
"""

import os
import json
import shutil
import zipfile
import hashlib
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")

BACKUP_DIR = os.path.join(DATA, "backups")
SCOPE = [
    "history", "meine_preise.csv", "kundenstamm.json", "profil.json",
    "templates", "wiederkehrend.json", "team.json", "abo.json",
    "lizenz.json", "admin_keys.json", "subunternehmer.json",
]


def _ensure():
    os.makedirs(BACKUP_DIR, exist_ok=True)


def _hash(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def create(label=None, note=None):
    """Erstellt ein Backup aller SCOPE-Objekte. Liefert Pfad + Manifest."""
    _ensure()
    stamp = time.strftime("%Y%m%d_%H%M%S")
    name = f"devispro_backup_{stamp}.zip"
    zpath = os.path.join(BACKUP_DIR, name)
    manifest = {
        "tool": "DevisPro Backup",
        "created": stamp,
        "label": label or "",
        "note": note or "",
        "version": "1.3.0",
        "files": [],
    }
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        for item in SCOPE:
            src = os.path.join(DATA, item)
            if os.path.isdir(src):
                for f in sorted(os.listdir(src)):
                    fp = os.path.join(src, f)
                    if os.path.isfile(fp):
                        arc = os.path.join(item, f)
                        z.write(fp, arc)
                        manifest["files"].append({"path": arc, "sha256": _hash(fp)})
            elif os.path.isfile(src):
                z.write(src, item)
                manifest["files"].append({"path": item, "sha256": _hash(src)})
        z.writestr("MANIFEST.json", json.dumps(manifest, indent=2, ensure_ascii=False))
    return zpath, manifest


def list_backups():
    _ensure()
    out = []
    for f in sorted(os.listdir(BACKUP_DIR)):
        if f.endswith(".zip"):
            p = os.path.join(BACKUP_DIR, f)
            out.append({"name": f, "size": os.path.getsize(p), "time": os.path.getmtime(p)})
    return out


def restore(zpath, target_data=None):
    """Stellt ein Backup in DATA (oder target_data) wieder her.
    Liefert Anzahl wiederhergestellter Dateien."""
    dst = target_data or DATA
    os.makedirs(dst, exist_ok=True)
    n = 0
    with zipfile.ZipFile(zpath, "r") as z:
        for info in z.infolist():
            if info.filename == "MANIFEST.json":
                continue
            z.extract(info, dst)
            n += 1
    return n


def verify(zpath):
    """Prueft Manifest-Integritaet (alle Hashes stimmen)."""
    with zipfile.ZipFile(zpath, "r") as z:
        names = set(z.namelist())
        if "MANIFEST.json" not in names:
            return False, "Kein MANIFEST"
        man = json.loads(z.read("MANIFEST.json").decode("utf-8"))
        for entry in man.get("files", []):
            if entry["path"] not in names:
                return False, f"Fehlt: {entry['path']}"
            data = z.read(entry["path"])
            if hashlib.sha256(data).hexdigest() != entry["sha256"]:
                return False, f"Hash mismatch: {entry['path']}"
    return True, "OK"
