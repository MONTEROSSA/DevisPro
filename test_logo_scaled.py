import subprocess, sys, time, os, tkinter as tk, importlib.util

RES = "/Volumes/SHGN7/DevisPro.app/Contents/Resources"
ap = os.path.join(RES, "devispro", "app_gui.py")
sys.path.insert(0, RES)
spec = importlib.util.spec_from_file_location("ag", ap)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
app = mod.DevisProApp()
app.update_idletasks()

# logo groesse nach subsample
if hasattr(app, "_logo_img"):
    print("Logo groesse nach skalierung:", app._logo_img.width(), "x", app._logo_img.height())

# finde die seitenleiste (frame mit den buttons)
side = None
for c in app.winfo_children():
    if isinstance(c, tk.Frame):
        # hat IMPORT button?
        for cc in c.winfo_children():
            if isinstance(cc, tk.Button) and "CRB" in (cc.cget("text") or ""):
                side = c
                break
    if side: break

if side:
    print("Seitenleiste gefunden, children:", len(side.winfo_children()))
    # y-positionen der ersten buttons
    for cc in side.winfo_children()[:6]:
        try:
            y = cc.winfo_y()
            txt = cc.cget("text")[:20]
            print(f"  y={y} {type(cc).__name__} '{txt}'")
        except: pass
    # ist das fenster hoch genug fuer alle?
    print("Fenster hoehe:", app.winfo_height())
else:
    print("Seitenleiste nicht gefunden")
app.quit(); app.destroy()
