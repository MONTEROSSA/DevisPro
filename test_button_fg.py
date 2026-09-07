import subprocess, sys, time, os, tkinter as tk, importlib.util

RES = "/Users/ferdinandrothlisberger/devis-auto/DevisPro.app/Contents/Resources"
ap = os.path.join(RES, "devispro", "app_gui.py")
sys.path.insert(0, RES)
spec = importlib.util.spec_from_file_location("ag", ap)
mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
app = mod.DevisProApp(); app.update_idletasks()

# alle buttons mit farbe + schriftfarbe
def walk(w, out):
    for c in w.winfo_children():
        if isinstance(c, tk.Button):
            out.append((c.cget("text"), c.cget("bg"), c.cget("fg")))
        walk(c, out)
btns = []
walk(app, btns)
for t, bg, fg in btns:
    # nur die grauen pruefen
    if bg.lower() in ("gray", "systembuttonface", "#ededed", "systemwindowbody"):
        print(f"  GRAU: '{t}' bg={bg} fg={fg} -> {'OK(schwarz)' if fg.lower() in ('black','#000000') else 'PROBLEM(weiss)'}")
# gesamt
print(f"\nButtons gesamt: {len(btns)}")
gray = [b for b in btns if b[1].lower() in ("gray",)]
print(f"Graue buttons: {len(gray)} -> alle schwarz?: {all(b[2].lower() in ('black','#000000') for b in gray)}")
app.quit(); app.destroy()
