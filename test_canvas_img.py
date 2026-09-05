import tkinter as tk, os
root = tk.Tk()
c = tk.Canvas(root, width=300, height=300, bg="navy")
c.pack()
lp = "/Volumes/SHGN7/DevisPro.app/Contents/Resources/devispro/logo.gif"
print("logo existiert:", os.path.exists(lp), os.path.getsize(lp) if os.path.exists(lp) else 0)
img = tk.PhotoImage(file=lp)
print("photoimage:", img.width(), "x", img.height())
sub = img
while sub.width() > 460:
    sub = sub.subsample(2)
print("nach subsample:", sub.width(), "x", sub.height())
c.image = sub
cid = c.create_image(150, 150, image=sub, anchor="center")
print("create_image id:", cid)
root.update_idletasks(); root.update()
# check ob das item da ist
items = c.find_all()
print("canvas items:", len(items), [c.type(i) for i in items])
print("image item vorhanden:", any(c.type(i)=="image" for i in items))
root.quit(); root.destroy()
print("FERTIG")
