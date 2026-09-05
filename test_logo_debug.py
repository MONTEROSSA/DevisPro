import subprocess, sys, time, os, tkinter as tk, importlib.util

RES = "/Users/ferdinandrothlisberger/devis-auto/DevisPro.app/Contents/Resources"
ap = os.path.join(RES, "devispro", "app_gui.py")
sys.path.insert(0, RES)
spec = importlib.util.spec_from_file_location("ag", ap)
mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)

# monkeypatch _draw_logo um zu sehen was passiert
orig = mod.DevisProApp._draw_logo
def patched(self, parent):
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    logo_path = os.path.join(base, "devispro", "logo.gif")
    print("logo_path existiert:", os.path.exists(logo_path), "->", logo_path)
    orig(self, parent)
    if hasattr(self, "_logo_img"):
        print("nach _draw_logo: logo groesse =", self._logo_img.width(), "x", self._logo_img.height())
mod.DevisProApp._draw_logo = patched

app = mod.DevisProApp()
app.update_idletasks()
app.quit(); app.destroy()
