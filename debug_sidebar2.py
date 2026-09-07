import subprocess, sys, time, os, tkinter as tk, importlib.util

RES = "/Volumes/SHGN7/DevisPro.app/Contents/Resources"
ap = os.path.join(RES, "devispro", "app_gui.py")
sys.path.insert(0, RES)
spec = importlib.util.spec_from_file_location("ag", ap)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
app = mod.DevisProApp()
app.update_idletasks()

# alle frames rekursiv durchsuchen, die "IMPORT" oder buttons enthalten
def walk(w, depth=0):
    for c in w.winfo_children():
        txt = ""
        try: txt = c.cget("text")
        except: pass
        if txt and ("IMPORT" in txt or "CRB" in txt or "GAEB" in txt):
            print(f"  Gefunden: {type(c).__name__} '{txt}'")
        walk(c, depth+1)
walk(app)

# zaehle buttons gesamt
btns = []
def count_buttons(w):
    for c in w.winfo_children():
        if isinstance(c, tk.Button): btns.append(c.cget("text"))
        count_buttons(c)
count_buttons(app)
print("Buttons gesamt:", len(btns))
print("Button-Texte:", btns[:10])

# logo bild?
print("Logo attr _logo_img:", hasattr(app, "_logo_img"))
if hasattr(app, "_logo_img"):
    try: print("  logo groesse:", app._logo_img.width(), "x", app._logo_img.height())
    except Exception as e: print("  logo fehler:", e)
app.quit(); app.destroy()
