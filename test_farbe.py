import tkinter as tk
root = tk.Tk()
f = tk.Frame(root, bg="#16243d", width=100, height=100)
f.pack()
root.update_idletasks(); root.update()
# was gibt tkinter als bg zurueck?
print("cget(bg):", repr(f.cget("bg")))
# winfo_rgb liefert die echte farbe die tkinter nutzt
try:
    r,g,b = root.winfo_rgb(f.cget("bg"))
    print("winfo_rgb:", r, g, b, "(0,0,0)=schwarz (65535,65535,65535)=weiss")
except Exception as e:
    print("winfo_rgb fehler:", e)
root.destroy()
print("FERTIG")
