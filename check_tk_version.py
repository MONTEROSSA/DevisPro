import sys, os, subprocess
print("Python:", sys.version)
# welche python startet die app?
print("sys.executable:", sys.executable)
# tk version
try:
    import tkinter as tk
    root = tk.Tk()
    print("Tk-Version (tkinter):", root.tk.call("info","patchlevel"))
    print("Tcl-Version:", root.tk.call("info","tclversion"))
    root.destroy()
except Exception as e:
    print("tkinter fehler:", e)
# ist tk ueberhaupt verfuegbar?
r = subprocess.run(["which","wish"], capture_output=True, text=True)
print("wish:", r.stdout.strip() or "(nicht gefunden)")
r2 = subprocess.run(["ls","-la","/usr/bin/wish*"], capture_output=True, text=True, shell=True)
print("wish binaries:", r2.stdout.strip())
