import subprocess, sys, os
sys.path.insert(0,"/Users/ferdinandrothlisberger/devis-auto")
HOST="root@187.77.79.26"; KEY="/Users/ferdinandrothlisberger/devis-auto/_vps_key"
from devispro import marketing as mkt
hp=mkt.homepage_html("de")
open("/Users/ferdinandrothlisberger/devis-auto/_homepage.html","w",encoding="utf-8").write(hp)
print("Homepage lokal generiert:", len(hp), "Zeichen")

def ssh(cmd,timeout=180):
    r=subprocess.run(["ssh","-i",KEY,"-o","StrictHostKeyChecking=no","-o","BatchMode=yes",
                      "-o","ConnectTimeout=15",HOST,cmd],capture_output=True,text=True,timeout=timeout)
    return r.returncode, r.stdout, r.stderr

# 1) Verbindung testen
rc,out,err=ssh("echo OK; whoami; uname -a")
if rc!=0:
    print("SSH FEHLER:", err.strip()); sys.exit(1)
print("SSH verbunden:", out.strip().splitlines()[0])

# 2) Homepage hochladen
r=subprocess.run(["scp","-i",KEY,"-o","StrictHostKeyChecking=no","-o","BatchMode=yes",
                 "/Users/ferdinandrothlisberger/devis-auto/_homepage.html",
                 f"{HOST}:/var/www/devispro/index.html"],capture_output=True,text=True,timeout=120)
print("SCP Homepage:", "OK" if r.returncode==0 else r.stderr.strip())

# 3) Pruefen dass es die neue Version ist
rc,out,err=ssh("grep -c 'Monterossa AG' /var/www/devispro/index.html; grep -c 'So funktioniert' /var/www/devispro/index.html; wc -c /var/www/devispro/index.html")
print("Server-Check (Monterossa / So-funktioniert / Bytes):")
print(out)
rc2,o2,e2=ssh("nginx -t 2>&1 | tail -1")
print("nginx:", o2.strip())
print("FERTIG")
