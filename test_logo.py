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
    # logo pruefen
    side = app.winfo_children()[0]
    has_img = False
    def find_img(w):
        global has_img
        for c in w.winfo_children():
            if isinstance(c, tk.Label) and getattr(c, "image", None):
                has_img = True
            find_img(c)
    find_img(app)
    lp = "/Users/ferdinandrothlisberger/devis-auto/devispro/logo.png"
    print("Logo-PNG existiert:", os.path.exists(lp), "| groesse:", os.path.getsize(lp) if os.path.exists(lp) else 0)
    print("Logo in GUI als Bild geladen:", has_img)
    # auch: tkinter kann png laden?
    try:
        tk.PhotoImage(file=lp); print("tkinter laedt PNG: JA")
    except Exception as e:
        print("tkinter PNG fehler:", e)
    root.destroy()
    print("FERTIG")
except Exception as e:
    import traceback; traceback.print_exc()
    root.destroy()
