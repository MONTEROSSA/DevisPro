import subprocess, sys, os, time
sys.path.insert(0, "/Users/ferdinandrothlisberger/devis-auto")
ROOT = "/Users/ferdinandrothlisberger/devis-auto"
HOST = "root@187.77.79.26"
KEY = os.path.join(ROOT, "_vps_key")

from devispro import marketing as mkt

# 1) Lokale Artefakte erzeugen (render_landing = die oeffentliche Homepage mit allen Features)
hp = mkt.render_landing("de")
hp_path = os.path.join(ROOT, "_homepage.html")
open(hp_path, "w", encoding="utf-8").write(hp)
print("Homepage generiert (render_landing): %d Zeichen" % len(hp))

bundle = os.path.join(ROOT, "DevisPro_Mac.zip")
print("Bundle: %d bytes" % os.path.getsize(bundle))

def ssh(cmd, timeout=180):
    r = subprocess.run(
        ["ssh", "-i", KEY, "-o", "StrictHostKeyChecking=no", "-o", "BatchMode=yes",
         "-o", "ConnectTimeout=15", HOST, cmd],
        capture_output=True, text=True, timeout=timeout)
    return r.returncode, r.stdout, r.stderr

def scp(local, remote, timeout=120):
    return subprocess.run(
        ["scp", "-i", KEY, "-o", "StrictHostKeyChecking=no", "-o", "BatchMode=yes",
         local, f"{HOST}:{remote}"],
        capture_output=True, text=True, timeout=timeout)

# 2) Verbindung testen (Key muss im hPanel sein!)
rc, out, err = ssh("echo OK; whoami")
if rc != 0:
    print("\n=== SSH NOCH NICHT MOEGLICH ===")
    print("Grund:", (err or "keine Antwort").strip()[:300])
    print(">>> Bitte den SSH-Public-Key im hPanel bei srv1622267 eintragen,")
    print(">>> dann diesen Helper erneut starten:  python3 _vps_upload.py")
    sys.exit(2)

print("SSH verbunden:", out.strip().splitlines()[0])

# 3) Homepage hochladen
r = scp(hp_path, "/var/www/devispro/index.html")
print("SCP Homepage:", "OK" if r.returncode == 0 else r.stderr.strip())

# 4) Bundle hochladen
r = scp(bundle, "/var/www/devispro/DevisPro_Mac.zip")
print("SCP Bundle:", "OK" if r.returncode == 0 else r.stderr.strip())

# 5) Server-Check
rc, out, err = ssh(
    "grep -c 'Beispiel-Devis erstellen' /var/www/devispro/index.html; "
    "grep -c 'erp_vorschau' /var/www/devispro/index.html; "
    "grep -c 'download_gate' /var/www/devispro/index.html; "
    "wc -c /var/www/devispro/index.html; "
    "ls -la /var/www/devispro/DevisPro_Mac.zip")
print("Server-Check (Beispiel-Devis / erp_vorschau / download_gate / Bytes / Bundle):")
print(out)

# 6) HTTPS pruefen
import urllib.request
try:
    with urllib.request.urlopen("https://devispro.de/", timeout=10) as resp:
        live = resp.read().decode("utf-8", "ignore")
    print("HTTPS devispro.de: HTTP %d, Beispiel-Devis drin: %s, ERP-Vorschau drin: %s" % (
        resp.status, "Beispiel-Devis erstellen" in live, "erp_vorschau" in live))
except Exception as e:
    print("HTTPS-Check Fehler:", e)
print("FERTIG")
