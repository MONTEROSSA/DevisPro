import subprocess, sys, time, os, tkinter as tk, importlib.util

RES = "/Volumes/SHGN7/DevisPro.app/Contents/Resources"
ap = os.path.join(RES, "devispro", "app_gui.py")
sys.path.insert(0, RES)

spec = importlib.util.spec_from_file_location("ag", ap)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
app = mod.DevisProApp()
app.update_idletasks()
print("Fenster exists:", app.winfo_exists())
print("Viewable:", app.winfo_viewable())
print("Groesse:", app.winfo_width(), "x", app.winfo_height())
# children zaehlen (rekursiv)
def count(w):
    n = len(w.winfo_children())
    for c in w.winfo_children():
        n += count(c)
    return n
print("Widgets gesamt:", count(app))
# logo?
print("Logo image attr:", hasattr(app, "_logo_img"))
try:
    print("Logo geladen:", app._logo_img.width(), "x", app._logo_img.height())
except Exception as e:
    print("Logo fehler:", e)
# import test
from devispro.importers import import_devis
BASE = "/Volumes/datapool/Ferdinand/Geschäft/ARDE Haus- & Fensterbau AG/Offerten/Tivoli Garten/Tivoli Garten Spreitenbach/Teil 1 Haus A+B/10145-spreitenbach-ueberbauung-tivoli-garten---spreitenbach-ueberbauung-tivoli-garten-bkp221-0-5"
d = import_devis(os.path.join(BASE, "Sub_2111_BKP221_11.crbx"))
app.devis = d; app._fill_table()
print("Import OK | pos:", len(d.positions))
app.quit(); app.destroy()
print("FERTIG")
