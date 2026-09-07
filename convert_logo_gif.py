import os, subprocess
p = "/Users/ferdinandrothlisberger/Downloads/IMG_3220 2.JPG"
out = "/Users/ferdinandrothlisberger/devis-auto/devispro/logo.gif"
r = subprocess.run(["sips","-s","format","gif",p,"--out",out], capture_output=True, text=True, timeout=30)
print("sips rc:", r.returncode, "| err:", r.stderr[:100])
if r.returncode == 0 and os.path.exists(out):
    print("GIF erstellt:", os.path.getsize(out), "bytes")
    # tkinter test
    import tkinter as tk
    root = tk.Tk(); root.withdraw()
    try:
        img = tk.PhotoImage(file=out)
        print("tkinter laedt GIF: JA | groesse:", img.width(), "x", img.height())
    except Exception as e:
        print("tkinter GIF fehler:", e)
    root.destroy()
