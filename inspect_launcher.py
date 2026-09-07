import subprocess, sys, time, os

LAUNCH = "/Volumes/SHGN7/DevisPro.app/Contents/MacOS/DevisPro"
# launcher inhalt zeigen
print("=== Launcher-Inhalt ===")
print(open(LAUNCH, encoding="utf-8", errors="ignore").read())

# welches python nutzt der launcher? (er macht exec python3)
# wir starten den launcher und checken den prozess-pfad
p = subprocess.Popen([LAUNCH], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
time.sleep(5)
alive = p.poll() is None
if alive:
    # prozess pfad ermitteln
    pid = p.pid
    # ueber ps den python pfad finden
    ps = subprocess.run(["ps","-o","command=","-p",str(pid)], capture_output=True, text=True).stdout.strip()
    print("\n=== Gestarteter Prozess ===")
    print("PID:", pid, "| command:", ps)
    p.terminate()
else:
    out, err = p.communicate(timeout=4)
    print("\n=== CRASH (STDERR) ===")
    print(err[:3000])
