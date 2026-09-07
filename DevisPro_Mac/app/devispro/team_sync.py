"""Team-Sync (offline-first) - Daten zwischen Geraeten abgleichen.

DevisPro ist bewusst KMU-lokal: kein Cloud-Zwang. Trotzdem soll ein Team
(Buero + Aussendienst, mehrere PCs) denselben Stand teilen. Sync laeuft ueber:

  1) Portabler Datentraeger (USB-Stick / geteilter Ordner):
     - "Export" erzeugt devispro_sync.zip mit Manifest (je Datei/Devis mtime)
     - "Import" wendet das Bundle an -> Last-Write-Wins (LWW)
  2) Lokales Netzwerk (LAN):
     - "Pull" laedt das aktuelle Bundle vom Buero-PC (per Sync-Token gesichert)

Konfliktstrategie: pro Datei bzw. pro Devis-Ordner gewinnt der juengere Stand
(file/dir mtime). Das ist vorhersagbar, ohne dass ein Server noetig ist.

Reine Stdlib.
"""

import os
import json
import zipfile
import shutil
import tempfile
from datetime import datetime

DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")

# (relativer Pfad in data/, art)  art: "file" = ganze Datei LWW, "dir" = je
# unmittelbarer Unterordner LWW (z.B. data/devis/devis_XXXX)
SYNC_ITEMS = [
    ("meine_preise.csv", "file"),
    ("profil.json", "file"),
    ("devis_vorlagen.json", "file"),
    ("wiederkehrend.json", "file"),
    ("kunden.json", "file"),
    ("team.json", "file"),
    ("devis", "dir"),
]


def _mtime(p):
    try:
        return float(os.path.getmtime(p))
    except Exception:
        return 0.0


def build_bundle(data_dir=DATA, out_zip=None):
    """Erzeugt ein Sync-Bundle (ZIP) mit Manifest. Gibt Pfad zurueck."""
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
            else:  # dir -> je Unterordner einzeln verpacken
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
    # Manifest ergaenzen (eigenes Mitglied im ZIP)
    with zipfile.ZipFile(out_zip, "a", zipfile.ZIP_DEFLATED) as z:
        z.writestr("sync_manifest.json", json.dumps(manifest, ensure_ascii=False, indent=1))
    return out_zip


def apply_bundle(zip_path, data_dir=DATA):
    """Wendet ein Bundle an (LWW). Gibt Report-Dict zurueck."""
    report = {"updated": [], "added": [], "skipped": []}
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
                # lokaler Stand juenger/gleich -> behalten
                report["skipped"].append(key)
                continue
            if info["kind"] == "file":
                os.makedirs(os.path.dirname(local) or ".", exist_ok=True)
                shutil.copy2(remote_path, local)
                if not os.path.exists(local) or local_mt == 0:
                    report["added"].append(key)
                else:
                    report["updated"].append(key)
            else:  # dir (devis/<did>)
                if os.path.exists(local):
                    shutil.rmtree(local)
                shutil.copytree(remote_path, local)
                os.utime(local, (remote_mt, remote_mt))
                report["updated" if local_mt > 0 else "added"].append(key)
        # letzten Sync vermerken
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
    """Einmal-Token fuer LAN-Pull (im Buero generiert, an Aussendienst weitergegeben)."""
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
