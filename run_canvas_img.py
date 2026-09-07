import subprocess, os
code = '''
import tkinter as tk, os
root = tk.Tk()
c = tk.Canvas(root, width=300, height=300, bg="navy")
c.pack()
lp = "/Volumes/SHGN7/DevisPro.app/Contents/Resources/devispro/logo.gif"
img = tk.PhotoImage(file=lp)
sub = img
while sub.width() > 460:
    sub = sub.subsample(2)
c.image = sub
cid = c.create_image(150, 150, image=sub, anchor="center")
root.update_idletasks(); root.update()
items = c.find_all()
print("ITEMS:", len(items), [c.type(i) for i in items])
print("IMAGE DA:", any(c.type(i)=="image" for i in items))
root.quit(); root.destroy()
'''
r = subprocess.run(["python3","-c",code], capture_output=True, text=True, timeout=20, cwd="/Users/ferdinandrothlisberger/devis-auto")
print("STDOUT:", r.stdout.strip())
print("ERR:", r.stderr.strip()[:200])
print("RC:", r.returncode)
