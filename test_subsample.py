import tkinter as tk, os
root = tk.Tk()
lp = "/Volumes/SHGN7/DevisPro.app/Contents/Resources/devispro/logo.gif"
img = tk.PhotoImage(file=lp)
print("start:", img.width(), "x", img.height())
while img.width() > 230:
    img = img.subsample(2)
    print("  nach subsample:", img.width(), "x", img.height())
print("ende:", img.width(), "x", img.height())
root.destroy()
