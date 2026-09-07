import subprocess, sys, time, os

VENV_PY = "/Users/ferdinandrothlisberger/.hermes/hermes-agent/venv/bin/python3"
RES = "/Volumes/SHGN7/DevisPro.app/Contents/Resources"
ap = os.path.join(RES, "devispro", "app_gui.py")

print("Teste App mit venv-python (tk 9.0.3)...")
p = subprocess.Popen([VENV_PY, ap], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
try:
    out, _ = p.communicate(timeout=4)
    print("ENDET (crash):", out[:1500] if out else "(keine ausgabe)")
except subprocess.TimeoutExpired:
    print("LEBT nach 4s")
    wid = subprocess.run(["osascript","-e",'tell application "System Events" to get id of first window of (first process whose name is "Python")'],capture_output=True,text=True,timeout=8).stdout.strip()
    print("Fenster-ID:", wid or "(KEIN FENSTER)")
    p.terminate()
