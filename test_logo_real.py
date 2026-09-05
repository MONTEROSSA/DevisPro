import subprocess, sys, time, os, tkinter as tk, importlib.util

RES = "/Users/ferdinandrothlisberger/devis-auto/DevisPro.app/Contents/Resources"
ap = os.path.join(RES, "devispro", "app_gui.py")
sys.path.insert(0, RES)
spec = importlib.util.spec_from_file_location("ag", ap)
mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
app = mod.DevisProApp()
app.update_idletasks()
# pruefe: wo liegt das logo laut app_gui?
import inspect
src = inspect.getsource(app._draw_logo)
print("app_gui __file__:", mod.__file__)
print("logo.gif direkt im devispro/?:", os.path.exists(os.path.join(os.path.dirname(mod.__file__), "logo.gif")))
print("Logo groesse nach _draw_logo:", app._logo_img.width() if hasattr(app,"_logo_img") else "KEIN LOGO")
app.quit(); app.destroy()
