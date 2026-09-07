import subprocess, os
code = '''
import tkinter as tk, os, sys
sys.path.insert(0, "/Users/ferdinandrothlisberger/devis-auto")
import importlib.util
spec = importlib.util.spec_from_file_location("ag", "/Users/ferdinandrothlisberger/devis-auto/devispro/app_gui.py")
mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
root = tk.Tk(); root.withdraw()
app = mod.DevisProApp()
# logo label finden
def find_img_label(w):
    res = []
    for c in w.winfo_children():
        if isinstance(c, tk.Label) and getattr(c, "image", None):
            res.append(c)
        res += find_img_label(c)
    return res
labels = find_img_label(app)
print("LOGO LABEL DA:", len(labels) > 0)
if labels:
    print("  label image attr:", getattr(labels[0], "image", None) is not None)
# canvas buttons
items = app.side.find_all()
rects = [i for i in items if app.side.type(i)=="rectangle"]
print("CANVAS BUTTONS:", len(rects), "| farbe:", app.side.itemcget(rects[0],"fill") if rects else "KEINE")
root.quit(); root.destroy()
'''
r = subprocess.run(["python3","-c",code], capture_output=True, text=True, timeout=25, cwd="/Users/ferdinandrothlisberger/devis-auto")
print("STDOUT:", r.stdout.strip())
print("ERR:", r.stderr.strip()[:300])
print("RC:", r.returncode)
