import subprocess, sys, time, os

LAUNCH = "/Volumes/SHGN7/DevisPro.app/Contents/MacOS/DevisPro"
# launcher starten, stderr zeigen (wie doppelklick)
p = subprocess.Popen([LAUNCH], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
time.sleep(5)
alive = p.poll() is None
if alive:
    print("LEBT (kein crash)")
    p.terminate()
    returncode = 0
else:
    out, err = p.communicate(timeout=4)
    print("=== CRASH STDERR ===")
    print(err[:2500])
