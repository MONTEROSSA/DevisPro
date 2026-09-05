import tkinter as tk
root = tk.Tk()
root.title("FARBTEST")
root.geometry("400x300")
# seitenleiste wie in app
side = tk.Frame(root, bg="#16243d", width=200)
side.pack(side="left", fill="y")
side.pack_propagate(False)
tk.Label(side, text="TEST NAVY", bg="#16243d", fg="white", font=("Helvetica",14,"bold")).pack(pady=20)
# rechts weiss
right = tk.Frame(root, bg="white")
right.pack(side="left", fill="both", expand=True)
tk.Label(right, text="WEISS", bg="white").pack(pady=20)
root.update_idletasks()
root.update()
import subprocess
# screenshot via screencapture des fensters
# fenster id ermitteln
try:
    wid = subprocess.run(["osascript","-e",'tell application "System Events" to get id of first window of (first process whose name is "Python")'],
                         capture_output=True, text=True, timeout=10).stdout.strip()
    subprocess.run(["screencapture","-l",wid,"/tmp/farbtest.png"], capture_output=True, text=True, timeout=10)
    print("wid:", wid, "| screenshot ok")
except Exception as e:
    print("screencapture fehlgeschlagen:", e)
    # fallback: ganze screen
    subprocess.run(["screencapture","/tmp/farbtest.png"], capture_output=True, text=True)
root.mainloop()
