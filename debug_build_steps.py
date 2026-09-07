import subprocess, sys, time, os, tkinter as tk, importlib.util, traceback

RES = "/Volumes/SHGN7/DevisPro.app/Contents/Resources"
ap = os.path.join(RES, "devispro", "app_gui.py")
sys.path.insert(0, RES)

# lade modul, baue app, fange fehler in _build_ui ab
spec = importlib.util.spec_from_file_location("ag", ap)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

app = mod.DevisProApp.__new__(mod.DevisProApp)
try:
    app.__init__()
    print("__init__ OK")
except Exception as e:
    print("FEHLER in __init__/_build_ui:")
    traceback.print_exc()

# wie viele direkte children der seitenleiste?
try:
    # finde das side-frame
    def find_side(w):
        for c in w.winfo_children():
            if isinstance(c, tk.Frame) and c.winfo_width()==250:
                return c
            r = find_side(c)
            if r: return r
        return None
    side = find_side(app)
    if side:
        print("Sidebar children:", len(side.winfo_children()))
        for c in side.winfo_children()[:8]:
            print("  ", type(c).__name__, c.cget("text")[:30] if hasattr(c,'cget') else "")
    else:
        print("Sidebar nicht gefunden")
    app.quit(); app.destroy()
except Exception as e:
    print("Fehler bei analyse:", e)
