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
    btns = []
    def count(w):
        for c in w.winfo_children():
            if isinstance(c, tk.Button): btns.append(c.cget("text"))
            count(c)
    count(app)
    print("GUI OK | sichtbare Buttons:", len(btns))
    print("  Logo-Canvas da:", any(isinstance(c, tk.Canvas) for c in app.winfo_children()[0].winfo_children() if hasattr(c,'winfo_children')))
    # kacheln
    print("  Kacheln (Netto/MWST/Brutto):", len(app.kachel.winfo_children()))
    # import test
    from devispro.importers import import_devis
    BASE = "/Volumes/datapool/Ferdinand/Geschäft/ARDE Haus- & Fensterbau AG/Offerten/Tivoli Garten/Tivoli Garten Spreitenbach/Teil 1 Haus A+B/10145-spreitenbach-ueberbauung-tivoli-garten---spreitenbach-ueberbauung-tivoli-garten-bkp221-0-5"
    d = import_devis(os.path.join(BASE, "Sub_2111_BKP221_11.crbx"))
    app.devis = d; app._fill_table()
    print("  Import+Tablle OK | pos:", len(d.positions))
    print("  Kacheln nach import:", len(app.kachel.winfo_children()))
    root.destroy()
    print("FERTIG")
except Exception as e:
    import traceback; traceback.print_exc()
    root.destroy()
