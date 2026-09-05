import subprocess, sys, time, os, tkinter as tk, importlib.util

RES = "/Volumes/SHGN7/DevisPro.app/Contents/Resources"
ap = os.path.join(RES, "devispro", "app_gui.py")
sys.path.insert(0, RES)

spec = importlib.util.spec_from_file_location("ag", ap)
mod = importlib.util.module_from_spec(spec)
try:
    spec.loader.exec_module(mod)
    print("Modul geladen OK")
    app = mod.DevisProApp.__new__(mod.DevisProApp)
    print("Instanz erstellt")
    try:
        app.__init__()
        print("_build_ui OK (kein fehler)")
        print("Children:", len(app.winfo_children()))
        app.quit(); app.destroy()
    except Exception as e:
        import traceback
        print("=== FEHLER IN _build_ui ===")
        traceback.print_exc()
except Exception as e:
    import traceback
    print("=== FEHLER BEIM LADEN ===")
    traceback.print_exc()
