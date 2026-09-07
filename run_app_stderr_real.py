import subprocess, sys, time, os

RES = "/Volumes/SHGN7/DevisPro.app/Contents/Resources"
ap = os.path.join(RES, "devispro", "app_gui.py")

# app direkt starten, stderr+stdout zeigen, innerhalb von 4s
p = subprocess.Popen([sys.executable, ap], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
# warte bis prozess endet oder 4s
try:
    out, _ = p.communicate(timeout=4)
    print("=== PROZESS ENDET (crash oder exit) ===")
    print(out[:3000] if out else "(keine ausgabe)")
except subprocess.TimeoutExpired:
    print("=== PROZESS LEBT NACH 4s (mainloop laeuft) ===")
    # fenster check
    wid = subprocess.run(["osascript","-e",'tell application "System Events" to get id of first window of (first process whose name is "Python")'],capture_output=True,text=True,timeout=8).stdout.strip()
    print("Fenster-ID:", wid or "(KEIN FENSTER)")
    p.terminate()
