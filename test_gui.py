import sys, os
sys.path.insert(0, "/Users/ferdinandrothlisberger/devis-auto")
# gui modul importierbar?
import importlib.util
spec = importlib.util.spec_from_file_location("app_gui", "/Users/ferdinandrothlisberger/devis-auto/devispro/app_gui.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
# tkinter braucht display - ueberspringe mainloop, teste nur klassen-definition
import tkinter as tk
# fake root
root = tk.Tk()
root.withdraw()
try:
    app = mod.DevisProApp()
    print("DevisProApp instanziiert: OK")
    print("hat _import_crbx:", hasattr(app, "_import_crbx"))
    print("hat _upload_preise:", hasattr(app, "_upload_preise"))
    print("hat _show_offerte:", hasattr(app, "_show_offerte"))
    # logik-test: eigene preise laden + crbx import (ohne gui aufruf)
    from devispro.importers import import_devis
    BASE = "/Volumes/datapool/Ferdinand/Geschäft/ARDE Haus- & Fensterbau AG/Offerten/Tivoli Garten/Tivoli Garten Spreitenbach/Teil 1 Haus A+B/10145-spreitenbach-ueberbauung-tivoli-garten---spreitenbach-ueberbauung-tivoli-garten-bkp221-0-5"
    d = import_devis(os.path.join(BASE, "Sub_2111_BKP221_11.crbx"))
    print("Import positionen:", len(d.positions), "| netto:", round(sum(p.betrag or 0 for p in d.positions),2))
    app.devis = d
    app._fill_table()
    print("Tabelle gefuellt: OK")
    root.destroy()
    print("FERTIG")
except Exception as e:
    import traceback; traceback.print_exc()
    root.destroy()
