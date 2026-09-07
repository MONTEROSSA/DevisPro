import subprocess, sys, time, os, tkinter as tk, importlib.util

# app laden und fenster-geometrie pruefen (ohne osascript)
VENV_PY = "/Users/ferdinandrothlisberger/.hermes/hermes-agent/venv/bin/python3"
RES = "/Volumes/SHGN7/DevisPro.app/Contents/Resources"
ap = os.path.join(RES, "devispro", "app_gui.py")

# wir laden die app_gui als modul und pruefen fenster
# aber: app_gui ruft mainloop in __main__. wir importieren die klasse
spec = importlib.util.spec_from_file_location("ag", ap)
mod = importlib.util.module_from_spec(spec)
# sys.path fuer devispro
sys.path.insert(0, RES)
spec.loader.exec_module(mod)
app = mod.DevisProApp()
app.update_idletasks()
print("Fenster existiert (winfo_exists):", app.winfo_exists())
print("Fenster groesse:", app.winfo_width(), "x", app.winfo_height())
print("Fenster sichtbar (viewable):", app.winfo_viewable())
print("Anzahl children (widgets):", len(app.winfo_children()))
app.quit(); app.destroy()
print("FERTIG")
