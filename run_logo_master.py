import subprocess, os
code = '''
import tkinter as tk, os, sys
sys.path.insert(0, "/Users/ferdinandrothlisberger/devis-auto")
import importlib.util
spec = importlib.util.spec_from_file_location("ag", "/Users/ferdinandrothlisberger/devis-auto/devispro/app_gui.py")
mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
app = mod.DevisProApp()
def find_logo(w):
    for c in w.winfo_children():
        if isinstance(c, tk.Label):
            try:
                if str(c.cget("image")) not in ("", "none", "{}"):
                    return True
            except Exception: pass
        if find_logo(c): return True
    return False
print("LOGO im App-Context (master=self):", find_logo(app))
items = app.side.find_all()
rects = [i for i in items if app.side.type(i)=="rectangle"]
print("Canvas-Buttons:", len(rects), "Farbe:", app.side.itemcget(rects[0],"fill"))
app.quit(); app.destroy()
'''
r = subprocess.run(["python3","-c",code], capture_output=True, text=True, timeout=25, cwd="/Users/ferdinandrothlisberger/devis-auto")
print("STDOUT:", r.stdout.strip())
print("ERR:", r.stderr.strip()[:300])
print("RC:", r.returncode)
