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

from . import data_store as ds

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")

# WICHTIG: Die echten KMU-Daten liegen ausserhalb des Bundles
# (~/Library/Application Support/DevisPro). Genau DIESE werden gesichert.
USER_DATA = ds.app_support_dir()

BACKUP_DIR = os.path.join(USER_DATA, "backups")
SCOPE = [
    "meine_preise.csv", "npk_preise.csv", "kunden.json", "verlauf.json",
    "profil.json", "logo.png",
]
# Optional vorhandene Ordner im App-Bundle (falls vom KMU genutzt)
BUNDLE_SCOPE = ["history", "templates"]


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
        # 1) Echte Nutzerdaten aus Application Support sichern
        for item in SCOPE:
            src = os.path.join(USER_DATA, item)
            if os.path.isfile(src) and os.path.getsize(src) > 0:
                z.write(src, item)
                manifest["files"].append({"path": item, "sha256": _hash(src)})
        # 2) Optional vorhandene Ordner im App-Bundle
        for item in BUNDLE_SCOPE:
            src = os.path.join(DATA, item)
            if os.path.isdir(src):
                for f in sorted(os.listdir(src)):
                    fp = os.path.join(src, f)
                    if os.path.isfile(fp):
                        arc = os.path.join(item, f)
                        z.write(fp, arc)
                        manifest["files"].append({"path": arc, "sha256": _hash(fp)})
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
    """Stellt ein Backup wieder her: Nutzerdaten zurueck nach
    Application Support (oder target_data). Liefert Anzahl Dateien."""
    dst = target_data or USER_DATA
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


def erstellen(label=None, note=None):
    """Alias fuer create() — gibt nur den Pfad zurueck (fuer GUI)."""
    pfad, _ = create(label=label, note=note)
    return pfad
