import tkinter as tk, os
gp = "/Volumes/SHGN7/DevisPro.app/Contents/Resources/devispro/logo.gif"
root = tk.Tk(); root.withdraw()
try:
    img = tk.PhotoImage(file=gp)
    print("PhotoImage geladen: JA |", img.width(), "x", img.height())
except Exception as e:
    print("PhotoImage FEHLER:", e)
root.destroy()
print("FERTIG")
