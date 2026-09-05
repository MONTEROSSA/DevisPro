import subprocess, os
code = '''
import tkinter as tk, os, sys
sys.path.insert(0, "/Users/ferdinandrothlisberger/devis-auto")
import importlib.util
spec = importlib.util.spec_from_file_location("ag", "/Users/ferdinandrothlisberger/devis-auto/devispro/app_gui.py")
mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
root = tk.Tk(); root.withdraw()
app = mod.DevisProApp()
# logo: pruefe ueber tk-option (nicht python attr)
def find_logo(w):
    res = []
    for c in w.winfo_children():
        if isinstance(c, tk.Label):
            try:
                v = str(c.cget("image"))
                if v and v != "" and v != "":
                    res.append((c, v))
            except Exception:
                pass
        res += find_logo(c)
    return res
labels = find_logo(app)
print("LOGO LABEL (cget image):", len(labels) > 0)
for l,v in labels[:1]:
    print("  image-option:", v)
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
