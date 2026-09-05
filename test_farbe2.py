import tkinter as tk, threading, time
root = tk.Tk()
f = tk.Frame(root, bg="#16243d", width=100, height=100)
f.pack()
root.update_idletasks(); root.update()
print("cget(bg):", repr(f.cget("bg")))
try:
    r,g,b = root.winfo_rgb(f.cget("bg"))
    print("winfo_rgb:", r, g, b)
except Exception as e:
    print("winfo_rgb fehler:", e)
root.quit()
root.destroy()
print("FERTIG")
