import subprocess, sys, time, os

APP = "/Users/ferdinandrothlisberger/devis-auto/DevisPro.app"
LAUNCH = os.path.join(APP, "Contents", "MacOS", "DevisPro")
RES = os.path.join(APP, "Contents", "Resources")

p = subprocess.Popen([LAUNCH], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
time.sleep(6)
alive = p.poll() is None
print("App lebt:", alive)
if alive:
    # tk version ueber runtime python mit TCL_LIBRARY gesetzt
    py = os.path.join(APP, "Contents", "MacOS", "python-runtime", "bin", "python3")
    env = dict(os.environ, TCL_LIBRARY=os.path.join(RES,"tcltk","tcl9.0"), TK_LIBRARY=os.path.join(RES,"tcltk","tk9.0"))
    r = subprocess.run([py,"-c","import tkinter as tk; w=tk.Tk(); print('tk', w.tk.call('info','patchlevel')); w.destroy()"],
        capture_output=True, text=True, env=env, timeout=10)
    print("tk test:", r.stdout.strip() or r.stderr.strip()[:200])
    p.terminate()
else:
    out, err = p.communicate(timeout=4)
    print("CRASH:", err[:2000])
