import subprocess, os

print("=== Verfügbare Pythons ===")
for py in ["/usr/bin/python3", "/Library/Developer/CommandLineTools/usr/bin/python3",
           "/opt/homebrew/bin/python3", "/usr/local/bin/python3",
           "/Users/ferdinandrothlisberger/.hermes/hermes-agent/venv/bin/python3"]:
    if os.path.exists(py):
        try:
            v = subprocess.run([py,"-c","import tkinter as tk; r=tk.Tk(); print(r.tk.call('info','patchlevel')); r.destroy()"],
                               capture_output=True, text=True, timeout=10).stdout.strip()
            print(f"  {py}: tk {v}")
        except Exception as e:
            print(f"  {py}: FEHLER {e}")

print("\n=== brew python? ===")
r = subprocess.run(["which","brew"], capture_output=True, text=True)
print("brew:", r.stdout.strip() or "(nicht installiert)")
if r.stdout.strip():
    r2 = subprocess.run(["brew","list","python3"], capture_output=True, text=True)
    print("python3 via brew:", "ja" if r2.returncode==0 else "nein")
