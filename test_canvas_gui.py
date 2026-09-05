import sys, os
sys.path.insert(0, "/Users/ferdinandrothlisberger/devis-auto")
import importlib.util
spec = importlib.util.spec_from_file_location("app_gui", "/Users/ferdinandrothlisberger/devis-auto/devispro/app_gui.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
import tkinter as tk
root = tk.Tk(); root.withdraw()
try:
    app = mod.DevisProApp()
    # canvas buttons?
    items = app.side.find_all()
    rects = [i for i in items if app.side.type(i) == "rectangle"]
    texts = [i for i in items if app.side.type(i) == "text"]
    imgs = [i for i in items if app.side.type(i) == "image"]
    print("Canvas-Items gesamt:", len(items))
    print("  Rechtecke (buttons):", len(rects))
    print("  Texte (labels):", len(texts))
    print("  Logo-Bild:", len(imgs) > 0)
    # farbe eines rechecks pruefen
    if rects:
        col = app.side.itemcget(rects[0], "fill")
        print("  Farbe button 1:", col, "(nicht systemWindowBody => canvas rendert)")
    # import test
    from devispro.importers import import_devis
    BASE = "/Volumes/datapool/Ferdinand/Geschäft/ARDE Haus- & Fensterbau AG/Offerten/Tivoli Garten/Tivoli Garten Spreitenbach/Teil 1 Haus A+B/10145-spreitenbach-ueberbauung-tivoli-garten---spreitenbach-ueberbauung-tivoli-garten-bkp221-0-5"
    d = import_devis(os.path.join(BASE, "Sub_2111_BKP221_11.crbx"))
    app.devis = d; app._fill_table()
    print("  Import OK | pos:", len(d.positions))
    print("  Kacheln:", len(app.kachel.winfo_children()))
    root.destroy()
    print("FERTIG")
except Exception as e:
    import traceback; traceback.print_exc()
    root.destroy()
