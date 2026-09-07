import sys, os
sys.path.insert(0, "/Users/ferdinandrothlisberger/devis-auto")
import tkinter as tk
import importlib.util
spec = importlib.util.spec_from_file_location("app_gui", "/Users/ferdinandrothlisberger/devis-auto/devispro/app_gui.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
root = tk.Tk(); root.withdraw()
try:
    app = mod.DevisProApp()
    # zaehle side buttons
    def count(btn, n=0):
        for c in btn.winfo_children():
            if isinstance(c, tk.Button): n+=1
            n = count(c, n)
        return n
    n = count(app)
    print("GUI instanziiert OK | sichtbare Buttons im Fenster:", n)
    # import test
    from devispro.importers import import_devis
    BASE = "/Volumes/datapool/Ferdinand/Geschäft/ARDE Haus- & Fensterbau AG/Offerten/Tivoli Garten/Tivoli Garten Spreitenbach/Teil 1 Haus A+B/10145-spreitenbach-ueberbauung-tivoli-garten---spreitenbach-ueberbauung-tivoli-garten-bkp221-0-5"
    d = import_devis(os.path.join(BASE, "Sub_2111_BKP221_11.crbx"))
    app.devis = d; app._fill_table()
    print("Import+Tablle OK | pos:", len(d.positions))
    root.destroy()
    print("FERTIG")
except Exception as e:
    import traceback; traceback.print_exc()
    root.destroy()
