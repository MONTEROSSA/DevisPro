import subprocess, os

# suche python mit tk >= 8.6 irgendwo am system
candidates = []
for root in ["/usr/local", "/opt/homebrew", "/Library/Frameworks/Python.framework",
             "/Users/ferdinandrothlisberger/.hermes", "/Applications"]:
    if not os.path.isdir(root): continue
    for dp,_,fs in os.walk(root):
        for f in fs:
            if f == "python3" or (f.startswith("python3.") and "." in f[7:]):
                p = os.path.join(dp, f)
                candidates.append(p)
        if len(candidates) > 30: break

seen = set()
for p in candidates:
    if p in seen: continue
    seen.add(p)
    try:
        v = subprocess.run([p,"-c","import tkinter as tk; r=tk.Tk(); print(r.tk.call('info','patchlevel')); r.destroy()"],
                           capture_output=True, text=True, timeout=8).stdout.strip()
        if v:
            print(f"  {p}: tk {v}")
    except Exception:
        pass
print("FERTIG")
