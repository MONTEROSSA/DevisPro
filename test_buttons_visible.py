import subprocess, sys, time, os, tkinter as tk, importlib.util

RES = "/Volumes/SHGN7/DevisPro.app/Contents/Resources"
ap = os.path.join(RES, "devispro", "app_gui.py")
sys.path.insert(0, RES)
spec = importlib.util.spec_from_file_location("ag", ap)
mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
app = mod.DevisProApp()
app.update_idletasks()

# rekursiv alle buttons
btns = []
def walk(w):
    for c in w.winfo_children():
        if isinstance(c, tk.Button):
            btns.append((c.cget("text"), c.winfo_y()))
        walk(c)
walk(app)
print("Buttons gesamt:", len(btns))
print("Erste 5 (text, y):", btns[:5])
# logo y
if hasattr(app, "_logo_img"):
    print("Logo groesse:", app._logo_img.width(), "x", app._logo_img.height())
# fenster hoehe
print("Fenster hoehe:", app.winfo_height())
# sind alle buttons innerhalb des fensters?
maxy = max(y for _,y in btns) if btns else 0
print("Tiefster button y:", maxy, "| innerhalb fenster:", maxy < app.winfo_height())
app.quit(); app.destroy()
