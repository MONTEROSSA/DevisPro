import subprocess, os
code = '''
import tkinter as tk, os
lp = "/Volumes/SHGN7/DevisPro.app/Contents/Resources/devispro/logo.gif"
print("exist:", os.path.exists(lp), os.path.getsize(lp))
root = tk.Tk()
try:
    img = tk.PhotoImage(file=lp)
    print("PHOTOIMAGE OK:", img.width(), "x", img.height())
    lbl = tk.Label(root, image=img, bg="#16243d")
    lbl.pack()
    v = lbl.cget("image")
    print("label cget image:", repr(v))
    print("label hat bild:", bool(v))
except Exception as e:
    print("FEHLER:", repr(e))
root.quit(); root.destroy()
'''
r = subprocess.run(["python3","-c",code], capture_output=True, text=True, timeout=20, cwd="/Users/ferdinandrothlisberger/devis-auto")
print("STDOUT:", r.stdout.strip())
print("ERR:", r.stderr.strip()[:300])
print("RC:", r.returncode)
