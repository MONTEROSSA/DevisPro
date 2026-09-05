import subprocess, sys, time, os

APP = "/Users/ferdinandrothlisberger/devis-auto/DevisPro.app"
LAUNCH = os.path.join(APP, "Contents", "MacOS", "DevisPro")
PY = os.path.join(APP, "Contents", "MacOS", "python-runtime", "bin", "python3")

print("Runtime python tk:", subprocess.run([PY,"-c","import tkinter as tk; r=tk.Tk(); print(r.tk.call('info','patchlevel')); r.destroy()"],
    capture_output=True, text=True).stdout.strip() or "FEHLER")

p = subprocess.Popen([LAUNCH], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
time.sleep(6)
alive = p.poll() is None
print("App lebt:", alive)
if alive:
    try:
        wid = subprocess.run(["osascript","-e",'tell application "System Events" to get id of first window of (first process whose name is "Python")'],
            capture_output=True, text=True, timeout=8).stdout.strip()
        print("Fenster-ID (osascript):", wid or "(unzuverlaessig in headless)")
    except Exception as e:
        print("osascript fehler:", e)
    p.terminate()
else:
    out, err = p.communicate(timeout=4)
    print("CRASH:", err[:2000])
